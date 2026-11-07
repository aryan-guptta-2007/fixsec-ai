"""
Workspace management for FixSec AI.

Each operation gets its own throwaway clone, removed as soon as the operation
ends. Concurrent scans of one repository cannot clobber each other, customer
code does not linger on disk, and the GitHub token never touches the filesystem:
it is handed to git through environment-only config, so it is not in the remote
URL, in .git/config, or in git's error output.
"""
import base64
import gc
import hashlib
import logging
import os
import shutil
import stat
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, Optional

import git

from config import settings
from core.security import redact

logger = logging.getLogger(__name__)


class WorkspaceError(Exception):
    """A repository could not be prepared. The message is safe to show users."""


def git_auth_env(token: Optional[str]) -> Dict[str, str]:
    """Environment that authenticates git to GitHub without persisting anything."""
    env = {"GIT_TERMINAL_PROMPT": "0"}
    if token:
        credentials = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        env.update(
            {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": f"http.{settings.GITHUB_WEB_URL}/.extraheader",
                "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {credentials}",
            }
        )
    return env


def _force_remove(function, path, _exc_info):
    """Git marks pack files read-only, which blocks deletion on Windows."""
    os.chmod(path, stat.S_IWRITE)
    function(path)


class WorkspaceManager:
    """Creates and cleans up per-operation repository checkouts."""

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or settings.WORKSPACE_DIR)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _job_dir(self, repo_full_name: str) -> Path:
        digest = hashlib.sha256(repo_full_name.encode()).hexdigest()[:12]
        return self.base_path / f"{digest}_{uuid.uuid4().hex}"

    @contextmanager
    def checkout(
        self,
        repo_full_name: str,
        clone_url: str,
        branch: str,
        token: Optional[str] = None,
    ) -> Iterator[git.Repo]:
        """Shallow-clone a branch into a fresh directory for the duration of the block."""
        job_dir = self._job_dir(repo_full_name)
        repo = None
        try:
            try:
                repo = git.Repo.clone_from(
                    clone_url,
                    job_dir / "repo",
                    env=git_auth_env(token),
                    branch=branch,
                    depth=1,
                    single_branch=True,
                )
            except git.GitCommandError as exc:
                logger.warning("Clone of %s failed: %s", repo_full_name, redact(exc.stderr))
                raise WorkspaceError(
                    f"Could not clone {repo_full_name}. The repository may be empty, or "
                    "FixSec AI may not have access to it."
                ) from None
            yield repo
        finally:
            if repo is not None:
                repo.close()
            self._remove(job_dir)

    def _remove(self, directory: Path, attempts: int = 5) -> bool:
        for attempt in range(attempts):
            if not directory.exists():
                return True
            try:
                gc.collect()  # release file handles GitPython may still hold
                shutil.rmtree(directory, onerror=_force_remove)
                return True
            except OSError as exc:
                logger.warning("Could not remove %s yet: %s", directory, exc)
                time.sleep(0.5 * (attempt + 1))
        return not directory.exists()

    def cleanup_old_workspaces(self, max_age_hours: int = 6) -> int:
        """Remove checkouts orphaned by a crash. Live ones are far younger than this."""
        removed = 0
        now = time.time()
        for entry in self.base_path.iterdir():
            if not entry.is_dir():
                continue
            if (now - entry.stat().st_mtime) / 3600 > max_age_hours and self._remove(entry):
                removed += 1
        return removed

    def get_workspace_stats(self) -> dict:
        total_size = 0
        total_workspaces = 0
        for entry in self.base_path.iterdir():
            if not entry.is_dir():
                continue
            total_workspaces += 1
            for file_path in entry.rglob("*"):
                try:
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
                except OSError:
                    continue  # the checkout may vanish while we walk it
        return {
            "total_workspaces": total_workspaces,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }


workspace_manager = WorkspaceManager()


def get_workspace_manager() -> WorkspaceManager:
    return workspace_manager
