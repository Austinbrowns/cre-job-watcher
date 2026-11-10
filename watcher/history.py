import csv
import gzip
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Iterable

from .config import SOURCE_BY_NAME, Source
from .sources import normalize_source_payload
from .title_rules import is_in_role


HISTORY_COLUMNS = [
    "posting_id",
    "source",
    "source_id",
    "employer",
    "title",
    "location",
    "department",
    "posted_date",
    "url",
    "in_role",
    "first_run",
    "first_seen",
    "last_seen",
    "status",
    "removed_date",
]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _raw_files(raw_root: Path) -> Iterable[tuple[str, str, Path]]:
    for day_dir in sorted(raw_root.iterdir()) if raw_root.exists() else []:
        if not day_dir.is_dir() or not DATE_RE.match(day_dir.name):
            continue
        for path in sorted(day_dir.glob("*.json.gz")):
            yield day_dir.name, path.name.removesuffix(".json.gz"), path


def _read_gzip_json(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _source_for_name(name: str) -> Source:
    return SOURCE_BY_NAME.get(name, Source(name, name, "lever", name))


def build_history(raw_root: Path) -> list[dict[str, str]]:
    """Rebuild the complete history using only the compressed raw files."""

    source_dates: dict[str, set[str]] = defaultdict(set)
    observations: dict[tuple[str, str], dict[str, dict[str, str]]] = defaultdict(dict)

    for day, source_name, path in _raw_files(raw_root):
        source = _source_for_name(source_name)
        payload = _read_gzip_json(path)
        source_dates[source_name].add(day)
        for posting in normalize_source_payload(source, payload):
            observations[(source_name, posting["source_id"])][day] = posting

    rows: list[dict[str, str]] = []
    for (source_name, source_id), by_day in observations.items():
        source = _source_for_name(source_name)
        dates = sorted(source_dates[source_name])
        listed_dates = sorted(by_day)
        first_seen = listed_dates[0]
        first_source_day = dates[0]
        first_run = first_seen == first_source_day
        state = "open"
        removed_date = ""
        last_seen = first_seen
        latest = dict(by_day[first_seen])

        for day in dates:
            posting = by_day.get(day)
            if posting is not None:
                latest = dict(posting)
                last_seen = day
                state = "open"
                removed_date = ""
            elif day >= first_seen and state == "open":
                state = "removed"
                removed_date = day

        rows.append(
            {
                "posting_id": f"{source_name}:{source_id}",
                "source": source_name,
                "source_id": source_id,
                "employer": latest.get("employer", source.employer),
                "title": latest.get("title", ""),
                "location": latest.get("location", ""),
                "department": latest.get("department", ""),
                "posted_date": latest.get("posted_date", ""),
                "url": latest.get("url", ""),
                "in_role": str(is_in_role(latest.get("title", ""))).lower(),
                "first_run": str(first_run).lower(),
                "first_seen": first_seen,
                "last_seen": last_seen,
                "status": state,
                "removed_date": removed_date,
            }
        )

    return sorted(rows, key=lambda row: row["posting_id"])


def write_history(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HISTORY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def read_history(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def latest_raw_date(raw_root: Path) -> str:
    days = [day for day, _, _ in _raw_files(raw_root)]
    return max(days) if days else ""


def change_lists(rows: list[dict[str, str]], day: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    new_rows = [row for row in rows if row["first_seen"] == day and row["first_run"] != "true"]
    removed_rows = [row for row in rows if row["removed_date"] == day]
    return new_rows, removed_rows
