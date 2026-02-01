from fastapi import APIRouter, Header, HTTPException, Query
from core.scan_history import get_scan_history, get_all_repos_with_history, get_latest_scan
from core.security_scorer import calculate_vulnerability_score, calculate_trend_analysis

router = APIRouter()

@router.get("/scan-history")
def get_repo_scan_history(
    repo: str = Query(..., description="Repository name (owner/repo)"),
    authorization: str = Header(None)
):
    """Get scan history for a specific repository"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    history = get_scan_history(repo)
    
    return {
        "repo": repo,
        "total_scans": len(history),
        "history": history
    }

@router.get("/security-score")
def get_repo_security_score(
    repo: str = Query(..., description="Repository name (owner/repo)"),
    authorization: str = Header(None)
):
    """Get current security score and trend analysis for a repository"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    history = get_scan_history(repo)
    
    if not history:
        return {
            "repo": repo,
            "error": "No scan history found",
            "message": "Run a scan first to get security score"
        }
    
    # Get latest scan for current score
    latest_scan = history[-1]
    vulnerabilities = latest_scan.get("vulnerabilities", [])
    current_score = calculate_vulnerability_score(vulnerabilities)
    
    # Calculate trend analysis
    trend_analysis = calculate_trend_analysis(history)
    
    return {
        "repo": repo,
        "current_score": current_score,
        "trend_analysis": trend_analysis,
        "last_scan": latest_scan.get("timestamp"),
        "total_scans": len(history)
    }

@router.get("/repos-with-history")
def get_repos_with_scan_history(authorization: str = Header(None)):
    """Get list of all repositories that have scan history"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    repos = get_all_repos_with_history()
    
    # Get latest scan info for each repo
    repos_info = []
    for repo in repos:
        latest = get_latest_scan(repo)
        if latest:
            repos_info.append({
                "repo": repo,
                "last_scan": latest["timestamp"],
                "last_count": latest["count"],
                "last_status": latest["status"]
            })
    
    return {
        "total_repos": len(repos_info),
        "repos": repos_info
    }