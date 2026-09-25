# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `PD`
- **Mã Nhóm / Lớp:** `K4-L3A`
- **Tên Repository Nộp Bài:** `https://github.com/DuyPhong123-ai/K4A-DAY10-PD`

---

## 1. Danh sách thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Nguyễn Duy Phong | 2A202602834 | phonghaha513@gmail.com | Trưởng nhóm / Pipeline Integrator (`core/`, `phase1.py`, `corruption_flow.py`) | [`report/2A202602834_NguyenDuyPhong.md`](../report/2A202602834_NguyenDuyPhong.md) |
| 2 | Nguyễn Thành Duy | 2A202602804 | duynguy3n2916@gmail.com | Data Foundation & Recovery (`crossref.py`, `cleaning.py`, raw data, self-healing) | [`report/2A202602804_NguyenThanhDuy.md`](../report/2A202602804_NguyenThanhDuy.md) |
| 3 | Phạm Quang Đạt | 2A202602704 | phamqdat99@gmail.com | RAG & Vector Index (`retrieval/index.py`, `embeddings.py`, ChromaDB, QA logic) | [`report/2A202602704_PhamQuangDat.md`](../report/2A202602704_PhamQuangDat.md) |
| 4 | Trần Quốc Khánh | 2A202602824 | trankhanh.ai.ptit@gmail.com | Observability & Evaluation (`quality.py` GX 1.x, `testset.py`, reporting) | [`report/2A202602824_TranQuocKhanh.md`](../report/2A202602824_TranQuocKhanh.md) |

---

## 2. Chi tiết đóng góp của từng thành viên

### Nguyễn Duy Phong — 2A202602834
- **Vai trò:** Trưởng nhóm / Pipeline Integrator & Data Quality Architect (Member 1).
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập cấu trúc dự án, cấu hình hệ thống `src/core/config.py`, và quản lý thư mục artifact `src/core/utils.py`.
  - Kết nối luồng thực thi Phase 1 Baseline trong `src/pipelines/phase1.py` và `script/run_phase1.py`.
  - Cài đặt 6 kịch bản tiêm độc tố dữ liệu trong `src/ingestion/corruption.py`.
  - Điều phối luồng Phase 2 mô phỏng sự cố, sửa chữa Idempotent Repair và xuất báo cáo so sánh trong `src/pipelines/corruption_flow.py` và `script/run_corruption_flow.py`.
  - Hotfix cơ chế nạp ChromaDB (`_build_documents`) để cho phép nạp dữ liệu bị nhân đôi (`allow_duplicates=True`) phục vụ kiểm thử sự cố.
  - Tích hợp Git workflow, review Pull Requests (#1, #2, #3) và đồng bộ nhánh `main`.
- **Điều học được / Đóng góp chính:**
  - Nắm vững kiến trúc Idempotent Pipeline đa tầng, khả năng điều phối luồng dữ liệu lớn và cơ chế phòng chống Silent Failure trong RAG.

### Nguyễn Thành Duy — 2A202602804
- **Vai trò:** Data Foundation, Data Cleaning, Lineage & Recovery Specialist (Member 2).
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module Ingestion thu thập dữ liệu Crossref REST API với cơ chế tự động Fallback offline snapshot trong `src/ingestion/crossref.py`.
  - Cài đặt pipeline tiền xử lý và làm sạch dữ liệu trong `src/ingestion/cleaning.py`: khử thẻ XML/HTML JATS, chuẩn hóa khoảng trắng, tính toán `age_days` chuẩn UTC, ghép chuỗi trường ngữ cảnh `text_for_embedding`.
  - Triển khai cơ chế truy vết nguồn gốc (Data Lineage) và phục hồi Idempotent Repair từ raw records gốc `data/raw/crossref_records.json`.
  - Xây dựng thêm bộ 3 hạng mục Bonus (+10 điểm):
    - **B1:** Web Dashboard trực quan hóa Data Quality & Drift Monitor (`dashboard/index.html` + `script/run_dashboard.py`).
    - **B2:** Pipeline tự động phục hồi lỗi Auto-Repair / Self-Healing (`src/pipelines/self_healing_pipeline.py` + `script/run_self_healing.py`).
    - **B3:** Bộ kiểm thử tự động toàn diện Pytest Suite (`tests/` + `script/run_tests.py` + `.github/workflows/test.yml`).
- **Điều học được / Đóng góp chính:**
  - Nhận thức sâu sắc rằng chất lượng của RAG bắt nguồn từ tầng dữ liệu ("Garbage In, Garbage Out"). Kỹ thuật lưu trữ snapshot bất biến (Raw Ingestion Snapshot) là chìa khóa để triển khai kiến trúc tự phục hồi an toàn trong môi trường sản xuất.

### Phạm Quang Đạt — 2A202602704
- **Vai trò:** RAG & Vector Index Specialist (Member 3).
- **Công việc chi tiết đã hoàn thành:**
  - Tích hợp mô hình embedding cục bộ `sentence-transformers/all-MiniLM-L6-v2` chuẩn hóa vector L2 384 chiều trong `src/retrieval/embeddings.py`.
  - Xây dựng lớp lưu trữ vector ChromaDB `LocalEmbeddingIndex` (`src/retrieval/index.py`) hỗ trợ quản lý 3 collection biệt lập: `papers-baseline`, `papers-corrupted`, `papers-repaired`.
  - Cài đặt bộ tìm kiếm ngữ nghĩa (Semantic Search) với Cosine Similarity và Exact Lookup theo DOI / title.
  - Xây dựng QA Execution Engine (`src/retrieval/qa.py`) và QA Agent có tool-calling (`src/retrieval/agent.py`) để sinh câu trả lời đối chiếu với ground truth.
- **Điều học được / Đóng góp chính:**
  - Hiểu rõ cách không gian embedding bị méo mó khi dữ liệu đầu vào chứa chuỗi rác (`NOISE_INJECTION`) hoặc tiêu đề bị cắt cụt, dẫn đến việc bộ tìm kiếm trích xuất sai văn bản gốc.

### Trần Quốc Khánh — 2A202602824
- **Vai trò:** Observability & Evaluation Lead (Member 4).
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập Data Quality Gate bằng **Great Expectations 1.x** với 6 expectation cốt lõi (`src/observability/quality.py`): kiểm tra null, tính duy nhất của `paper_id`, độ dài `summary >= 30`, miền giá trị của `age_days >= 0`.
  - Triển khai giám sát Freshness SLA cảnh báo tài liệu lỗi thời (`age_days > 180` vượt ngưỡng 25%).
  - Xây dựng Benchmark Test Set gồm 10 câu hỏi chuẩn hóa đại diện 4 tác vụ (`summary`, `authors`, `date`, `categories`) trong `src/evaluation/testset.py`.
  - Xây dựng công cụ sinh báo cáo Markdown tự động `src/observability/reporting.py`, đo lường chỉ số Retrieval Hit Rate, Mean Token F1 và LLM Judge.
- **Điều học được / Đóng góp chính:**
  - Nắm vững vai trò của chốt chặn Data Observability như một hệ thống kiểm dịch bắt buộc trước khi nạp dữ liệu vào Vector DB, giúp phát hiện sớm các sự cố dữ liệu mà không cần chờ người dùng cuối phát hiện.
