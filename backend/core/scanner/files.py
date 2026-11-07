"""
Shared file walking for the scanners.
"""
import os
from pathlib import PurePosixPath
from typing import Iterator, Set, Tuple

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "bower_components", "vendor", "dist", "build",
    "out", "target", ".next", ".nuxt", ".cache", ".venv", "venv", "env", "__pycache__",
    ".tox", ".pytest_cache", "coverage", "site-packages",
}
SKIP_NAMES = {
    "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "Pipfile.lock", "composer.lock", "Gemfile.lock", "go.sum", "Cargo.lock",
}
MAX_FILE_BYTES = 1_000_000

TEST_DIRS = {"test", "tests", "__tests__", "spec", "specs", "fixtures", "__mocks__"}
TEST_MARKERS = (".test.", ".spec.", "_test.", "_spec.")


def walk_files(repo_path: str) -> Iterator[Tuple[str, str]]:
    """Yield (absolute path, repo-relative POSIX path) for every scannable file."""
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name in SKIP_NAMES or name.endswith((".min.js", ".min.css", ".map")):
                continue
            path = os.path.join(root, name)
            try:
                if os.path.getsize(path) > MAX_FILE_BYTES or os.path.islink(path):
                    continue
            except OSError:
                continue
            yield path, os.path.relpath(path, repo_path).replace(os.sep, "/")


def walk_with_extensions(repo_path: str, extensions: Set[str]) -> Iterator[Tuple[str, str]]:
    for path, relative in walk_files(repo_path):
        name = PurePosixPath(relative).name
        if name.startswith(".env") or PurePosixPath(relative).suffix in extensions:
            yield path, relative


def is_test_path(relative_path: str) -> bool:
    path = PurePosixPath(relative_path.lower())
    if TEST_DIRS.intersection(path.parts[:-1]):
        return True
    name = path.name
    return name.startswith(("test_", "spec_")) or any(m in name for m in TEST_MARKERS)
