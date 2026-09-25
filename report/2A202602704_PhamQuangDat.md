# Báo cáo vai trò thành viên — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Phạm Quang Đạt (Pham Quang Dat) |
| MSSV | 2A202602704 |
| Khóa/Lớp | K4 — L3A |
| Tên nhóm | PD |
| Vai trò chính | Thành viên 3 — RAG & Agent Specialist |
| Repository | https://github.com/DuyPhong123-ai/K4A-DAY10-PD |
| Nhánh/commit đóng góp | `quangdat` / `b98dc1a` |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| MiniLM embedding | `src/retrieval/embeddings.py`, `MiniLMEmbeddings` | Danh sách `text_for_embedding`; tên model trong settings | Vector đã chuẩn hóa, kích thước 384 | Hoàn thành |
| ChromaDB vector index | `src/retrieval/index.py`, `LocalEmbeddingIndex.build/load` | Clean/corrupted/repaired DataFrame | Ba collection và embedding manifest | Hoàn thành |
| Semantic search và exact lookup | `LocalEmbeddingIndex.search/lookup` | Câu truy vấn, DOI hoặc title | Danh sách `SearchResult` có score, metadata và context | Hoàn thành |
| QA logic | `src/retrieval/qa.py`, `answer_question` | Câu hỏi, settings và vector index | Câu trả lời, document IDs, contexts và titles đã truy xuất | Hoàn thành |
| QA Agent | `src/retrieval/agent.py`, `build_agent/run_agent_question` | Settings, index và câu hỏi người dùng | Agent có semantic-search tool và exact-lookup tool | Hoàn thành |

Tôi chỉ nhận ownership cho lớp retrieval/RAG. Việc tạo raw/clean data, Great Expectations, test set, orchestration và báo cáo tổng do các thành viên tương ứng phụ trách.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Chuẩn hóa contract index | `pipelines/phase1.py`, `pipelines/corruption_flow.py` | Cùng một API build/load dùng được cho baseline, corrupted và repaired |
| Bảo vệ artifact binary | Git/repository | Thêm `.gitattributes` để file Chroma không bị đổi LF/CRLF trên Windows |
| Quản lý cache model | Môi trường chạy chung | Thêm `.cache/` vào `.gitignore`, tránh commit trọng số MiniLM |
| Kiểm thử offline | Nhóm tích hợp | Bổ sung `LocalPaperAgent` cho provider `mock`, không cần API key khi smoke test |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Sinh embedding MiniLM | `embeddings.py` | Vector 384 chiều, chuẩn hóa cosine | Kiểm tra `embedding_dimension` trong manifest |
| Lập chỉ mục baseline | `index.py`, `data/chroma/` | `papers-baseline`: 24 documents | Đối chiếu Chroma collection và manifest |
| Cô lập ba trạng thái | Ba file trong `data/embeddings/` | `papers-baseline` 24, `papers-corrupted` 22, `papers-repaired` 24 | Đọc `collection_name` và `document_count` |
| Semantic search | `LocalEmbeddingIndex.search()` | Trả về top-k có cosine score và metadata | Query cùng nội dung document cho top hit đúng DOI, score 1.0 |
| Exact lookup | `LocalEmbeddingIndex.lookup()` | Tra cứu không phân biệt hoa/thường theo DOI hoặc title | Lookup cùng paper bằng cả DOI và title |
| QA theo tài liệu | `qa.py` | Trả lời đúng bốn loại summary/authors/date/categories | Smoke test trên title/DOI và kiểm tra retrieved ID |
| Agent | `agent.py` | Tool-calling agent cho provider thật và agent offline cho `mock` | `run_agent_question()` trả cùng đáp án với QA deterministic |

Artifact chính của phần việc:

- `data/chroma/chroma.sqlite3`
- `data/embeddings/papers_embeddings.json`
- `data/embeddings/papers_embeddings_corrupted.json`
- `data/embeddings/papers_embeddings_repaired.json`
- Commit cá nhân `b98dc1a`: `feat(retrieval): add MiniLM Chroma index and QA agent`

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần chuyển văn bản bài báo thành vector ngữ nghĩa, lưu bền vững và truy xuất đúng tài liệu cho câu hỏi. Ba trạng thái dữ liệu phải được cách ly để corruption không ghi đè baseline và kết quả repaired có thể so sánh công bằng. Lớp QA phải trả lại cả câu trả lời lẫn bằng chứng retrieval để evaluation tính Hit Rate và Token F1.

### Cách triển khai

`MiniLMEmbeddings` tải `sentence-transformers/all-MiniLM-L6-v2`, encode theo batch và chuẩn hóa vector. `LocalEmbeddingIndex.build()` kiểm tra schema, dữ liệu rỗng và DOI trùng trước khi tạo collection cosine trong ChromaDB. Tên manifest quyết định collection tương ứng: baseline, corrupted hoặc repaired.

Mỗi document lưu `paper_id`, title, nội dung embedding và metadata cần cho QA. `search()` nhúng query, giới hạn `top_k` theo số document rồi chuyển cosine distance thành score. `lookup()` dùng map DOI/title để ưu tiên chính xác tài liệu được nhắc trong câu hỏi. `answer_question()` hỗ trợ tham chiếu title trong nháy đơn/đôi và DOI; sau đó trích summary, authors, published hoặc categories từ metadata. Agent LangChain cung cấp hai tool semantic search và exact lookup; chế độ mock dùng cùng QA logic để kiểm thử offline.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | DataFrame có `paper_id`, `title`, `text_for_embedding`, `published`, `authors_joined`, `categories_joined`, `summary`, URL |
| Output | Persistent Chroma collection, JSON manifest, `SearchResult` và `AnswerResult` |
| Module phụ thuộc | `core/config.py`, clean data của ingestion |
| Module sử dụng output | `evaluation/metrics.py`, `pipelines/phase1.py`, `pipelines/corruption_flow.py` |
| Điều kiện lỗi cần xử lý | Thiếu cột, DataFrame rỗng, DOI trùng, text rỗng, collection/manifest chưa tồn tại, `top_k <= 0` |

### Cách xác minh

```powershell
$env:HF_HUB_OFFLINE = "1"
python -c "import json; from pathlib import Path; m=json.loads(Path('data/embeddings/papers_embeddings.json').read_text()); print(m['collection_name'], m['document_count'], m['embedding_dimension'])"
python -m py_compile src/retrieval/embeddings.py src/retrieval/index.py src/retrieval/qa.py src/retrieval/agent.py
```

- **Kết quả mong đợi:** `papers-baseline 24 384`; các file compile thành công.
- **Kết quả thực tế:** đạt đúng kết quả mong đợi; semantic search, exact lookup và bốn loại QA đều pass smoke test.
- **Artifact/log:** `data/embeddings/`, `data/chroma/`, `data/results/*_answers.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần embedding/index chạy lặp lại được trên máy học viên, không phụ thuộc dịch vụ tính phí và phải hỗ trợ so sánh ba trạng thái.
- **Các phương án đã cân nhắc:** (1) embedding API bên ngoài và vector database cloud; (2) MiniLM cục bộ với ChromaDB persistent; (3) tìm kiếm từ khóa hoặc index chỉ nằm trong RAM.
- **Phương án đã chọn:** `all-MiniLM-L6-v2` cục bộ, vector được normalize và ChromaDB dùng cosine distance; mỗi trạng thái có collection riêng.
- **Lý do:** Không phát sinh chi phí API, có thể chạy offline sau lần tải đầu, vector 384 chiều tương đối nhẹ, artifact tồn tại sau khi chương trình kết thúc và tránh nhiễm chéo giữa baseline/corrupted/repaired.
- **Bằng chứng quyết định phù hợp:** Baseline retrieval hit rate đạt 1.0; corrupted giảm còn 0.6; repaired trở lại 1.0 trên cùng test set. Ba manifest ghi đúng collection và số documents tương ứng.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `WinError 10061: No connection could be made because the target machine actively refused it` khi Sentence Transformers tải MiniLM; cơ chế Hugging Face Xet dừng ở file trọng số.
- **Lệnh hoặc bước tái hiện:** Khởi tạo `MiniLMEmbeddings('sentence-transformers/all-MiniLM-L6-v2')` trên máy chưa có cache.
- **Nguyên nhân gốc:** Kết nối tới backend tải Xet không ổn định; metadata tải được nhưng trọng số không hoàn tất.
- **Cách xử lý:** Đặt `HF_HUB_DISABLE_XET=1`, dùng HTTP thông thường, lưu cache vào `.cache/huggingface` trong workspace và ignore `.cache/` khỏi Git.
- **Cách xác minh sau khi sửa:** Model load thành công; manifest báo dimension 384; collection baseline nhận đủ 24 documents và truy vấn top hit đúng DOI.
- **Điều học được:** Cần tách lỗi tải model khỏi lỗi index, hỗ trợ cache/offline và không commit trọng số lớn vào repository.

## 7. Hiểu biết về luồng end-to-end

1. Crossref payload được giữ nguyên ở raw, parse thành `PaperRecord`, làm sạch và ghép `text_for_embedding`. Quality Gate kiểm tra dữ liệu trước khi MiniLM tạo vector và ChromaDB lưu collection.
2. Evaluation set chứa câu hỏi, đáp án chuẩn và `ground_truth_doc_ids`. Retrieval Hit Rate kiểm tra document đúng có nằm trong kết quả hay không; Token F1 và judge so sánh câu trả lời với ground truth.
3. Quality checks kiểm tra completeness, uniqueness, row count và độ dài nội dung. Freshness monitoring tập trung vào tuổi dữ liệu và tỷ lệ bản ghi vượt SLA 180 ngày.
4. Phải dùng cùng test set cho baseline, corrupted và repaired để thay đổi metric phản ánh thay đổi dữ liệu/index, không phải do đề đánh giá khác nhau.
5. Repair thành công khi dữ liệu được tái tạo từ raw một cách idempotent, Quality/Freshness trở lại pass và các metric repaired tiến gần hoặc bằng baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000 | Corruption làm mất 40% retrieval hit; repair phục hồi hoàn toàn |
| `mean_token_f1` | 1.0000 | 0.5741 | 1.0000 | Nội dung lỗi làm câu trả lời lệch đáng kể |
| `judge_accuracy` | 1.0000 | 0.6000 | 1.0000 | Judge heuristic xác nhận cùng xu hướng với retrieval |
| `mean_judge_score` | 5.0 | 3.2 | 5.0 | Điểm giảm 1.8 khi dữ liệu bị làm bẩn |
| Quality checks | PASS | FAIL | PASS | Null/duplicate/độ dài và các lỗi schema được phát hiện |
| Freshness status | PASS | FAIL | PASS | Stale-date vượt SLA ở corrupted và được sửa từ raw |

Ragas không chạy vì `RUN_RAGAS` chưa được bật. LLM evaluator không khả dụng trong lần chạy artifact nên hệ thống dùng fallback heuristic judge; báo cáo không diễn giải các điểm này như kết quả từ LLM bên ngoài.

### Kết luận từ số liệu

1. Sáu corruption được áp dụng đồng thời → Quality Gate và Freshness chuyển sang FAIL → Hit Rate giảm từ 1.0 xuống 0.6, Token F1 giảm xuống 0.5741.
2. Dữ liệu được dựng lại từ raw → Quality/Freshness trở lại PASS → toàn bộ metric repaired trở về mức baseline.

Không thể kết luận trung thực một loại corruption riêng lẻ ảnh hưởng mạnh nhất vì phiên chạy hiện tại tiêm cả sáu loại cùng lúc. Drop-latest làm mất ground-truth document, còn blank-summary/noise/truncated-title trực tiếp làm suy yếu retrieval và answer quality; duplicate/stale-date thể hiện rõ nhất ở observability. Muốn xác định đóng góp riêng cần chạy ablation: mỗi lần chỉ tiêm một loại lỗi trên cùng test set.

Kết quả đáng chú ý là repaired phục hồi đúng bằng baseline thay vì chỉ gần baseline. Điều này hợp lý vì repair đọc cùng raw snapshot, dùng cùng cleaning rules, embedding model và test set; đây là bằng chứng cho tính idempotent của flow hiện tại.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Vector index chỉ đáng tin khi document identity, schema và collection boundary ổn định; chất lượng retrieval phụ thuộc trực tiếp chất lượng dữ liệu đầu vào.
2. Quality Gate và Freshness phát hiện lỗi dữ liệu trước serving, trong khi RAG metrics đo hậu quả của lỗi lên người dùng; hai nhóm tín hiệu bổ sung cho nhau.
3. Giữ nguyên test set và cấu hình embedding là điều kiện bắt buộc để so sánh baseline, corrupted và repaired có ý nghĩa.

### Nếu có thêm thời gian

Tôi sẽ bổ sung bộ ablation tự động, tạo sáu corrupted collection riêng và đo delta Hit Rate/Token F1 cho từng corruption. Cải tiến này giúp xác định lỗi nào gây thiệt hại lớn nhất thay vì chỉ đo tác động tổng hợp. Ngoài ra có thể bật Ragas khi có cấu hình evaluator phù hợp và ghi rõ chi phí/thời gian chạy.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Quang Đạt
**Ngày xác nhận:** 2026-09-25
