from __future__ import annotations

from datetime import datetime, timezone
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import PaperRecord


def test_build_clean_dataframe():
    rec1 = PaperRecord(
        paper_id="10.1145/001",
        title="Paper One",
        summary="Summary for paper one that is long enough.",
        authors=["Alice", "Bob"],
        categories=["AI"],
        primary_category="AI",
        published="2026-05-01",
        updated="2026-05-01",
        abs_url="https://doi.org/10.1145/001",
        pdf_url="https://doi.org/10.1145/001",
        comment="Test",
    )
    # Duplicate rec1
    rec1_dup = PaperRecord(
        paper_id="10.1145/001",
        title="Paper One Duplicate",
        summary="Summary for paper one duplicate.",
        authors=["Alice"],
        categories=["AI"],
        primary_category="AI",
        published="2026-05-01",
        updated="2026-05-01",
        abs_url="https://doi.org/10.1145/001",
        pdf_url="https://doi.org/10.1145/001",
        comment="Test",
    )
    rec2 = PaperRecord(
        paper_id="10.1145/002",
        title="Paper Two",
        summary="Summary for paper two that is long enough.",
        authors=["Charlie"],
        categories=["IR"],
        primary_category="IR",
        published="2026-06-01",
        updated="2026-06-01",
        abs_url="https://doi.org/10.1145/002",
        pdf_url="https://doi.org/10.1145/002",
        comment="Test",
    )

    now = datetime(2026, 9, 25, tzinfo=timezone.utc)
    df = build_clean_dataframe([rec1, rec1_dup, rec2], now)

    # Assert deduplication: only 2 unique rows
    assert len(df) == 2
    assert set(df["paper_id"]) == {"10.1145/001", "10.1145/002"}

    # Assert schema
    expected_cols = {"paper_id", "title", "summary", "authors_joined", "categories_joined", "text_for_embedding", "age_days"}
    assert expected_cols.issubset(set(df.columns))

    # Assert age_days calculation
    row1 = df[df["paper_id"] == "10.1145/001"].iloc[0]
    expected_age = (now.date() - datetime(2026, 5, 1).date()).days
    assert row1["age_days"] == expected_age

    # Assert text_for_embedding structure
    assert "Title: Paper One" in row1["text_for_embedding"]
    assert "Authors: Alice, Bob" in row1["text_for_embedding"]
    assert "Summary: Summary for paper one" in row1["text_for_embedding"]
