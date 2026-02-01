"""
Multi-Channel Notification System
Supports Email, Discord, Slack, and Webhook notifications
"""
import requests
import json
from typing import Dict, Any, List
from datetime import datetime

def format_scan_notification(
    repo: str,
    scan_result: Dict[str, Any],
    notification_type: str = "scheduled"
) -> Dict[str, str]:
    """Format scan results for notifications"""
    
    count = scan_result.get("count", 0)
    security_score = scan_result.get("security_score", {})
    score = security_score.get("score", 0)
    grade = security_score.get("grade", "N/A")
    risk_level = security_score.get("risk_level", "UNKNOWN")
    
    # Create different message formats
    if notification_type == "scheduled":
        title = f"🔍 Scheduled Security Scan Complete: {repo}"
    else:
        title = f"🚨 Security Scan Alert: {repo}"
    
    # Determine emoji and color based on results
    if count == 0:
        emoji = "✅"
        color = "good"  # Green for Slack
        status = "SECURE"
    elif count <= 2:
        emoji = "⚠️"
        color = "warning"  # Yellow for Slack
        status = "MINOR ISSUES"
    else:
        emoji = "🚨"
        color = "danger"  # Red for Slack
        status = "ATTENTION REQUIRED"
    
    summary = f"{emoji} {status}\n"
    summary += f"Security Score: {score}/100 (Grade {grade})\n"
    summary += f"Risk Level: {risk_level}\n"
    summary += f"Vulnerabilities Found: {count}\n"
    summary += f"Scan Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    
    # Detailed breakdown
    details = ""
    if security_score.get("severity_breakdown"):
        details += "\n📊 Vulnerability Breakdown:\n"
        for severity, count_sev in security_score["severity_breakdown"].items():
            details += f"• {severity}: {count_sev}\n"
    
    return {
        "title": title,
        "summary": summary,
        "details": details,
        "color": color,
        "repo": repo,
        "score": str(score),
        "grade": grade,
        "count": str(count)
    }

async def send_email_notification(
    email: str,
    message_data: Dict[str, str]
) -> Dict[str, Any]:
    """Send email notification (placeholder - integrate with SendGrid/AWS SES)"""
    
    # This is a placeholder - in production, integrate with:
    # - SendGrid API
    # - AWS SES
    # - Mailgun
    # - etc.
    
    print(f"📧 EMAIL NOTIFICATION to {email}:")
    print(f"Subject: {message_data['title']}")
    print(f"Body: {message_data['summary']}{message_data['details']}")
    
    return {
        "status": "success",
        "channel": "email",
        "recipient": email,
        "message": "Email notification sent (simulated)"
    }

async def send_discord_notification(
    webhook_url: str,
    message_data: Dict[str, str]
) -> Dict[str, Any]:
    """Send Discord webhook notification"""
    
    try:
        # Discord webhook payload
        payload = {
            "embeds": [{
                "title": message_data["title"],
                "description": message_data["summary"],
                "color": 0x00ff00 if message_data["color"] == "good" else 
                        0xffff00 if message_data["color"] == "warning" else 0xff0000,
                "fields": [
                    {
                        "name": "Repository",
                        "value": message_data["repo"],
                        "inline": True
                    },
                    {
                        "name": "Security Score",
                        "value": f"{message_data['score']}/100 ({message_data['grade']})",
                        "inline": True
                    },
                    {
                        "name": "Issues Found",
                        "value": message_data["count"],
                        "inline": True
                    }
                ],
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": "FixSec AI Security Scanner"
                }
            }]
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code == 204:
            return {
                "status": "success",
                "channel": "discord",
                "message": "Discord notification sent successfully"
            }
        else:
            return {
                "status": "error",
                "channel": "discord",
                "message": f"Discord webhook failed: {response.status_code}"
            }
    
    except Exception as e:
        return {
            "status": "error",
            "channel": "discord",
            "message": f"Discord notification failed: {str(e)}"
        }

async def send_slack_notification(
    webhook_url: str,
    message_data: Dict[str, str]
) -> Dict[str, Any]:
    """Send Slack webhook notification"""
    
    try:
        # Slack webhook payload
        payload = {
            "text": message_data["title"],
            "attachments": [{
                "color": message_data["color"],
                "fields": [
                    {
                        "title": "Repository",
                        "value": message_data["repo"],
                        "short": True
                    },
                    {
                        "title": "Security Score",
                        "value": f"{message_data['score']}/100 ({message_data['grade']})",
                        "short": True
                    },
                    {
                        "title": "Vulnerabilities",
                        "value": message_data["count"],
                        "short": True
                    },
                    {
                        "title": "Summary",
                        "value": message_data["summary"],
                        "short": False
                    }
                ],
                "footer": "FixSec AI",
                "ts": int(datetime.utcnow().timestamp())
            }]
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return {
                "status": "success",
                "channel": "slack",
                "message": "Slack notification sent successfully"
            }
        else:
            return {
                "status": "error",
                "channel": "slack",
                "message": f"Slack webhook failed: {response.status_code}"
            }
    
    except Exception as e:
        return {
            "status": "error",
            "channel": "slack",
            "message": f"Slack notification failed: {str(e)}"
        }

async def send_webhook_notification(
    webhook_url: str,
    message_data: Dict[str, str],
    custom_payload: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Send custom webhook notification"""
    
    try:
        # Use custom payload if provided, otherwise use standard format
        if custom_payload:
            payload = custom_payload
        else:
            payload = {
                "event": "security_scan_completed",
                "repository": message_data["repo"],
                "security_score": int(message_data["score"]),
                "grade": message_data["grade"],
                "vulnerabilities_count": int(message_data["count"]),
                "timestamp": datetime.utcnow().isoformat(),
                "summary": message_data["summary"]
            }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if 200 <= response.status_code < 300:
            return {
                "status": "success",
                "channel": "webhook",
                "message": f"Webhook notification sent successfully ({response.status_code})"
            }
        else:
            return {
                "status": "error",
                "channel": "webhook",
                "message": f"Webhook failed: {response.status_code}"
            }
    
    except Exception as e:
        return {
            "status": "error",
            "channel": "webhook",
            "message": f"Webhook notification failed: {str(e)}"
        }

async def send_notifications(
    notification_channels: List[Dict[str, Any]],
    scan_result: Dict[str, Any],
    repo: str
) -> List[Dict[str, Any]]:
    """Send notifications to all configured channels"""
    
    message_data = format_scan_notification(repo, scan_result)
    results = []
    
    for channel in notification_channels:
        channel_type = channel.get("type")
        
        try:
            if channel_type == "email":
                result = await send_email_notification(
                    channel.get("email"),
                    message_data
                )
            elif channel_type == "discord":
                result = await send_discord_notification(
                    channel.get("webhook_url"),
                    message_data
                )
            elif channel_type == "slack":
                result = await send_slack_notification(
                    channel.get("webhook_url"),
                    message_data
                )
            elif channel_type == "webhook":
                result = await send_webhook_notification(
                    channel.get("webhook_url"),
                    message_data,
                    channel.get("custom_payload")
                )
            else:
                result = {
                    "status": "error",
                    "channel": channel_type,
                    "message": f"Unknown notification channel: {channel_type}"
                }
            
            results.append(result)
            
        except Exception as e:
            results.append({
                "status": "error",
                "channel": channel_type,
                "message": f"Notification failed: {str(e)}"
            })
    
    return results