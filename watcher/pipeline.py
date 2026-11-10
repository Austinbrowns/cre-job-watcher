import argparse
import gzip
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .config import SOURCES
from .github import sync_daily_issue
from .history import build_history, change_lists, write_history
from .sources import SourceFetchError, fetch_source
from .status import build_status, write_status


def _write_raw(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
    temporary.replace(path)


def _git(args: list[str], root: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=check)


def commit_changes(root: Path, day: str) -> str:
    _git(["config", "user.name", "github-actions[bot]"], root)
    _git(["config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], root)
    _git(["add", "data"], root)
    _git(["commit", "--allow-empty", "-m", f"Daily CRE job watcher run: {day}"], root)
    _git(["push"], root)
    return "committed and pushed daily data"


def run_pipeline(root: Path, now: datetime | None = None, commit: bool = False, post_issues: bool = True) -> dict:
    now = now or datetime.now(timezone.utc)
    day = now.astimezone(timezone.utc).date().isoformat()
    data_root = root / "data"
    raw_root = data_root / "raw"
    raw_day = raw_root / day
    raw_root.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict] = {}
    for source in SOURCES:
        raw_path = raw_day / f"{source.name}.json.gz"
        if raw_path.exists():
            raw_path.unlink()
        try:
            payload, count = fetch_source(source)
            _write_raw(raw_path, payload)
            results[source.name] = {"ok": True, "count": count, "error": ""}
        except Exception as exc:  # one source must never stop the run
            results[source.name] = {"ok": False, "count": 0, "error": str(exc)}

    history_rows = build_history(raw_root)
    write_history(data_root / "history.csv", history_rows)
    status = build_status(now, raw_root, history_rows, results)
    write_status(data_root / "status.json", status)

    run_log = data_root / "runs.jsonl"
    with run_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"date": day, "run_time": status["run_time"], "sources": results}) + "\n")

    current_day_has_raw = raw_day.exists() and any(raw_day.glob("*.json.gz"))
    change_day = day if current_day_has_raw else ""
    new_rows, removed_rows = change_lists(history_rows, change_day) if change_day else ([], [])
    issue_result = sync_daily_issue(day, new_rows, removed_rows) if post_issues else "GitHub issue sync disabled"
    commit_result = commit_changes(root, day) if commit else "commit disabled"
    return {"date": day, "status": status, "issues": issue_result, "commit": commit_result}


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch public CRE job boards and rebuild history.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--commit", action="store_true", help="commit and push data changes")
    parser.add_argument("--no-issues", action="store_true", help="skip GitHub Issue synchronization")
    args = parser.parse_args()
    result = run_pipeline(args.root.resolve(), commit=args.commit, post_issues=not args.no_issues)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
