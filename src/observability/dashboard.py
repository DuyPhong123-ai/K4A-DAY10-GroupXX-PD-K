from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_DIR / "data"

STATE_CONFIG = {
    "Baseline": {
        "quality": DATA_DIR / "quality" / "baseline_quality_report.json",
        "metrics": DATA_DIR / "results" / "baseline_metrics.json",
        "dataset": DATA_DIR / "clean" / "papers_clean.csv",
    },
    "Corrupted": {
        "quality": DATA_DIR / "quality" / "corrupted_quality_report.json",
        "metrics": DATA_DIR / "results" / "corrupted_metrics.json",
        "dataset": DATA_DIR / "clean" / "papers_clean_corrupted.csv",
    },
    "Repaired": {
        "quality": DATA_DIR / "quality" / "repaired_quality_report.json",
        "metrics": DATA_DIR / "results" / "repaired_metrics.json",
        "dataset": DATA_DIR / "clean" / "papers_clean_repaired.csv",
    },
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_dataframe(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError):
        return pd.DataFrame()


def load_dashboard_data() -> dict[str, Any]:
    states: dict[str, dict[str, Any]] = {}
    for state, paths in STATE_CONFIG.items():
        states[state] = {
            "quality": _read_json(paths["quality"]),
            "metrics": _read_json(paths["metrics"]),
            "dataset": _read_dataframe(paths["dataset"]),
        }

    return {
        "states": states,
        "phase1_healing": _read_json(DATA_DIR / "results" / "phase1_self_healing_log.json"),
        "corruption_healing": _read_json(
            DATA_DIR / "results" / "corruption_self_healing_log.json"
        ),
        "loaded_at": datetime.now(UTC),
    }


def _status_label(success: bool) -> str:
    return "PASS" if success else "FAIL"


def _metric_value(payload: dict[str, Any], name: str) -> float:
    try:
        return float(payload.get(name, 0.0))
    except (TypeError, ValueError):
        return 0.0


def _render_quality_overview(states: dict[str, dict[str, Any]]) -> None:
    st.subheader("Data Quality & Freshness SLA")
    columns = st.columns(3)
    for column, (state, payload) in zip(columns, states.items(), strict=True):
        quality = payload["quality"]
        freshness = quality.get("freshness", {})
        quality_success = bool(quality.get("success", False))
        freshness_success = bool(freshness.get("is_fresh", False))
        stale_ratio = _metric_value(freshness, "stale_ratio")
        row_count = int(quality.get("row_count", len(payload["dataset"])) or 0)

        with column:
            st.markdown(f"#### {state}")
            if quality_success:
                st.success("Quality Gate: PASS")
            else:
                st.error("Quality Gate: FAIL")
            st.metric("Freshness SLA", _status_label(freshness_success))
            st.metric("Stale ratio", f"{stale_ratio:.1%}")
            st.metric("Số bản ghi", row_count)


def _render_metrics(states: dict[str, dict[str, Any]]) -> None:
    st.subheader("So sánh hiệu năng RAG")
    rows = []
    for state, payload in states.items():
        metrics = payload["metrics"]
        rows.append(
            {
                "Trạng thái": state,
                "Retrieval Hit Rate": _metric_value(metrics, "retrieval_hit_rate"),
                "Mean Token F1": _metric_value(metrics, "mean_token_f1"),
                "Judge Accuracy": _metric_value(metrics, "judge_accuracy"),
                "Mean Judge Score": _metric_value(metrics, "mean_judge_score"),
            }
        )

    metrics_df = pd.DataFrame(rows).set_index("Trạng thái")
    st.bar_chart(metrics_df[["Retrieval Hit Rate", "Mean Token F1", "Judge Accuracy"]])
    st.dataframe(metrics_df.style.format("{:.4f}"), width="stretch")


def _render_age_distribution(states: dict[str, dict[str, Any]]) -> None:
    st.subheader("Phân bố độ tuổi bài báo")
    age_rows: list[dict[str, Any]] = []
    labels = ["0–30 ngày", "31–90 ngày", "91–180 ngày", ">180 ngày"]
    for state, payload in states.items():
        dataset = payload["dataset"]
        if "age_days" not in dataset.columns:
            continue
        ages = pd.to_numeric(dataset["age_days"], errors="coerce").dropna()
        buckets = pd.cut(
            ages,
            bins=[-1, 30, 90, 180, float("inf")],
            labels=labels,
            include_lowest=True,
        )
        counts = buckets.value_counts(sort=False)
        for bucket in labels:
            age_rows.append(
                {
                    "Nhóm tuổi": bucket,
                    "Trạng thái": state,
                    "Số bài báo": int(counts.get(bucket, 0)),
                }
            )

    if not age_rows:
        st.info("Chưa có dữ liệu `age_days`. Hãy chạy pipeline trước khi mở dashboard.")
        return

    age_df = pd.DataFrame(age_rows)
    chart_df = age_df.pivot(index="Nhóm tuổi", columns="Trạng thái", values="Số bài báo")
    chart_df = chart_df.reindex(labels).fillna(0).astype(int)
    st.bar_chart(chart_df)


def _render_failed_expectations(states: dict[str, dict[str, Any]]) -> None:
    st.subheader("Expectation thất bại")
    failures = []
    for state, payload in states.items():
        for check in payload["quality"].get("checks", []):
            if not check.get("success", False):
                failures.append(
                    {
                        "Trạng thái": state,
                        "Expectation": check.get("name", "unknown"),
                        "Lỗi": check.get("error", "Expectation returned success=false"),
                    }
                )

    if failures:
        st.dataframe(pd.DataFrame(failures), hide_index=True, width="stretch")
    else:
        st.success("Không có expectation thất bại trong các artifact hiện tại.")


def _render_drift_alerts(states: dict[str, dict[str, Any]]) -> None:
    st.subheader("Drift Monitor")
    baseline = states["Baseline"]
    corrupted = states["Corrupted"]
    repaired = states["Repaired"]

    baseline_metrics = baseline["metrics"]
    corrupted_metrics = corrupted["metrics"]
    repaired_metrics = repaired["metrics"]
    hit_rate_drop = _metric_value(baseline_metrics, "retrieval_hit_rate") - _metric_value(
        corrupted_metrics, "retrieval_hit_rate"
    )
    token_f1_drop = _metric_value(baseline_metrics, "mean_token_f1") - _metric_value(
        corrupted_metrics, "mean_token_f1"
    )
    corrupted_freshness = corrupted["quality"].get("freshness", {})

    alert_columns = st.columns(3)
    alert_columns[0].metric("Hit Rate drift", f"-{max(hit_rate_drop, 0.0):.4f}")
    alert_columns[1].metric("Token F1 drift", f"-{max(token_f1_drop, 0.0):.4f}")
    alert_columns[2].metric(
        "Corrupted stale ratio",
        f"{_metric_value(corrupted_freshness, 'stale_ratio'):.1%}",
    )

    if not corrupted["quality"].get("success", False):
        st.error("CẢNH BÁO DRIFT: dữ liệu corrupted vi phạm Quality Gate/Freshness SLA.")
    if repaired["quality"].get("success", False) and (
        _metric_value(repaired_metrics, "retrieval_hit_rate")
        >= _metric_value(baseline_metrics, "retrieval_hit_rate")
    ):
        st.success("RECOVERY: dữ liệu repaired đã đạt lại quality và hiệu năng baseline.")


def _render_self_healing(data: dict[str, Any]) -> None:
    st.subheader("Automated Self-Healing")
    logs = {
        "Phase 1": data["phase1_healing"],
        "Corruption flow": data["corruption_healing"],
    }
    if not any(logs.values()):
        st.info("Chạy hai pipeline để sinh self-healing audit log.")
        return

    rows = []
    for pipeline, log in logs.items():
        if not log:
            continue
        strategies = ", ".join(
            str(attempt.get("strategy", "")) for attempt in log.get("attempts", [])
        ) or "Không cần repair"
        rows.append(
            {
                "Pipeline": pipeline,
                "Triggered": bool(log.get("triggered", False)),
                "Trigger signals": ", ".join(log.get("trigger_signals", [])) or "—",
                "Strategy": strategies,
                "Final quality": _status_label(bool(log.get("final_quality_success", False))),
                "Serving allowed": bool(log.get("serving_allowed", False)),
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def render_dashboard() -> None:
    data = load_dashboard_data()
    states = data["states"]
    _render_quality_overview(states)
    st.divider()
    _render_metrics(states)
    st.divider()
    _render_age_distribution(states)
    st.divider()
    _render_failed_expectations(states)
    st.divider()
    _render_drift_alerts(states)
    st.divider()
    _render_self_healing(data)
    st.caption(f"Cập nhật gần nhất: {data['loaded_at'].astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}")


def main() -> None:
    st.set_page_config(
        page_title="Day 10 Observability Dashboard",
        page_icon="📊",
        layout="wide",
    )
    st.title("📊 Data Observability & Drift Monitor")
    st.caption("Great Expectations · Freshness SLA · RAG metrics · Automated Self-Healing")

    st.sidebar.header("Điều khiển")
    if st.sidebar.button("Làm mới ngay", width="stretch"):
        st.rerun()
    auto_refresh = st.sidebar.toggle("Tự động làm mới", value=False)
    refresh_seconds = st.sidebar.slider("Chu kỳ làm mới (giây)", 5, 60, 10, 5)
    st.sidebar.caption(f"Nguồn artifact: {DATA_DIR}")

    run_every = f"{refresh_seconds}s" if auto_refresh else None

    @st.fragment(run_every=run_every)
    def live_dashboard() -> None:
        render_dashboard()

    live_dashboard()


if __name__ == "__main__":
    main()
