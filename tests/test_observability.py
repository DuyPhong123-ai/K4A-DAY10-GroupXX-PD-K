from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.config import load_settings
from observability.quality import _freshness_payload


def test_freshness_sla():
    settings = load_settings()
    
    # Dataset with 1 stale out of 10 -> ratio 0.10 <= 0.25 -> is_fresh = True
    df_fresh = pd.DataFrame({
        "published": ["2026-08-01"] * 9 + ["2024-01-01"],
        "age_days": [30] * 9 + [500],
    })
    res_fresh = _freshness_payload(df_fresh, settings)
    assert res_fresh["is_fresh"] is True
    assert res_fresh["stale_rows"] == 1
    assert res_fresh["stale_ratio"] == 0.1

    # Dataset with 5 stale out of 10 -> ratio 0.50 > 0.25 -> is_fresh = False
    df_stale = pd.DataFrame({
        "published": ["2026-08-01"] * 5 + ["2024-01-01"] * 5,
        "age_days": [30] * 5 + [500] * 5,
    })
    res_stale = _freshness_payload(df_stale, settings)
    assert res_stale["is_fresh"] is False
    assert res_stale["stale_rows"] == 5
    assert res_stale["stale_ratio"] == 0.5
