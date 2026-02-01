from fastapi import APIRouter, Header, HTTPException
import requests

router = APIRouter()

@router.get("")
@router.get("/")
def list_repos(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = authorization.replace("Bearer ", "").strip()
    
    res = requests.get(
        "https://api.github.com/user/repos?per_page=100&sort=updated",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    
    data = res.json()
    
    if isinstance(data, dict) and data.get("message"):
        return {"error": data["message"], "status": res.status_code}
    
    return data