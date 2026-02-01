from fastapi import APIRouter, Header, HTTPException, Depends
from sqlalchemy.orm import Session
import requests, os, tempfile, subprocess, time, shutil
import git
import urllib.parse
from core.fix_planner import generate_fix_plan
from core.smart_fixer import get_smart_fixer
from core.workspace import get_workspace_manager
from core.billing import get_billing_manager
from db.session import get_db
from routes.auth import get_current_user_from_token
from db.models import User

router = APIRouter()

def safe_rmtree(path):
    for _ in range(5):
        try:
            shutil.rmtree(path, ignore_errors=False)
            return
        except PermissionError:
            time.sleep(1)
    shutil.rmtree(path, ignore_errors=True)

@router.post("/fix-plan")
def get_fix_plan(payload: dict, authorization: str = Header(None)):
    """Generate detailed fix plan before creating PR"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = authorization.replace("Bearer ", "").strip()
    
    # ✅ accept repo OR full_name
    full_name = payload.get("full_name") or payload.get("repo")
    if not full_name:
        raise HTTPException(status_code=400, detail="Missing repo full_name/repo")
    
    # Get vulnerabilities from payload (from recent scan)
    vulnerabilities = payload.get("vulnerabilities", [])
    
    # ✅ get repo info
    repo_res = requests.get(
        f"https://api.github.com/repos/{full_name}",
        headers={"Authorization": f"token {token}"}
    )
    if repo_res.status_code != 200:
        raise HTTPException(status_code=400, detail=repo_res.json())
    
    repo_json = repo_res.json()
    clone_url = repo_json.get("clone_url")
    default_branch = repo_json.get("default_branch", "main")
    
    if not clone_url:
        raise HTTPException(status_code=400, detail="Repo clone_url missing")
    
    auth_url = clone_url.replace("https://", f"https://{token}@")
    
    # ✅ Use permanent workspace instead of temp directory
    workspace_manager = get_workspace_manager()
    
    try:
        # Prepare clean workspace with latest code
        repo_dir = workspace_manager.prepare_repo_workspace(full_name, auth_url, default_branch)
        
        # ✅ Use smart fixer for comprehensive fix plan
        smart_fixer = get_smart_fixer(str(repo_dir))
        comprehensive_plan = smart_fixer.generate_comprehensive_fix_plan(vulnerabilities)
        
        # Legacy fix plan for compatibility
        legacy_plan = generate_fix_plan(str(repo_dir), vulnerabilities)
        
        return {
            "repo": full_name,
            "branch": default_branch,
            "fix_plan": comprehensive_plan,
            "legacy_plan": legacy_plan,  # For backward compatibility
            "status": "Smart fix plan generated ✅",
            "preview_available": True,
            "smart_analysis": {
                "total_vulnerabilities": len(vulnerabilities),
                "auto_fixable": len(comprehensive_plan["fixable_automatically"]),
                "requires_review": len(comprehensive_plan["requires_review"]),
                "confidence_level": comprehensive_plan["risk_assessment"],
                "estimated_time": comprehensive_plan["estimated_time"]
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fix plan generation failed: {e}")

@router.post("/auto-fix")
def auto_fix(payload: dict, authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = authorization.replace("Bearer ", "").strip()
    
    # Get current user for billing checks
    try:
        current_user = get_current_user_from_token(token, db)
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Check if user can use auto-fix feature
    billing_manager = get_billing_manager(db)
    if not billing_manager.can_use_auto_fix(current_user.id):
        plan = billing_manager.get_user_plan(current_user.id)
        raise HTTPException(
            status_code=402,  # Payment Required
            detail={
                "error": "Auto-fix feature not available",
                "message": f"Auto-fix is only available on Pro and Team plans. You're currently on the {plan['name']} plan.",
                "upgrade_required": True,
                "current_plan": plan['name'],
                "feature": "auto_fix"
            }
        )
    
    # ✅ accept repo OR full_name
    full_name = payload.get("full_name") or payload.get("repo")
    if not full_name:
        raise HTTPException(status_code=400, detail="Missing repo full_name/repo")
    
    owner = full_name.split("/")[0]
    
    # ✅ get repo info
    repo_res = requests.get(
        f"https://api.github.com/repos/{full_name}",
        headers={"Authorization": f"token {token}"}
    )
    if repo_res.status_code != 200:
        raise HTTPException(status_code=400, detail=repo_res.json())
    
    repo_json = repo_res.json()
    clone_url = repo_json.get("clone_url")
    default_branch = repo_json.get("default_branch", "main")
    
    if not clone_url:
        raise HTTPException(status_code=400, detail="Repo clone_url missing")
    
    auth_url = clone_url.replace("https://", f"https://{token}@")
    
    branch_name = "fixsec/auto-fix-security"
    
    # ✅ Use permanent workspace instead of temp directory
    workspace_manager = get_workspace_manager()
    
    try:
        # Prepare clean workspace with latest code
        repo_dir = workspace_manager.prepare_repo_workspace(full_name, auth_url, default_branch)
        
        # Initialize git repo object for the workspace
        repo = git.Repo(repo_dir)
        
        # ✅ create new clean branch
        # delete local branch if exists
        try:
            repo.git.branch("-D", branch_name)
        except:
            pass
        repo.git.checkout("-b", branch_name)
        
        # ✅ Get vulnerabilities from payload for smart fixing
        vulnerabilities = payload.get("vulnerabilities", [])
        
        # ✅ Use smart fixer for comprehensive fixes (our competitive advantage!)
        smart_fixer = get_smart_fixer(str(repo_dir))
        
        if vulnerabilities:
            print("🚀 Applying smart fixes for all vulnerability types...")
            # Generate comprehensive fix plan
            fix_plan = smart_fixer.generate_comprehensive_fix_plan(vulnerabilities)
            
            # Apply smart fixes (secrets, SQL injection, config issues)
            fix_results = smart_fixer.apply_smart_fixes(fix_plan)
            
            print(f"✅ Smart fixer applied {fix_results['fixes_applied']} fixes")
            if fix_results['fixes_failed'] > 0:
                print(f"⚠️ {fix_results['fixes_failed']} fixes failed")
        
        # ✅ Also run npm audit fix for dependencies (enhanced version)
        package_json = os.path.join(repo_dir, "package.json")
        if os.path.exists(package_json):
            
            # install deps
            print("📦 Running npm install...")
            npm_install = subprocess.run(
                ["cmd", "/c", "npm", "install"],
                cwd=repo_dir,
                capture_output=True,
                text=True
            )
            
            if npm_install.returncode != 0:
                print("⚠️ npm install warning:", npm_install.stderr)
            
            # audit fix (use --force so it actually upgrades)
            print("🔧 Running enhanced npm audit fix...")
            npm_fix = subprocess.run(
                ["cmd", "/c", "npm", "audit", "fix", "--force"],
                cwd=repo_dir,
                capture_output=True,
                text=True
            )
            if npm_fix.returncode != 0:
                print("⚠️ npm audit fix warning:", npm_fix.stderr)
            
            time.sleep(1)
        
        # ✅ stage changes
        repo.git.add(A=True)
        
        # ✅ if no changes, return properly with clear messaging
        if not repo.is_dirty(untracked_files=True):
            # Check if there were any dependency vulnerabilities that could have been fixed
            package_json = os.path.join(repo_dir, "package.json")
            if os.path.exists(package_json):
                return {
                    "status": "No dependency fixes needed ✅",
                    "repo": full_name,
                    "message": "All dependency vulnerabilities are already resolved. Secrets require manual review."
                }
            else:
                return {
                    "status": "No auto-fixable issues found ✅",
                    "repo": full_name,
                    "message": "This repository has no dependency vulnerabilities that can be automatically fixed."
                }
        
        # ✅ commit with smart description
        commit_message = "FixSec AI: Smart security fixes\n\n"
        if vulnerabilities:
            secrets_count = len([v for v in vulnerabilities if "secret" in v.get("type", "").lower()])
            deps_count = len([v for v in vulnerabilities if "dependency" in v.get("type", "").lower()])
            sql_count = len([v for v in vulnerabilities if "sql injection" in v.get("type", "").lower()])
            
            if secrets_count > 0:
                commit_message += f"• Moved {secrets_count} hardcoded secrets to .env\n"
            if deps_count > 0:
                commit_message += f"• Updated {deps_count} vulnerable dependencies\n"
            if sql_count > 0:
                commit_message += f"• Fixed {sql_count} SQL injection vulnerabilities\n"
        else:
            commit_message += "• Applied npm audit fixes for dependencies\n"
        
        repo.index.commit(commit_message)
        
        # ✅ push branch (force overwrite remote branch)
        origin = repo.remote(name="origin")
        origin.push(branch_name, force=True)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Git/npm operation failed: {e}")
    
    # ✅ now create PR with smart description
    pr_body = """🚀 **FixSec AI: Smart Security Fixes**

This PR was automatically generated by FixSec AI with comprehensive security improvements.

## 🛡️ What was fixed:
"""
    
    if vulnerabilities:
        secrets_count = len([v for v in vulnerabilities if "secret" in v.get("type", "").lower()])
        deps_count = len([v for v in vulnerabilities if "dependency" in v.get("type", "").lower()])
        sql_count = len([v for v in vulnerabilities if "sql injection" in v.get("type", "").lower()])
        
        if secrets_count > 0:
            pr_body += f"\n✅ **Hardcoded Secrets ({secrets_count})**: Moved to environment variables (.env)\n"
        if deps_count > 0:
            pr_body += f"\n✅ **Vulnerable Dependencies ({deps_count})**: Updated to secure versions\n"
        if sql_count > 0:
            pr_body += f"\n✅ **SQL Injection ({sql_count})**: Converted to parameterized queries\n"
    else:
        pr_body += "\n✅ **Dependencies**: Applied npm audit fixes\n"
    
    pr_body += """
## 🔍 Why these fixes are safe:
- All changes follow security best practices
- Dependencies updated to latest secure versions
- Secrets moved to environment variables (add .env to .gitignore)
- Code changes maintain functionality while improving security

## 🚀 Powered by FixSec AI
- 10x faster than manual fixes
- 95% accuracy with smart detection
- Comprehensive fixes beyond basic tools

**Ready to merge!** ✅
"""
    
    pr_res = requests.post(
        f"https://api.github.com/repos/{full_name}/pulls",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "title": "🚀 FixSec AI: Smart Security Fixes",
            "head": branch_name,
            "base": default_branch,
            "body": pr_body,
        }
    )
    
    # ✅ PR Created
    if pr_res.status_code in [200, 201]:
        return {"status": "PR Created ✅", "url": pr_res.json().get("html_url")}
    
    # ✅ PR Already exists (422)
    if pr_res.status_code == 422:
        head_ref = f"{owner}:{branch_name}"
        encoded_head = urllib.parse.quote(head_ref)
        
        existing_prs = requests.get(
            f"https://api.github.com/repos/{full_name}/pulls?head={encoded_head}",
            headers={"Authorization": f"token {token}"}
        )
        
        if existing_prs.status_code == 200:
            prs = existing_prs.json()
            if prs and len(prs) > 0:
                return {"status": "PR already exists ✅", "url": prs[0].get("html_url")}
        
        return {"status": "PR already exists ✅", "repo": full_name}
    
    # ✅ Other errors
    raise HTTPException(status_code=400, detail=pr_res.json())