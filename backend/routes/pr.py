import logging
from typing import Any, Dict

import git
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from core import github
from core.billing import get_billing_manager
from core.scan_engine import (
    PlanLimitError,
    analyze_repository,
    is_demo_repo,
    require_github_token,
    seed_demo_repo,
)
from core.scan_history import get_latest_scan_id
from core.security import redact
from core.smart_fixer import build_commit_message, build_pr_body, get_smart_fixer, public_plan
from core.workspace import WorkspaceError, get_workspace_manager, git_auth_env
from db.models import PullRequest, User
from db.session import get_db
from routes.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

BRANCH_NAME = "fixsec/auto-fix-security"
PR_TITLE = "FixSec AI: security fixes"
COMMIT_AUTHOR = git.Actor("FixSec AI", "fixsec-bot@users.noreply.github.com")


def _repository_from(payload: Dict[str, Any], token: str) -> Dict[str, Any]:
    full_name = payload.get("full_name") or payload.get("repo")
    if not github.is_valid_full_name(full_name):
        raise HTTPException(status_code=400, detail="Expected a repository as owner/repo")
    return github.get_repo(full_name, token)


@router.post("/fix-plan")
def get_fix_plan(
    payload: dict = Body(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preview what auto-fix would change.

    Findings are recomputed from a fresh clone. Client-supplied findings are never
    trusted: they carry file paths, and line numbers go stale as the code moves.
    """
    full_name = payload.get("full_name") or payload.get("repo")
    if is_demo_repo(full_name):
        repo_info, demo_dir = seed_demo_repo(full_name)
        branch = "main"
        findings, _ = analyze_repository(str(demo_dir), repo_info)
        plan = get_smart_fixer(str(demo_dir)).generate_comprehensive_fix_plan(findings)
        return {
            "repo": full_name,
            "branch": branch,
            "fix_plan": public_plan(plan),
            "can_auto_fix": get_billing_manager(db).can_use_auto_fix(user.id),
        }

    token = require_github_token(user)
    repo_info = _repository_from(payload, token)
    full_name = repo_info["full_name"]
    branch = repo_info.get("default_branch", "main")

    with get_workspace_manager().checkout(full_name, repo_info["clone_url"], branch, token) as repo:
        findings, _ = analyze_repository(repo.working_tree_dir, repo_info)
        plan = get_smart_fixer(repo.working_tree_dir).generate_comprehensive_fix_plan(findings)

    return {
        "repo": full_name,
        "branch": branch,
        "fix_plan": public_plan(plan),
        "can_auto_fix": get_billing_manager(db).can_use_auto_fix(user.id),
    }


@router.post("/auto-fix")
def auto_fix(
    payload: dict = Body(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    billing = get_billing_manager(db)
    if not billing.can_use_auto_fix(user.id):
        plan = billing.get_user_plan(user.id)
        raise PlanLimitError(
            {
                "error": "Auto-fix feature not available",
                "message": f"Auto-fix PRs are on the Professional and Team plans. "
                f"You're on the {plan['name']} plan.",
                "upgrade_required": True,
                "current_plan": plan["name"],
                "feature": "auto_fix",
            }
        )

    full_name = payload.get("full_name") or payload.get("repo")
    if is_demo_repo(full_name):
        repo_info, demo_dir = seed_demo_repo(full_name)
        branch = "main"
        findings, _ = analyze_repository(str(demo_dir), repo_info)
        fixer = get_smart_fixer(str(demo_dir))
        plan = fixer.generate_comprehensive_fix_plan(findings)
        results = fixer.apply_smart_fixes(plan)

        pr_url = f"https://github.com/{full_name}/pull/1"
        latest_scan_id = get_latest_scan_id(db, user, full_name)
        if latest_scan_id:
            db.add(
                PullRequest(
                    scan_id=latest_scan_id,
                    pr_url=pr_url,
                    branch_name=BRANCH_NAME,
                    fixes_applied=results["fixes_applied"],
                )
            )
            db.commit()

        return {
            "status": "PR Created",
            "repo": full_name,
            "url": pr_url,
            "fixes_applied": results["fixes_applied"],
            "fixes_failed": results["fixes_failed"],
            "requires_review": len(plan["requires_review"]),
            "env_vars": results["env_vars"],
        }

    token = require_github_token(user)
    repo_info = _repository_from(payload, token)
    full_name = repo_info["full_name"]
    branch = repo_info.get("default_branch", "main")
    if repo_info.get("archived"):
        raise HTTPException(status_code=409, detail="This repository is archived.")
    if not (repo_info.get("permissions") or {}).get("push"):
        raise HTTPException(
            status_code=403, detail=f"You don't have push access to {full_name}."
        )

    with get_workspace_manager().checkout(full_name, repo_info["clone_url"], branch, token) as repo:
        repo_dir = repo.working_tree_dir
        findings, _ = analyze_repository(repo_dir, repo_info)
        fixer = get_smart_fixer(repo_dir)
        plan = fixer.generate_comprehensive_fix_plan(findings)
        results = fixer.apply_smart_fixes(plan)

        if not results["modified_files"]:
            return {
                "status": "No automatic fixes available",
                "repo": full_name,
                "message": f"{len(plan['requires_review'])} issue(s) need manual review. "
                "Nothing could be changed automatically.",
                "requires_review": len(plan["requires_review"]),
            }

        # Stage exactly what the fixer changed, so nothing else can reach the
        # remote: not a stray .env, and not anything npm left behind.
        try:
            repo.git.checkout("-B", BRANCH_NAME)
            repo.git.add("--", *sorted(set(results["modified_files"])))
            repo.index.commit(
                build_commit_message(results), author=COMMIT_AUTHOR, committer=COMMIT_AUTHOR
            )
            with repo.git.custom_environment(**git_auth_env(token)):
                repo.git.push("--force", "origin", f"HEAD:refs/heads/{BRANCH_NAME}")
        except git.GitCommandError as exc:
            logger.warning("Push to %s failed: %s", full_name, redact(exc.stderr))
            raise WorkspaceError(
                f"Could not push the fix branch to {full_name}. Check that branch "
                "protection allows it."
            ) from None

    body = build_pr_body(results, plan)
    owner = full_name.split("/")[0]
    pull_request = github.create_pull_request(token, full_name, BRANCH_NAME, branch, PR_TITLE, body)

    status = "PR Created"
    if pull_request is None:
        status = "PR Updated"
        pull_request = github.find_open_pull_request(token, full_name, owner, BRANCH_NAME)
        if pull_request:
            github.update_pull_request(token, full_name, pull_request["number"], body)

    url = pull_request.get("html_url") if pull_request else None
    scan_id = get_latest_scan_id(db, user, full_name)
    if url and scan_id:
        db.add(
            PullRequest(
                scan_id=scan_id,
                pr_url=url,
                branch_name=BRANCH_NAME,
                fixes_applied=results["fixes_applied"],
            )
        )
        db.commit()

    return {
        "status": status,
        "repo": full_name,
        "url": url,
        "fixes_applied": results["fixes_applied"],
        "fixes_failed": results["fixes_failed"],
        "requires_review": len(plan["requires_review"]),
        "env_vars": results["env_vars"],
    }
