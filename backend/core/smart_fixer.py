"""
Auto-fix engine.

A change is only made when it is known to be safe:

* Hardcoded secrets in supported languages are replaced with an environment
  lookup. The value itself is never written anywhere in the repository; the PR
  documents the variable name in .env.example and tells the owner to rotate.
* Vulnerable dependencies are updated with `npm audit fix`, without --force, so
  breaking major upgrades stay a human decision.
* Everything else goes to the review list with a concrete suggestion.

Every edited file is re-parsed and restored if the edit broke it.
"""
import ast
import hashlib
import logging
import os
import re
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional

from core.scanner.npm_audit import fix_dependencies
from core.scanner.secrets import mask, public_finding

logger = logging.getLogger(__name__)

ENV_SYNTAX = {
    ".py": 'os.environ["{}"]',
    ".js": "process.env.{}",
    ".jsx": "process.env.{}",
    ".mjs": "process.env.{}",
    ".cjs": "process.env.{}",
    ".ts": "process.env.{}",
    ".tsx": "process.env.{}",
    ".rb": 'ENV["{}"]',
    ".php": "getenv('{}')",
}
NODE_CHECKED = {".js", ".mjs", ".cjs"}
BACKTICK_STRINGS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
PHP_CONSTANT_CONTEXT = re.compile(r"\b(const|public|private|protected|static)\b")
ROTATE = "Rotate this credential: it is in the repository history and must be treated as exposed."


class SmartFixer:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self._env_names: Dict[str, str] = {}

    # ------------------------------------------------------------------ planning

    def generate_comprehensive_fix_plan(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Decide, per finding, whether it can be fixed safely and how."""
        auto: List[Dict[str, Any]] = []
        review: List[Dict[str, Any]] = []

        for finding in findings:
            analysis = self._analyze(finding)
            if analysis["auto_fixable"]:
                auto.append(
                    {
                        "vulnerability": public_finding(finding),
                        "fix_method": analysis["method"],
                        "confidence": analysis["confidence"],
                        "risk_level": "LOW" if analysis["confidence"] >= 90 else "MEDIUM",
                        "explanation": analysis["explanation"],
                        "preview": analysis["preview"],
                        "diff": analysis.get("diff"),
                        "_finding": finding,
                        "_env_name": analysis.get("env_name"),
                    }
                )
            else:
                review.append(
                    {
                        "vulnerability": public_finding(finding),
                        "reason": analysis["reason"],
                        "suggested_action": analysis["suggestion"],
                    }
                )

        return {
            "fixable_automatically": auto,
            "requires_review": review,
            "total_fixes": len(auto),
            "estimated_time": f"About {max(1, len(auto) + 5 * len(review))} minutes to review",
            "risk_assessment": self._overall_risk(auto),
        }

    def _analyze(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        category = finding.get("category")
        if category == "dependency":
            return self._analyze_dependency(finding)
        if category == "secret":
            return self._analyze_secret(finding)
        if category == "sql_injection":
            return {
                "auto_fixable": False,
                "reason": "Rewriting a query safely needs knowledge of the database driver "
                "and the surrounding code.",
                "suggestion": f"Use a parameterized query, for example: {finding.get('suggested_fix')}",
            }
        return {
            "auto_fixable": False,
            "reason": "No automatic fix exists for this issue type.",
            "suggestion": "Review this finding manually.",
        }

    def _analyze_dependency(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        package = finding.get("package", "this package")
        if finding.get("fixable"):
            return {
                "auto_fixable": True,
                "method": "npm_audit_fix",
                "confidence": 90,
                "explanation": f"Update {package} to a patched, non-breaking version with npm audit fix.",
                "preview": f"{finding['file_path']}: {package} updated to a patched version",
            }
        if finding.get("breaking_fix"):
            reason = f"The fix for {package} is a major version upgrade that may break your code."
            suggestion = f"Upgrade {package} deliberately and run your test suite."
        elif finding.get("pinned") and finding.get("fix_available"):
            reason = f"{package} is pinned to an exact version in package.json."
            suggestion = f"Update the version of {package} in package.json to a patched release."
        elif not finding.get("has_lockfile", True):
            reason = "This project has no package-lock.json, so it may use another package manager."
            suggestion = "Run your package manager's audit fix, or commit a package-lock.json."
        else:
            reason = f"No patched version of {package} is available yet."
            suggestion = "Check the advisory for workarounds or replace the package."
        return {"auto_fixable": False, "reason": reason, "suggestion": suggestion}

    def _analyze_secret(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        def review(reason: str, suggestion: str = "") -> Dict[str, Any]:
            return {
                "auto_fixable": False,
                "reason": reason,
                "suggestion": suggestion or f"Move it to an environment variable. {ROTATE}",
            }

        raw, span = finding.get("_raw"), finding.get("_span")
        if not raw or not span:
            return review(
                "Key material cannot be replaced with a single environment lookup.",
                f"Remove the key from the repository and load it at runtime. {ROTATE}",
            )
        if finding.get("type") == "Potential Secret":
            return review("This looks like a secret but could be a harmless identifier.")

        relative = finding["file_path"]
        suffix = PurePosixPath(relative).suffix
        template = ENV_SYNTAX.get(suffix)
        if template is None:
            return review(
                "Configuration files cannot read environment variables in a portable way.",
                f"Remove the value from this file and inject it at deploy time. {ROTATE}",
            )

        try:
            lines = self._read_lines(relative)
            line = lines[finding["line_number"] - 1]
        except (OSError, IndexError, UnicodeDecodeError, ValueError):
            return review("The file could not be read for an exact edit.")

        start, end = span
        quote = line[start - 1] if start > 0 else ""
        allowed = "\"'`" if suffix in BACKTICK_STRINGS else "\"'"
        is_whole_literal = (
            line[start:end] == raw
            and quote
            and quote in allowed
            and line[end:end + 1] == quote
            and not (start >= 2 and (line[start - 2].isalnum() or line[start - 2] in "\"'"))
        )
        if not is_whole_literal:
            return review("The secret is embedded in a larger string, so it needs a manual edit.")
        if suffix == ".php" and PHP_CONSTANT_CONTEXT.search(line):
            return review("PHP does not allow function calls in constant or property initialisers.")

        env_name = self._env_name_for(raw, finding.get("_env_name"))
        replacement = template.format(env_name)
        before = line.replace(raw, mask(raw)).strip()
        after = (line[:start - 1] + replacement + line[end + 1:]).strip()
        return {
            "auto_fixable": True,
            "method": "move_to_env",
            "confidence": 85,
            "explanation": f"Read {env_name} from the environment instead of hardcoding it.",
            "preview": f"{relative}:{finding['line_number']}: hardcoded value replaced with {replacement}",
            "diff": {"before": before, "after": after},
            "env_name": env_name,
        }

    def _env_name_for(self, value: str, preferred: Optional[str]) -> str:
        """One variable per distinct secret, even when two share a natural name."""
        if value in self._env_names:
            return self._env_names[value]
        base = re.sub(r"[^A-Z0-9_]", "_", (preferred or "APP_SECRET").upper()).strip("_")
        if not base or base[0].isdigit():
            base = f"APP_{base}"
        name, suffix = base, 2
        while name in self._env_names.values():
            name, suffix = f"{base}_{suffix}", suffix + 1
        self._env_names[value] = name
        return name

    @staticmethod
    def _overall_risk(fixes: List[Dict[str, Any]]) -> str:
        if not fixes:
            return "NONE"
        average = sum(fix["confidence"] for fix in fixes) / len(fixes)
        return "LOW" if average >= 90 else "MEDIUM"

    # ----------------------------------------------------------------- file access

    def _resolve(self, relative: str) -> Path:
        candidate = (self.repo_path / relative).resolve()
        if not candidate.is_relative_to(self.repo_path):
            raise ValueError(f"Path escapes the repository: {relative}")
        return candidate

    def _read_lines(self, relative: str) -> List[str]:
        with open(self._resolve(relative), "r", encoding="utf-8", newline="") as handle:
            return list(handle)

    # ------------------------------------------------------------------- applying

    def apply_smart_fixes(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Apply the plan. Only changes that really happened are reported as applied."""
        results: Dict[str, Any] = {
            "fixes_applied": 0,
            "fixes_failed": 0,
            "applied": [],
            "failed": [],
            "modified_files": [],
            "env_vars": [],
        }

        secret_fixes: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        dependency_fixes: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for item in plan["fixable_automatically"]:
            finding = item["_finding"]
            if item["fix_method"] == "move_to_env":
                secret_fixes[finding["file_path"]].append(item)
            else:
                dependency_fixes[finding["package_dir"]].append(item)

        for relative, items in secret_fixes.items():
            self._apply_secret_fixes(relative, items, results)
        for package_dir, items in dependency_fixes.items():
            self._apply_dependency_fixes(package_dir, items, results)

        if results["env_vars"]:
            self._document_env_vars(results)
        return results

    def _record(self, results: Dict[str, Any], items: List[Dict[str, Any]], error: Optional[str]) -> None:
        for item in items:
            if error:
                results["fixes_failed"] += 1
                results["failed"].append({**self._summary(item), "error": error})
            else:
                results["fixes_applied"] += 1
                results["applied"].append(self._summary(item))

    @staticmethod
    def _summary(item: Dict[str, Any]) -> Dict[str, Any]:
        vulnerability = item["vulnerability"]
        return {
            "type": vulnerability["type"],
            "category": vulnerability["category"],
            "file": vulnerability["file_path"],
            "line": vulnerability.get("line_number"),
            "description": item["explanation"],
        }

    def _apply_secret_fixes(
        self, relative: str, items: List[Dict[str, Any]], results: Dict[str, Any]
    ) -> None:
        path = self._resolve(relative)
        original = path.read_bytes()
        lines = self._read_lines(relative)
        suffix = path.suffix

        # Right to left, so earlier spans on a line stay valid.
        ordered = sorted(
            items,
            key=lambda i: (i["_finding"]["line_number"], i["_finding"]["_span"][0]),
            reverse=True,
        )
        for item in ordered:
            finding = item["_finding"]
            index = finding["line_number"] - 1
            start, end = finding["_span"]
            line = lines[index]
            replacement = ENV_SYNTAX[suffix].format(item["_env_name"])
            lines[index] = line[:start - 1] + replacement + line[end + 1:]

        text = "".join(lines)
        if suffix == ".py":
            text = self._ensure_python_import(text)

        node_baseline = suffix in NODE_CHECKED and self._node_accepts(path)
        path.write_bytes(text.encode("utf-8"))
        if not self._still_parses(path, suffix, node_baseline):
            path.write_bytes(original)
            self._record(results, items, "The edit would have broken the file, so it was reverted.")
            return

        self._record(results, items, None)
        results["modified_files"].append(relative)
        for item in items:
            if item["_env_name"] not in results["env_vars"]:
                results["env_vars"].append(item["_env_name"])

    @staticmethod
    def _ensure_python_import(text: str) -> str:
        if re.search(r"^\s*import\s+(?:[\w.]+\s*,\s*)*os\b", text, re.MULTILINE):
            return text
        newline = "\r\n" if "\r\n" in text else "\n"
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return text  # reported by the post-edit check
        insert_at = 0
        for node in tree.body:
            is_docstring = (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            )
            is_future = isinstance(node, ast.ImportFrom) and node.module == "__future__"
            if not (is_docstring or is_future):
                break
            insert_at = node.end_lineno
        lines = text.splitlines(keepends=True)
        lines.insert(insert_at, f"import os{newline}")
        return "".join(lines)

    @staticmethod
    def _node_accepts(path: Path) -> bool:
        node = shutil.which("node")
        if node is None:
            return False
        try:
            # --check only parses, so repository code is not executed.
            result = subprocess.run(
                [node, "--check", str(path)],
                capture_output=True,
                timeout=20,
                env={"PATH": os.environ.get("PATH", "")},
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0

    def _still_parses(self, path: Path, suffix: str, node_baseline: bool) -> bool:
        if suffix == ".py":
            try:
                ast.parse(path.read_text(encoding="utf-8"))
                return True
            except (SyntaxError, ValueError):
                return False
        # Node cannot parse JSX or every module flavour, so only trust it when it
        # accepted the file before the edit.
        return self._node_accepts(path) if node_baseline else True

    def _apply_dependency_fixes(
        self, package_dir: str, items: List[Dict[str, Any]], results: Dict[str, Any]
    ) -> None:
        tracked = [
            "package.json" if package_dir == "." else f"{package_dir}/package.json",
            "package-lock.json" if package_dir == "." else f"{package_dir}/package-lock.json",
        ]

        def fingerprint() -> Dict[str, str]:
            return {
                name: hashlib.sha256(self._resolve(name).read_bytes()).hexdigest()
                for name in tracked
                if self._resolve(name).exists()
            }

        before = fingerprint()
        remaining = fix_dependencies(str(self.repo_path), package_dir)
        after = fingerprint()
        changed = [name for name in tracked if before.get(name) != after.get(name)]

        if remaining is None or not changed:
            self._record(results, items, "npm could not update this dependency automatically.")
            return

        fixed = [i for i in items if i["vulnerability"]["package"] not in remaining]
        unfixed = [i for i in items if i["vulnerability"]["package"] in remaining]
        self._record(results, fixed, None)
        self._record(results, unfixed, "npm could not patch this without a breaking change.")
        if fixed:
            results["modified_files"].extend(changed)

    def _document_env_vars(self, results: Dict[str, Any]) -> None:
        example = self._resolve(".env.example")
        existing = example.read_text(encoding="utf-8") if example.exists() else ""
        known = set(re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=", existing, re.MULTILINE))
        missing = [name for name in results["env_vars"] if name not in known]
        if missing:
            if existing and not existing.endswith("\n"):
                existing += "\n"
            header = "" if existing else "# Copy to .env and fill in real values. Never commit .env.\n"
            example.write_text(
                existing + header + "".join(f"{name}=\n" for name in missing), encoding="utf-8"
            )
            results["modified_files"].append(".env.example")

        gitignore = self._resolve(".gitignore")
        content = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        patterns = {line.strip() for line in content.splitlines()}
        if not patterns & {".env", ".env*", "*.env", "/.env"}:
            if content and not content.endswith("\n"):
                content += "\n"
            gitignore.write_text(content + ".env\n", encoding="utf-8")
            results["modified_files"].append(".gitignore")


def public_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """The plan without the raw secret material the fixer needs internally."""
    return {
        **plan,
        "fixable_automatically": [
            {key: value for key, value in item.items() if not key.startswith("_")}
            for item in plan["fixable_automatically"]
        ],
    }


def build_commit_message(results: Dict[str, Any]) -> str:
    secrets = sum(1 for fix in results["applied"] if fix["category"] == "secret")
    dependencies = sum(1 for fix in results["applied"] if fix["category"] == "dependency")
    lines = ["FixSec AI: security fixes", ""]
    if secrets:
        lines.append(f"- Replace {secrets} hardcoded secret(s) with environment variables")
    if dependencies:
        lines.append(f"- Update {dependencies} vulnerable dependency finding(s)")
    return "\n".join(lines) + "\n"


def build_pr_body(results: Dict[str, Any], plan: Dict[str, Any]) -> str:
    """Describe what actually changed, and what is still the reviewer's job."""
    sections = ["FixSec AI generated this PR. Please review it before merging.", "", "## Changes"]
    for fix in results["applied"]:
        location = f"`{fix['file']}`" + (f" line {fix['line']}" if fix["line"] else "")
        sections.append(f"- {location}: {fix['description']}")

    if results["env_vars"]:
        sections += [
            "",
            "## Required before merging",
            "",
            "**1. Set these environment variables** wherever the app runs, or it will fail at "
            "startup. They are listed in `.env.example`; no secret values are in this PR.",
            "",
        ]
        sections += [f"- `{name}`" for name in results["env_vars"]]
        sections += [
            "",
            "**2. Rotate every one of these credentials.** The old values stay in your git "
            "history, so removing them from the code does not make them safe.",
        ]

    if results["failed"]:
        sections += ["", "## Could not be fixed automatically"]
        for fix in results["failed"]:
            sections.append(f"- `{fix['file']}`: {fix['type']}. {fix['error']}")

    if plan["requires_review"]:
        sections += ["", "## Still needs manual review"]
        for item in plan["requires_review"]:
            vulnerability = item["vulnerability"]
            line = vulnerability.get("line_number")
            location = f"`{vulnerability['file_path']}`" + (f" line {line}" if line else "")
            sections.append(f"- {location}: {vulnerability['type']}. {item['suggested_action']}")

    return "\n".join(sections) + "\n"


def get_smart_fixer(repo_path: str) -> SmartFixer:
    return SmartFixer(repo_path)
