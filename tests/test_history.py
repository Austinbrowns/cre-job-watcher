import gzip
import json
import shutil
from pathlib import Path

from watcher.history import build_history


def write_raw(root: Path, day: str, payload):
    target = root / day / "nai_norcal.json.gz"
    target.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(target, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle)


def job(job_id: str, title: str):
    return {
        "id": job_id,
        "text": title,
        "categories": {"location": "Oakland, CA", "team": "Brokerage"},
        "createdAt": 1767258000000,
        "hostedUrl": f"https://jobs.example.com/{job_id}",
    }


def test_first_seen_last_seen_removed_and_reopened_logic():
    test_root = Path(__file__).parent / ".tmp-history"
    if test_root.exists():
        shutil.rmtree(test_root)
    raw = test_root / "raw"
    try:
        write_raw(raw, "2026-01-01", [job("a", "Investment Analyst"), job("b", "Research Analyst")])
        write_raw(raw, "2026-01-02", [job("a", "Investment Analyst"), job("c", "Valuation Analyst")])
        write_raw(raw, "2026-01-03", [job("a", "Investment Analyst"), job("b", "Research Analyst")])

        rows = {row["source_id"]: row for row in build_history(raw)}

        assert rows["a"]["first_run"] == "true"
        assert rows["a"]["first_seen"] == "2026-01-01"
        assert rows["a"]["last_seen"] == "2026-01-03"
        assert rows["a"]["status"] == "open"

    # b disappeared for one successful source day, then reappeared. Its
    # removed date must be cleared while its original first_seen is preserved.
        assert rows["b"]["first_seen"] == "2026-01-01"
        assert rows["b"]["last_seen"] == "2026-01-03"
        assert rows["b"]["status"] == "open"
        assert rows["b"]["removed_date"] == ""

        assert rows["c"]["first_run"] == "false"
        assert rows["c"]["first_seen"] == "2026-01-02"
        assert rows["c"]["last_seen"] == "2026-01-02"
        assert rows["c"]["status"] == "removed"
        assert rows["c"]["removed_date"] == "2026-01-03"
    finally:
        if test_root.exists():
            shutil.rmtree(test_root)
