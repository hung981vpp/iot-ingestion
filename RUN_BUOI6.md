# Chạy Buổi 6 - IoT Ingestion

Buổi 6 tập trung vào service chạy thật, gọi thật và có minh chứng thật. Không cần tập trung vào slide dài.

## 1. Chạy Service

```powershell
docker compose --profile mqtt up -d --build
docker compose --profile mqtt ps
```

Cần thấy các service chính đang chạy:

- `api`
- `db`
- `mqtt-worker`
- `ai-service` nếu vẫn giữ trong stack demo

## 2. Kiểm Tra Health Local

```powershell
curl.exe http://localhost:8000/health
```

Kỳ vọng:

```json
{"status":"ok","service":"iot-ingestion","version":"0.5.0"}
```

## 3. Kiểm Tra MQTT Live

```powershell
docker compose logs --tail=80 mqtt-worker
```

Cần thấy log có các từ khóa:

- `mqtt_connected`
- `processed_raw`
- `published_processed_event`

Processed event được publish lên topic:

```text
smart-campus/events/sensor
```

## 4. Cập Nhật URL Nhóm Đối Tác

Không hardcode IP trong code. Cập nhật `.env`:

```env
CORE_SERVICE_URL=http://172.20.10.x:8000
ANALYTICS_SERVICE_URL=http://172.20.10.y:8000
REQUEST_TIMEOUT=5
```

Sau khi sửa `.env`, chạy lại:

```powershell
docker compose up -d
curl.exe -H "Authorization: Bearer local-dev-token" http://localhost:8000/partners/health
```

## 5. Công Bố Service Của Nhóm Mình

Lấy IP máy demo:

```powershell
ipconfig
```

Công bố cho nhóm khác:

```text
http://<IP_MAY_MINH>:8000/health
```

Lưu ý:

- Trong cùng laptop/container: có thể dùng Docker service name.
- Qua laptop khác/hotspot: phải dùng IP máy host và port.
- Không dùng `localhost`, `127.0.0.1`, `api`, `db`, `ai-service` để gọi máy nhóm khác.

## 6. Endpoint Tích Hợp Chính

Test processed events:

```powershell
curl.exe -H "Authorization: Bearer local-dev-token" http://localhost:8000/iot/processed-events
```

Test xử lý raw payload mẫu:

```powershell
curl.exe -X POST http://localhost:8000/iot/raw/process `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer local-dev-token" `
  --data-binary "@reports/raw-demo-request.json"
```

Quy ước đặt tên field:

- Raw IoT input từ simulator/HiveMQ theo `IoTIngestion_README.md` dùng `snake_case`.
- Processed IoT event publish lên `smart-campus/events/sensor` cũng theo README, chủ yếu dùng `snake_case`.
- Contract REST/OpenAPI events dùng `camelCase`.
- Vì vậy `reports/raw-demo-request.json` dùng `event_id`, `device_id`, `temperature_c` là đúng cho raw IoT input.

## 7. Rubric Gợi Ý

| Tiêu chí | Điểm |
| --- | ---: |
| Service chạy ổn định trên máy demo, `/health` thành công | 2.0 |
| Nhóm khác gọi được service qua hotspot/IP | 2.0 |
| Endpoint tích hợp đúng OpenAPI đã chốt | 1.5 |
| Có xử lý timeout hoặc lỗi từ service phụ thuộc | 1.5 |
| Có minh chứng: log, ảnh, Newman report, request/response | 1.5 |
| Trình bày demo rõ ràng, đúng luồng tích hợp | 1.5 |
| Tổng | 10.0 |

## 8. Minh Chứng Cần Nộp

Thư mục `reports/` cần có:

```text
reports/
+-- docker-compose-ps.png
+-- health-local.png
+-- health-partner.png
+-- integration-request-response.png
+-- logs-compose.txt
+-- newman-report.html hoặc newman-report.xml
+-- readiness-checklist.md
```

Có thể tạo log text:

```powershell
docker compose --profile mqtt ps > reports/logs-compose.txt
docker compose logs --tail=120 mqtt-worker >> reports/logs-compose.txt
```
