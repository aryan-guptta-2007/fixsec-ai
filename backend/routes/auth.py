import logging
import secrets
from typing import Optional
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import settings
from core import github
from core.billing import get_billing_manager
from core.security import create_session_token, decode_session_token, encrypt_token
from db.models import User
from db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

STATE_COOKIE = "fixsec_oauth_state"
OAUTH_SCOPES = "repo user:email"


def _login_error(code: str) -> RedirectResponse:
    response = RedirectResponse(f"{settings.FRONTEND_URL}/login?error={code}")
    response.delete_cookie(STATE_COOKIE)
    return response


@router.get("/config")
def auth_config():
    return {
        "github_oauth_configured": bool(settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET),
        "demo_mode": not settings.is_production,
    }


@router.get("/demo/login")
def demo_login(db: Session = Depends(get_db)):
    if settings.is_production:
        raise HTTPException(status_code=403, detail="Demo login is disabled in production")

    demo_user = db.query(User).filter(User.github_id == "demo-user-dev").first()
    if demo_user is None:
        demo_user = User(
            name="Demo Developer",
            email="demo@fixsec.ai",
            github_id="demo-user-dev",
            github_token=encrypt_token("demo-token-fixsec"),
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)
        get_billing_manager(db).set_user_plan(demo_user.id, "pro")

    session = create_session_token(demo_user.id)
    return RedirectResponse(f"{settings.FRONTEND_URL}/dashboard#token={session}")


@router.get("/github/login")
def github_login():
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")

    state = secrets.token_urlsafe(32)
    query = urlencode(
        {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": settings.github_redirect_uri,
            "scope": OAUTH_SCOPES,
            "state": state,
        }
    )
    response = RedirectResponse(f"{settings.GITHUB_WEB_URL}/login/oauth/authorize?{query}")
    response.set_cookie(
        STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
    )
    return response


def _exchange_code(code: str) -> Optional[str]:
    try:
        response = requests.post(
            f"{settings.GITHUB_WEB_URL}/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
            },
            timeout=github.TIMEOUT,
        )
        return response.json().get("access_token")
    except (requests.RequestException, ValueError) as exc:
        logger.warning("GitHub token exchange failed: %s", type(exc).__name__)
        return None


def _upsert_user(db: Session, access_token: str) -> User:
    profile = github.get_user(access_token)
    github_id = str(profile["id"])
    email = profile.get("email") or github.get_primary_email(access_token)
    name = profile.get("name") or profile.get("login") or "GitHub user"

    user = db.query(User).filter(User.github_id == github_id).first()
    if user is None:
        user = User(github_id=github_id)
        db.add(user)
    user.name = name
    user.email = email
    user.github_token = encrypt_token(access_token)
    try:
        db.commit()
    except IntegrityError:
        # The address already belongs to another account. Sign-in must still work.
        db.rollback()
        user = db.query(User).filter(User.github_id == github_id).first() or User(
            github_id=github_id
        )
        db.add(user)
        user.name = name
        user.email = None
        user.github_token = encrypt_token(access_token)
        db.commit()
    db.refresh(user)
    return user


@router.get("/github/callback")
def github_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    oauth_state: Optional[str] = Cookie(None, alias=STATE_COOKIE),
    db: Session = Depends(get_db),
):
    if error:
        return _login_error("access_denied")
    if not state or not oauth_state or not secrets.compare_digest(state, oauth_state):
        return _login_error("invalid_state")
    if not code:
        return _login_error("missing_code")

    access_token = _exchange_code(code)
    if not access_token:
        return _login_error("token_exchange_failed")

    try:
        user = _upsert_user(db, access_token)
    except github.GitHubError as exc:
        logger.warning("Could not load GitHub profile: %s", exc.message)
        return _login_error("github_unavailable")

    # The session token travels in the URL fragment, which is never sent to a
    # server, so it stays out of access logs and Referer headers.
    session = create_session_token(user.id)
    response = RedirectResponse(f"{settings.FRONTEND_URL}/dashboard#token={session}")
    response.delete_cookie(STATE_COOKIE)
    return response


def get_current_user(
    authorization: Optional[str] = Header(None), db: Session = Depends(get_db)
) -> User:
    """Resolve the Authorization: Bearer <session token> header to a user."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = decode_session_token(token.strip())
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    return user


@router.get("/me")
def read_current_user(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = get_billing_manager(db).get_user_plan(user.id)
    return {"id": user.id, "name": user.name, "email": user.email, "plan": plan["name"]}
