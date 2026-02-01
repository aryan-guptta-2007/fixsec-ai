from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from core.scheduler import (
    create_scheduled_scan, get_user_scheduled_scans, get_scheduled_scan,
    update_scheduled_scan, delete_scheduled_scan, ScanFrequency,
    NotificationChannel, mark_scan_completed, get_schedule_statistics
)
from core.notifications import send_notifications
import asyncio

router = APIRouter()

class NotificationChannelModel(BaseModel):
    type: NotificationChannel
    email: Optional[str] = None
    webhook_url: Optional[str] = None
    custom_payload: Optional[Dict[str, Any]] = None

class CreateScheduleModel(BaseModel):
    repo: str
    frequency: ScanFrequency
    notification_channels: List[NotificationChannelModel]
    enabled: bool = True

class UpdateScheduleModel(BaseModel):
    frequency: Optional[ScanFrequency] = None
    notification_channels: Optional[List[NotificationChannelModel]] = None
    enabled: Optional[bool] = None

@router.post("/create")
def create_schedule(
    schedule_data: CreateScheduleModel,
    authorization: str = Header(None)
):
    """Create a new scheduled scan"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = authorization.replace("Bearer ", "").strip()
    
    # Convert Pydantic models to dicts
    channels = [channel.dict(exclude_none=True) for channel in schedule_data.notification_channels]
    
    try:
        schedule = create_scheduled_scan(
            user_token=token,
            repo=schedule_data.repo,
            frequency=schedule_data.frequency,
            notification_channels=channels,
            enabled=schedule_data.enabled
        )
        
        return {
            "status": "Scheduled scan created ✅",
            "schedule": schedule
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")

@router.get("/list")
def list_schedules(authorization: str = Header(None)):
    """Get all scheduled scans for the authenticated user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = authorization.replace("Bearer ", "").strip()
    
    schedules = get_user_scheduled_scans(token)
    
    return {
        "total": len(schedules),
        "schedules": schedules
    }

@router.get("/{schedule_id}")
def get_schedule(
    schedule_id: str,
    authorization: str = Header(None)
):
    """Get a specific scheduled scan"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = authorization.replace("Bearer ", "").strip()
    
    schedule = get_scheduled_scan(schedule_id)
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Scheduled scan not found")
    
    # Verify ownership
    if schedule["user_token"] != token:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return schedule

@router.put("/{schedule_id}")
def update_schedule(
    schedule_id: str,
    update_data: UpdateScheduleModel,
    authorization: str = Header(None)
):
    """Update a scheduled scan"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = authorization.replace("Bearer ", "").strip()
    
    # Verify ownership
    schedule = get_scheduled_scan(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Scheduled scan not found")
    
    if schedule["user_token"] != token:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Convert notification channels if provided
        channels = None
        if update_data.notification_channels:
            channels = [channel.dict(exclude_none=True) for channel in update_data.notification_channels]
        
        updated_schedule = update_scheduled_scan(
            schedule_id=schedule_id,
            frequency=update_data.frequency,
            notification_channels=channels,
            enabled=update_data.enabled
        )
        
        return {
            "status": "Schedule updated ✅",
            "schedule": updated_schedule
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")

@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: str,
    authorization: str = Header(None)
):
    """Delete a scheduled scan"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = authorization.replace("Bearer ", "").strip()
    
    # Verify ownership
    schedule = get_scheduled_scan(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Scheduled scan not found")
    
    if schedule["user_token"] != token:
        raise HTTPException(status_code=403, detail="Access denied")
    
    success = delete_scheduled_scan(schedule_id)
    
    if success:
        return {"status": "Schedule deleted ✅"}
    else:
        raise HTTPException(status_code=404, detail="Scheduled scan not found")

@router.post("/test-notification")
async def test_notification(
    notification_data: Dict[str, Any],
    authorization: str = Header(None)
):
    """Test a notification channel"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    # Create a test scan result
    test_scan_result = {
        "count": 3,
        "security_score": {
            "score": 75,
            "grade": "B",
            "risk_level": "LOW",
            "severity_breakdown": {
                "HIGH": 1,
                "MEDIUM": 2
            }
        }
    }
    
    try:
        results = await send_notifications(
            notification_channels=[notification_data],
            scan_result=test_scan_result,
            repo="test/repository"
        )
        
        return {
            "status": "Test notification sent ✅",
            "results": results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test notification failed: {str(e)}")

@router.get("/stats/overview")
def get_scheduling_stats(authorization: str = Header(None)):
    """Get scheduling statistics"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    stats = get_schedule_statistics()
    
    return {
        "status": "Statistics retrieved ✅",
        "statistics": stats
    }