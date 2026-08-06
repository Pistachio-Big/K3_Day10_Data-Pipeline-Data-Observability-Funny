# Commit map CP0 → CP3 (Baseline đã chạy thật)

Baseline đã chạy end-to-end với LLM judge thật (OpenRouter). Mỗi thành viên commit **file source mình sở hữu + artifact do module mình sinh ra**.

**KHÔNG commit:**
- `.env` (chứa API key — đã nằm trong `.gitignore`).
- `data/chroma/` (DB vector nhị phân, nặng, tái tạo được từ `papers_embeddings.json`). Khuyến nghị thêm dòng `data/chroma/` vào `.gitignore`.

---

## Phái — Ingestion (CP0)
**Đã làm:** implement `parse_crossref_payload` + `fetch_source_records` (retry/backoff 429/5xx, lưu raw response trước khi parse) + `load_raw_records`. Sinh snapshot 24 records từ Crossref, `paper_id = DOI`.
**Commit:**
```bash
git add src/ingestion/crossref.py data/raw/crossref_response.json data/raw/crossref_records.json
git commit -m "feat(ingestion): Crossref fetch/parse/load + raw snapshot (CP0)"
```

## Huy Anh — Cleaning (CP1)
**Đã làm:** implement `build_clean_dataframe` (normalize title/summary/authors/categories, parse date, tính `age_days`, build `text_for_embedding`, dedupe theo `paper_id`, log count filter). Kết quả: 24 rows sạch, 0 record bị loại.
**Commit:**
```bash
git add src/ingestion/cleaning.py data/clean/papers_clean.csv data/clean/papers_clean.json
git commit -m "feat(cleaning): clean dataframe + text_for_embedding + age_days (CP1)"
```

## Phong — RAG & Evaluation (CP2 + phần eval của CP3)
**Đã làm:** implement `build_test_set` (24 câu hỏi, 4 loại summary/authors/date/categories, dùng đúng cụm khóa của `qa._extract_answer`); vận hành `LocalEmbeddingIndex` build collection `papers-baseline` + smoke test search/lookup/agent. Evaluation sinh metrics + answers (hit 1.0, token_f1 1.0, judge 1.0/5, 24/24 judge LLM thật).
**Commit:**
```bash
git add src/evaluation/testset.py data/eval/test_set.json data/embeddings/papers_embeddings.json data/results/baseline_metrics.json data/results/baseline_answers.json
git commit -m "feat(eval): test set + baseline index/metrics/answers (CP2-CP3)"
```

## Kiên — Observability & Reporting (CP1 quality + CP3 report)
**Đã làm:** implement `run_data_quality_checks` (6 checks: row count, paper_id null/unique, title, summary length, freshness) + `build_freshness_report` + `generate_phase1_report`. Kết quả: quality 6/6 pass, `is_fresh=True`, baseline report markdown.
**Commit:**
```bash
git add src/observability/quality.py src/observability/reporting.py data/quality/quality_baseline.json data/quality/freshness_report.json data/reports/phase1_report.md
git commit -m "feat(observability): quality + freshness + phase1 report (CP1-CP3)"
```
> Lưu ý: `reporting.py` mới implement `generate_phase1_report`; `generate_corruption_report` vẫn `NotImplementedError` (để CP6).

## Đại — Lead / Integrator (CP0 setup + CP3 orchestration & run)
**Đã làm:** implement `phase1.py::main` (raw→clean→index→testset→evaluate→quality/freshness→report); cấu hình `.env` provider (OpenRouter, model `openai/gpt-4o-mini`); chạy `run_phase1.py` end-to-end, verify artifact; điều phối handoff cả nhóm.
**Commit:**
```bash
git add src/pipelines/phase1.py report/checkpoint-plan.md report/commit-map-cp0-cp3.md
git commit -m "feat(pipeline): baseline phase1 orchestration end-to-end (CP3)"
```
> Khuyến nghị Đại thêm `data/chroma/` vào `.gitignore` (một commit riêng) trước khi cả nhóm add `data/`.

---

## Bảng tổng hợp file → người commit

| File | Người | CP |
|------|-------|----|
| `src/ingestion/crossref.py` | Phái | CP0 |
| `data/raw/crossref_response.json` | Phái | CP0 |
| `data/raw/crossref_records.json` | Phái | CP0 |
| `src/ingestion/cleaning.py` | Huy Anh | CP1 |
| `data/clean/papers_clean.csv` | Huy Anh | CP1 |
| `data/clean/papers_clean.json` | Huy Anh | CP1 |
| `src/evaluation/testset.py` | Phong | CP2 |
| `data/eval/test_set.json` | Phong | CP2 |
| `data/embeddings/papers_embeddings.json` | Phong | CP2 |
| `data/results/baseline_metrics.json` | Phong | CP3 |
| `data/results/baseline_answers.json` | Phong | CP3 |
| `src/observability/quality.py` | Kiên | CP1 |
| `src/observability/reporting.py` | Kiên | CP1/CP3 |
| `data/quality/quality_baseline.json` | Kiên | CP1 |
| `data/quality/freshness_report.json` | Kiên | CP1 |
| `data/reports/phase1_report.md` | Kiên | CP3 |
| `src/pipelines/phase1.py` | Đại | CP3 |
| `report/checkpoint-plan.md`, `report/commit-map-cp0-cp3.md` | Đại | — |

**Không commit:** `.env`, `data/chroma/` (nên gitignore).
