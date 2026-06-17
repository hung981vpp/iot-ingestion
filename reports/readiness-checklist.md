# Checklist Sẵn Sàng Demo Buổi 6 - IoT Ingestion

Tick từng mục trước khi báo nhóm đã sẵn sàng demo.

- [ ] Máy demo đã kết nối đúng hotspot của Product.
- [ ] Đã lấy IP máy demo và công bố cho Product/nhóm đối tác.
- [ ] Đã cập nhật `.env` với URL nhóm đối tác.
- [ ] `docker compose --profile mqtt ps` hiển thị các container cần thiết đang chạy.
- [ ] `GET /health` của nhóm mình trả thành công.
- [ ] Nhóm khác gọi được `GET /health` của nhóm mình qua IP hotspot.
- [ ] Mình gọi được `GET /health` của nhóm đối tác qua `/partners/health`.
- [ ] Endpoint tích hợp chính đã test bằng request mẫu.
- [ ] MQTT worker nhận dữ liệu live và publish processed event.
- [ ] Có log, screenshot, request/response mẫu.
- [ ] Có phương án xử lý timeout hoặc service phụ thuộc lỗi.

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
- [ ] `reports/logs-compose.txt`
- [ ] `reports/newman-report.html` hoặc `reports/newman-report.xml`
- [x] `reports/readiness-checklist.md`

## Rubric Gợi Ý

| Tiêu chí | Điểm |
| --- | ---: |
| Service chạy ổn định trên máy demo, `/health` thành công | 2.0 |
| Nhóm khác gọi được service qua hotspot/IP | 2.0 |
| Endpoint tích hợp đúng OpenAPI đã chốt | 1.5 |
| Có xử lý timeout hoặc lỗi từ service phụ thuộc | 1.5 |
| Có minh chứng: log, ảnh, Newman report, request/response | 1.5 |
| Trình bày demo rõ ràng, đúng luồng tích hợp | 1.5 |
| Tổng | 10.0 |

Trọng tâm Buổi 6 là khả năng bắt tay thật giữa các service, không phải slide dài.

## Kết Quả Hiện Tại

Cập nhật trong lúc chuẩn bị demo:

```text
Docker compose:
- Chưa cập nhật

Local /health:
- Chưa cập nhật

Partner /health:
- Chưa cập nhật

IoT MQTT live:
- Chưa cập nhật

Endpoint tích hợp chính:
- Chưa cập nhật

Timeout/failure handling:
- REQUEST_TIMEOUT được đọc từ .env.
- /partners/health trả lời có error/statusCode thay vì treo vô hạn khi partner lỗi.
```
