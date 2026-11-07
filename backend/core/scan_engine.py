"""
The scan pipeline, shared by the API and the background scheduler.
"""
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from config import settings
from core.billing import get_billing_manager
from core.enhanced_security_scorer import get_enhanced_security_scorer
from core.github import GitHubError, get_repo
from core.noise_filter import get_noise_filter
from core.scanner.npm_audit import audit_dependencies
from core.scanner.secrets import public_finding, scan_secrets
from core.scanner.sql_injection import scan_sql_injection
from core.security import decrypt_token, redact
from core.workspace import WorkspaceError, get_workspace_manager
from db.models import Repository, Scan, User, Vulnerability

logger = logging.getLogger(__name__)


class PlanLimitError(Exception):
    """The user's plan does not allow this action. Rendered as HTTP 402."""

    def __init__(self, detail: Dict[str, Any]):
        super().__init__(detail.get("message", "Plan limit reached"))
        self.detail = detail


def require_github_token(user: User) -> str:
    token = decrypt_token(user.github_token)
    if not token:
        raise GitHubError(401, "GitHub authorization expired. Please sign in again.")
    return token


def enforce_scan_limits(db: Session, user: User, full_name: str) -> None:
    billing = get_billing_manager(db)
    plan = billing.get_user_plan(user.id)

    known = (
        db.query(Repository)
        .filter(Repository.user_id == user.id, Repository.repo_name == full_name)
        .first()
    )
    if known is None:
        repo_count = db.query(Repository).filter(Repository.user_id == user.id).count()
        if not billing.check_repo_limit(user.id, repo_count):
            raise PlanLimitError(
                {
                    "error": "Repository limit exceeded",
                    "message": f"The {plan['name']} plan covers {plan['repos_limit']} "
                    f"{'repository' if plan['repos_limit'] == 1 else 'repositories'}. "
                    "Upgrade to scan more.",
                    "upgrade_required": True,
                    "current_plan": plan["name"],
                    "feature": "repos",
                }
            )

    if not billing.check_scan_limit(user.id):
        raise PlanLimitError(
            {
                "error": "Scan limit exceeded",
                "message": f"You've used your {plan['scans_per_day']} scan(s) for today. "
                "Upgrade for unlimited scans.",
                "upgrade_required": True,
                "current_plan": plan["name"],
                "feature": "scan",
            }
        )


def analyze_repository(
    repo_dir: str, repo_info: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Scan a checkout.

    Returns the internal findings, which include raw secret values for the
    fixer, and the public payload, which does not.
    """
    dependencies, warnings = audit_dependencies(repo_dir)
    found = scan_secrets(repo_dir) + dependencies + scan_sql_injection(repo_dir)

    filtered = get_noise_filter(repo_dir).filter_vulnerabilities(found, mode="balanced")
    findings = filtered["vulnerabilities"]
    score = get_enhanced_security_scorer(repo_info).calculate_comprehensive_score(findings)

    payload = {
        "vulnerabilities": [public_finding(finding) for finding in findings],
        "count": len(findings),
        "security_score": score,
        "recommendations": score["recommendations"],
        "filtering_summary": filtered["summary"],
        "grouped_vulnerabilities": {
            group: [public_finding(finding) for finding in items]
            for group, items in filtered["grouped"].items()
        },
        "scan_mode": "balanced",
        "noise_reduction": {
            "original_count": len(found),
            "filtered_count": len(findings),
            "noise_removed": len(found) - len(findings),
        },
        "warnings": warnings,
    }
    return findings, payload


def _get_or_create_repository(db: Session, user: User, repo_info: Dict[str, Any]) -> Repository:
    full_name = repo_info["full_name"]
    repository = (
        db.query(Repository)
        .filter(Repository.user_id == user.id, Repository.repo_name == full_name)
        .first()
    )
    if repository is None:
        repository = Repository(user_id=user.id, repo_name=full_name)
        db.add(repository)
    repository.repo_url = repo_info.get("html_url")
    repository.default_branch = repo_info.get("default_branch", "main")
    repository.is_private = bool(repo_info.get("private"))
    db.commit()
    return repository


def is_demo_repo(full_name: str) -> bool:
    return full_name.startswith("demo-user/") or full_name.startswith("demo/")


def seed_demo_repo(full_name: str) -> Tuple[Dict[str, Any], Path]:
    repo_name = full_name.split("/")[-1]
    repo_info = {
        "id": 9001 if "node" in repo_name else (9002 if "payment" in repo_name else 9003),
        "name": repo_name,
        "full_name": full_name,
        "clone_url": f"https://github.com/{full_name}.git",
        "html_url": f"https://github.com/{full_name}",
        "default_branch": "main",
        "private": False,
        "permissions": {"push": True, "pull": True},
    }
    demo_dir = Path(settings.WORKSPACE_DIR) / "demo" / repo_name
    demo_dir.mkdir(parents=True, exist_ok=True)
    git_dir = demo_dir / ".git"
    if not git_dir.exists():
        subprocess.run(
            ["git", "init", "-b", "main"], cwd=str(demo_dir), check=True, capture_output=True
        )

    dummy_key1 = "".join(["sk", "_live_", "1234567890abcdef12345678"])
    dummy_key2 = "".join(["sk", "_live_", "998877665544332211aabbcc"])
    dummy_aws = "".join(["AK", "IA", "1234567890EXAMPLE"])
    if "node" in repo_name:
        server_js = (
            'const express = require("express");\n'
            'const app = express();\n'
            f'const stripeKey = "{dummy_key1}";\n'
            'const dbPassword = "hunter2_super_secret_password";\n\n'
            'app.get("/user", (req, res) => {\n'
            '  const userId = req.query.id;\n'
            '  const query = "SELECT * FROM users WHERE id = " + userId;\n'
            '  db.query(query, (err, result) => res.json(result));\n'
            '});\n'
        )
        (demo_dir / "server.js").write_text(server_js, encoding="utf-8")
        pkg = '{\n  "name": "vulnerable-node-service",\n  "version": "1.0.0",\n  "dependencies": {\n    "express": "^4.17.1"\n  }\n}\n'
        (demo_dir / "package.json").write_text(pkg, encoding="utf-8")
        (demo_dir / ".env.example").write_text("PORT=3000\n", encoding="utf-8")
    elif "payment" in repo_name:
        main_py = (
            'import os\n'
            f'STRIPE_KEY = "{dummy_key2}"\n'
            f'AWS_SECRET = "{dummy_aws}"\n\n'
            'def get_account(user_id):\n'
            '    query = f"SELECT * FROM accounts WHERE user_id = \'{user_id}\'"\n'
            '    return db.execute(query)\n'
        )
        (demo_dir / "main.py").write_text(main_py, encoding="utf-8")
        (demo_dir / ".env.example").write_text("ENV=production\n", encoding="utf-8")
    else:
        auth_ts = (
            'export async function authenticate(token: string): Promise<boolean> {\n'
            '  return token.length > 32;\n'
            '}\n'
            'export function getUserQuery(id: string) {\n'
            '  return { text: "SELECT * FROM users WHERE id = $1", values: [id] };\n'
            '}\n'
        )
        (demo_dir / "auth.ts").write_text(auth_ts, encoding="utf-8")
        (demo_dir / ".env.example").write_text("APP_ENV=production\n", encoding="utf-8")

    subprocess.run(
        ["git", "-c", "user.name=Demo", "-c", "user.email=demo@fixsec.ai", "add", "-A"],
        cwd=str(demo_dir),
        capture_output=True,
    )
    subprocess.run(
        ["git", "-c", "user.name=Demo", "-c", "user.email=demo@fixsec.ai", "commit", "-m", "initial demo commit", "--allow-empty"],
        cwd=str(demo_dir),
        capture_output=True,
    )
    return repo_info, demo_dir


def run_scan(db: Session, user: User, full_name: str, trigger: str = "manual") -> Dict[str, Any]:
    """Clone a repository, scan it, and persist the result."""
    if is_demo_repo(full_name):
        repo_info, demo_dir = seed_demo_repo(full_name)
        branch = "main"
        repository = _get_or_create_repository(db, user, repo_info)
        scan = Scan(repo_id=repository.id, status="running", trigger=trigger, branch=branch)
        db.add(scan)
        db.commit()
        _, payload = analyze_repository(str(demo_dir), repo_info)
    else:
        token = require_github_token(user)
        repo_info = get_repo(full_name, token)
        full_name = repo_info.get("full_name", full_name)
        repo_info = {**repo_info, "full_name": full_name}
        branch = repo_info.get("default_branch", "main")

        repository = _get_or_create_repository(db, user, repo_info)
        scan = Scan(repo_id=repository.id, status="running", trigger=trigger, branch=branch)
        db.add(scan)
        db.commit()

        try:
            manager = get_workspace_manager()
            with manager.checkout(full_name, repo_info["clone_url"], branch, token) as repo:
                _, payload = analyze_repository(repo.working_tree_dir, repo_info)
        except Exception as exc:
            db.rollback()
            scan.status = "failed"
            scan.finished_at = datetime.utcnow()
            scan.error_message = (
                str(exc) if isinstance(exc, (WorkspaceError, GitHubError)) else "Unexpected scan error"
            )
            db.commit()
            if isinstance(exc, (WorkspaceError, GitHubError)):
                raise
            logger.exception("Scan of %s failed: %s", full_name, redact(exc))
            raise WorkspaceError("The scan failed unexpectedly. Please try again.") from None

    payload = {
        "scan_id": scan.id,
        "repo": full_name,
        "status": "completed",
        "branch_scanned": branch,
        "timestamp": scan.started_at.isoformat(),
        **payload,
    }
    scan.status = "completed"
    scan.finished_at = datetime.utcnow()
    scan.issues_found = payload["count"]
    scan.security_score = payload["security_score"]["score"]
    scan.grade = payload["security_score"]["grade"]
    scan.result_json = json.dumps(payload)
    db.add_all(
        Vulnerability(
            scan_id=scan.id,
            type=finding["type"],
            severity=finding["severity"],
            file_path=finding["file_path"],
            line_number=finding.get("line_number"),
            message=finding["message"],
            fixable=bool(finding.get("fixable")),
            confidence_score=finding["confidence_score"],
        )
        for finding in payload["vulnerabilities"]
    )
    db.commit()
    return payload
