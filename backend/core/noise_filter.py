"""
Reduces scanner output to what is worth acting on: applies .fixsecignore rules,
removes duplicates, and drops likely-fake values in test code.
"""
import fnmatch
import logging
from pathlib import Path
from typing import Any, Dict, List

from core.scanner.files import is_test_path

logger = logging.getLogger(__name__)

GROUPS = {
    "secret": "secrets",
    "dependency": "dependencies",
    "sql_injection": "sql_injection",
}


class NoiseFilter:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.ignore_rules = self._load_ignore_rules()

    def _load_ignore_rules(self) -> Dict[str, List[str]]:
        """Load .fixsecignore: paths and globs, plus `vuln:<type>` lines."""
        rules: Dict[str, List[str]] = {"paths": [], "vulnerabilities": []}
        ignore_file = self.repo_path / ".fixsecignore"
        if not ignore_file.is_file():
            return rules
        try:
            content = ignore_file.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            logger.warning("Could not read .fixsecignore: %s", exc)
            return rules
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("vuln:"):
                rules["vulnerabilities"].append(line[5:].strip().lower())
            else:
                rules["paths"].append(line)
        return rules

    def filter_vulnerabilities(
        self, vulnerabilities: List[Dict[str, Any]], mode: str = "balanced"
    ) -> Dict[str, Any]:
        """Modes: 'all', 'balanced', 'exploitable_only'."""
        after_ignore = self._apply_ignore_rules(vulnerabilities)
        deduplicated = self._remove_duplicates(after_ignore)

        if mode == "exploitable_only":
            final = self._filter_exploitable_only(deduplicated)
        elif mode == "balanced":
            final = self._filter_balanced(deduplicated)
        else:
            final = deduplicated

        return {
            "vulnerabilities": final,
            "grouped": self._group(final),
            "summary": {
                "total_found": len(vulnerabilities),
                "after_filtering": len(final),
                "ignored_by_rules": len(vulnerabilities) - len(after_ignore),
                "duplicates_removed": len(after_ignore) - len(deduplicated),
                "false_positives_removed": len(deduplicated) - len(final),
            },
        }

    def _apply_ignore_rules(self, vulnerabilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        kept = []
        for vuln in vulnerabilities:
            file_path = vuln.get("file_path", "")
            vuln_type = vuln.get("type", "").lower()
            if any(self._matches_path(file_path, rule) for rule in self.ignore_rules["paths"]):
                continue
            if any(rule in vuln_type for rule in self.ignore_rules["vulnerabilities"]):
                continue
            kept.append(vuln)
        return kept

    @staticmethod
    def _matches_path(file_path: str, rule: str) -> bool:
        rule = rule.lstrip("/")
        if rule.startswith("./"):
            rule = rule[2:]
        if rule.endswith("/"):
            return file_path.startswith(rule) or f"/{rule}" in f"/{file_path}"
        name = file_path.rsplit("/", 1)[-1]
        return (
            file_path == rule
            or fnmatch.fnmatch(file_path, rule)
            or fnmatch.fnmatch(name, rule)
            or (rule.startswith("**/") and fnmatch.fnmatch(file_path, rule[3:]))
        )

    @staticmethod
    def _remove_duplicates(vulnerabilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for vuln in vulnerabilities:
            key = (
                vuln.get("category"),
                vuln.get("file_path"),
                vuln.get("line_number"),
                vuln.get("package") or vuln.get("secret_value"),
            )
            if key not in seen:
                seen.add(key)
                unique.append(vuln)
        return unique

    @staticmethod
    def _filter_exploitable_only(vulnerabilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            vuln
            for vuln in vulnerabilities
            if vuln.get("severity") in ("CRITICAL", "HIGH")
            and vuln.get("confidence_score", 0) >= 70
        ]

    @staticmethod
    def _filter_balanced(vulnerabilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        kept = []
        for vuln in vulnerabilities:
            if vuln.get("severity") == "LOW" and vuln.get("confidence_score", 0) < 50:
                continue
            # Test code is full of fake credentials and intentionally unsafe queries.
            # Vendor token formats are checksum-like and stay reported even there.
            in_test = is_test_path(vuln.get("file_path", ""))
            if in_test and (
                vuln.get("category") == "sql_injection"
                or (vuln.get("category") == "secret" and vuln.get("confidence_score", 0) < 95)
            ):
                continue
            kept.append(vuln)
        return kept

    @staticmethod
    def _group(vulnerabilities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for vuln in vulnerabilities:
            groups.setdefault(GROUPS.get(vuln.get("category"), "other"), []).append(vuln)
        return groups


def get_noise_filter(repo_path: str) -> NoiseFilter:
    return NoiseFilter(repo_path)
