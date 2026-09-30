# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-2A202602656`

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Latency P95 của `response_sent.latency_ms` (SLO `fast_successful_requests`)
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` kéo dài trong 5 phút
- Ảnh hưởng tới người dùng: Trải nghiệm người dùng bị chậm, thời gian chờ câu trả lời vượt quá ngưỡng chấp nhận được (3 giây)
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** Mở panel Latency trên Dashboard để kiểm tra xu hướng P50, P95, P99 và TTFT nhằm xác định latency tăng đột biến ở giai đoạn nào.
  2. **Logs:** Lọc file `data/logs.jsonl` theo sự kiện `response_sent` có `latency_ms > 3000` trong 5 phút gần nhất, trích xuất `correlation_id` và thông tin request liên quan.
  3. **Traces:** Tra cứu `correlation_id` đó trên Langfuse Tracing để kiểm tra waterfall; xác định xem điểm nghẽn nằm ở span `retrieval` (vector DB chậm) hay span `generation` (LLM phản hồi chậm/token dài).
- Mitigation tạm thời: Nếu do prompt mới làm sinh token quá dài thì rollback `production` prompt về phiên bản trước; nếu do vector database thì áp dụng caching hoặc fallback sang keyword search.
- Owner: `student-2A202602656`

## Alert 2

- Tên: `HighErrorRate`
- Severity: `critical`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Tỉ lệ lỗi tổng thể trên hệ thống (`error_rate_pct_max: 2%`)
- Điều kiện và thời gian duy trì: `error_rate_pct > 2%` (tỉ lệ request_failed trên request_received vượt 2%) trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng nhận mã lỗi HTTP 500 hoặc không nhận được câu trả lời từ chatbot.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** Kiểm tra panel Errors trên Dashboard để xem error rate thực tế và danh sách phân bố các loại lỗi (`error_type`).
  2. **Logs:** Lọc `data/logs.jsonl` các dòng có `event == "request_failed"`, kiểm tra `error_type` (ví dụ: `RuntimeError`, `Timeout`, `HTTPException`), `payload.detail`, và lấy các `correlation_id` đại diện.
  3. **Traces:** Mở trace của các `correlation_id` bị lỗi trên Langfuse để kiểm tra trạng thái lỗi (ERROR status) tại span con nào (`retrieval` timeout hay LLM provider outage).
- Mitigation tạm thời: Bật cơ chế retry có exponential backoff, kích hoạt fallback response tĩnh cho người dùng, hoặc tạm dừng luồng retrieval nếu vector store gặp sự cố nghiêm trọng.
- Owner: `student-2A202602656`

## Alert 3

- Tên: `LowQualityScore`
- Severity: `warning`
- Duration: `10m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Điểm chất lượng trung bình của câu trả lời (`quality_score_avg_min: 0.75`)
- Điều kiện và thời gian duy trì: `mean(quality_score) < 0.75` kéo dài liên tục trong 10 phút
- Ảnh hưởng tới người dùng: Câu trả lời chatbot đưa ra kém chính xác, thiếu ngữ cảnh tài liệu cần thiết hoặc bị lỗi lặp từ.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** Mở panel Quality trên Dashboard để xem giá trị trung bình điểm chất lượng theo thời gian so với đường ngưỡng 0.75; đồng thời kiểm tra tỉ lệ `retrieval_success_rate`.
  2. **Logs:** Lọc các log `response_sent` có `quality_score < 0.75` và `tool_success == false`, ghi nhận `session_id`, `feature` và `prompt_version` đang dùng.
  3. **Traces:** Mở trace trên Langfuse để kiểm tra span `retrieval` xem tài liệu có được lấy ra hay rỗng (`doc_count == 0`), và kiểm tra version prompt đang chạy.
- Mitigation tạm thời: Kiểm tra lại prompt label `production`, rollback prompt về phiên bản đã qua kiểm định nếu phiên bản mới làm giảm chất lượng; kiểm tra kết nối tới dịch vụ tìm kiếm ngữ cảnh.
- Owner: `student-2A202602656`
