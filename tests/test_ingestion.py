from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingestion.crossref import PaperRecord, _clean_abstract, _format_date, parse_crossref_payload


def test_clean_abstract():
    raw = "<jats:p>This is a <b>test</b> abstract with <jats:italic>tags</jats:italic>.</jats:p>"
    cleaned = _clean_abstract(raw)
    assert cleaned == "This is a test abstract with tags."
    assert "<" not in cleaned and ">" not in cleaned


def test_format_date():
    assert _format_date([[2026, 5, 20]]) == "2026-05-20"
    assert _format_date([[2026, 9]]) == "2026-09-01"
    assert _format_date([[2026]]) == "2026-01-01"
    assert _format_date(None) == "2026-01-01"


def test_parse_crossref_payload():
    payload = {
        "status": "ok",
        "message": {
            "items": [
                {
                    "DOI": "10.1234/test.001",
                    "title": ["Test Paper on Agentic RAG"],
                    "abstract": "<jats:p>Abstract content here for testing.</jats:p>",
                    "author": [{"given": "Duy", "family": "Nguyen"}],
                    "subject": ["Computer Science"],
                    "published": {"date-parts": [[2026, 6, 15]]},
                    "URL": "https://doi.org/10.1234/test.001",
                }
            ]
        },
    }
    records = parse_crossref_payload(payload)
    assert len(records) == 1
    rec = records[0]
    assert rec.paper_id == "10.1234/test.001"
    assert rec.title == "Test Paper on Agentic RAG"
    assert rec.summary == "Abstract content here for testing."
    assert rec.authors == ["Duy Nguyen"]
    assert rec.published == "2026-06-15"
