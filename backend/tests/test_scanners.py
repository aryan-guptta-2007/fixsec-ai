import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import LIVE_KEY, PASSWORD
from core.enhanced_security_scorer import EnhancedSecurityScorer
from core.noise_filter import NoiseFilter
from core.scanner import npm_audit
from core.scanner.files import is_test_path
from core.scanner.secrets import public_finding, scan_secrets
from core.scanner.sql_injection import scan_sql_injection
from core.security import redact


def write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_app_imports_on_a_legacy_windows_code_page(tmp_path):
    """Regression: emoji in log output crashed the server at import time."""
    backend = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "-c", "import main"],
        cwd=backend,
        env={
            **__import__("os").environ,
            "PYTHONIOENCODING": "cp1252",
            "PYTHONUTF8": "0",
            "WORKSPACE_DIR": str(tmp_path),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_finds_real_secrets_and_masks_them_publicly(tmp_path):
    write(tmp_path, "a.js", f'const k = "{LIVE_KEY}";\n')
    (finding,) = scan_secrets(str(tmp_path))
    assert finding["severity"] == "CRITICAL"
    assert finding["file_path"] == "a.js"
    assert LIVE_KEY not in json.dumps(public_finding(finding))


@pytest.mark.parametrize(
    "line",
    [
        "const password = process.env.DB_PASSWORD;",
        'password = os.environ["DB_PASSWORD"]',
        'const apiKey = "your-api-key-here";',
        'password: "changeme123"',
        'const url = "https://example.com/some/long/path/that/is/not/a/secret/at/all";',
        'const hash = "d41d8cd98f00b204e9800998ecf8427e";',
        'secret_type = "STRIPE_SECRET_KEY"',
        'secret_kind = "session_cookie_value"',
        'PATTERN = r"-----BEGIN PRIVATE KEY-----"',
    ],
)
def test_common_non_secrets_are_not_flagged(tmp_path, line):
    write(tmp_path, "a.js", line + "\n")
    assert scan_secrets(str(tmp_path)) == []


@pytest.mark.parametrize("name", [".env.example", ".env.production.template", ".env.sample"])
def test_env_templates_are_documentation_not_secrets(tmp_path, name):
    write(tmp_path, name, f"STRIPE_SECRET_KEY={LIVE_KEY}\nSECRET_KEY=abcdefgh12345678\n")
    assert scan_secrets(str(tmp_path)) == []


def test_elided_placeholders_are_ignored(tmp_path):
    write(tmp_path, ".env.staging", "STRIPE_SECRET_KEY=sk_live_...\n")
    assert scan_secrets(str(tmp_path)) == []


def test_real_env_files_are_still_scanned(tmp_path):
    write(tmp_path, ".env.production", "API_TOKEN=abcdefgh12345678\n")
    assert len(scan_secrets(str(tmp_path))) == 1


@pytest.mark.parametrize(
    "relative,content",
    [
        ("server.key", "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA\n"),
        ("a.js", 'const k = "-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBg";\n'),
    ],
)
def test_real_private_keys_are_found(tmp_path, relative, content):
    write(tmp_path, relative, content)
    assert scan_secrets(str(tmp_path))[0]["type"] == "Private Key"


def test_one_finding_per_secret_even_when_patterns_overlap(tmp_path):
    write(tmp_path, "a.py", f'stripe_api_key = "{LIVE_KEY}"\n')
    assert len(scan_secrets(str(tmp_path))) == 1


def test_scanners_skip_dependency_and_build_directories(tmp_path):
    write(tmp_path, "node_modules/x/index.js", f'const k = "{LIVE_KEY}";\n')
    write(tmp_path, "dist/bundle.js", f'const k = "{LIVE_KEY}";\n')
    write(tmp_path, "package-lock.json", f'{{"k": "{LIVE_KEY}"}}\n')
    assert scan_secrets(str(tmp_path)) == []


@pytest.mark.parametrize(
    "line",
    [
        'db.query("SELECT * FROM users WHERE id = " + id);',
        "db.query(`SELECT * FROM users WHERE id = ${id}`);",
        'cursor.execute(f"SELECT * FROM users WHERE id = {uid}")',
        'cursor.execute("DELETE FROM users WHERE id = %s" % uid)',
        'cursor.execute("UPDATE users SET a = {}".format(a))',
    ],
)
def test_sql_injection_patterns_report_once_per_line(tmp_path, line):
    write(tmp_path, "db.py" if "cursor" in line else "db.js", line + "\n")
    assert len(scan_sql_injection(str(tmp_path))) == 1


@pytest.mark.parametrize(
    "line",
    [
        'db.query("SELECT * FROM users WHERE id = $1", [id]);',
        'cursor.execute("SELECT * FROM users WHERE id = %s", (uid,))',
        '// db.query("SELECT * FROM users WHERE id = " + id);',
        'console.log("Please select an option from " + menu);',
    ],
)
def test_safe_sql_is_not_flagged(tmp_path, line):
    write(tmp_path, "db.js", line + "\n")
    assert scan_sql_injection(str(tmp_path)) == []


@pytest.mark.parametrize(
    "path,expected",
    [
        ("tests/test_a.py", True),
        ("src/__tests__/a.js", True),
        ("src/a.spec.ts", True),
        ("test_a.py", True),
        ("src/latest_config.py", False),
        ("src/contest.js", False),
    ],
)
def test_is_test_path(path, expected):
    assert is_test_path(path) is expected


def test_noise_filter_drops_fake_test_credentials_but_keeps_vendor_tokens(tmp_path):
    write(tmp_path, "tests/a.py", f'password = "{PASSWORD}"\nkey = "{LIVE_KEY}"\n')
    result = NoiseFilter(str(tmp_path)).filter_vulnerabilities(scan_secrets(str(tmp_path)))
    assert [f["type"] for f in result["vulnerabilities"]] == ["Stripe Live Secret Key"]
    assert result["summary"]["false_positives_removed"] == 1


def test_fixsecignore_rules(tmp_path):
    write(tmp_path, ".fixsecignore", "legacy/\n*.gen.js\nvuln:password\n")
    write(tmp_path, "legacy/a.js", f'const k = "{LIVE_KEY}";\n')
    write(tmp_path, "src/b.gen.js", f'const k = "{LIVE_KEY}";\n')
    write(tmp_path, "src/c.js", f'const password = "{PASSWORD}";\n')
    write(tmp_path, "src/d.js", f'const k = "{LIVE_KEY}";\n')
    result = NoiseFilter(str(tmp_path)).filter_vulnerabilities(scan_secrets(str(tmp_path)))
    assert [f["file_path"] for f in result["vulnerabilities"]] == ["src/d.js"]


def test_clean_repository_scores_a_plus_even_when_public():
    """Regression: exposure multipliers cost clean public repos their grade."""
    result = EnhancedSecurityScorer(
        {"private": False, "stargazers_count": 5000}
    ).calculate_comprehensive_score([])
    assert (result["score"], result["grade"]) == (100, "A+")


def test_live_key_costs_more_than_a_potential_secret():
    base = {"category": "secret", "confidence_score": 90, "file_path": "src/a.js"}
    scorer = EnhancedSecurityScorer({"private": True})
    live = scorer.calculate_comprehensive_score(
        [{**base, "type": "Stripe Live Secret Key", "severity": "CRITICAL"}]
    )
    weak = scorer.calculate_comprehensive_score(
        [{**base, "type": "Potential Secret", "severity": "MEDIUM"}]
    )
    assert live["score"] < weak["score"]


def test_transitive_dependency_findings_do_not_alone_zero_the_score():
    """Regression: a repository's score hit 0 from npm findings on dev tooling alone."""
    findings = [
        {"category": "dependency", "severity": "HIGH", "confidence_score": 95, "file_path": "package.json"}
    ] * 40
    assert EnhancedSecurityScorer({"private": True}).calculate_comprehensive_score(findings)["score"] == 50


def test_redact_removes_credentials():
    token = "ghp_" + "a" * 36
    text = f"fatal: https://{token}@github.com/o/r.git failed, Authorization: Bearer {token}"
    assert token not in redact(text)


AUDIT_OUTPUT = {
    "vulnerabilities": {
        "lodash": {
            "severity": "moderate",
            "range": "<4.17.21",
            "via": [{"title": "Prototype Pollution", "url": "https://advisory.test/1"}],
            "fixAvailable": True,
        },
        "next": {
            "severity": "critical",
            "range": "<14",
            "via": ["other"],
            "fixAvailable": {"name": "next", "version": "15.0.0", "isSemVerMajor": True},
        },
    }
}


class FakeProcess:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def test_npm_runs_without_scripts_and_without_server_secrets(tmp_path, monkeypatch):
    """Repositories are untrusted: install scripts would be remote code execution."""
    monkeypatch.setattr(npm_audit, "npm_path", lambda: "npm")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "must-not-leak")
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs["env"]))
        return FakeProcess(json.dumps(AUDIT_OUTPUT), 1 if "audit" in command else 0)

    monkeypatch.setattr(npm_audit.subprocess, "run", fake_run)
    write(tmp_path, "package.json", "{}")
    findings, warnings = npm_audit.audit_dependencies(str(tmp_path))

    install = calls[0][0]
    assert "--ignore-scripts" in install and "--package-lock-only" in install
    assert all(env["npm_config_ignore_scripts"] == "true" for _, env in calls)
    assert all("STRIPE_SECRET_KEY" not in env for _, env in calls)
    assert warnings == []
    assert [f["severity"] for f in findings] == ["CRITICAL", "MEDIUM"]


def test_audit_maps_fixability(tmp_path, monkeypatch):
    monkeypatch.setattr(npm_audit, "npm_path", lambda: "npm")
    monkeypatch.setattr(
        npm_audit.subprocess, "run", lambda *a, **k: FakeProcess(json.dumps(AUDIT_OUTPUT), 1)
    )
    write(tmp_path, "package.json", "{}")
    write(tmp_path, "package-lock.json", "{}")
    findings, _ = npm_audit.audit_dependencies(str(tmp_path))
    by_name = {f["package"]: f for f in findings}
    assert by_name["lodash"]["fixable"] is True
    assert by_name["next"]["fixable"] is False and by_name["next"]["breaking_fix"] is True


def test_exact_pins_are_not_promised_as_automatic(tmp_path, monkeypatch):
    """npm audit fix cannot move an exact pin, so the plan must not claim it can."""
    monkeypatch.setattr(npm_audit, "npm_path", lambda: "npm")
    monkeypatch.setattr(
        npm_audit.subprocess, "run", lambda *a, **k: FakeProcess(json.dumps(AUDIT_OUTPUT), 1)
    )
    write(tmp_path, "package.json", '{"dependencies": {"lodash": "4.17.15"}}')
    write(tmp_path, "package-lock.json", "{}")
    findings, _ = npm_audit.audit_dependencies(str(tmp_path))
    lodash = next(f for f in findings if f["package"] == "lodash")
    assert lodash["pinned"] is True and lodash["fixable"] is False


def test_fix_reports_what_is_still_vulnerable_despite_npm_exit_code(tmp_path, monkeypatch):
    """Regression: npm exits 1 after a partial fix, which read as a total failure."""
    monkeypatch.setattr(npm_audit, "npm_path", lambda: "npm")
    left = {"vulnerabilities": {"next": {}}}
    monkeypatch.setattr(
        npm_audit.subprocess, "run", lambda *a, **k: FakeProcess(json.dumps(left), 1)
    )
    assert npm_audit.fix_dependencies(str(tmp_path), ".") == {"next"}


def test_failed_audit_is_a_warning_not_a_clean_result(tmp_path, monkeypatch):
    monkeypatch.setattr(npm_audit, "npm_path", lambda: "npm")
    monkeypatch.setattr(
        npm_audit.subprocess,
        "run",
        lambda *a, **k: FakeProcess(json.dumps({"error": {"code": "ENOAUDIT"}}), 1),
    )
    write(tmp_path, "package.json", "{}")
    write(tmp_path, "package-lock.json", "{}")
    findings, warnings = npm_audit.audit_dependencies(str(tmp_path))
    assert findings == [] and len(warnings) == 1


def test_missing_npm_is_reported(tmp_path):
    write(tmp_path, "package.json", "{}")
    _, warnings = npm_audit.audit_dependencies(str(tmp_path))
    assert "npm is not available" in warnings[0]


def test_finds_nested_package_dirs_but_not_node_modules(tmp_path):
    write(tmp_path, "package.json", "{}")
    write(tmp_path, "frontend/package.json", "{}")
    write(tmp_path, "node_modules/x/package.json", "{}")
    assert npm_audit.find_package_dirs(str(tmp_path)) == [".", "frontend"]
