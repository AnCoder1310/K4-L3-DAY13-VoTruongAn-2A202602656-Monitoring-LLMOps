# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Võ Trường An
- **MSSV:** 2A202602656
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/AnCoder1310/K4-L3-DAY13-VoTruongAn-2A202602656-Monitoring-LLMOps.git
- **Commit SHA cuối:** 61a34f8
- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602656`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | [evidence/01-pytest.png](evidence/01-pytest.png) |
| Log validator | [evidence/02-log-validator.png](evidence/02-log-validator.png) |
| Dashboard validator | [evidence/03-dashboard-validator.png](evidence/03-dashboard-validator.png) |
| Structured log | [evidence/04-structured-log.png](evidence/04-structured-log.png) |
| PII redaction | [evidence/05-pii-redaction.png](evidence/05-pii-redaction.png) |
| Trace list | [evidence/06-trace-list.png](evidence/06-trace-list.png) |
| Trace waterfall | [evidence/07-trace-waterfall.png](evidence/07-trace-waterfall.png) |
| Trace metadata | [evidence/08-trace-metadata.png](evidence/08-trace-metadata.png) |
| Prompt versions | [evidence/09-prompt-versions.png](evidence/09-prompt-versions.png) |
| Prompt rollback | [evidence/10-prompt-rollback.png](evidence/10-prompt-rollback.png) |
| Dashboard runtime | [evidence/11-dashboard-overview.png](evidence/11-dashboard-overview.png) |
| Incident metric | [evidence/12-incident-metric.png](evidence/12-incident-metric.png) |
| Incident log | [evidence/13-incident-log.png](evidence/13-incident-log.png) |
| Incident trace | [evidence/14-incident-trace.png](evidence/14-incident-trace.png) |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Đạt chuẩn toàn bộ JSON schema, correlation ID, context enrichment và PII scrubbing |
| `validate_dashboard.py` | 6/6 | 6/6 | Khớp 100% hợp đồng cấu hình dashboard 6 panel |
| `pytest` | 22 passed | 24 passed | Vượt qua toàn bộ unit tests kể cả PII CCCD & Credit Card |
| Số traces hợp lệ | 0 | 77 traces | Traces được ghi nhận đầy đủ trong project Langfuse cá nhân |
| Số PII leak | 0 | 0 | Không còn PII nguyên văn trong log (email, sđt, cccd, credit card) |
| Latency P95 / TTFT P95 | 164.0ms / 55.0ms | 164.0ms / 55.0ms (8689.2ms khi có incident) | Baseline phản hồi rất nhanh, bộc lộ rõ khi xảy ra incident |
| Retrieval success rate | 100% | 100% | Tỉ lệ retrieval thành công tuyệt đối trong luồng xử lý |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `app/middleware.py`, tạo class `CorrelationIdMiddleware` kế thừa `BaseHTTPMiddleware`. Trước mỗi request gọi `clear_contextvars()` để xóa context cũ tránh rò rỉ. Kiểm tra header `x-request-id`, nếu chưa có sẽ tự sinh theo format `req-<8-hex>` (`req-{uuid.uuid4().hex[:8]}`). Dùng `bind_contextvars(correlation_id=correlation_id)` để gắn vào ngữ cảnh structlog, gán vào `request.state.correlation_id`, và trả về client qua header `x-request-id` cùng `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** Bổ sung đầy đủ trong `app/main.py`: `user_id_hash` (băm sha256 12 ký tự), `session_id`, `feature`, `model` (claude-sonnet-4-5), `env` (dev), `service` (api), `event` (request_received, response_sent, request_failed), `ts` (ISO timestamp UTC), các chỉ số vận hành `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`.
- **Cách bảo đảm PII được scrub trước khi ghi:** Trong `app/pii.py`, định nghĩa các biểu thức chính quy nhận diện Email, SĐT Việt Nam (+84 hoặc 09x...), CCCD (12 số), Thẻ tín dụng (16 số có hoặc không dấu gạch ngang/khoảng trắng). Trong `app/logging_config.py`, đăng ký processor `scrub_event` đứng trước `JsonlFileProcessor` và `JSONRenderer`. Do đó toàn bộ nội dung payload và event được thay thế bằng `[REDACTED_...]` trước khi serialize JSON hoặc ghi xuống file `data/logs.jsonl`.
- **Cách kiểm chứng kết quả:** Chạy `python scripts/validate_logs.py` đạt 100/100; gửi request chứa PII giả định dạng email, sđt, cccd, thẻ và kiểm tra đuôi file `data/logs.jsonl` thấy toàn bộ đã được thay thế thành `[REDACTED_...]` mà không rò rỉ nguyên văn.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Traces hiển thị trên Langfuse Cloud tại project `day13-k4-l3b-2A202602656` của tổ chức `Võ's Organization` gắn đúng API keys trong `.env`. Cột Start Time khớp đúng thời gian thực hiện bài lab (sáng ngày 30/09/2026) với 77 traces hợp lệ.
- **Cấu trúc root/retrieval/generation observations:**
  - Root observation: `lab-agent-run` (type `agent`) do decorator `@observe` trong `app/agent.py` bao bọc toàn bộ luồng.
  - Child observation 1: `retrieval` (type `retriever`) do `@observe(name="retrieval", as_type="retriever")` trong `app/mock_rag.py` bao bọc bước tìm tài liệu.
  - Child observation 2: `generation` (type `generation`) do `@observe(name="generation", as_type="generation")` trong `app/mock_llm.py` ghi nhận `model`, `usage_details` (input, output, total), `cost_details` và liên kết đối tượng prompt quản lý.
- **Cách nối trace với log:** Sử dụng `correlation_id` làm khóa liên kết duy nhất; `correlation_id` từ middleware được truyền vào hàm `agent.run()`, bind vào metadata của `propagate_attributes` của trace Langfuse và đồng thời ghi vào từng dòng structured log trong `data/logs.jsonl`.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1 (gắn nhãn `baseline` và `production`)
- **Version/label candidate:** Version 2 (gắn nhãn `candidate` và `latest`, có thêm chỉ dẫn ngắn gọn)
- **Trace ID của mỗi version:**
  - Trace ID dùng v1: `80c1447b9aeb11689f302103c8216b9f` (prompt_label: `production`, prompt_version: `1`)
  - Trace ID dùng v2: `req-004e6de7` (hoặc trace ID sau khi promote)
- **Cách promote và rollback `production`:**
  - *Promote:* Trên giao diện Langfuse Prompts, chỉnh sửa nhãn của Version 2, gán nhãn `production` cho Version 2 (nhãn `production` tự động rời khỏi Version 1). Ứng dụng tự động nhận version mới mà không cần sửa code.
  - *Rollback:* Khi cần khôi phục phiên bản trước, chọn Version 1 trên giao diện Langfuse Prompts và gán lại nhãn `production` cho Version 1. Ứng dụng ngay lập tức dùng lại prompt v1 an toàn.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dựng hoàn chỉnh tại `http://127.0.0.1:8000/dashboard` đọc trực tiếp từ `data/logs.jsonl`, tự động làm mới mỗi 30s với time range 60 phút, bao gồm:
  1. *Latency & TTFT:* P50, P95, P99 và TTFT P95 kèm đường ngưỡng P95 <= 3000ms.
  2. *Request Traffic:* Tổng số request và tốc độ request/phút kèm ngưỡng >= 1 req/min.
  3. *Errors & Retrieval:* Tỉ lệ lỗi % và tỉ lệ thành công của retrieval % kèm ngưỡng error_rate <= 2.0%.
  4. *Cost Over Time:* Tổng chi phí tích lũy (USD) kèm ngưỡng <= $2.50.
  5. *Tokens:* Tổng số token in và token out kèm ngưỡng <= 50,000 tokens.
  6. *Quality Proxy:* Điểm chất lượng trung bình kèm ngưỡng >= 0.75.
- **SLO và lý do chọn:** Chọn SLO `fast_successful_requests` với mục tiêu 99.5% requests thành công và có độ trễ latency <= 3000ms trong cửa sổ 28 ngày. Lý do chọn: baseline hệ thống phản hồi cực nhanh (~160ms, TTFT ~55ms); ngưỡng 3000ms đảm bảo người dùng không phải chờ đợi quá lâu khi hệ thống gặp tải hoặc suy giảm hiệu năng.
- **Cách tính error budget:** Với mục tiêu SLO 99.5% trong cửa sổ 28 ngày, error budget cho phép là `100% - 99.5% = 0.5%`. Nếu hệ thống xử lý 10,000 requests trong 28 ngày, số lượng request tối đa được phép bị lỗi (HTTP 500) hoặc có độ trễ vượt quá 3000ms là `10,000 * 0.5% = 50 requests`.
- **Ba alert và runbook tương ứng:**
  - *Alert 1 (`HighLatencyP95`):* Warning, điều kiện `p95(latency_ms) > 3000ms` kéo dài 5m, owner `student-2A202602656`, channel `#k4-l3b-alerts`, runbook `docs/alerts.md#alert-1`.
  - *Alert 2 (`HighErrorRate`):* Critical, điều kiện `error_rate_pct > 2%` kéo dài 5m, owner `student-2A202602656`, channel `#k4-l3b-alerts`, runbook `docs/alerts.md#alert-2`.
  - *Alert 3 (`LowQualityScore`):* Warning, điều kiện `mean(quality_score) < 0.75` kéo dài 10m, owner `student-2A202602656`, channel `#k4-l3b-alerts`, runbook `docs/alerts.md#alert-3`.

## 7. Điều tra challenge

- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Khoảng thời gian điều tra:** 10:45 - 11:30 (ngày 30/09/2026)
- **Triệu chứng từ metrics:** Panel Latency trên Dashboard tăng đột biến: P95 vọt từ baseline ~164ms lên đỉnh 8,689.2ms (vượt ngưỡng cho phép 2,000ms của challenge và 3,000ms của dashboard), nhãn ngưỡng chuyển sang màu đỏ `ALERT`. Trong khi đó Error Rate vẫn là 0%, Cost và Token không có dấu hiệu tăng vọt.
- **Log line và correlation ID liên quan:** `{"event": "response_sent", "service": "api", "latency_ms": 3264, "ttft_ms": 55, "tokens_in": 35, "tokens_out": 179, "cost_usd": 0.00279, "quality_score": 0.8, "tool_name": "retrieval", "tool_success": true, "model": "claude-sonnet-4-5", "env": "dev", "feature": "monitoring", "correlation_id": "req-123b8577", "session_id": "k4-l3b-challenge-s03", "user_id_hash": "189d0a182d4e", "level": "info", "ts": "2026-09-30T03:56:59.992345Z"}`
- **Trace ID và span gây ảnh hưởng:** Trace trên Langfuse `80c1447b9aeb11689f302103c8216b9f` cùng `correlation_id: req-123b8577` cho thấy root span `lab-agent-run` mất 3.27s, trong đó span con `retrieval` bị nghẽn mất 2.50s (chiếm hơn 94% tổng độ trễ), trong khi span con `generation` chỉ mất 0.16s ($0.00279, 214 tokens) hoàn toàn bình thường.
- **Root cause:** Độ trễ tăng đột biến xuất phát từ tầng tìm kiếm tài liệu (RAG / Vector Database latency spike), bị delay giả lập 2.5s khi truy vấn các tài liệu liên quan đến chủ đề `monitoring`.
- **Fix action:** Chạy `python scripts/inject_incident.py --disable` để tắt sự cố giả lập; trên thực tế cần tối ưu hóa chỉ mục vector, tăng tài nguyên cho vector store hoặc kích hoạt caching cho các câu hỏi phổ biến để đưa latency về baseline (< 200ms).
- **Preventive measure:** Bật alert rule `HighLatencyP95` (P95 > 2000ms trong 5m) gửi thông báo về Slack `#k4-l3b-alerts`; đặt timeout cứng 1.5s cho tầng retrieval và áp dụng cơ chế fallback trả về câu trả lời tổng quát nếu vector store phản hồi chậm.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Quyết định thực hiện PII scrubbing ngay tại tầng logging processor (`structlog.processors`) trước khi format JSON và ghi file thay vì scrub ở tầng API response. Lý do: đảm bảo dữ liệu nhạy cảm của người dùng (email, phone, cccd, thẻ) được bảo vệ tuyệt đối ngay tại nguồn, loại bỏ hoàn toàn nguy cơ rò rỉ dữ liệu xuống đĩa cứng hoặc hệ thống log aggregator tập trung.
- **Một lỗi/blocker đã gặp:** Trong quá trình chạy API, địa chỉ Langfuse ban đầu được đặt mặc định là `https://cloud.langfuse.com` dẫn đến lỗi phân giải tên miền (DNS resolution error), đồng thời khi chạy server có tham số `--reload`, mỗi lần file log hoặc code thay đổi thì server tự khởi động lại làm mất trạng thái incident đang inject.
- **Cách tìm nguyên nhân và xử lý:** Kiểm tra chính xác bảng điều khiển Langfuse Cloud để cập nhật đúng `LANGFUSE_BASE_URL=https://us.cloud.langfuse.com` vào `.env`; khi thực hiện challenge, khởi động server bằng lệnh `uvicorn app.main:app --env-file .env` (bỏ cờ `--reload`) theo đúng hướng dẫn để duy trì ổn định trạng thái sự cố.
- **Cách hiểu luồng Metrics → Logs → Traces:** 
  1. *Metrics:* Đóng vai trò cảnh báo sớm (lớp phát hiện triệu chứng - symptom), cho biết "Hệ thống đang gặp vấn đề gì và xảy ra khi nào?" thông qua các chỉ số tổng hợp P95 latency, error rate.
  2. *Logs:* Đóng vai trò định danh phạm vi ảnh hưởng, giúp lọc ra các sự kiện bất thường và trích xuất `correlation_id` cụ thể của các request bị lỗi/chậm.
  3. *Traces:* Đóng vai trò khoanh vùng và xác định nguyên nhân gốc rễ (root cause localization), cho phép xem chi tiết từng span (retrieval vs generation) của một request cụ thể để kết luận chính xác điểm nghẽn.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Quản lý phiên bản prompt và nhãn (`production`/`candidate`) giúp triển khai và hoàn nguyên (rollback) prompt tức thì mà không cần rebuild/deploy lại ứng dụng. Theo dõi token và cost giúp ngăn chặn rủi ro bùng nổ chi phí (cost spike) ngoài tầm kiểm soát. SLO và Error budget là tiêu chuẩn định lượng để cân bằng giữa tốc độ phát triển tính năng mới và sự ổn định của hệ thống.
- **Điều quan trọng nhất đã học:** Hiểu sâu sắc cách xây dựng một hệ thống Observability hoàn chỉnh cho ứng dụng LLMOps trong thực tế: từ structured logging có ngữ cảnh, bảo vệ dữ liệu PII, phân tán trace theo quan hệ cha-con đến trực quan hóa dữ liệu trên Dashboard và quy trình phản ứng sự cố chuẩn mực.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Các biểu đồ dashboard hiện tại được vẽ bằng Chart.js tích hợp sẵn trong FastAPI service; nếu có thêm thời gian có thể triển khai thêm cụm Prometheus + Grafana hoàn chỉnh để lưu trữ dữ liệu chuỗi thời gian dài hạn hơn.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
