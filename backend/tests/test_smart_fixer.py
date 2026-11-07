import ast
import shutil
from pathlib import Path

import pytest

from conftest import LIVE_KEY, PASSWORD
from core import smart_fixer
from core.scanner.secrets import scan_secrets
from core.scanner.sql_injection import scan_sql_injection
from core.smart_fixer import SmartFixer, build_pr_body, public_plan


def plan_and_apply(root: Path):
    fixer = SmartFixer(str(root))
    plan = fixer.generate_comprehensive_fix_plan(
        scan_secrets(str(root)) + scan_sql_injection(str(root))
    )
    return plan, fixer.apply_smart_fixes(plan)


def repo(tmp_path: Path, files: dict) -> Path:
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return tmp_path


def test_python_fix_adds_import_after_docstring_and_stays_valid(tmp_path):
    root = repo(tmp_path, {"a.py": f'"""Doc."""\nfrom __future__ import annotations\nKEY = "{LIVE_KEY}"\n'})
    _, results = plan_and_apply(root)
    content = (root / "a.py").read_text()
    assert results["fixes_applied"] == 1
    assert 'KEY = os.environ["STRIPE_SECRET_KEY"]' in content
    assert LIVE_KEY not in content
    tree = ast.parse(content)
    assert isinstance(tree.body[2], ast.Import)


def test_python_fix_does_not_duplicate_import(tmp_path):
    root = repo(tmp_path, {"a.py": f'import os\nKEY = "{LIVE_KEY}"\n'})
    plan_and_apply(root)
    assert (root / "a.py").read_text().count("import os") == 1


def test_javascript_uses_process_env(tmp_path):
    root = repo(tmp_path, {"a.js": f'const password = "{PASSWORD}";\n'})
    plan_and_apply(root)
    assert (root / "a.js").read_text() == "const password = process.env.PASSWORD;\n"


def test_language_specific_syntax(tmp_path):
    root = repo(
        tmp_path,
        {"a.rb": f'KEY = "{LIVE_KEY}"\n', "b.php": f'<?php $key = "{LIVE_KEY}";\n'},
    )
    plan_and_apply(root)
    assert 'ENV["STRIPE_SECRET_KEY"]' in (root / "a.rb").read_text()
    assert "getenv('STRIPE_SECRET_KEY')" in (root / "b.php").read_text()


def test_the_secret_is_never_written_anywhere(tmp_path):
    """Regression: the value used to be written to a .env that was then committed."""
    root = repo(tmp_path, {"a.py": f'KEY = "{LIVE_KEY}"\n'})
    plan_and_apply(root)
    assert not (root / ".env").exists()
    for path in root.rglob("*"):
        if path.is_file():
            assert LIVE_KEY not in path.read_text(encoding="utf-8")
    assert "STRIPE_SECRET_KEY=\n" in (root / ".env.example").read_text()
    assert ".env" in (root / ".gitignore").read_text().splitlines()


def test_existing_gitignore_and_env_example_are_preserved(tmp_path):
    root = repo(
        tmp_path,
        {
            "a.py": f'KEY = "{LIVE_KEY}"\n',
            ".gitignore": "node_modules\n.env\n",
            ".env.example": "EXISTING=1",
        },
    )
    _, results = plan_and_apply(root)
    assert (root / ".gitignore").read_text() == "node_modules\n.env\n"
    assert (root / ".env.example").read_text() == "EXISTING=1\nSTRIPE_SECRET_KEY=\n"
    assert ".gitignore" not in results["modified_files"]


def test_different_secrets_get_different_variables(tmp_path):
    """Regression: every secret became SECRET_VALUE, so they overwrote each other."""
    other = "sk_live_" + "Z9y8X7w6" * 3
    root = repo(tmp_path, {"a.js": f'const a = "{LIVE_KEY}";\nconst b = "{other}";\nconst c = "{LIVE_KEY}";\n'})
    _, results = plan_and_apply(root)
    assert sorted(results["env_vars"]) == ["STRIPE_SECRET_KEY", "STRIPE_SECRET_KEY_2"]
    lines = (root / "a.js").read_text().splitlines()
    assert lines[0].endswith("process.env.STRIPE_SECRET_KEY;")
    assert lines[1].endswith("process.env.STRIPE_SECRET_KEY_2;")
    assert lines[2].endswith("process.env.STRIPE_SECRET_KEY;")


def test_two_secrets_on_one_line(tmp_path):
    other = "sk_live_" + "Z9y8X7w6" * 3
    root = repo(tmp_path, {"a.js": f'const keys = ["{LIVE_KEY}", "{other}"];\n'})
    plan_and_apply(root)
    assert (root / "a.js").read_text() == (
        "const keys = [process.env.STRIPE_SECRET_KEY, process.env.STRIPE_SECRET_KEY_2];\n"
    )


def test_crlf_line_endings_are_preserved(tmp_path):
    root = tmp_path
    (root / "a.js").write_bytes(f'const a = 1;\r\nconst k = "{LIVE_KEY}";\r\n'.encode())
    plan_and_apply(root)
    assert (root / "a.js").read_bytes() == (
        b"const a = 1;\r\nconst k = process.env.STRIPE_SECRET_KEY;\r\n"
    )


@pytest.mark.parametrize(
    "relative,content",
    [
        ("config.json", '{{"password": "{p}"}}\n'),
        ("deploy.yaml", 'password: "{p}"\n'),
        (".env", "DB_PASSWORD={p}\n"),
        ("main.go", 'var password = "{p}"\n'),
        ("a.py", 'url = f"Bearer {p}"\npassword = "prefix {p}"\n'),
        ("b.php", '<?php class A {{ private $password = "{p}"; }}\n'),
    ],
)
def test_unsafe_targets_go_to_review_untouched(tmp_path, relative, content):
    root = repo(tmp_path, {relative: content.format(p=PASSWORD)})
    before = (root / relative).read_text()
    plan, results = plan_and_apply(root)
    assert results["modified_files"] == []
    assert (root / relative).read_text() == before
    assert all(item["suggested_action"] for item in plan["requires_review"])


def test_private_key_blocks_go_to_review(tmp_path):
    root = repo(tmp_path, {"a.py": 'KEY = """-----BEGIN RSA PRIVATE KEY-----\nabc\n"""\n'})
    plan, results = plan_and_apply(root)
    assert results["fixes_applied"] == 0 and len(plan["requires_review"]) == 1


def test_sql_injection_is_review_only_and_the_code_is_untouched(tmp_path):
    """Regression: the old rewrite produced code that no longer parsed."""
    source = 'db.query("SELECT * FROM users WHERE id = " + id);\n'
    root = repo(tmp_path, {"a.js": source})
    plan, results = plan_and_apply(root)
    assert (root / "a.js").read_text() == source
    assert results["fixes_applied"] == 0
    assert "parameterized" in plan["requires_review"][0]["suggested_action"]


def test_edit_that_breaks_the_file_is_reverted(tmp_path, monkeypatch):
    source = f'KEY = "{LIVE_KEY}"\n'
    root = repo(tmp_path, {"a.py": source})
    monkeypatch.setattr(SmartFixer, "_still_parses", lambda *a: False)
    _, results = plan_and_apply(root)
    assert (root / "a.py").read_text() == source
    assert results["fixes_failed"] == 1 and results["modified_files"] == []
    assert not (root / ".env.example").exists()


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_javascript_fix_passes_node_syntax_check(tmp_path):
    root = repo(tmp_path, {"a.js": f'const cfg = {{ key: "{LIVE_KEY}", n: 1 }};\nmodule.exports = cfg;\n'})
    _, results = plan_and_apply(root)
    assert results["fixes_applied"] == 1 and results["fixes_failed"] == 0


def test_path_traversal_is_rejected(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (tmp_path / "outside.py").write_text(f'KEY = "{LIVE_KEY}"\n')
    fixer = SmartFixer(str(root))
    with pytest.raises(ValueError):
        fixer._resolve("../outside.py")

    forged = {
        "category": "secret",
        "type": "Stripe Live Secret Key",
        "file_path": "../outside.py",
        "line_number": 1,
        "_raw": LIVE_KEY,
        "_span": (7, 7 + len(LIVE_KEY)),
    }
    plan = fixer.generate_comprehensive_fix_plan([forged])
    assert plan["fixable_automatically"] == []
    assert LIVE_KEY in (tmp_path / "outside.py").read_text()


def test_public_plan_and_pr_body_contain_no_secret(tmp_path):
    root = repo(tmp_path, {"a.py": f'KEY = "{LIVE_KEY}"\n', "c.json": f'{{"password": "{PASSWORD}"}}\n'})
    plan, results = plan_and_apply(root)
    assert LIVE_KEY not in str(public_plan(plan))
    assert PASSWORD not in str(public_plan(plan))
    body = build_pr_body(results, plan)
    assert LIVE_KEY not in body and PASSWORD not in body
    assert "Rotate" in body and "STRIPE_SECRET_KEY" in body
    assert "manual review" in body
    assert "c.json" in body


def dependency(package, **overrides):
    return {
        "category": "dependency",
        "type": "Insecure Dependency",
        "severity": "HIGH",
        "package": package,
        "package_dir": ".",
        "file_path": "package.json",
        "line_number": None,
        "fixable": True,
        "id": package,
        **overrides,
    }


def apply_dependencies(root, monkeypatch, remaining, findings, changes_lock=True):
    def fake_fix(repo_path, package_dir):
        if changes_lock:
            (root / "package-lock.json").write_text('{"updated": true}')
        return remaining

    monkeypatch.setattr(smart_fixer, "fix_dependencies", fake_fix)
    fixer = SmartFixer(str(root))
    return fixer.apply_smart_fixes(fixer.generate_comprehensive_fix_plan(findings))


def test_partial_dependency_fix_is_reported_per_package(tmp_path, monkeypatch):
    root = repo(tmp_path, {"package.json": "{}", "package-lock.json": "{}"})
    results = apply_dependencies(
        root, monkeypatch, {"stubborn"}, [dependency("fixed"), dependency("stubborn")]
    )
    assert [fix["description"].split()[1] for fix in results["applied"]] == ["fixed"]
    assert results["fixes_failed"] == 1
    assert results["modified_files"] == ["package-lock.json"]


def test_dependency_fix_that_changes_nothing_commits_nothing(tmp_path, monkeypatch):
    root = repo(tmp_path, {"package.json": "{}", "package-lock.json": "{}"})
    results = apply_dependencies(root, monkeypatch, set(), [dependency("a")], changes_lock=False)
    assert results["fixes_applied"] == 0 and results["modified_files"] == []


def test_npm_failure_is_reported(tmp_path, monkeypatch):
    root = repo(tmp_path, {"package.json": "{}", "package-lock.json": "{}"})
    results = apply_dependencies(root, monkeypatch, None, [dependency("a")])
    assert results["fixes_failed"] == 1 and results["modified_files"] == []


@pytest.mark.parametrize(
    "overrides,expected",
    [
        ({"breaking_fix": True}, "major version"),
        ({"pinned": True, "fix_available": True}, "pinned"),
        ({"has_lockfile": False}, "package-lock"),
        ({}, "No patched version"),
    ],
)
def test_unfixable_dependencies_explain_why(tmp_path, overrides, expected):
    plan = SmartFixer(str(tmp_path)).generate_comprehensive_fix_plan(
        [dependency("a", fixable=False, **overrides)]
    )
    assert expected in plan["requires_review"][0]["reason"]
