# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                 |
| ------------------ | ------------------------------------------------------------------------- |
| Họ và tên          | Nguyễn Duy Phong                                                   |
| MSSV               | 2A202602834                                      |
| Khóa/Lớp           | K4/L3A                                                 |
| Tên nhóm           | PD                                                          |
| Vai trò chính      | Thành viên 1(Trưởng nhóm) / Pipeline Integrator & Data Quality Architect     |
| Repository         | https://github.com/DuyPhong123-ai/K4A-DAY10-PD                |
| Ngày hoàn thành    | 2026-09-25                                                               |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Baseline Pipeline Orchestration** | [`src/pipelines/phase1.py`](../src/pipelines/phase1.py)<br>[`script/run_phase1.py`](../script/run_phase1.py) | Cấu hình `Settings`, raw records, hàm clean từ TV2, index từ TV3, quality checks từ TV4 | `baseline_metrics.json`, `baseline_answers.json`, `phase1_report.md`, collection `papers-baseline` | Hoàn thành |
| **Data Corruption Suite** | [`src/ingestion/corruption.py`](../src/ingestion/corruption.py)<br>`corrupt_clean_dataframe` | DataFrame sạch `papers_clean.json` | 6 kịch bản lỗi, DataFrame bị bẩn, `corruption_log.json`, `papers_clean_corrupted.csv/json` | Hoàn thành |
| **Corruption, Repair & Comparison Flow** | [`src/pipelines/corruption_flow.py`](../src/pipelines/corruption_flow.py)<br>[`script/run_corruption_flow.py`](../script/run_corruption_flow.py) | DataFrame bẩn, raw snapshot `crossref_records.json`, benchmark test set | `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_report.md`, collection `papers-repaired` | Hoàn thành |
| **ChromaDB Indexing Hotfix** | [`src/retrieval/index.py`](../src/retrieval/index.py)<br>`build` & `_build_documents` | DataFrame có trùng lặp bản ghi | Hỗ trợ nạp vector cho collection `papers-corrupted` mà không crash | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| **Tích hợp & Review PR** | Toàn bộ nhóm (PR #1 Duy, PR #2 Quang Đạt, PR #3 TQKhanh) | Rà soát schema interface, merge vào nhánh `main`, đảm bảo không xung đột thư viện. |
| **Xử lý mã hóa Windows Console** | Toàn bộ hệ thống chạy trên môi trường PowerShell/cmd | Thêm cơ chế `sys.stdout.reconfigure(encoding="utf-8")` và loại bỏ unicode emoji gây lỗi charmap cp1252. |
| **Nối tầng Observability** | TV4 (TQKhanh - Great Expectations 1.x) | Kết nối chốt kiểm định GX 1.x và Freshness SLA vào báo cáo Markdown tự động `corruption_report.md`. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Triển khai luồng Phase 1 Baseline End-to-End | [`src/pipelines/phase1.py`](../src/pipelines/phase1.py) | `data/results/baseline_metrics.json`<br>`data/reports/phase1_report.md` | Chạy lệnh `python script/run_phase1.py` đạt Hit Rate = 1.0000, F1 = 1.0000 |
| Cài đặt 6 kịch bản tiêm độc tố dữ liệu | [`src/ingestion/corruption.py`](../src/ingestion/corruption.py) | `data/results/corruption_log.json`<br>`data/clean/papers_clean_corrupted.json` | Log ghi nhận đủ 6 scenarios, DataFrame bẩn kích hoạt Quality Gate báo FAIL |
| Cài đặt luồng Phục hồi an toàn (Idempotent Repair) | [`src/pipelines/corruption_flow.py`](../src/pipelines/corruption_flow.py) | `data/results/repaired_metrics.json`<br>`data/reports/corruption_report.md` | Chạy `python script/run_corruption_flow.py` xuất bảng đối chiếu 3 trạng thái chứng minh RAG phục hồi 100% |

**Output tiêu biểu sở hữu trực tiếp:**  
Báo cáo so sánh đối chiếu 3 trạng thái [`data/reports/corruption_report.md`](../data/reports/corruption_report.md). Báo cáo này định lượng chi tiết hiện tượng **Silent Failure** khi dữ liệu bị tiêm lỗi (Retrieval Hit Rate sụt giảm nghiêm trọng từ 1.0000 xuống 0.6000, Token F1 giảm xuống 0.5741) và chứng minh năng lực tự phục hồi (Self-healing) đưa toàn bộ chỉ số về lại 1.0000.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Trong các hệ thống RAG thực tế, dữ liệu bẩn thường không làm crash hệ thống phần mềm mà gây ra **Silent Failure** (AI vẫn trả lời tự tin nhưng nội dung sai lệch hoàn toàn). Nhiệm vụ của tôi là thiết kế **Pipeline Orchestrator** đa tầng, vừa kiểm soát chất lượng dữ liệu sạch ở Baseline, vừa giả lập sự cố tiêm lỗi để kiểm chứng hệ thống cảnh báo sớm (Great Expectations 1.x + Freshness SLA), đồng thời hiện thực hóa cơ chế **Idempotent Repair** để hệ thống có khả năng tự sửa chữa và khôi phục về trạng thái sạch ban đầu.

### Cách triển khai
1. **Luồng Phase 1 (Baseline):**
   - Điều phối tuần tự: `fetch_source_records` $\rightarrow$ `build_clean_dataframe` $\rightarrow$ `run_data_quality_checks` (GX 1.x) $\rightarrow$ `LocalEmbeddingIndex.build` $\rightarrow$ `evaluate_pipeline` $\rightarrow$ `generate_phase1_report`.
2. **Luồng Phase 2 (Corruption & Repair):**
   - Triển khai 6 kịch bản tiêm lỗi độc lập trong `corrupt_clean_dataframe`: Bỏ 20% bài mới nhất, xóa rỗng abstract, chèn noise token `### NOISE_INJECTION...`, cắt ngắn tiêu đề `< 8 chars`, lùi ngày xuất bản 365 ngày (kích hoạt Freshness SLA vi phạm > 25%), nhân đôi bản ghi (vi phạm Primary Key uniqueness).
   - Re-index tập dữ liệu bẩn vào collection ChromaDB riêng biệt `papers-corrupted` để đo lường độ suy giảm chất lượng truy vấn.
   - Kích hoạt **Idempotent Repair**: Đọc trực tiếp từ bản lưu trữ thô bất biến `data/raw/crossref_records.json`, tái tạo hoàn toàn DataFrame sạch, nạp vào collection `papers-repaired` và chạy đối chiếu 3 trạng thái.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | Dữ liệu raw snapshot `crossref_records.json`, file clean dataframe `papers_clean.json`, benchmark test set `test_set.json` |
| **Output** | `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_log.json`, `corruption_report.md` |
| **Module phụ thuộc** | `ingestion.crossref`, `ingestion.cleaning`, `retrieval.index`, `observability.quality`, `evaluation.metrics` |
| **Module sử dụng output** | Dashboard báo cáo, bài thuyết trình Live Demo Checkpoint 6 |
| **Điều kiện lỗi cần xử lý** | Dữ liệu bẩn có trùng `paper_id` khi nạp vào vector store, lỗi encoding font console Windows, fallback offline khi API Crossref bị 429 |

### Cách xác minh thực tế

```bash
# 1. Chạy toàn tuyến Baseline (Phase 1)
python script/run_phase1.py

# 2. Chạy toàn tuyến Tiêm lỗi, Phục hồi và Đối chiếu (Phase 2)
python script/run_corruption_flow.py
```
- **Kết quả mong đợi:** Cả 2 script chạy với exit code 0; xuất hiện đầy đủ 3 collection ChromaDB; bảng Markdown `corruption_report.md` có đầy đủ 3 cột so sánh.
- **Kết quả thực tế:** Tất cả chỉ số Baseline và Repaired đều đạt 1.0000; Corrupted bị suy giảm còn 0.6000 Hit Rate và 0.5741 Token F1; Quality Gate bắt trúng 100% lỗi vi phạm.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi thực hiện bước phục hồi dữ liệu (Repair), cần lựa chọn phương pháp xử lý dữ liệu bị hỏng.
- **Các phương án đã cân nhắc:**
  - *Phương án 1 (Heuristic Patching):* Viết hàm tìm và xóa các dòng trùng lặp, lọc bỏ các dòng có tiêu đề ngắn hoặc xóa token rác trực tiếp trên DataFrame lỗi.
  - *Phương án 2 (Idempotent Raw Rebuild - Được chọn):* Khôi phục toàn diện từ nguồn dữ liệu thô ban đầu (`data/raw/crossref_records.json`) thông qua pipeline làm sạch chuẩn hóa.
- **Lý do chọn:** Phương án 1 tiềm ẩn nguy cơ tích lũy lỗi ngầm (Technical Debt), không đảm bảo được tính toàn vẹn (Data Lineage) khi gặp các lỗi phức tạp như mất mát bản ghi mới. Phương án 2 tuân thủ chặt chẽ nguyên lý **Idempotency** trong Data Engineering: Bất kể dữ liệu serving bị tàn phá nặng nề đến đâu, chỉ cần chạy lại luồng từ Raw snapshot, hệ thống luôn tái tạo được 100% dữ liệu chuẩn sạch mà không cần can thiệp thủ công.
- **Bằng chứng phù hợp:** Chỉ số sau phục hồi (`repaired_metrics.json`) đạt chính xác tuyệt đối bằng 100% chỉ số của Baseline (Hit Rate = 1.0000, F1 = 1.0000, Quality Gate: 6/6 checks PASS).

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  ValueError: Duplicate paper_id cannot be indexed: 10.1145/3637528.3671802
  ```
- **Lệnh tái hiện:** `python script/run_corruption_flow.py` (tại bước index dữ liệu bị tiêm lỗi duplicate rows vào ChromaDB).
- **Nguyên nhân gốc:** Hàm `_build_documents` trong [`src/retrieval/index.py`](../src/retrieval/index.py) có đoạn kiểm tra nghiêm ngặt `if normalized_paper_id in seen_paper_ids: raise ValueError(...)`. Khi luồng tiêm lỗi cố tình nhân đôi dòng dữ liệu để thử thách hệ thống, hàm này ném ngoại lệ làm dừng pipeline thay vì cho phép lưu vector để đánh giá suy giảm.
- **Cách xử lý:** Bổ sung tham số `allow_duplicates: bool = False` cho `_build_documents` và `build`. Khi collection đích là `papers-corrupted`, hệ thống tự động cho phép nạp các bản ghi trùng lặp (vì ChromaDB sử dụng `record_id` dạng `f"{paper_id}::{index}"` nên không bị trùng key trong database).
- **Cách xác minh sau khi sửa:** Chạy lại `python script/run_corruption_flow.py`, collection `papers-corrupted` được nạp thành công với 22 tài liệu và đo lường chính xác sự suy giảm điểm số của AI.
- **Điều học được:** Khi xây dựng testbed mô phỏng sự cố (Chaos Engineering), các tầng downstream (Vector DB, Serving Layer) cần có cơ chế linh hoạt để ghi nhận và đánh giá được tác động của dữ liệu lỗi thay vì chỉ chặn lỗi ở tầng application code.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index:**  
   Crossref REST API trả về payload JSON $\rightarrow$ parse thành `PaperRecord` và lưu bản sao lưu gốc vào `data/raw/` $\rightarrow$ qua `build_clean_dataframe` để làm sạch HTML/JATS tags, chuẩn hóa khoảng trắng, tính `age_days` và ghép trường `text_for_embedding` $\rightarrow$ kiểm tra qua chốt kiểm dịch Great Expectations 1.x $\rightarrow$ đưa vào mô hình `all-MiniLM-L6-v2` chuyển đổi thành vector 384 chiều $\rightarrow$ lưu vào ChromaDB collection kèm metadata.

2. **Cách dùng Evaluation Set và Ground-truth IDs đo chất lượng:**  
   Bộ 10 câu hỏi test đại diện cho 4 tác vụ nghiệp vụ. Khi Agent nhận câu hỏi, bộ tìm kiếm sẽ trả về top $K$ tài liệu liên quan (`retrieved_doc_ids`). Nếu ID của tài liệu chuẩn (`ground_truth_doc_ids`) nằm trong danh sách này, ta ghi nhận **Retrieval Hit**. Câu trả lời sinh ra được so khớp từng từ với câu trả lời mẫu (`ground_truth`) để tính **Token F1**, đồng thời được chấm điểm qua LLM Judge.

3. **Sự khác biệt giữa Quality Checks và Freshness Monitoring:**  
   - *Quality Checks (GX 1.x):* Đảm bảo tính toàn vẹn về mặt cú pháp và hình thức dữ liệu (schema validation, không bị null, không bị trùng khóa chính, độ dài tối thiểu của văn bản).
   - *Freshness Monitoring (SLA):* Đảm bảo tính đúng đắn về mặt ngữ cảnh thời gian. Dữ liệu dù sạch 100% nhưng nếu quá cũ (`age_days > 180` chiếm > 25%) thì câu trả lời của AI sẽ bị lỗi thời (Stale knowledge), gây ra nguy cơ Silent Failure.

4. **Tại sao phải dùng chung một Test Set cho cả 3 trạng thái?**  
   Để đảm bảo tính khách quan và khoa học của thực nghiệm (A/B Testing chuẩn hóa). Việc giữ cố định "đề thi" giúp ta cô lập hoàn toàn biến số: Mọi sự thay đổi về điểm số chỉ bắt nguồn từ sự thay đổi của chất lượng dữ liệu trong kho vector, không bị nhiễu bởi độ khó của câu hỏi.

5. **Tiêu chuẩn đánh giá Repair thành công:**  
   Repair được coi là thành công khi thỏa mãn đồng thời 2 điều kiện:
   - *Observability Signals:* Báo cáo Great Expectations 1.x chuyển trạng thái từ FAIL sang PASS (6/6 checks đạt) và Freshness SLA phục hồi về `is_fresh = True`.
   - *RAG Performance Metrics:* Retrieval Hit Rate và Token F1 phục hồi từ mức suy giảm (0.6000 / 0.5741) trở về tương đương hoặc bằng mức Baseline ban đầu (1.0000).

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | **1.0000** | **0.6000** | **1.0000** | Mất bản ghi mới và cắt ngắn tiêu đề làm bộ tìm kiếm trích xuất sai 40% câu hỏi. |
| `mean_token_f1` | **1.0000** | **0.5741** | **1.0000** | Tóm tắt bị xóa trắng và chèn ký tự rác làm câu trả lời của AI bị méo mó. |
| `judge_accuracy` | **1.0000** | **0.6000** | **1.0000** | Tỷ lệ câu trả lời đạt yêu cầu giảm tương ứng với tỷ lệ mất mát ngữ cảnh. |
| `mean_judge_score` | **5.0000** | **3.2000** | **5.0000** | Điểm số chất lượng câu trả lời bị tụt dốc rõ rệt khi dữ liệu bẩn. |
| **Quality checks (GX 1.x)**| **PASS (6/6)** | **FAIL (4/6)** | **PASS (6/6)** | Bắt trúng lỗi trùng lặp `paper_id` và lỗi độ dài tóm tắt `< 30 chars`. |
| **Freshness SLA** | **PASS (4.17%)** | **FAIL (50.0%)** | **PASS (4.17%)** | Bắt trúng sự cố 11/22 bài báo bị quá hạn 180 ngày do bị lùi ngày xuất bản. |

### Kết luận từ số liệu

1. **Chuỗi sự cố:**  
   Tiêm lỗi xóa abstract & nhân đôi dòng $\rightarrow$ Quality Gate GX 1.x chuyển sang FAIL (4/6 checks) & Freshness SLA chuyển sang FAIL $\rightarrow$ Retrieval Hit Rate sụt giảm từ 1.0000 xuống 0.6000 và F1 giảm xuống 0.5741.
2. **Chuỗi phục hồi:**  
   Kích hoạt Idempotent Repair tái tạo từ raw records $\rightarrow$ Quality Gate và Freshness SLA phục hồi PASS 100% $\rightarrow$ Retrieval Hit Rate và F1 hồi phục hoàn hảo về 1.0000.

**Dạng lỗi ảnh hưởng nặng nhất:**  
Lỗi **Drop latest records** và **Blank summary** gây ảnh hưởng nghiêm trọng nhất vì nó triệt tiêu hoàn toàn ngữ cảnh thông tin. Khi tài liệu không còn trong cơ sở dữ liệu, bộ tìm kiếm buộc phải lấy các tài liệu không liên quan, dẫn đến việc AI trả về thông tin rác hoặc bị ảo giác.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Garbage In $\rightarrow$ Garbage Out:** Chất lượng của RAG Agent phụ thuộc 80% vào tính chuẩn xác của Data Pipeline, mô hình ngôn ngữ dù tân tiến đến đâu cũng bất lực trước dữ liệu sai lệch.
2. **Sức mạnh của Data Quality Gate:** Việc triển khai Great Expectations 1.x như một chốt chặn kiểm dịch trước khi nạp dữ liệu vào Vector Store là giải pháp cứu cánh để ngăn chặn triệt để hiện tượng Silent Failure.
3. **Triết lý Idempotency:** Thiết kế pipeline có khả năng chạy lại an toàn từ nguồn Raw Snapshot là chìa khóa vàng cho các hệ thống tự phục hồi (Self-healing systems) trong môi trường sản xuất.

### Hướng cải thiện nếu có thêm thời gian
Xây dựng một **Automated Rollback Webhook**: Khi Data Quality Gate hoặc Freshness SLA phát hiện vi phạm, hệ thống sẽ tự động gửi cảnh báo qua Slack/Telegram và lập tức rollback collection ChromaDB về phiên bản snapshot ổn định gần nhất mà không cần kỹ sư phải kích hoạt lệnh chạy lại bằng tay.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Người báo cáo:** Duy Phong  
**Ngày xác nhận:** 2026-09-25
