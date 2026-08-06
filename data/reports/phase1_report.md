# Phase 1 — Baseline Report

## Nguon du lieu
- Source: Crossref REST API
- Query: agentic retrieval augmented generation large language model
- Filter: from-pub-date:2026-02-07,has-abstract:true
- So records: 24

## Metrics (baseline)
- retrieval_hit_rate: 1.000
- mean_token_f1: 1.000
- judge_accuracy: 0.958
- mean_judge_score: 4.833
- samples: 24

## Data quality
- Passed 6/6 checks
  - [PASS] row_count (Completeness) — {'rows': 24}
  - [PASS] paper_id_not_null (Completeness) — {'nulls': 0}
  - [PASS] paper_id_unique (Uniqueness) — {'duplicates': 0}
  - [PASS] title_not_null (Completeness) — {'empty_titles': 0}
  - [PASS] summary_length (Validity) — {'below_threshold': 0, 'min_chars': 20, 'coverage': 1.0}
  - [PASS] freshness (Timeliness) — {'stale_rows': 0, 'threshold_days': 180}

## Freshness
- latest_published: 2026-08-01
- oldest_published: 2026-02-12
- stale_rows: 0/24
- threshold_days: 180
- is_fresh: True

