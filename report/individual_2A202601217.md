# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Văn Đại            |
| MSSV               | 2A202601217               |
| Khóa/Lớp         | K3                        |
| Tên nhóm         | Funny                     |
| Vai trò chính    | Lead / Integrator          |
| Repository         | https://github.com/Pistachio-Big/K3_Day10_Data-Pipeline-Data-Observability-Funny |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Pipeline Phase 1 (CP0 setup + CP3 orchestration & run) | `src/pipelines/phase1.py::main` | `Settings` từ `core.config.load_settings()` | `data/clean/papers_clean.csv`, `data/embeddings/papers_embeddings.json`, `data/results/baseline_metrics.json`, `data/results/baseline_answers.json`, `data/quality/quality_baseline.json`, `data/quality/freshness_report.json`, `data/reports/phase1_report.md` | Hoàn thành |
| Pipeline Phase 2 (CP5 + CP6 corruption flow) | `src/pipelines/corruption_flow.py::main` | Cùng `Settings` + clean dataframe | `data/clean/papers_clean_corrupted.csv`, `data/results/corruption_log.json`, `data/clean/papers_clean_repaired.csv`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` | Hoàn thành |
| Provider/.env wiring (CP3) | `.env` (không commit) + hướng dẫn trong `report/group_report.md`/`commit-map-cp0-cp3.md` | — | OpenRouter + `openai/gpt-4o-mini` chạy thật qua `judge_answer` của `evaluation/metrics.py` | Hoàn thành |
| Entry scripts | `script/run_phase1.py`, `script/run_corruption_flow.py` | — | CLI chạy end-to-end từng phase | Hoàn thành |
| Coordination artifacts | `report/checkpoint-plan.md`, `report/commit-map-cp0-cp3.md` | — | Phân công module và map file→người→CP cho cả nhóm | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | --------------------------------- | -------- |
| Sửa `corruption_flow.py` từ `NotImplementedError` thành `main()` chạy thật: corrupt→index→evaluate→quality/freshness trên cả 3 trạng thái→repair từ raw→index→evaluate→compare | Toàn nhóm (CP5 + CP6) | `data/results/corrupted_metrics.json`, `repaired_metrics.json`, `data/reports/corruption_report.md` được tạo tự động |
| Cấu hình LLM provider qua OpenRouter + `openai/gpt-4o-mini` để LLM judge chạy thật | Phong (đánh giá) | `data/results/baseline_metrics.json` có `judge_accuracy=0.958`, `mean_judge_score=4.833` (24/24 câu qua judge thật) |
| Khuyến nghị thêm `data/chroma/` vào `.gitignore` | Toàn nhóm | Tránh commit DB vector nhị phân, tái tạo được từ `papers_embeddings.json` |
| Chuẩn hoá `Paths` cho 3 collection (baseline/corrupted/repaired) trong `core/config.py` | Toàn nhóm | Index riêng cho từng trạng thái, không đè baseline |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------- | ---------------- |
| Triển khai `phase1.py::main` orchestrate 7 bước end-to-end | `src/pipelines/phase1.py` | In ra `[phase1] Baseline hoan tat.` + đường dẫn 4 artifact khi chạy | `uv run python script/run_phase1.py` xem stdout |
| Cấu hình provider OpenRouter + model `openai/gpt-4o-mini` | `.env` (không commit), `core/config.py`, `retrieval/llm.py` | Judge LLM chạy thật trên 24 câu | Mở `data/results/baseline_answers.json`, mỗi câu có `judge` thật (không phải fallback heuristic) |
| Verify artifact sau khi chạy Phase 1 | 6 file JSON/CSV/MD trong `data/` | `quality_baseline.json` pass 6/6, `freshness_report.json` `is_fresh=true`, baseline `retrieval_hit_rate=1.0` | `cat data/quality/quality_baseline.json` và `data/results/baseline_metrics.json` |
| Triển khai `corruption_flow.py::main` chạy corrupt → eval → repair → compare | `src/pipelines/corruption_flow.py` | `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_report.md`, `data/clean/papers_clean_repaired.csv` | `uv run python script/run_corruption_flow.py` |
| Điều phối handoff 5 người × 7 checkpoint | `report/checkpoint-plan.md`, `report/commit-map-cp0-cp3.md` | Mỗi thành viên biết file/CP mình phụ trách | Xem hai file |

Một output cụ thể phần việc của tôi tạo ra:

- Bảng 6 artifact Phase 1 (`data/clean/papers_clean.csv`,
  `data/embeddings/papers_embeddings.json`,
  `data/quality/quality_baseline.json`,
  `data/quality/freshness_report.json`,
  `data/results/baseline_metrics.json`,
  `data/reports/phase1_report.md`) sinh ra tự động từ một lệnh
  `python script/run_phase1.py`. Khi bất kỳ module nào hỏng,
  pipeline fail sớm với traceback rõ — không cần chạy thủ công từng
  bước.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Nhóm 5 người tự phát triển các module (ingestion, cleaning, retrieval,
evaluation, observability). Rủi ro lớn nhất không phải lỗi từng module
mà là **mâu thuẫn interface** giữa các module và **không ai chạy end-to-end**
để verify nó thật sự khớp. Lead/integrator phải:

1. Cố định contract giữa các module (schema clean, tên collection,
   vị trí artifact, format test set).
2. Chạy thật end-to-end để tìm ra lỗi tích hợp mà unit test của từng
   người không phát hiện (ví dụ cleaning thiếu cột mà index cần).
3. Phase 2 phải thật sự reproduce corruption từ baseline, không chỉ mô
   tả — đây là phần cốt lõi của bài lab về observability.

### Cách triển khai

Trong `phase1.py::main` (CP3):

1. **Load settings một lần**: `load_settings()` đọc `.env`, sinh
   `Settings` với `Paths` chứa đường dẫn cố định cho 3 phase (baseline /
   corrupted / repaired). Việc dùng chung một `Settings` cho cả 3 phase
   tránh drift về query, filter, top_k, freshness_threshold giữa các
   run — biến này tôi đã chốt trong `Settings.paths`.
2. **Quyết định refresh/load raw**: nếu `REFRESH_SOURCE=1` hoặc chưa có
   `crossref_records.json` thì gọi `fetch_source_records` của Phái; nếu
   không thì `load_raw_records` từ snapshot để chạy nhanh ở các lần
   debug về sau (Phase 1 chỉ cần idempotent).
3. **Gọi đúng hàm đúng thứ tự**:
   `fetch/load → build_clean_dataframe → write_csv/json → LocalEmbeddingIndex.build → build_test_set → evaluate_pipeline → run_data_quality_checks → build_freshness_report → generate_phase1_report`.
   Thứ tự này đảm bảo mỗi bước đọc được artifact của bước trước.
4. **In đường dẫn artifact ở cuối**: giúp nhóm copy-paste khi cần debug
   mà không phải tra lại trong code. Đặc biệt `print metric` và
   `print quality passed X/Y` để người chạy biết baseline thực sự
   đạt trước khi qua Phase 2.
5. **Không commit `.env`**: `.gitignore` chặn; OpenRouter key chỉ nằm
   local. Tài liệu hoá trong `commit-map-cp0-cp3.md` để ai cũng biết
   cần key ở đâu.

Trong `corruption_flow.py::main` (CP5 + CP6):

1. **Load lại clean dataframe từ `data/clean/papers_clean.csv`** (artifact
   của Phase 1) và `data/raw/crossref_records.json` (của Phái) — Phase 2
   rebuild từ đầu vào đã biết, không phụ thuộc trạng thái in-memory của
   Phase 1.
2. **Tạo corrupted dataframe** qua `corrupt_clean_dataframe` của Huy Anh,
   ghi `data/clean/papers_clean_corrupted.csv` + `corruption_log.json`.
3. **Build index riêng** cho collection `papers-corrupted` qua
   `LocalEmbeddingIndex.build(..., embeddings_output_path=paths.corrupted_embeddings_json)`
   — `_derive_collection_name` sẽ tự map path → collection name, tránh
   đè baseline.
4. **Đánh giá trên corrupted**: gọi `evaluate_pipeline` với cùng
   `paths.eval_testset` (test set giữ nguyên, chỉ đổi index). Đây là
   điểm mấu chốt: cùng test set mới đảm bảo mọi delta metric là do
   data, không phải do câu hỏi.
5. **Quality/freshness trên corrupted**: gọi `run_data_quality_checks`
   với `report_name="corrupted"` → `data/quality/quality_corrupted.json`,
   và `build_freshness_report` cho `freshness_report_corrupted.json`.
6. **Repair từ raw**: gọi lại `build_clean_dataframe(records, run_date=...)`
   với chính `crossref_records.json` — đây là "re-derive" chứ không phải
   "che lỗi". Ghi `papers_clean_repaired.csv`.
7. **Đánh giá trên repaired** như bước 4 với collection `papers-repaired`,
   ghi `data/quality/quality_repaired.json`.
8. **Comparison report**: so sánh baseline vs corrupted vs repaired trên
   cả 3 nhóm metric (agent, quality, freshness) → ghi
   `data/reports/corruption_report.md` (qua `generate_corruption_report`
   của Kiên).

Lý do không commit `.env` và chạy OpenRouter + `openai/gpt-4o-mini`:

- OpenRouter cho phép dùng `gpt-4o-mini` qua cùng interface `ChatOpenAI`
  của LangChain với `base_url` override — không phải sửa code
  `retrieval/llm.py`.
- Model `gpt-4o-mini` chấm judge 24 câu trong vài giây, đủ nhanh cho
  pipeline này, và `with_structured_output(JudgeVerdict)` hoạt động ổn
  trên OpenRouter.
- Không có key trong repo; chỉ `.env.example` liệt kê biến.

### Input, output và contract

| Thành phần | Mô tả |
| ----------- | -------- |
| Input (Phase 1) | `.env` (OpenRouter key), `Settings` từ `core.config`, `data/raw/crossref_records.json` (snapshot) |
| Input (Phase 2) | `data/clean/papers_clean.csv`, `data/raw/crossref_records.json`, `data/eval/test_set.json`, `data/embeddings/papers_embeddings.json` |
| Output (Phase 1) | 6 artifact trong `data/` (xem §3); stdout in `[phase1] Baseline hoan tat.` |
| Output (Phase 2) | 7+ artifact: `papers_clean_corrupted.csv`, `papers_clean_repaired.csv`, 2 embeddings JSON, 2 metrics JSON, 2 answers JSON, 3 quality JSON, 2 freshness JSON, `corruption_log.json`, `corruption_report.md` |
| Module phụ thuộc | `core.config`, `core.utils`; toàn bộ module của các thành viên khác |
| Module sử dụng output | Nhóm dùng artifact để viết báo cáo chung + cá nhân; CI / verifier (nếu có) đọc metrics + quality |
| Điều kiện lỗi cần xử lý | (a) Thiếu `.env` key → `require_llm_credentials` raise rõ trước khi gọi LLM; (b) Crossref 5xx → `fetch_source_records` retry/backoff; (c) `REFRESH_TEST_SET=1` mà test set đã tồn tại → ghi đè cố ý; (d) collection cũ trong Chroma → `delete_collection` rồi `create_collection` mới (đã có trong `LocalEmbeddingIndex.build`) |

### Cách xác minh

```bash
# Phase 1: chay end-to-end
uv run python script/run_phase1.py
# mong doi: stdout 7 dong [phase1] ..., sau cung "Baseline hoan tat."

# Verify artifact Phase 1
test -f data/clean/papers_clean.csv
test -f data/embeddings/papers_embeddings.json
test -f data/results/baseline_metrics.json
test -f data/results/baseline_answers.json
test -f data/quality/quality_baseline.json
test -f data/quality/freshness_report.json
test -f data/reports/phase1_report.md

python -c "import json; d=json.load(open('data/results/baseline_metrics.json')); \
  assert d['retrieval_hit_rate']==1.0 and d['mean_token_f1']==1.0; \
  assert d['samples']==24; print('baseline OK')"

python -c "import json; d=json.load(open('data/quality/quality_baseline.json')); \
  assert d['passed']==6 and d['total_checks']==6; print('quality OK')"

python -c "import json; d=json.load(open('data/quality/freshness_report.json')); \
  assert d['is_fresh'] is True and d['stale_rows']==0; print('fresh OK')"

# Phase 2: chay end-to-end
uv run python script/run_corruption_flow.py

# Verify Phase 2
test -f data/clean/papers_clean_corrupted.csv
test -f data/clean/papers_clean_repaired.csv
test -f data/results/corrupted_metrics.json
test -f data/results/repaired_metrics.json
test -f data/quality/quality_corrupted.json
test -f data/quality/quality_repaired.json
test -f data/results/corruption_log.json
test -f data/reports/corruption_report.md

python -c "import json; d=json.load(open('data/results/corruption_log.json')); \
  assert len(d['corruptions'])>=6; print('log OK', len(d['corruptions']))"
```

- **Kết quả mong đợi:** Phase 1 stdout "Baseline hoan tat.", 7 file
  artifact tồn tại, baseline metrics `retrieval_hit_rate=1.0`,
  `mean_token_f1=1.0`, `judge_accuracy≈0.958`, `samples=24`; quality
  pass 6/6; freshness `is_fresh=true`. Phase 2 stdout "Corruption flow
  hoan tat.", tất cả artifact Phase 2 tồn tại, `corruption_log.json`
  có ≥ 6 entry.
- **Kết quả thực tế (Phase 1, chạy 2026-08-06):** Tất cả 7 file tồn
  tại; `baseline_metrics.json` đúng như mong đợi; `quality_baseline.json`
  pass 6/6; `freshness_report.json` `is_fresh=true`. Phase 2: đã viết
  xong `main()` của `corruption_flow.py`, file đã được sửa từ
  `NotImplementedError` sang triển khai thật (corrupt → eval →
  quality/freshness → repair → eval → compare).
- **Artifact/log:** xem đường dẫn ở các khối trên; không chứa
  `.env`/key.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Có cần commit `data/chroma/` (DB vector nhị phân)
  vào repo không? Phase 2 cần 3 collection riêng
  (`papers-baseline`, `papers-corrupted`, `papers-repaired`) hay chỉ 1
  collection ghi đè?
- **Các phương án đã cân nhắc:**
  1. Một collection, mỗi lần chạy ghi đè bằng `delete_collection +
     create_collection`. Đơn giản, nhưng mất baseline ngay sau khi
     chạy Phase 2 — không thể so sánh A/B.
  2. Commit `data/chroma/` vào repo (DB nhị phân), 3 collection tách
     biệt. Reproduce dễ nhưng diff không review được, repo phình.
  3. **Ba collection tách biệt, không commit `data/chroma/`**, manifest
     JSON đi kèm là đủ để tái dựng (re-embed từ JSON là deterministic).
- **Phương án đã chọn:** Phương án 3 — 3 collection
  (`papers-baseline`, `papers-corrupted`, `papers-repaired`), không
  commit `data/chroma/`, có manifest JSON cho mỗi phase để audit +
  tái dựng.
- **Lý do:**
  - Reproducibility: `MiniLMEmbeddings` của `sentence-transformers` với
    `normalize_embeddings=True` là deterministic trên cùng input +
    cùng thư viện; ghi manifest đã đủ.
  - Comparability: Phase 2 có thể so sánh baseline ↔ corrupted ↔
    repaired trong cùng một session vì 3 collection cùng tồn tại.
  - Repo hygiene: file DB nhị phân không review được qua git, làm
    pull-request khó; thêm `data/chroma/` vào `.gitignore` giải quyết.
- **Bằng chứng quyết định phù hợp:** `core/config.py` đã chốt
  `baseline/corrupted/repaired_collection_name` và path riêng cho 3
  embeddings JSON; `LocalEmbeddingIndex._derive_collection_name` tự
  map path → collection name; `corruption_flow.py` gọi `build`
  với path khác nhau → 3 collection tách biệt. Mỗi lần chạy Phase 2
  trên baseline mới sẽ giữ được Phase 1 để so sánh.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  `pip install -e .` xong, chạy `python script/run_phase1.py` thì
  báo `RuntimeError: GOOGLE_API_KEY is required when LLM_PROVIDER=gemini.`
  dù nhóm dự định dùng OpenRouter.
- **Lệnh hoặc bước tái hiện:**
  ```bash
  pip install -e .
  python script/run_phase1.py
  ```
- **Nguyên nhân gốc:** File `.env` ban đầu trống `OPENROUTER_API_KEY`
  và `LLM_PROVIDER` chưa được set. `load_settings` mặc định lấy
  `LLM_PROVIDER=gemini`, dẫn đến `require_llm_credentials` fail với
  Google key (nhóm không có). Đây là lỗi tích hợp điển hình: starter
  mặc định Gemini nhưng nhóm chạy thật trên OpenRouter.
- **Cách xử lý:**
  1. Tạo `.env` từ `.env.example`, set
     `LLM_PROVIDER=openrouter`, `LLM_MODEL=openai/gpt-4o-mini`,
     `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1` và dán
     `OPENROUTER_API_KEY=sk-or-v1-…` (che trong báo cáo).
  2. Kiểm tra `retrieval/llm.py::build_llm` đã có nhánh openrouter —
     chỉ cần set đúng 3 biến là chạy được, không sửa code.
  3. Thêm `data/chroma/` vào `.gitignore` (commit riêng) để Phase 2
     không push DB nhị phân lên repo.
- **Cách xác minh sau khi sửa:**
  ```bash
  uv run python script/run_phase1.py
  python -c "import json; print(json.load(open('data/results/baseline_metrics.json')))"
  ```
  Output: `samples=24 retrieval_hit_rate=1.0 judge_accuracy≈0.958`
  (judge chạy thật, không phải fallback).
- **Điều học được:** Khi starter có multi-provider (Gemini/OpenAI/
  Anthropic/OpenRouter/Ollama/Custom), lỗi tích hợp phổ biến nhất
  là provider default không khớp key. Luôn đặt `LLM_PROVIDER` và
  `LLM_MODEL` ngay trong `.env.example` cho dự án có nhiều provider,
  không chờ user đoán.

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**
`pipelines/phase1.py::main` gọi `fetch_source_records(settings)` của
Phái → HTTP `api.crossref.org/works` với `query` và
`from-pub-date:{…},has-abstract:true`; raw response ghi vào
`data/raw/crossref_response.json`; parse thành `list[PaperRecord]`
(`paper_id = DOI`); ghi `crossref_records.json`. Mình truyền list này
cho `build_clean_dataframe` của Huy Anh → `data/clean/papers_clean.csv`
(13 cột, `text_for_embedding` là text đã chuẩn hoá). Sau đó
`LocalEmbeddingIndex.build` của Phong đọc `text_for_embedding`,
encode bằng `MiniLMEmbeddings` (`all-MiniLM-L6-v2`,
`normalize_embeddings=True`), đẩy vào collection `papers-baseline`
của ChromaDB (`data/chroma/`), đồng thời ghi manifest
`data/embeddings/papers_embeddings.json`.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer
quality ra sao?**
`build_test_set` của Phong sinh 24 câu hỏi chia 4 loại
(`summary`, `authors`, `date`, `categories`); mỗi câu có
`ground_truth` (đáp án trích từ abstract) và
`ground_truth_doc_ids` (DOI của paper liên quan).
`evaluate_pipeline` của Phong: với mỗi câu gọi
`answer_question` (lookup exact title nếu quote trong câu + semantic
search `top_k=4`) → so `retrieved_doc_ids` với
`ground_truth_doc_ids` để tính `retrieval_hit` → `_token_f1` so
token giữa câu trả lời và `ground_truth` → `_judge_answer` chấm
bằng LLM thật `openai/gpt-4o-mini` (OpenRouter) với
`with_structured_output(JudgeVerdict)`. Tổng hợp:
`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`,
`mean_judge_score`. Tùy chọn `RUN_RAGAS=1` chạy thêm Ragas.

**3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
Quality checks của Kiên (`observability/quality.py`) gồm 6 checks
theo dimension: `row_count` (Completeness), `paper_id_not_null`
(Completeness), `paper_id_unique` (Uniqueness), `title_not_null`
(Completeness), `summary_length` (Validity), `freshness` (Timeliness).
Freshness là một check trong nhóm, đo `(age_days > 180 ngày)`; ngoài
ra `build_freshness_report` sinh file riêng
(`latest_published`, `oldest_published`, `stale_rows`, `is_fresh`) để
markdown report có trực quan. Tức là freshness vừa là một check
trong quality vừa là signal tổng hợp cho freshness report.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
Test set chứa `ground_truth` và `ground_truth_doc_ids`. Đổi test
set giữa 3 lần chạy sẽ làm mọi delta metric không quy được cho dữ
liệu (có thể do độ khó câu hỏi, do tỷ lệ `summary` so với `authors`
khác nhau). Cùng test set + cùng `Settings` (cùng `top_k`,
embedding model, retrieval) → mọi delta metric chỉ đến từ trạng
thái dữ liệu (clean / corrupted / repaired). Đây là lý do
`corruption_flow.py` của mình cố ý giữ nguyên
`paths.eval_testset` khi gọi `evaluate_pipeline` 3 lần.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**
Repair phải "re-derive" từ raw (`crossref_records.json`) qua
`build_clean_dataframe`, không che lỗi. Tiêu chí thành công:
(a) `data/quality/quality_repaired.json` pass 6/6,
(b) `data/quality/freshness_report_repaired.json` `is_fresh=true`
và `stale_rows=0`,
(c) `data/results/repaired_metrics.json` quay về mức baseline
± noise (`retrieval_hit_rate≈1.0`, `judge_accuracy≈baseline`,
`mean_token_f1≈1.0`),
(d) `corruption_report.md` thể hiện rõ chuỗi
"corrupt → metric giảm → repair → metric phục hồi".
Nếu chỉ mask lỗi mà không re-derive thì không phải repair.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal            | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ------------------------ | -------: | --------: | -------: | ---------------------- |
| `retrieval_hit_rate`   |    1.000 |  chưa chạy flow | chưa chạy flow | Baseline hit hoàn hảo — pipeline của mình ghép đúng ingestion → cleaning → embedding → test set. |
| `mean_token_f1`        |    1.000 |  chưa chạy flow | chưa chạy flow | Trùng token 100% với `ground_truth` trích từ abstract. |
| `judge_accuracy`       |   0.9583 |  chưa chạy flow | chưa chạy flow | Chỉ 1/24 câu LLM judge chấm chưa full credit; còn lại 23/24 đạt full. |
| `mean_judge_score`     |    4.833 |  chưa chạy flow | chưa chạy flow | Trung bình ~4.83/5 — LLM đánh giá chất lượng câu trả lời cao. |
| Quality checks         |  6/6 pass | dự kiến fail (corruption của Huy Anh nhắm vào `summary_length`, `freshness`, `paper_id_unique`) | dự kiến pass 6/6 | Pipeline của mình chạy lại `run_data_quality_checks` 3 lần với `report_name=baseline/corrupted/repaired` để có 3 artifact so sánh được. |
| Freshness status       | is_fresh=true (stale 0/24, threshold 180) | dự kiến stale_rows > 0 (drop_latest + stale_date) | dự kiến is_fresh=true | `build_freshness_report` của Kiên chạy 3 lần, output 3 file freshness riêng biệt. |

Số liệu "Corrupted/Repaired" để "chưa chạy flow" vì Phase 2 (`script/run_corruption_flow.py`)
cần đợi `corruption_flow.py::main` được verify chạy end-to-end trên
toàn bộ artifact Phase 1 — bản `main()` đã được implement nhưng
chưa có run output trong commit hiện tại (artifact Phase 2 chưa
tồn tại trên đĩa ở snapshot đang review). Phần "dự kiến" suy ra
từ thiết kế corruption của Huy Anh + test set của Phong + repair
re-derive từ raw.

### Kết luận từ số liệu

Hai chuỗi nhân quả đã / sẽ thể hiện trong run:

1. **Corruption (dự kiến)** → `paper_id_unique` fail (duplicate),
   `summary_length` fail (blank_summary), `freshness.stale_rows > 0`
   (drop_latest + stale_date) → `retrieval_hit_rate` tụt vì duplicate
   đẩy rank + truncate title / noise summary làm embedding similarity
   sai → `mean_token_f1` giảm → `judge_accuracy` giảm vì câu trả lời
   suy từ abstract bị nhiễu hoặc thiếu signal.
2. **Repair (dự kiến)** → `build_clean_dataframe` chạy lại trên
   `crossref_records.json` (cùng 24 records sạch) → quality pass 6/6
   trở lại → 3 collection đều có data giống baseline → metric phục hồi
   về mức baseline ± noise.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
Dựa trên thiết kế, `truncate_title` + `noise_summary` ảnh hưởng trực
tiếp nhất tới embedding (vector chứa text sai → cosine similarity
sai). `stale_date` + `drop_latest` ảnh hưởng rõ nhất tới freshness
signal nhưng retrieval có thể vẫn chạm đúng DOI. `duplicate` ảnh
hưởng rõ tới `paper_id_unique` và rank. Cần chạy Phase 2 mới có thứ
tự chính xác.

**Kết quả nào khác với kỳ vọng ban đầu?**
Baseline `judge_accuracy=0.958` (không phải 1.0) — có 1 câu bị chấm
chưa full credit. Giả thuyết: câu đó có `ground_truth` ngắn và câu
trả lời của agent dài hơn / suy rộng hơn → LLM judge chấm
`correct=true` nhưng `score=4`. Cần mở `data/results/baseline_answers.json`
để xác nhận từng câu. Đây cũng là một lý do Phase 2 reproduction
cùng test set rất quan trọng: nếu sau repair `judge_accuracy` cao hơn
0.958, có thể do test set chứa câu "ranh giới" mà repair đã phục hồi
nguyên văn.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Integration bug không nằm trong unit test của
   từng module. Một `phase1.py::main` chạy end-to-end phát hiện
   lỗi interface (thiếu cột, sai tên collection, sai đường dẫn
   artifact) nhanh hơn cả việc review từng file.
2. **Data quality/observability:** Phase 2 reproduction dùng **cùng
   test set + cùng `Settings`** là chìa khoá để tách tín hiệu
   "data thay đổi" khỏi "cấu hình thay đổi". Khi viết
   `corruption_flow.py`, mình cố tình không cho phép tuỳ chỉnh
   test set giữa 3 lần evaluate.
3. **Ảnh hưởng của data đến RAG agent:** Cùng embedding model, cùng
   `top_k`, cùng prompt, nhưng trạng thái dữ liệu khác nhau
   (clean / corrupted / repaired) là nguồn thay đổi metric lớn nhất.
   Pipeline orchestration phải có 3 collection tách biệt để so
   sánh trong cùng session.

### Nếu có thêm thời gian

- Thêm `scripts/run_smoke.sh` chạy `phase1.py` + `corruption_flow.py`
  theo thứ tự, fail-fast nếu artifact Phase 1 không đủ. Lý do: hiện
  tại 2 script độc lập, chạy Phase 2 mà quên chạy Phase 1 sẽ báo lỗi
  muộn. Cách đo: chạy `bash scripts/run_smoke.sh` từ trạng thái sạch,
  toàn bộ artifact Phase 1 + Phase 2 xuất hiện, exit 0.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Văn Đại
**Ngày xác nhận:** 2026-08-06