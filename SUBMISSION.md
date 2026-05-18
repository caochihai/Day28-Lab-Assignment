# Hướng Dẫn Nộp Bài - Lab #28: Full Platform Integration Sprint

## Yêu Cầu Nộp Bài

**Full AI infrastructure platform demo** - từ data ingestion đến model serving với full observability.

## Các Artifacts Cần Nộp

### 1. Source Code
- Folder `lab28/` hoàn chỉnh với tất cả files
- Tất cả integration scripts hoạt động
- Prefect flows đã deploy và schedule

### 2. Screenshots Demo
Chụp màn hình các bước:
- Prefect UI: http://localhost:4200 (flow đang chạy)
- API Gateway call: `curl http://localhost:8000/health`
- Grafana dashboard: http://localhost:3000

### 3. Kết Quả Smoke Tests
Chạy và chụp màn hình kết quả:
```bash
cd lab28
pytest smoke-tests/ -v
```
Kỳ vọng: 5/5 tests passing

### 4. Production Readiness Score
```bash
python scripts/production_readiness_check.py
```
Kỳ vọng: Score >80%

### 5. Documentation
- `README.md` giải thích cách:
  - Start platform: `docker compose up -d`
  - Deploy Prefect flows
  - Run smoke tests
  - Access dashboards (Grafana:3000, Prometheus:9090, Prefect:4200)

## Định Dạng Nộp Bài

Tạo Repo GitHub chứa:
```
lab28_submission_[student_id]
├── lab28/                    # Source code hoàn chỉnh
│   ├── docker-compose.yml
│   ├── prefect/flows/
│   ├── scripts/
│   ├── api-gateway/
│   └── monitoring/
├── screenshots/              # Screenshots demo
│   ├── prefect_ui.png
│   ├── api_gateway.png
│   └── grafana_dashboard.png
├── smoke_tests_results.png   # Screenshot kết quả pytest
├── production_readiness.png  # Screenshot readiness score
└── README.md                # Hướng dẫn setup
```

## Địa Điểm Nộp
Nộp link repo GitHub qua LMS

## Tiêu Chí Chấm Điểm

| Tiêu Chí | Trọng Số | Mô Tả |
|----------|----------|-------|
| Integration Completeness | 40% | Tất cả 10 integration points hoạt động, data flow end-to-end |
| Observability | 25% | Logs, metrics, traces hiển thị; alerts configured |
| Performance | 20% | Latency trong SLO; load tested; không có memory leaks |
| Architecture Quality | 15% | Clean separation, GitOps config, documented decisions |

## Các Vấn Đề Cần Tránh

- Config drift giữa các environments
- Thiếu error handling tại integration points
- Monitoring coverage không hoàn chỉnh
- Không có rollback strategy
- Demo không test trước khi nộp

## 5 Câu Hỏi Cần Trả Lời Khi Nộp

### 1. Phân tích các trade-offs trong thiết kế kiến trúc AI platform của bạn. Bạn đã cân bằng giữa performance, reliability, và maintainability như thế nào?
*   **Performance (Hiệu năng) vs Cost (Chi phí)**: Thiết kế Hybrid giải phóng hoàn toàn các tác vụ tính toán hạng nặng (LLM Qwen 7B và dịch vụ Embeddings BGE) lên GPU Kaggle miễn phí, giảm thiểu chi phí đầu tư local. Mặc dù phải đánh đổi bằng độ trễ mạng (Network Latency) do qua internet và ngrok tunnels, hệ thống đã cân bằng bằng cách truy vấn Context cực nhanh tại local thông qua Qdrant và Feast (Redis) trước, chỉ truyền tải payload văn bản tối ưu lên cloud.
*   **Reliability (Độ tin cậy)**: Hệ thống áp dụng triết lý **Graceful Degradation (Suy giảm chất lượng có kiểm soát)**. API Gateway và Qdrant sync không crash khi mất kết nối cloud, thay vào đó kích hoạt cơ chế Offline Fallback an toàn (trả về offline response thông minh và sinh vector mock cosine 384 chiều cục bộ).
*   **Maintainability (Khả năng bảo trì)**: Kiến trúc Docker Compose module hóa 8 dịch vụ local chạy biệt lập, giúp dễ dàng thay thế, nâng cấp từng cấu phần (như Vector DB hay Feature Store) mà không làm ảnh hưởng đến tổng thể nền tảng. Tất cả config được quản lý tập trung ở file `.env`.

### 2. Trong kiến trúc hybrid (Local + Kaggle), bạn xử lý ngắt kết nối giữa local và Kaggle như thế nào? Có cơ chế fallback không?
*   **Xử lý ngắt kết nối**: Do ngrok tunnels có vòng đời ngắn hạn hoặc kết nối mạng công cộng có thể chập chờn, API Gateway được cấu hình thư viện `httpx.AsyncClient` với cơ chế thiết lập **Timeout nghiêm ngặt** (3.0s đối với Qdrant search và 30.0s đối với vLLM chat completions) để ngăn chặn đứng luồng hoặc nghẽn thread.
*   **Cơ chế Fallback**:
    1.  *Đối với luồng Embedding*: Khi kết nối tới dịch vụ embedding Kaggle bị lỗi hoặc không có URL ngrok cấu hình, script sẽ tự động chuyển sang sinh các vector nhúng Mock ngẫu nhiên nhưng đảm bảo chuẩn hóa cosine 384 chiều cục bộ để tiếp tục ghi vào Qdrant ổn định.
    2.  *Đối với luồng API Gateway*: Toàn bộ luồng chat được bao bọc trong khối `try-except` an toàn. Nếu xảy ra ngoại lệ ngắt kết nối hoặc timeout, Gateway sẽ trả về phản hồi offline chuẩn hóa: *"Error: LLM service is currently unavailable. Falling back to offline response."*, giữ cho hệ thống luôn phản hồi 100%.

### 3. Giải thích cách event-driven architecture với Kafka giúp decouple các components trong AI platform của bạn.
*   **Decoupling (Khử ghép nối hoàn toàn)**: Lớp thu nhận dữ liệu thô (Data Producer) chỉ chịu trách nhiệm đẩy dữ liệu thô vào topic `data.raw` của Kafka với tốc độ tối đa. Nó hoàn toàn không cần biết phía sau có những dịch vụ nào tiêu thụ dữ liệu, chúng chạy bằng ngôn ngữ gì hay Delta Lake lưu trữ ra sao.
*   **Buffer & Khắc phục Backpressure**: Kafka đóng vai trò là một hàng đợi trung gian (Message Buffer) phân tán. Nếu Prefect ETL Flow hoặc Delta Lake bị chậm hoặc quá tải, dữ liệu vẫn được lưu trữ an toàn trong Kafka. Prefect Worker tiêu thụ dữ liệu theo cơ chế kéo (pull-based) phù hợp với năng lực xử lý của nó, loại bỏ nguy cơ sập hệ thống do nghẽn cổ chai.
*   **Khả năng phát lại (Replayability)**: Khi có lỗi xử lý xảy ra ở Delta Lake, chúng ta chỉ cần reset offset của consumer để đọc lại dữ liệu từ Kafka để tái xử lý mà không cần nguồn dữ liệu ban đầu phải phát lại.

### 4. Bạn đã implement observability như thế nào? Logs, metrics, và traces được thu thập và visualized ra sao?
*   **Metrics (Prometheus + Grafana)**: API Gateway tích hợp `prometheus-fastapi-instrumentator` để tự động thu thập các metrics hiệu năng hệ thống (throughput, request rate, error rate, latency). Prometheus Server local định kỳ scrape cổng `/metrics` này. Grafana kết nối vào Prometheus để trực quan hóa thành các biểu đồ dashboard sinh động ở cổng `3000`.
*   **Traces (LangSmith)**: API Gateway được trang bị decorator `@traceable` của LangSmith. Mọi chi tiết về prompt đầu vào, vector tương ứng, context thu được từ Qdrant, và câu trả lời sinh ra từ LLM trên Kaggle cùng thời gian xử lý đều được gửi trực tiếp lên SaaS dashboard trực tuyến để giám sát chuyên sâu.
*   **Logs**: Docker Logging tự động thu thập và lưu trữ tập trung logs của toàn bộ 8 services, giúp nhà quản trị dễ dàng truy vết bằng lệnh `docker compose logs -f`.

### 5. Nếu một service trong stack (ví dụ: Qdrant hoặc Kafka) bị crash, hệ thống của bạn sẽ xử lý như thế nào? Có graceful degradation không?
*   **Kafka Crash**: Lớp đẩy dữ liệu thô sẽ lỗi nhưng **API Gateway chính vẫn chạy ổn định**. Người dùng cuối vẫn Chat RAG bình thường nhờ dữ liệu cũ đã đồng bộ sẵn trong Feast và Qdrant.
*   **Qdrant Crash**: API Gateway bắt giữ ngoại lệ kết nối Qdrant trong khối `try-except` và tự động chuyển sang chế độ **Graceful Degradation** (bỏ qua bước tìm kiếm Context và gửi câu hỏi trực tiếp hoặc sử dụng thông tin tĩnh dự phòng từ Feast). Hệ thống phản hồi chậm hơn hoặc kém chính xác hơn nhưng tuyệt đối không trả về trang lỗi hệ thống 500 cho người dùng.
*   **Self-Healing**: Các container được Docker Compose giám sát và tự động khởi động lại (restart) khi crash nhằm khôi phục trạng thái sẵn sàng sớm nhất.

## Câu Hỏi Thêm?
Liên hệ giảng viên qua LMS hoặc office hours.
