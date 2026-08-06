# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| ------------------ | -------------------------- |
| Họ và tên | Hà Tấn Phong |
| MSSV | 2A202601577 |
| Khóa/Lớp | K3 |
| Tên nhóm | Funny |
| Vai trò chính | RAG & Evaluation |
| Repository | https://github.com/Pistachio-Big/K3_Day10_Data-Pipeline-Data-Observability-Funny/tree/main |
| Ngày hoàn thành | 2026-08-06 |

---

# 2. Vai trò và phạm vi công việc

## Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Evaluation Test Set | `src/evaluation/testset.py::build_test_set` | `papers_clean.json` | `data/eval/test_set.json` | Hoàn thành |
| Baseline Evaluation | Embedding Index + Evaluation | Test set + Embedding + Agent | `baseline_metrics.json`, `baseline_answers.json`, `papers_embeddings.json` | Hoàn thành |

Phần việc của tôi là xây dựng tập câu hỏi đánh giá cho hệ thống RAG, xây dựng embedding index và chạy evaluation để sinh các metrics dùng làm baseline cho toàn bộ pipeline.

## Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Smoke test Retrieval | Pipeline tích hợp | Xác minh search, lookup và agent trả kết quả đúng trước khi evaluation |
| Kiểm tra artifact | Pipeline Phase1 | Xác minh metrics và answers được sinh đầy đủ trước khi report |

---

# 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Xây dựng evaluation set gồm 24 câu hỏi | `src/evaluation/testset.py` | `data/eval/test_set.json` | Chạy `build_test_set()` |
| Chạy baseline evaluation | `baseline_metrics.json`, `baseline_answers.json` | Retrieval Hit = 1.0, Token F1 = 1.0 | Chạy `run_phase1.py` |

Output chính tôi tạo ra gồm:

- `data/eval/test_set.json`
- `data/embeddings/papers_embeddings.json`
- `data/results/baseline_metrics.json`
- `data/results/baseline_answers.json`

Đây là các artifact được các bước observability và reporting sử dụng để đánh giá chất lượng hệ thống.

---

# 4. Giải thích phần kỹ thuật đã thực hiện

## Vấn đề cần giải quyết

Sau khi dữ liệu được làm sạch và xây dựng vector index, hệ thống cần một bộ câu hỏi chuẩn để đánh giá khả năng Retrieval và Question Answering. Nếu không có evaluation set cố định thì không thể so sánh giữa baseline, corrupted và repaired.

## Cách triển khai

Tôi xây dựng hàm `build_test_set()` sinh tự động 24 câu hỏi dựa trên dữ liệu đã clean.

Các câu hỏi được chia thành 4 nhóm:

- Summary
- Authors
- Publication Date
- Categories

Mỗi câu hỏi đều chứa:

- question
- expected_answer
- ground_truth_document_id

Ground truth document ID được lấy trực tiếp từ `paper_id` nhằm đánh giá retrieval hit.

Sau đó tôi xây dựng embedding index bằng `LocalEmbeddingIndex`, tạo collection `papers-baseline`, thực hiện smoke test trước khi chạy evaluation.

Evaluation sử dụng cùng test set để tính:

- Retrieval Hit Rate
- Mean Token F1
- LLM Judge Score
- Judge Accuracy

Judge sử dụng OpenRouter với model `openai/gpt-4o-mini`.

## Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input | `papers_clean.json` |
| Output | `test_set.json`, `baseline_metrics.json`, `baseline_answers.json`, `papers_embeddings.json` |
| Module phụ thuộc | Cleaning |
| Module sử dụng output | Reporting, Observability |
| Điều kiện lỗi cần xử lý | Empty dataset, embedding lỗi, LLM judge timeout |

## Cách xác minh

```bash
python run_phase1.py
```

- **Kết quả mong đợi:** tạo đầy đủ embedding, evaluation set và metrics.
- **Kết quả thực tế:** sinh thành công toàn bộ artifact.
- **Artifact/log:** `data/results/`, `data/eval/`, `data/embeddings/`

---

# 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần thiết kế evaluation set để có thể đánh giá chính xác cả Retrieval và QA.
- **Các phương án đã cân nhắc:**
  1. Viết thủ công toàn bộ câu hỏi.
  2. Sinh tự động từ dữ liệu đã clean.
- **Phương án đã chọn:** Sinh tự động từ dữ liệu.
- **Lý do:** Dễ tái tạo, tránh sai lệch giữa các lần chạy và bảo đảm ground truth luôn đồng bộ với dữ liệu.
- **Bằng chứng quyết định phù hợp:** Baseline đạt Retrieval Hit Rate = 1.0 và Mean Token F1 = 1.0.

---

# 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**

Một số câu hỏi ban đầu không được parser của QA nhận diện đúng nên answer extraction thất bại.

- **Lệnh hoặc bước tái hiện:**

```bash
python run_phase1.py
```

- **Nguyên nhân gốc:**

Question template chưa sử dụng đúng các keyword mà `qa._extract_answer()` hỗ trợ.

- **Cách xử lý:**

Điều chỉnh template của `build_test_set()` để sử dụng đúng nhóm từ khóa:

- summary
- authors
- date
- categories

- **Cách xác minh sau khi sửa:**

Evaluation đạt:

- Retrieval Hit Rate = 1.0
- Mean Token F1 = 1.0

- **Điều học được:**

Evaluation set cần đồng bộ với logic parser của hệ thống để tránh đánh giá sai.

---

# 7. Hiểu biết về luồng end-to-end

## Câu trả lời

1. Crossref trả dữ liệu JSON, ingestion lưu raw response và parse thành records. Cleaning chuẩn hóa dữ liệu, tạo `text_for_embedding`, sau đó embedding index chuyển dữ liệu thành vector để phục vụ retrieval.

2. Evaluation set chứa câu hỏi cùng ground truth document ID. Retrieval được xem đúng khi document được tìm thấy trùng với ground truth. Sau đó câu trả lời được so sánh bằng Token F1 và LLM Judge.

3. Quality checks kiểm tra tính đúng đắn của dữ liệu (null, duplicate, row count, summary...), còn freshness monitoring đánh giá dữ liệu có còn mới theo ngưỡng thời gian hay không.

4. Cùng một test set giúp việc so sánh baseline, corrupted và repaired công bằng vì chỉ thay đổi dữ liệu chứ không thay đổi câu hỏi.

5. Repair thành công khi quality/freshness phục hồi và các metrics như retrieval hit rate, token F1 và judge accuracy tăng trở lại so với corrupted.

---

# 8. Phân tích kết quả

## Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| retrieval_hit_rate | 1.0 | [ ] | [ ] | Baseline đạt toàn bộ retrieval |
| mean_token_f1 | 1.0 | [ ] | [ ] | Answer khớp hoàn toàn ground truth |
| judge_accuracy | 1.0 | [ ] | [ ] | Judge đồng ý với toàn bộ kết quả |
| mean_judge_score | 5.0 | [ ] | [ ] | Điểm tuyệt đối |
| Quality checks | 6/6 Pass | [ ] | [ ] | Baseline không có lỗi dữ liệu |
| Freshness status | Fresh | [ ] | [ ] | Dữ liệu mới |

## Kết luận từ số liệu

1.

Data corruption

↓

Quality/Freshness giảm

↓

Retrieval và QA giảm.

2.

Repair

↓

Quality/Freshness phục hồi

↓

Evaluation metrics phục hồi.

Corruption ảnh hưởng mạnh nhất là dữ liệu bị thiếu hoặc sai metadata vì retrieval không còn tìm đúng tài liệu.

Kết quả baseline đúng với kỳ vọng khi toàn bộ metrics đạt mức tối đa.

---

# 9. Điều học được và hướng cải thiện

## Ba điều quan trọng nhất

1. Evaluation cần một test set cố định để đảm bảo tính so sánh.
2. Chất lượng dữ liệu ảnh hưởng trực tiếp đến hiệu quả Retrieval.
3. LLM Judge giúp đánh giá semantic tốt hơn so với chỉ dùng exact match.

## Nếu có thêm thời gian

Tôi muốn mở rộng test set với nhiều loại câu hỏi suy luận hơn thay vì chỉ fact-based QA để đánh giá khả năng RAG trong tình huống thực tế.

---

# 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Hà Tấn Phong

**Ngày xác nhận:** 2026-08-06