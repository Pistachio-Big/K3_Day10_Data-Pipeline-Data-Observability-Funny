# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                   |
| ------------------ |--------------------------------------------|
| Họ và tên       | Hoàng Văn Phái                             |
| MSSV               | 2A202601575                                |
| Khóa/Lớp         | K3                                         |
| Tên nhóm         | Funny                                           |
| Vai trò chính    | Ingestion (CP0)                            |
| Repository         | https://github.com/Pistachio-Big/K3_Day10_Data-Pipeline-Data-Observability-Funny |
| Ngày hoàn thành | 2026-08-06                                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Tải dữ liệu Crossref | `src/ingestion/crossref.py` / `fetch_source_records` | Query params từ config | `data/raw/crossref_response.json` | Hoàn thành |
| Parse dữ liệu raw | `src/ingestion/crossref.py` / `parse_crossref_payload` | Raw JSON Payload | `data/raw/crossref_records.json` (24 PaperRecord) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Viết tài liệu/report phần ingestion | Cả nhóm | Báo cáo chi tiết pipeline ingestion CP0 |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Gọi API Crossref, xử lý retry/backoff | `src/ingestion/crossref.py` | Raw snapshot artifact | `cat data/raw/crossref_response.json` |
| Bóc tách, làm sạch HTML/JATS trong abstract | `src/ingestion/crossref.py` | Parsed records | `cat data/raw/crossref_records.json` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Tạo ra 2 artifact đầu nguồn quan trọng: `crossref_response.json` lưu giữ nguyên vẹn payload từ API để đảm bảo traceability (có thể repair sau này), và `crossref_records.json` lưu 24 bản ghi chuẩn (`PaperRecord`) với `paper_id` được gán cố định bằng DOI.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Hệ thống RAG cần một tập dữ liệu context đầu vào (các bài báo khoa học). Bước CP0 giải quyết bài toán tải tự động (ingestion) metadata của các bài báo từ Crossref API, đảm bảo độ ổn định khi gọi API (tránh rate limit) và tạo nền móng data thô cho các bước làm sạch tiếp theo.

### Cách triển khai

- Hàm `fetch_source_records` gọi API tới `https://api.crossref.org/works`. Nếu gặp lỗi tạm thời như 429 (Too Many Requests) hoặc 50x, hệ thống tự động Sleep và thử lại (Exponential backoff lên đến 5 lần).
- Trước khi parse dữ liệu, raw response được dump xuống file. Việc này cho phép flow Repair về sau có thể đọc lại dữ liệu gốc mà không tốn công gọi API thêm lần nữa.
- Hàm `parse_crossref_payload` lọc bỏ các record không có DOI/Title. Các thẻ JATS/HTML lẫn trong `abstract` được strip sạch bằng Regex. Ngày tháng được đưa về định dạng chuẩn `YYYY-MM-DD`.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `Settings` (chứa query, filter, max_results) |
| Output                         | `List[PaperRecord]` và 2 file JSON ở `data/raw/` |
| Module phụ thuộc             | `core.config`, `core.utils` (để gọi regex/json io) |
| Module sử dụng output        | `src/ingestion/cleaning.py` (CP1) |
| Điều kiện lỗi cần xử lý | Server rate limit (429), timeout (50x), thiếu trường bắt buộc (DOI/Title). |

### Cách xác minh

```bash
uv run python script/run_phase1.py
```

- **Kết quả mong đợi:** Pipeline chạy thành công bước Ingestion mà không crash vì API limit. Thấy thông báo lấy thành công 24 records.
- **Kết quả thực tế:** Pipeline tạo ra đúng 24 records, parse abstract sạch HTML.
- **Artifact/log:** `data/raw/crossref_records.json`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Crossref API giới hạn số lượng request khá nghiêm ngặt và thi thoảng trả về 503.
- **Các phương án đã cân nhắc:** (1) Fail ngay lập tức, (2) Retry với thời gian chờ cố định, (3) Exponential backoff (đợi 1s, 2s, 4s, 8s...).
- **Phương án đã chọn:** Exponential backoff kèm lưu raw data trước khi parse.
- **Lý do:** Tối ưu hóa tính ổn định (resilience). Lưu dump trước khi parse đảm bảo dẫu logic parse bị lỗi (schema mismatch), ta không mất đi response quý giá vừa lấy được, giúp việc debug/repair dễ dàng (reproducibility).
- **Bằng chứng quyết định phù hợp:** Log ingestion không còn văng Exception `429 Too Many Requests` khi chạy liên tục.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Báo lỗi `KeyError` hoặc parse lỗi ngày tháng khi record trả về từ Crossref không có `date-parts` đầy đủ hoặc không có `abstract`.
- **Lệnh hoặc bước tái hiện:** Quét query phổ biến, lấy dữ liệu về.
- **Nguyên nhân gốc:** Schema của Crossref không đồng nhất, một số article chưa có abstract, một số date chỉ có năm `[2024]` thay vì `[2024, 8, 12]`.
- **Cách xử lý:** Viết hàm helper `_date_parts_to_iso` kiểm tra độ dài list để fill mặc định ngày/tháng là `1` nếu thiếu. Dùng `dict.get` kết hợp `or []` thay vì truy cập trực tiếp bằng key.
- **Cách xác minh sau khi sửa:** Chạy lại `fetch_source_records`, dữ liệu không còn văng Exception và field ngày tháng ra đúng chuẩn ISO string.
- **Điều học được:** Data từ real-world API không bao giờ sạch như tài liệu mô tả, luôn phải code phòng thủ (defensive programming) ngay từ khâu Ingestion.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu thô từ Crossref API (JSON) -> qua Ingestion (lọc DOI) -> qua Cleaning (chuẩn hóa title/abstract, metadata, filter stale) -> gộp thành `text_for_embedding` -> đưa qua embedding model (`all-MiniLM-L6-v2`) -> lưu vector và metadata vào collection của ChromaDB.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Evaluation set sinh các câu hỏi test với câu trả lời kỳ vọng (`ground_truth`) và ID tài liệu chuẩn chứa câu trả lời đó (`ground_truth_doc_ids`). Retrieval đo tỷ lệ lấy trúng ID chuẩn (Hit rate). Answer quality đo sự chính xác (F1/LLM Judge) giữa câu agent trả lời và câu `ground_truth`.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks kiểm tra tính toàn vẹn của dữ liệu tĩnh: không thiếu giá trị (null), ID không trùng lặp, abstract đủ dài. Freshness monitoring đánh giá tính hợp thời: dữ liệu lấy về (hoặc sinh ra) có bị lỗi thời quá số ngày cho phép (`threshold_days`) hay không.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để duy trì một thước đo chuẩn (ground truth) cố định. Chỉ khi test set cố định, chúng ta mới thấy được sụt giảm/cải thiện chỉ số thuần túy do chất lượng của base dữ liệu (vector index) thay đổi.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Artifact repair (`papers_clean_repaired.json`/`csv`) phải loại bỏ được data rác/trùng và giống với baseline. Metric của Repaired pipeline (như `retrieval_hit_rate` và `judge_accuracy`) phải khôi phục về điểm số của Baseline. Báo cáo Quality check pass 6/6 (0 trùng, 0 stale).

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.0 |       0.625 |      1.0 | Rớt thê thảm khi dữ liệu bị hỏng, sau repair phục hồi tuyệt đối |
| `mean_token_f1`      |      1.0 |       0.505 |      1.0 | Chất lượng câu trả lời bị ảnh hưởng trực tiếp từ context kém |
| `judge_accuracy`     |      0.958 |       0.458 |      0.958 | LLM đánh giá tỷ lệ trả lời đúng giảm mạnh khi corrupted |
| `mean_judge_score`   |      4.833 |       3.125 |      4.833 | Điểm judge rớt xuống mức trung bình/kém |
| Quality checks         |      6/6 |       4/6 |      6/6 | Phát hiện ra lỗi Duplicate (Unique fail) |
| Freshness status       |      Fresh |       Stale |      Fresh | Phát hiện 5 rows bị quá hạn tuổi (stale) |

### Kết luận từ số liệu

1. **[Data corruption]** → **[quality/freshness signal thay đổi]** → **[agent metric thay đổi]**.
2. **[Repair action]** → **[quality/freshness signal phục hồi]** → **[agent metric phục hồi]**.

Corruption nào ảnh hưởng rõ nhất và vì sao?
Việc xoá/sửa abstract (làm trống hoặc thêm nhiễu) khiến Vector DB không embed được ngữ nghĩa thật của bài báo. Khi user query, retriever bị miss (retrieval_hit_rate rớt từ 1.0 -> 0.625), từ đó Agent sinh câu trả lời bịa đặt hoặc thiếu sót, kéo tụt điểm Judge (0.958 -> 0.458).

Kết quả nào khác với kỳ vọng ban đầu?
Nhiều lúc cứ nghĩ LLM mạnh thì có thể "vớt vát" được từ khóa rơi rớt, nhưng chỉ số `mean_token_f1` giảm một nửa (còn 0.505) minh chứng rằng Garbage In -> Garbage Out. Không có context tốt thì LLM có xịn đến mấy cũng không chắp vá được.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Ingestion không chỉ là "gọi API" mà phải thiết kế cơ chế chịu lỗi (backoff) và có điểm rollback (dump raw data). 
2. **Về data quality/observability:** Lỗi dữ liệu im lặng (silent failure) cực kỳ nguy hiểm. Quality Checks & Freshness Monitoring là phòng tuyến cuối cùng báo hiệu có dữ liệu "bẩn" lọt vào index.
3. **Về ảnh hưởng của data đến RAG agent:** LLM/Agent chỉ tốt bằng dữ liệu nó được cấp (Context). Dữ liệu rỗng, nhiễu hoặc sai lệch làm hỏng hoàn toàn độ chính xác của câu trả lời, được thể hiện rõ qua sự tụt dốc của Judge Accuracy.

### Nếu có thêm thời gian

Tôi sẽ cải thiện khâu Ingestion để lưu metadata (như log thời gian chạy, số lượng record fetch thành công, http status codes) vào Datahub hoặc một dashboard nhỏ. Mục đích để observability ngay từ nguồn dữ liệu chứ không đợi đến khâu cuối. 

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phái
**Ngày xác nhận:** 2026-08-06
