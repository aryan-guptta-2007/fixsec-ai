from fastapi import APIRouter

from core.workspace import get_workspace_manager

router = APIRouter()


@router.get("/health")
def workspace_health_check():
    """Disk usage of in-flight checkouts. Clones are temporary, so this stays near zero."""
    stats = get_workspace_manager().get_workspace_stats()
    return {
        "status": "warning" if stats["total_size_mb"] > 1000 else "healthy",
        "workspace_stats": stats,
    }
