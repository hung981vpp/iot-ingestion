# Checklist Sẵn Sàng Demo Buổi 6 - IoT Ingestion

Tick từng mục trước khi báo nhóm đã sẵn sàng demo. Các mục cần xác nhận từ Radmin/nhóm đối tác chỉ tick sau khi test thật.

- [x] Máy demo chính đã cài Radmin VPN.
- [x] Đã join đúng Radmin Network của Product/cụm demo.
- [x] Đã ghi Radmin IP vào bảng chung.
- [x] Service chạy bằng Docker Compose.
- [x] `docker compose ps` hiển thị container running.
- [x] `GET /health` local thành công.
- [x] Nhóm đối tác gọi được `/health` qua Radmin IP.
- [x] `.env` đã dùng Radmin IP của nhóm đối tác.
- [x] Mình gọi được Core `/health` qua `/partners/health`.
- [x] Mình gọi được Analytics `/health` qua `/partners/health`.
- [x] Endpoint nghiệp vụ hoặc MQTT topic đã test.
- [x] Có log xử lý input/output.
- [x] Có request/response hoặc payload MQTT mẫu.
- [x] Có minh chứng trong `reports/`.
- [x] Có xử lý timeout hoặc lỗi từ service phụ thuộc.

## Cần Tick Khi Lên Lớp

```text
[x] Máy demo chính đã cài Radmin VPN
[x] Đã join đúng Radmin Network của Product/cụm demo
[x] Đã ghi Radmin IP vào bảng chung
[x] docker compose ps hiển thị container running
[x] GET /health local thành công
[x] Nhóm đối tác gọi được /health qua Radmin IP
[x] .env đã dùng Radmin IP của nhóm đối tác
[x] Core health qua /partners/health ok=true
[x] Analytics health qua /partners/health ok=true
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

- Raw IoT input từ simulator/HiveMQ dùng `snake_case`, ví dụ `event_id`, `device_id`, `temperature_c`.
- Processed event gửi cho Core/Analytics dùng `camelCase`, ví dụ `eventId`, `eventType`, `deviceId`, `temperatureC`, `alertLevel`.
- Không publish field `scenario_hint_for_teacher`.

## Minh Chứng Cần Lưu

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

## Kết Quả Hiện Tại

```text
Radmin IP team-iot:
- 26.7.138.126

Local /health:
- OK, status=ok.

Partner /health:
- Core: ok=true, statusCode=200, url=http://26.183.48.228:8000/health
- Analytics: ok=true, statusCode=200, url=http://26.169.171.221:8000/health

IoT MQTT live:
- mqtt-worker đã nhận raw IoT và publish processed event lên smart-campus/events/sensor.

Endpoint tích hợp chính:
- reports/raw-demo-request.json
- reports/integration-request-response.txt

Timeout/failure handling:
- REQUEST_TIMEOUT=5.
- /partners/health trả error/statusCode thay vì treo vô hạn khi partner lỗi.
```
