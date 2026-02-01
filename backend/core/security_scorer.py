"""
Security Score Calculator - Calculates repository security ratings
This is what premium cybersecurity SaaS platforms charge $200-500/month for
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta

# Severity point values (industry standard)
SEVERITY_POINTS = {
    "CRITICAL": 10,
    "HIGH": 7,
    "MEDIUM": 4,
    "LOW": 1,
    "UNKNOWN": 2
}

# Maximum points before score becomes 0 (tunable)
MAX_PENALTY_POINTS = 50

def calculate_vulnerability_score(vulnerabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate security score based on vulnerabilities"""
    
    if not vulnerabilities:
        return {
            "score": 100,
            "grade": "A+",
            "total_points": 0,
            "severity_breakdown": {},
            "risk_level": "MINIMAL"
        }
    
    # Count vulnerabilities by severity
    severity_counts = {}
    total_penalty_points = 0
    
    for vuln in vulnerabilities:
        severity = vuln.get("severity", "UNKNOWN").upper()
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        total_penalty_points += SEVERITY_POINTS.get(severity, 2)
    
    # Calculate score (100 - penalty points, minimum 0)
    raw_score = max(0, 100 - total_penalty_points)
    
    # Apply curve for better distribution
    if raw_score >= 90:
        final_score = raw_score
    elif raw_score >= 70:
        final_score = raw_score - 5  # Slight penalty
    elif raw_score >= 50:
        final_score = raw_score - 10  # Moderate penalty
    else:
        final_score = max(0, raw_score - 15)  # Heavy penalty
    
    return {
        "score": int(final_score),
        "grade": get_security_grade(final_score),
        "total_points": total_penalty_points,
        "severity_breakdown": severity_counts,
        "risk_level": get_risk_level(final_score),
        "total_vulnerabilities": len(vulnerabilities)
    }

def get_security_grade(score: float) -> str:
    """Convert numeric score to letter grade"""
    if score >= 95:
        return "A+"
    elif score >= 90:
        return "A"
    elif score >= 85:
        return "A-"
    elif score >= 80:
        return "B+"
    elif score >= 75:
        return "B"
    elif score >= 70:
        return "B-"
    elif score >= 65:
        return "C+"
    elif score >= 60:
        return "C"
    elif score >= 55:
        return "C-"
    elif score >= 50:
        return "D+"
    elif score >= 45:
        return "D"
    elif score >= 40:
        return "D-"
    else:
        return "F"

def get_risk_level(score: float) -> str:
    """Convert score to risk level"""
    if score >= 90:
        return "MINIMAL"
    elif score >= 75:
        return "LOW"
    elif score >= 60:
        return "MODERATE"
    elif score >= 40:
        return "HIGH"
    else:
        return "CRITICAL"

def get_score_color(score: int) -> str:
    """Get color class for score display"""
    if score >= 90:
        return "text-green-600"
    elif score >= 75:
        return "text-blue-600"
    elif score >= 60:
        return "text-yellow-600"
    elif score >= 40:
        return "text-orange-600"
    else:
        return "text-red-600"

def get_grade_color(grade: str) -> str:
    """Get color class for grade display"""
    if grade.startswith("A"):
        return "bg-green-100 text-green-800"
    elif grade.startswith("B"):
        return "bg-blue-100 text-blue-800"
    elif grade.startswith("C"):
        return "bg-yellow-100 text-yellow-800"
    elif grade.startswith("D"):
        return "bg-orange-100 text-orange-800"
    else:
        return "bg-red-100 text-red-800"

def calculate_trend_analysis(scan_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze security score trends over time"""
    if len(scan_history) < 2:
        return {
            "trend": "INSUFFICIENT_DATA",
            "change": 0,
            "message": "Need more scans for trend analysis"
        }
    
    # Calculate scores for recent scans
    recent_scores = []
    for scan in scan_history[-5:]:  # Last 5 scans
        vulnerabilities = scan.get("vulnerabilities", [])
        score_data = calculate_vulnerability_score(vulnerabilities)
        recent_scores.append({
            "timestamp": scan.get("timestamp"),
            "score": score_data["score"]
        })
    
    if len(recent_scores) < 2:
        return {
            "trend": "INSUFFICIENT_DATA",
            "change": 0,
            "message": "Need more scans for trend analysis"
        }
    
    # Calculate trend
    first_score = recent_scores[0]["score"]
    last_score = recent_scores[-1]["score"]
    change = last_score - first_score
    
    if change > 5:
        trend = "IMPROVING"
        message = f"Security improved by {change} points"
    elif change < -5:
        trend = "DECLINING"
        message = f"Security declined by {abs(change)} points"
    else:
        trend = "STABLE"
        message = "Security score is stable"
    
    return {
        "trend": trend,
        "change": change,
        "message": message,
        "scores": recent_scores
    }

def generate_security_recommendations(score_data: Dict[str, Any]) -> List[str]:
    """Generate actionable security recommendations"""
    recommendations = []
    
    severity_breakdown = score_data.get("severity_breakdown", {})
    score = score_data.get("score", 100)
    
    # Critical vulnerabilities
    if severity_breakdown.get("CRITICAL", 0) > 0:
        recommendations.append("🚨 Address CRITICAL vulnerabilities immediately - these pose severe security risks")
    
    # High vulnerabilities
    if severity_breakdown.get("HIGH", 0) > 0:
        recommendations.append("⚠️ Fix HIGH severity issues within 24-48 hours")
    
    # Medium vulnerabilities
    if severity_breakdown.get("MEDIUM", 0) > 0:
        recommendations.append("📋 Schedule MEDIUM severity fixes for next sprint")
    
    # Score-based recommendations
    if score < 40:
        recommendations.append("🔥 Security score is critically low - immediate action required")
        recommendations.append("🛡️ Consider security audit and penetration testing")
    elif score < 60:
        recommendations.append("📈 Implement regular security scanning schedule")
        recommendations.append("🔍 Review code for security best practices")
    elif score < 80:
        recommendations.append("✅ Good security posture - maintain with regular scans")
    else:
        recommendations.append("🏆 Excellent security score - keep up the great work!")
    
    # General recommendations
    if score < 90:
        recommendations.append("🔄 Enable automated dependency updates")
        recommendations.append("📚 Train team on secure coding practices")
    
    return recommendations