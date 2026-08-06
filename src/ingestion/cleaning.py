"""Cleaning raw records -> dataframe san sang de embed.

Owner: Huy Anh (Cleaning). Pha 1.

Output dataframe la CONTRACT cho ca nhom: index.py va qa.py bat buoc cac cot
paper_id, title, summary, authors_joined, categories_joined, published,
abs_url, pdf_url, text_for_embedding, age_days.
"""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def _parse_iso_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean va chuan hoa records; tinh freshness; build text_for_embedding.

    Quy tac cleaning (moi filter deu de lai count de truy vet):
    - Loai record thieu paper_id hoac title (Completeness).
    - Loai record khong parse duoc published (can cho freshness).
    - Dedupe theo paper_id.
    """
    run_day = run_date.date()
    rows: list[dict] = []
    dropped_missing = 0
    dropped_no_date = 0

    for record in records:
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        if not record.paper_id or not title:
            dropped_missing += 1
            continue

        published_date = _parse_iso_date(record.published)
        if published_date is None:
            dropped_no_date += 1
            continue

        published = published_date.isoformat()
        age_days = (run_day - published_date).days
        authors_joined = compact_join(record.authors)
        categories_joined = compact_join(record.categories)
        text_for_embedding = normalize_whitespace(
            f"{title}. {summary} Authors: {authors_joined}. Categories: {categories_joined}."
        )

        rows.append(
            {
                "paper_id": str(record.paper_id),
                "title": title,
                "summary": summary,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "primary_category": record.primary_category,
                "published": published,
                "updated": record.updated,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "summary_chars": len(summary),
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("Cleaning tao ra dataframe rong; kiem tra raw records.")

    before_dedupe = len(df)
    df = df.drop_duplicates(subset="paper_id", keep="first")
    df = df[df["text_for_embedding"].str.len() > 0]
    df = df.sort_values("published", ascending=False).reset_index(drop=True)

    print(
        f"[cleaning] input={len(records)} "
        f"dropped_missing_title={dropped_missing} dropped_no_date={dropped_no_date} "
        f"dropped_duplicates={before_dedupe - df['paper_id'].nunique()} clean_rows={len(df)}"
    )
    return df
