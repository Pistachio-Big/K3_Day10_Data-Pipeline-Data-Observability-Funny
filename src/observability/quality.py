"""Data quality checks va freshness reporting.

Owner: Kien (Observability). Pha 1.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json

MIN_SUMMARY_CHARS = 20
MIN_SUMMARY_COVERAGE = 0.8


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chay bo data quality checks va ghi ket qua vao data/quality/."""
    checks: list[dict[str, Any]] = []

    def add(name: str, dimension: str, passed: bool, detail: dict[str, Any]) -> None:
        checks.append({"check": name, "dimension": dimension, "passed": bool(passed), "detail": detail})

    row_count = len(df)
    add("row_count", "Completeness", row_count > 0, {"rows": row_count})

    paper_id_nulls = int(df["paper_id"].isna().sum())
    add("paper_id_not_null", "Completeness", paper_id_nulls == 0, {"nulls": paper_id_nulls})

    duplicate_ids = int(row_count - df["paper_id"].nunique())
    add("paper_id_unique", "Uniqueness", duplicate_ids == 0, {"duplicates": duplicate_ids})

    empty_titles = int((df["title"].fillna("").str.len() == 0).sum())
    add("title_not_null", "Completeness", empty_titles == 0, {"empty_titles": empty_titles})

    summary_len = df["summary"].fillna("").str.len()
    below = int((summary_len < MIN_SUMMARY_CHARS).sum())
    coverage = float((summary_len >= MIN_SUMMARY_CHARS).mean()) if row_count else 0.0
    add(
        "summary_length",
        "Validity",
        coverage >= MIN_SUMMARY_COVERAGE,
        {"below_threshold": below, "min_chars": MIN_SUMMARY_CHARS, "coverage": round(coverage, 3)},
    )

    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
    add(
        "freshness",
        "Timeliness",
        stale_rows == 0,
        {"stale_rows": stale_rows, "threshold_days": settings.freshness_threshold_days},
    )

    result = {
        "report_name": report_name,
        "total_checks": len(checks),
        "passed": sum(1 for c in checks if c["passed"]),
        "failed": sum(1 for c in checks if not c["passed"]),
        "checks": checks,
    }
    write_json(settings.paths.quality_dir / f"quality_{report_name}.json", result)
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tong hop freshness report va ghi JSON."""
    published = df["published"].dropna()
    published = published[published.str.len() > 0]
    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())

    payload = {
        "latest_published": published.max() if not published.empty else None,
        "oldest_published": published.min() if not published.empty else None,
        "stale_rows": stale_rows,
        "total_rows": len(df),
        "threshold_days": settings.freshness_threshold_days,
        "is_fresh": stale_rows == 0,
    }
    write_json(report_path, payload)
    return payload
