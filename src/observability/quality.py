from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def _quality_report_path(settings: Settings, report_name: str | Path) -> Path:
    report_path = Path(report_name)
    if report_path.suffix.lower() == ".json" or report_path.parent != Path("."):
        return report_path
    if report_name == "baseline":
        return settings.paths.baseline_quality_report
    if report_name == "corrupted":
        return settings.paths.corrupted_quality_report
    return settings.paths.quality_dir / f"{report_name}_quality_report.json"


def _serializable_result(result: Any) -> dict[str, Any]:
    payload = getattr(result, "to_json_dict", None)
    if callable(payload):
        result_dict = payload()
    elif hasattr(result, "to_json_dict"):
        result_dict = result.to_json_dict
    else:
        result_dict = {
            "success": bool(getattr(result, "success", False)),
            "result": getattr(result, "result", {}),
        }
    return result_dict if isinstance(result_dict, dict) else {"result": str(result_dict)}


def _freshness_payload(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    if df.empty:
        return {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 0.0,
            "threshold_days": settings.freshness_threshold_days,
            "max_stale_ratio": 0.25,
            "is_fresh": False,
        }

    published = pd.to_datetime(df.get("published"), errors="coerce", utc=True)
    if "age_days" in df.columns:
        age_days = pd.to_numeric(df["age_days"], errors="coerce")
    else:
        age_days = (pd.Timestamp.now(tz="UTC") - published).dt.days
    stale_mask = age_days > settings.freshness_threshold_days
    total_rows = len(df)
    stale_rows = int(stale_mask.fillna(False).sum())
    stale_ratio = stale_rows / total_rows if total_rows else 1.0

    valid_dates = published.dropna()
    return {
        "latest_published": valid_dates.max().date().isoformat() if not valid_dates.empty else None,
        "oldest_published": valid_dates.min().date().isoformat() if not valid_dates.empty else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio": 0.25,
        "is_fresh": stale_ratio <= 0.25,
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the required Great Expectations 1.x checks and freshness SLA."""
    try:
        import great_expectations as gx
        from great_expectations.expectations import (
            ExpectColumnValueLengthsToBeBetween,
            ExpectColumnValuesToBeUnique,
            ExpectColumnValuesToNotBeNull,
            ExpectTableRowCountToBeBetween,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Great Expectations is required. Install project dependencies with `python -m pip install -e .`."
        ) from exc

    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"papers_source_{report_name}")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    expectations = [
        ("row_count", ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)),
        ("paper_id_not_null", ExpectColumnValuesToNotBeNull(column="paper_id")),
        ("title_not_null", ExpectColumnValuesToNotBeNull(column="title")),
        ("text_for_embedding_not_null", ExpectColumnValuesToNotBeNull(column="text_for_embedding")),
        ("paper_id_unique", ExpectColumnValuesToBeUnique(column="paper_id")),
        (
            "summary_length",
            ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
        ),
    ]
    checks: list[dict[str, Any]] = []
    for check_name, expectation in expectations:
        try:
            validation = batch.validate(expectation)
            payload = _serializable_result(validation)
            success = bool(payload.get("success", getattr(validation, "success", False)))
            checks.append({"name": check_name, "success": success, "result": payload})
        except Exception as exc:
            checks.append({"name": check_name, "success": False, "error": str(exc)})

    freshness = _freshness_payload(df, settings)
    report = {
        "report_name": report_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(df),
        "success": all(check["success"] for check in checks) and freshness["is_fresh"],
        "checks": checks,
        "freshness": freshness,
    }
    write_json(_quality_report_path(settings, report_name), report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build and persist the Freshness SLA payload independently of GX."""
    report = _freshness_payload(df, settings)
    report["generated_at"] = datetime.now(UTC).isoformat()
    write_json(Path(report_path), report)
    return report
