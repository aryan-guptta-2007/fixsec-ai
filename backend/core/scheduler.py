"""
Scheduled scans: stored in the database and run by a background thread.

Several server workers can run this loop at once. A due schedule is claimed with
a conditional UPDATE, so only one worker gets each run.
"""
import json
import logging
import threading
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import update
from sqlalchemy.orm import Session

from config import settings
from core.billing import get_billing_manager
from core.notifications import send_notifications
from core.scan_engine import run_scan
from core.security import redact
from core.workspace import get_workspace_manager
from db.models import ScheduledScan, User
from db.session import SessionLocal

logger = logging.getLogger(__name__)


class ScanFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    DISCORD = "discord"
    SLACK = "slack"
    WEBHOOK = "webhook"


INTERVALS = {
    ScanFrequency.DAILY.value: timedelta(days=1),
    ScanFrequency.WEEKLY.value: timedelta(weeks=1),
    ScanFrequency.MONTHLY.value: timedelta(days=30),
}


def next_run_after(moment: datetime, frequency: str) -> datetime:
    return moment + INTERVALS[frequency]


def serialize_schedule(schedule: ScheduledScan) -> Dict[str, Any]:
    return {
        "id": schedule.id,
        "schedule_id": schedule.id,
        "repo": schedule.repo_name,
        "frequency": schedule.frequency,
        "notification_channels": json.loads(schedule.notification_channels or "[]"),
        "enabled": schedule.enabled,
        "status": "ACTIVE" if schedule.enabled else "PAUSED",
        "next_run": schedule.next_run.isoformat(),
        "last_run": schedule.last_run.isoformat() if schedule.last_run else None,
        "run_count": schedule.run_count or 0,
        "last_result": json.loads(schedule.last_result) if schedule.last_result else None,
        "created_at": schedule.created_at.isoformat(),
    }


def create_scheduled_scan(
    db: Session,
    user: User,
    repo: str,
    frequency: ScanFrequency,
    notification_channels: List[Dict[str, Any]],
    enabled: bool = True,
) -> ScheduledScan:
    schedule = ScheduledScan(
        user_id=user.id,
        repo_name=repo,
        frequency=frequency.value,
        notification_channels=json.dumps(notification_channels),
        enabled=enabled,
        next_run=next_run_after(datetime.utcnow(), frequency.value),
        run_count=0,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def get_user_scheduled_scans(db: Session, user: User) -> List[ScheduledScan]:
    return (
        db.query(ScheduledScan)
        .filter(ScheduledScan.user_id == user.id)
        .order_by(ScheduledScan.created_at.desc())
        .all()
    )


def get_scheduled_scan(db: Session, user: User, schedule_id: int) -> Optional[ScheduledScan]:
    return (
        db.query(ScheduledScan)
        .filter(ScheduledScan.id == schedule_id, ScheduledScan.user_id == user.id)
        .first()
    )


def claim_due_scans(db: Session, now: Optional[datetime] = None) -> List[int]:
    """Atomically move each due schedule to its next slot, returning those we won."""
    now = now or datetime.utcnow()
    due = (
        db.query(ScheduledScan.id, ScheduledScan.next_run, ScheduledScan.frequency)
        .filter(ScheduledScan.enabled.is_(True), ScheduledScan.next_run <= now)
        .all()
    )
    claimed = []
    for schedule_id, next_run, frequency in due:
        result = db.execute(
            update(ScheduledScan)
            .where(ScheduledScan.id == schedule_id, ScheduledScan.next_run == next_run)
            .values(next_run=next_run_after(now, frequency))
        )
        db.commit()
        if result.rowcount == 1:
            claimed.append(schedule_id)
    return claimed


def execute_schedule(db: Session, schedule_id: int) -> None:
    """Run one claimed schedule and notify its channels."""
    schedule = db.get(ScheduledScan, schedule_id)
    if schedule is None:
        return
    user = db.get(User, schedule.user_id)
    now = datetime.utcnow()

    if not get_billing_manager(db).can_use_scheduled_scans(user.id):
        schedule.enabled = False
        schedule.last_result = json.dumps(
            {
                "timestamp": now.isoformat(),
                "status": "PAUSED",
                "message": "Scheduled scans are not included in the current plan.",
            }
        )
        db.commit()
        return

    try:
        result = run_scan(db, user, schedule.repo_name, trigger="scheduled")
        outcome = {
            "timestamp": now.isoformat(),
            "status": "SUCCESS",
            "vulnerabilities_found": result["count"],
            "security_score": result["security_score"]["score"],
        }
        channels = json.loads(schedule.notification_channels or "[]")
        outcome["notifications"] = send_notifications(channels, result, schedule.repo_name)
    except Exception as exc:
        db.rollback()
        logger.warning("Scheduled scan %s failed: %s", schedule_id, redact(exc))
        outcome = {"timestamp": now.isoformat(), "status": "FAILED", "message": redact(exc)}

    schedule.last_run = now
    schedule.run_count = (schedule.run_count or 0) + 1
    schedule.last_result = json.dumps(outcome)
    db.commit()


def run_due_scans() -> int:
    """One scheduler tick. Returns how many schedules ran."""
    db = SessionLocal()
    try:
        claimed = claim_due_scans(db)
        for schedule_id in claimed:
            execute_schedule(db, schedule_id)
        return len(claimed)
    finally:
        db.close()


class SchedulerThread:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="fixsec-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self) -> None:
        while not self._stop.wait(settings.SCHEDULER_INTERVAL_SECONDS):
            try:
                run_due_scans()
                get_workspace_manager().cleanup_old_workspaces()
            except Exception:
                logger.exception("Scheduler tick failed")
