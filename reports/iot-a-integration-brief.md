# Nghiệp Vụ Tích Hợp Với IoT A

## 1. Thông tin chung

Nhóm IoT A nhận dữ liệu cảm biến realtime từ HiveMQ, làm sạch dữ liệu, kiểm tra thiết bị, phân loại trạng thái môi trường, sau đó publish processed event cho các service phía sau.

```text
Service: IoT A
sourceService: a1-iot-ingestion
Output topic: smart-campus/events/sensor
Cơ chế: MQTT publish/subscribe
```

Payload IoT A gửi đi là processed event, không phải raw data.

## 2. Payload IoT A publish

Ví dụ processed event:

```json
{
  "eventId": "sensor-event-...",
  "eventType": "sensor.reading.processed",
  "sourceService": "a1-iot-ingestion",
  "timestamp": "2026-06-20T14:45:33+07:00",
  "rawEventId": "raw-iot-...",
  "deviceId": "esp32-lab-a101",
  "location": "Lab A101",
  "temperatureC": 31.5,
  "humidityPercent": 87.2,
  "motionDetected": false,
  "lightLux": 438,
  "co2Ppm": 665,
  "smokePpm": 0.02,
  "batteryPercent": 63,
  "status": "warning",
  "alertLevel": "medium",
  "reason": "humidity_warning"
}
```

## 3. Core Business cần làm gì

Core Business subscribe topic:

```text
smart-campus/events/sensor
```

Core chỉ xử lý event của IoT A:

```text
sourceService = a1-iot-ingestion
```

Core dùng event để ra quyết định có cần tạo cảnh báo hay không.

Core cần đọc các field:

```text
deviceId
location
timestamp
status
alertLevel
reason
temperatureC
co2Ppm
smokePpm
motionDetected
```

Rule gợi ý cho Core:

```text
status = danger
-> tạo alert mức high/critical

status = warning
-> tạo alert mức medium

status = sensor_error
-> tạo alert lỗi cảm biến

status = invalid_device
-> tạo alert thiết bị không hợp lệ

status = normal
-> không tạo alert, chỉ ghi nhận nếu cần
```

Một số reason quan trọng:

```text
temperature_too_high
co2_too_high
smoke_detected
temperature_warning
humidity_warning
co2_warning
smoke_warning
low_battery
missing_sensor_value
invalid_sensor_value
device_not_registered
environment_normal
```

Core không cần làm dashboard từ toàn bộ dữ liệu sensor. Core tập trung vào policy và cảnh báo. Nếu cần gửi thông báo, Core sẽ gửi tiếp sang Notification.

## 4. Analytics cần làm gì

Analytics subscribe topic:

```text
smart-campus/events/sensor
```

Analytics chỉ lấy event của IoT A:

```text
sourceService = a1-iot-ingestion
```

Analytics dùng dữ liệu để tổng hợp KPI và dashboard.

Analytics cần đọc các field:

```text
deviceId
location
timestamp
temperatureC
humidityPercent
lightLux
co2Ppm
smokePpm
batteryPercent
status
alertLevel
reason
```

KPI gợi ý cho Analytics:

```text
avg_temperature_by_room
avg_humidity_by_room
co2_average_by_room
smoke_alert_count
warning_event_count
danger_event_count
low_battery_device_count
sensor_error_count
invalid_device_count
```

Dashboard gợi ý:

```text
Nhiệt độ theo phòng
Độ ẩm theo phòng
CO2 theo thời gian
Số lượng warning/danger
Thiết bị pin yếu
Thiết bị lỗi hoặc không hợp lệ
```

Analytics không tạo alert và không gửi Notification. Analytics chỉ lưu, tổng hợp và hiển thị dữ liệu.

## 5. Lưu ý khi có nhiều nhóm IoT

Topic `smart-campus/events/sensor` có thể có nhiều nhóm IoT publish cùng lúc.

Core và Analytics cần filter đúng nguồn IoT A:

```python
if payload.get("sourceService") != "a1-iot-ingestion":
    return
```

Nếu nhận payload có:

```json
{
  "source_service": "b1-iot-ingestion"
}
```

thì đó là IoT B, không phải IoT A.

Nếu nhận payload có:

```json
{
  "sourceService": "a1-iot-ingestion"
}
```

thì đó là event của IoT A.

## 6. Tóm tắt luồng tích hợp

```text
Pi IoT Simulator
-> smart-campus/raw/iot/environment
-> IoT A validate + normalize + check registry + classify
-> smart-campus/events/sensor
-> Core Business tạo alert nếu cần
-> Analytics tổng hợp KPI/dashboard
```
