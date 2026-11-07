"""
Hardcoded secret detection.

Findings carry the raw value and its position under underscore-prefixed keys so
the fixer can act on them. Those keys never leave the process: public_finding()
strips them before anything is stored or returned.
"""
import hashlib
import logging
import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from core.scanner.files import walk_with_extensions

logger = logging.getLogger(__name__)

SCANNED_EXTENSIONS = {
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".py", ".java", ".go", ".php", ".rb",
    ".cs", ".json", ".yaml", ".yml", ".toml", ".ini", ".properties", ".sh", ".pem", ".key",
}

# Files that exist to document configuration, not to hold it.
TEMPLATE_FILE = re.compile(r"(example|sample|template|dist)", re.IGNORECASE)

# name, regex (group 1 is the secret), severity, env var, confidence
TOKEN_PATTERNS: List[Tuple[str, str, str, str, int]] = [
    ("Stripe Live Secret Key", r"\b(sk_live_[A-Za-z0-9]{16,})", "CRITICAL", "STRIPE_SECRET_KEY", 98),
    ("Stripe Restricted Key", r"\b(rk_live_[A-Za-z0-9]{16,})", "CRITICAL", "STRIPE_RESTRICTED_KEY", 98),
    ("Stripe Test Secret Key", r"\b(sk_test_[A-Za-z0-9]{16,})", "HIGH", "STRIPE_TEST_SECRET_KEY", 95),
    ("AWS Access Key", r"\b((?:AKIA|ASIA)[0-9A-Z]{16})\b", "CRITICAL", "AWS_ACCESS_KEY_ID", 95),
    ("GitHub Token", r"\b((?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,})", "CRITICAL", "GITHUB_TOKEN", 98),
    ("GitHub Token", r"\b(github_pat_[A-Za-z0-9_]{40,})", "CRITICAL", "GITHUB_TOKEN", 98),
    ("Google API Key", r"\b(AIza[0-9A-Za-z_-]{35})", "HIGH", "GOOGLE_API_KEY", 95),
    ("Slack Token", r"\b(xox[baprs]-[0-9A-Za-z-]{10,})", "HIGH", "SLACK_TOKEN", 95),
    ("SendGrid API Key", r"\b(SG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,})", "HIGH", "SENDGRID_API_KEY", 95),
]

NAMED_ASSIGNMENT = re.compile(
    r"""(?ix)
    \b([a-z0-9_]*(?:password|passwd|pwd|secret|api_?key|auth_?token|access_?token|
                    private_?key|client_?secret)[a-z0-9_]*)
    ["']?\s*(?::|=|=>)\s*
    (["'])([^"'\s]{8,})\2
    """
)
DOTENV_ASSIGNMENT = re.compile(
    r"""(?ix)^\s*(?:export\s+)?
    ([a-z0-9_]*(?:password|passwd|pwd|secret|key|token)[a-z0-9_]*)
    \s*=\s*["']?([^"'\s\#]{8,})["']?\s*$"""
)
# The lookahead skips the bare marker in a string literal, as in a detection rule.
PRIVATE_KEY_BLOCK = re.compile(
    r"""-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----(?!["'`])"""
)
HIGH_ENTROPY_LITERAL = re.compile(r"""(["'])([A-Za-z0-9+/_=-]{32,})\1""")

PLACEHOLDER = re.compile(
    r"your|example|changeme|change_me|placeholder|xxxx|\*\*\*|dummy|sample|fake|"
    r"redacted|insert|replace|todo|<|\$\{|\{\{|%\(|\.\.\.|process\.env|os\.environ|getenv",
    re.IGNORECASE,
)


def _entropy(value: str) -> float:
    counts = Counter(value)
    return -sum((n / len(value)) * math.log2(n / len(value)) for n in counts.values())


def _is_placeholder(value: str) -> bool:
    return bool(PLACEHOLDER.search(value)) or len(set(value)) <= 3


def _is_name_not_value(value: str) -> bool:
    """`kind = "STRIPE_SECRET_KEY"` names a secret. It does not contain one."""
    return bool(re.fullmatch(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+|[a-z]+(?:_[a-z]+)+", value))


def _looks_generated(value: str) -> bool:
    """A random-looking literal, as opposed to a hash, path or identifier."""
    if re.fullmatch(r"[a-fA-F0-9]+", value) or "/" in value:
        return False
    has_letters = re.search(r"[A-Za-z]", value)
    has_digits = re.search(r"\d", value)
    return bool(has_letters and has_digits) and _entropy(value) >= 4.5


def mask(value: str) -> str:
    return f"{value[:4]}{'*' * 8}" if len(value) > 8 else "*" * 8


def finding_id(*parts: Any) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


def public_finding(finding: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in finding.items() if not key.startswith("_")}


def _finding(
    name: str,
    severity: str,
    relative: str,
    line_number: int,
    value: Optional[str],
    span: Optional[Tuple[int, int]],
    env_name: Optional[str],
    confidence: int,
) -> Dict[str, Any]:
    return {
        "id": finding_id("secret", relative, line_number, name),
        "category": "secret",
        "type": name,
        "severity": severity,
        "file": relative,
        "file_path": relative,
        "line": line_number,
        "line_number": line_number,
        "message": f"{name} detected" if name.startswith("Hardcoded") else f"Hardcoded {name.lower()} detected",
        "confidence_score": confidence,
        "fixable": value is not None,
        "secret_value": mask(value) if value else None,
        "_raw": value,
        "_span": span,
        "_env_name": env_name,
    }


def _scan_line(line: str, relative: str, line_number: int, is_dotenv: bool) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    taken: List[Tuple[int, int]] = []

    def overlaps(span: Tuple[int, int]) -> bool:
        return any(span[0] < end and start < span[1] for start, end in taken)

    def add(name, severity, value, span, env_name, confidence):
        if not overlaps(span):
            taken.append(span)
            findings.append(
                _finding(name, severity, relative, line_number, value, span, env_name, confidence)
            )

    if PRIVATE_KEY_BLOCK.search(line):
        findings.append(
            _finding("Private Key", "CRITICAL", relative, line_number, None, None, None, 99)
        )

    for name, pattern, severity, env_name, confidence in TOKEN_PATTERNS:
        for match in re.finditer(pattern, line):
            if not _is_placeholder(match.group(1)):
                add(name, severity, match.group(1), match.span(1), env_name, confidence)

    for match in NAMED_ASSIGNMENT.finditer(line):
        identifier, value = match.group(1), match.group(3)
        if not _is_placeholder(value) and not _is_name_not_value(value):
            is_password = re.search(r"pass|pwd", identifier, re.IGNORECASE)
            add(
                "Hardcoded Password" if is_password else "Hardcoded API Secret",
                "HIGH",
                value,
                match.span(3),
                re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", identifier).upper(),
                85,
            )

    if is_dotenv:
        match = DOTENV_ASSIGNMENT.match(line)
        if match and not _is_placeholder(match.group(2)):
            add("Committed Env Secret", "HIGH", match.group(2), match.span(2), match.group(1), 85)
    else:
        for match in HIGH_ENTROPY_LITERAL.finditer(line):
            value = match.group(2)
            if _looks_generated(value) and not _is_placeholder(value):
                add("Potential Secret", "MEDIUM", value, match.span(2), None, 55)

    return findings


def scan_secrets(repo_path: str) -> List[Dict[str, Any]]:
    """Scan a repository for hardcoded secrets."""
    findings: List[Dict[str, Any]] = []
    for path, relative in walk_with_extensions(repo_path, SCANNED_EXTENSIONS):
        name = relative.rsplit("/", 1)[-1]
        is_dotenv = name.startswith(".env")
        if is_dotenv and TEMPLATE_FILE.search(name):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                for line_number, line in enumerate(handle, 1):
                    if len(line) <= 2000:  # skip minified bundles and embedded blobs
                        findings.extend(
                            _scan_line(line.rstrip("\r\n"), relative, line_number, is_dotenv)
                        )
        except OSError as exc:
            logger.warning("Could not read %s: %s", relative, exc)
    return findings
