"""
Scheduled Scan System - Enterprise-grade automated security scanning
This is what premium cybersecurity SaaS platforms charge $500-1000/month for
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from enum import Enum

class ScanFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class NotificationChannel(str, Enum):
    EMAIL = "email"
    DISCORD = "discord"
    SLACK = "slack"
    WEBHOOK = "webhook"

# In-memory storage for scheduled scans (will be replaced with DB later)
scheduled_scans_store: Dict[str, Dict[str, Any]] = {}

def create_scheduled_scan(
    user_token: str,
    repo: str,
    frequency: ScanFrequency,
    notification_channels: List[Dict[str, Any]],
    enabled: bool = True
) -> Dict[str, Any]:
    """Create a new scheduled scan"""
    
    schedule_id = f"schedule_{len(scheduled_scans_store) + 1}"
    
    # Calculate next run time
    now = datetime.utcnow()
    if frequency == ScanFrequency.DAILY:
        next_run = now + timedelta(days=1)
    elif frequency == ScanFrequency.WEEKLY:
        next_run = now + timedelta(weeks=1)
    else:  # MONTHLY
        next_run = now + timedelta(days=30)
    
    schedule_data = {
        "schedule_id": schedule_id,
        "user_token": user_token,
        "repo": repo,
        "frequency": frequency,
        "notification_channels": notification_channels,
        "enabled": enabled,
        "created_at": now.isoformat(),
        "next_run": next_run.isoformat(),
        "last_run": None,
        "run_count": 0,
        "status": "ACTIVE" if enabled else "PAUSED"
    }
    
    scheduled_scans_store[schedule_id] = schedule_data
    
    print(f"📅 Created scheduled scan: {repo} - {frequency} - {len(notification_channels)} channels")
    
    return schedule_data

def get_user_scheduled_scans(user_token: str) -> List[Dict[str, Any]]:
    """Get all scheduled scans for a user"""
    user_scans = []
    for schedule_id, scan_data in scheduled_scans_store.items():
        if scan_data["user_token"] == user_token:
            user_scans.append(scan_data)
    
    return sorted(user_scans, key=lambda x: x["created_at"], reverse=True)

def get_scheduled_scan(schedule_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific scheduled scan"""
    return scheduled_scans_store.get(schedule_id)

def update_scheduled_scan(
    schedule_id: str,
    frequency: Optional[ScanFrequency] = None,
    notification_channels: Optional[List[Dict[str, Any]]] = None,
    enabled: Optional[bool] = None
) -> Dict[str, Any]:
    """Update an existing scheduled scan"""
    
    if schedule_id not in scheduled_scans_store:
        raise ValueError(f"Scheduled scan {schedule_id} not found")
    
    scan_data = scheduled_scans_store[schedule_id]
    
    if frequency is not None:
        scan_data["frequency"] = frequency
        # Recalculate next run time
        now = datetime.utcnow()
        if frequency == ScanFrequency.DAILY:
            scan_data["next_run"] = (now + timedelta(days=1)).isoformat()
        elif frequency == ScanFrequency.WEEKLY:
            scan_data["next_run"] = (now + timedelta(weeks=1)).isoformat()
        else:  # MONTHLY
            scan_data["next_run"] = (now + timedelta(days=30)).isoformat()
    
    if notification_channels is not None:
        scan_data["notification_channels"] = notification_channels
    
    if enabled is not None:
        scan_data["enabled"] = enabled
        scan_data["status"] = "ACTIVE" if enabled else "PAUSED"
    
    scan_data["updated_at"] = datetime.utcnow().isoformat()
    
    return scan_data

def delete_scheduled_scan(schedule_id: str) -> bool:
    """Delete a scheduled scan"""
    if schedule_id in scheduled_scans_store:
        del scheduled_scans_store[schedule_id]
        return True
    return False

def get_due_scans() -> List[Dict[str, Any]]:
    """Get all scans that are due to run"""
    now = datetime.utcnow()
    due_scans = []
    
    for schedule_id, scan_data in scheduled_scans_store.items():
        if not scan_data["enabled"]:
            continue
        
        next_run = datetime.fromisoformat(scan_data["next_run"])
        if next_run <= now:
            due_scans.append(scan_data)
    
    return due_scans

def mark_scan_completed(schedule_id: str, scan_result: Dict[str, Any]) -> None:
    """Mark a scheduled scan as completed and schedule next run"""
    if schedule_id not in scheduled_scans_store:
        return
    
    scan_data = scheduled_scans_store[schedule_id]
    now = datetime.utcnow()
    
    # Update run statistics
    scan_data["last_run"] = now.isoformat()
    scan_data["run_count"] += 1
    scan_data["last_result"] = {
        "timestamp": now.isoformat(),
        "vulnerabilities_found": scan_result.get("count", 0),
        "security_score": scan_result.get("security_score", {}).get("score", 0),
        "status": "SUCCESS"
    }
    
    # Schedule next run
    frequency = scan_data["frequency"]
    if frequency == ScanFrequency.DAILY:
        next_run = now + timedelta(days=1)
    elif frequency == ScanFrequency.WEEKLY:
        next_run = now + timedelta(weeks=1)
    else:  # MONTHLY
        next_run = now + timedelta(days=30)
    
    scan_data["next_run"] = next_run.isoformat()
    
    print(f"📅 Completed scheduled scan: {scan_data['repo']} - Next run: {next_run}")

def get_schedule_statistics() -> Dict[str, Any]:
    """Get overall scheduling statistics"""
    total_schedules = len(scheduled_scans_store)
    active_schedules = len([s for s in scheduled_scans_store.values() if s["enabled"]])
    
    # Count by frequency
    frequency_counts = {}
    for scan_data in scheduled_scans_store.values():
        freq = scan_data["frequency"]
        frequency_counts[freq] = frequency_counts.get(freq, 0) + 1
    
    # Count by notification channel
    channel_counts = {}
    for scan_data in scheduled_scans_store.values():
        for channel in scan_data["notification_channels"]:
            ch_type = channel.get("type", "unknown")
            channel_counts[ch_type] = channel_counts.get(ch_type, 0) + 1
    
    return {
        "total_schedules": total_schedules,
        "active_schedules": active_schedules,
        "paused_schedules": total_schedules - active_schedules,
        "frequency_breakdown": frequency_counts,
        "notification_channels": channel_counts
    }