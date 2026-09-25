from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd

from core.utils import read_json, write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Simulate 6 realistic data corruption scenarios and log all modifications.

    1. Drop latest records (drop 20% most recent papers).
    2. Blank summary (clear summaries in a subset of rows).
    3. Inject noise (insert garbage characters into summaries).
    4. Truncate title (shorten titles to under 8 characters).
    5. Stale date (shift publication dates back by 365 days to violate Freshness SLA).
    6. Duplicate rows (re-insert rows to create non-unique paper_ids).
    7. Rebuild text_for_embedding column.
    8. Write corruption log to output_log_path.
    """
    if df.empty:
        raise ValueError("Cannot corrupt an empty DataFrame.")

    corrupted = df.copy()
    corruptions_applied = []
    output_path = Path(output_log_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Drop latest records (20% of dataset)
    total_records = len(corrupted)
    n_drop = max(1, int(total_records * 0.20))
    # Ensure sorted by published descending before dropping latest
    if "published" in corrupted.columns:
        corrupted = corrupted.sort_values(by="published", ascending=False).reset_index(drop=True)
    dropped_ids = corrupted.iloc[:n_drop]["paper_id"].tolist()
    corrupted = corrupted.iloc[n_drop:].copy().reset_index(drop=True)
    corruptions_applied.append(
        {
            "scenario": "drop_latest_records",
            "description": f"Dropped {n_drop} latest records (20% of dataset)",
            "affected_count": n_drop,
            "dropped_paper_ids": dropped_ids,
        }
    )

    current_len = len(corrupted)

    # 2. Blank summary on 2 rows
    blank_indices = [0, 1] if current_len > 1 else [0]
    for idx in blank_indices:
        corrupted.at[idx, "summary"] = ""
        if "summary_chars" in corrupted.columns:
            corrupted.at[idx, "summary_chars"] = 0
    corruptions_applied.append(
        {
            "scenario": "blank_summary",
            "description": "Erased abstract/summary to simulate empty scraped data",
            "affected_indices": blank_indices,
            "affected_paper_ids": corrupted.loc[blank_indices, "paper_id"].tolist(),
        }
    )

    # 3. Inject noise into summary on next 2 rows
    noise_indices = [2, 3] if current_len > 3 else [min(1, current_len - 1)]
    noise_marker = " ### NOISE_INJECTION: GARBAGE_DATA_CORRUPTED_TOKEN_@@@@ ### "
    for idx in noise_indices:
        orig = str(corrupted.at[idx, "summary"])
        corrupted.at[idx, "summary"] = f"{noise_marker}{orig}{noise_marker}"
        if "summary_chars" in corrupted.columns:
            corrupted.at[idx, "summary_chars"] = len(corrupted.at[idx, "summary"])
    corruptions_applied.append(
        {
            "scenario": "inject_noise",
            "description": "Injected random garbage strings into abstracts to pollute semantic similarity",
            "affected_indices": noise_indices,
            "affected_paper_ids": corrupted.loc[noise_indices, "paper_id"].tolist(),
        }
    )

    # 4. Truncate title on next 2 rows (< 8 characters)
    truncate_indices = [4, 5] if current_len > 5 else [0]
    for idx in truncate_indices:
        corrupted.at[idx, "title"] = "Paper.."
    corruptions_applied.append(
        {
            "scenario": "truncate_title",
            "description": "Truncated titles down to < 8 characters ('Paper..')",
            "affected_indices": truncate_indices,
            "affected_paper_ids": corrupted.loc[truncate_indices, "paper_id"].tolist(),
        }
    )

    # 5. Stale date (shift published dates back by 365 days for 40% of records)
    stale_count = max(1, int(current_len * 0.40))
    stale_indices = list(range(stale_count))
    for idx in stale_indices:
        raw_date = str(corrupted.at[idx, "published"])[:10]
        try:
            dt = datetime.strptime(raw_date, "%Y-%m-%d") - timedelta(days=365)
            new_date = dt.strftime("%Y-%m-%d")
        except Exception:
            new_date = "2024-01-01"
        corrupted.at[idx, "published"] = new_date
        if "age_days" in corrupted.columns:
            corrupted.at[idx, "age_days"] = int(corrupted.at[idx, "age_days"]) + 365
    corruptions_applied.append(
        {
            "scenario": "stale_date",
            "description": f"Shifted {stale_count} paper publication dates back by 365 days to fail Freshness SLA (>180 days)",
            "affected_count": stale_count,
            "affected_indices": stale_indices,
        }
    )

    # 6. Duplicate rows (re-insert first 2 rows to violate uniqueness)
    dup_rows = corrupted.iloc[:2].copy()
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    corruptions_applied.append(
        {
            "scenario": "duplicate_rows",
            "description": "Duplicated 2 rows to violate primary key uniqueness expectation (ExpectColumnValuesToBeUnique)",
            "duplicated_count": len(dup_rows),
            "duplicated_paper_ids": dup_rows["paper_id"].tolist(),
        }
    )

    # 7. Rebuild text_for_embedding for all corrupted rows
    corrupted["text_for_embedding"] = corrupted.apply(
        lambda r: (
            f"Title: {r.get('title', '')}\n"
            f"Authors: {r.get('authors_joined', 'Unknown')}\n"
            f"Published: {r.get('published', '')}\n"
            f"Categories: {r.get('categories_joined', 'General')}\n"
            f"Summary: {r.get('summary', '')}"
        ).strip(),
        axis=1,
    )

    # 8. Log corruption audit trail
    log_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "original_rows": total_records,
        "corrupted_rows": len(corrupted),
        "total_scenarios_applied": len(corruptions_applied),
        "scenarios": corruptions_applied,
    }
    write_json(output_path, log_payload)

    return corrupted
