"""
Fix Plan Generator - Analyzes vulnerabilities and creates detailed fix plans
This gives users confidence about what changes will be made
"""
import os
import json
import subprocess
from typing import List, Dict, Any

def analyze_npm_fixes(repo_path: str) -> List[Dict[str, Any]]:
    """Analyze what npm audit fix will change"""
    package_json = os.path.join(repo_path, "package.json")
    if not os.path.exists(package_json):
        return []
    
    fixes = []
    
    try:
        # Get current package.json
        with open(package_json, 'r') as f:
            current_deps = json.load(f).get('dependencies', {})
        
        # Run npm audit to get vulnerability details
        audit_result = subprocess.run(
            ["cmd", "/c", "npm", "audit", "--json"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if audit_result.stdout:
            audit_data = json.loads(audit_result.stdout)
            vulnerabilities = audit_data.get("vulnerabilities", {})
            
            for pkg_name, vuln_info in vulnerabilities.items():
                severity = vuln_info.get("severity", "unknown").upper()
                via = vuln_info.get("via", [])
                
                # Get current version
                current_version = current_deps.get(pkg_name, "unknown")
                
                # Simulate what npm audit fix would do
                fix_available = vuln_info.get("fixAvailable", {})
                if fix_available:
                    new_version = fix_available.get("version", "latest")
                    
                    fixes.append({
                        "type": "dependency_update",
                        "package": pkg_name,
                        "current_version": current_version,
                        "new_version": new_version,
                        "severity": severity,
                        "reason": f"Fixes {len(via)} security vulnerabilities",
                        "description": f"Update {pkg_name} from {current_version} to {new_version}",
                        "impact": "Security vulnerability patched"
                    })
    
    except Exception as e:
        print(f"⚠️ Fix analysis error: {e}")
    
    return fixes

def analyze_secret_fixes(repo_path: str, vulnerabilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Analyze what secret fixes would be needed"""
    fixes = []
    
    secret_vulns = [v for v in vulnerabilities if v.get("type") == "Hardcoded Secret"]
    
    for vuln in secret_vulns:
        file_path = vuln.get("file", "")
        line_num = vuln.get("line", 0)
        
        fixes.append({
            "type": "secret_removal",
            "file": file_path,
            "line": line_num,
            "severity": vuln.get("severity", "HIGH"),
            "reason": "Remove hardcoded secret",
            "description": f"Remove or encrypt secret in {file_path}:{line_num}",
            "impact": "Prevents credential exposure",
            "action": "Manual review required - secrets should be moved to environment variables"
        })
    
    return fixes

def generate_fix_plan(repo_path: str, vulnerabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate comprehensive fix plan for all vulnerabilities"""
    
    # Analyze different types of fixes
    npm_fixes = analyze_npm_fixes(repo_path)
    secret_fixes = analyze_secret_fixes(repo_path, vulnerabilities)
    
    all_fixes = npm_fixes + secret_fixes
    
    # Calculate impact summary
    total_fixes = len(all_fixes)
    auto_fixes = len([f for f in all_fixes if f["type"] == "dependency_update"])
    manual_fixes = len([f for f in all_fixes if f["type"] == "secret_removal"])
    
    # Severity breakdown
    severity_counts = {}
    for fix in all_fixes:
        sev = fix.get("severity", "UNKNOWN")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    
    # ✅ Clear messaging about what can be auto-fixed
    auto_fix_message = ""
    if auto_fixes > 0 and manual_fixes > 0:
        auto_fix_message = f"Can auto-fix {auto_fixes} dependency issues. {manual_fixes} secrets require manual review."
    elif auto_fixes > 0:
        auto_fix_message = f"Can auto-fix all {auto_fixes} dependency vulnerabilities."
    elif manual_fixes > 0:
        auto_fix_message = f"All {manual_fixes} issues are secrets that require manual review."
    else:
        auto_fix_message = "No fixable vulnerabilities found."
    
    return {
        "total_fixes": total_fixes,
        "auto_fixes": auto_fixes,
        "manual_fixes": manual_fixes,
        "severity_breakdown": severity_counts,
        "fixes": all_fixes,
        "summary": {
            "can_auto_fix": auto_fixes > 0,
            "requires_manual": manual_fixes > 0,
            "estimated_time": f"{auto_fixes * 2 + manual_fixes * 10} minutes",
            "risk_reduction": calculate_risk_reduction(all_fixes),
            "auto_fix_message": auto_fix_message,
            "limitations": get_auto_fix_limitations(auto_fixes, manual_fixes)
        }
    }

def get_auto_fix_limitations(auto_fixes: int, manual_fixes: int) -> List[str]:
    """Get clear messaging about auto-fix limitations"""
    limitations = []
    
    if auto_fixes > 0:
        limitations.append("✅ Dependency vulnerabilities: Automatically fixed with npm audit fix")
    
    if manual_fixes > 0:
        limitations.append("⚠️ Hardcoded secrets: Manual review required (auto-fix coming soon)")
        limitations.append("💡 Secrets should be moved to environment variables")
    
    if auto_fixes == 0 and manual_fixes == 0:
        limitations.append("ℹ️ No vulnerabilities detected that can be automatically fixed")
    
    return limitations

def calculate_risk_reduction(fixes: List[Dict[str, Any]]) -> str:
    """Calculate estimated risk reduction percentage"""
    total_risk = 0
    
    severity_weights = {
        "CRITICAL": 10,
        "HIGH": 7,
        "MEDIUM": 4,
        "LOW": 1
    }
    
    for fix in fixes:
        severity = fix.get("severity", "LOW")
        total_risk += severity_weights.get(severity, 1)
    
    if total_risk == 0:
        return "0%"
    elif total_risk <= 5:
        return "25-40%"
    elif total_risk <= 15:
        return "50-70%"
    else:
        return "70-90%"