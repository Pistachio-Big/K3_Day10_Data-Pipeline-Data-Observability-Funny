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
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
