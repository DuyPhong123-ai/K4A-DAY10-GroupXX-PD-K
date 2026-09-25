# Báo Cáo Cá Nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Trần Quốc Khánh |
| MSSV | 2A202602824 |
| Khóa/Lớp | K4/L3A|
| Tên nhóm | PD |
| Vai trò chính |Thành viên 4 - Observability & Evaluation Lead |
| Repository | https://github.com/DuyPhong123-ai/K4A-DAY10-PD |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Great Expectations Quality Gate và Freshness SLA | `src/observability/quality.py`: `run_data_quality_checks`, `build_freshness_report` | Clean/corrupted/repaired dataframe, `Settings` | Quality reports JSON, freshness report, trạng thái `success` | Hoàn thành |
| Benchmark Evaluation Set | `src/evaluation/testset.py`: `build_test_set` | Clean dataframe | `data/eval/test_set.json` gồm 10 câu hỏi và ground truth | Hoàn thành |
| Markdown reporting | `src/observability/reporting.py`: `generate_phase1_report`, `generate_corruption_report` | Metrics, quality results, freshness results | `phase1_report.md`, `corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Tích hợp và kiểm chứng output observability/evaluation vào pipeline | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` | Baseline và corruption/repair flow chạy end-to-end; report được sinh từ kết quả thực tế |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Dựng Quality Gate bằng GX 1.x | `src/observability/quality.py`, `data/quality/*_quality_report.json` | 6 checks; clean và repaired pass, corrupted fail | Chạy `run_phase1.py` và `run_corruption_flow.py` |
| Triển khai Freshness SLA | `build_freshness_report`, `data/quality/freshness_report.json` | Baseline: 1/24 stale, ratio 4.17%, pass; corrupted: 11/22 stale, ratio 50%, fail | Đọc quality report và console pipeline |
| Tạo benchmark test set | `src/evaluation/testset.py`, `data/eval/test_set.json` | 10 câu hỏi: summary 3, authors 3, date 2, categories 2 | Kiểm tra JSON và metrics evaluation |
| Sinh báo cáo Markdown | `src/observability/reporting.py`, `data/reports/` | Báo cáo baseline và bảng so sánh 3 trạng thái | Kiểm tra file report sau pipeline |

Output quan trọng nhất là bảng đối chiếu cho thấy dữ liệu bẩn làm Retrieval Hit Rate giảm từ `1.0000` xuống `0.6000`, Mean Token F1 giảm từ `1.0000` xuống `0.5741`, sau đó phục hồi về `1.0000` sau repair.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

RAG có thể vẫn trả lời dù dữ liệu đầu vào bị thiếu, trùng, rỗng hoặc cũ. Vì vậy pipeline cần một Quality Gate để phát hiện lỗi trước khi serving, Freshness SLA để phát hiện dữ liệu quá cũ, và một benchmark cố định để đo ảnh hưởng của corruption một cách công bằng.

### Cách triển khai

`run_data_quality_checks` tạo ephemeral context bằng API Great Expectations 1.x:

```python
context = gx.get_context(mode="ephemeral")
data_source = context.data_sources.add_pandas(name="papers_source")
data_asset = data_source.add_dataframe_asset(name="papers_asset")
batch_definition = data_asset.add_batch_definition_whole_dataframe("papers_batch")
batch = batch_definition.get_batch(batch_parameters={"dataframe": df})
```

Quality Gate kiểm tra row count, các cột bắt buộc không null, `paper_id` unique và độ dài `summary` tối thiểu 30 ký tự. Freshness được tính từ `age_days`; hệ thống fail khi tỷ lệ bản ghi có `age_days > 180` vượt quá 25%.

Test set được tạo deterministic từ 10 document đầu tiên của clean dataframe. Mỗi câu hỏi chứa `id`, `question_type`, `question`, `ground_truth` và `ground_truth_doc_ids`, vì vậy cùng một đề được dùng cho baseline, corrupted và repaired.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Clean dataframe có `paper_id`, `title`, `summary`, `authors_joined`, `published`, `categories_joined`, `age_days` |
| Output | Quality result JSON, freshness JSON, test set JSON và Markdown reports |
| Module phụ thuộc | `core.config`, `core.utils`, `ingestion.cleaning`, `evaluation.metrics` |
| Module sử dụng output | `pipelines.phase1`, `pipelines.corruption_flow`, Retrieval evaluator |
| Điều kiện lỗi cần xử lý | Null field, duplicate ID, summary quá ngắn, thiếu document, dữ liệu stale và corrupted dataframe |

### Cách xác minh

```powershell
$env:PYTHONPATH = "src"
& .venv\Scripts\python.exe script\run_phase1.py
& .venv\Scripts\python.exe script\run_corruption_flow.py
```

- **Kết quả mong đợi:** Baseline pass; corrupted fail Quality/Freshness và giảm metrics; repaired pass và phục hồi metrics.
- **Kết quả thực tế:** Đúng như mong đợi. Baseline và repaired đạt Hit Rate/F1/Judge `1.0000`; corrupted đạt Hit Rate `0.6000`, Token F1 `0.5741`, Quality/Freshness fail.
- **Artifact/log:** `data/quality/`, `data/eval/test_set.json`, `data/results/`, `data/reports/`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần dùng cùng một benchmark để so sánh ba trạng thái dữ liệu.
- **Các phương án đã cân nhắc:** Sinh test set mới cho từng trạng thái; hoặc sinh một test set cố định từ clean dataframe rồi tái sử dụng.
- **Phương án đã chọn:** Dùng một test set deterministic gồm 10 câu hỏi và giữ nguyên `ground_truth_doc_ids` cho cả ba lần đánh giá.
- **Lý do:** Test set cố định loại bỏ sai lệch do đề thi thay đổi, giúp chênh lệch metrics phản ánh corruption/repair thay vì phản ánh khác biệt của dữ liệu đánh giá.
- **Bằng chứng quyết định phù hợp:** Cả baseline và repaired đều đạt `retrieval_hit_rate = 1.0000`, `mean_token_f1 = 1.0000`; corrupted giảm rõ rệt trên cùng 10 câu hỏi.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'chromadb'` và `ModuleNotFoundError: No module named 'pipelines'` khi chạy bằng Python hệ thống.
- **Lệnh hoặc bước tái hiện:** Chạy `python script\run_phase1.py` khi chưa chọn virtual environment và chưa đặt `PYTHONPATH`.
- **Nguyên nhân gốc:** Dependencies được cài trong `.venv`, còn Python hệ thống không có package; project dùng layout `src` nên cần expose `src` khi chạy script.
- **Cách xử lý:** Cấu hình `.venv`, cài dependencies và chạy bằng `.venv\Scripts\python.exe` với `$env:PYTHONPATH = "src"`.
- **Cách xác minh sau khi sửa:** Smoke test in `Môi trường sẵn sàng`; cả hai pipeline chạy đến `[DONE]`.
- **Điều học được:** Cần xác nhận interpreter và import path trước khi kết luận pipeline bị lỗi logic.

Một cảnh báo phụ vẫn tồn tại: phần agent demo bị skip do `HumanMessage` không JSON serializable. Cảnh báo này không ảnh hưởng Quality Gate, benchmark metrics, corruption analysis hoặc repair flow.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu được lấy từ Crossref hoặc raw snapshot, lưu thành raw records, sau đó `cleaning.py` chuẩn hóa schema, loại duplicate, tính `age_days` và tạo `text_for_embedding`. Clean dataframe được quality check trước khi embedding và đưa vào ChromaDB.
2. Evaluation set chứa câu hỏi, đáp án chuẩn và document ID đúng. Retrieval hit được tính khi kết quả truy vấn chứa document ID chuẩn; Token F1 và judge accuracy đo chất lượng câu trả lời so với ground truth.
3. Quality checks kiểm tra tính hợp lệ của schema và nội dung tại một thời điểm cụ thể. Freshness monitoring tập trung vào độ cũ của dữ liệu và SLA tỷ lệ stale.
4. Cần dùng cùng test set để mọi thay đổi metrics chỉ phản ánh tác động của data corruption hoặc repair, không bị trộn với thay đổi đề đánh giá.
5. Repair thành công khi raw snapshot tạo lại clean dataset 24 dòng, quality/freshness chuyển về `PASS`, và các metrics phục hồi về baseline: Hit Rate/F1/Judge đều `1.0000`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000 | Corruption làm mất hoặc làm sai ngữ cảnh truy hồi; repair phục hồi hoàn toàn. |
| `mean_token_f1` | 1.0000 | 0.5741 | 1.0000 | Summary rỗng, noise và title bị truncate làm câu trả lời lệch ground truth. |
| `judge_accuracy` | 1.0000 | 0.6000 | 1.0000 | Chất lượng câu trả lời suy giảm tương ứng với retrieval. |
| `mean_judge_score` | 5.0 | 3.4 | 5.0 | Judge phản ánh rõ khoảng cách giữa clean và corrupted. |
| Quality checks | PASS, 6/6 | FAIL, 4/6 | PASS, 6/6 | Duplicate và summary ngắn bị phát hiện ở corrupted state. |
| Freshness status | PASS, 1/24 stale | FAIL, 11/22 stale | PASS, 1/24 stale | Stale date làm tỷ lệ stale tăng lên 50%, vượt SLA 25%. |

### Kết luận từ số liệu

1. **Data corruption** gồm drop record, blank summary, noise, truncate title, stale date và duplicate rows → Quality Gate còn `4/6`, Freshness từ `4.17%` lên `50%` và đều fail → Retrieval Hit Rate giảm còn `0.6000`, Token F1 còn `0.5741`.
2. **Repair từ raw snapshot** → dataset trở lại 24 dòng, Quality Gate `6/6`, Freshness `1/24 stale` và pass → Retrieval Hit Rate, Token F1 và Judge Accuracy phục hồi về `1.0000`.

Corruption ảnh hưởng rõ nhất đến observability là `stale_date`: 8 bản ghi bị lùi ngày khiến Freshness ratio đạt 50%, vượt gấp đôi SLA 25%. Về RAG, nhóm corruption kết hợp làm Hit Rate giảm 40 điểm phần trăm và Token F1 giảm 42.59 điểm phần trăm.

Kết quả đáng chú ý là dữ liệu corrupted chỉ còn 22 dòng thay vì 24 do kịch bản drop latest records, nhưng pipeline vẫn chạy và trả lời được. Đây chính là silent failure: hệ thống không crash, nhưng metrics và quality signals cho thấy dữ liệu không còn đáng tin cậy.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data pipeline cần bảo toàn raw snapshot để có thể tái tạo và repair idempotent, thay vì sửa trực tiếp trên dữ liệu đã biến đổi.
2. Quality Gate và Freshness SLA kiểm soát hai rủi ro khác nhau: một bên kiểm tra tính hợp lệ của record, một bên kiểm tra mức độ cập nhật của toàn bộ dataset.
3. RAG vẫn có thể trả lời khi dữ liệu lỗi, nên cần benchmark định lượng và quality observability để phát hiện silent failure.

### Nếu có thêm thời gian

Sẽ bổ sung test tự động cho từng expectation và kiểm tra idempotency bằng cách chạy repair hai lần rồi so sánh hash của clean artifacts. Ngoài ra, phần agent demo nên chuyển `HumanMessage` sang dạng serializable trước khi ghi JSON để loại bỏ cảnh báo còn lại.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Quốc Khánh  
**Ngày xác nhận:** 2026-09-25
