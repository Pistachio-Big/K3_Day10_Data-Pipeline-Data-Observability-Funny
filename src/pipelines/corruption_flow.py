"""Corruption -> evaluate -> repair -> compare flow (Pha 2).

Owner: Dai (Pipeline Integrator).

Dung path + collection RIENG cho corrupted/repaired; KHONG ghi de baseline.
Danh gia ca 3 trang thai tren CUNG test_set.json de so sanh cong bang.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    settings = load_settings()
    paths = settings.paths

    if not paths.clean_json.exists() or not paths.baseline_metrics.exists():
        raise RuntimeError("Chua co baseline artifact. Chay script/run_phase1.py truoc.")
    if not paths.eval_testset.exists():
        raise RuntimeError("Chua co test_set.json. Chay baseline truoc de khoa test set.")

    baseline_df = pd.DataFrame(read_json(paths.clean_json))
    baseline_metrics = read_json(paths.baseline_metrics)

    # --- CORRUPT -------------------------------------------------------------
    corrupted_df = corrupt_clean_dataframe(baseline_df, paths.corruption_log)
    write_csv(corrupted_df, paths.corrupted_clean_csv)
    write_json(paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))

    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, embeddings_output_path=paths.corrupted_embeddings_json
    )
    corrupted_bundle = evaluate_pipeline(
        settings, corrupted_index, paths.eval_testset, paths.corrupted_metrics, paths.corrupted_answers
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, report_name="corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, paths.quality_dir / "freshness_corrupted.json"
    )

    # --- REPAIR (chay lai cleaning tu raw source, khong sua tay) --------------
    records = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(records, run_date=datetime.now(timezone.utc))
    write_csv(repaired_df, paths.repaired_clean_csv)
    write_json(paths.repaired_clean_json, repaired_df.to_dict(orient="records"))

    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, embeddings_output_path=paths.repaired_embeddings_json
    )
    repaired_bundle = evaluate_pipeline(
        settings, repaired_index, paths.eval_testset, paths.repaired_metrics, paths.repaired_answers
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, report_name="repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, paths.quality_dir / "freshness_repaired.json"
    )

    # --- COMPARE -------------------------------------------------------------
    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics,
        corrupted_bundle.summary,
        repaired_bundle.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )

    def line(name: str, metrics: dict) -> str:
        return (
            f"  {name:9s} hit={metrics['retrieval_hit_rate']:.3f} "
            f"f1={metrics['mean_token_f1']:.3f} "
            f"judge_acc={metrics['judge_accuracy']:.3f} "
            f"judge={metrics['mean_judge_score']:.2f}"
        )

    print("[corruption_flow] hoan tat.")
    print(line("baseline", baseline_metrics))
    print(line("corrupted", corrupted_bundle.summary))
    print(line("repaired", repaired_bundle.summary))
    print(f"  quality corrupted={corrupted_quality['passed']}/{corrupted_quality['total_checks']} "
          f"repaired={repaired_quality['passed']}/{repaired_quality['total_checks']}")
    print(f"  report: {paths.comparison_report}")


if __name__ == "__main__":
    main()
