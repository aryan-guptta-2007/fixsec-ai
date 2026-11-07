"""
Stored scan queries. Every function is scoped to one user: nobody can read
findings for a repository they did not scan themselves.
"""
import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.security_scorer import calculate_trend_analysis
from db.models import Repository, Scan, User


def _record(scan: Scan, repo_name: str) -> Dict[str, Any]:
    return {
        "scan_id": scan.id,
        "timestamp": scan.started_at.isoformat(),
        "repo": repo_name,
        "count": scan.issues_found or 0,
        "status": scan.status,
        "branch_scanned": scan.branch,
        "score": scan.security_score,
        "grade": scan.grade,
        "trigger": scan.trigger,
    }


def get_scan_result(db: Session, user: User, scan_id: int) -> Optional[Dict[str, Any]]:
    scan = (
        db.query(Scan)
        .join(Repository)
        .filter(Scan.id == scan_id, Repository.user_id == user.id, Scan.status == "completed")
        .first()
    )
    return json.loads(scan.result_json) if scan and scan.result_json else None


def get_scan_history(db: Session, user: User, repo: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Scans for one repository, oldest first."""
    scans = (
        db.query(Scan)
        .join(Repository)
        .filter(Repository.user_id == user.id, Repository.repo_name == repo)
        .order_by(Scan.started_at.desc(), Scan.id.desc())
        .limit(limit)
        .all()
    )
    return [_record(scan, repo) for scan in reversed(scans)]


def get_latest_scan_id(db: Session, user: User, repo: str) -> Optional[int]:
    scan = (
        db.query(Scan)
        .join(Repository)
        .filter(
            Repository.user_id == user.id,
            Repository.repo_name == repo,
            Scan.status == "completed",
        )
        .order_by(Scan.started_at.desc(), Scan.id.desc())
        .first()
    )
    return scan.id if scan else None


def get_security_score(db: Session, user: User, repo: str) -> Optional[Dict[str, Any]]:
    history = [scan for scan in get_scan_history(db, user, repo) if scan["status"] == "completed"]
    if not history:
        return None
    latest = history[-1]
    result = get_scan_result(db, user, latest["scan_id"]) or {}
    return {
        "repo": repo,
        "current_score": result.get("security_score"),
        "trend_analysis": calculate_trend_analysis(history),
        "last_scan": latest["timestamp"],
        "total_scans": len(history),
    }


def get_overview(db: Session, user: User) -> List[Dict[str, Any]]:
    """Every scanned repository with recent history and its current score."""
    repositories = (
        db.query(Repository)
        .filter(Repository.user_id == user.id)
        .order_by(Repository.repo_name)
        .all()
    )
    overview = []
    for repository in repositories:
        history = get_scan_history(db, user, repository.repo_name, limit=10)
        if history:
            overview.append(
                {
                    "repo": repository.repo_name,
                    "history": history,
                    "score": get_security_score(db, user, repository.repo_name),
                }
            )
    return overview
