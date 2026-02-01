from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import os
import requests
from db.session import get_db
from db.models import User

router = APIRouter()

@router.get("/github/login")
def github_login():
    print("✅ GITHUB_CLIENT_ID =", os.getenv("GITHUB_CLIENT_ID"))
    
    client_id = os.getenv("GITHUB_CLIENT_ID")
    redirect_uri = os.getenv("GITHUB_REDIRECT_URI")
    
    if not client_id or not redirect_uri:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    
    github_auth_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=repo,user:email"
    )
    return RedirectResponse(github_auth_url)

@router.get("/github/callback")
def github_callback(code: str):
    client_id = os.getenv("GITHUB_CLIENT_ID")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    frontend = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    
    token_res = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code
        }
    ).json()
    
    access_token = token_res.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to get access token")
    
    return RedirectResponse(f"{frontend}/dashboard?token={access_token}")

def get_current_user_from_token(token: str, db: Session) -> User:
    """Get user from GitHub token"""
    try:
        # Get user info from GitHub
        user_res = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {token}"}
        )
        
        if user_res.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        github_user = user_res.json()
        github_id = str(github_user["id"])
        
        # Find or create user in database
        user = db.query(User).filter(User.github_id == github_id).first()
        
        if not user:
            # Create new user
            user = User(
                email=github_user.get("email", ""),
                name=github_user.get("name", github_user.get("login", "")),
                github_id=github_id,
                github_token=token
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update token
            user.github_token = token
            db.commit()
        
        return user
    
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(token: str = None, db: Session = Depends(get_db)) -> User:
    """Dependency to get current user"""
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    
    return get_current_user_from_token(token, db)