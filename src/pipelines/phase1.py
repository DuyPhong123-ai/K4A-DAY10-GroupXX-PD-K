from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.config import load_settings
from core.utils import read_json, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent
from retrieval.index import LocalEmbeddingIndex


def _failed_quality_signals(report: dict) -> list[str]:
    failures = [
        str(check.get("name", "unknown_check"))
        for check in report.get("checks", [])
        if not check.get("success", False)
    ]
    if not report.get("freshness", {}).get("is_fresh", False):
        failures.append("freshness_sla")
    return failures or ["quality_gate"]


def _persist_clean_dataframe(df, settings) -> None:
    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(settings.paths.clean_csv, index=False)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))


def main() -> None:
    print("=" * 60)
    print(">>> STARTING PHASE 1: BASELINE DATA PIPELINE & OBSERVABILITY")
    print("=" * 60)

    # 1. Load settings
    settings = load_settings()
    now = datetime.now(timezone.utc)

    # 2. Ingestion: load or fetch raw records
    print("\n[Step 1/6] Ingestion: Fetching source records...")
    records = fetch_source_records(settings)
    print(f"  -> Ingested {len(records)} raw records from Crossref.")

    # 3. Clean & Transform data
    print("\n[Step 2/6] Cleaning: Transforming and standardizing schema...")
    df = build_clean_dataframe(records, run_date=now)
    _persist_clean_dataframe(df, settings)
    print(f"  -> Cleaned {len(df)} records. Saved to:")
    print(f"     CSV : {settings.paths.clean_csv}")
    print(f"     JSON: {settings.paths.clean_json}")

    # 4. Data Quality Gate (GX 1.x & Freshness SLA)
    print("\n[Step 3/6] Observability: Running Great Expectations 1.x quality gate & Freshness SLA...")
    quality_report = run_data_quality_checks(df, settings, "baseline")
    freshness_report = quality_report.get("freshness", {})
    quality_success = quality_report.get("success", False)
    print(f"  -> Quality Gate Passed: {quality_success}")
    print(f"  -> Freshness SLA: is_fresh = {freshness_report.get('is_fresh', False)} (stale ratio: {freshness_report.get('stale_ratio', 0.0):.2%})")

    # Automated Self-Healing (Rubric B2): a failed gate triggers repair without
    # manual intervention. Serving/indexing remains blocked until validation passes.
    healing_log = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": "phase1",
        "detector": "great_expectations_and_freshness_sla",
        "triggered": not quality_success,
        "initial_quality_success": bool(quality_success),
        "trigger_signals": _failed_quality_signals(quality_report) if not quality_success else [],
        "attempts": [],
    }

    if not quality_success:
        print("  -> AUTO-HEAL TRIGGERED: Quality violations detected; blocking vector indexing.")
        repair_strategies = []
        if settings.paths.raw_records_json.exists():
            repair_strategies.append(
                ("rebuild_from_raw_snapshot", lambda: load_raw_records(settings.paths.raw_records_json))
            )
        repair_strategies.append(
            (
                "refetch_crossref_and_rebuild",
                lambda: fetch_source_records(replace(settings, refresh_source=True)),
            )
        )

        for strategy_name, load_records in repair_strategies:
            attempt = {"strategy": strategy_name, "success": False}
            print(f"  -> Auto-repair attempt: {strategy_name}")
            try:
                repaired_records = load_records()
                repaired_df = build_clean_dataframe(repaired_records, run_date=now)
                _persist_clean_dataframe(repaired_df, settings)
                repaired_quality = run_data_quality_checks(repaired_df, settings, "baseline")
                attempt["quality_success"] = bool(repaired_quality.get("success", False))
                attempt["row_count"] = len(repaired_df)
                attempt["success"] = attempt["quality_success"]
                if attempt["success"]:
                    records = repaired_records
                    df = repaired_df
                    quality_report = repaired_quality
                    quality_success = True
                    print(f"  -> Auto-repair succeeded with {strategy_name}.")
            except Exception as exc:
                attempt["error"] = str(exc)
                print(f"  -> Auto-repair attempt failed: {exc}")
            healing_log["attempts"].append(attempt)
            if quality_success:
                break

    healing_log["final_quality_success"] = bool(quality_success)
    healing_log["serving_allowed"] = bool(quality_success)
    healing_log_path = settings.paths.project_dir / "data" / "results" / "phase1_self_healing_log.json"
    write_json(healing_log_path, healing_log)
    print(f"  -> Self-healing audit log: {healing_log_path}")

    if not quality_success:
        raise RuntimeError(
            "Quality Gate still fails after automatic repair/refetch; vector indexing is blocked."
        )

    freshness_report = quality_report.get("freshness", {})

    # 5. Build Chroma Vector Index
    print("\n[Step 4/6] Retrieval: Indexing clean papers into ChromaDB...")
    index = LocalEmbeddingIndex.build(
        df=df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    print(f"  -> Successfully indexed {len(df)} documents into collection '{settings.baseline_collection_name}'.")

    # 6. Evaluation: Test Set & Benchmark
    print("\n[Step 5/6] Evaluation: Generating test set and evaluating baseline RAG...")
    if settings.paths.eval_testset.exists() and not settings.refresh_test_set:
        print(f"  -> Loading existing test set from {settings.paths.eval_testset}")
        test_set = read_json(settings.paths.eval_testset)
    else:
        print(f"  -> Building fresh test set...")
        test_set = build_test_set(df=df, output_path=settings.paths.eval_testset)
    print(f"  -> Benchmark test set ready with {len(test_set)} questions across 4 categories.")

    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    summary = bundle.summary
    print(f"  -> Retrieval Hit Rate: {summary.get('retrieval_hit_rate', 0.0):.4f}")
    print(f"  -> Mean Token F1     : {summary.get('mean_token_f1', 0.0):.4f}")
    print(f"  -> Judge Accuracy    : {summary.get('judge_accuracy', 0.0):.4f}")

    # 7. Generate Phase 1 Report
    print("\n[Step 6/6] Reporting: Generating Phase 1 Baseline Report...")
    source_summary = {
        "Source API": settings.source_api,
        "Query": settings.source_query,
        "Total Ingested": len(records),
        "Clean Records": len(df),
        "Collection Name": settings.baseline_collection_name,
        "Embedding Model": settings.embedding_model,
        "Run Date": now.date().isoformat(),
    }
    settings.paths.baseline_report.parent.mkdir(parents=True, exist_ok=True)
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=summary,
        quality=quality_report,
        freshness=freshness_report,
    )
    print(f"  -> Baseline report generated at: {settings.paths.baseline_report}")

    # Optional: Quick Agent Demo
    try:
        agent = build_agent(settings, index)
        demo_question = test_set[0]["question"] if test_set else "What are these papers about?"
        demo_response = agent.invoke({"messages": [{"role": "user", "content": demo_question}]})
        write_json(settings.paths.demo_answers, demo_response)
        print(f"  -> Agent demo answers recorded at: {settings.paths.demo_answers}")
    except Exception as exc:
        print(f"  -> Agent demo skipped: {exc}")

    print("\n" + "=" * 60)
    print("[DONE] PHASE 1 BASELINE PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
