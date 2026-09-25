from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any

from core.config import Settings
from core.utils import read_json, write_json


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


def _clean_abstract(raw_abstract: str) -> str:
    cleaned = re.sub(r"<[^>]+>", "", raw_abstract or "")
    return re.sub(r"\s+", " ", cleaned).strip()


def _format_date(date_parts: list[Any] | None) -> str:
    if not date_parts or not date_parts[0]:
        return "2026-01-01"
    parts = date_parts[0]
    year = int(parts[0]) if len(parts) > 0 else 2026
    month = int(parts[1]) if len(parts) > 1 else 1
    day = int(parts[2]) if len(parts) > 2 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI", "").strip()
        if not doi:
            continue

        raw_title = item.get("title", [])
        if isinstance(raw_title, list):
            title = raw_title[0].strip() if raw_title else ""
        else:
            title = str(raw_title).strip()

        raw_abstract = item.get("abstract", "")
        summary = _clean_abstract(raw_abstract)

        authors: list[str] = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            full_name = f"{given} {family}".strip()
            if full_name:
                authors.append(full_name)

        categories = item.get("subject", [])
        if not categories:
            categories = ["General"]
        primary_category = categories[0]

        date_parts = item.get("published", {}).get("date-parts")
        published = _format_date(date_parts)

        created_parts = item.get("created", {}).get("date-parts")
        updated = _format_date(created_parts) if created_parts else published

        url = item.get("URL", f"https://doi.org/{doi}")

        record = PaperRecord(
            paper_id=doi,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=url,
            pdf_url=url,
            comment=f"Crossref record {doi}",
        )
        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API, luu raw response, parse thanh records co co che fallback offline."""
    payload: dict | None = None

    if settings.refresh_source:
        try:
            try:
                import requests

                params = {
                    "query": settings.source_query,
                    "rows": settings.max_results,
                }
                if settings.source_filter:
                    params["filter"] = settings.source_filter
                headers = {"User-Agent": "Day10LabStudent/1.0 (mailto:student@vinuni.edu.vn)"}
                resp = requests.get("https://api.crossref.org/works", params=params, headers=headers, timeout=15)
                if resp.status_code == 200:
                    payload = resp.json()
                    write_json(settings.paths.raw_api_response, payload)
            except ImportError:
                import urllib.parse
                import urllib.request
                import json

                query_dict = {"query": settings.source_query, "rows": settings.max_results}
                if settings.source_filter:
                    query_dict["filter"] = settings.source_filter
                qs = urllib.parse.urlencode(query_dict)
                req = urllib.request.Request(
                    f"https://api.crossref.org/works?{qs}",
                    headers={"User-Agent": "Day10LabStudent/1.0 (mailto:student@vinuni.edu.vn)"},
                )
                with urllib.request.urlopen(req, timeout=15) as res:
                    if res.status == 200:
                        payload = json.loads(res.read().decode("utf-8"))
                        write_json(settings.paths.raw_api_response, payload)
        except Exception:
            payload = None

    if payload is None:
        if settings.paths.raw_api_response.exists():
            payload = read_json(settings.paths.raw_api_response)
        elif settings.paths.raw_records_json.exists():
            return load_raw_records(settings.paths.raw_records_json)
        else:
            raise FileNotFoundError(
                f"Cannot find raw API response at {settings.paths.raw_api_response} and API fetch was not performed."
            )

    records = parse_crossref_payload(payload)
    records_dict = [asdict(r) for r in records]
    write_json(settings.paths.raw_records_json, records_dict)
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh list PaperRecord."""
    data = read_json(path)
    return [PaperRecord(**item) for item in data]
