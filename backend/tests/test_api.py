import ast
import hashlib
import hmac
import json
import subprocess
import time
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
import stripe

from conftest import LIVE_KEY, PASSWORD
from config import settings
from core import notifications, scheduler
from core.billing import BillingManager
from core.security import create_session_token, decrypt_token, encrypt_token
from core.workspace import get_workspace_manager
from db.models import PullRequest, Repository, Scan, ScheduledScan, Subscription, User, Vulnerability

REPO = "acme/app"


def show(bare, ref, path=None):
    target = f"{ref}:{path}" if path else ref
    return subprocess.run(
        ["git", "--git-dir", str(bare), "show", target], capture_output=True, text=True
    )


def changed_files(bare, ref):
    result = subprocess.run(
        ["git", "--git-dir", str(bare), "diff", "--name-only", "main", ref],
        capture_output=True,
        text=True,
    )
    return set(result.stdout.split())


# ---------------------------------------------------------------- authentication


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/repos"),
        ("post", "/scan/"),
        ("get", "/scan/1"),
        ("post", "/pr/fix-plan"),
        ("post", "/pr/auto-fix"),
        ("get", "/history/overview"),
        ("get", f"/history/scan-history?repo={REPO}"),
        ("get", f"/history/security-score?repo={REPO}"),
        ("get", "/schedule/list"),
        ("post", "/schedule/test-notification"),
        ("get", "/billing/subscription"),
        ("get", "/billing/usage"),
        ("get", "/auth/me"),
    ],
)
@pytest.mark.parametrize("header", [None, "Bearer not-a-valid-token", "anything"])
def test_every_protected_route_rejects_bad_credentials(client, method, path, header):
    """Regression: most routes accepted any non-empty Authorization header."""
    headers = {"Authorization": header} if header else {}
    response = getattr(client, method)(path, headers=headers)
    assert response.status_code == 401


def test_session_for_a_deleted_user_is_rejected(client):
    headers = {"Authorization": f"Bearer {create_session_token(999)}"}
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_expired_session_is_rejected(client, make_user, monkeypatch):
    user = make_user()
    monkeypatch.setattr(settings, "SESSION_TTL_HOURS", -1)
    headers = {"Authorization": f"Bearer {create_session_token(user.id)}"}
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_billing_endpoints_accept_the_bearer_header(client, make_user):
    """Regression: these read a query parameter, so the UI always got 401."""
    user = make_user()
    assert client.get("/billing/subscription", headers=user.headers).status_code == 200
    assert client.get("/billing/usage", headers=user.headers).status_code == 200


def test_login_sets_state_and_callback_rejects_a_mismatch(client):
    login = client.get("/auth/github/login", follow_redirects=False)
    assert login.status_code == 307
    assert "state=" in login.headers["location"]
    assert "fixsec_oauth_state" in login.headers["set-cookie"]

    bad = client.get("/auth/github/callback?code=x&state=forged", follow_redirects=False)
    assert bad.headers["location"].endswith("/login?error=invalid_state")


def _complete_oauth(client, monkeypatch, github, profile):
    monkeypatch.setattr(
        "routes.auth.requests.post",
        lambda *a, **k: SimpleNamespace(json=lambda: {"access_token": "gho_real_token"}),
    )
    monkeypatch.setattr("routes.auth.github.get_user", lambda token: profile)
    monkeypatch.setattr("routes.auth.github.get_primary_email", lambda token: None)
    login = client.get("/auth/github/login", follow_redirects=False)
    state = login.headers["location"].split("state=")[1]
    return client.get(f"/auth/github/callback?code=abc&state={state}", follow_redirects=False)


def test_oauth_flow_issues_a_session_and_encrypts_the_github_token(client, monkeypatch, github, db):
    callback = _complete_oauth(
        client, monkeypatch, github, {"id": 42, "login": "octo", "name": None, "email": None}
    )
    location = callback.headers["location"]
    assert "/dashboard#token=" in location
    assert "gho_real_token" not in location

    user = db.query(User).filter(User.github_id == "42").one()
    assert user.name == "octo"
    assert user.github_token != "gho_real_token"
    assert decrypt_token(user.github_token) == "gho_real_token"

    session = location.split("#token=")[1]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {session}"})
    assert me.json()["plan"] == "Free"


def test_two_users_with_private_emails_can_both_sign_in(client, monkeypatch, github, db):
    """Regression: the second user with no public email hit a unique constraint."""
    for github_id in (1, 2):
        _complete_oauth(
            client, monkeypatch, github, {"id": github_id, "login": f"u{github_id}", "email": None}
        )
        client.cookies.clear()
    assert db.query(User).count() == 2


def test_expired_github_token_returns_401_so_the_ui_can_reauthenticate(client, make_user, github):
    """Regression: GitHub errors came back as HTTP 200 and looked like an empty list."""
    github.reject_token = True
    assert client.get("/repos", headers=make_user().headers).status_code == 401


def test_undecryptable_github_token_asks_for_login(client, make_user, db, github):
    user = make_user()
    user.model.github_token = "not-encrypted"
    db.commit()
    assert client.get("/repos", headers=user.headers).status_code == 401


def test_production_refuses_the_default_secret_key(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SECRET_KEY", "your-secret-key-change-in-production")
    with pytest.raises(RuntimeError):
        settings.validate()


def test_postgres_scheme_is_normalised(monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", "postgres://u:p@h/db")
    assert settings.database_url == "postgresql://u:p@h/db"


# ------------------------------------------------------------------------- scans


def test_scan_persists_and_masks_results(client, make_user, github, seeded_remote, db):
    github.add_repo(REPO, seeded_remote.url)
    user = make_user()

    response = client.post("/scan/", json={"full_name": REPO}, headers=user.headers)
    assert response.status_code == 200, response.text
    data = response.json()

    assert LIVE_KEY not in response.text and PASSWORD not in response.text
    found = {(v["file_path"], v["category"]) for v in data["vulnerabilities"]}
    assert ("app.py", "secret") in found
    assert ("server.js", "sql_injection") in found
    assert not any("node_modules" in v["file_path"] for v in data["vulnerabilities"])
    assert not any(v["file_path"].startswith("tests/") for v in data["vulnerabilities"])
    assert data["security_score"]["score"] < 100
    assert data["warnings"] == []  # no package.json in this repository

    scan = db.query(Scan).one()
    assert (scan.status, scan.issues_found) == ("completed", data["count"])
    assert LIVE_KEY not in scan.result_json
    assert db.query(Vulnerability).count() == data["count"]
    assert client.get(f"/scan/{data['scan_id']}", headers=user.headers).json() == data


def test_workspace_is_removed_after_a_scan(client, make_user, github, seeded_remote):
    github.add_repo(REPO, seeded_remote.url)
    client.post("/scan/", json={"full_name": REPO}, headers=make_user().headers)
    assert get_workspace_manager().get_workspace_stats()["total_workspaces"] == 0


def test_github_token_is_not_stored_in_the_clone(make_user, github, seeded_remote):
    manager = get_workspace_manager()
    with manager.checkout(REPO, seeded_remote.url, "main", "gho_secret_value") as repo:
        config = (repo.git_dir + "/config")
        assert "gho_secret_value" not in open(config, encoding="utf-8").read()


def test_free_plan_daily_limit(client, make_user, github, seeded_remote):
    """Regression: this check crashed, so every scan on a free plan returned 500."""
    github.add_repo(REPO, seeded_remote.url)
    user = make_user()
    assert client.post("/scan/", json={"full_name": REPO}, headers=user.headers).status_code == 200

    second = client.post("/scan/", json={"full_name": REPO}, headers=user.headers)
    assert second.status_code == 402
    assert second.json()["detail"]["upgrade_required"] is True
    assert second.json()["detail"]["feature"] == "scan"


def test_failed_scan_does_not_use_the_allowance(client, make_user, github, tmp_path):
    github.add_repo(REPO, (tmp_path / "missing.git").as_uri())
    user = make_user()
    failed = client.post("/scan/", json={"full_name": REPO}, headers=user.headers)
    assert failed.status_code == 422
    assert client.get("/billing/usage", headers=user.headers).json()["usage"]["scans_today"]["current"] == 0


def test_free_plan_repository_limit(client, make_user, github, seeded_remote, db):
    github.add_repo(REPO, seeded_remote.url)
    github.add_repo("acme/other", seeded_remote.url)
    user = make_user()
    client.post("/scan/", json={"full_name": REPO}, headers=user.headers)
    db.query(Scan).delete()  # a new day
    db.commit()
    response = client.post("/scan/", json={"full_name": "acme/other"}, headers=user.headers)
    assert response.status_code == 402
    assert response.json()["detail"]["feature"] == "repos"


def test_paid_plan_has_no_daily_limit(client, make_user, github, seeded_remote):
    github.add_repo(REPO, seeded_remote.url)
    user = make_user(plan="starter")
    for _ in range(3):
        assert client.post("/scan/", json={"full_name": REPO}, headers=user.headers).status_code == 200


@pytest.mark.parametrize("name", ["", "noslash", "a/b/../../user", "../etc", None, 5])
def test_invalid_repository_names_are_rejected(client, make_user, name):
    assert client.post("/scan/", json={"full_name": name}, headers=make_user().headers).status_code == 400


def test_unknown_repository_returns_404(client, make_user, github):
    assert client.post("/scan/", json={"full_name": "acme/nope"}, headers=make_user().headers).status_code == 404


def test_clone_failure_does_not_expose_credentials(client, make_user, github, tmp_path):
    github.add_repo(REPO, (tmp_path / "gone.git").as_uri())
    response = client.post("/scan/", json={"full_name": REPO}, headers=make_user().headers)
    assert response.status_code == 422
    assert "gho_" not in response.text and "file:" not in response.text


def test_history_is_isolated_between_users(client, make_user, github, seeded_remote):
    """Regression: anyone could read any repository's findings."""
    github.add_repo(REPO, seeded_remote.url)
    owner, stranger = make_user("1"), make_user("2")
    scan_id = client.post("/scan/", json={"full_name": REPO}, headers=owner.headers).json()["scan_id"]

    assert client.get(f"/history/scan-history?repo={REPO}", headers=owner.headers).json()["total_scans"] == 1
    assert client.get("/history/overview", headers=owner.headers).json()["total_repos"] == 1

    assert client.get(f"/history/scan-history?repo={REPO}", headers=stranger.headers).json()["total_scans"] == 0
    assert client.get("/history/overview", headers=stranger.headers).json()["total_repos"] == 0
    assert client.get(f"/history/security-score?repo={REPO}", headers=stranger.headers).status_code == 404
    assert client.get(f"/scan/{scan_id}", headers=stranger.headers).status_code == 404


def test_history_survives_a_restart_and_scores_match_the_scan(client, make_user, github, seeded_remote):
    """Regression: history lived in process memory and used a second, different score."""
    github.add_repo(REPO, seeded_remote.url)
    user = make_user(plan="pro")
    scan = client.post("/scan/", json={"full_name": REPO}, headers=user.headers).json()
    score = client.get(f"/history/security-score?repo={REPO}", headers=user.headers).json()
    assert score["current_score"]["score"] == scan["security_score"]["score"]


# ---------------------------------------------------------------------- auto-fix


def test_auto_fix_end_to_end(client, make_user, github, seeded_remote, db):
    github.add_repo(REPO, seeded_remote.url)
    user = make_user(plan="pro")
    client.post("/scan/", json={"full_name": REPO}, headers=user.headers)

    response = client.post("/pr/auto-fix", json={"full_name": REPO}, headers=user.headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "PR Created" and data["url"]
    assert data["fixes_applied"] == 2

    branch = "fixsec/auto-fix-security"
    assert changed_files(seeded_remote.path, branch) == {
        "app.py", "server.js", ".env.example", ".gitignore",
    }

    app_py = show(seeded_remote.path, branch, "app.py").stdout
    ast.parse(app_py)
    assert LIVE_KEY not in app_py and 'os.environ["STRIPE_SECRET_KEY"]' in app_py

    assert show(seeded_remote.path, branch, ".env").returncode != 0
    assert ".env" in show(seeded_remote.path, branch, ".gitignore").stdout

    # The SQL line and the JSON secret are left alone and flagged for review.
    assert 'SELECT * FROM users WHERE id = " + userId' in show(seeded_remote.path, branch, "server.js").stdout
    assert PASSWORD in show(seeded_remote.path, branch, "deploy.json").stdout

    body = github.pull_requests[0]["body"]
    assert "Rotate" in body and "Ready to merge" not in body
    assert LIVE_KEY not in body and PASSWORD not in body

    assert db.query(PullRequest).one().fixes_applied == 2
    assert get_workspace_manager().get_workspace_stats()["total_workspaces"] == 0


def test_auto_fix_uses_server_side_findings_not_client_input(client, make_user, github, seeded_remote):
    """Regression: client-supplied paths allowed arbitrary file reads and writes."""
    github.add_repo(REPO, seeded_remote.url)
    user = make_user(plan="pro")
    forged = [{"category": "secret", "type": "x", "file_path": "../../main.py", "line_number": 1}]
    response = client.post(
        "/pr/auto-fix", json={"full_name": REPO, "vulnerabilities": forged}, headers=user.headers
    )
    assert response.status_code == 200
    assert "../../main.py" not in changed_files(seeded_remote.path, "fixsec/auto-fix-security")


def test_running_auto_fix_again_updates_the_existing_pr(client, make_user, github, seeded_remote):
    github.add_repo(REPO, seeded_remote.url)
    user = make_user(plan="team")
    client.post("/pr/auto-fix", json={"full_name": REPO}, headers=user.headers)
    second = client.post("/pr/auto-fix", json={"full_name": REPO}, headers=user.headers)
    assert second.json()["status"] == "PR Updated"
    assert second.json()["url"] == "https://github.test/pr/7"
    assert len(github.pull_requests) == 1


@pytest.mark.parametrize("plan", [None, "starter"])
def test_auto_fix_requires_a_plan_with_the_feature(client, make_user, github, plan):
    response = client.post("/pr/auto-fix", json={"full_name": REPO}, headers=make_user(plan=plan).headers)
    assert response.status_code == 402
    assert response.json()["detail"]["feature"] == "auto_fix"


def test_auto_fix_needs_push_access(client, make_user, github, seeded_remote):
    github.add_repo(REPO, seeded_remote.url, push=False)
    response = client.post("/pr/auto-fix", json={"full_name": REPO}, headers=make_user(plan="pro").headers)
    assert response.status_code == 403


def test_fix_plan_is_available_on_free_and_contains_no_secrets(client, make_user, github, seeded_remote):
    github.add_repo(REPO, seeded_remote.url)
    response = client.post("/pr/fix-plan", json={"full_name": REPO}, headers=make_user().headers)
    assert response.status_code == 200, response.text
    assert LIVE_KEY not in response.text and PASSWORD not in response.text

    data = response.json()
    assert data["can_auto_fix"] is False
    plan = data["fix_plan"]
    assert plan["total_fixes"] == 2
    assert {item["vulnerability"]["file_path"] for item in plan["requires_review"]} == {
        "server.js", "deploy.json",
    }
    assert any("os.environ" in item["diff"]["after"] for item in plan["fixable_automatically"])


# ---------------------------------------------------------------------- schedules


def test_schedule_lifecycle_and_ownership(client, make_user, github, seeded_remote):
    github.add_repo(REPO, seeded_remote.url)
    owner, stranger = make_user("1", plan="team"), make_user("2", plan="team")

    created = client.post(
        "/schedule/create",
        json={"repo": REPO, "frequency": "daily", "notification_channels": [{"type": "email", "email": "a@b.test"}]},
        headers=owner.headers,
    )
    assert created.status_code == 200, created.text
    schedule = created.json()["schedule"]
    assert "user_token" not in created.text
    url = f"/schedule/{schedule['schedule_id']}"

    assert client.get(url, headers=stranger.headers).status_code == 404
    assert client.delete(url, headers=stranger.headers).status_code == 404
    assert client.put(url, json={"enabled": False}, headers=stranger.headers).status_code == 404

    assert client.put(url, json={"enabled": False}, headers=owner.headers).json()["schedule"]["status"] == "PAUSED"
    assert client.get("/schedule/list", headers=owner.headers).json()["total"] == 1
    assert client.delete(url, headers=owner.headers).status_code == 200
    assert client.get(url, headers=owner.headers).status_code == 404


@pytest.mark.parametrize("plan", [None, "pro"])
def test_scheduling_requires_the_team_plan(client, make_user, plan):
    response = client.post(
        "/schedule/create", json={"repo": REPO, "frequency": "daily"}, headers=make_user(plan=plan).headers
    )
    assert response.status_code == 402


def _due_schedule(db, user_id, channels="[]"):
    schedule = ScheduledScan(
        user_id=user_id,
        repo_name=REPO,
        frequency="weekly",
        notification_channels=channels,
        enabled=True,
        next_run=datetime.utcnow() - timedelta(minutes=1),
        run_count=0,
    )
    db.add(schedule)
    db.commit()
    return schedule.id


def test_scheduler_runs_due_scans_and_notifies(make_user, github, seeded_remote, db, monkeypatch):
    """Regression: nothing ever ran schedules. They were created and then ignored."""
    github.add_repo(REPO, seeded_remote.url)
    user = make_user(plan="team")
    sent = []
    monkeypatch.setattr(
        scheduler, "send_notifications", lambda channels, result, repo: sent.append((repo, result["count"])) or []
    )
    schedule_id = _due_schedule(db, user.id)

    assert scheduler.run_due_scans() == 1
    db.expire_all()
    schedule = db.get(ScheduledScan, schedule_id)
    assert schedule.run_count == 1
    assert schedule.next_run > datetime.utcnow() + timedelta(days=6)
    assert json.loads(schedule.last_result)["status"] == "SUCCESS"
    assert db.query(Scan).one().trigger == "scheduled"
    assert sent and sent[0][0] == REPO

    assert scheduler.run_due_scans() == 0


def test_a_schedule_is_claimed_only_once(make_user, db):
    """Several server workers run this loop, and only one may win each schedule."""
    user = make_user(plan="team")
    schedule_id = _due_schedule(db, user.id)
    stale = db.get(ScheduledScan, schedule_id).next_run

    assert scheduler.claim_due_scans(db) == [schedule_id]

    # A second worker that read the row earlier must lose the conditional update.
    from sqlalchemy import update

    result = db.execute(
        update(ScheduledScan)
        .where(ScheduledScan.id == schedule_id, ScheduledScan.next_run == stale)
        .values(next_run=datetime.utcnow())
    )
    assert result.rowcount == 0


def test_scheduled_scan_failure_is_recorded(make_user, github, db, tmp_path):
    github.add_repo(REPO, (tmp_path / "gone.git").as_uri())
    user = make_user(plan="team")
    schedule_id = _due_schedule(db, user.id)
    scheduler.run_due_scans()
    db.expire_all()
    assert json.loads(db.get(ScheduledScan, schedule_id).last_result)["status"] == "FAILED"


def test_schedule_pauses_after_downgrade(make_user, github, db):
    user = make_user()
    schedule_id = _due_schedule(db, user.id)
    scheduler.run_due_scans()
    db.expire_all()
    schedule = db.get(ScheduledScan, schedule_id)
    assert schedule.enabled is False
    assert json.loads(schedule.last_result)["status"] == "PAUSED"


@pytest.mark.parametrize(
    "url,channel",
    [
        ("http://example.com/hook", "webhook"),
        ("https://127.0.0.1/hook", "webhook"),
        ("https://169.254.169.254/latest/meta-data", "webhook"),
        ("https://10.0.0.1/", "webhook"),
        ("https://[::1]/", "webhook"),
        ("https://localhost/", "webhook"),
        ("file:///etc/passwd", "webhook"),
        ("https://example.com/hook", "slack"),
        ("https://example.com/hook", "discord"),
        ("", "webhook"),
    ],
)
def test_webhook_urls_cannot_reach_internal_services(url, channel):
    with pytest.raises(ValueError):
        notifications.validate_webhook_url(url, channel)


def test_test_notification_blocks_ssrf_through_the_api(client, make_user):
    response = client.post(
        "/schedule/test-notification",
        json={"type": "webhook", "webhook_url": "https://169.254.169.254/"},
        headers=make_user(plan="team").headers,
    )
    assert response.status_code == 400


def test_email_without_sendgrid_reports_an_error_not_success(monkeypatch):
    """Regression: email claimed success while sending nothing."""
    monkeypatch.setattr(settings, "SENDGRID_API_KEY", None)
    (result,) = notifications.send_notifications(
        [{"type": "email", "email": "a@b.test"}], {"count": 0}, REPO
    )
    assert result["status"] == "error"


def test_email_is_sent_through_sendgrid(monkeypatch):
    monkeypatch.setattr(settings, "SENDGRID_API_KEY", "key")
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs["json"]))
        return SimpleNamespace(status_code=202)

    monkeypatch.setattr(notifications.requests, "post", fake_post)
    (result,) = notifications.send_notifications(
        [{"type": "email", "email": "a@b.test"}], {"count": 2}, REPO
    )
    assert result["status"] == "success"
    assert calls[0][1]["personalizations"][0]["to"][0]["email"] == "a@b.test"


# ------------------------------------------------------------------------ billing


def signed_event(event):
    payload = json.dumps(event)
    timestamp = int(time.time())
    digest = hmac.new(
        settings.STRIPE_WEBHOOK_SECRET.encode(), f"{timestamp}.{payload}".encode(), hashlib.sha256
    ).hexdigest()
    return payload, {"stripe-signature": f"t={timestamp},v1={digest}"}


def post_event(client, event):
    payload, headers = signed_event(event)
    return client.post("/billing/webhook", content=payload, headers=headers)


def stripe_subscription(user_id, status="active", price="price_pro", cancel=False):
    return {
        "id": "sub_123",
        "customer": "cus_123",
        "status": status,
        "cancel_at_period_end": cancel,
        "metadata": {"user_id": str(user_id), "plan_id": "pro"},
        "items": {
            "data": [
                {
                    "price": {"id": price},
                    "current_period_start": 1_800_000_000,
                    "current_period_end": 1_802_000_000,
                }
            ]
        },
    }


def test_webhook_rejects_a_bad_signature(client):
    response = client.post(
        "/billing/webhook", content="{}", headers={"stripe-signature": "t=1,v1=forged"}
    )
    assert response.status_code == 400


def test_webhook_subscription_lifecycle(client, make_user, db, monkeypatch):
    user = make_user()
    monkeypatch.setattr(
        stripe.Subscription, "retrieve", lambda subscription_id: stripe_subscription(user.id)
    )
    session = {
        "subscription": "sub_123",
        "metadata": {"user_id": str(user.id), "plan_id": "pro"},
    }
    event = {"type": "checkout.session.completed", "data": {"object": session}}
    assert post_event(client, event).status_code == 200
    plan = client.get("/billing/subscription", headers=user.headers).json()
    assert plan["subscription"]["plan_id"] == "pro"

    # Delivering the same event twice must not create a second subscription.
    post_event(client, event)
    assert db.query(Subscription).count() == 1

    # Plan change in the Stripe portal.
    post_event(
        client,
        {
            "type": "customer.subscription.updated",
            "data": {"object": stripe_subscription(user.id, price="price_team")},
        },
    )
    assert client.get("/billing/subscription", headers=user.headers).json()["subscription"]["plan_id"] == "team"

    # Failed renewal keeps access during Stripe's retry window.
    post_event(client, {"type": "invoice.payment_failed", "data": {"object": {"subscription": "sub_123"}}})
    assert client.get("/billing/check-limits/auto_fix", headers=user.headers).json()["allowed"] is True

    # Regression: deletion events were ignored, so canceled plans stayed active forever.
    post_event(
        client,
        {"type": "customer.subscription.deleted", "data": {"object": {"id": "sub_123"}}},
    )
    db.expire_all()
    assert client.get("/billing/subscription", headers=user.headers).json()["subscription"]["plan_id"] == "free"
    assert client.get("/billing/check-limits/auto_fix", headers=user.headers).json()["allowed"] is False


def test_cancel_keeps_access_until_the_period_ends(client, make_user, monkeypatch):
    """Regression: canceling removed paid access immediately."""
    user = make_user(plan="pro")
    calls = []
    monkeypatch.setattr(stripe.Subscription, "modify", lambda sid, **k: calls.append(k))
    assert client.post("/billing/cancel", headers=user.headers).status_code == 200
    assert calls == [{"cancel_at_period_end": True}]

    current = client.get("/billing/subscription", headers=user.headers).json()["subscription"]
    assert current["plan_id"] == "pro" and current["cancel_at_period_end"] is True


def test_checkout_uses_the_plan_price(client, make_user, monkeypatch):
    user = make_user()
    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(url="https://checkout.test/session")

    monkeypatch.setattr(stripe.checkout.Session, "create", fake_create)
    response = client.post("/billing/subscribe", json={"plan_id": "starter"}, headers=user.headers)
    assert response.json()["checkout_url"] == "https://checkout.test/session"
    assert calls[0]["line_items"][0]["price"] == "price_starter"
    assert calls[0]["subscription_data"]["metadata"]["user_id"] == str(user.id)


def test_existing_subscriber_is_sent_to_the_portal_not_a_second_checkout(client, make_user, db, monkeypatch):
    """Two checkouts would mean two live subscriptions and double billing."""
    user = make_user(plan="starter")
    db.query(Subscription).update({"stripe_customer_id": "cus_1"})
    db.commit()
    monkeypatch.setattr(
        stripe.billing_portal.Session, "create", lambda **k: SimpleNamespace(url="https://portal.test")
    )
    monkeypatch.setattr(stripe.checkout.Session, "create", lambda **k: pytest.fail("second checkout"))
    response = client.post("/billing/subscribe", json={"plan_id": "pro"}, headers=user.headers)
    assert response.json()["checkout_url"] == "https://portal.test"


def test_unconfigured_stripe_returns_a_clear_503(client, make_user, monkeypatch):
    monkeypatch.setitem(BillingManager.PLANS["pro"], "stripe_price_id", "")
    response = client.post("/billing/subscribe", json={"plan_id": "pro"}, headers=make_user().headers)
    assert response.status_code == 503


def test_invalid_plan_is_rejected(client, make_user):
    for plan in ("free", "enterprise"):
        response = client.post("/billing/subscribe", json={"plan_id": plan}, headers=make_user(github_id=plan).headers)
        assert response.status_code == 400


def test_public_plans_hide_stripe_ids(client):
    plans = client.get("/billing/plans").json()["plans"]
    assert set(plans) == {"free", "starter", "pro", "team"}
    assert "stripe_price_id" not in plans["pro"]


def test_token_encryption_round_trip():
    ciphertext = encrypt_token("gho_abc")
    assert ciphertext != "gho_abc" and decrypt_token(ciphertext) == "gho_abc"
    assert decrypt_token("plaintext-from-an-older-version") is None
