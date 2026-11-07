from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from core.github import is_valid_full_name
from core.scan_engine import enforce_scan_limits, run_scan
from core.scan_history import get_scan_result
from db.models import User
from db.session import get_db
from routes.auth import get_current_user

router = APIRouter()


@router.post("")
@router.post("/")
def scan_repo(
    payload: dict = Body(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    full_name = payload.get("full_name") or payload.get("repo")
    if not is_valid_full_name(full_name):
        raise HTTPException(status_code=400, detail="Expected a repository as owner/repo")

    enforce_scan_limits(db, user, full_name)
    return run_scan(db, user, full_name)


@router.get("/{scan_id}")
def read_scan(
    scan_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = get_scan_result(db, user, scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return result
