# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                 |
| ------------------ | ------------------------------------------------------------------------ |
| Họ và tên          | Nguyễn Thành Duy                                                         |
| MSSV               | 2A202602804                                                              |
| Khóa/Lớp           | K4/L3A                                           |
| Tên nhóm           | PD                                              |
| Vai trò chính      | Thành viên 2 — Data Foundation Owner (Kỹ sư Dữ liệu Nền tảng & Phục hồi)  |
| Repository         | https://github.com/DuyPhong123-ai/K4A-DAY10-PD                |
| Ngày hoàn thành    | 2026-09-25                                                               |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :---: |
| **Raw Ingestion & Lineage** | `src/ingestion/crossref.py`<br>- `parse_crossref_payload()`<br>- `fetch_source_records()`<br>- `load_raw_records()` | Crossref REST API hoặc snapshot local `data/raw/crossref_response.json` | `data/raw/crossref_response.json`<br>`data/raw/crossref_records.json` (24 records) | **Hoàn thành** |
| **Data Cleaning & Modeling** | `src/ingestion/cleaning.py`<br>- `build_clean_dataframe()` | Danh sách `PaperRecord` từ raw data và `run_date` | `data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json` (24 dòng sạch) | **Hoàn thành** |
| **Idempotent Recovery Logic** | `src/ingestion/crossref.py`<br>`src/ingestion/cleaning.py` | Bản sao lưu `data/raw/crossref_records.json` | Khôi phục 100% dữ liệu sạch cho luồng Repair của Phase 2 | **Hoàn thành** |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| **Quản lý Git & Điều phối nhánh** | Toàn bộ nhóm | Hỗ trợ nhóm quy chuẩn phân chia nhánh làm việc (`duy`, `quangdat`, `tqkhanh`), tạo và review Pull Request, giải quyết xung đột khi merge vào nhánh `main`. |
| **Xử lý sự cố môi trường & Run-time** | Toàn bộ nhóm | Hỗ trợ khắc phục lỗi môi trường Python không tương thích trên máy Windows, cấu hình lại `.venv` và fix lỗi font/encoding UTF-8 trên PowerShell khi in kết quả. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Thu thập metadata Crossref theo cơ chế Dual-Mode | `src/ingestion/crossref.py` | `data/raw/crossref_records.json` (24 bài) | Chạy lệnh CP0 in ra: `Tín hiệu hoàn thành: Đã tải 24 bài báo` |
| Làm sạch, tính `age_days`, ghép `text_for_embedding` | `src/ingestion/cleaning.py` | `data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json` | Chạy lệnh CP1 in ra: `Tín hiệu hoàn thành: Clean thành công 24 dòng` |
| Đóng góp vào nhánh chung của nhóm | Pull Request #1 trên GitHub | Merge thành công vào nhánh `main` qua commit `9e0eaa2` | Kiểm tra Git log và GitHub Insights Contributors |

**Mô tả cụ thể output bàn giao:**  
Tôi đã bàn giao tập dữ liệu sạch gồm 24 bài báo khoa học học thuật mới nhất về chủ đề *Agentic RAG & Large Language Models*. Dữ liệu có cấu trúc schema 16 cột hoàn chỉnh, loại bỏ hoàn toàn các thẻ JATS XML rác, khử trùng lặp theo khóa chính `paper_id` (DOI) và sinh ra trường ngữ cảnh tối ưu `text_for_embedding` phục vụ trực tiếp cho quá trình Indexing của Thành viên 3.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Trong các hệ thống RAG thực tế, lỗi "Silent Failure" thường xuất phát từ việc dữ liệu đầu vào bị bẩn, thiếu tóm tắt, dính thẻ HTML/XML rác hoặc bị lỗi thời. Nếu không lưu bản thô nguyên bản (**Raw Preservation**) và không làm sạch chuẩn chỉnh, AI Agent sẽ bị "ngộ độc dữ liệu" dẫn tới việc trả lời sai sự thật (hallucination).

### Cách triển khai
1. **Bóc tách và lọc thẻ XML:** Viết Regex `re.sub(r"<[^>]+>", "", raw_abstract)` để dọn sạch các thẻ `<jats:p>`, `</jats:p>`, `<b>`, `<i>` từ Crossref abstract.
2. **Cơ chế Dual-Mode (Online & Offline Fallback):** Viết logic tự động bắt lỗi mạng hoặc mã lỗi `429 Too Many Requests` để chuyển sang nạp snapshot `crossref_response.json`, giúp pipeline không bao giờ bị dừng đột ngột.
3. **Tính tuổi thọ dữ liệu:** `age_days = (run_date.date() - published_date.date()).days` để hỗ trợ chốt kiểm định Freshness SLA (>180 ngày).
4. **Cấu trúc hóa `text_for_embedding`:** Định dạng thống nhất 5 phần:
   ```text
   Title: <Tiêu đề>
   Authors: <Danh sách tác giả>
   Published: <Ngày xuất bản>
   Categories: <Chuyên ngành>
   Summary: <Tóm tắt>
   ```

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | JSON payload từ `https://api.crossref.org/works` hoặc local file `data/raw/crossref_response.json`. |
| **Output** | Danh sách 24 đối tượng `PaperRecord`, DataFrame sạch lưu tại `data/clean/papers_clean.csv` và `.json`. |
| **Module phụ thuộc** | `core.config.Settings`, `core.utils`. |
| **Module sử dụng output** | `retrieval.index` (TV3), `observability.quality` (TV4), `evaluation.testset` (TV4), `pipelines.phase1` (TV1). |
| **Điều kiện lỗi cần xử lý** | Mất mạng, API rate-limit 429, mảng ngày tháng `date-parts` bị khuyết thiếu, bản ghi trùng lặp DOI. |

### Cách xác minh

```bash
$env:PYTHONIOENCODING="utf-8"
python -c "import sys; sys.path.insert(0, 'src'); from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
python -c "import sys; sys.path.insert(0, 'src'); from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
```

- **Kết quả mong đợi:** In ra `Tín hiệu hoàn thành: Đã tải 24 bài báo` và `Tín hiệu hoàn thành: Clean thành công 24 dòng`.
- **Kết quả thực tế:** Hoàn toàn trùng khớp, exit code 0.
- **Artifact:** `data/raw/crossref_records.json`, `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quyết định kiến trúc nạp dữ liệu: Nên cào trực tiếp từ mạng và làm sạch ngay trên RAM, hay lưu tách biệt 2 tầng file raw trước khi làm sạch?
- **Các phương án đã cân nhắc:**
  - *Phương án 1:* Cào trực tiếp từ API và xuất thẳng ra `papers_clean.csv`, không lưu trung gian.
  - *Phương án 2:* Kiến trúc 2 tầng (Dual-stage Lineage): Lưu nguyên gốc API response vào `data/raw/crossref_response.json`, parse thành `data/raw/crossref_records.json`, sau đó mới đọc lên để clean.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** 
  1. Bảo toàn cội nguồn dữ liệu (**Data Lineage / Raw Preservation**): Khi bước làm sạch phía sau cần thay đổi logic, ta có thể chạy lại bất cứ lúc nào từ bản raw mà không tốn chi phí gọi API hay sợ bị khóa IP.
  2. Tạo nền tảng cho tính **Idempotent Repair**: Khi hệ thống bị tiêm lỗi ở Pha 2, cơ chế phục hồi chỉ việc đọc lại từ `crossref_records.json` là tái tạo được 100% dữ liệu sạch mà không phụ thuộc vào Internet.
- **Bằng chứng quyết định phù hợp:** Toàn bộ quá trình chạy kiểm thử và tự phục hồi sau đó đều diễn ra ổn định với thời gian xử lý < 1 giây từ local raw snapshot.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  ERROR: Package 'day10-data-observability-lab-student' requires a different Python: 3.10.11 not in '<3.14,>=3.11'
  UnicodeEncodeError: 'charmap' codec can't encode character '\u1ec7' in position 6: character maps to <undefined>
  ```
- **Lệnh hoặc bước tái hiện:** Chạy `python -m pip install -e .` và chạy script in chuỗi tiếng Việt trên Windows PowerShell mặc định.
- **Nguyên nhân gốc:** 
  1. Môi trường Python mặc định trên máy là bản 3.10.11, trong khi dự án cấu hình yêu cầu nghiêm ngặt Python `>=3.11, <3.14`.
  2. Bảng mã console mặc định của PowerShell là `cp1252` không hỗ trợ hiển thị ký tự tiếng Việt có dấu.
- **Cách xử lý:** 
  1. Dùng trình quản lý `py -3.13 -m venv .venv` để tạo lại môi trường ảo với Python 3.13.14 tương thích.
  2. Thiết lập biến môi trường `$env:PYTHONIOENCODING="utf-8"` trước khi thực thi script Python.
- **Cách xác minh sau khi sửa:** Lệnh cài đặt hoàn tất không còn lỗi phân giải phiên bản; console in ra chính xác đầy đủ chuỗi có dấu: `Tín hiệu hoàn thành: Đã tải 24 bài báo`.
- **Điều học được:** Luôn kiểm tra ràng buộc phiên bản trong `pyproject.toml` trước khi khởi tạo venv và chủ động cấu hình encoding UTF-8 khi làm việc trên môi trường Windows.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**  
   Dữ liệu thô từ Crossref API $\rightarrow$ lưu vào `crossref_response.json` $\rightarrow$ parse thành `crossref_records.json` $\rightarrow$ làm sạch và tạo `text_for_embedding` trong `papers_clean.csv` $\rightarrow$ mô hình `all-MiniLM-L6-v2` nhúng thành vector 384 chiều $\rightarrow$ lưu trữ vĩnh viễn trong ChromaDB collection `papers-baseline`.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**  
   Bộ test gồm 10 câu hỏi chuẩn. Với mỗi câu hỏi, ta đối chiếu các tài liệu được truy xuất (`retrieved_doc_ids`) với tài liệu chuẩn (`ground_truth_doc_ids`). Nếu có mặt tài liệu chuẩn trong top-k thì tính là Retrieval Hit (`Hit Rate`). Câu trả lời của AI sau đó được so sánh với `ground_truth` để tính `Token F1` và điểm số giám khảo `LLM-as-a-Judge`.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**  
   - `Quality checks` (GX 1.x): Kiểm soát **tính toàn vẹn về cấu trúc và cú pháp dữ liệu** (schema, null values, uniqueness, độ dài tối thiểu của tóm tắt).
   - `Freshness monitoring`: Giám sát **độ tươi mới về mặt nghiệp vụ theo thời gian**, cảnh báo khi dữ liệu bị lỗi thời (bài báo cũ hơn 180 ngày vượt quá tỷ lệ 25% cho phép) gây nguy cơ tư vấn kiến thức cũ rích.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**  
   Để đảm bảo **tính khách quan và tính khoa học trong thực nghiệm** (Controlled Experiment). Chỉ khi giữ nguyên một "đề thi" cố định 10 câu hỏi, ta mới đo lường chính xác mức độ suy giảm do dữ liệu bẩn và chứng minh sự phục hồi phong độ của AI sau khi sửa chữa.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**  
   Dựa trên:
   - File artifact: Báo cáo `data/reports/corruption_report.md` và `data/results/repaired_metrics.json`.
   - Metric: `retrieval_hit_rate` và `mean_token_f1` hồi phục về mức tương đương hoặc bằng Baseline; chốt kiểm dịch Great Expectations và Freshness SLA chuyển lại trạng thái `PASS` và `FRESH`.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | **100.0%** (1.0000) | **60.0%** (0.6000) | **100.0%** (1.0000) | Bị sụt giảm 40% do drop 20% bài mới nhất và cắt ngắn tiêu đề làm cơ chế tra cứu bị hỏng; sau khi Repair từ raw data đã hồi phục hoàn toàn 100%. |
| `mean_token_f1` | **1.0000** | **0.5741** | **1.0000** | Xóa rỗng summary và bơm ký tự rác làm AI không còn context chuẩn để trích xuất từ khóa, chỉ số giảm mạnh từ 1.0 xuống 0.5741; hồi phục trọn vẹn 1.0 sau Repair. |
| `judge_accuracy` | **100.0%** (1.0000) | **60.0%** (0.6000) | **100.0%** (1.0000) | Minh chứng rõ nét cho Silent Failure: AI trả lời sai ngữ nghĩa ở 4/10 câu hỏi khi dữ liệu bị lỗi; lấy lại độ chuẩn xác tuyệt đối sau khôi phục. |
| `mean_judge_score` | **5.00** / 5.0 | **3.20** / 5.0 | **5.00** / 5.0 | Điểm đánh giá chất lượng câu trả lời từ giám khảo giảm sâu xuống 3.20 và phục hồi hoàn toàn về mức 5.00 điểm tối đa. |
| Quality checks (GX 1.x) | **PASS** (6/6) | **FAIL** (4/6) | **PASS** (6/6) | Chốt kiểm dịch phát hiện ngay 2 Expectation vi phạm: duplicate ID và summary rỗng (<30 ký tự); sau Repair vượt qua 6/6 checks. |
| Freshness status | **FRESH** (ratio 0.04) | **STALE** (ratio 0.50) | **FRESH** (ratio 0.04) | Báo động SLA kích hoạt ngay khi 11/22 dòng bị lùi ngày 365 ngày (tỷ lệ 50% > ngưỡng 25%); sau Repair tỷ lệ stale chỉ còn 4.17%, đạt SLA. |

### Kết luận từ số liệu
1. **Chuỗi suy giảm:** Data corruption (drop bài, xóa summary, lùi ngày) $\rightarrow$ GX Gate báo `FAIL` và Freshness báo `STALE` $\rightarrow$ Retrieval Hit Rate và Token F1 sụt giảm nghiêm trọng $\rightarrow$ Chứng minh hiện tượng **Silent Failure**.
2. **Chuỗi phục hồi:** Idempotent Repair từ `crossref_records.json` $\rightarrow$ GX Gate trở lại `PASS`, Freshness trở lại `FRESH` $\rightarrow$ Agent Metrics lấy lại 100% phong độ ban đầu.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Về Data Pipeline:** Tầm quan trọng tối thượng của nguyên tắc **Raw Preservation** và tính **Idempotent**; dữ liệu sạch là xương sống quyết định chất lượng của mọi sản phẩm AI.
2. **Về Data Observability:** Cách thiết lập chốt kiểm dịch tự động với **Great Expectations 1.x** để ngăn chặn dữ liệu xấu trước khi kịp lọt vào Vector Store.
3. **Về RAG Agent:** Hiểu rõ bản chất hiểm họa **Silent Failure** — AI không báo lỗi mà vẫn tự tin trả lời bịa đặt khi dữ liệu nền tảng bị thoái hóa.

### Nếu có thêm thời gian
Tôi muốn xây dựng thêm một **Auto-Healing Worker (Tự động phục hồi theo sự kiện)**: Khi Quality Gate hoặc Freshness SLA phát hiện lỗi vi phạm ngưỡng, hệ thống sẽ tự động kích hoạt tiến trình làm sạch lại từ bản Raw và cập nhật Vector Index ngầm (Zero-downtime re-indexing) mà không cần con người can thiệp.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thành Duy  
**Ngày xác nhận:** 2026-09-25
