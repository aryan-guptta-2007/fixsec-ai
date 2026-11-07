"""
SQL injection detection.

A finding means a line builds SQL by splicing in a value. Rewriting such a query
needs knowledge of the driver and the surrounding call, so these findings come
with a concrete suggestion rather than an automatic code change.
"""
import logging
import re
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

from core.scanner.files import walk_with_extensions
from core.scanner.secrets import finding_id

logger = logging.getLogger(__name__)

SCANNED_EXTENSIONS = {
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".py", ".java", ".php", ".rb", ".go", ".cs",
}

# A real column list, so prose like "select an option from" does not match.
_COLUMN = r"[\w.`()*]+(?:\s+AS\s+\w+)?"
_COLUMNS = rf"(?:\*|{_COLUMN}(?:\s*,\s*{_COLUMN})*)"
SQL_STATEMENT = (
    rf"(?:SELECT\s+(?:DISTINCT\s+)?{_COLUMNS}\s+FROM\s|INSERT\s+INTO\s|"
    r"UPDATE\s+\S+\s+SET\s|DELETE\s+FROM\s)"
)

# (label, regex, severity), most specific first. Only the first match per line is reported.
PATTERNS: List[Tuple[str, str, str]] = [
    ("Template Literal", r"`[^`]*" + SQL_STATEMENT + r"[^`]*\$\{", "HIGH"),
    ("Python f-string", r"\bf[\"'][^\"']*" + SQL_STATEMENT + r"[^\"']*\{", "HIGH"),
    ("String Concatenation", r"[\"'][^\"']*" + SQL_STATEMENT + r"[^\"']*[\"']\s*(?:\+|\.)\s*\$?[A-Za-z_]", "HIGH"),
    ("Format String", r"[\"'][^\"']*" + SQL_STATEMENT + r"[^\"']*%[sd][^\"']*[\"']\s*%\s*[A-Za-z_(]", "HIGH"),
    ("str.format", r"[\"'][^\"']*" + SQL_STATEMENT + r"[^\"']*\{[^\"']*[\"']\.format\(", "HIGH"),
]

COMMENT_PREFIXES = ("//", "#", "/*", "*", "--")

SUGGESTIONS = {
    ".py": 'cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))  # use ? with sqlite3',
    ".rb": 'client.prepare("SELECT * FROM users WHERE id = ?").execute(user_id)',
    ".php": '$stmt = $pdo->prepare("SELECT * FROM users WHERE id = ?"); $stmt->execute([$id]);',
    ".java": 'PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?"); ps.setInt(1, id);',
    ".go": 'db.Query("SELECT * FROM users WHERE id = $1", id)',
    ".cs": 'cmd.CommandText = "SELECT * FROM users WHERE id = @id"; cmd.Parameters.AddWithValue("@id", id);',
}
JS_SUGGESTION = 'db.query("SELECT * FROM users WHERE id = $1", [userId])  // ? for mysql/sqlite'


def suggestion_for(relative_path: str) -> str:
    return SUGGESTIONS.get(PurePosixPath(relative_path).suffix, JS_SUGGESTION)


def _match_line(line: str) -> Optional[Tuple[str, str]]:
    stripped = line.strip()
    if not stripped or stripped.startswith(COMMENT_PREFIXES):
        return None
    for label, pattern, severity in PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return label, severity
    return None


def scan_sql_injection(repo_path: str) -> List[Dict[str, Any]]:
    """Scan source files for SQL built from interpolated values."""
    findings: List[Dict[str, Any]] = []
    for path, relative in walk_with_extensions(repo_path, SCANNED_EXTENSIONS):
        if relative.rsplit("/", 1)[-1].startswith(".env"):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                for line_number, line in enumerate(handle, 1):
                    if len(line) > 2000:
                        continue
                    match = _match_line(line)
                    if match is None:
                        continue
                    label, severity = match
                    snippet = line.strip()
                    findings.append(
                        {
                            "id": finding_id("sql", relative, line_number),
                            "category": "sql_injection",
                            "type": f"SQL Injection ({label})",
                            "severity": severity,
                            "file": relative,
                            "file_path": relative,
                            "line": line_number,
                            "line_number": line_number,
                            "message": "SQL query built from an interpolated value",
                            "confidence_score": 80,
                            "fixable": False,
                            "code_snippet": snippet[:120] + ("..." if len(snippet) > 120 else ""),
                            "suggested_fix": suggestion_for(relative),
                        }
                    )
        except OSError as exc:
            logger.warning("Could not read %s: %s", relative, exc)
    return findings
