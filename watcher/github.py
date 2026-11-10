import json
import os
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GitHubError(RuntimeError):
    pass


class GitHubClient:
    def __init__(self, token: str, repository: str):
        self.token = token
        self.repository = repository
        self.base = f"https://api.github.com/repos/{repository}"

    def request(self, method: str, path: str, payload=None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            self.base + path,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "cre-job-watcher/1.0",
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read()
        except (HTTPError, URLError) as exc:
            detail = exc.read().decode("utf-8", "replace") if isinstance(exc, HTTPError) else str(exc)
            raise GitHubError(detail) from exc
        return json.loads(raw.decode("utf-8")) if raw else None


def _issue_body(day: str, new_rows: list[dict], removed_rows: list[dict]) -> str:
    def lines(rows):
        if not rows:
            return "- None"
        return "\n".join(
            f"- [{row['title']}]({row['url']}) — {row['employer']} — {row['location']}"
            for row in rows
        )

    return (
        f"# CRE analyst job watcher — {day}\n\n"
        f"## New postings ({len(new_rows)})\n\n{lines(new_rows)}\n\n"
        f"## Removed postings ({len(removed_rows)})\n\n{lines(removed_rows)}\n"
    )


def sync_daily_issue(day: str, new_rows: list[dict], removed_rows: list[dict]) -> str:
    token = os.getenv("GITHUB_TOKEN", "")
    repository = os.getenv("GITHUB_REPOSITORY", "")
    if not token or not repository:
        return "GitHub issue sync skipped: GITHUB_TOKEN or GITHUB_REPOSITORY is missing"

    client = GitHubClient(token, repository)
    body = _issue_body(day, new_rows, removed_rows)
    issues = client.request("GET", "/issues?state=open&per_page=100")
    current = next((issue for issue in issues if issue.get("title") == day and not issue.get("pull_request")), None)

    for issue in issues:
        title = issue.get("title", "")
        if issue.get("pull_request") or title == day:
            continue
        try:
            issue_day = date.fromisoformat(title)
        except ValueError:
            continue
        if issue_day < date.fromisoformat(day):
            client.request("PATCH", f"/issues/{issue['number']}", {"state": "closed"})

    if current:
        client.request("PATCH", f"/issues/{current['number']}", {"body": body, "state": "open"})
        return f"updated GitHub issue #{current['number']}"
    created = client.request("POST", "/issues", {"title": day, "body": body})
    return f"created GitHub issue #{created['number']}"
