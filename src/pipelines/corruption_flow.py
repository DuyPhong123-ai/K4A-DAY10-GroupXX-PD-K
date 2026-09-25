from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.config import load_settings
from core.utils import read_json, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    print("=" * 70)
    print(">>> STARTING CORRUPTION, EVALUATION, REPAIR & COMPARISON FLOW")
    print("=" * 70)

    # 1. Load settings
    settings = load_settings()
    now = datetime.now(timezone.utc)

    # 2. Verify / Load Baseline State
    print("\n[Step 1/5] Checking baseline artifacts...")
    if not settings.paths.clean_json.exists() or not settings.paths.baseline_metrics.exists():
        print("  -> Baseline artifacts not found! Automatically running Phase 1 first...")
        from pipelines.phase1 import main as run_phase1

        run_phase1()

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = pd.read_json(settings.paths.clean_json)
    print(f"  -> Baseline loaded: {len(clean_df)} clean papers.")
    print(f"  -> Baseline Hit Rate: {baseline_metrics.get('retrieval_hit_rate', 0.0):.4f}")
    print(f"  -> Baseline Token F1: {baseline_metrics.get('mean_token_f1', 0.0):.4f}")

    # 3. Simulate Data Corruption (Checkpoint 4)
    print("\n[Step 2/5] Corruption: Injecting 6 controlled data corruption scenarios...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)

    settings.paths.corrupted_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    corrupted_df.to_csv(settings.paths.corrupted_clean_csv, index=False)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    print(f"  -> Corrupted dataset saved ({len(corrupted_df)} records). Log written to:")
    print(f"     {settings.paths.corruption_log}")

    # 4. Observability on Corrupted Data
    print("\n[Step 3/5] Observability: Validating corrupted dataset against Quality Gate...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = corrupted_quality.get("freshness", {})
    print(f"  -> Corrupted Quality Gate Status: {corrupted_quality.get('success', False)} (Expected: False)")
    print(f"  -> Corrupted Freshness SLA Status: {corrupted_freshness.get('is_fresh', False)} (Expected: False)")

    # Index and evaluate corrupted corpus
    print("  -> Indexing corrupted papers into collection 'papers-corrupted'...")
    corrupted_index = LocalEmbeddingIndex.build(
        df=corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    print("  -> Evaluating RAG degradation on corrupted data...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_bundle.summary
    print(f"  -> Corrupted Hit Rate: {corrupted_metrics.get('retrieval_hit_rate', 0.0):.4f}")
    print(f"  -> Corrupted Token F1: {corrupted_metrics.get('mean_token_f1', 0.0):.4f}")

    # 5. Idempotent Repair (Checkpoint 5)
    print("\n[Step 4/5] Self-Healing: Executing Idempotent Repair from raw snapshot...")
    if settings.paths.raw_records_json.exists():
        raw_records = load_raw_records(settings.paths.raw_records_json)
    else:
        raw_records = fetch_source_records(settings)

    repaired_df = build_clean_dataframe(raw_records, run_date=now)
    settings.paths.repaired_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    repaired_df.to_csv(settings.paths.repaired_clean_csv, index=False)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    print(f"  -> Repaired dataset rebuilt from raw source ({len(repaired_df)} records).")

    print("  -> Validating repaired dataset with Quality Gate...")
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = repaired_quality.get("freshness", {})
    print(f"  -> Repaired Quality Gate Status: {repaired_quality.get('success', False)} (Expected: True)")
    print(f"  -> Repaired Freshness SLA Status: {repaired_freshness.get('is_fresh', False)} (Expected: True)")

    print("  -> Indexing repaired papers into collection 'papers-repaired'...")
    repaired_index = LocalEmbeddingIndex.build(
        df=repaired_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )

    print("  -> Evaluating recovered RAG performance...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_bundle.summary
    print(f"  -> Repaired Hit Rate: {repaired_metrics.get('retrieval_hit_rate', 0.0):.4f}")
    print(f"  -> Repaired Token F1: {repaired_metrics.get('mean_token_f1', 0.0):.4f}")

    # 6. Generate Three-State Comparison Report
    print("\n[Step 5/5] Reporting: Generating three-state comparison report...")
    settings.paths.comparison_report.parent.mkdir(parents=True, exist_ok=True)
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"  -> Comparison report saved at: {settings.paths.comparison_report}")

    # 7. Print Comparative Table to Console
    print("\n" + "=" * 70)
    print("📊 THREE-STATE PERFORMANCE COMPARISON SUMMARY:")
    print("=" * 70)
    print(f"{'Metric / Signal':<25} | {'Baseline':<12} | {'Corrupted':<12} | {'Repaired':<12}")
    print("-" * 70)
    print(
        f"{'Retrieval Hit Rate':<25} | "
        f"{baseline_metrics.get('retrieval_hit_rate', 0.0):<12.4f} | "
        f"{corrupted_metrics.get('retrieval_hit_rate', 0.0):<12.4f} | "
        f"{repaired_metrics.get('retrieval_hit_rate', 0.0):<12.4f}"
    )
    print(
        f"{'Mean Token F1':<25} | "
        f"{baseline_metrics.get('mean_token_f1', 0.0):<12.4f} | "
        f"{corrupted_metrics.get('mean_token_f1', 0.0):<12.4f} | "
        f"{repaired_metrics.get('mean_token_f1', 0.0):<12.4f}"
    )
    print(
        f"{'Quality Gate':<25} | "
        f"{'PASS':<12} | "
        f"{'FAIL' if not corrupted_quality.get('success', False) else 'PASS':<12} | "
        f"{'PASS' if repaired_quality.get('success', False) else 'FAIL':<12}"
    )
    print(
        f"{'Freshness SLA':<25} | "
        f"{'PASS':<12} | "
        f"{'FAIL' if not corrupted_freshness.get('is_fresh', False) else 'PASS':<12} | "
        f"{'PASS' if repaired_freshness.get('is_fresh', False) else 'FAIL':<12}"
    )
    print("=" * 70)
    print("[DONE] CORRUPTION & REPAIR FLOW COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
