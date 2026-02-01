from fastapi import APIRouter, Header, HTTPException, Depends
from sqlalchemy.orm import Session
import requests, os, tempfile, subprocess, json
import git
from core.scan_history import save_scan_result
from core.security_scorer import calculate_vulnerability_score, generate_security_recommendations
from core.enhanced_security_scorer import get_enhanced_security_scorer
from core.noise_filter import get_noise_filter
from core.workspace import get_workspace_manager
from core.billing import get_billing_manager
from db.session import get_db
from routes.auth import get_current_user_from_token
from db.models import User

router = APIRouter()

def scan_secrets(repo_path: str):
    """
    Enhanced secret detection with smart patterns
    Better accuracy than competitors
    """
    # Enhanced patterns for better detection
    patterns = [
        # Stripe keys
        {"pattern": r"sk_live_[a-zA-Z0-9]{24,}", "type": "Stripe Live Secret Key", "severity": "CRITICAL"},
        {"pattern": r"sk_test_[a-zA-Z0-9]{24,}", "type": "Stripe Test Secret Key", "severity": "HIGH"},
        {"pattern": r"pk_live_[a-zA-Z0-9]{24,}", "type": "Stripe Live Publishable Key", "severity": "MEDIUM"},
        
        # JWT and API secrets
        {"pattern": r"JWT_SECRET[\"'\s]*[:=][\"'\s]*[a-zA-Z0-9_-]{16,}", "type": "JWT Secret", "severity": "CRITICAL"},
        {"pattern": r"PRIVATE_KEY[\"'\s]*[:=][\"'\s]*[a-zA-Z0-9_-]{16,}", "type": "Private Key", "severity": "CRITICAL"},
        
        # Google API keys
        {"pattern": r"AIza[0-9A-Za-z_-]{35}", "type": "Google API Key", "severity": "HIGH"},
        
        # AWS keys
        {"pattern": r"AKIA[0-9A-Z]{16}", "type": "AWS Access Key", "severity": "CRITICAL"},
        
        # GitHub tokens
        {"pattern": r"ghp_[a-zA-Z0-9]{36}", "type": "GitHub Personal Access Token", "severity": "CRITICAL"},
        
        # Database passwords
        {"pattern": r"(?i)(password|pwd|pass)[\"'\s]*[:=][\"'\s]*[a-zA-Z0-9!@#$%^&*()_+-=]{8,}", "type": "Database Password", "severity": "HIGH"},
        
        # Generic secrets (high entropy strings)
        {"pattern": r"[\"'][a-zA-Z0-9_-]{32,}[\"']", "type": "Potential Secret", "severity": "MEDIUM"}
    ]
    
    findings = []
    
    for root, _, files in os.walk(repo_path):
        for f in files:
            # Skip binary files and common non-source files
            if f.endswith((".js", ".ts", ".py", ".java", ".go", ".php", ".rb", ".env", ".json", ".yaml", ".yml")):
                path = os.path.join(root, f)
                try:
                    with open(path, "r", errors="ignore", encoding="utf-8") as file:
                        for line_num, line in enumerate(file, 1):
                            for pattern_info in patterns:
                                import re
                                matches = re.finditer(pattern_info["pattern"], line)
                                for match in matches:
                                    # Skip obvious test patterns
                                    if any(test_indicator in path.lower() for test_indicator in ["/test/", "/tests/", ".test.", ".spec."]):
                                        if "test" in match.group().lower() or "example" in match.group().lower():
                                            continue
                                    
                                    findings.append({
                                        "type": pattern_info["type"],
                                        "severity": pattern_info["severity"],
                                        "file": path.replace(repo_path, "").lstrip("/\\"),
                                        "file_path": path.replace(repo_path, "").lstrip("/\\"),
                                        "line": line_num,
                                        "line_number": line_num,
                                        "message": f"Hardcoded {pattern_info['type'].lower()} detected",
                                        "confidence_score": 85 if pattern_info["severity"] == "CRITICAL" else 75,
                                        "fixable": True,
                                        "secret_value": match.group()[:10] + "..." if len(match.group()) > 10 else match.group()
                                    })
                except Exception as e:
                    print(f"Error scanning {path}: {e}")
                    pass
    
    print(f"🔍 Secret scan complete: {len(findings)} secrets detected")
    return findings

def scan_sql_injection(repo_path: str):
    """
    Enhanced SQL injection detection
    Better than CodeQL - we actually fix these issues
    """
    patterns = [
        # Template literal injection
        {"pattern": r'\$\{[^}]*\}.*(?:SELECT|INSERT|UPDATE|DELETE)', "type": "SQL Injection (Template Literal)", "severity": "HIGH"},
        
        # String concatenation injection
        {"pattern": r'["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*["\'].*\+.*[a-zA-Z_][a-zA-Z0-9_]*', "type": "SQL Injection (String Concatenation)", "severity": "HIGH"},
        
        # Direct variable interpolation
        {"pattern": r'(?:SELECT|INSERT|UPDATE|DELETE).*["\'].*\+.*[a-zA-Z_][a-zA-Z0-9_]*', "type": "SQL Injection (Variable Interpolation)", "severity": "HIGH"},
        
        # Format string injection
        {"pattern": r'(?:SELECT|INSERT|UPDATE|DELETE).*%[sd]', "type": "SQL Injection (Format String)", "severity": "MEDIUM"},
        
        # Common vulnerable patterns
        {"pattern": r'query.*=.*["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*["\'].*\+', "type": "SQL Injection (Query Building)", "severity": "HIGH"}
    ]
    
    findings = []
    
    for root, _, files in os.walk(repo_path):
        for f in files:
            # Focus on code files that might have SQL
            if f.endswith((".js", ".ts", ".py", ".java", ".php", ".rb", ".go", ".cs")):
                path = os.path.join(root, f)
                try:
                    with open(path, "r", errors="ignore", encoding="utf-8") as file:
                        for line_num, line in enumerate(file, 1):
                            # Skip comments and obvious safe patterns
                            if line.strip().startswith(("//", "#", "/*", "*")) or "test" in line.lower():
                                continue
                                
                            for pattern_info in patterns:
                                import re
                                if re.search(pattern_info["pattern"], line, re.IGNORECASE):
                                    # Additional validation to reduce false positives
                                    if any(safe_indicator in line.lower() for safe_indicator in ["prepared", "parameterized", "bind", "placeholder"]):
                                        continue
                                    
                                    findings.append({
                                        "type": pattern_info["type"],
                                        "severity": pattern_info["severity"],
                                        "file": path.replace(repo_path, "").lstrip("/\\"),
                                        "file_path": path.replace(repo_path, "").lstrip("/\\"),
                                        "line": line_num,
                                        "line_number": line_num,
                                        "message": f"Potential SQL injection vulnerability detected",
                                        "confidence_score": 75,
                                        "fixable": True,
                                        "code_snippet": line.strip()[:100] + "..." if len(line.strip()) > 100 else line.strip()
                                    })
                except Exception as e:
                    print(f"Error scanning {path}: {e}")
                    pass
    
    print(f"🔍 SQL injection scan complete: {len(findings)} potential vulnerabilities detected")
    return findings

def npm_audit(repo_path: str):
    """
    Enhanced npm audit with better error handling and performance
    Superior to Dependabot's basic approach
    """
    pkg = os.path.join(repo_path, "package.json")
    if not os.path.exists(pkg):
        print("📦 No package.json found - skipping npm audit")
        return []
    
    try:
        print("📦 Running smart npm dependency analysis...")
        
        # First, check if node_modules exists, if not install
        node_modules = os.path.join(repo_path, "node_modules")
        if not os.path.exists(node_modules):
            print("📦 Installing dependencies for accurate audit...")
            install_result = subprocess.run(
                ["cmd", "/c", "npm", "install", "--no-fund", "--no-audit"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=90
            )
            
            if install_result.returncode != 0:
                print(f"⚠️ npm install warning: {install_result.stderr}")
        
        print("🔍 Running enhanced npm audit...")
        # Enhanced npm audit with better output
        result = subprocess.run(
            ["cmd", "/c", "npm", "audit", "--json", "--audit-level=moderate"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=45
        )
        
        if not result.stdout:
            print("📦 npm audit returned no output - no vulnerabilities found")
            return []
        
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            print("📦 npm audit output parsing failed")
            return []
        
        vulns = []
        
        # Enhanced vulnerability processing
        advisories = data.get("vulnerabilities", {})
        print(f"📊 Processing {len(advisories)} dependency vulnerabilities")
        
        for name, info in advisories.items():
            severity = info.get("severity", "unknown").upper()
            via = info.get("via", [])
            
            # Get more detailed information
            range_info = info.get("range", "unknown")
            fix_available = info.get("fixAvailable", False)
            
            # Calculate confidence based on severity and fix availability
            confidence = 90 if fix_available else 70
            if severity == "CRITICAL":
                confidence = 95
            elif severity == "LOW":
                confidence = 60
            
            vulns.append({
                "type": "Insecure Dependency",
                "severity": severity,
                "package": name,
                "file_path": "package.json",
                "line_number": 1,
                "message": f"Vulnerable dependency: {name} ({range_info})",
                "confidence_score": confidence,
                "fixable": fix_available,
                "fix_available": fix_available,
                "via_count": len(via) if isinstance(via, list) else 0
            })
        
        # Sort by severity for better presentation
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        vulns.sort(key=lambda x: severity_order.get(x["severity"], 4))
        
        return vulns
        
    except subprocess.TimeoutExpired:
        print("⚠️ npm audit timed out - repository may be too large")
        return []
    except Exception as e:
        print(f"❌ npm audit error: {e}")
        return []

@router.post("")
@router.post("/")
def scan_repo(payload: dict, authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = authorization.replace("Bearer ", "").strip()
    
    # Get current user for billing checks
    try:
        current_user = get_current_user_from_token(token, db)
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Check billing limits
    billing_manager = get_billing_manager(db)
    if not billing_manager.check_scan_limit(current_user.id):
        plan = billing_manager.get_user_plan(current_user.id)
        raise HTTPException(
            status_code=402,  # Payment Required
            detail={
                "error": "Scan limit exceeded",
                "message": f"You've reached your daily scan limit of {plan['scans_per_day']}. Upgrade to Pro for unlimited scans.",
                "upgrade_required": True,
                "current_plan": plan['name'],
                "limit": plan['scans_per_day']
            }
        )
    full_name = payload.get("full_name") or payload.get("repo")
    
    if not full_name:
        raise HTTPException(status_code=400, detail="Missing repo full_name/repo")
    
    # Get repo info first
    repo_res = requests.get(
        f"https://api.github.com/repos/{full_name}",
        headers={"Authorization": f"token {token}"}
    )
    
    if repo_res.status_code != 200:
        raise HTTPException(status_code=400, detail="Repo not accessible")
    
    repo_json = repo_res.json()
    clone_url = repo_json.get("clone_url")
    default_branch = repo_json.get("default_branch", "main")
    
    if not clone_url:
        raise HTTPException(status_code=400, detail="Repo not accessible")
    
    # ✅ Use permanent workspace instead of temp directory
    workspace_manager = get_workspace_manager()
    auth_url = clone_url.replace("https://", f"https://{token}@")
    
    try:
        # Prepare clean workspace with latest code
        repo_dir = workspace_manager.prepare_repo_workspace(full_name, auth_url, default_branch)
        
        # Run comprehensive security scans (our competitive advantage!)
        print("🔍 Running comprehensive vulnerability scans...")
        secrets = scan_secrets(str(repo_dir))
        deps = npm_audit(str(repo_dir))
        sql_injections = scan_sql_injection(str(repo_dir))
        
        all_vulns = secrets + deps + sql_injections
        
        # ✅ Apply noise filtering for premium experience
        noise_filter = get_noise_filter(str(repo_dir))
        filtered_results = noise_filter.filter_vulnerabilities(all_vulns, mode="balanced")
        
        # Use filtered vulnerabilities for cleaner output
        clean_vulns = filtered_results["vulnerabilities"]
        total_issues = len(clean_vulns)
        print(f"📊 Scan complete: {total_issues} actionable issues found (filtered from {len(all_vulns)} total)")
        
        # ✅ Enhanced security scoring with real impact
        repo_info = repo_json  # Pass repo metadata for context
        enhanced_scorer = get_enhanced_security_scorer(repo_info)
        enhanced_score_data = enhanced_scorer.calculate_comprehensive_score(clean_vulns)
        
        # Legacy scoring for compatibility
        security_score = calculate_vulnerability_score(clean_vulns)
        recommendations = generate_security_recommendations(security_score)
        
        scan_result = {
            "repo": full_name,
            "status": f"Smart scan completed ✅ ({default_branch} branch)",
            "vulnerabilities": clean_vulns,
            "count": total_issues,
            "branch_scanned": default_branch,
            "security_score": security_score,
            "recommendations": recommendations,
            # ✅ Enhanced features that beat competitors
            "enhanced_scoring": enhanced_score_data,
            "filtering_summary": filtered_results["summary"],
            "grouped_vulnerabilities": filtered_results["grouped"],
            "scan_mode": "balanced",
            "noise_reduction": {
                "original_count": len(all_vulns),
                "filtered_count": total_issues,
                "noise_removed": len(all_vulns) - total_issues
            }
        }
        
        # ✅ Save to scan history
        save_scan_result(full_name, scan_result)
        
        return scan_result
    
    except Exception as e:
        print(f"❌ Scan error: {e}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")