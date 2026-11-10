import json
from pathlib import Path

from watcher.config import SOURCE_BY_NAME
from watcher.sources import normalize_source_payload


FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_greenhouse_conversion_to_common_columns():
    rows = normalize_source_payload(SOURCE_BY_NAME["northmarq"], load("greenhouse.json"))
    assert rows[0] == {
        "source_id": "101",
        "employer": "Northmarq",
        "title": "Investment Analyst",
        "location": "Chicago, IL",
        "department": "Debt + Equity",
        "posted_date": "2026-01-01",
        "url": "https://example.com/jobs/101",
    }


def test_lever_conversion_to_common_columns():
    rows = normalize_source_payload(SOURCE_BY_NAME["nai_norcal"], load("lever.json"))
    assert rows[0]["source_id"] == "lever-201"
    assert rows[0]["department"] == "Brokerage"
    assert rows[0]["location"] == "Oakland, CA"
    assert rows[0]["posted_date"] == "2026-01-01"


def test_smartrecruiters_conversion_to_common_columns():
    rows = normalize_source_payload(SOURCE_BY_NAME["colliers"], load("smartrecruiters.json"))
    assert rows[0]["source_id"] == "sr-301"
    assert rows[0]["title"] == "Commercial Mortgage Analyst"
    assert rows[0]["location"] == "Toronto, ON, Canada"
    assert rows[0]["department"] == "Commercial Credit"
