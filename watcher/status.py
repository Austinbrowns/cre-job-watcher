import json
from datetime import datetime, timezone
from pathlib import Path

from .config import SOURCES
from .history import change_lists, latest_raw_date


def build_status(
    run_time: datetime,
    raw_root: Path,
    history_rows: list[dict[str, str]],
    source_results: dict[str, dict],
) -> dict:
    raw_days = sorted({day for day_dir in raw_root.iterdir() if day_dir.is_dir() for day in [day_dir.name]}) if raw_root.exists() else []
    # "Today" is the UTC date of the run, not the most recent historical day.
    # This keeps new_today/removed_today at zero when every source fails today.
    latest_day = run_time.astimezone(timezone.utc).date().isoformat()
    new_today, removed_today = change_lists(history_rows, latest_day) if latest_day else ([], [])
    sources = []
    for source in SOURCES:
        result = source_results.get(source.name, {"ok": False, "count": 0, "error": "not attempted"})
        item = {"name": source.name, "ok": bool(result.get("ok")), "count": int(result.get("count", 0))}
        if result.get("error"):
            item["error"] = result["error"]
        sources.append(item)

    return {
        "run_time": run_time.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "first_run_date": min(raw_days) if raw_days else "",
        "days_with_success": len(raw_days),
        "open": sum(row["status"] == "open" for row in history_rows),
        "new_today": len(new_today),
        "removed_today": len(removed_today),
        "sources": sources,
    }


def write_status(path: Path, status: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
