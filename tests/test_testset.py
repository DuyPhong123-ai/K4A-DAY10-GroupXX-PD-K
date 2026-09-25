from __future__ import annotations

import importlib.util
from pathlib import Path
import pandas as pd

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
spec = importlib.util.spec_from_file_location("testset_module", SRC_DIR / "evaluation" / "testset.py")
testset_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(testset_module)
build_test_set = testset_module.build_test_set


def test_build_test_set(tmp_path):
    rows = []
    for i in range(12):
        rows.append({
            "paper_id": f"10.1145/{i:03d}",
            "title": f"Paper Title {i}",
            "summary": f"Summary for paper {i}. Sentence two.",
            "authors_joined": f"Author {i}",
            "published": "2026-05-20",
            "categories_joined": "Computer Science",
        })
    df = pd.DataFrame(rows)
    out_file = tmp_path / "test_set.json"
    test_set = build_test_set(df, out_file)

    assert len(test_set) == 10
    types = [q["question_type"] for q in test_set]
    assert "summary" in types
    assert "authors" in types
    assert "date" in types
    assert "categories" in types
    assert out_file.exists()
