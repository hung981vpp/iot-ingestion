# Giải Thích Demo Buổi 6 - Team IoT Ingestion

Tài liệu này dùng để trả lời nhanh khi giảng viên hỏi service của nhóm làm gì, nhận gì, xử lý ra sao, gửi cho ai và minh chứng nằm ở đâu.

## 1. Vai Trò Của Nhóm

Nhóm IoT xây dựng **IoT Ingestion Service** cho Smart Campus Operations Platform.

Service có nhiệm vụ nhận dữ liệu cảm biến môi trường dạng raw từ HiveMQ, kiểm tra dữ liệu đầu vào, chuẩn hóa, phân loại trạng thái môi trường, rồi publish event sạch cho các service tiếp theo.

Vai trò của nhóm:

- Là **consumer** của dữ liệu raw từ Pi IoT Simulator.
- Là **provider** dữ liệu processed sensor event cho Core Business và Analytics.
- Giao tiếp nghiệp vụ chính bằng **MQTT async**.
- Expose REST `/health` để các nhóm khác kiểm tra service còn sống.

Luồng tổng quát:

```text
Pi IoT Simulator
-> HiveMQ topic smart-campus/raw/iot/environment
-> IoT Ingestion Service
-> Validate + Normalize + Classify + Transform
-> HiveMQ topic smart-campus/events/sensor
-> Core Business / Analytics
```

## 2. Input

Input chính là raw IoT payload từ HiveMQ.

Topic subscribe:

```text
smart-campus/raw/iot/environment
```

Simulator gửi dữ liệu khoảng 5 giây/lần.

Payload raw dùng `snake_case` vì đây là dữ liệu do simulator cung cấp:

```json
{
  "event_id": "raw-iot-abc123",
  "event_type": "iot.environment.sampled",
  "source_service": "pi-iot-simulator",
  "device_id": "esp32-lab-a101",
  "timestamp": "2026-06-07T14:30:10+07:00",
  "location": "Lab A101",
  "temperature_c": 31.2,
  "humidity_percent": 68.5,
  "motion_detected": false,
  "light_lux": 420,
  "co2_ppm": 650,
  "smoke_ppm": 0.02,
  "battery_percent": 87,
  "scenario_hint_for_teacher": "normal"
}
```

Các field bắt buộc:

```text
event_id
event_type
timestamp
device_id
temperature_c
humidity_percent
motion_detected
```

Lưu ý:

- Raw input chưa có kết luận `normal`, `warning`, `danger`.
- Raw input chưa có `alertLevel`.
- Raw input có thể lỗi: null, sai kiểu dữ liệu, thiết bị lạ, vượt ngưỡng.
- `scenario_hint_for_teacher` chỉ để giảng viên debug/chấm scenario, service không dùng field này để xử lý nghiệp vụ.

## 3. Xử Lý Nghiệp Vụ

Code xử lý chính nằm ở:

```text
src/iot_app/processor.py
src/iot_app/mqtt_worker.py
```

### 3.1. Load Registry Thiết Bị

Service đọc danh sách thiết bị hợp lệ từ:

```text
data/IoT_device_registry.csv
```

Registry hiện có 5 thiết bị:

```text
esp32-lab-a101
esp32-lab-a102
esp32-gate-a
esp32-library-01
esp32-hall-b201
```

Log xác nhận:

```text
loaded_registry count=5 path=data/IoT_device_registry.csv
```

Nếu `device_id` không tồn tại trong registry:

```json
{
  "status": "invalid_device",
  "alertLevel": "high",
  "reason": "device_not_registered"
}
```

### 3.2. Validate Schema Đầu Vào

Nếu thiếu field bắt buộc, service log lỗi và không publish event sai schema:

```text
invalid_raw_payload error=missing_required_field missing_fields=[...]
```

### 3.3. Normalize Dữ Liệu

Trước khi xử lý, service chuẩn hóa:

- Timestamp phải đúng ISO 8601.
- Nhiệt độ giữ đơn vị Celsius.
- Độ ẩm giữ đơn vị phần trăm.
- Ép kiểu number cho `temperature_c`, `humidity_percent`, `light_lux`, `co2_ppm`, `smoke_ppm`, `battery_percent`.
- Ép kiểu boolean cho `motion_detected`.
- Loại bỏ `scenario_hint_for_teacher`.

Nếu normalize lỗi:

```json
{
  "status": "sensor_error",
  "alertLevel": "medium",
  "reason": "normalization_failed"
}
```

### 3.4. Classify Trạng Thái Môi Trường

Rule hiện dùng:

```text
sensor_error:
- temperature_c = null
- humidity_percent = null
- dữ liệu không đúng kiểu số

invalid_device:
- device_id không tồn tại trong device_registry.csv

danger:
- temperature_c >= 40
- co2_ppm >= 1800
- smoke_ppm >= 1.0

warning:
- temperature_c >= 35
- humidity_percent >= 85
- co2_ppm >= 1200
- smoke_ppm >= 0.5
- battery_percent < 20

normal:
- Không rơi vào các trường hợp trên
```

Các scenario đã thấy trong log:

```text
normal
warning
danger
sensorError
invalidDevice
```

## 4. Output

Output là processed sensor event gửi cho Core/Analytics.

Hợp đồng output dùng **camelCase**.

Output topic:

```text
smart-campus/events/sensor
```

Payload mẫu khi cảnh báo nhiệt độ:

```json
{
  "eventId": "sensor-event-39a15cc5-40ef-4ed6-bba2-123fe1c397b0",
  "eventType": "sensor.reading.processed",
  "sourceService": "team-iot",
  "timestamp": "2026-06-14T20:00:00Z",
  "rawEventId": "raw-demo-001",
  "deviceId": "esp32-lab-a101",
  "location": "Lab A101",
  "temperatureC": 38.5,
  "humidityPercent": 70,
  "motionDetected": true,
  "lightLux": 400,
  "co2Ppm": 800,
  "smokePpm": 0,
  "batteryPercent": 90,
  "status": "warning",
  "alertLevel": "medium",
  "reason": "temperature_warning"
}
```

Payload khi thiết bị lạ:

```json
{
  "eventType": "sensor.reading.processed",
  "sourceService": "team-iot",
  "deviceId": "esp32-unknown-01",
  "location": "Unknown Area",
  "status": "invalid_device",
  "alertLevel": "high",
  "reason": "device_not_registered"
}
```

## 5. Output Gửi Cho Ai?

IoT publish processed event cho:

- **Core Business**
- **Analytics**

Cơ chế chính:

```text
MQTT publish
Topic: smart-campus/events/sensor
QoS: 1
```

Core Business dùng event để:

- Kiểm tra policy ngưỡng nhiệt độ, khói, CO2.
- Tạo alert nếu `status = warning` hoặc `status = danger`.
- Kết hợp `motionDetected` với khung giờ để phát hiện bất thường.
- Gửi alert sang Notification nếu cần.

Analytics dùng event để:

- Tính nhiệt độ trung bình theo phòng.
- Tính độ ẩm trung bình theo thời gian.
- Đếm số lần warning/danger theo ngày.
- Theo dõi pin yếu theo thiết bị.
- Vẽ biểu đồ CO2, smoke, temperature theo timeline.

Health check đối tác qua Radmin:

```text
Core:      http://26.183.48.228:8000/health -> ok=true, 200
Analytics: http://26.169.171.221:8000/health -> ok=true, 200
```

Radmin IP của team IoT:

```text
26.7.138.126
```

Nhóm khác kiểm tra team IoT:

```text
http://26.7.138.126:8000/health
```

## 6. Minh Chứng Demo

Các lệnh cần chạy khi giảng viên kiểm tra:

```powershell
docker compose ps
curl.exe http://localhost:8000/health
curl.exe -H "Authorization: Bearer local-dev-token" http://localhost:8000/partners/health
docker compose logs --tail=100 mqtt-worker
```

Minh chứng hiện có trong repo:

```text
reports/readiness-checklist.md
reports/raw-demo-request.json
reports/integration-request-response.txt
reports/logs-compose.txt
```

Minh chứng MQTT cần chỉ ra trong log:

```text
mqtt_connected reason_code=Success input_topic=smart-campus/raw/iot/environment
processed_raw raw_event_id=... device_id=... status=...
published_processed_event topic=smart-campus/events/sensor event_id=... status=...
```

Minh chứng tích hợp Analytics:

```text
Analytics đã subscribe smart-campus/events/sensor
Analytics đã nhận payload có eventType=sensor.reading.processed
Analytics đã parse được deviceId, temperatureC, humidityPercent, status, alertLevel
```

Minh chứng xử lý service phụ thuộc:

```text
/partners/health dùng REQUEST_TIMEOUT=5.
Nếu Core/Analytics lỗi hoặc timeout, response trả ok=false kèm error/statusCode, không treo vô hạn.
```

## Câu Trả Lời Ngắn Khi Bị Hỏi

```text
Team IoT nhận raw sensor data từ smart-campus/raw/iot/environment.
Service validate schema, đọc device_registry.csv, normalize dữ liệu, bỏ scenario_hint_for_teacher, classify normal/warning/danger/sensor_error/invalid_device.
Sau đó service publish processed event camelCase lên smart-campus/events/sensor cho Core và Analytics.
Core dùng để tạo alert/policy; Analytics dùng để aggregate KPI/dashboard.
Minh chứng nằm trong reports/ và log mqtt-worker.
```
