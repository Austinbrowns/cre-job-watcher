from datetime import datetime, timezone

from watcher.status import build_status


def test_empty_raw_day_is_not_counted_as_successful(tmp_path):
    raw = tmp_path / "raw"
    (raw / "2026-01-01").mkdir(parents=True)
    (raw / "2026-01-02").mkdir()
    (raw / "2026-01-01" / "crexi.json.gz").write_bytes(b"not-read-by-this-test")

    status = build_status(datetime(2026, 1, 3, tzinfo=timezone.utc), raw, [], {})

    assert status["days_with_success"] == 1
    assert status["first_run_date"] == "2026-01-01"
