"""Markdown reporting.

Owner: Kien (Observability & Reporting).
generate_phase1_report -> Pha 1. generate_corruption_report -> Pha 2.
"""

from __future__ import annotations

from typing import Any

from core.utils import write_text


def _fmt(value: Any) -> str:
    return f"{value:.3f}" if isinstance(value, (int, float)) else str(value)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viet markdown report cho baseline phase, tro toi artifact that."""
    lines: list[str] = [
        "# Phase 1 — Baseline Report",
        "",
        "## Nguon du lieu",
        f"- Source: {source_summary.get('source')}",
        f"- Query: {source_summary.get('query')}",
        f"- Filter: {source_summary.get('filter')}",
        f"- So records: {source_summary.get('records')}",
        "",
        "## Metrics (baseline)",
        f"- retrieval_hit_rate: {_fmt(metrics.get('retrieval_hit_rate'))}",
        f"- mean_token_f1: {_fmt(metrics.get('mean_token_f1'))}",
        f"- judge_accuracy: {_fmt(metrics.get('judge_accuracy'))}",
        f"- mean_judge_score: {_fmt(metrics.get('mean_judge_score'))}",
        f"- samples: {metrics.get('samples')}",
        "",
        "## Data quality",
        f"- Passed {quality.get('passed')}/{quality.get('total_checks')} checks",
    ]
    for check in quality.get("checks", []):
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(f"  - [{status}] {check['check']} ({check['dimension']}) — {check['detail']}")

    lines += [
        "",
        "## Freshness",
        f"- latest_published: {freshness.get('latest_published')}",
        f"- oldest_published: {freshness.get('oldest_published')}",
        f"- stale_rows: {freshness.get('stale_rows')}/{freshness.get('total_rows')}",
        f"- threshold_days: {freshness.get('threshold_days')}",
        f"- is_fresh: {freshness.get('is_fresh')}",
        "",
    ]
    write_text(report_path, "\n".join(lines) + "\n")


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
    """Viet markdown report so sanh baseline/corrupted/repaired tro toi artifact that."""
    metric_keys = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]

    lines: list[str] = [
        "# Corruption Comparison Report",
        "",
        "## Metrics: baseline vs corrupted vs repaired",
        "",
        "| Metric | Baseline | Corrupted | Repaired | Δ corruption | Δ repair |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key in metric_keys:
        base = baseline_metrics.get(key)
        corr = corrupted_metrics.get(key)
        rep = repaired_metrics.get(key)
        d_corr = (corr - base) if isinstance(base, (int, float)) and isinstance(corr, (int, float)) else None
        d_rep = (rep - corr) if isinstance(corr, (int, float)) and isinstance(rep, (int, float)) else None
        lines.append(
            f"| {key} | {_fmt(base)} | {_fmt(corr)} | {_fmt(rep)} | {_fmt(d_corr)} | {_fmt(d_rep)} |"
        )

    lines += [
        "",
        "## Data quality (passed / total)",
        f"- corrupted: {corrupted_quality.get('passed')}/{corrupted_quality.get('total_checks')}",
        f"- repaired: {repaired_quality.get('passed')}/{repaired_quality.get('total_checks')}",
        "",
        "## Freshness",
        f"- corrupted: is_fresh={corrupted_freshness.get('is_fresh')}, "
        f"stale_rows={corrupted_freshness.get('stale_rows')}/{corrupted_freshness.get('total_rows')}",
        f"- repaired: is_fresh={repaired_freshness.get('is_fresh')}, "
        f"stale_rows={repaired_freshness.get('stale_rows')}/{repaired_freshness.get('total_rows')}",
        "",
        "## Ket luan nhan qua",
        "1. Corruption (blank summary / stale date / noise / truncate / duplicate) "
        "-> quality checks FAIL + freshness stale -> retrieval_hit_rate & mean_token_f1 giam.",
        "2. Repair chay lai cleaning tu raw source -> quality/freshness phuc hoi "
        "-> metrics quay lai gan baseline.",
        "",
        "> Luu y: chi ket luan corruption 'co tac dong' khi so lieu that su thay doi. "
        "Neu recovery chua hoan toan, ghi ro signal/metric con xau.",
        "",
    ]
    write_text(report_path, "\n".join(lines) + "\n")
