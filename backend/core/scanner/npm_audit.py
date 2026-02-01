import subprocess
import json
import os
from typing import List, Dict

def run_npm_audit(repo_path: str) -> List[Dict]:
    """Run npm audit and parse vulnerabilities"""
    findings = []
    
    # Check if package.json exists
    package_json_path = os.path.join(repo_path, "package.json")
    if not os.path.exists(package_json_path):
        return findings
    
    try:
        # Run npm audit with JSON output
        result = subprocess.run(
            ["npm", "audit", "--json"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.stdout:
            audit_data = json.loads(result.stdout)
            
            # Parse vulnerabilities from npm audit output
            vulnerabilities = audit_data.get("vulnerabilities", {})
            
            for package_name, vuln_info in vulnerabilities.items():
                severity = vuln_info.get("severity", "unknown").upper()
                
                # Map npm severity to our severity levels
                severity_mapping = {
                    "INFO": "LOW",
                    "LOW": "LOW", 
                    "MODERATE": "MEDIUM",
                    "HIGH": "HIGH",
                    "CRITICAL": "CRITICAL"
                }
                
                mapped_severity = severity_mapping.get(severity, "MEDIUM")
                
                findings.append({
                    "type": "dependency",
                    "subtype": "vulnerable_package",
                    "severity": mapped_severity,
                    "file_path": "package.json",
                    "line_number": None,
                    "message": f"Vulnerable dependency: {package_name}",
                    "package_name": package_name,
                    "current_version": vuln_info.get("via", [{}])[0].get("range", "unknown"),
                    "fixable": vuln_info.get("fixAvailable", False),
                    "confidence_score": 90,
                    "cwe": vuln_info.get("via", [{}])[0].get("cwe", []),
                    "advisory_url": vuln_info.get("via", [{}])[0].get("url", "")
                })
                
    except subprocess.TimeoutExpired:
        print("npm audit timed out")
    except json.JSONDecodeError:
        print("Failed to parse npm audit output")
    except Exception as e:
        print(f"Error running npm audit: {e}")
    
    return findings

def check_outdated_packages(repo_path: str) -> List[Dict]:
    """Check for outdated packages that may have security updates"""
    findings = []
    
    try:
        # Run npm outdated with JSON output
        result = subprocess.run(
            ["npm", "outdated", "--json"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.stdout:
            outdated_data = json.loads(result.stdout)
            
            for package_name, package_info in outdated_data.items():
                current = package_info.get("current", "")
                wanted = package_info.get("wanted", "")
                latest = package_info.get("latest", "")
                
                # Focus on packages that are significantly outdated
                if current and latest and current != latest:
                    findings.append({
                        "type": "dependency",
                        "subtype": "outdated_package",
                        "severity": "LOW",
                        "file_path": "package.json",
                        "line_number": None,
                        "message": f"Outdated package: {package_name} (current: {current}, latest: {latest})",
                        "package_name": package_name,
                        "current_version": current,
                        "latest_version": latest,
                        "fixable": True,
                        "confidence_score": 85
                    })
                    
    except subprocess.TimeoutExpired:
        print("npm outdated timed out")
    except json.JSONDecodeError:
        pass  # npm outdated returns non-zero exit code when packages are outdated
    except Exception as e:
        print(f"Error running npm outdated: {e}")
    
    return findings

def generate_dependency_fix(finding: Dict) -> Dict:
    """Generate fix suggestion for dependency vulnerabilities"""
    package_name = finding.get("package_name", "")
    subtype = finding.get("subtype", "")
    
    if subtype == "vulnerable_package":
        if finding.get("fixable", False):
            return {
                "confidence": 90,
                "fix_type": "npm_audit_fix",
                "description": f"Run 'npm audit fix' to automatically update {package_name}",
                "changes": [
                    {
                        "action": "run_command",
                        "command": "npm audit fix",
                        "description": "Automatically fix vulnerable dependencies"
                    }
                ]
            }
        else:
            return {
                "confidence": 70,
                "fix_type": "manual_update",
                "description": f"Manually update {package_name} to a secure version",
                "changes": [
                    {
                        "action": "manual_review",
                        "description": f"Check {package_name} documentation for secure version and update manually"
                    }
                ]
            }
    
    elif subtype == "outdated_package":
        latest_version = finding.get("latest_version", "")
        return {
            "confidence": 85,
            "fix_type": "version_update",
            "description": f"Update {package_name} to latest version {latest_version}",
            "changes": [
                {
                    "action": "run_command",
                    "command": f"npm install {package_name}@{latest_version}",
                    "description": f"Update {package_name} to version {latest_version}"
                }
            ]
        }
    
    return {
        "confidence": 50,
        "fix_type": "manual_review",
        "description": "Manual review required for this dependency issue"
    }