"""
Workspace Management for FixSec AI
Handles permanent workspace directories for repository operations
Solves Windows temp-lock issues (WinError 32) permanently
"""
import os
import shutil
import time
import hashlib
from pathlib import Path
from typing import Optional
import git

class WorkspaceManager:
    """Manages permanent workspace directories for repository operations"""
    
    def __init__(self, base_path: str = "workspace"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        print(f"📁 Workspace manager initialized: {self.base_path.absolute()}")
    
    def get_repo_workspace(self, repo_full_name: str) -> Path:
        """Get a permanent workspace directory for a repository"""
        # Create safe directory name from repo name
        safe_name = self._sanitize_repo_name(repo_full_name)
        workspace_dir = self.base_path / safe_name
        workspace_dir.mkdir(exist_ok=True)
        return workspace_dir
    
    def _sanitize_repo_name(self, repo_full_name: str) -> str:
        """Convert repo name to safe directory name"""
        # Replace all special characters with underscores
        safe_name = ""
        for char in repo_full_name:
            if char.isalnum():
                safe_name += char
            else:
                safe_name += "_"
        
        # Remove multiple consecutive underscores
        while "__" in safe_name:
            safe_name = safe_name.replace("__", "_")
        
        # Remove leading/trailing underscores
        safe_name = safe_name.strip("_")
        
        # Add hash to prevent collisions and ensure uniqueness
        hash_suffix = hashlib.md5(repo_full_name.encode()).hexdigest()[:8]
        return f"{safe_name}_{hash_suffix}"
    
    def prepare_repo_workspace(self, repo_full_name: str, clone_url: str, default_branch: str = "main") -> Path:
        """Prepare a clean workspace with the latest repository code"""
        workspace_dir = self.get_repo_workspace(repo_full_name)
        repo_dir = workspace_dir / "repo"
        
        print(f"📁 Preparing workspace: {workspace_dir}")
        
        # Clean existing repo if it exists
        if repo_dir.exists():
            print("🧹 Cleaning existing repository...")
            self._safe_remove_directory(repo_dir)
        
        # Clone fresh repository
        print(f"📥 Cloning {repo_full_name}...")
        try:
            repo = git.Repo.clone_from(clone_url, repo_dir)
            
            # Checkout and pull latest
            print(f"🔄 Checking out latest {default_branch}")
            repo.git.checkout(default_branch)
            repo.git.pull("origin", default_branch)
            
            print(f"✅ Repository ready: {repo_dir}")
            return repo_dir
            
        except Exception as e:
            print(f"❌ Failed to prepare repository: {e}")
            # Clean up on failure
            if repo_dir.exists():
                self._safe_remove_directory(repo_dir)
            raise
    
    def _safe_remove_directory(self, directory: Path, max_retries: int = 5) -> bool:
        """Safely remove directory with Windows file lock handling"""
        if not directory.exists():
            return True
        
        for attempt in range(max_retries):
            try:
                # Close any potential file handles
                import gc
                gc.collect()
                
                # Try to remove
                shutil.rmtree(directory, ignore_errors=False)
                print(f"🗑️ Removed directory: {directory}")
                return True
                
            except PermissionError as e:
                print(f"⚠️ Attempt {attempt + 1}: Permission error removing {directory}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Wait before retry
                else:
                    print(f"⚠️ Could not remove {directory}, will try ignore_errors=True")
                    try:
                        shutil.rmtree(directory, ignore_errors=True)
                        return True
                    except:
                        print(f"❌ Failed to remove {directory} completely")
                        return False
            except Exception as e:
                print(f"❌ Unexpected error removing {directory}: {e}")
                return False
        
        return False
    
    def cleanup_old_workspaces(self, max_age_hours: int = 24) -> int:
        """Clean up old workspace directories"""
        if not self.base_path.exists():
            return 0
        
        current_time = time.time()
        cleaned_count = 0
        
        for workspace_dir in self.base_path.iterdir():
            if not workspace_dir.is_dir():
                continue
            
            # Check if workspace is old
            dir_age_hours = (current_time - workspace_dir.stat().st_mtime) / 3600
            
            if dir_age_hours > max_age_hours:
                print(f"🧹 Cleaning old workspace: {workspace_dir.name} ({dir_age_hours:.1f}h old)")
                if self._safe_remove_directory(workspace_dir):
                    cleaned_count += 1
        
        if cleaned_count > 0:
            print(f"✅ Cleaned {cleaned_count} old workspaces")
        
        return cleaned_count
    
    def get_workspace_stats(self) -> dict:
        """Get statistics about workspace usage"""
        if not self.base_path.exists():
            return {"total_workspaces": 0, "total_size_mb": 0}
        
        total_workspaces = 0
        total_size = 0
        
        for workspace_dir in self.base_path.iterdir():
            if workspace_dir.is_dir():
                total_workspaces += 1
                # Calculate directory size
                for file_path in workspace_dir.rglob("*"):
                    if file_path.is_file():
                        try:
                            total_size += file_path.stat().st_size
                        except:
                            pass  # Skip files we can't access
        
        return {
            "total_workspaces": total_workspaces,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "base_path": str(self.base_path.absolute())
        }

# Global workspace manager instance
workspace_manager = WorkspaceManager()

def get_workspace_manager() -> WorkspaceManager:
    """Get the global workspace manager instance"""
    return workspace_manager