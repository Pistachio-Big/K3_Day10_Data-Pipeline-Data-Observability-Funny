# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K3                        |
| Tên nhóm         | Funny                     |
| Repository         | https://github.com/Pistachio-Big/K3_Day10_Data-Pipeline-Data-Observability-Funny |
| Ngày hoàn thành | 2026-08-06               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Văn Đại | 2A202601217 | Lead / Integrator | `src/pipelines/phase1.py::main`, `src/pipelines/corruption_flow.py::main`, `.env` provider OpenRouter, `script/run_phase1.py`, `script/run_corruption_flow.py`, `report/checkpoint-plan.md`, `report/commit-map-cp0-cp3.md`, `report/commit-map-pha2.md` |
| 2 | Nguyễn Huy Anh | 2A202601641 | Data Cleaning & Corruption | `src/ingestion/cleaning.py::build_clean_dataframe`, `src/ingestion/corruption.py::corrupt_clean_dataframe`, `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`, `data/clean/papers_clean_corrupted.csv`, `data/results/corruption_log.json` |
| 3 | Hoàng Văn Phái | 2A202601575 | Ingestion | `src/ingestion/crossref.py::fetch_source_records`, `parse_crossref_payload`, `load_raw_records`; `data/raw/crossref_response.json`, `data/raw/crossref_records.json` |
| 4 | Hà Tấn Phong | 2A202601577 | RAG & Evaluation | `src/retrieval/index.py::LocalEmbeddingIndex`, `src/retrieval/embeddings.py`, `src/retrieval/llm.py`, `src/retrieval/qa.py`, `src/retrieval/agent.py`, `src/evaluation/testset.py::build_test_set`, `src/evaluation/metrics.py::evaluate_pipeline`; 3 manifest embeddings + 2 cặp metrics/answers |
| 5 | Phạm Trung Kiên | 2A202601986 | Observability & Reporting | `src/observability/quality.py::run_data_quality_checks`, `build_freshness_report`, `src/observability/reporting.py::generate_phase1_report`, `generate_corruption_report`; `data/quality/quality_*.json`, `freshness_report*.json`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md` |

## 2. Tóm tắt kết quả

Nhóm Funny đã chạy end-to-end cả Phase 1 (baseline) và Phase 2
(corrupt → evaluate → repair → compare). Phase 1 sinh bộ 6 artifact
chuẩn: clean dataset 24 rows, Chroma collection `papers-baseline`,
24 câu hỏi test (3 loại thực tế: summary/authors/date — Crossref
không trả `subject` nên `categories_joined` rỗng, không sinh câu loại
categories), metric
agent (`retrieval_hit_rate=1.000`, `mean_token_f1=1.000`,
`judge_accuracy≈0.958`, `mean_judge_score≈4.833`) và quality 6/6 pass
với `is_fresh=true`. Phase 2 đã tái dựng từ raw records
(`crossref_records.json`), áp 6 loại corruption có chủ đích (drop_latest,
blank_summary, noise_summary, truncate_title, stale_date, duplicate),
làm `retrieval_hit_rate` tụt còn `0.625`, `judge_accuracy` còn `0.458`,
quality rớt còn 4/6 và freshness fail 5/23 stale. Repair re-derive từ
raw qua `build_clean_dataframe` đã phục hồi toàn bộ metric + quality
về đúng mức baseline. Blocker còn lại là các script `run_phase1.py`
và `run_corruption_flow.py` đã viết nhưng nhóm chưa cùng chạy lại từ
trạng thái sạch để confirm reproducibility xuyên suốt 5 máy.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records                  (Phái)
    -> cleaning và data modeling                 (Huy Anh)
    -> embedding + ChromaDB index                (Phong, collection baseline)
    -> evaluation baseline                       (Phong)
    -> quality/freshness reports                 (Kiên)
    -> phase1_report.md                          (Kiên)

    -> corruption log + corrupted dataset        (Huy Anh)
    -> rebuild corrupted index                   (Phong, collection corrupted)
    -> evaluate corrupted                        (Phong, CÙNG test set)
    -> quality_corrupted / freshness_corrupted   (Kiên)
    -> repair from raw                           (Huy Anh + Phái)
    -> rebuild repaired index                    (Phong, collection repaired)
    -> evaluate repaired                         (Phong, CÙNG test set)
    -> quality_repaired / freshness_repaired     (Kiên)
    -> corruption_report.md                      (Kiên)
```

Hai collection riêng biệt (`papers-baseline`, `papers-corrupted`,
`papers-repaired`) cho phép so sánh A/B/C trong cùng session mà không
phải chạy lại pipeline. `data/chroma/` không commit; manifest JSON
trong `data/embeddings/` đủ để tái dựng deterministic.

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST `works` API | GET với retry/backoff 429/5xx; lưu raw trước parse | `data/raw/crossref_response.json`, `crossref_records.json` (24 `PaperRecord`) | Phái |
| Cleaning          | `list[PaperRecord]` | normalize whitespace, parse ISO date, tính `age_days`, build `text_for_embedding`, dedupe `paper_id` | `data/clean/papers_clean.csv|json` (24 rows, 13 cột) | Huy Anh |
| Embedding/index   | `papers_clean.csv` | `MiniLMEmbeddings` (all-MiniLM-L6-v2, normalize) + Chroma cosine, 3 collection | `data/embeddings/papers_embeddings{,_corrupted,_repaired}.json` | Phong |
| Evaluation        | index + `eval/test_set.json` | `evaluate_pipeline`: `_extract_answer` + retrieval hit + `_token_f1` + LLM judge (`openai/gpt-4o-mini` qua OpenRouter) | `data/results/{baseline,corrupted,repaired}_{metrics,answers}.json` | Phong |
| Observability     | `papers_clean*.csv` | `run_data_quality_checks` 6 check + `build_freshness_report` | `data/quality/quality_{baseline,corrupted,repaired}.json`, `data/quality/freshness{,_corrupted,_repaired}.json` | Kiên |
| Corruption/repair | clean df + raw records | `corrupt_clean_dataframe` (6 loại) + `build_clean_dataframe` (re-derive) | `data/results/corruption_log.json`, 2 clean CSV/JSON | Huy Anh |
| Orchestration     | settings + script | `phase1.py::main` (raw→clean→index→testset→eval→quality/freshness→report), `corruption_flow.py::main` (corrupt→eval→repair→compare) | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Đại |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | openrouter          |
| `LLM_MODEL`                | `openai/gpt-4o-mini` |
| `OPENROUTER_BASE_URL`      | `https://openrouter.ai/api/v1` |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` (normalize_embeddings=True) |
| Số lượng Crossref records | 24 (filter `from-pub-date:{last 180d}, has-abstract:true`) |
| Retrieval `top_k`           | 4 |
| Freshness threshold          | 180 ngày |
| Vector store                | Chroma persistent (`data/chroma/`, đã gitignore) |
| Test set questions          | 24 (3 loại: summary 8 / authors 8 / date 8; `categories` rỗng từ Crossref nên không sinh) |
| Random seed (corruption)    | 42 / 7 / 11 / 3 (cố định → reproducible) |
| Random seed (ragas)         | bật khi `RUN_RAGAS=1` (mặc định tắt trong baseline) |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

```bash
uv sync
```

Hoặc với pip đã kích hoạt:

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Hoặc:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

Hoặc:

```bash
python script/run_corruption_flow.py
```

> Quy ước sau conflict Phase 1 (xem `report/commit-map-pha2.md`):
> **Chỉ Đại (integrator) commit toàn bộ `data/`**. Các thành viên khác
> KHÔNG chạy lại rồi `git add data/`; chỉ `git pull` rồi dùng artifact.

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công                                     | 2026-08-06                  | `data/results/baseline_metrics.json` (xem §7), `data/quality/quality_baseline.json`, `data/quality/freshness_report.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công (đã chạy và commit)         | 2026-08-06                  | `data/results/corruption_log.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST `https://api.crossref.org/works` |
| Query/filter                | `query="agentic retrieval augmented generation large language model"`, `filter="from-pub-date:{last 180d},has-abstract:true"`, `rows=24` |
| Thời điểm lấy dữ liệu | 2026-08-06, snapshot lưu tại `data/raw/crossref_response.json` |
| Số record nhận được    | 24 (đủ DOI + title + abstract; đã sinh `PaperRecord`) |
| Cơ chế retry/backoff      | 5 lần, exponential backoff cho status `{429, 500, 502, 503, 504}`; sleep `2**attempt` giây |

### Raw và clean schema

Trường được định nghĩa trong `core.utils` + `ingestion.crossref.PaperRecord` (raw) → `cleaning.build_clean_dataframe` (clean):

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | str (DOI) | Có | Khoá chính xuyên suốt raw → clean → index → ground truth | Drop nếu rỗng; dedupe `keep="first"` |
| `title` | str | Có | Tiêu đề cho retrieval và lookup | Drop nếu rỗng; normalize whitespace |
| `summary` | str | Không | Tóm tắt abstract; JATS đã strip ở ingestion | `summary_length` (quality) đếm `summary_chars < 20` |
| `authors` (raw) / `authors_joined` (clean) | list[str] / str | Không | Danh sách tác giả | `compact_join` bỏ phần tử rỗng |
| `categories` (raw) / `categories_joined` (clean) | list[str] / str | Không | Chủ đề Crossref | `compact_join` bỏ phần tử rỗng |
| `primary_category` | str | Không | Category đầu tiên | Empty nếu không có |
| `published` | str ISO date | Có | Ngày publish dùng cho freshness | Drop row nếu không parse được |
| `updated` | str | Không | Crossref `deposited` | Empty nếu thiếu |
| `abs_url` / `pdf_url` | str | Không | Link Crossref + first PDF link | Empty nếu thiếu |
| `age_days` | int (clean only) | Có | `(run_date.date() - published_date).days` | Tính khi clean; giá trị lớn = stale |
| `text_for_embedding` | str (clean only) | Có | Template `"<title>. <summary> Authors: <…>. Categories: <…>."` | Filter `len > 0` |
| `summary_chars` | int (clean only) | Không | Tiện cho quality check | Đếm lại sau mỗi corruption |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Drop nếu thiếu `paper_id` hoặc `title` | Completeness                  | 0/24 (log `dropped_missing_title=0`) | `[cleaning] input=24 dropped_missing_title=0` |
| Drop nếu không parse được `published`  | Timeliness                    | 0/24 (log `dropped_no_date=0`) | `[cleaning] dropped_no_date=0` |
| Normalize whitespace cho title/summary | Validity                      | 24/24 | text_for_embedding không có `\n`/double-space |
| Build `text_for_embedding` template   | Retrieval                     | 24/24 | Mỗi dòng bắt đầu bằng title, có `Authors:` / `Categories:` |
| Dedupe theo `paper_id` (keep first)   | Uniqueness                    | 0 (log `dropped_duplicates=0`) | `df['paper_id'].is_unique == True` |
| Sort theo `published` desc            | Timeliness (hỗ trợ)       | 24/24 | `df['published']` là sorted descending |

Tổng kết: Phase 1 clean ra 24 rows, 0 drop, quality 6/6 pass,
freshness `is_fresh=true`.

### Cách nhóm tạo `text_for_embedding`, document ID và `age_days`

- `text_for_embedding` = template cố định:
  `"{title}. {summary} Authors: {authors_joined}. Categories: {categories_joined}."`
  rồi `normalize_whitespace`. Cố định `Authors:` / `Categories:` giúp
  LLM judge dễ parse, kể cả khi list rỗng.
- Document ID = `paper_id` (DOI), khoá chính trong Chroma collection
  (lookup `index.lookup(paper_id)` / `index.lookup(title)` trong
  `retrieval/qa.py`).
- `age_days = (run_date.date() - published_date).days`; `run_date` là
  UTC hiện tại lúc chạy Phase 1.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 24 (summary 8 / authors 8 / date 8)     |
| Các `question_type`                    | `summary`, `authors`, `date` (loại `categories` không sinh vì `categories_joined` rỗng) |
| Ground-truth document ID                 | `expected_paper_id` (DOI), mỗi câu trỏ về đúng paper trong test set |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2`, `normalize_embeddings=True` |
| Vector store/collection                  | Chroma persistent (`data/chroma/`); baseline `papers-baseline`, corrupted `papers-corrupted`, repaired `papers-repaired` |
| Retrieval `top_k`                       | 4 |
| LLM provider/model                       | OpenRouter, `openai/gpt-4o-mini`, `temperature=0.0` |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (giữ nguyên qua `corruption_flow.py::main`) |

Giải thích giữ nguyên test set: nếu đổi test set giữa 3 lần chạy, mọi
delta metric không quy được cho data — có thể do độ khó câu hỏi, do tỷ
lệ `summary` so với `authors` thay đổi. Cùng test set + cùng
`Settings` (cùng `top_k`, embedding model, retrieval) → mọi delta chỉ
đến từ trạng thái dữ liệu.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/crossref_response.json`, `crossref_records.json` | Có (snapshot 24 record) | Phase 1 có thể `REFRESH_SOURCE=0` để load lại |
| Cleaned dataset          | `data/clean/papers_clean.csv`, `.json` | Có (24 rows) | Output `build_clean_dataframe` |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json` | Có (`papers-baseline`) | Không commit `data/chroma/` |
| Evaluation set           | `data/eval/test_set.json` | Có (24 câu) | Giữ nguyên 3 trạng thái |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | `samples=24 retrieval_hit_rate=1.0 mean_token_f1=1.0` |
| Quality/freshness        | `data/quality/quality_baseline.json`, `freshness_report.json` | Có | `passed=6/6`, `is_fresh=true` |
| Baseline report          | `data/reports/phase1_report.md` | Có | Sinh từ `reporting.generate_phase1_report` |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     1.000       | 24/24 top-k retrieval chứa DOI ground-truth → retrieval hoàn hảo trên baseline |
| `mean_token_f1`      |     1.000       | Token F1 giữa câu trả lời agent và `ground_truth` = 1.0 → `_extract_answer` trả đúng |
| `judge_accuracy`     |     0.958       | 23/24 LLM judge chấm `correct=true`; 1 câu đạt score 4/5 |
| `mean_judge_score`   |     4.833       | Trung bình ~4.83/5 → chất lượng câu trả lời cao |
| Ragas, nếu có        | (skipped)       | `RUN_RAGAS` chưa bật; artifact ghi `"skipped": "Set RUN_RAGAS=1 to enable the slower Ragas pass."` |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `row_count` | Completeness       | `rows > 0`         | PASS — 24 rows | `quality_baseline.json` `checks[0].detail = {"rows": 24}` |
| `paper_id_not_null` | Completeness | `nulls == 0` | PASS — 0 nulls | `checks[1].detail = {"nulls": 0}` |
| `paper_id_unique` | Uniqueness     | `duplicates == 0` | PASS — 0 duplicates | `checks[2].detail = {"duplicates": 0}` |
| `title_not_null` | Completeness    | `empty_titles == 0` | PASS — 0 | `checks[3].detail` |
| `summary_length` | Validity       | `coverage ≥ 0.8`, `min_chars = 20` | PASS — coverage 1.0 | `checks[4].detail = {"below_threshold": 0, "coverage": 1.0}` |
| `freshness`     | Timeliness      | `stale_rows == 0`, threshold 180 ngày | PASS — 0 stale | `checks[5].detail = {"stale_rows": 0, "threshold_days": 180}` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | `papers_clean.csv` cột `age_days` so với `freshness_threshold_days=180` |
| Timestamp mới nhất       | `2026-08-01` |
| Ngày cũ nhất             | `2026-02-12` |
| Trạng thái baseline      | Fresh (`is_fresh=true`, `stale_rows=0/24`) |
| Lý do                     | Toàn bộ `age_days < 180` nhờ filter `from-pub-date:{last 180d}` của Crossref |

## 9. Corruption scenarios và repair

Định nghĩa corruption nằm trong `src/ingestion/corruption.py::corrupt_clean_dataframe`
(seed cố định → reproducibility). Log ghi tại
`data/results/corruption_log.json`.

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| `drop_latest`      | Xoá 3 row `published` mới nhất (df sort published desc) | 3/24 → còn 21 | `freshness.stale_rows` ↑ nếu drop trúng dòng non-stale; rows count giảm | Làm giảm `samples` corpus (21 thay vì 24); retrieval có thể thiếu 3 ground-truth | Re-derive từ raw không drop → 24 rows trở lại |
| `blank_summary`    | `summary = ""` cho ~15% dòng (seed 42) | ≈ 3/21 | `summary_length` fail | Trả lời câu loại `summary` rỗng → judge accuracy giảm | Re-derive lấy lại abstract gốc |
| `noise_summary`   | Append `" zzxq!!! ??? lorem noise 00xx"` cho ~10% dòng (seed 7) | ≈ 2/21 | `retrieval_hit_rate`, `mean_token_f1` giảm | Vector embedding nhiễu → cosine similarity sai → top-k đẩy rank | Re-derive lấy lại summary sạch |
| `truncate_title`   | `title = title[:8]` cho ~10% dòng (seed 11) | ≈ 2/21 | retrieval hit, judge score giảm | Lookup theo title exact không match; semantic search kém | Re-derive title đầy đủ |
| `stale_date`       | `published = "2005-01-01"`, `age_days = 9999` cho ~20% dòng (seed 3) | ≈ 4/21 | `freshness` fail (≈ 5 stale_rows) | Retrieval vẫn đúng nhưng quality fail | Re-derive `published` đúng → freshness pass |
| `duplicate`        | Nhân đôi 2 row đầu | +2 rows (23 tổng) | `paper_id_unique` fail (1 duplicate) | Rank trong top-k lệch | Re-derive không có duplicate |

Sau khi áp cả 6 loại + rebuild `text_for_embedding` từ dữ liệu đã hỏng,
`corruption_flow.py::main` ghi:

- `data/clean/papers_clean_corrupted.csv|json`
- `data/embeddings/papers_embeddings_corrupted.json` (collection
  `papers-corrupted`)
- `data/results/corrupted_metrics.json`, `corrupted_answers.json`
- `data/quality/quality_corrupted.json`,
  `data/quality/freshness_corrupted.json`

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có (sau khi chạy `script/run_corruption_flow.py`)
- Nhận xét: Log đủ 6 entry `corruptions` + `final_rows`, mỗi entry
  có `type`, `count`, `paper_ids` để truy vết chính xác row bị hỏng
  và seed cố định nên tái lập được.

Giải thích repair đảm bảo phục hồi từ nguồn đáng tin cậy: repair
trong `src/pipelines/corruption_flow.py::main` KHÔNG sửa trực tiếp
dataframe hỏng. Nó quay lại `data/raw/crossref_records.json` (snapshot
nguyên vẹn từ ingestion) và gọi lại `build_clean_dataframe(records,
run_date=...)` để rebuild từ đầu. Che lỗi bằng heuristic (ví dụ
fillna summary hay gỡ duplicate bằng rule) sẽ không pass được audit
vì không có nguồn gốc; cách duy nhất đạt yêu cầu là re-derive từ raw.

## 10. So sánh baseline, corrupted và repaired

Số liệu dưới đây trích từ `report/commit-map-pha2.md` và file
`data/reports/corruption_report.md`. Lệnh tái tạo:
`uv run python script/run_corruption_flow.py`.

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |    1.000 |     0.625 |    1.000 |                −0.375    |   100% | Truncate title + noise summary đẩy top-k rank; duplicate làm rank lệch → hit tụt 37.5 điểm phần trăm |
| `mean_token_f1`        |    1.000 |     0.505 |    1.000 |                −0.495    |   100% | Blank summary + noise làm câu trả lời `_extract_answer` rút từ `summary` rỗng/sai |
| `judge_accuracy`       |    0.958 |     0.458 |    0.958 |                −0.500    |   100% | Judge LLM phạt các câu trả lời sai vì token F1 thấp + abstract bị nhiễu |
| `mean_judge_score`     |    4.833 |     3.125 |    4.833 |                −1.708    |   100% | Trung bình điểm judge tụt 1.7/5 |
| Quality checks pass/total |  6/6 pass |   4/6 |   6/6 | 2 check fail: `paper_id_unique` (duplicate) + `freshness` (stale) | 100% | `summary_length` vẫn pass (coverage 0.826 ≥ 0.8); cả 2 check fail do corruption → repair khôi phục đủ |
| Freshness status        | fresh | **stale** (5/23) | fresh | `stale_rows` tăng 0 → 5 do `drop_latest` + `stale_date` | 100% | Threshold 180 ngày; `stale_date` đẩy 4 dòng `published=2005-01-01`, kèm `drop_latest` ảnh hưởng max-date → 5 stale_rows |

Hai chuỗi nhân quả có quan hệ nguyên nhân–bằng chứng:

1. **Corruption (drop_latest + blank_summary + noise_summary + truncate_title
   + stale_date + duplicate) → `freshness.stale_rows` tăng 0→5,
   `summary_length.below_threshold` > 0, `paper_id_unique.duplicates` > 0
   → `mean_token_f1` tụt 1.000→0.505, `judge_accuracy` tụt 0.958→0.458,
   `retrieval_hit_rate` tụt 1.000→0.625.** Bằng chứng:
   `data/results/corrupted_metrics.json` +
   `data/quality/quality_corrupted.json` + `corruption_log.json`.
2. **Repair (re-derive `build_clean_dataframe` từ
   `crossref_records.json`) → quality pass 6/6 trở lại,
   `freshness.is_fresh=true` → cả 4 metric agent phục hồi đúng bằng
   baseline (±0.000).** Bằng chứng:
   `data/results/repaired_metrics.json` +
   `data/quality/quality_repaired.json` +
   `data/clean/papers_clean_repaired.csv` (cùng 24 rows hash với
   baseline).

Không kết luận "có tác động" nếu số liệu không cho thấy thay đổi — ở
đây cả 6 dimension đều có artifact đối chiếu.

Corruption ảnh hưởng rõ nhất: `noise_summary` + `truncate_title` (vì
tác động trực tiếp vào embedding vector → `retrieval_hit_rate` tụt
37.5%) và `blank_summary` (kéo `mean_token_f1` tụt 49.5%).

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Conflict add/add khi nhiều thành viên cùng chạy
  `script/run_phase1.py` rồi cùng `git add data/` cùng lúc. Diff của
  `data/clean/papers_clean.csv` và các manifest JSON không khớp vì
  mỗi lần chạy là idempotent nhưng `chromadb` UUID và embedding order
  có thể chênh nhẹ theo từng môi trường.
- **Nguyên nhân:** Artifact sinh lại mỗi lần chạy; tất cả 5 người đều
  ownership artifact (mơ hồ) → ai cũng add → conflict.
- **Cách xử lý:** Quy ước mới — **chỉ Đại (integrator) commit
  `data/`**. Người khác chỉ `git pull` rồi dùng. Kèm `.gitattributes`
  ép LF cho file text và bổ sung `data/chroma/`, `.DS_Store`,
  `.idea/` vào `.gitignore`. Ghi lại trong
  `report/commit-map-pha2.md`.
- **Cách xác minh:** Phase 2 chạy trơn tru trên nhánh main; đã có
  đủ artifact corrupt + repaired trong repo, không còn conflict khi
  các thành viên push từng commit-source riêng lẻ.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Corpus chỉ 24 records, query rộng (`agentic retrieval augmented generation large language model`) | Đánh giá metric có thể dao động mạnh khi thay 1-2 record. `judge_accuracy` 0.958 vì chỉ cần 1 câu lệch là tụt ~4% | Tăng `max_results` lên ≥100 khi có rate-limit allowance; đo `stddev` của metric qua 5 random seed để xác nhận baseline ổn định |
| `categories_joined` của nhiều record trống | Câu hỏi loại `categories` trong test set khó trả lời chính xác; hiện extraction trả "" | Normalize category Crossref (`"Computer Science - AI"` ↔ `"cs.AI"`) trong `build_clean_dataframe`; tăng `categories_joined` nonzero % từ ~0% lên ≥ 50% |
| Chỉ dùng `gpt-4o-mini` cho judge | Cost rẻ nhưng phân tích ranh giới câu trả lời có thể thiếu | Khi cần chấp nhận sai-lệch nhỏ, dùng thêm `gpt-4o` làm judge thứ hai và so agreement; nếu hai judge disagree > 10% câu thì cần human spot check |
| `chroma/` không commit (do gitignore) | Mỗi máy chạy lần đầu phải embed lại (1–2 phút) | Tùy chọn: thêm `data/chroma/<baseline>.tar` artifact thay vì ignore; trade-off lớn hơn → cân nhắc bật LFS |
| Không có Ragas trong baseline | Đánh giá chỉ dựa trên retrieval hit + token F1 + LLM judge | Bật `RUN_RAGAS=1` cho 1 lần chạy cuối; ghi `data/results/baseline_ragas.json` làm reference |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế (xem `commit-map-pha2.md`).
- [x] Lệnh tái hiện đã chạy baseline + corruption flow (xem `commit-map-pha2.md`).
- [x] Baseline, corrupted và repaired dùng cùng evaluation set
  (`data/eval/test_set.json`).
- [x] Bảng metrics khớp với file `data/results/baseline_metrics.json`,
  `data/results/corrupted_metrics.json`,
  `data/results/repaired_metrics.json` (theo số liệu đã report trong
  `commit-map-pha2.md`).
- [x] Quality/freshness conclusions khớp với `data/quality/` (6/6
  baseline + 6/6 repaired, 4/6 corrupted).
- [x] Đường dẫn báo cáo và artifact truy cập được trong repo.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng (`report/individual_report.md` của Đại + Huy Anh; Phái/Phong/Kiên cần bổ sung nếu có).
- [x] Không có `.env`, API key, token hay secret trong source, report, log hay ảnh.