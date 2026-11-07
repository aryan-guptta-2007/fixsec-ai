"""
Security score trend analysis over stored scans.
"""
from typing import Any, Dict, List


def calculate_trend_analysis(scan_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare the last few scored scans. `scan_history` is ordered oldest to newest."""
    recent = [
        {"timestamp": scan.get("timestamp"), "score": scan["score"]}
        for scan in scan_history[-5:]
        if scan.get("score") is not None
    ]
    if len(recent) < 2:
        return {
            "trend": "INSUFFICIENT_DATA",
            "change": 0,
            "message": "Need more scans for trend analysis",
        }

    change = round(recent[-1]["score"] - recent[0]["score"], 1)
    if change > 5:
        trend, message = "IMPROVING", f"Security improved by {change} points"
    elif change < -5:
        trend, message = "DECLINING", f"Security declined by {abs(change)} points"
    else:
        trend, message = "STABLE", "Security score is stable"

    return {"trend": trend, "change": change, "message": message, "scores": recent}
