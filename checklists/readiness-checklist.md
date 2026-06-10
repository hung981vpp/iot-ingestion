# Readiness Checklist – Lab 05

Đây là danh sách kiểm tra (checklist) để đảm bảo stack Docker Compose của bạn đã sẵn sàng trước khi gửi bài. Hãy tick vào mỗi mục sau khi hoàn thành.

- [x] **Database ready:** container DB đã chạy và phản hồi `pg_isready`. Kiểm tra bằng `docker exec fit4110-db-lab05 pg_isready -U lab05 -d iotdb`.
- [x] **AI service ready:** container AI service trả về `200` cho endpoint `/health` và `/predict` hoạt động.
- [x] **API ready:** container API trả `200` cho `/health` và có thể tạo/lấy readings khi token hợp lệ.
- [x] **Environment variables:** `.env` đã được thiết lập đúng (APP_PORT, POSTGRES_USER, AUTH_TOKEN,…). Không sử dụng secret thật; lưu secret vào `.env` cục bộ, commit `.env.example`.
- [x] **Network & Ports:** mạng `team-internal` hoạt động; API gọi được AI bằng hostname `ai-service`; ports 8000 (API) và 9000 (AI) được map ra host, DB dùng port 5432 trong mạng nội bộ.
- [x] **Image tags:** bạn đã build image với tag `v0.1.0-iot-ingestion` và push lên GHCR.

Ghi chú thêm những vấn đề gặp phải hoặc điều chỉnh tại đây:

```
- 2026-06-10: `docker compose ps` hiển thị `api`, `ai-service` và `db` đều healthy.
- DB readiness pass: `/var/run/postgresql:5432 - accepting connections`.
- AI readiness pass: `GET http://localhost:9000/health` trả `status=ok`; `POST /predict` trả dummy objects.
- API readiness pass: `GET http://localhost:8000/health` trả `status=ok`; tạo reading `R-20260610-0001` và lấy lại qua `/readings/latest` thành công với token `local-dev-token`.
- Network nội bộ pass: từ container API gọi `http://ai-service:9000/health` trả HTTP 200.
- Image đã build lại với tag local `lab-5-hung981vpp-api:v0.1.0-iot-ingestion` và `lab-5-hung981vpp-ai-service:v0.1.0-iot-ingestion`.
- Image đã push lên GHCR: `ghcr.io/hung981vpp/iot-ingestion-api:v0.1.0-iot-ingestion` và `ghcr.io/hung981vpp/iot-ingestion-ai-service:v0.1.0-iot-ingestion`.
- Newman test pass: 5 requests, 19 assertions, 0 failed. Reports đã tạo tại `reports/newman-lab05-compose.xml` và `reports/newman-lab05-compose.html`.
- Evidence log đã tạo tại `reports/compose-evidence.log`.
```
