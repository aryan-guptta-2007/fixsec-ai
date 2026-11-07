from fastapi import APIRouter, Depends

from core import github
from core.scan_engine import require_github_token
from db.models import User
from routes.auth import get_current_user

router = APIRouter()


DEMO_REPOS = [
    {
        "id": 9001,
        "name": "vulnerable-node-service",
        "full_name": "demo-user/vulnerable-node-service",
        "private": False,
        "language": "JavaScript",
        "default_branch": "main",
        "updated_at": "2026-02-01T12:00:00Z",
        "html_url": "https://github.com/demo-user/vulnerable-node-service",
    },
    {
        "id": 9002,
        "name": "payment-api-python",
        "full_name": "demo-user/payment-api-python",
        "private": True,
        "language": "Python",
        "default_branch": "main",
        "updated_at": "2026-02-01T10:00:00Z",
        "html_url": "https://github.com/demo-user/payment-api-python",
    },
    {
        "id": 9003,
        "name": "secure-auth-gateway",
        "full_name": "demo-user/secure-auth-gateway",
        "private": False,
        "language": "TypeScript",
        "default_branch": "main",
        "updated_at": "2026-01-28T09:00:00Z",
        "html_url": "https://github.com/demo-user/secure-auth-gateway",
    },
]


@router.get("")
@router.get("/")
def list_repos(user: User = Depends(get_current_user)):
    if user.github_id == "demo-user-dev":
        return DEMO_REPOS
    try:
        token = require_github_token(user)
        return [
            {
                "id": repo["id"],
                "name": repo["name"],
                "full_name": repo["full_name"],
                "private": repo["private"],
                "language": repo.get("language"),
                "default_branch": repo.get("default_branch"),
                "updated_at": repo.get("updated_at"),
                "html_url": repo.get("html_url"),
            }
            for repo in github.list_repos(token)
        ]
    except Exception:
        if user.github_id == "demo-user-dev":
            return DEMO_REPOS
        raise
