"""
Thin GitHub REST client. Every call has a timeout, and failures surface as
GitHubError so they map to a meaningful HTTP response instead of a crash.
"""
import re
from typing import Any, Dict, List, Optional

import requests

from config import settings

TIMEOUT = 20
_FULL_NAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]*)/[A-Za-z0-9._-]+$")


class GitHubError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def is_valid_full_name(full_name: Any) -> bool:
    return (
        isinstance(full_name, str)
        and bool(_FULL_NAME.match(full_name))
        and ".." not in full_name
    )


def _headers(token: Optional[str]) -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _request(method: str, path: str, token: Optional[str], **kwargs) -> requests.Response:
    try:
        response = requests.request(
            method,
            f"{settings.GITHUB_API_URL}{path}",
            headers=_headers(token),
            timeout=TIMEOUT,
            **kwargs,
        )
    except requests.RequestException as exc:
        raise GitHubError(502, "Could not reach GitHub. Please try again.") from exc

    if response.status_code == 401:
        raise GitHubError(401, "GitHub authorization expired. Please sign in again.")
    if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
        raise GitHubError(429, "GitHub API rate limit reached. Please try again later.")
    return response


def _message(response: requests.Response) -> str:
    try:
        return response.json().get("message", "GitHub request failed")
    except (ValueError, AttributeError):
        return "GitHub request failed"


def get_user(token: str) -> Dict[str, Any]:
    response = _request("GET", "/user", token)
    if response.status_code != 200:
        raise GitHubError(response.status_code, _message(response))
    return response.json()


def get_primary_email(token: str) -> Optional[str]:
    """Private GitHub profiles return a null email, so ask for it explicitly."""
    response = _request("GET", "/user/emails", token)
    if response.status_code != 200:
        return None
    for entry in response.json():
        if entry.get("primary") and entry.get("verified"):
            return entry.get("email")
    return None


def list_repos(token: str, max_pages: int = 10) -> List[Dict[str, Any]]:
    repos: List[Dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        response = _request(
            "GET",
            "/user/repos",
            token,
            params={"per_page": 100, "page": page, "sort": "updated"},
        )
        if response.status_code != 200:
            raise GitHubError(response.status_code, _message(response))
        batch = response.json()
        repos.extend(batch)
        if len(batch) < 100:
            break
    return repos


def get_repo(full_name: str, token: Optional[str]) -> Dict[str, Any]:
    if not is_valid_full_name(full_name):
        raise GitHubError(400, "Invalid repository name. Expected owner/repo.")
    response = _request("GET", f"/repos/{full_name}", token)
    if response.status_code == 404:
        raise GitHubError(404, f"Repository {full_name} was not found or is not accessible.")
    if response.status_code != 200:
        raise GitHubError(response.status_code, _message(response))
    return response.json()


def create_pull_request(
    token: str, full_name: str, head: str, base: str, title: str, body: str
) -> Optional[Dict[str, Any]]:
    """Open a PR. Returns None when one already exists for this branch."""
    response = _request(
        "POST",
        f"/repos/{full_name}/pulls",
        token,
        json={"title": title, "head": head, "base": base, "body": body},
    )
    if response.status_code in (200, 201):
        return response.json()
    if response.status_code == 422 and "already exists" in response.text:
        return None
    raise GitHubError(
        response.status_code if response.status_code >= 400 else 502,
        f"GitHub rejected the pull request: {_message(response)}",
    )


def update_pull_request(token: str, full_name: str, number: int, body: str) -> None:
    _request("PATCH", f"/repos/{full_name}/pulls/{number}", token, json={"body": body})


def find_open_pull_request(
    token: str, full_name: str, owner: str, branch: str
) -> Optional[Dict[str, Any]]:
    response = _request(
        "GET",
        f"/repos/{full_name}/pulls",
        token,
        params={"head": f"{owner}:{branch}", "state": "open"},
    )
    if response.status_code == 200 and response.json():
        return response.json()[0]
    return None
