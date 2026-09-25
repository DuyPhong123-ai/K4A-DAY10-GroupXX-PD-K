from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import write_text


METRIC_NAMES = (
    "retrieval_hit_rate",
    "mean_token_f1",
    "judge_accuracy",
    "mean_judge_score",
)


def _value(payload: dict[str, Any], key: str, default: Any = "n/a") -> Any:
    value = payload.get(key, default)
    return default if value is None else value


def _display(value: Any) -> str:
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _quality_summary(quality: dict[str, Any]) -> str:
    checks = quality.get("checks", [])
    passed = sum(1 for check in checks if check.get("success") is True)
    return f"{passed}/{len(checks)} checks passed; overall {_display(bool(quality.get('success', False)))}"


def _freshness_summary(freshness: dict[str, Any]) -> str:
    return (
        f"{_display(freshness.get('stale_rows', 'n/a'))} stale / "
        f"{_display(freshness.get('total_rows', 'n/a'))} rows; "
        f"ratio {_display(freshness.get('stale_ratio', 'n/a'))}; "
        f"status {_display(bool(freshness.get('is_fresh', False)))}"
    )


def _metric_table(rows: list[tuple[str, dict[str, Any]]]) -> str:
    lines = [
        "| Metric | " + " | ".join(label for label, _ in rows) + " |",
        "| --- | " + " | ".join("---" for _ in rows) + " |",
    ]
    for metric_name in METRIC_NAMES:
        values = [_display(metrics.get(metric_name, "n/a")) for _, metrics in rows]
        lines.append(f"| `{metric_name}` | " + " | ".join(values) + " |")
    return "\n".join(lines)


def _quality_table(rows: list[tuple[str, dict[str, Any], dict[str, Any]]]) -> str:
    lines = [
        "| Signal | " + " | ".join(label for label, _, _ in rows) + " |",
        "| --- | " + " | ".join("---" for _ in rows) + " |",
    ]
    lines.append(
        "| Quality gate | "
        + " | ".join(_quality_summary(quality) for _, quality, _ in rows)
        + " |"
    )
    lines.append(
        "| Freshness SLA | "
        + " | ".join(_freshness_summary(freshness) for _, _, freshness in rows)
        + " |"
    )
    return "\n".join(lines)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline data quality and retrieval evaluation report."""
    source_lines = "\n".join(
        f"- **{key}:** {_display(value)}" for key, value in source_summary.items()
    ) or "- No source summary was provided."
    content = f"""# Phase 1 Baseline Report

## Source Summary
{source_lines}

## Evaluation Metrics
{_metric_table([('Baseline', metrics)])}

## Data Quality and Freshness
{_quality_table([('Baseline', quality, freshness)])}

### Freshness Details
- Latest published: {_display(freshness.get('latest_published', 'n/a'))}
- Oldest published: {_display(freshness.get('oldest_published', 'n/a'))}
- Threshold: {_display(freshness.get('threshold_days', 'n/a'))} days

## Interpretation
- The baseline is eligible for serving only when the quality gate and Freshness SLA both pass.
- Retrieval and answer metrics above are the reference values for corruption impact analysis.
"""
    write_text(Path(report_path), content)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write the three-state corruption and repair comparison report."""
    content = f"""# Corruption and Repair Comparison Report

## Evaluation Metrics
{_metric_table([
    ('Baseline', baseline_metrics),
    ('Corrupted', corrupted_metrics),
    ('Repaired', repaired_metrics),
])}

## Observability Signals
{_quality_table([
    ('Corrupted', corrupted_quality, corrupted_freshness),
    ('Repaired', repaired_quality, repaired_freshness),
])}

## State Analysis
- **Baseline:** reference performance on the clean benchmark dataset.
- **Corrupted:** quality gate and freshness signals should expose injected data defects before serving.
- **Repaired:** data rebuilt from the raw snapshot should restore the quality contract and improve the evaluation metrics toward baseline.

## Repair Evidence
- Corrupted quality status: **{_display(bool(corrupted_quality.get('success', False)))}**
- Repaired quality status: **{_display(bool(repaired_quality.get('success', False)))}**
- Corrupted freshness status: **{_display(bool(corrupted_freshness.get('is_fresh', False)))}**
- Repaired freshness status: **{_display(bool(repaired_freshness.get('is_fresh', False)))}**
"""
    write_text(Path(report_path), content)
