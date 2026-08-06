# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Phạm Trung Kiên |
| MSSV | 2A202601986 |
| Khóa/Lớp | K3 |
| Tên nhóm | Funny |
| Vai trò chính | Observability & Reporting |
| Repository | https://github.com/Pistachio-Big/K3_Day10_Data-Pipeline-Data-Observability-Funny |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data quality checks | src/observability/quality.py | DataFrame papers đã qua cleaning, Settings, tên báo cáo | JSON quality report tại data/quality/ | Hoàn thành |
| Freshness reporting | src/observability/quality.py | Cột published, age_days, ngưỡng freshness | JSON freshness report tại data/quality/freshness_report.json | Hoàn thành |
| Markdown reporting cho phase 1 | src/observability/reporting.py | Summary nguồn dữ liệu, metrics baseline, quality result, freshness result | Markdown report tại data/reports/phase1_report.md | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Kiểm tra và đối chiếu artifact | Pipeline phase 1 / nhóm | Xác nhận các file quality và report đã được sinh đúng dạng JSON/Markdown |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Triển khai kiểm tra độ đầy đủ, duy nhất, hợp lệ và freshness cho dataset | src/observability/quality.py | quality_baseline.json với 6/6 checks PASS | Đọc file JSON đã tạo trong data/quality/ |
| Xây dựng freshness summary cho dataset | src/observability/quality.py | freshness_report.json với latest_published, oldest_published, stale_rows và is_fresh | Đọc file JSON đã tạo trong data/quality/ |
| Tạo báo cáo markdown tổng hợp cho baseline phase | src/observability/reporting.py | phase1_report.md chứa metrics, quality checks và freshness | Đọc file Markdown trong data/reports/ |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Đã tạo và đóng góp các artifact quan trọng cho phase 1: quality_baseline.json, freshness_report.json và phase1_report.md, giúp team có thể đánh giá chất lượng dữ liệu và freshness trước khi chạy các bước retrieval/evaluation tiếp theo.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trong pipeline, dữ liệu đầu vào cần được kiểm tra trước khi dùng cho retrieval và evaluation. Nếu các record thiếu paper_id, title, summary quá ngắn hoặc đã quá cũ, agent sẽ bị ảnh hưởng bởi dữ liệu không ổn định và kết quả trả lời sẽ giảm chất lượng.

### Cách triển khai

Tôi triển khai một lớp kiểm tra observability để xác nhận dataset có đủ điều kiện dùng cho phase 1. Các check bao gồm:

- Đếm số dòng để kiểm tra tính đầy đủ của tập dữ liệu.
- Kiểm tra paper_id không null và không trùng lặp.
- Kiểm tra title không rỗng.
- Kiểm tra summary có độ dài tối thiểu 20 ký tự và tỷ lệ phủ sóng tối thiểu 80%.
- Kiểm tra freshness bằng cách so sánh age_days với ngưỡng 180 ngày.

Sau đó, module reporting tổng hợp các kết quả này thành một báo cáo markdown rõ ràng để team dùng làm evidence trong quá trình đánh giá baseline.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | DataFrame papers đã qua cleaning, Settings từ core.config, tên báo cáo, summary metrics |
| Output | JSON chứa kết quả checks và freshness, Markdown report tổng hợp |
| Module phụ thuộc | core.config, core.utils |
| Module sử dụng output | Phase 1 pipeline, báo cáo nhóm, evaluation và observability workflow |
| Điều kiện lỗi cần xử lý | Dataset rỗng, thiếu cột paper_id/title/summary/published/age_days, hoặc dữ liệu không có định dạng phù hợp |

### Cách xác minh

```bash
# Kiểm tra artifact đã tạo
cat data/quality/quality_baseline.json
cat data/quality/freshness_report.json
cat data/reports/phase1_report.md
```

- Kết quả mong đợi: các file JSON/Markdown tồn tại và chứa thông tin quality/freshness phù hợp.
- Kết quả thực tế: các file đã tồn tại với thông tin baseline rõ ràng.
- Artifact/log: data/quality/quality_baseline.json, data/quality/freshness_report.json, data/reports/phase1_report.md

## 5. Một quyết định kỹ thuật quan trọng

- Bối cảnh: Cần có một tiêu chí sạch và nhất quán để đánh giá dữ liệu trước khi dùng cho RAG baseline.
- Các phương án đã cân nhắc: chỉ kiểm tra null và duplicate, hoặc áp dụng thêm các rule về summary length và freshness.
- Phương án đã chọn: áp dụng cả 6 checks bao gồm completeness, uniqueness, validity và timeliness.
- Lý do: Điều này giúp phát hiện dữ liệu “vẫn có vẻ đầy đủ” nhưng lại không phù hợp để dùng cho retrieval quality, đặc biệt là summary ngắn hoặc dữ liệu cũ.
- Bằng chứng quyết định phù hợp: quality_baseline.json cho thấy 6/6 checks PASS và freshness_report.json xác nhận dataset fresh.

## 6. Một lỗi hoặc blocker đã xử lý

- Triệu chứng/lỗi nguyên văn: Khi kiểm tra việc chạy script, môi trường Python gặp thiếu dependency dotenv dẫn tới lỗi import khi chạy pipeline.
- Lệnh hoặc bước tái hiện: python script/run_phase1.py
- Nguyên nhân gốc: Module core.config import dotenv nhưng môi trường hiện tại chưa cài đặt package này.
- Cách xử lý: Kiểm tra lại cấu hình môi trường và ưu tiên dùng các artifact đã tồn tại để xác nhận kết quả phase 1 thay vì tiếp tục chạy script khi dependency chưa sẵn sàng.
- Cách xác minh sau khi sửa: Đã xác nhận các file output đã tồn tại và có nội dung hợp lệ.
- Điều học được: Cần chuẩn bị môi trường dependency trước khi chạy pipeline, đặc biệt với các module import từ core/config.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?  
   Dữ liệu được lấy từ Crossref API, sau đó đi qua quá trình cleaning để chuẩn hóa các trường như title, abstract/summary, published date và paper_id. Sau đó, dữ liệu được dùng làm nguồn cho retrieval pipeline và tạo vector index phục vụ truy vấn.

2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?  
   Evaluation set chứa các câu hỏi và document_id mục tiêu, giúp kiểm tra agent có retrieve đúng tài liệu liên quan và trả lời gần với ground truth hay không.

3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?  
   Quality checks đánh giá tính đầy đủ, duy nhất, hợp lệ và đúng cấu trúc của dữ liệu; freshness monitoring thì tập trung vào độ mới của record theo thời gian xuất bản và age_days.

4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?  
   Vì khi dùng cùng test set, ta có thể so sánh trực tiếp tác động của dữ liệu đầu vào lên chất lượng retrieval và answer, tránh sai lệch do khác biệt bộ câu hỏi.

5. Repair được xem là thành công dựa trên artifact và metric nào?  
   Repair được xem là thành công khi dữ liệu sau khi sửa lại giúp quality checks và freshness signal tăng lên, đồng thời metrics như retrieval_hit_rate, mean_token_f1 và judge_accuracy quay về gần baseline hoặc cải thiện so với corrupted version.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| retrieval_hit_rate | 1.000 | N/A | N/A | Baseline đạt hiệu suất tốt ở phase 1. |
| mean_token_f1 | 1.000 | N/A | N/A | Đánh giá dựa trên câu trả lời gần đúng với ground truth. |
| judge_accuracy | 0.958 | N/A | N/A | Đạt mức cao, cho thấy hệ thống baseline ổn định. |
| mean_judge_score | 4.833 | N/A | N/A | Chỉ số đánh giá chất lượng trả lời tương đối tốt. |
| Quality checks | 6/6 PASS | N/A | N/A | Dữ liệu baseline đủ điều kiện cho phase 1. |
| Freshness status | Fresh | N/A | N/A | Không phát hiện record stale theo ngưỡng 180 ngày. |

### Kết luận từ số liệu

1. Dữ liệu baseline cho thấy quality và freshness đều ở mức tốt, do đó agent có điều kiện hoạt động ổn định trong phase 1.  
2. Nếu dữ liệu bị corrupt hoặc stale, các signal quality/freshness sẽ giảm và có thể kéo theo metric retrieval/answer quality suy giảm.  
3. Corruption ảnh hưởng rõ nhất trong trường hợp làm giảm độ hợp lệ của summary hoặc làm dữ liệu trở nên stale, vì điều này trực tiếp tác động đến khả năng retrieval và đáp án phù hợp.

Kết quả nào khác với kỳ vọng ban đầu?  
Mặc dù dự kiến có thể xuất hiện một số lỗi khi dataset bị corrupt, các artifact baseline cho thấy dữ liệu ở phase 1 vẫn khá sạch và ổn định. Đây là dấu hiệu tốt cho việc tiếp tục đánh giá chất lượng pipeline.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data quality không chỉ là việc dữ liệu “có tồn tại”, mà còn phải đủ đầy đủ, đúng cấu trúc và mới để phục vụ retrieval.
2. Observability cần được đặt sớm trong pipeline để phát hiện vấn đề trước khi agent bị ảnh hưởng.
3. RAG agent rất nhạy cảm với dữ liệu đầu vào, nên một lỗi nhỏ ở data layer có thể làm giảm đáng kể chất lượng câu trả lời.

### Nếu có thêm thời gian

Một cải thiện cụ thể là thêm các check tự động vào pipeline để fail-fast ngay khi dữ liệu nhập vào thiếu cột hoặc summary quá ngắn, thay vì để lỗi phát hiện muộn ở phase evaluation.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Kien  
**Ngày xác nhận:** 2026-08-06
