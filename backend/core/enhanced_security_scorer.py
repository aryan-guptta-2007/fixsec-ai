"""
Enhanced Security Scoring System
"Security Score that actually matters" - based on real risk impact
"""
from typing import Dict, List, Any, Tuple

from core.scanner.files import is_test_path


# npm reports every transitive package separately, so one outdated framework can
# produce dozens of findings. Past this point, more of them say little new.
DEPENDENCY_DEDUCTION_CAP = 50.0


class EnhancedSecurityScorer:
    """
    Advanced security scoring that considers real-world impact
    Not just random numbers - actual risk-based scoring
    """
    
    def __init__(self, repo_info: Dict[str, Any] = None):
        self.repo_info = repo_info or {}
        
    def calculate_comprehensive_score(self, vulnerabilities: List[Dict]) -> Dict[str, Any]:
        """
        Calculate security score based on real impact factors
        Returns score, grade, and actionable recommendations
        """
        impact_breakdown = {
            "secrets": {"deduction": 0.0, "count": 0, "impact": "CRITICAL"},
            "dependencies": {"deduction": 0.0, "count": 0, "impact": "HIGH"},
            "sql_injection": {"deduction": 0.0, "count": 0, "impact": "CRITICAL"},
            "other": {"deduction": 0.0, "count": 0, "impact": "LOW"},
        }
        severity_breakdown: Dict[str, int] = {}
        exposure = self._exposure_multiplier()

        for vuln in vulnerabilities:
            deduction, category = self._calculate_vulnerability_impact(vuln)
            impact_breakdown[category]["deduction"] += deduction * exposure
            impact_breakdown[category]["count"] += 1
            severity = vuln.get("severity", "UNKNOWN")
            severity_breakdown[severity] = severity_breakdown.get(severity, 0) + 1

        dependencies = impact_breakdown["dependencies"]
        dependencies["deduction"] = min(dependencies["deduction"], DEPENDENCY_DEDUCTION_CAP)

        total_deduction = sum(item["deduction"] for item in impact_breakdown.values())
        score = max(0.0, 100.0 - total_deduction)

        for item in impact_breakdown.values():
            item["deduction"] = round(item["deduction"], 1)

        return {
            "score": round(score, 1),
            "grade": self._calculate_grade(score),
            "impact_breakdown": impact_breakdown,
            "severity_breakdown": severity_breakdown,
            "total_vulnerabilities": len(vulnerabilities),
            "recommendations": self._generate_smart_recommendations(impact_breakdown, score),
            "next_best_fixes": self._get_next_best_fixes(impact_breakdown),
            "time_to_a_plus": self._estimate_time_to_a_plus(impact_breakdown),
            "risk_level": self._get_overall_risk_level(score),
        }

    def _calculate_vulnerability_impact(self, vuln: Dict) -> Tuple[float, str]:
        """
        Calculate impact score for individual vulnerability
        Based on real-world exploitation likelihood and damage
        """
        category_name = vuln.get("category")
        confidence = vuln.get("confidence_score", 50)
        file_path = vuln.get("file_path", "")

        if category_name == "secret":
            base_impact = self._calculate_secret_impact(vuln)
            category = "secrets"
        elif category_name == "dependency":
            base_impact = self._calculate_dependency_impact(vuln)
            category = "dependencies"
        elif category_name == "sql_injection":
            base_impact = self._calculate_sql_injection_impact(vuln)
            category = "sql_injection"
        else:
            base_impact = 5.0
            category = "other"

        # Adjust by confidence (low confidence = lower impact)
        confidence_multiplier = confidence / 100.0
        
        # Adjust by file criticality
        file_multiplier = self._get_file_criticality_multiplier(file_path)
        
        final_impact = base_impact * confidence_multiplier * file_multiplier
        
        return final_impact, category
    
    def _calculate_secret_impact(self, vuln: Dict) -> float:
        """
        Calculate impact for hardcoded secrets
        Secrets are CRITICAL - can lead to complete compromise
        """
        secret_type = vuln.get("type", "").lower()

        if vuln.get("severity") == "CRITICAL":
            return 25.0  # live keys and private keys
        if "password" in secret_type:
            return 20.0
        if "test" in secret_type:
            return 15.0
        if "potential" in secret_type:
            return 8.0
        return 12.0

    def _calculate_dependency_impact(self, vuln: Dict) -> float:
        """
        Calculate impact for vulnerable dependencies
        Based on exploitability and attack surface
        """
        severity = vuln.get("severity", "").upper()
        package = vuln.get("package", "").lower()
        
        # Critical dependencies with known exploits
        if severity == "CRITICAL":
            return 15.0
        elif severity == "HIGH":
            return 10.0
        elif severity == "MEDIUM":
            return 6.0
        else:  # LOW
            return 3.0
    
    def _calculate_sql_injection_impact(self, vuln: Dict) -> float:
        """
        Calculate impact for SQL injection vulnerabilities
        SQL injection = potential data breach
        """
        file_path = vuln.get("file_path", "").lower()
        
        # Production database queries = maximum impact
        if any(indicator in file_path for indicator in ["prod", "api", "server"]):
            return 22.0
        
        # Regular database queries = high impact
        else:
            return 18.0
    
    def _get_file_criticality_multiplier(self, file_path: str) -> float:
        """
        Adjust impact based on file criticality
        """
        file_path = file_path.lower()
        
        # Test files = lower impact
        if is_test_path(file_path):
            return 0.3
        
        # Config files = higher impact
        elif any(config in file_path for config in ["config", "env", "settings"]):
            return 1.5
        
        # API/server files = higher impact
        elif any(api in file_path for api in ["api", "server", "route", "controller"]):
            return 1.3
        
        # Database files = higher impact
        elif any(db in file_path for db in ["db", "database", "model", "schema"]):
            return 1.4
        
        # Regular files = normal impact
        else:
            return 1.0
    
    def _exposure_multiplier(self) -> float:
        """Issues in public repositories are easier to find and exploit."""
        if self.repo_info.get("private", True):
            return 0.9
        if self.repo_info.get("stargazers_count", 0) > 100:
            return 1.2
        return 1.1

    def _calculate_grade(self, score: float) -> str:
        """
        Convert score to letter grade
        """
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "A-"
        elif score >= 80:
            return "B+"
        elif score >= 75:
            return "B"
        elif score >= 70:
            return "B-"
        elif score >= 65:
            return "C+"
        elif score >= 60:
            return "C"
        elif score >= 55:
            return "C-"
        elif score >= 50:
            return "D+"
        elif score >= 45:
            return "D"
        elif score >= 40:
            return "D-"
        else:
            return "F"
    
    def _generate_smart_recommendations(self, impact_breakdown: Dict, score: float) -> List[str]:
        """
        Generate actionable recommendations based on actual issues
        """
        recommendations = []
        
        # Prioritize by impact
        if impact_breakdown["secrets"]["count"] > 0:
            recommendations.append(
                f"🚨 CRITICAL: Fix {impact_breakdown['secrets']['count']} hardcoded secrets immediately. "
                "These can lead to complete system compromise."
            )
        
        if impact_breakdown["sql_injection"]["count"] > 0:
            recommendations.append(
                f"🚨 CRITICAL: Fix {impact_breakdown['sql_injection']['count']} SQL injection vulnerabilities. "
                "These can lead to data breaches."
            )
        
        if impact_breakdown["dependencies"]["count"] > 0:
            recommendations.append(
                f"⚠️ HIGH: Update {impact_breakdown['dependencies']['count']} vulnerable dependencies. "
                "Run 'npm audit fix' to resolve automatically."
            )
        
        # Score-based recommendations
        if score < 50:
            recommendations.append("🔥 Your repository has critical security issues that need immediate attention.")
        elif score < 70:
            recommendations.append("⚠️ Your repository has several security issues that should be addressed soon.")
        elif score < 85:
            recommendations.append("📈 Your repository is fairly secure but has room for improvement.")
        else:
            recommendations.append("✅ Your repository has good security practices!")
        
        return recommendations
    
    def _get_next_best_fixes(self, impact_breakdown: Dict) -> List[Dict[str, Any]]:
        """
        Get the top 3 fixes that will improve score the most
        Gamification element to encourage fixing
        """
        fixes = []
        
        # Sort by impact
        sorted_categories = sorted(
            impact_breakdown.items(),
            key=lambda x: x[1]["deduction"],
            reverse=True
        )
        
        for category, data in sorted_categories[:3]:
            if data["count"] > 0:
                fix_info = self._get_fix_info(category, data)
                fixes.append(fix_info)
        
        return fixes
    
    def _get_fix_info(self, category: str, data: Dict) -> Dict[str, Any]:
        """
        Get fix information for a category
        """
        fix_map = {
            "secrets": {
                "title": "Move secrets to environment variables",
                "impact": f"+{data['deduction']:.1f} points",
                "difficulty": "Easy",
                "time": "5 minutes",
                "auto_fixable": True
            },
            "dependencies": {
                "title": "Update vulnerable dependencies",
                "impact": f"+{data['deduction']:.1f} points",
                "difficulty": "Easy",
                "time": "2 minutes",
                "auto_fixable": True
            },
            "sql_injection": {
                "title": "Use parameterized queries",
                "impact": f"+{data['deduction']:.1f} points",
                "difficulty": "Medium",
                "time": "10 minutes",
                "auto_fixable": False
            }
        }

        return fix_map.get(category, {
            "title": "Fix security issues",
            "impact": f"+{data['deduction']:.1f} points",
            "difficulty": "Medium",
            "time": "5 minutes",
            "auto_fixable": False
        })
    
    def _estimate_time_to_a_plus(self, impact_breakdown: Dict) -> str:
        """
        Estimate time to reach A+ grade
        Gamification element
        """
        total_fixes = sum(data["count"] for data in impact_breakdown.values())
        
        if total_fixes == 0:
            return "Already there"
        elif total_fixes <= 3:
            return "10-15 minutes"
        elif total_fixes <= 7:
            return "20-30 minutes"
        else:
            return "45-60 minutes"
    
    def _get_overall_risk_level(self, score: float) -> str:
        """
        Get overall risk level based on score
        """
        if score >= 85:
            return "LOW"
        elif score >= 70:
            return "MEDIUM"
        elif score >= 50:
            return "HIGH"
        else:
            return "CRITICAL"

def get_enhanced_security_scorer(repo_info: Dict = None) -> EnhancedSecurityScorer:
    """Factory function to create EnhancedSecurityScorer instance"""
    return EnhancedSecurityScorer(repo_info)