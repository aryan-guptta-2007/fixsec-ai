"""
Session tokens, encryption of stored GitHub tokens, and log/error redaction.
"""
import base64
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional

import jwt
from cryptography.fernet import Fernet, InvalidToken

from config import settings

ALGORITHM = "HS256"

_URL_CREDENTIALS = re.compile(r"(https?://)[^/\s@]+@")
_GITHUB_TOKENS = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")
_AUTH_HEADERS = re.compile(r"(?i)(authorization:\s*\w+\s+)\S+")


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()


def decrypt_token(ciphertext: Optional[str]) -> Optional[str]:
    """Return the stored GitHub token, or None if it cannot be read."""
    if not ciphertext:
        return None
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def create_session_token(user_id: int) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(hours=settings.SESSION_TTL_HOURS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_session_token(token: str) -> Optional[int]:
    """Return the user id in a valid session token, otherwise None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        return None


def redact(text: object) -> str:
    """Strip credentials from text that may reach logs or API responses."""
    cleaned = _URL_CREDENTIALS.sub(r"\1***@", str(text))
    cleaned = _AUTH_HEADERS.sub(r"\1***", cleaned)
    return _GITHUB_TOKENS.sub("***", cleaned)
