from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def _parse_date(date_str: str) -> datetime:
    try:
        clean_str = date_str.strip()[:10]
        return datetime.strptime(clean_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return datetime(2026, 1, 1, tzinfo=timezone.utc)


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed."""
    if run_date.tzinfo is None:
        run_date = run_date.replace(tzinfo=timezone.utc)

    rows = []
    seen_ids = set()

    for r in records:
        paper_id = normalize_whitespace(r.paper_id)
        if not paper_id or paper_id in seen_ids:
            continue

        title = normalize_whitespace(r.title)
        if not title:
            continue

        summary = normalize_whitespace(r.summary)
        pub_dt = _parse_date(r.published)
        age_days = max(0, (run_date.date() - pub_dt.date()).days)

        authors_clean = [normalize_whitespace(a) for a in r.authors if normalize_whitespace(a)]
        authors_joined = compact_join(authors_clean, ", ") or "Unknown"

        categories_clean = [normalize_whitespace(c) for c in r.categories if normalize_whitespace(c)]
        categories_joined = compact_join(categories_clean, ", ") or r.primary_category or "General"

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {r.published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        ).strip()

        seen_ids.add(paper_id)
        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "summary_chars": len(summary),
                "authors": authors_clean,
                "authors_joined": authors_joined,
                "categories": categories_clean,
                "categories_joined": categories_joined,
                "primary_category": r.primary_category or (categories_clean[0] if categories_clean else "General"),
                "published": r.published,
                "updated": r.updated or r.published,
                "age_days": age_days,
                "abs_url": r.abs_url,
                "pdf_url": r.pdf_url,
                "comment": r.comment,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by="published", ascending=False).reset_index(drop=True)
    return df
