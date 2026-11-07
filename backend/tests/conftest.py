"""
Test harness.

Git is real: repositories are cloned from and pushed to a local bare repository.
Only the network edges are faked: GitHub's REST API, Stripe and outbound webhooks.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

_TMP = tempfile.mkdtemp(prefix="fixsec-tests-")
os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{_TMP}/test.db",
        "WORKSPACE_DIR": f"{_TMP}/workspace",
        "SECRET_KEY": "test-secret-key-for-the-test-suite-only",
        "SCHEDULER_ENABLED": "false",
        "ENVIRONMENT": "test",
        "GITHUB_CLIENT_ID": "test-client-id",
        "GITHUB_CLIENT_SECRET": "test-client-secret",
        "STRIPE_SECRET_KEY": "sk_test_unit",
        "STRIPE_WEBHOOK_SECRET": "whsec_unit",
        "STRIPE_PRO_PRICE_ID": "price_pro",
        "STRIPE_TEAM_PRICE_ID": "price_team",
        "STRIPE_STARTER_PRICE_ID": "price_starter",
    }
)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from core import github as github_module  # noqa: E402
from core.scanner import npm_audit  # noqa: E402
from core.security import create_session_token, encrypt_token  # noqa: E402
from db.models import Base, Subscription, User  # noqa: E402
from db.session import SessionLocal, engine  # noqa: E402

# Built at runtime so this file never contains anything shaped like a real key.
LIVE_KEY = "sk_live_" + "a1B2c3D4" * 3
PASSWORD = "hunter2-" + "Zq9" * 3


def _git(cwd, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.test", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


SEED_FILES = {
    "app.py": f'"""Billing helpers."""\nSTRIPE_KEY = "{LIVE_KEY}"\n\n\ndef key():\n    return STRIPE_KEY\n',
    "server.js": (
        f'const dbPassword = "{PASSWORD}";\n'
        'const q = "SELECT * FROM users WHERE id = " + userId;\n'
        "module.exports = {{ dbPassword, q }};\n"
    ).replace("{{", "{").replace("}}", "}"),
    "deploy.json": f'{{"password": "{PASSWORD}x"}}\n',
    "tests/test_login.py": 'password = "correct-horse-battery"\n',
    "node_modules/pkg/index.js": f'const k = "{LIVE_KEY}";\n',
}


@pytest.fixture
def seeded_remote(tmp_path):
    """A bare repository acting as origin, plus its file:// URL."""
    bare = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(bare)], check=True, capture_output=True
    )
    work = tmp_path / "seed"
    work.mkdir()
    _git(work, "init", "-b", "main")
    for relative, content in SEED_FILES.items():
        path = work / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _git(work, "add", "-A", "-f")
    _git(work, "commit", "-m", "seed")
    _git(work, "remote", "add", "origin", str(bare))
    _git(work, "push", "origin", "main")
    return SimpleNamespace(path=bare, url=bare.as_uri())


class FakeResponse:
    def __init__(self, status_code, body=None, headers=None):
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}
        self.text = json.dumps(body)

    def json(self):
        return self._body


class FakeGitHub:
    """Stands in for api.github.com."""

    def __init__(self):
        self.repos = {}
        self.pull_requests = []
        self.requests = []
        self.reject_token = False

    def add_repo(self, full_name, clone_url, push=True, private=True):
        self.repos[full_name] = {
            "id": len(self.repos) + 1,
            "name": full_name.split("/")[1],
            "full_name": full_name,
            "private": private,
            "clone_url": clone_url,
            "html_url": f"https://github.test/{full_name}",
            "default_branch": "main",
            "permissions": {"push": push},
        }

    def __call__(self, method, url, headers=None, timeout=None, **kwargs):
        assert timeout, "every GitHub call must set a timeout"
        path = url.replace(github_module.settings.GITHUB_API_URL, "")
        self.requests.append((method, path, kwargs))
        if self.reject_token:
            return FakeResponse(401, {"message": "Bad credentials"})
        if path == "/user/repos":
            return FakeResponse(200, list(self.repos.values()))
        if method == "POST" and path.endswith("/pulls"):
            if any(pr["head"] == kwargs["json"]["head"] for pr in self.pull_requests):
                return FakeResponse(422, {"message": "A pull request already exists"})
            pr = {**kwargs["json"], "number": 7, "html_url": "https://github.test/pr/7"}
            self.pull_requests.append(pr)
            return FakeResponse(201, pr)
        if method == "GET" and path.endswith("/pulls"):
            return FakeResponse(200, self.pull_requests)
        if method == "PATCH":
            self.pull_requests[0]["body"] = kwargs["json"]["body"]
            return FakeResponse(200, self.pull_requests[0])
        full_name = path.replace("/repos/", "")
        if full_name in self.repos:
            return FakeResponse(200, self.repos[full_name])
        return FakeResponse(404, {"message": "Not Found"})


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def github(monkeypatch):
    fake = FakeGitHub()
    monkeypatch.setattr(github_module.requests, "request", fake)
    return fake


@pytest.fixture(autouse=True)
def no_real_npm(monkeypatch):
    """Dependency auditing has its own tests. Elsewhere it must not hit the network."""
    monkeypatch.setattr(npm_audit, "npm_path", lambda: None)


@pytest.fixture
def client():
    return TestClient(main.app, raise_server_exceptions=False)


@pytest.fixture
def make_user(db):
    def create(github_id="1", plan=None):
        user = User(
            github_id=github_id,
            name=f"user{github_id}",
            email=f"user{github_id}@example.test",
            github_token=encrypt_token(f"gho_token_for_{github_id}"),
        )
        db.add(user)
        db.commit()
        if plan:
            db.add(
                Subscription(
                    user_id=user.id, plan_id=plan, status="active", stripe_subscription_id=f"sub_{github_id}"
                )
            )
            db.commit()
        headers = {"Authorization": f"Bearer {create_session_token(user.id)}"}
        return SimpleNamespace(id=user.id, model=user, headers=headers)

    return create
