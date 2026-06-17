# Checklist Sẵn Sàng Demo Buổi 6 - IoT Ingestion

Tick từng mục trước khi báo nhóm đã sẵn sàng demo. Các mục cần xác nhận từ Radmin/nhóm đối tác để trống cho đến khi test thật trên lớp.

- [x] Máy demo chính đã cài Radmin VPN.
- [ ] Đã join đúng Radmin Network của Product/cụm demo.
- [ ] Đã ghi Radmin IP vào bảng chung.
- [x] Service chạy bằng Docker Compose.
- [x] `docker compose ps` hiển thị container running.
- [x] `GET /health` local thành công.
- [ ] Nhóm đối tác gọi được `/health` qua Radmin IP.
- [ ] `.env` đã dùng Radmin IP của nhóm đối tác.
- [x] Endpoint nghiệp vụ hoặc MQTT topic đã test.
- [x] Có log xử lý input/output.
- [x] Có request/response hoặc payload MQTT mẫu.
- [x] Có minh chứng trong `reports/`.
- [x] Có xử lý timeout hoặc lỗi từ service phụ thuộc.

## Cần Tick Khi Lên Lớp

Các mục này chỉ tick sau khi đã có Radmin Network/IP thật:

```text
[ ] Máy demo chính đã cài Radmin VPN
[ ] Đã join đúng Radmin Network của Product/cụm demo
[ ] Đã ghi Radmin IP vào bảng chung
[x] docker compose ps hiển thị container running
[x] GET /health local thành công
[ ] Nhóm đối tác gọi được /health qua Radmin IP
[ ] .env đã dùng Radmin IP của nhóm đối tác
```

## Endpoint Cần Test

Local service:

```powershell
curl.exe http://localhost:8000/health
curl.exe -H "Authorization: Bearer local-dev-token" http://localhost:8000/iot/processed-events
```

Partner health:

```powershell
curl.exe -H "Authorization: Bearer local-dev-token" http://localhost:8000/partners/health
```

MQTT live processing:

```powershell
docker compose logs --tail=80 mqtt-worker
```

## Lưu Ý Payload

- Raw IoT input từ simulator/HiveMQ theo `IoTIngestion_README.md` dùng `snake_case`, ví dụ `event_id`, `device_id`, `temperature_c`.
- Processed IoT event publish lên `smart-campus/events/sensor` cũng theo README, chủ yếu dùng `snake_case`.
- Contract REST/OpenAPI events dùng `camelCase`, ví dụ `eventId`, `eventType`, `deviceId`, `sensorType`, `locationId`.

## Minh Chứng Cần Lưu

Lưu ảnh chụp/log vào `reports/`:

- [ ] `reports/docker-compose-ps.png`
- [ ] `reports/health-local.png`
- [ ] `reports/health-partner.png`
- [ ] `reports/integration-request-response.png`
- [x] `reports/logs-compose.txt`
- [x] `reports/integration-request-response.txt`
- [x] `reports/raw-demo-request.json`
- [x] `reports/readiness-checklist.md`

## Rubric Gợi Ý

| Tiêu chí | Điểm |
| --- | ---: |
| Service chạy ổn định trên máy demo, `/health` thành công | 2.0 |
| Nhóm khác gọi được service qua Radmin IP | 2.0 |
| Endpoint tích hợp đúng OpenAPI đã chốt | 1.5 |
| Có xử lý timeout hoặc lỗi từ service phụ thuộc | 1.5 |
| Có minh chứng: log, ảnh, request/response hoặc payload MQTT | 1.5 |
| Trình bày demo rõ ràng, đúng luồng tích hợp | 1.5 |
| Tổng | 10.0 |

Trọng tâm Buổi 6 là khả năng bắt tay thật giữa các service, không phải slide dài.

## Kết Quả Hiện Tại

```text
Docker compose:
- Đã từng chạy được với api, db, ai-service và mqtt-worker.
- Cần chạy lại trên lớp sau khi Docker Desktop sẵn sàng.

Local /health:
- Đã từng trả status=ok.
- Cần test lại ngay trước demo.

Partner /health:
- Chưa tick vì cần Radmin IP thật của nhóm đối tác.

IoT MQTT live:
- Đã có log mqtt-worker xử lý raw IoT và publish processed event.

Endpoint tích hợp chính:
- Đã có reports/raw-demo-request.json.
- Đã có reports/integration-request-response.txt.

Timeout/failure handling:
- REQUEST_TIMEOUT được đọc từ .env.
- /partners/health trả lời có error/statusCode thay vì treo vô hạn khi partner lỗi.
```
