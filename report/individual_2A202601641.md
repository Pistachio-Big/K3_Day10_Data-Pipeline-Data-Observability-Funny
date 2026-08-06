# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Huy Anh            |
| MSSV               | 2A202601641               |
| Khóa/Lớp         | K3                        |
| Tên nhóm         | Funny                     |
| Vai trò chính    | Data Cleaning & Corruption |
| Repository         | https://github.com/Pistachio-Big/K3_Day10_Data-Pipeline-Data-Observability-Funny |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Cleaning (Pha 1, CP1) | `src/ingestion/cleaning.py::build_clean_dataframe` | `list[PaperRecord]` từ `crossref.py` + `run_date` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` (24 rows) | Hoàn thành |
| Corruption (Pha 2, CP5) | `src/ingestion/corruption.py::corrupt_clean_dataframe` | Clean dataframe `data/clean/papers_clean.csv` | Dataframe bị hỏng + `data/results/corruption_log.json` | Hoàn thành |

Contract tôi chốt với nhóm: dataframe clean phải có đủ các cột
`paper_id, title, summary, authors_joined, categories_joined, primary_category,
published, updated, abs_url, pdf_url, summary_chars, age_days, text_for_embedding`
để `retrieval/index.py` (của Phong), `evaluation/metrics.py` (của Phong),
`observability/quality.py` (của Kiên) và `pipelines/phase1.py` (của Đại) gọi
đồng nhất.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | --------------------------------- | -------- |
| Sửa `compact_join` để bỏ phần tử rỗng trong danh sách authors/categories | Toàn nhóm (qua `core/utils.py`) | Authors/categories join đúng không chèn `", "` khi giá trị trống |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------- | ---------------- |
| Clean Crossref records theo schema chuẩn | `src/ingestion/cleaning.py` | `data/clean/papers_clean.csv` (24 rows, 0 drop) | `python -c "import pandas as pd; print(pd.read_csv('data/clean/papers_clean.csv').shape)"` → `(24, 13)` |
| Log count filter trong cleaning | `src/ingestion/cleaning.py::build_clean_dataframe` | Stdout: `[cleaning] input=24 dropped_missing_title=0 dropped_no_date=0 dropped_duplicates=0 clean_rows=24` | In ra khi chạy `python script/run_phase1.py` |
| Sinh 6 loại corruption có log | `src/ingestion/corruption.py::corrupt_clean_dataframe` | `data/results/corruption_log.json` (7 entries: 6 corruption + header) | Đọc file JSON, đếm `len(log["corruptions"]) == 7` (drop_latest, blank_summary, noise_summary, truncate_title, stale_date, duplicate + final_rows) |

Một output cụ thể phần việc của tôi tạo ra:

- `data/clean/papers_clean.csv` (96 KB) với 24 dòng, schema 13 cột,
  `text_for_embedding` đã được chuẩn hóa thành
  `"<title>. <summary> Authors: <...>. Categories: <...>."` và
  `age_days` tính từ `run_date - published`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Crossref trả về record dạng dict với abstract chứa JATS/HTML (`<jats:p>...`),
title có thể có whitespace dư, author là list object có `given`/`family`,
date ở `date-parts: [[2026, 8, 1]]`, và thiếu DOI hoặc thiếu title vẫn có thể
lọt vào. Nếu đưa thẳng vào embedding và evaluation sẽ có:

- text bị nhiễu tag HTML → embedding similarity kém, retrieval hit giảm.
- author rỗng/None nối bằng `", "` → token thừa trong context.
- date không parse được → freshness không tính được.
- DOI trùng (Crossref trả trùng ở một số query) → duplicate gây sai hit-rate.

### Cách triển khai

Trong `build_clean_dataframe` (CP1):

1. **Normalize text**: gọi `core.utils.normalize_whitespace` để gộp mọi
   khoảng trắng (kể cả `\n`, `\t`) về một space và trim; áp dụng trên
   `title` và `summary`. JATS đã được `_strip_jats` ở ingestion nên cleaning
   chỉ nhận text thường.
2. **Filter completeness**: bỏ record thiếu `paper_id` hoặc `title` (đếm
   `dropped_missing`); bỏ record không parse được `published` (đếm
   `dropped_no_date`) vì freshness cần date chuẩn ISO.
3. **Parse date**: `_parse_iso_date` lấy 10 ký tự đầu của chuỗi ISO rồi
   `date.fromisoformat`. Nếu lỗi thì coi như missing → drop, không âm thầm
   để trống để freshness check về sau đếm được đúng `stale_rows`.
4. **Tính freshness**: `age_days = (run_date.date() - published_date).days`
   lưu cùng dataframe. Đây là cột cố định mà `observability/quality.py`
   đọc trực tiếp (không cần parse lại).
5. **Build `text_for_embedding`**: dùng template cố định
   `"<title>. <summary> Authors: <authors_joined>. Categories: <categories_joined>."`.
   Phần `Authors:` và `Categories:` luôn có mặt để LLM judge dễ đối chiếu
   (đề phòng author list rỗng vẫn giữ token mốc). `compact_join` bỏ chuỗi
   falsy, tránh `", "` thừa.
6. **Dedupe**: `drop_duplicates(subset="paper_id", keep="first")` sau khi đã
   chuẩn hóa. Thêm filter `text_for_embedding.str.len() > 0` để bỏ những
   row mà title/summary cùng rỗng sau bước 1.
7. **Sắp xếp**: `sort_values("published", ascending=False)` để các chunk
   sau luôn thấy tài liệu mới nhất trước — thuận tiện cho cả index build
   lẫn debug bằng mắt.
8. **Log count filter**: in `[cleaning] input=… dropped_missing_title=…
   dropped_no_date=… dropped_duplicates=… clean_rows=…` ra stdout để log
   pipeline có số đếm cụ thể, dễ debug khi clean rỗng bất thường.

Trong `corrupt_clean_dataframe` (CP5):

1. Nhận vào clean dataframe đã sort theo `published desc`.
2. Tạo 6 mutation cố ý, mỗi mutation push một entry vào `log["corruptions"]`
   gồm `type`, `count`, `paper_ids` để truy vết được chính xác record bị hỏng.
3. Sau cùng, **rebuild `text_for_embedding`** từ các cột đã hỏng
   (`title`, `summary`, `authors_joined`, `categories_joined`) để các bước
   sau (embed, evaluate, quality check) đều đọc đúng dữ liệu đã bị mutation —
   tránh tình trạng corruption trên cột thô nhưng cột embed vẫn sạch.
4. Ghi `corruption_log.json` qua `core.utils.write_json` (atomic, indent 2,
   UTF-8) và in `[corruption] original=… -> final=…; log=…`.

6 loại corruption sinh ra (mapping tới quality/freshness signal):

| # | type             | Cách tạo                                  | Signal kỳ vọng bật  |
|---|------------------|--------------------------------------------|----------------------|
| 1 | `drop_latest`   | Xóa 3 dòng `published` mới nhất           | `freshness.stale_rows` > 0 |
| 2 | `blank_summary` | Set `summary = ""` cho ~15% dòng (seed 42) | `summary_length.below_threshold` > 0 |
| 3 | `noise_summary` | Append " zzxq!!! ??? lorem noise 00xx" vào ~10% summary (seed 7) | `retrieval_hit_rate`, `mean_token_f1` giảm |
| 4 | `truncate_title`| Cắt `title` còn 8 ký tự cho ~10% dòng (seed 11) | `retrieval_hit_rate`, `mean_judge_score` giảm |
| 5 | `stale_date`    | Gán `published = "2005-01-01"`, `age_days = 9999` cho ~20% dòng (seed 3) | `freshness.stale_rows` tăng mạnh |
| 6 | `duplicate`     | Nhân đôi 2 dòng đầu của dataframe | `paper_id_unique.duplicates` > 0 |

### Input, output và contract

| Thành phần | Mô tả |
| ----------- | -------- |
| Input (cleaning) | `list[PaperRecord]` (dataclass từ `ingestion.crossref`) + `run_date: datetime` (UTC) |
| Input (corruption) | `pd.DataFrame` đã qua `build_clean_dataframe` + `output_log_path: Path` |
| Output (cleaning) | `pd.DataFrame` 13 cột nêu trên + log count filter qua `print` |
| Output (corruption) | `pd.DataFrame` đã qua 6 mutation (rows thay đổi tùy tỷ lệ) + `corruption_log.json` |
| Module phụ thuộc | `core/utils.py` (`normalize_whitespace`, `compact_join`, `write_json`); `ingestion/crossref.py` (`PaperRecord`) |
| Module sử dụng output | `retrieval/index.py` đọc `text_for_embedding`; `evaluation/metrics.py` truy vấn theo `paper_id`; `observability/quality.py` đọc `summary`, `age_days`; `pipelines/phase1.py` orchestrate; `pipelines/corruption_flow.py` (CP6) sẽ gọi corruption → re-index → re-evaluate → repair |
| Điều kiện lỗi cần xử lý | (a) Mọi `PaperRecord` đều thiếu `title`/`paper_id` → raise `ValueError("Cleaning tao ra dataframe rong")`; (b) `published` không phải ISO → drop, không âm thầm; (c) `output_log_path` mà parent chưa tồn tại → `write_json` tự `mkdir -p` |

### Cách xác minh

```bash
# 1. Chạy baseline để tái tạo clean dataframe
uv run python script/run_phase1.py

# 2. Kiểm tra shape và log count filter
python - <<'EOF'
import pandas as pd
df = pd.read_csv("data/clean/papers_clean.csv")
assert df.shape == (24, 13)
assert df["text_for_embedding"].str.len().gt(0).all()
assert df["paper_id"].is_unique
assert df["age_days"].ge(0).all()
print("clean OK:", df.shape)
EOF

# 3. Chạy corruption để sinh log
python - <<'EOF'
from src.ingestion.cleaning import build_clean_dataframe
from src.ingestion.crossref import load_raw_records
from datetime import datetime, timezone
from pathlib import Path
from src.ingestion.corruption import corrupt_clean_dataframe

records = load_raw_records(Path("data/raw/crossref_records.json"))
df = build_clean_dataframe(records, run_date=datetime.now(timezone.utc))
df_bad = corrupt_clean_dataframe(df, Path("data/results/corruption_log.json"))
print("corrupted shape:", df_bad.shape)
EOF
```

- **Kết quả mong đợi:** clean shape `(24, 13)` không drop; log count
  `dropped_missing_title=0 dropped_no_date=0 dropped_duplicates=0 clean_rows=24`.
  Corruption shape `(21, 13)` (24 - 3 dropped + 2 duplicated) và
  `corruption_log.json` có 7 entry (6 corruption + final_rows).
- **Kết quả thực tế:** (từ lần chạy baseline ngày 2026-08-06)
  clean shape đúng `(24, 13)`; cờ `clean` của Phase 1 pass 6/6.
  (số liệu corrupted phụ thuộc tỷ lệ ngẫu nhiên; seed cố định nên tái lập
  được.)
- **Artifact/log:** `data/clean/papers_clean.csv`,
  `data/clean/papers_clean.json`, `data/results/corruption_log.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** `text_for_embedding` có nên chỉ gồm `title + summary`, hay
  thêm `Authors:` và `Categories:`?
- **Các phương án đã cân nhắc:**
  1. Chỉ nối `title + summary` (gọn, retrieval ít nhiễu).
  2. Ghép đầy đủ `title + summary + Authors + Categories` (giàu thông tin,
     giúp LLM judge bóc tách đúng cụm khi câu hỏi hỏi author/date/category).
  3. Tách thành nhiều trường cho multi-field embedding.
- **Phương án đã chọn:** Phương án 2 — template cố định
  `"<title>. <summary> Authors: <authors_joined>. Categories: <categories_joined>."`.
- **Lý do:** Test set của Phong có 4 loại câu hỏi (`summary`, `authors`,
  `date`, `categories`). Nếu embedding không chứa author/category, retrieval
  cho câu hỏi author sẽ kém đo. Giữ `Authors:` / `Categories:` làm mốc cố
  định giúp LLM dễ parse ngay cả khi list rỗng, đồng thời `compact_join`
  vẫn đảm bảo không chèn `", "` thừa. Phương án 3 phức tạp vượt scope
  cleaning, đẩy sang embedding.
- **Bằng chứng quyết định phù hợp:** `data/results/baseline_metrics.json`
  baseline đạt `retrieval_hit_rate=1.0`, `mean_token_f1=1.0`,
  `judge_accuracy=0.958` trên cùng template này. Nếu phương án 1, các câu
  hỏi author/category sẽ suy giảm.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** "cleaning tao ra dataframe rong" — code cũ
  raise ngay khi df rỗng; đồng thời một số run Phase 1 in log
  `dropped_no_date` lớn vì date trong raw lẫn lộn `2026` và `2025`.
- **Lệnh hoặc bước tái hiện:**

  ```bash
  uv run python script/run_phase1.py | grep "dropped_"
  ```

- **Nguyên nhân gốc:** Hai vấn đề tách biệt:
  1. Chuỗi `published` ở một số record Crossref có giờ phút đi kèm
     (`2026-08-01T00:00:00Z`), `date.fromisoformat` của Python 3.11+ chấp
     nhận nhưng bản cũ raise. Code dùng `value[:10]` để cắt trước khi
     parse — đây là phòng hờ đúng.
  2. Định nghĩa drop: cũ hơn drop cả record có `summary` rỗng → số row
     sụt giảm vì một số bản ghi có `abstract` chỉ chứa JATS toàn tag
     rỗng, sau `_strip_jats` trả về chuỗi rỗng.
- **Cách xử lý:**
  1. Tách bạch rule: cleaning chỉ drop khi thiếu `paper_id`/`title` hoặc
     không parse được date. `summary` rỗng **không drop** ở cleaning — để
     `summary_length` (validity) của Kiên làm nhiệm vụ đếm.
  2. Dùng `value[:10]` trước khi `date.fromisoformat` để chịu được cả hai
     dạng ISO có `T…Z` và không.
  3. Ném `ValueError` chỉ khi toàn bộ dataframe rỗng (input không dùng
     được), giữ log count filter in ra stdout để vẫn quan sát được
     từng record bị drop riêng.
- **Cách xác minh sau khi sửa:** Phase 1 chạy lại, `cleaning` stdout in
  `input=24 dropped_missing_title=0 dropped_no_date=0 dropped_duplicates=0
  clean_rows=24`; `data/clean/papers_clean.csv` có đúng 24 rows.
- **Điều học được:** Phân vai giữa cleaning và quality checks: cleaning
  loại "không dùng được" (thiếu khóa, không parse được), để observability
  loại "không đạt chuẩn" (summary ngắn, trùng, stale) — tránh dữ liệu bị
  xóa trước khi vào báo cáo, các check mất ý nghĩa.

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**
Crossref REST (`works`) → `fetch_source_records` (retry 429/5xx, lưu raw
`data/raw/crossref_response.json`) → `parse_crossref_payload` ra
`list[PaperRecord]` với `paper_id = DOI` (ghi `crossref_records.json`).
Mình nhận list này ở `build_clean_dataframe`, normalize và dedupe → ghi
`data/clean/papers_clean.csv|json`. `LocalEmbeddingIndex.build`
(Phong) embed từ cột `text_for_embedding` của mình, đưa vào collection
`papers-baseline` của ChromaDB.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer
quality ra sao?**
`build_test_set` (Phong) tạo 24 câu hỏi chia 4 loại. Mỗi câu chứa
`expected_paper_id` (DOI) làm ground-truth document ID. `evaluate_pipeline`
search top-k bằng embedding, lấy `paper_id` của top hit và so với
`expected_paper_id` để tính `retrieval_hit_rate`. `mean_token_f1` so token
giữa câu trả lời của agent và đáp án trích từ abstract. `judge_*` chấm
bằng LLM thật (`openai/gpt-4o-mini` qua OpenRouter).

**3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
Quality checks (Kiên) gồm `row_count`, `paper_id_not_null`,
`paper_id_unique`, `title_not_null`, `summary_length`, `freshness` —
mỗi check phản ánh một dimension (Completeness, Uniqueness, Validity,
Timeliness). Freshness là một check trong nhóm đó, đo `age_days > threshold`
trên cùng dataframe. Ngoài ra còn `build_freshness_report` riêng để ra
file `data/quality/freshness_report.json` và đưa lên report Markdown.
Tức là freshness vừa là một check vừa là một signal tổng.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
Test set chứa ground-truth `expected_paper_id`. Nếu đổi test set giữa ba
lần chạy, mọi khác biệt metric sẽ không thể quy cho data — có thể do độ
khó câu hỏi. Cùng test set + cùng index config (collection khác nhau)
đảm bảo mọi delta `retrieval_hit_rate`, `mean_token_f1`, `judge_*` chỉ
đến từ trạng thái dữ liệu (clean / corrupted / repaired).

**5. Repair được xem là thành công dựa trên artifact và metric nào?**
Repair dựa trên việc tái dựng clean dataframe từ
`data/raw/crossref_records.json` (Phái) qua lại đúng pipeline
`build_clean_dataframe`, kết hợp downstream chạy lại quality/freshness
và `evaluate_pipeline`. Tiêu chí thành công: (a)
`data/quality/quality_baseline.json` (sau khi đổi tên cho repaired) lại
pass 6/6, (b) `data/quality/freshness_report.json` `is_fresh=true` và
`stale_rows=0`, (c) các metric agent khôi phục về mức baseline ± noise.
Nếu chỉ che lỗi trên dataframe mà không re-derive từ raw thì không
được coi là repair — đó là masking.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal            | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ------------------------ | -------: | --------: | -------: | ---------------------- |
| `retrieval_hit_rate`   |    1.000 |  chưa chạy | chưa chạy | Baseline hit hoàn hảo — text_for_embedding từ cleaning của mình đủ signal. |
| `mean_token_f1`        |    1.000 |  chưa chạy | chưa chạy | Đáp án trùng token 100% với đáp án trích từ abstract. |
| `judge_accuracy`       |    0.958 |  chưa chạy | chưa chạy | Chỉ 1/24 câu LLM judge chấm chưa full credit. |
| `mean_judge_score`     |    4.833 |  chưa chạy | chưa chạy | Trung bình ~4.83/5 — LLM đánh giá chất lượng cao. |
| Quality checks         |   6/6 pass | dự kiến fail (`summary_length`, `freshness`, `paper_id_unique`) | dự kiến pass 6/6 | Corruption của mình chủ động nhắm vào 3 dimension trên. |
| Freshness status       | is_fresh=true (stale 0/24, threshold 180) | dự kiến stale tăng (drop_latest + stale_date) | dự kiến is_fresh=true | Phase 2 chưa chạy flow, nhưng tính đúng đã được build-in trong `stale_date` và `drop_latest`. |

Số liệu "Corrupted/Repaired" chưa có vì Phase 2 (CP6 — corruption flow của
Đại) chưa orchestrate chạy end-to-end. Phần "dự kiến" suy ra từ cơ chế
các corruption trong `corrupt_clean_dataframe`: `drop_latest` xóa 3
row mới nhất + `stale_date` đẩy 20% về 2005-01-01 → freshness stale_rows
tăng rõ rệt; `blank_summary` vi phạm `summary_length`; `duplicate` vi
phạm `paper_id_unique`.

### Kết luận từ số liệu

Hai chuỗi nhân quả đã / sẽ thể hiện trong run:

1. **Corruption (dự kiến)** → `quality_summary_length` fail, `freshness.stale_rows`
   > 0, `paper_id_unique` có duplicate → `mean_token_f1` giảm (noise +
   truncate title làm LLM trích sai đáp án), `retrieval_hit_rate` có thể
   tụt vì top hit bị truncate title hoặc duplicate đẩy nhầm rank.
2. **Repair (dự kiến)** → re-run `build_clean_dataframe` từ raw records →
   mọi artifact của cleaning khôi phục → quality pass 6/6 → metric agent
   khôi phục về baseline.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
Dựa trên thiết kế, `truncate_title` + `noise_summary` ảnh hưởng trực tiếp
nhất tới embedding (vector chứa text bị cắt / nhiễu → cosine similarity
sai). `stale_date` và `drop_latest` ảnh hưởng rõ nhất tới signal
freshness nhưng retrieval có thể vẫn chạm đúng DOI nếu query không
lọc theo time. `blank_summary` ảnh hưởng rõ tới `summary_length` nhưng
vì câu hỏi author/date/category có thể vẫn trả lời đúng nếu các trường
còn lại còn nguyên. Cần đợi Phase 2 chạy để xác nhận trật tự thực tế.

**Kết quả nào khác với kỳ vọng ban đầu?**
Baseline `judge_accuracy=0.958` chứ không phải 1.0. Giả thuyết: câu duy
nhất bị judge chấm chưa full credit (4/5 thay vì 5/5) có thể do câu trả
lời LLM suy rộng hơn đáp án trích từ abstract. Khi có đáp án từng câu
trong `data/results/baseline_answers.json`, kiểm tra nội dung để xác
nhận — chưa có dữ liệu câu-nào-trả-lời-sai để khẳng định pattern.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Cleaning không phải chỗ thay thế observability —
   phân biệt "không dùng được" (drop) với "không đạt chuẩn" (check fail).
   Hai hệ thống đo khác nhau, gộp vào nhau sẽ mất tín hiệu trong báo cáo.
2. **Data quality/observability:** Log count filter ở stdout + JSON
   artifact cùng lúc là cần thiết: stdout giúp debug runtime, JSON giúp
   so sánh giữa các run mà không cần log scraping.
3. **Ảnh hưởng của data đến RAG agent:** Cùng pipeline nhưng khi text bị
   truncate/duplicate, metric retrieval có thể sụt rất nhanh. Phase 2
   chưa chạy nhưng thiết kế corruption đã cố ý map 6 loại → 6 signal
   khác nhau để đảm bảo khi đo được cả 3 failure mode (freshness,
   validity, uniqueness).

### Nếu có thêm thời gian

- Thêm bước `summarize_category_alignment` ở cleaning: gom các biến thể
  category Crossref (`"Computer Science - AI"` ↔ `"cs.AI"`). Lý do: hiện
  `categories_joined` trong `papers_clean.json` rất nhiều record để
  rỗng, có thể ảnh hưởng câu hỏi loại `categories` khi Phase 2 chạy.
  Cách đo: chạy lại Phase 1, đếm % row có `categories_joined` khác rỗng,
  kỳ vọng tăng từ ~0% lên ≥ 50%.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Huy Anh
**Ngày xác nhận:** 2026-08-06