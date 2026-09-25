from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingestion.corruption import corrupt_clean_dataframe


def test_corrupt_clean_dataframe(tmp_path):
    rows = []
    for i in range(24):
        rows.append({
            "paper_id": f"10.1145/{i:03d}",
            "title": f"Original Long Title For Paper Number {i}",
            "summary": f"Summary for paper {i} that is long enough to satisfy all initial conditions.",
            "authors_joined": f"Author {i}",
            "published": "2026-05-20",
            "categories_joined": "AI",
            "age_days": 30,
            "text_for_embedding": f"Text {i}",
        })
    df = pd.DataFrame(rows)
    log_file = tmp_path / "corruption_log.json"
    corrupted_df = corrupt_clean_dataframe(df, log_file)

    assert log_file.exists()
    assert len(corrupted_df) > 0
    # Check that text_for_embedding was rebuilt
    assert "text_for_embedding" in corrupted_df.columns
