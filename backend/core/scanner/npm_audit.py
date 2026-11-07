"""
Dependency auditing through npm.

The repositories processed here are untrusted, so npm must never execute their
code: lifecycle scripts are disabled and only lockfiles are resolved, nothing is
installed. npm also runs with a minimal environment, so it cannot see this
server's secrets, and with the public registry forced, so a .npmrc in the
repository cannot redirect it.
"""
import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from core.scanner.files import SKIP_DIRS
from core.scanner.secrets import finding_id

logger = logging.getLogger(__name__)

MAX_PACKAGE_DIRS = 5
MAX_DEPTH = 3
SEVERITY_MAP = {
    "info": "LOW",
    "low": "LOW",
    "moderate": "MEDIUM",
    "high": "HIGH",
    "critical": "CRITICAL",
}
SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
PASSTHROUGH_ENV = (
    "PATH", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "SYSTEMROOT", "SYSTEMDRIVE",
    "TEMP", "TMP", "COMSPEC", "PATHEXT", "PROGRAMFILES", "NVM_HOME", "NVM_SYMLINK",
)
SAFE_FLAGS = ["--ignore-scripts", "--no-fund"]


def npm_path() -> Optional[str]:
    """Locate npm. Resolves npm.cmd on Windows and plain npm everywhere else."""
    return shutil.which("npm")


def _env() -> Dict[str, str]:
    env = {key: os.environ[key] for key in PASSTHROUGH_ENV if key in os.environ}
    env.update(
        {
            "npm_config_ignore_scripts": "true",
            "npm_config_registry": "https://registry.npmjs.org/",
            "npm_config_update_notifier": "false",
        }
    )
    return env


def _run_npm(args: List[str], cwd: str, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        [npm_path(), *args],
        cwd=cwd,
        env=_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def find_package_dirs(repo_path: str) -> List[str]:
    """Repo-relative directories holding a package.json, shallowest first."""
    found: List[str] = []
    for root, dirs, files in os.walk(repo_path):
        relative = os.path.relpath(root, repo_path).replace(os.sep, "/")
        depth = 0 if relative == "." else relative.count("/") + 1
        dirs[:] = [] if depth >= MAX_DEPTH else [d for d in dirs if d not in SKIP_DIRS]
        if "package.json" in files:
            found.append(relative)
    found.sort(key=lambda path: (0 if path == "." else path.count("/") + 1, path))
    return found[:MAX_PACKAGE_DIRS]


def _manifest_path(package_dir: str) -> str:
    return "package.json" if package_dir == "." else f"{package_dir}/package.json"


def _exact_pins(directory: str) -> Set[str]:
    """Direct dependencies pinned to one version, which `npm audit fix` will not move."""
    try:
        with open(os.path.join(directory, "package.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError):
        return set()
    declared = {**manifest.get("dependencies", {}), **manifest.get("devDependencies", {})}
    return {name for name, spec in declared.items() if re.fullmatch(r"\d[\w.+-]*", str(spec))}


def _parse_audit(
    data: Dict[str, Any], package_dir: str, has_lockfile: bool, pins: Set[str]
) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    manifest = _manifest_path(package_dir)
    for name, info in data.get("vulnerabilities", {}).items():
        severity = SEVERITY_MAP.get(str(info.get("severity", "")).lower(), "MEDIUM")
        fix = info.get("fixAvailable", False)
        breaking = isinstance(fix, dict) and bool(fix.get("isSemVerMajor"))
        via = info.get("via", [])
        advisories = [item for item in via if isinstance(item, dict)]
        title = advisories[0].get("title") if advisories else None
        findings.append(
            {
                "id": finding_id("dep", manifest, name),
                "category": "dependency",
                "type": "Insecure Dependency",
                "severity": severity,
                "package": name,
                "package_dir": package_dir,
                "file": manifest,
                "file_path": manifest,
                "line": None,
                "line_number": None,
                "message": f"{name} ({info.get('range', 'unknown')}): {title or 'vulnerable dependency'}",
                "confidence_score": 95,
                "fixable": bool(fix) and not breaking and has_lockfile and name not in pins,
                "fix_available": bool(fix),
                "breaking_fix": breaking,
                "pinned": name in pins,
                "has_lockfile": has_lockfile,
                "advisory_url": advisories[0].get("url") if advisories else None,
            }
        )
    return findings


def _audit_directory(
    repo_path: str, package_dir: str
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    directory = str(Path(repo_path) / package_dir)
    label = _manifest_path(package_dir)
    has_lockfile = os.path.exists(os.path.join(directory, "package-lock.json"))
    try:
        if not has_lockfile:
            lock = _run_npm(
                ["install", "--package-lock-only", "--no-audit", *SAFE_FLAGS], directory, 120
            )
            if lock.returncode != 0:
                return [], f"Could not resolve dependencies for {label}."

        result = _run_npm(["audit", "--json"], directory, 60)
    except subprocess.TimeoutExpired:
        return [], f"Dependency audit timed out for {label}."
    except OSError as exc:
        logger.warning("npm failed for %s: %s", label, exc)
        return [], f"Dependency audit could not run for {label}."

    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return [], f"Dependency audit returned unreadable output for {label}."
    if "error" in data or "vulnerabilities" not in data:
        return [], f"Dependency audit failed for {label}."
    return _parse_audit(data, package_dir, has_lockfile, _exact_pins(directory)), None


def audit_dependencies(repo_path: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Audit every package.json near the top of the repository.

    Returns findings plus warnings. A warning means part of the audit did not
    happen, which must not read as "no vulnerabilities".
    """
    package_dirs = find_package_dirs(repo_path)
    if not package_dirs:
        return [], []
    if npm_path() is None:
        return [], ["npm is not available on the server, so dependencies were not audited."]

    findings: List[Dict[str, Any]] = []
    warnings: List[str] = []
    for package_dir in package_dirs:
        directory_findings, warning = _audit_directory(repo_path, package_dir)
        findings.extend(directory_findings)
        if warning:
            warnings.append(warning)
    findings.sort(key=lambda item: SEVERITY_ORDER.get(item["severity"], 4))
    return findings, warnings


def fix_dependencies(repo_path: str, package_dir: str) -> Optional[Set[str]]:
    """Apply non-breaking updates to package.json and package-lock.json only.

    Returns the packages still vulnerable afterwards, or None if npm could not
    run. `npm audit fix` exits non-zero whenever anything remains, even after a
    partial fix, so the result comes from auditing again.
    """
    if npm_path() is None:
        return None
    directory = str(Path(repo_path) / package_dir)
    try:
        _run_npm(["audit", "fix", "--package-lock-only", *SAFE_FLAGS], directory, 180)
        result = _run_npm(["audit", "--json"], directory, 60)
        data = json.loads(result.stdout or "{}")
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as exc:
        logger.warning("npm audit fix failed for %s: %s", package_dir, exc)
        return None
    if "vulnerabilities" not in data:
        return None
    return set(data["vulnerabilities"])
