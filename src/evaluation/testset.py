"""Tao evaluation set tu cleaned dataframe.

Owner: Phong (RAG & Evaluation). Pha 1.

Cau hoi phai dung dung cum khoa ma qa._extract_answer nhan dien:
- "who authored" -> authors_joined
- "when was ... published on" -> published
- "what categories" -> categories_joined
- con lai -> first_sentence(summary)
Title duoc nhung trong dau '...' de agent lookup exact match (qa.py regex).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

MIN_DOCUMENTS = 4
MAX_PAPERS = 8


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao bo cau hoi (summary/authors/date/categories) tu cleaned dataframe."""
    if len(df) < MIN_DOCUMENTS:
        raise ValueError(f"Can toi thieu {MIN_DOCUMENTS} document de tao test set, hien co {len(df)}.")

    sample = df.head(MAX_PAPERS)
    test_set: list[dict[str, Any]] = []

    for i, row in enumerate(sample.itertuples(index=False)):
        paper_id = str(row.paper_id)
        title = row.title

        test_set.append(
            {
                "id": f"q_summary_{i}",
                "question_type": "summary",
                "question": f"Summarize the paper titled '{title}'.",
                "ground_truth": first_sentence(row.summary),
                "ground_truth_doc_ids": [paper_id],
            }
        )
        if row.authors_joined:
            test_set.append(
                {
                    "id": f"q_authors_{i}",
                    "question_type": "authors",
                    "question": f"Who authored the paper titled '{title}'?",
                    "ground_truth": row.authors_joined,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
        test_set.append(
            {
                "id": f"q_date_{i}",
                "question_type": "date",
                "question": f"When was the paper titled '{title}' published on?",
                "ground_truth": row.published,
                "ground_truth_doc_ids": [paper_id],
            }
        )
        if row.categories_joined:
            test_set.append(
                {
                    "id": f"q_categories_{i}",
                    "question_type": "categories",
                    "question": f"What categories does the paper titled '{title}' belong to?",
                    "ground_truth": row.categories_joined,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    write_json(output_path, test_set)
    return test_set
