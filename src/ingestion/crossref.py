"""Ingestion tu Crossref REST API.

Owner: Phai (Ingestion). Pha 1.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

CROSSREF_API_URL = "https://api.crossref.org/works"
_RETRY_STATUS = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _date_parts_to_iso(date_obj: dict | None) -> str:
    """Chuyen Crossref date {"date-parts": [[y, m, d]]} thanh 'YYYY-MM-DD'."""
    if not date_obj:
        return ""
    parts = (date_obj.get("date-parts") or [[]])[0]
    if not parts:
        return ""
    year = parts[0]
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    try:
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except (TypeError, ValueError):
        return ""


def _strip_jats(text: str | None) -> str:
    """Bo tag JATS/HTML trong abstract cua Crossref."""
    if not text:
        return ""
    return normalize_whitespace(re.sub(r"<[^>]+>", " ", text))


def _first_pdf_url(item: dict) -> str:
    for link in item.get("link", []) or []:
        if str(link.get("content-type", "")).lower() == "application/pdf":
            return link.get("URL", "")
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord.

    - paper_id = DOI (khoa on dinh xuyen suot raw -> clean -> index -> ground truth).
    - Bo record khong co DOI hoac khong co title.
    """
    items = payload.get("message", {}).get("items", []) or []
    records: list[PaperRecord] = []
    for item in items:
        doi = item.get("DOI")
        title_list = item.get("title") or []
        title = normalize_whitespace(title_list[0]) if title_list else ""
        if not doi or not title:
            continue

        summary = _strip_jats(item.get("abstract"))
        authors = []
        for author in item.get("author", []) or []:
            name = normalize_whitespace(f"{author.get('given', '')} {author.get('family', '')}")
            if name:
                authors.append(name)
        categories = [normalize_whitespace(c) for c in (item.get("subject") or []) if c]
        primary_category = categories[0] if categories else ""
        published = _date_parts_to_iso(item.get("published") or item.get("issued"))
        updated = _date_parts_to_iso(item.get("deposited")) or published

        records.append(
            PaperRecord(
                paper_id=str(doi),
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=item.get("URL", ""),
                pdf_url=_first_pdf_url(item),
                comment="",
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi Crossref API, luu raw response, parse thanh records va luu records.

    Retry voi exponential backoff cho cac status code tam thoi (429/5xx).
    Luon luu raw response TRUOC khi parse de co the truy vet va repair.
    """
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": "DOI,title,abstract,author,subject,published,issued,deposited,URL,link",
    }
    headers = {"User-Agent": "day10-data-pipeline-lab/1.0 (mailto:student@example.com)"}

    response = None
    for attempt in range(5):
        response = requests.get(CROSSREF_API_URL, params=params, headers=headers, timeout=30)
        if response.status_code in _RETRY_STATUS:
            time.sleep(2**attempt)
            continue
        response.raise_for_status()
        break
    else:
        raise RuntimeError("Crossref khong phan hoi thanh cong sau nhieu lan retry.")

    payload = response.json()
    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh list PaperRecord."""
    rows = read_json(path)
    return [PaperRecord(**row) for row in rows]
