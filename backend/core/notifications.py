"""
Notifications for Email (SendGrid), Discord, Slack and custom webhooks.

Webhook URLs are supplied by users and requested by this server, so they are
validated to stop them being pointed at internal services.
"""
import ipaddress
import logging
import socket
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from config import settings

logger = logging.getLogger(__name__)

TIMEOUT = 10
PROVIDER_HOSTS = {
    "slack": {"hooks.slack.com"},
    "discord": {"discord.com", "discordapp.com"},
}


def validate_webhook_url(url: Optional[str], channel_type: str = "webhook") -> None:
    """Raise ValueError unless the URL is an https endpoint on the public internet."""
    parsed = urlparse(url or "")
    host = parsed.hostname
    if parsed.scheme != "https" or not host:
        raise ValueError("Webhook URL must be a valid https:// address.")

    allowed_hosts = PROVIDER_HOSTS.get(channel_type)
    if allowed_hosts and host.lower() not in allowed_hosts:
        raise ValueError(f"A {channel_type} webhook must point to {sorted(allowed_hosts)[0]}.")

    try:
        addresses = socket.getaddrinfo(host, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError) as exc:
        raise ValueError("Webhook host could not be resolved.") from exc
    for address in addresses:
        if not ipaddress.ip_address(address[4][0].split("%")[0]).is_global:
            raise ValueError("Webhook URL must not point to a private network address.")


def format_scan_notification(repo: str, scan_result: Dict[str, Any]) -> Dict[str, str]:
    """Format scan results for notifications."""
    count = scan_result.get("count", 0)
    security_score = scan_result.get("security_score", {})
    score = security_score.get("score", 0)
    grade = security_score.get("grade", "N/A")
    risk_level = security_score.get("risk_level", "UNKNOWN")

    if count == 0:
        emoji, color, status = "✅", "good", "SECURE"
    elif count <= 2:
        emoji, color, status = "⚠️", "warning", "MINOR ISSUES"
    else:
        emoji, color, status = "🚨", "danger", "ATTENTION REQUIRED"

    summary = (
        f"{emoji} {status}\n"
        f"Security Score: {score}/100 (Grade {grade})\n"
        f"Risk Level: {risk_level}\n"
        f"Vulnerabilities Found: {count}\n"
        f"Scan Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )

    details = ""
    if security_score.get("severity_breakdown"):
        details = "\n\nVulnerability Breakdown:\n" + "".join(
            f"- {severity}: {total}\n"
            for severity, total in security_score["severity_breakdown"].items()
        )

    return {
        "title": f"Security Scan Complete: {repo}",
        "summary": summary,
        "details": details,
        "color": color,
        "repo": repo,
        "score": str(score),
        "grade": grade,
        "count": str(count),
    }


def _result(channel: str, success: bool, message: str) -> Dict[str, Any]:
    return {"status": "success" if success else "error", "channel": channel, "message": message}


def send_email_notification(email: Optional[str], message: Dict[str, str]) -> Dict[str, Any]:
    if not settings.SENDGRID_API_KEY:
        return _result("email", False, "Email is not configured on this server (SENDGRID_API_KEY).")
    if not email:
        return _result("email", False, "No email address configured.")

    response = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}"},
        json={
            "personalizations": [{"to": [{"email": email}]}],
            "from": {"email": settings.FROM_EMAIL, "name": "FixSec AI"},
            "subject": message["title"],
            "content": [
                {"type": "text/plain", "value": f"{message['summary']}{message['details']}"}
            ],
        },
        timeout=TIMEOUT,
    )
    if response.status_code in (200, 202):
        return _result("email", True, f"Email sent to {email}")
    return _result("email", False, f"SendGrid returned {response.status_code}")


def _post_webhook(channel: str, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    validate_webhook_url(url, channel)
    response = requests.post(url, json=payload, timeout=TIMEOUT, allow_redirects=False)
    if 200 <= response.status_code < 300:
        return _result(channel, True, f"{channel.capitalize()} notification sent")
    return _result(channel, False, f"{channel.capitalize()} webhook returned {response.status_code}")


def send_discord_notification(url: str, message: Dict[str, str]) -> Dict[str, Any]:
    color = {"good": 0x00FF00, "warning": 0xFFFF00}.get(message["color"], 0xFF0000)
    return _post_webhook(
        "discord",
        url,
        {
            "embeds": [
                {
                    "title": message["title"],
                    "description": message["summary"],
                    "color": color,
                    "footer": {"text": "FixSec AI"},
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ]
        },
    )


def send_slack_notification(url: str, message: Dict[str, str]) -> Dict[str, Any]:
    return _post_webhook(
        "slack",
        url,
        {
            "text": message["title"],
            "attachments": [
                {
                    "color": message["color"],
                    "text": f"{message['summary']}{message['details']}",
                    "footer": "FixSec AI",
                }
            ],
        },
    )


def send_webhook_notification(
    url: str, message: Dict[str, str], custom_payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    payload = custom_payload or {
        "event": "security_scan_completed",
        "repository": message["repo"],
        "security_score": float(message["score"]),
        "grade": message["grade"],
        "vulnerabilities_count": int(message["count"]),
        "timestamp": datetime.utcnow().isoformat(),
        "summary": message["summary"],
    }
    return _post_webhook("webhook", url, payload)


def send_notifications(
    notification_channels: List[Dict[str, Any]], scan_result: Dict[str, Any], repo: str
) -> List[Dict[str, Any]]:
    """Send to every channel. One failing channel does not affect the others."""
    message = format_scan_notification(repo, scan_result)
    results = []
    for channel in notification_channels:
        channel_type = channel.get("type")
        try:
            if channel_type == "email":
                results.append(send_email_notification(channel.get("email"), message))
            elif channel_type == "discord":
                results.append(send_discord_notification(channel.get("webhook_url"), message))
            elif channel_type == "slack":
                results.append(send_slack_notification(channel.get("webhook_url"), message))
            elif channel_type == "webhook":
                results.append(
                    send_webhook_notification(
                        channel.get("webhook_url"), message, channel.get("custom_payload")
                    )
                )
            else:
                results.append(_result(str(channel_type), False, "Unknown notification channel"))
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Notification via %s failed: %s", channel_type, type(exc).__name__)
            results.append(_result(str(channel_type), False, "Notification could not be delivered"))
    return results
