"""
Noise-Free Security Output Engine
Makes FixSec AI feel premium by reducing false positives and noise
"""
import re
from typing import Dict, List, Any, Set
from pathlib import Path

class NoiseFilter:
    """
    Advanced filtering system to reduce noise and focus on actionable vulnerabilities
    This makes FixSec AI feel more premium than competitors
    """
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.ignore_rules = self._load_ignore_rules()
        
    def _load_ignore_rules(self) -> Dict[str, List[str]]:
        """Load .fixsecignore rules if they exist"""
        ignore_file = self.repo_path / ".fixsecignore"
        rules = {
            "files": [],
            "patterns": [],
            "vulnerabilities": []
        }
        
        if ignore_file.exists():
            with open(ignore_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if line.startswith('vuln:'):
                            rules["vulnerabilities"].append(line[5:])
                        elif '*' in line or '?' in line:
                            rules["patterns"].append(line)
                        else:
                            rules["files"].append(line)
        
        return rules
    
    def filter_vulnerabilities(self, vulnerabilities: List[Dict], mode: str = "balanced") -> Dict[str, Any]:
        """
        Filter vulnerabilities based on mode and rules
        Modes: 'all', 'balanced', 'exploitable_only'
        """
        filtered = {
            "vulnerabilities": [],
            "grouped": {},
            "summary": {
                "total_found": len(vulnerabilities),
                "after_filtering": 0,
                "duplicates_removed": 0,
                "false_positives_removed": 0
            }
        }
        
        # Step 1: Remove ignored items
        after_ignore = self._apply_ignore_rules(vulnerabilities)
        
        # Step 2: Remove duplicates and group similar issues
        deduplicated = self._remove_duplicates(after_ignore)
        
        # Step 3: Apply mode-specific filtering
        if mode == "exploitable_only":
            final_vulns = self._filter_exploitable_only(deduplicated)
        elif mode == "balanced":
            final_vulns = self._filter_balanced(deduplicated)
        else:  # mode == "all"
            final_vulns = deduplicated
        
        # Step 4: Group related vulnerabilities
        grouped = self._group_related_vulnerabilities(final_vulns)
        
        filtered["vulnerabilities"] = final_vulns
        filtered["grouped"] = grouped
        filtered["summary"]["after_filtering"] = len(final_vulns)
        filtered["summary"]["duplicates_removed"] = len(vulnerabilities) - len(deduplicated)
        
        return filtered
    
    def _apply_ignore_rules(self, vulnerabilities: List[Dict]) -> List[Dict]:
        """Apply .fixsecignore rules"""
        filtered = []
        
        for vuln in vulnerabilities:
            file_path = vuln.get("file_path", "")
            vuln_type = vuln.get("type", "")
            
            # Check file ignores
            if any(ignored_file in file_path for ignored_file in self.ignore_rules["files"]):
                continue
                
            # Check pattern ignores
            if any(self._matches_pattern(file_path, pattern) for pattern in self.ignore_rules["patterns"]):
                continue
                
            # Check vulnerability type ignores
            if any(ignored_vuln in vuln_type.lower() for ignored_vuln in self.ignore_rules["vulnerabilities"]):
                continue
            
            filtered.append(vuln)
        
        return filtered
    
    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches ignore pattern"""
        import fnmatch
        return fnmatch.fnmatch(file_path, pattern)
    
    def _remove_duplicates(self, vulnerabilities: List[Dict]) -> List[Dict]:
        """Remove duplicate vulnerabilities"""
        seen = set()
        unique = []
        
        for vuln in vulnerabilities:
            # Create unique key based on type, file, and line
            key = (
                vuln.get("type", ""),
                vuln.get("file_path", ""),
                vuln.get("line_number", 0),
                vuln.get("message", "")[:50]  # First 50 chars of message
            )
            
            if key not in seen:
                seen.add(key)
                unique.append(vuln)
        
        return unique
    
    def _filter_exploitable_only(self, vulnerabilities: List[Dict]) -> List[Dict]:
        """Filter to show only highly exploitable vulnerabilities"""
        exploitable = []
        
        for vuln in vulnerabilities:
            severity = vuln.get("severity", "").upper()
            vuln_type = vuln.get("type", "").lower()
            confidence = vuln.get("confidence_score", 0)
            
            # High priority: Critical/High severity with high confidence
            if severity in ["CRITICAL", "HIGH"] and confidence >= 80:
                exploitable.append(vuln)
            # Secrets are always exploitable
            elif "secret" in vuln_type and confidence >= 70:
                exploitable.append(vuln)
            # SQL injection is always serious
            elif "sql injection" in vuln_type and confidence >= 60:
                exploitable.append(vuln)
        
        return exploitable
    
    def _filter_balanced(self, vulnerabilities: List[Dict]) -> List[Dict]:
        """Balanced filtering - remove obvious false positives"""
        filtered = []
        
        for vuln in vulnerabilities:
            # Skip low confidence, low severity issues
            if (vuln.get("severity", "").upper() == "LOW" and 
                vuln.get("confidence_score", 0) < 50):
                continue
            
            # Skip test files for certain vulnerability types
            file_path = vuln.get("file_path", "")
            if self._is_test_file(file_path):
                vuln_type = vuln.get("type", "").lower()
                if vuln_type in ["hardcoded secret", "sql injection"]:
                    continue  # Test files often have fake secrets/queries
            
            filtered.append(vuln)
        
        return filtered
    
    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file"""
        test_indicators = [
            "/test/", "/tests/", "/__tests__/",
            ".test.", ".spec.", "_test.", "_spec.",
            "test_", "spec_"
        ]
        
        return any(indicator in file_path.lower() for indicator in test_indicators)
    
    def _group_related_vulnerabilities(self, vulnerabilities: List[Dict]) -> Dict[str, List[Dict]]:
        """Group related vulnerabilities for better presentation"""
        groups = {
            "secrets": [],
            "dependencies": [],
            "sql_injection": [],
            "config_issues": [],
            "other": []
        }
        
        for vuln in vulnerabilities:
            vuln_type = vuln.get("type", "").lower()
            
            if "secret" in vuln_type or "hardcoded" in vuln_type:
                groups["secrets"].append(vuln)
            elif "dependency" in vuln_type or "insecure dependency" in vuln_type:
                groups["dependencies"].append(vuln)
            elif "sql injection" in vuln_type:
                groups["sql_injection"].append(vuln)
            elif "config" in vuln_type or "cors" in vuln_type:
                groups["config_issues"].append(vuln)
            else:
                groups["other"].append(vuln)
        
        # Remove empty groups
        return {k: v for k, v in groups.items() if v}

def create_fixsecignore_template(repo_path: str):
    """Create a template .fixsecignore file"""
    ignore_file = Path(repo_path) / ".fixsecignore"
    
    template = """# FixSec AI Ignore Rules
# Ignore specific files
node_modules/
*.min.js
dist/
build/

# Ignore file patterns
test/**/*.js
spec/**/*.js
*.test.js
*.spec.js

# Ignore specific vulnerability types
vuln:test secret
vuln:demo data

# Ignore specific patterns in files
# Use this to ignore false positives
"""
    
    with open(ignore_file, 'w') as f:
        f.write(template)

def get_noise_filter(repo_path: str) -> NoiseFilter:
    """Factory function to create NoiseFilter instance"""
    return NoiseFilter(repo_path)