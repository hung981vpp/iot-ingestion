import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


SOURCE_SERVICE = "iot-ingestion"


@dataclass(frozen=True)
class DeviceRecord:
    device_id: str
    device_type: str
    location: str
    room: str
    status: str


@dataclass(frozen=True)
class ProcessedRawSample:
    raw_event_id: str
    device_id: str
    status: str
    alert_level: str
    reason: str
    processed_event: Optional[Dict[str, Any]]
    events: List[Dict[str, Any]]


def load_device_registry(path: str | Path) -> Dict[str, DeviceRecord]:
    registry_path = Path(path)
    with registry_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return {
            row["device_id"]: DeviceRecord(
                device_id=row["device_id"],
                device_type=row.get("device_type", ""),
                location=row.get("location", ""),
                room=row.get("room", ""),
                status=row.get("status", ""),
            )
            for row in reader
        }


def validate_raw_payload(payload: Dict[str, Any]) -> List[str]:
    required = [
        "event_id",
        "event_type",
        "source_service",
        "device_id",
        "timestamp",
        "temperature_c",
        "humidity_percent",
        "motion_detected",
    ]
    return [field for field in required if field not in payload]


def classify_raw_payload(payload: Dict[str, Any], device: Optional[DeviceRecord]) -> tuple[str, str, str]:
    if device is None:
        return "invalidDevice", "high", "deviceNotRegistered"
    if device.status != "active":
        return "invalidDevice", "high", "deviceInactive"

    temperature = payload.get("temperature_c")
    humidity = payload.get("humidity_percent")
    co2 = payload.get("co2_ppm")
    smoke = payload.get("smoke_ppm")
    battery = payload.get("battery_percent")

    if temperature is None or humidity is None:
        return "sensorError", "medium", "missingSensorValue"

    numeric_values = [temperature, humidity, co2, smoke, battery]
    if any(value is not None and not isinstance(value, (int, float)) for value in numeric_values):
        return "sensorError", "medium", "invalidSensorValue"

    if temperature >= 40:
        return "danger", "high", "temperatureTooHigh"
    if co2 is not None and co2 >= 1800:
        return "danger", "high", "co2TooHigh"
    if smoke is not None and smoke >= 1.0:
        return "danger", "high", "smokeDetected"

    if temperature >= 35:
        return "warning", "medium", "temperatureWarning"
    if humidity >= 85:
        return "warning", "medium", "humidityWarning"
    if co2 is not None and co2 >= 1200:
        return "warning", "medium", "co2Warning"
    if smoke is not None and smoke >= 0.5:
        return "warning", "medium", "smokeWarning"
    if battery is not None and battery < 20:
        return "warning", "medium", "lowBattery"

    return "normal", "none", "environmentNormal"


def build_event(event_type: str, timestamp: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "eventId": str(uuid4()),
        "eventType": event_type,
        "timestamp": timestamp,
        "source": SOURCE_SERVICE,
        "data": data,
    }


def to_processed_status(status: str) -> str:
    return {
        "sensorError": "sensor_error",
        "invalidDevice": "invalid_device",
    }.get(status, status)


def to_processed_reason(reason: str) -> str:
    return {
        "deviceNotRegistered": "device_not_registered",
        "deviceInactive": "device_inactive",
        "missingRequiredField": "missing_required_field",
        "missingSensorValue": "missing_sensor_value",
        "invalidSensorValue": "invalid_sensor_value",
        "temperatureTooHigh": "temperature_too_high",
        "co2TooHigh": "co2_too_high",
        "smokeDetected": "smoke_detected",
        "temperatureWarning": "temperature_warning",
        "humidityWarning": "humidity_warning",
        "co2Warning": "co2_warning",
        "smokeWarning": "smoke_warning",
        "lowBattery": "low_battery",
        "environmentNormal": "environment_normal",
    }.get(reason, reason)


def build_processed_event(
    payload: Dict[str, Any],
    *,
    status: str,
    alert_level: str,
    reason: str,
    device: Optional[DeviceRecord],
) -> Dict[str, Any]:
    return {
        "event_id": f"sensor-event-{uuid4()}",
        "event_type": "sensor.reading.processed",
        "source_service": "team-iot",
        "timestamp": payload["timestamp"],
        "raw_event_id": payload.get("event_id"),
        "device_id": payload["device_id"],
        "location": device.location if device else payload.get("location", "Unknown Area"),
        "temperature_c": payload.get("temperature_c"),
        "humidity_percent": payload.get("humidity_percent"),
        "motion_detected": payload.get("motion_detected"),
        "light_lux": payload.get("light_lux"),
        "co2_ppm": payload.get("co2_ppm"),
        "smoke_ppm": payload.get("smoke_ppm"),
        "battery_percent": payload.get("battery_percent"),
        "status": to_processed_status(status),
        "alert_level": alert_level,
        "reason": to_processed_reason(reason),
    }


def build_sensor_reading_events(payload: Dict[str, Any], device: DeviceRecord) -> List[Dict[str, Any]]:
    base = {
        "deviceId": payload["device_id"],
        "timestamp": payload["timestamp"],
        "locationId": device.room or None,
        "correlationId": None,
    }
    values = [
        ("temperature", payload.get("temperature_c"), "celsius"),
        ("humidity", payload.get("humidity_percent"), "percent"),
        ("motion", payload.get("motion_detected"), "boolean"),
        ("smoke", payload.get("smoke_ppm"), "ppm"),
    ]

    events = []
    for sensor_type, value, unit in values:
        if value is None:
            continue
        data = {**base, "sensorType": sensor_type, "value": value, "unit": unit}
        events.append(build_event("sensor.reading.created", payload["timestamp"], data))
    return events


def build_telemetry_events(payload: Dict[str, Any], device: DeviceRecord) -> List[Dict[str, Any]]:
    base = {
        "deviceId": payload["device_id"],
        "timestamp": payload["timestamp"],
        "zoneId": device.room or None,
        "batchId": None,
    }
    values = [
        ("temperature", payload.get("temperature_c"), "celsius"),
        ("humidity", payload.get("humidity_percent"), "percent"),
        ("motion", payload.get("motion_detected"), "boolean"),
        ("smoke", payload.get("smoke_ppm"), "ppm"),
    ]

    events = []
    for sensor_type, value, unit in values:
        if value is None:
            continue
        data = {**base, "sensorType": sensor_type, "value": value, "unit": unit}
        events.append(build_event("telemetry.ingested", payload["timestamp"], data))
    return events


def build_threshold_events(payload: Dict[str, Any], device: DeviceRecord) -> List[Dict[str, Any]]:
    thresholds = [
        ("temperature", payload.get("temperature_c"), 35.0, 40.0, "celsius"),
        ("humidity", payload.get("humidity_percent"), 85.0, None, "percent"),
        ("smoke", payload.get("smoke_ppm"), 0.5, 1.0, "ppm"),
    ]

    events = []
    for sensor_type, value, warning, critical, unit in thresholds:
        if value is None:
            continue
        if critical is not None and value >= critical:
            threshold = critical
            severity = "CRITICAL"
        elif value >= warning:
            threshold = warning
            severity = "HIGH"
        else:
            continue

        data = {
            "deviceId": payload["device_id"],
            "sensorType": sensor_type,
            "value": value,
            "threshold": threshold,
            "unit": unit,
            "timestamp": payload["timestamp"],
            "severity": severity,
            "locationId": device.room or None,
        }
        events.append(build_event("sensor.threshold.exceeded", payload["timestamp"], data))
    return events


def process_raw_sample(payload: Dict[str, Any], registry: Dict[str, DeviceRecord]) -> ProcessedRawSample:
    missing = validate_raw_payload(payload)
    if missing:
        return ProcessedRawSample(
            raw_event_id=str(payload.get("event_id", "")),
            device_id=str(payload.get("device_id", "")),
            status="sensorError",
            alert_level="medium",
            reason="missingRequiredField",
            processed_event=None,
            events=[],
        )

    device_id = payload["device_id"]
    device = registry.get(device_id)
    status, alert_level, reason = classify_raw_payload(payload, device)

    if device is None or status in {"invalidDevice", "sensorError"}:
        return ProcessedRawSample(
            raw_event_id=payload["event_id"],
            device_id=device_id,
            status=status,
            alert_level=alert_level,
            reason=reason,
            processed_event=build_processed_event(
                payload,
                status=status,
                alert_level=alert_level,
                reason=reason,
                device=device,
            ),
            events=[],
        )

    events: List[Dict[str, Any]] = []
    events.extend(build_sensor_reading_events(payload, device))
    events.extend(build_threshold_events(payload, device))
    events.extend(build_telemetry_events(payload, device))

    return ProcessedRawSample(
        raw_event_id=payload["event_id"],
        device_id=device_id,
        status=status,
        alert_level=alert_level,
        reason=reason,
        processed_event=build_processed_event(
            payload,
            status=status,
            alert_level=alert_level,
            reason=reason,
            device=device,
        ),
        events=events,
    )


def topic_for_event(event: Dict[str, Any], sensor_topic: str, telemetry_topic: str) -> str:
    if event["eventType"] in {"sensor.reading.created", "sensor.threshold.exceeded"}:
        return sensor_topic
    return telemetry_topic
