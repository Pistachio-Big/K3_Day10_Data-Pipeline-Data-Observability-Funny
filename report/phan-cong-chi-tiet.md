# Phân công chi tiết — Day 10: Data Pipeline & Data Observability

Nhóm 5 người: **Đại, Phái, Huy Anh, Phong, Kiên**.

Mục tiêu bài lab: chạy được baseline pipeline end-to-end trên dữ liệu sạch, sau đó cố ý làm hỏng dữ liệu (corruption), đo tác động lên agent, repair từ raw và **chứng minh bằng số liệu** baseline → corrupted → repaired.

Có đúng **8 hàm `NotImplementedError`** cần code. Phần `src/retrieval/`, `src/evaluation/metrics.py`, `src/core/` đã cho sẵn, chỉ đọc-hiểu-dùng.

---

## Bảng phân công tổng quan

| Người | Vai trò | File sở hữu (phải code) | Hàm |
|-------|---------|--------------------------|-----|
| **Đại** | Pipeline Integrator (Lead) | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` | `main()` × 2 |
| **Phái** | Ingestion Owner | `src/ingestion/crossref.py` | `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` |
| **Huy Anh** | Cleaning & Corruption Owner | `src/ingestion/cleaning.py`, `src/ingestion/corruption.py` | `build_clean_dataframe`, `corrupt_clean_dataframe` |
| **Phong** | RAG & Evaluation Owner | `src/evaluation/testset.py` (+ vận hành `src/retrieval/`) | `build_test_set` |
| **Kiên** | Observability & Reporting Owner | `src/observability/quality.py`, `src/observability/reporting.py` | `run_data_quality_checks`, `build_freshness_report`, `generate_phase1_report`, `generate_corruption_report` |

### Thứ tự phụ thuộc (ai chờ ai)

```
Phái (raw records)
  -> Huy Anh (clean dataframe)      <- khóa schema clean ở đây, mọi người phụ thuộc cột này
      -> Phong (test set + index/agent)
      -> Kiên (quality/freshness + report)
      -> Đại (ghép phase1.py) --- baseline xong ---
          -> Huy Anh (corruption) + Phái (repair từ raw)
              -> Đại (ghép corruption_flow.py) + Kiên (comparison report)
```

**Nguyên tắc:** Huy Anh phải chốt **schema của clean dataframe** sớm nhất có thể (cuối giờ 1) vì Phong, Kiên, Đại đều đọc các cột `paper_id, title, summary, authors_joined, categories_joined, published, age_days, text_for_embedding`.

---

## Contract chung — schema clean dataframe (cả nhóm học thuộc)

`LocalEmbeddingIndex._build_documents` và `qa.py` **bắt buộc** các cột sau tồn tại trong clean dataframe:

| Cột | Kiểu | Dùng ở đâu |
|-----|------|-----------|
| `paper_id` | str, unique | id document, ground_truth_doc_ids, retrieval hit |
| `title` | str | lookup theo title, metadata |
| `summary` | str | agent trả lời câu hỏi summary, quality check độ dài |
| `authors_joined` | str | agent trả lời "who authored", metadata |
| `categories_joined` | str | agent trả lời "what categories", metadata |
| `published` | str (ISO date) | agent trả lời "when was", freshness |
| `abs_url`, `pdf_url` | str | metadata |
| `text_for_embedding` | str | nội dung được embed vào Chroma |
| `age_days` | int | freshness report, quality check |

> Nếu thiếu bất kỳ cột nào ở trên, `index.py` hoặc `qa.py` sẽ `KeyError`. Đây là hợp đồng quan trọng nhất của cả bài.

---

## ĐẠI — Pipeline Integrator (Lead)

**File:** `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`
**Chạy:** `script/run_phase1.py`, `script/run_corruption_flow.py`

### Việc phải làm

Đại là người ghép mọi module lại và chạy end-to-end. Không viết logic dữ liệu, nhưng phải hiểu contract của tất cả để gọi đúng thứ tự. Đại cũng lo `.env`, chọn provider, và điều phối demo/nộp bài.

### `phase1.py::main()` — làm thế nào

```python
from datetime import datetime, UTC
from core.config import load_settings
from core.utils import write_csv, write_json, read_json
from ingestion.crossref import fetch_source_records, load_raw_records
from ingestion.cleaning import build_clean_dataframe
from evaluation.testset import build_test_set
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex

def main() -> None:
    settings = load_settings()
    p = settings.paths

    # 1. Raw: fetch mới nếu chưa có hoặc REFRESH_SOURCE=1, ngược lại load lại snapshot
    if settings.refresh_source or not p.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(p.raw_records_json)

    # 2. Clean
    df = build_clean_dataframe(records, run_date=datetime.now(UTC))
    write_csv(df, p.clean_csv)
    write_json(p.clean_json, df.to_dict(orient="records"))

    # 3. Index (Chroma collection papers-baseline) — dùng path embeddings baseline
    index = LocalEmbeddingIndex.build(df, settings, embeddings_output_path=p.embeddings_json)

    # 4. Test set: tạo mới nếu chưa có / REFRESH_TEST_SET, ngược lại giữ nguyên
    if settings.refresh_test_set or not p.eval_testset.exists():
        build_test_set(df, p.eval_testset)

    # 5. Evaluate -> baseline_metrics.json + baseline_answers.json
    evaluate_pipeline(settings, index, p.eval_testset, p.baseline_metrics, p.baseline_answers)

    # 6. Quality + freshness
    quality = run_data_quality_checks(df, settings, report_name="baseline")
    freshness = build_freshness_report(df, settings, p.freshness_report)

    # 7. Report markdown
    source_summary = {"source": settings.source_api, "query": settings.source_query,
                      "filter": settings.source_filter, "records": len(df)}
    metrics = read_json(p.baseline_metrics)
    generate_phase1_report(p.baseline_report, source_summary, metrics, quality, freshness)
    print("Baseline done.")
```

### `corruption_flow.py::main()` — làm thế nào

Chỉ chạy **sau khi baseline có đủ artifact**. Dùng **path và collection riêng** cho corrupted/repaired, tuyệt đối không ghi đè baseline.

```python
def main() -> None:
    settings = load_settings()
    p = settings.paths

    # 1. Load clean baseline (KHÔNG fetch lại source)
    baseline_df = pd.DataFrame(read_json(p.clean_json))
    baseline_metrics = read_json(p.baseline_metrics)

    # 2. Corrupt
    corrupted_df = corrupt_clean_dataframe(baseline_df.copy(), p.corruption_log)
    write_csv(corrupted_df, p.corrupted_clean_csv)
    write_json(p.corrupted_clean_json, corrupted_df.to_dict(orient="records"))

    # 3. Index corrupted (collection papers-corrupted qua path riêng)
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings,
                                                embeddings_output_path=p.corrupted_embeddings_json)

    # 4. Evaluate corrupted TRÊN CÙNG test_set.json
    evaluate_pipeline(settings, corrupted_index, p.eval_testset,
                      p.corrupted_metrics, p.corrupted_answers)
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(corrupted_df, settings,
                                                 p.quality_dir / "freshness_corrupted.json")

    # 5. Repair: chạy lại cleaning TỪ RAW (không sửa tay)
    records = load_raw_records(p.raw_records_json)
    repaired_df = build_clean_dataframe(records, run_date=datetime.now(UTC))
    write_csv(repaired_df, p.repaired_clean_csv)
    write_json(p.repaired_clean_json, repaired_df.to_dict(orient="records"))
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings,
                                               embeddings_output_path=p.repaired_embeddings_json)
    evaluate_pipeline(settings, repaired_index, p.eval_testset,
                      p.repaired_metrics, p.repaired_answers)
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(repaired_df, settings,
                                                p.quality_dir / "freshness_repaired.json")

    # 6. Comparison report
    generate_corruption_report(
        p.comparison_report, baseline_metrics,
        read_json(p.corrupted_metrics), read_json(p.repaired_metrics),
        corrupted_quality, repaired_quality,
        corrupted_freshness, repaired_freshness)
    print("Corruption flow done.")
```

### Xác minh
- `python script/run_phase1.py` chạy hết, sinh đủ file trong `data/results`, `data/quality`, `data/reports`.
- `python script/run_corruption_flow.py` chạy sau, không ghi đè `baseline_metrics.json`.
- Kiểm tra collection tách biệt: `papers-baseline`, `papers-corrupted`, `papers-repaired`.

### Trách nhiệm điều phối
- Chốt `.env` (mặc định Gemini + `GOOGLE_API_KEY`), branch, definition of done.
- Kiểm tra không commit `.env`/API key.
- Điều phối demo cuối: mở artifact thật, không "tô" số liệu.

---

## PHÁI — Ingestion Owner

**File:** `src/ingestion/crossref.py` (3 hàm) · **Artifact:** `data/raw/`

### Bối cảnh
Crossref REST API: `https://api.crossref.org/works`. Trả về JSON dạng `{"message": {"items": [...]}}`. Mỗi item có `DOI, title (list), abstract, author (list of {given, family}), subject (list), published/issued (date-parts), URL, ...`.

Config đã cho: `settings.source_query`, `settings.source_filter` (`from-pub-date:...,has-abstract:true`), `settings.max_results` (24).

### `parse_crossref_payload(payload) -> list[PaperRecord]` — làm thế nào
`PaperRecord` là dataclass có sẵn với các field: `paper_id, title, summary, authors, categories, primary_category, published, updated, abs_url, pdf_url, comment`.

```python
def parse_crossref_payload(payload):
    items = payload.get("message", {}).get("items", [])
    records = []
    for it in items:
        doi = it.get("DOI")
        title_list = it.get("title") or []
        title = normalize_whitespace(title_list[0]) if title_list else ""
        if not doi or not title:
            continue  # bỏ record không hợp lệ
        abstract = it.get("abstract", "")
        # abstract Crossref có tag JATS <jats:p>...; strip tag
        summary = normalize_whitespace(re.sub(r"<[^>]+>", " ", abstract))
        authors = [normalize_whitespace(f"{a.get('given','')} {a.get('family','')}")
                   for a in it.get("author", [])]
        authors = [a for a in authors if a]
        categories = it.get("subject", []) or []
        primary = categories[0] if categories else ""
        published = _date_parts_to_iso(it.get("published") or it.get("issued"))
        updated = _date_parts_to_iso(it.get("deposited")) or published
        records.append(PaperRecord(
            paper_id=doi, title=title, summary=summary,
            authors=authors, categories=categories, primary_category=primary,
            published=published, updated=updated,
            abs_url=it.get("URL", ""),
            pdf_url=_first_pdf_link(it),  # duyệt it.get("link", []) tìm content-type pdf
            comment=""))
    return records
```
Helper `_date_parts_to_iso`: lấy `x["date-parts"][0]` = `[year, month, day]`, pad thành `YYYY-MM-DD` (thiếu tháng/ngày thì dùng `01`).

`paper_id = DOI` là khóa ổn định xuyên suốt raw → clean → index → ground truth. **Không đổi cách sinh id giữa chừng.**

### `fetch_source_records(settings) -> list[PaperRecord]` — làm thế nào
```python
def fetch_source_records(settings):
    params = {"query": settings.source_query,
              "filter": settings.source_filter,
              "rows": settings.max_results,
              "select": "DOI,title,abstract,author,subject,published,issued,deposited,URL,link"}
    # gọi có retry cho 429/503
    for attempt in range(5):
        resp = requests.get("https://api.crossref.org/works", params=params,
                            headers={"User-Agent": "day10-lab/1.0 (mailto:you@example.com)"},
                            timeout=30)
        if resp.status_code in (429, 503):
            time.sleep(2 ** attempt)      # exponential backoff
            continue
        resp.raise_for_status()
        break
    payload = resp.json()
    write_json(settings.paths.raw_api_response, payload)     # LƯU RAW TRƯỚC khi parse
    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json,
               [asdict(r) for r in records])                 # lưu records đã parse
    return records
```
Bắt buộc: **lưu raw response nguyên bản trước khi parse** (để repair và truy vết).

### `load_raw_records(path) -> list[PaperRecord]` — làm thế nào
```python
def load_raw_records(path):
    data = read_json(path)
    return [PaperRecord(**row) for row in data]  # authors/categories đã là list trong JSON
```

### Hỗ trợ repair (giờ 3–4)
Repair = Đại gọi lại `load_raw_records` + cleaning từ raw. Phái đảm bảo `data/raw/crossref_records.json` là snapshot đúng, đọc lại được, đủ field để cleaning không phải đoán.

### Xác minh
```bash
python -c "from ingestion.crossref import fetch_source_records; from core.config import load_settings; r=fetch_source_records(load_settings()); print(len(r), r[0].paper_id, r[0].title)"
ls data/raw   # crossref_response.json + crossref_records.json
```

---

## HUY ANH — Cleaning & Corruption Owner

**File:** `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`

### `build_clean_dataframe(records, run_date) -> pd.DataFrame` — làm thế nào
Đây là **hàm quan trọng nhất** — output định nghĩa contract cho cả nhóm (xem bảng schema ở đầu).

```python
def build_clean_dataframe(records, run_date):
    rows = []
    for r in records:
        title = normalize_whitespace(r.title)
        summary = normalize_whitespace(r.summary)
        if not r.paper_id or not title:
            continue                       # loại record thiếu id/title (Completeness)
        published = _parse_date(r.published)      # -> "YYYY-MM-DD" hoặc ""
        if not published:
            continue                       # cần published để tính freshness
        age_days = (run_date.date() - date.fromisoformat(published)).days
        authors_joined = compact_join(r.authors)          # "A, B, C"
        categories_joined = compact_join(r.categories)
        text_for_embedding = f"{title}. {summary} Authors: {authors_joined}. Categories: {categories_joined}."
        rows.append({
            "paper_id": r.paper_id, "title": title, "summary": summary,
            "authors_joined": authors_joined, "categories_joined": categories_joined,
            "primary_category": r.primary_category,
            "published": published, "updated": r.updated,
            "abs_url": r.abs_url, "pdf_url": r.pdf_url,
            "summary_chars": len(summary), "age_days": age_days,
            "text_for_embedding": normalize_whitespace(text_for_embedding),
        })
    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset="paper_id", keep="first")   # dedupe theo id ổn định
    df = df[df["text_for_embedding"].str.len() > 0]
    df = df.sort_values("published", ascending=False).reset_index(drop=True)
    return df
```
Quy tắc phải **để lại count/log**: bao nhiêu record bị loại vì thiếu title, bao nhiêu do trùng — ghi ra để làm evidence (in `print` hoặc trả count cho report). Đừng làm mất record âm thầm.

### `corrupt_clean_dataframe(df, output_log_path) -> pd.DataFrame` — làm thế nào (giờ 3)
Cố ý tạo lỗi **có chủ đích, có log, đo được**. Ghi log chi tiết: loại lỗi, paper_id bị tác động, tham số, count before/after.

```python
def corrupt_clean_dataframe(df, output_log_path):
    df = df.copy().reset_index(drop=True)
    log = {"original_rows": len(df), "corruptions": []}

    # 1. Drop 3 record mới nhất (df đã sort published desc) -> mất tính freshness
    latest = df.head(3)["paper_id"].tolist()
    df = df[~df["paper_id"].isin(latest)]
    log["corruptions"].append({"type": "drop_latest", "paper_ids": latest})

    # 2. Blank summary ở ~15% dòng
    blank_idx = df.sample(frac=0.15, random_state=42).index
    df.loc[blank_idx, "summary"] = ""
    df.loc[blank_idx, "summary_chars"] = 0
    log["corruptions"].append({"type": "blank_summary", "count": len(blank_idx)})

    # 3. Inject noise vào summary vài dòng
    noise_idx = df.sample(frac=0.1, random_state=7).index
    df.loc[noise_idx, "summary"] = df.loc[noise_idx, "summary"] + " zzxq!!! ??? lorem noise 00xx"
    log["corruptions"].append({"type": "noise", "count": len(noise_idx)})

    # 4. Truncate title vài dòng
    trunc_idx = df.sample(frac=0.1, random_state=11).index
    df.loc[trunc_idx, "title"] = df.loc[trunc_idx, "title"].str[:8]
    log["corruptions"].append({"type": "truncate_title", "count": len(trunc_idx)})

    # 5. Làm published cũ đi (stale) -> hỏng freshness
    stale_idx = df.sample(frac=0.2, random_state=3).index
    df.loc[stale_idx, "published"] = "2005-01-01"
    df.loc[stale_idx, "age_days"] = 9999
    log["corruptions"].append({"type": "stale_date", "count": len(stale_idx)})

    # 6. Thêm duplicate rows
    dups = df.head(2).copy()
    df = pd.concat([df, dups], ignore_index=True)
    log["corruptions"].append({"type": "duplicate", "count": len(dups)})

    # 7. Rebuild text_for_embedding từ dữ liệu đã hỏng
    df["text_for_embedding"] = (df["title"].fillna("") + ". " + df["summary"].fillna("")
        + " Authors: " + df["authors_joined"].fillna("")
        + ". Categories: " + df["categories_joined"].fillna("") + ".")
    df["text_for_embedding"] = df["text_for_embedding"].map(normalize_whitespace)

    log["final_rows"] = len(df)
    write_json(output_log_path, log)   # data/results/corruption_log.json
    return df
```
Mỗi loại corruption phải khớp một **quality signal** mà Kiên đo được: drop_latest/stale → freshness xấu; blank_summary → summary length fail; duplicate → uniqueness fail; truncate/noise → token_f1 và retrieval hit giảm.

### Xác minh
```bash
python script/run_phase1.py   # cần clean chạy được trước
cat data/results/corruption_log.json
```

---

## PHONG — RAG & Evaluation Owner

**File cần code:** `src/evaluation/testset.py` · **File cần đọc-hiểu-vận hành:** `src/retrieval/index.py`, `embeddings.py`, `agent.py`, `qa.py`, `llm.py`

### Phần vận hành RAG (không cần code, nhưng phải nắm & smoke-test)
- `LocalEmbeddingIndex.build(df, settings, embeddings_output_path=...)`: tạo Chroma collection từ df, dùng MiniLM (`all-MiniLM-L6-v2`), lưu manifest. Collection name tự map theo path (`papers-baseline/corrupted/repaired`).
- `qa.answer_question`: agent lookup theo title trong dấu `'...'`, semantic search top-k, rồi `_extract_answer` chọn field theo dạng câu hỏi (authors / published / categories / summary).
- Phong xác nhận: mọi metadata `qa.py` cần (`authors_joined, published, categories_joined, summary`) đều có trong df của Huy Anh. Nếu thiếu → báo Huy Anh sửa contract, **không vá index**.
- Smoke test sau khi index: `index.search("agentic RAG")` trả document; `index.lookup("<title>")` trả đúng paper.

### `build_test_set(df, output_path) -> list[dict]` — làm thế nào
`metrics.evaluate_pipeline` đọc mỗi item cần: `id, question_type, question, ground_truth, ground_truth_doc_ids`. Và `_extract_answer` chỉ nhận diện đúng nếu câu hỏi chứa cụm khóa: **"who authored" / "list the authors"**, **"when was" / "publication date" / "published on"**, **"what categories"**, còn lại → summary.

```python
def build_test_set(df, output_path):
    if len(df) < 4:
        raise ValueError("Cần tối thiểu vài document để tạo test set.")
    rows = []
    sample = df.head(8)  # vài paper đại diện, đều có trong index
    for i, r in enumerate(sample.itertuples()):
        pid = r.paper_id
        # câu hỏi summary
        rows.append({"id": f"q_sum_{i}", "question_type": "summary",
            "question": f"Summarize the paper titled '{r.title}'.",
            "ground_truth": first_sentence(r.summary),
            "ground_truth_doc_ids": [pid]})
        # authors — dùng đúng cụm khóa "who authored"
        rows.append({"id": f"q_auth_{i}", "question_type": "authors",
            "question": f"Who authored the paper titled '{r.title}'?",
            "ground_truth": r.authors_joined,
            "ground_truth_doc_ids": [pid]})
        # date — cụm "when was"
        rows.append({"id": f"q_date_{i}", "question_type": "date",
            "question": f"When was the paper titled '{r.title}' published on?",
            "ground_truth": r.published,
            "ground_truth_doc_ids": [pid]})
        # categories — cụm "what categories"
        rows.append({"id": f"q_cat_{i}", "question_type": "categories",
            "question": f"What categories does the paper titled '{r.title}' belong to?",
            "ground_truth": r.categories_joined,
            "ground_truth_doc_ids": [pid]})
    write_json(output_path, rows)
    return rows
```
Quan trọng:
- `ground_truth_doc_ids` lấy **đúng `paper_id`** từ df, không bịa.
- Câu hỏi nhúng title trong dấu `'...'` để agent lookup exact match (xem `qa.py` regex `'([^']+)'`).
- Ground truth phải khớp cách `_extract_answer` trả lời (authors → `authors_joined`, date → `published`, summary → `first_sentence(summary)`).
- Test set tạo **một lần rồi khóa**: baseline/corrupted/repaired dùng chung file `test_set.json` để so sánh công bằng.

### Xác minh
```bash
python script/run_phase1.py
cat data/eval/test_set.json
cat data/results/baseline_metrics.json   # retrieval_hit_rate, mean_token_f1, judge_accuracy
```
Đọc 1 hit và 1 miss trong `baseline_answers.json`, giải thích được vì sao.

---

## KIÊN — Observability & Reporting Owner

**File:** `src/observability/quality.py` (2 hàm), `src/observability/reporting.py` (2 hàm)

### `run_data_quality_checks(df, settings, report_name) -> dict` — làm thế nào
```python
def run_data_quality_checks(df, settings, report_name):
    checks = []
    def add(name, dim, passed, detail):
        checks.append({"check": name, "dimension": dim, "passed": bool(passed), "detail": detail})

    add("row_count", "Completeness", len(df) > 0, {"rows": len(df)})
    add("paper_id_not_null", "Completeness", df["paper_id"].notna().all(),
        {"nulls": int(df["paper_id"].isna().sum())})
    add("paper_id_unique", "Uniqueness", df["paper_id"].is_unique,
        {"duplicates": int(len(df) - df["paper_id"].nunique())})
    add("title_not_null", "Completeness", df["title"].notna().all() and (df["title"].str.len() > 0).all(),
        {"empty_titles": int((df["title"].str.len() == 0).sum())})
    min_len = 20
    add("summary_length", "Validity", (df["summary"].str.len() >= min_len).mean() > 0.8,
        {"below_threshold": int((df["summary"].str.len() < min_len).sum()), "threshold": min_len})
    stale = int((df["age_days"] > settings.freshness_threshold_days).sum())
    add("freshness", "Timeliness", stale == 0, {"stale_rows": stale,
        "threshold_days": settings.freshness_threshold_days})

    result = {"report_name": report_name, "total_checks": len(checks),
              "passed": sum(c["passed"] for c in checks),
              "failed": sum(not c["passed"] for c in checks), "checks": checks}
    write_json(settings.paths.quality_dir / f"quality_{report_name}.json", result)
    return result
```

### `build_freshness_report(df, settings, report_path) -> dict` — làm thế nào
```python
def build_freshness_report(df, settings, report_path):
    published = df["published"].dropna()
    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
    payload = {
        "latest_published": published.max(),
        "oldest_published": published.min(),
        "stale_rows": stale_rows,
        "total_rows": len(df),
        "threshold_days": settings.freshness_threshold_days,
        "is_fresh": stale_rows == 0,
    }
    write_json(report_path, payload)
    return payload
```

### `generate_phase1_report(report_path, source_summary, metrics, quality, freshness)` — làm thế nào
Viết markdown đọc được, trỏ tới artifact thật:
```python
def generate_phase1_report(report_path, source_summary, metrics, quality, freshness):
    lines = ["# Phase 1 — Baseline Report", "",
        "## Nguồn dữ liệu",
        f"- Source: {source_summary['source']}",
        f"- Query: {source_summary['query']}",
        f"- Records: {source_summary['records']}", "",
        "## Metrics",
        f"- retrieval_hit_rate: {metrics['retrieval_hit_rate']:.3f}",
        f"- mean_token_f1: {metrics['mean_token_f1']:.3f}",
        f"- judge_accuracy: {metrics['judge_accuracy']:.3f}",
        f"- mean_judge_score: {metrics['mean_judge_score']:.3f}", "",
        "## Data Quality",
        f"- Passed {quality['passed']}/{quality['total_checks']} checks"]
    for c in quality["checks"]:
        lines.append(f"  - [{'PASS' if c['passed'] else 'FAIL'}] {c['check']} ({c['dimension']})")
    lines += ["", "## Freshness",
        f"- latest: {freshness['latest_published']}, oldest: {freshness['oldest_published']}",
        f"- stale_rows: {freshness['stale_rows']}/{freshness['total_rows']}",
        f"- is_fresh: {freshness['is_fresh']}"]
    write_text(report_path, "\n".join(lines) + "\n")
```

### `generate_corruption_report(...)` — làm thế nào
Bảng so sánh 3 trạng thái + kết luận nhân quả:
```python
def generate_corruption_report(report_path, baseline, corrupted, repaired,
                               c_quality, r_quality, c_fresh, r_fresh):
    def row(k): return f"| {k} | {baseline[k]:.3f} | {corrupted[k]:.3f} | {repaired[k]:.3f} |"
    keys = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
    lines = ["# Corruption Comparison Report", "",
        "| Metric | Baseline | Corrupted | Repaired |", "|---|---|---|---|"]
    lines += [row(k) for k in keys]
    lines += ["", "## Quality checks (passed/total)",
        f"- corrupted: {c_quality['passed']}/{c_quality['total_checks']}",
        f"- repaired: {r_quality['passed']}/{r_quality['total_checks']}", "",
        "## Freshness",
        f"- corrupted is_fresh: {c_fresh['is_fresh']} (stale {c_fresh['stale_rows']})",
        f"- repaired is_fresh: {r_fresh['is_fresh']} (stale {r_fresh['stale_rows']})", "",
        "## Kết luận nhân quả",
        "1. Corruption (blank/stale/noise) → quality FAIL + freshness stale → hit_rate & token_f1 giảm.",
        "2. Repair từ raw → quality/freshness phục hồi → metrics quay lại gần baseline."]
    write_text(report_path, "\n".join(lines) + "\n")
```
Nguyên tắc: **không kết luận corruption "có tác động" nếu số liệu không đổi.** Nếu recovery chưa hoàn toàn, ghi rõ.

### Xác minh
```bash
cat data/quality/quality_baseline.json data/quality/freshness_report.json
cat data/reports/phase1_report.md
cat data/reports/corruption_report.md
```

---

## Quy tắc xuyên suốt (cả nhóm)

1. Chỉ chạy corruption **sau khi** baseline tạo đủ artifact.
2. Giữ nguyên test set / ground truth / evaluator / top_k khi so sánh 3 trạng thái.
3. Dùng path + collection riêng cho baseline / corrupted / repaired; **không ghi đè baseline**.
4. Repair = chạy lại từ raw đáng tin, **không sửa tay** answers/metrics.
5. Report phải trỏ artifact thật; **không commit `.env`/API key**.
6. `paper_id` (= DOI) là khóa ổn định xuyên suốt; không đổi cách sinh id giữa chừng.

## Lệnh cài & chạy

```bash
uv sync
```
```bash
python script/run_phase1.py
```
```bash
python script/run_corruption_flow.py
```

## Báo cáo nộp
- Nhóm: điền `report/group_report.md`.
- Mỗi người: điền `report/individual_report.md` theo phần việc của mình (không copy nhau).
