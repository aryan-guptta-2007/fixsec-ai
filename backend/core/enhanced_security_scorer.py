"""
Enhanced Security Scoring System
"Security Score that actually matters" - based on real risk impact
"""
from typing import Dict, List, Any, Tuple
from datetime import datetime

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
        # Base score starts at 100
        score = 100.0
        impact_breakdown = {
            "secrets": {"deduction": 0, "count": 0, "impact": "CRITICAL"},
            "dependencies": {"deduction": 0, "count": 0, "impact": "HIGH"},
            "sql_injection": {"deduction": 0, "count": 0, "impact": "CRITICAL"},
            "config_issues": {"deduction": 0, "count": 0, "impact": "MEDIUM"},
            "other": {"deduction": 0, "count": 0, "impact": "LOW"}
        }
        
        # Process each vulnerability with smart weighting
        for vuln in vulnerabilities:
            deduction, category = self._calculate_vulnerability_impact(vuln)
            score -= deduction
            impact_breakdown[category]["deduction"] += deduction
            impact_breakdown[category]["count"] += 1
        
        # Apply repository context multipliers
        score = self._apply_context_multipliers(score, vulnerabilities)
        
        # Ensure score is between 0-100
        score = max(0, min(100, score))
        
        # Calculate grade
        grade = self._calculate_grade(score)
        
        # Generate actionable recommendations
        recommendations = self._generate_smart_recommendations(impact_breakdown, score)
        
        return {
            "score": round(score, 1),
            "grade": grade,
            "impact_breakdown": impact_breakdown,
            "recommendations": recommendations,
            "next_best_fixes": self._get_next_best_fixes(impact_breakdown),
            "time_to_a_plus": self._estimate_time_to_a_plus(impact_breakdown),
            "risk_level": self._get_overall_risk_level(score)
        }
    
    def _calculate_vulnerability_impact(self, vuln: Dict) -> Tuple[float, str]:
        """
        Calculate impact score for individual vulnerability
        Based on real-world exploitation likelihood and damage
        """
        vuln_type = vuln.get("type", "").lower()
        severity = vuln.get("severity", "").upper()
        confidence = vuln.get("confidence_score", 50)
        file_path = vuln.get("file_path", "")
        
        # Base impact by vulnerability type (real-world impact)
        if "secret" in vuln_type or "hardcoded" in vuln_type:
            base_impact = self._calculate_secret_impact(vuln)
            category = "secrets"
        elif "dependency" in vuln_type or "insecure dependency" in vuln_type:
            base_impact = self._calculate_dependency_impact(vuln)
            category = "dependencies"
        elif "sql injection" in vuln_type:
            base_impact = self._calculate_sql_injection_impact(vuln)
            category = "sql_injection"
        elif "config" in vuln_type or "cors" in vuln_type:
            base_impact = self._calculate_config_impact(vuln)
            category = "config_issues"
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
        message = vuln.get("message", "").lower()
        
        # Production API keys = maximum impact
        if any(key in message for key in ["sk_live_", "prod", "production"]):
            return 25.0  # Huge impact
        
        # Test/development keys = high impact
        elif any(key in message for key in ["sk_test_", "dev", "development"]):
            return 15.0
        
        # Database credentials = critical impact
        elif any(key in message for key in ["password", "db_", "database"]):
            return 20.0
        
        # JWT secrets = high impact
        elif "jwt" in message:
            return 18.0
        
        # Generic secrets = medium-high impact
        else:
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
    
    def _calculate_config_impact(self, vuln: Dict) -> float:
        """
        Calculate impact for configuration issues
        Usually medium impact but can be serious
        """
        message = vuln.get("message", "").lower()
        
        if "cors" in message:
            return 8.0
        elif "jwt" in message:
            return 10.0
        elif "ssl" in message or "tls" in message:
            return 12.0
        else:
            return 6.0
    
    def _get_file_criticality_multiplier(self, file_path: str) -> float:
        """
        Adjust impact based on file criticality
        """
        file_path = file_path.lower()
        
        # Test files = lower impact
        if any(test in file_path for test in ["/test/", "/tests/", ".test.", ".spec."]):
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
    
    def _apply_context_multipliers(self, score: float, vulnerabilities: List[Dict]) -> float:
        """
        Apply repository context to adjust score
        Public repos = higher risk, Private repos = lower risk
        """
        is_public = self.repo_info.get("private", True) == False
        has_many_stars = self.repo_info.get("stargazers_count", 0) > 100
        
        # Public repositories with many stars = higher risk
        if is_public and has_many_stars:
            # Reduce score more for public repos (higher risk)
            multiplier = 0.9
        elif is_public:
            multiplier = 0.95
        else:
            # Private repos = slightly less risk
            multiplier = 1.02
        
        return score * multiplier
    
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
        
        if impact_breakdown["config_issues"]["count"] > 0:
            recommendations.append(
                f"📋 MEDIUM: Fix {impact_breakdown['config_issues']['count']} configuration issues. "
                "Apply secure configuration defaults."
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
                "auto_fixable": True
            },
            "config_issues": {
                "title": "Apply secure configuration",
                "impact": f"+{data['deduction']:.1f} points",
                "difficulty": "Easy",
                "time": "3 minutes",
                "auto_fixable": True
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
            return "Already A+ grade!"
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