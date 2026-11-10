import json
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from urllib.request import Request, urlopen

from .config import Source


USER_AGENT = "cre-job-watcher/1.0 (educational project; public ATS JSON feeds)"


class SourceFetchError(RuntimeError):
    pass


def fetch_json(url: str, timeout: int = 45) -> Any:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise SourceFetchError(str(exc)) from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceFetchError(f"response was not valid UTF-8 JSON: {exc}") from exc


def _smartrecruiters_url(source: Source, offset: int) -> str:
    params = [("limit", "100"), ("offset", str(offset)), ("destination", "PUBLIC")]
    if source.query:
        params.append(("q", source.query))
    return f"https://api.smartrecruiters.com/v1/companies/{source.token}/postings?{urlencode(params)}"


def fetch_source(source: Source) -> tuple[Any, int]:
    """Fetch one public ATS board and return raw JSON plus posting count."""

    if source.kind == "greenhouse":
        payload = fetch_json(source.url)
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
            raise SourceFetchError("Greenhouse response did not contain a jobs list")
        return payload, len(payload["jobs"])

    if source.kind == "lever":
        payload = fetch_json(source.url)
        if not isinstance(payload, list):
            raise SourceFetchError("Lever response was not a JSON list")
        return payload, len(payload)

    if source.kind == "smartrecruiters":
        pages: list[dict[str, Any]] = []
        offset = 0
        total = None
        while True:
            page = fetch_json(_smartrecruiters_url(source, offset))
            if not isinstance(page, dict) or not isinstance(page.get("content"), list):
                raise SourceFetchError("SmartRecruiters response did not contain content")
            pages.append(page)
            content_count = len(page["content"])
            total = page.get("totalFound", total)
            offset += content_count
            if content_count == 0 or content_count < 100 or (total is not None and offset >= int(total)):
                break
            if len(pages) >= 100:
                raise SourceFetchError("SmartRecruiters pagination exceeded 100 pages")
        return {"pages": pages}, sum(len(page["content"]) for page in pages)

    raise SourceFetchError(f"unsupported source type: {source.kind}")


def _date_from_value(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()
    text = str(value).strip()
    if not text:
        return ""
    try:
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).date().isoformat()
    except ValueError:
        return text[:10] if len(text) >= 10 else ""


def _greenhouse_jobs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return payload.get("jobs", [])


def _lever_jobs(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return payload


def _smartrecruiters_jobs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for page in payload.get("pages", []):
        jobs.extend(page.get("content", []))
    return jobs


def _join_location(value: Any) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""
    parts = [value.get("city"), value.get("region"), value.get("country")]
    return ", ".join(str(part) for part in parts if part)


def normalize_source_payload(source: Source, payload: Any) -> list[dict[str, str]]:
    """Convert an ATS response into the assignment's common posting columns."""

    if source.kind == "greenhouse":
        jobs = _greenhouse_jobs(payload)
    elif source.kind == "lever":
        jobs = _lever_jobs(payload)
    elif source.kind == "smartrecruiters":
        jobs = _smartrecruiters_jobs(payload)
    else:
        raise ValueError(f"unsupported source type: {source.kind}")

    normalized: list[dict[str, str]] = []
    for job in jobs:
        if source.kind == "greenhouse":
            source_id = job.get("id")
            title = job.get("title", "")
            location = _join_location(job.get("location", {}).get("name", ""))
            departments = job.get("departments") or []
            department = ", ".join(str(item.get("name", "")) for item in departments if item.get("name"))
            posted_date = _date_from_value(job.get("first_published"))
            url = job.get("absolute_url", "")
        elif source.kind == "lever":
            source_id = job.get("id")
            title = job.get("text", "")
            categories = job.get("categories") or {}
            location = categories.get("location", "")
            department = categories.get("team") or categories.get("department") or ""
            posted_date = _date_from_value(job.get("createdAt"))
            url = job.get("hostedUrl") or job.get("applyUrl") or ""
        else:
            source_id = job.get("id") or job.get("ref")
            title = job.get("name", "")
            location = _join_location(job.get("location", {}))
            department_data = job.get("department") or {}
            department = department_data.get("label", "") if isinstance(department_data, dict) else str(department_data)
            posted_date = _date_from_value(job.get("releasedDate"))
            url = job.get("ref") or job.get("jobAdUrl") or ""

        if source_id in (None, "") or not title:
            continue
        normalized.append(
            {
                "source_id": str(source_id),
                "employer": source.employer,
                "title": str(title).strip(),
                "location": str(location or "").strip(),
                "department": str(department or "").strip(),
                "posted_date": posted_date,
                "url": str(url or "").strip(),
            }
        )
    return normalized
