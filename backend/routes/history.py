from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.scan_history import get_overview, get_scan_history, get_security_score
from db.models import User
from db.session import get_db
from routes.auth import get_current_user

router = APIRouter()


@router.get("/overview")
def scan_overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every repository the user has scanned, with recent history and current score."""
    repos = get_overview(db, user)
    return {"total_repos": len(repos), "repos": repos}


@router.get("/scan-history")
def repo_scan_history(
    repo: str = Query(..., description="Repository name (owner/repo)"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    history = get_scan_history(db, user, repo)
    return {"repo": repo, "total_scans": len(history), "history": history}


@router.get("/security-score")
def repo_security_score(
    repo: str = Query(..., description="Repository name (owner/repo)"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    score = get_security_score(db, user, repo)
    if score is None:
        raise HTTPException(status_code=404, detail="No completed scans for this repository")
    return score
