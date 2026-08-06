# Phân công theo Checkpoint — Day 10

Nhóm 5: **Đại** (Lead/Integrator), **Phái** (Ingestion), **Huy Anh** (Cleaning & Corruption), **Phong** (RAG & Evaluation), **Kiên** (Observability & Reporting).

Timeline gốc 4 giờ, 7 checkpoint (CP0–CP6). Nghỉ 15' ở CP4.

---

## VỊ TRÍ HIỆN TẠI: cửa CP3 (chưa qua gate)

Code Pha 1 (CP0→CP3) đã viết xong và compile OK, **nhưng chưa chạy `run_phase1.py`** nên chưa có artifact trong `data/`. Pass-criteria các CP đều cần artifact tồn tại ⇒ **chưa clear CP0–CP3**.

| CP | Code | Artifact | Gate |
|----|------|----------|------|
| CP0 Ingestion | ✅ | ❌ | ❌ |
| CP1 Cleaning+Quality | ✅ | ❌ | ❌ |
| CP2 Testset+Index | ✅ | ❌ | ❌ |
| CP3 Baseline e2e | ✅ | ❌ | ❌ |
| CP5 Corruption | ❌ TODO | ❌ | ❌ |
| CP6 Repair+Compare | ❌ TODO | ❌ | ❌ |

**Hành động kế tiếp (bắt buộc):** Đại cài `.env` (Gemini + `GOOGLE_API_KEY`) → `uv sync` → `python script/run_phase1.py`. Chạy xong verify artifact ⇒ CP0–CP3 pass đồng loạt, rồi mới sang CP5.

---

## CP0 · 00:00–00:30 · Khởi động, contract & ingestion raw
**Pass:** raw response + raw records JSON tồn tại; `PaperRecord` có `paper_id` ổn định (= DOI).
**Trạng thái: code xong, chờ chạy để sinh `data/raw/`.**

| Người | Việc |
|-------|------|
| Đại | Chốt ownership/branch/definition-of-done; kiểm tra Python 3.11–3.13, `uv sync`, `.env` provider; vẽ sơ đồ handoff raw→clean→index→eval→report. |
| Phái | ✅ Đã implement `parse_crossref_payload` + `fetch_source_records` (retry 429/5xx, lưu raw trước parse) + `load_raw_records`. Việc còn: chạy fetch thật để tạo `data/raw/`. |
| Huy Anh | Chốt clean schema (rule null/date/duplicate); chỉ ra field tạo `text_for_embedding` + `age_days`. |
| Phong | Đọc `LocalEmbeddingIndex`/`embeddings`/`agent` để nắm metadata tối thiểu; chuẩn bị smoke query. |
| Kiên | Liệt kê artifact bắt buộc; định nghĩa signals (row count, null, duplicate, `age_days`). |

## CP1 · 00:30–01:05 · Cleaning, data model & quality gates
**Pass:** clean CSV/JSON đọc được; `paper_id` unique; có `text_for_embedding` + `age_days`; count record bị loại truy vết được.
**Trạng thái: code xong, chờ chạy để sinh `data/clean/`.**

| Người | Việc |
|-------|------|
| Đại | Review raw count → clean count; ghi bất thường thành blocker; chỉ cho gọi index/test set sau khi schema ổn định. |
| Phái | Đối chiếu raw snapshot với `PaperRecord`; đảm bảo raw đủ field để cleaning không phải đoán; bàn giao raw path. |
| Huy Anh | ✅ Đã implement `build_clean_dataframe` (normalize, parse date, `age_days`, dedupe theo `paper_id`, log count filter). Việc còn: xác minh trên dữ liệu thật sau khi Phái fetch. |
| Phong | Đọc vài `text_for_embedding` thật (đủ title/summary, không rỗng); xác nhận df có đủ cột index cần. |
| Kiên | ✅ Đã implement `run_data_quality_checks` (row count, `paper_id` null/unique, title, summary length, freshness). Việc còn: chạy để ghi `quality_baseline.json` đầu tiên. |

## CP2 · 01:05–01:35 · Test set, RAG index & agent smoke test
**Pass:** `test_set.json`, embedding manifest, collection `papers-baseline` tồn tại; semantic search + exact lookup + agent trả kết quả có nguồn.
**Trạng thái: code xong, chờ build index + smoke test.**

| Người | Việc |
|-------|------|
| Đại | Khóa clean schema; điều phối handoff clean→test set/index; đảm bảo path/collection baseline đặt riêng. |
| Phái | Trace một `paper_id` xuyên raw→clean→index metadata; không refresh source giữa chừng. |
| Huy Anh | Xác minh không còn `text_for_embedding` rỗng / `paper_id` trùng; review row được chọn vào test set. |
| Phong | ✅ Đã implement `build_test_set` (summary/authors/date/categories, dùng đúng cụm khóa của `qa._extract_answer`). Việc còn: build MiniLM+Chroma, smoke test `search`/`lookup`/agent. |
| Kiên | Kiểm tra embedding manifest, collection name, count documents auditable; ghi baseline signals để so sánh sau. |

## CP3 · 01:35–02:00 · Baseline end-to-end & báo cáo  ← ĐANG Ở ĐÂY
**Pass:** `baseline_metrics.json`, `baseline_answers.json`, quality/freshness, `phase1_report.md` tồn tại; giải thích được ≥1 hit/miss bằng artifact.
**Trạng thái: code xong, CHƯA chạy — đây là việc kế tiếp.**

| Người | Việc |
|-------|------|
| Đại | ✅ Đã implement `phase1.py::main` (raw→clean→index→testset→evaluate→quality/freshness→report). **Việc còn: chạy `python script/run_phase1.py` end-to-end, ghi traceback nếu fail, verify path/artifact.** |
| Phái | Xác minh raw response/records + lineage sample vẫn đọc được; đảm bảo phase1 không fetch lại ngoài ý muốn. |
| Huy Anh | Kiểm tra clean schema/`age_days`/`text_for_embedding` trong artifact đã ghi; quality check phản ánh dữ liệu thật (không hard-code pass). |
| Phong | Xác nhận `papers-baseline` + manifest khớp clean data; demo 1 semantic search + 1 exact lookup; đọc 1 hit/miss trong `baseline_answers.json`, giải thích `retrieval_hit_rate`/`token_f1`/judge. |
| Kiên | ✅ Đã implement `build_freshness_report` + `generate_phase1_report`. Việc còn: đối chiếu report với JSON/CSV thật; ghi baseline signals làm mốc. |

## CP4 · 02:00–02:15 · Nghỉ 15 phút
Mọi người nghỉ. Trước khi nghỉ: Đại ghi baseline checklist + blocker còn lại. Sau nghỉ quay lại với corruption scenario đã định (raw source, signal kỳ vọng, cách repair).

## CP5 · 02:15–03:15 · Corruption có kiểm soát & đo impact
**Pass:** corruption log + corrupted clean/index/answers/metrics/quality + report đủ; baseline KHÔNG bị ghi đè.
**Trạng thái: CHƯA làm (Pha 2).**

| Người | Việc |
|-------|------|
| Đại | Implement `corruption_flow.py::main` (corrupt→rebuild→evaluate→quality/freshness→repair→compare); path/collection riêng; dừng để sửa data contract thay vì vá JSON. |
| Phái | Xác nhận raw source nguyên vẹn trước khi corrupt; đảm bảo flow không fetch source mới (giữ comparison công bằng). |
| Huy Anh | **Implement `corrupt_clean_dataframe`** (drop latest, blank summary, noise, truncate title, stale date, duplicate) + ghi `corruption_log.json`; xác nhận corrupted khác baseline đúng như log. |
| Phong | Build `papers-corrupted` riêng; evaluate corrupted trên **cùng test set**; so answer/metric với baseline, tìm 1 case xấu đi có evidence; kiểm evaluator không silently fallback thành success giả. |
| Kiên | Run quality/freshness cho corrupted (lưu report riêng); nối corruption log ↔ quality signal ↔ metric change; ghi signal nào không đổi để tránh kết luận quá mức. |

## CP6 · 03:15–04:00 · Repair từ raw, comparison, review & demo
**Pass:** repaired artifacts + comparison report có baseline–corrupted–repaired/delta; repo không secret; demo dùng artifact thật.
**Trạng thái: CHƯA làm (Pha 2).**

| Người | Việc |
|-------|------|
| Đại | Điều phối repair/comparison; checklist cuối (artifact đủ, report match output, no secret/no hard-code path); chỉ công bố recovery khi số liệu chứng minh. |
| Phái | Reload raw records đúng snapshot; chứng minh record corrupt/drop đã phục hồi bằng lineage; hỗ trợ kiểm API key không lọt Git. |
| Huy Anh | Re-run cleaning từ raw tạo repaired dataset (không copy sửa tay); kiểm repaired schema/row count/quality; demo khác biệt clean/corrupted/repaired. |
| Phong | Build `papers-repaired`; evaluate repaired trên cùng test set; tính delta 3 trạng thái; chuẩn bị 1 hit/miss tiêu biểu để demo trung thực. |
| Kiên | **Implement `generate_corruption_report`** từ metrics/quality/freshness thật; nêu recovery chưa hoàn toàn nếu signal/metric còn xấu; demo bảng comparison + giới hạn kết luận. |

---

## Quy tắc xuyên suốt
1. Chỉ chạy corruption sau khi baseline đủ artifact.
2. Giữ nguyên test set/ground truth/evaluator/`top_k` khi so sánh 3 trạng thái.
3. Path + collection riêng cho baseline/corrupted/repaired; không ghi đè baseline.
4. Repair = chạy lại từ raw, không sửa tay answers/metrics.
5. Report trỏ artifact thật; không commit `.env`/API key.
