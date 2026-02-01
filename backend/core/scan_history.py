"""
In-memory scan history store
Later this will be replaced with a proper database
"""
from datetime import datetime
from typing import List, Dict, Any
import json

# In-memory storage (will be replaced with DB later)
scan_history_store: Dict[str, List[Dict[str, Any]]] = {}

def save_scan_result(repo: str, scan_data: Dict[str, Any]) -> None:
    """Save scan result to history"""
    if repo not in scan_history_store:
        scan_history_store[repo] = []
    
    # Add timestamp and scan ID
    scan_record = {
        "scan_id": f"scan_{len(scan_history_store[repo]) + 1}",
        "timestamp": datetime.utcnow().isoformat(),
        "repo": repo,
        "vulnerabilities": scan_data.get("vulnerabilities", []),
        "count": scan_data.get("count", 0),
        "status": scan_data.get("status", ""),
        "branch_scanned": scan_data.get("branch_scanned", "main")
    }
    
    # Keep only last 10 scans per repo (memory management)
    scan_history_store[repo].append(scan_record)
    if len(scan_history_store[repo]) > 10:
        scan_history_store[repo] = scan_history_store[repo][-10:]
    
    print(f"📊 Saved scan history for {repo}: {scan_record['count']} issues")

def get_scan_history(repo: str) -> List[Dict[str, Any]]:
    """Get scan history for a repository"""
    return scan_history_store.get(repo, [])

def get_all_repos_with_history() -> List[str]:
    """Get list of all repos that have scan history"""
    return list(scan_history_store.keys())

def get_latest_scan(repo: str) -> Dict[str, Any] | None:
    """Get the most recent scan for a repository"""
    history = get_scan_history(repo)
    return history[-1] if history else None