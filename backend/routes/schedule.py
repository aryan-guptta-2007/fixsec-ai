import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core import github
from core.billing import get_billing_manager
from core.notifications import send_notifications, validate_webhook_url
from core.scan_engine import PlanLimitError, is_demo_repo, require_github_token
from core.scheduler import (
    NotificationChannel,
    ScanFrequency,
    create_scheduled_scan,
    get_scheduled_scan,
    get_user_scheduled_scans,
    next_run_after,
    serialize_schedule,
)
from db.models import ScheduledScan, User
from db.session import get_db
from routes.auth import get_current_user

router = APIRouter()


class NotificationChannelModel(BaseModel):
    type: NotificationChannel
    email: Optional[str] = None
    webhook_url: Optional[str] = None
    custom_payload: Optional[Dict[str, Any]] = None


class CreateScheduleModel(BaseModel):
    repo: str
    frequency: ScanFrequency
    notification_channels: List[NotificationChannelModel] = []
    enabled: bool = True


class UpdateScheduleModel(BaseModel):
    frequency: Optional[ScanFrequency] = None
    notification_channels: Optional[List[NotificationChannelModel]] = None
    enabled: Optional[bool] = None


def _require_scheduling(db: Session, user: User) -> None:
    billing = get_billing_manager(db)
    if not billing.can_use_scheduled_scans(user.id):
        plan = billing.get_user_plan(user.id)
        raise PlanLimitError(
            {
                "error": "Scheduled scans not available",
                "message": "Scheduled scans are on the Team plan. "
                f"You're on the {plan['name']} plan.",
                "upgrade_required": True,
                "current_plan": plan["name"],
                "feature": "scheduled_scans",
            }
        )


def _validated_channels(channels: List[NotificationChannelModel]) -> List[Dict[str, Any]]:
    validated = []
    for channel in channels:
        data = channel.model_dump(mode="json", exclude_none=True)
        try:
            if channel.type == NotificationChannel.EMAIL:
                if not channel.email or "@" not in channel.email:
                    raise ValueError("Enter a valid email address.")
            else:
                validate_webhook_url(channel.webhook_url, channel.type.value)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        validated.append(data)
    return validated


def _owned_schedule(db: Session, user: User, schedule_id: int) -> ScheduledScan:
    schedule = get_scheduled_scan(db, user, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Scheduled scan not found")
    return schedule


@router.post("/create")
def create_schedule(
    schedule_data: CreateScheduleModel,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_scheduling(db, user)
    channels = _validated_channels(schedule_data.notification_channels)
    if is_demo_repo(schedule_data.repo):
        full_name = schedule_data.repo
    else:
        repo_info = github.get_repo(schedule_data.repo, require_github_token(user))
        full_name = repo_info.get("full_name", schedule_data.repo)
    schedule = create_scheduled_scan(
        db,
        user,
        full_name,
        schedule_data.frequency,
        channels,
        schedule_data.enabled,
    )
    return {"status": "Scheduled scan created", "schedule": serialize_schedule(schedule)}


@router.get("/list")
def list_schedules(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    schedules = [serialize_schedule(item) for item in get_user_scheduled_scans(db, user)]
    return {"total": len(schedules), "schedules": schedules}


@router.post("/test-notification")
def test_notification(
    channel: NotificationChannelModel,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_scheduling(db, user)
    channels = _validated_channels([channel])
    sample = {
        "count": 3,
        "security_score": {
            "score": 75,
            "grade": "B",
            "risk_level": "MEDIUM",
            "severity_breakdown": {"HIGH": 1, "MEDIUM": 2},
        },
    }
    return {"results": send_notifications(channels, sample, "test/repository")}


@router.get("/{schedule_id}")
def get_schedule(
    schedule_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return serialize_schedule(_owned_schedule(db, user, schedule_id))


@router.put("/{schedule_id}")
def update_schedule(
    schedule_id: int,
    update_data: UpdateScheduleModel,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    schedule = _owned_schedule(db, user, schedule_id)
    if update_data.enabled:
        _require_scheduling(db, user)

    if update_data.frequency is not None:
        schedule.frequency = update_data.frequency.value
        schedule.next_run = next_run_after(datetime.utcnow(), schedule.frequency)
    if update_data.notification_channels is not None:
        schedule.notification_channels = json.dumps(
            _validated_channels(update_data.notification_channels)
        )
    if update_data.enabled is not None:
        schedule.enabled = update_data.enabled
    db.commit()
    return {"status": "Schedule updated", "schedule": serialize_schedule(schedule)}


@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.delete(_owned_schedule(db, user, schedule_id))
    db.commit()
    return {"status": "Schedule deleted"}
