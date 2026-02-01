from fastapi import APIRouter, Header, HTTPException
from core.workspace import get_workspace_manager

router = APIRouter()

@router.get("/stats")
def get_workspace_stats(authorization: str = Header(None)):
    """Get workspace usage statistics"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    workspace_manager = get_workspace_manager()
    stats = workspace_manager.get_workspace_stats()
    
    return {
        "status": "Workspace stats retrieved ✅",
        "stats": stats
    }

@router.post("/cleanup")
def cleanup_old_workspaces(
    max_age_hours: int = 24,
    authorization: str = Header(None)
):
    """Clean up old workspace directories"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    workspace_manager = get_workspace_manager()
    cleaned_count = workspace_manager.cleanup_old_workspaces(max_age_hours)
    
    return {
        "status": "Workspace cleanup completed ✅",
        "cleaned_workspaces": cleaned_count,
        "max_age_hours": max_age_hours
    }

@router.get("/health")
def workspace_health_check():
    """Check workspace system health"""
    workspace_manager = get_workspace_manager()
    stats = workspace_manager.get_workspace_stats()
    
    # Determine health status
    health_status = "healthy"
    warnings = []
    
    if stats["total_size_mb"] > 1000:  # More than 1GB
        warnings.append(f"Large workspace size: {stats['total_size_mb']}MB")
        health_status = "warning"
    
    if stats["total_workspaces"] > 50:  # More than 50 workspaces
        warnings.append(f"Many workspaces: {stats['total_workspaces']}")
        health_status = "warning"
    
    return {
        "status": health_status,
        "workspace_stats": stats,
        "warnings": warnings,
        "recommendations": [
            "Run cleanup if workspace size > 1GB",
            "Consider reducing max_age_hours for automatic cleanup",
            "Monitor workspace growth in production"
        ] if warnings else []
    }