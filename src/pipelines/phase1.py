"""Baseline pipeline end-to-end (Pha 1).

Owner: Dai (Pipeline Integrator).

Luong: raw -> clean -> index -> test set -> evaluate -> quality/freshness -> report.
"""

from __future__ import annotations

from datetime import datetime, timezone

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    settings = load_settings()
    paths = settings.paths

    # 1. Raw: fetch neu chua co snapshot hoac REFRESH_SOURCE=1, nguoc lai load lai.
    if settings.refresh_source or not paths.raw_records_json.exists():
        print("[phase1] Fetching records from source...")
        records = fetch_source_records(settings)
    else:
        print("[phase1] Loading raw records tu snapshot...")
        records = load_raw_records(paths.raw_records_json)
    print(f"[phase1] raw records = {len(records)}")

    # 2. Clean.
    df = build_clean_dataframe(records, run_date=datetime.now(timezone.utc))
    write_csv(df, paths.clean_csv)
    write_json(paths.clean_json, df.to_dict(orient="records"))

    # 3. Build Chroma index (collection papers-baseline).
    index = LocalEmbeddingIndex.build(df, settings, embeddings_output_path=paths.embeddings_json)

    # 4. Test set: tao moi neu chua co / REFRESH_TEST_SET, nguoc lai giu nguyen.
    if settings.refresh_test_set or not paths.eval_testset.exists():
        build_test_set(df, paths.eval_testset)
    print(f"[phase1] test set = {len(read_json(paths.eval_testset))} cau hoi")

    # 5. Evaluate -> baseline_metrics.json + baseline_answers.json.
    bundle = evaluate_pipeline(
        settings,
        index,
        paths.eval_testset,
        paths.baseline_metrics,
        paths.baseline_answers,
    )

    # 6. Data quality + freshness.
    quality = run_data_quality_checks(df, settings, report_name="baseline")
    freshness = build_freshness_report(df, settings, paths.freshness_report)

    # 7. Markdown report.
    source_summary = {
        "source": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "records": len(df),
    }
    generate_phase1_report(paths.baseline_report, source_summary, bundle.summary, quality, freshness)

    print("[phase1] Baseline hoan tat.")
    print(f"  metrics : {paths.baseline_metrics}")
    print(f"  quality : passed {quality['passed']}/{quality['total_checks']}")
    print(f"  fresh   : is_fresh={freshness['is_fresh']}")
    print(f"  report  : {paths.baseline_report}")


if __name__ == "__main__":
    main()
