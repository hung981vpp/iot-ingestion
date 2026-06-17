import os
from datetime import datetime, timezone
from enum import Enum
from http import HTTPStatus
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from iot_app.processor import load_device_registry, process_raw_sample

# Đọc biến môi trường với giá trị mặc định
SERVICE_NAME = os.getenv("SERVICE_NAME", "iot-ingestion")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.5.0")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")
CORE_SERVICE_URL = os.getenv("CORE_SERVICE_URL", "").rstrip("/")
ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "").rstrip("/")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "5"))
DEVICE_REGISTRY_PATH = os.getenv("DEVICE_REGISTRY_PATH", "data/IoT_device_registry.csv")


def status_title(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP Error"


app = FastAPI(
    title="FIT4110 Lab 05 - IoT Ingestion Service",
    version=SERVICE_VERSION,
    description=(
        "IoT Ingestion API chạy trong ngữ cảnh Docker Compose cho Lab 05. "
        "Luồng logic được kế thừa từ Lab 04 và tiếp tục được dùng để kiểm thử end‑to‑end."
    ),
)


class SensorMetric(str, Enum):
    temperature = "temperature"
    humidity = "humidity"
    motion = "motion"
    smoke = "smoke"


class SensorUnit(str, Enum):
    celsius = "celsius"
    percent = "percent"
    boolean = "boolean"
    ppm = "ppm"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DeviceAvailability(str, Enum):
    online = "online"
    offline = "offline"
    maintenance = "maintenance"


class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int = Field(..., ge=400, le=599)
    detail: str
    instance: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class SensorReadingCreate(BaseModel):
    device_id: str = Field(..., min_length=3, examples=["ESP32-LAB-A01"])
    metric: SensorMetric = Field(..., examples=["temperature"])
    value: float = Field(
        ...,
        ge=-40,
        le=80,
        description="Boundary range used in Lab 03 và Lab 04: -40 đến 80.",
        examples=[31.5],
    )
    unit: Optional[SensorUnit] = Field(default=None, examples=["celsius"])
    timestamp: str = Field(..., examples=["2026-05-13T08:30:00+07:00"])


class SensorReading(BaseModel):
    reading_id: str
    device_id: str
    metric: SensorMetric
    value: float
    unit: Optional[SensorUnit] = None
    timestamp: str
    created_at: str


class SensorReadingCreated(BaseModel):
    reading_id: str
    device_id: str
    metric: SensorMetric
    accepted: bool
    created_at: str


class ContractModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ContractSensorReadingCreate(ContractModel):
    device_id: str = Field(..., alias="deviceId", min_length=3, examples=["SENSOR-001"])
    sensor_type: SensorMetric = Field(..., alias="sensorType", examples=["temperature"])
    value: float = Field(..., ge=-100, le=1000, examples=[38.5])
    unit: SensorUnit = Field(..., examples=["celsius"])
    timestamp: str = Field(..., examples=["2026-05-12T10:30:00Z"])
    location_id: Optional[str] = Field(default=None, alias="locationId", examples=["ZONE-A-01"])
    correlation_id: Optional[str] = Field(default=None, alias="correlationId")


class ContractSensorReading(ContractSensorReadingCreate):
    id: str
    created_at: str = Field(..., alias="createdAt")


class ContractSensorReadingList(ContractModel):
    items: List[ContractSensorReading]
    total: int
    next_cursor: Optional[str] = Field(default=None, alias="nextCursor")


class ContractThresholdData(ContractModel):
    device_id: str = Field(..., alias="deviceId")
    sensor_type: SensorMetric = Field(..., alias="sensorType")
    value: float
    threshold: float
    unit: Optional[SensorUnit] = None
    timestamp: str
    severity: Optional[Severity] = None
    location_id: Optional[str] = Field(default=None, alias="locationId")


class ContractTelemetryData(ContractModel):
    device_id: str = Field(..., alias="deviceId")
    sensor_type: SensorMetric = Field(..., alias="sensorType")
    value: float
    unit: SensorUnit
    timestamp: str
    zone_id: Optional[str] = Field(default=None, alias="zoneId")
    batch_id: Optional[str] = Field(default=None, alias="batchId")


class ContractDeviceStatus(ContractModel):
    device_id: str = Field(..., alias="deviceId")
    status: DeviceAvailability
    timestamp: str
    previous_status: Optional[DeviceAvailability] = Field(default=None, alias="previousStatus")
    reason: Optional[str] = None


class ContractEvent(ContractModel):
    event_id: str = Field(..., alias="eventId")
    event_type: str = Field(..., alias="eventType")
    timestamp: str
    source: str
    data: Dict


class ContractEventList(ContractModel):
    items: List[ContractEvent]
    total: int
    next_cursor: Optional[str] = Field(default=None, alias="nextCursor")


class PartnerHealth(ContractModel):
    name: str
    configured: bool
    url: Optional[str] = None
    ok: bool
    status_code: Optional[int] = Field(default=None, alias="statusCode")
    error: Optional[str] = None


class PartnerHealthList(ContractModel):
    items: List[PartnerHealth]


READINGS: List[Dict] = []
CONTRACT_READINGS: List[Dict] = []
CONTRACT_THRESHOLD_EVENTS: List[Dict] = []
CONTRACT_TELEMETRY_EVENTS: List[Dict] = []
CONTRACT_EVENTS: List[Dict] = []
DEVICE_STATUSES: Dict[str, Dict] = {}
PROCESSED_IOT_EVENTS: List[Dict] = []


def build_problem(
    *,
    status_code: int,
    title: str,
    detail: str,
    instance: Optional[str] = None,
    problem_type: str = "about:blank",
) -> Dict:
    problem = {
        "type": problem_type,
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    if instance:
        problem["instance"] = instance
    return problem


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        problem = exc.detail
    else:
        problem = build_problem(
            status_code=exc.status_code,
            title=status_title(exc.status_code),
            detail=str(exc.detail),
            instance=str(request.url.path),
        )

    problem.setdefault("status", exc.status_code)
    problem.setdefault("title", status_title(exc.status_code))
    problem.setdefault("type", "about:blank")
    problem.setdefault("detail", "Request failed")
    problem.setdefault("instance", str(request.url.path))

    return JSONResponse(
        status_code=exc.status_code,
        content=problem,
        media_type="application/problem+json",
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(item) for item in first_error.get("loc", []))
    message = first_error.get("msg", "Request validation error")
    detail = f"{location}: {message}" if location else message

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_problem(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation error",
            detail=detail,
            instance=str(request.url.path),
            problem_type="https://smart-campus.local/problems/validation-error",
        ),
        media_type="application/problem+json",
    )


def verify_bearer_token(authorization: Optional[str] = Header(default=None)) -> None:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Missing Authorization header",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )

    expected = f"Bearer {AUTH_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Invalid bearer token",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def next_reading_id() -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"R-{today}-{len(READINGS) + 1:04d}"


def build_contract_event(event_type: str, data: Dict) -> Dict:
    return {
        "eventId": str(uuid4()),
        "eventType": event_type,
        "timestamp": now_iso(),
        "source": SERVICE_NAME,
        "data": data,
    }


def threshold_for_reading(reading: Dict) -> Optional[Dict]:
    sensor_type = reading["sensorType"]
    value = reading["value"]

    thresholds = {
        "temperature": {"warning": 35.0, "critical": 40.0, "unit": "celsius"},
        "humidity": {"warning": 85.0, "critical": None, "unit": "percent"},
        "smoke": {"warning": 0.5, "critical": 1.0, "unit": "ppm"},
    }
    config = thresholds.get(sensor_type)
    if not config:
        return None

    critical = config["critical"]
    warning = config["warning"]
    if critical is not None and value >= critical:
        threshold = critical
        severity = Severity.CRITICAL.value
    elif value >= warning:
        threshold = warning
        severity = Severity.HIGH.value
    else:
        return None

    return {
        "deviceId": reading["deviceId"],
        "sensorType": sensor_type,
        "value": value,
        "threshold": threshold,
        "unit": config["unit"],
        "timestamp": reading["timestamp"],
        "severity": severity,
        "locationId": reading.get("locationId"),
    }


def remember_contract_reading(reading: Dict) -> None:
    CONTRACT_READINGS.append(reading)

    sensor_event = build_contract_event("sensor.reading.created", reading)
    CONTRACT_EVENTS.append(sensor_event)

    telemetry_data = {
        "deviceId": reading["deviceId"],
        "sensorType": reading["sensorType"],
        "value": reading["value"],
        "unit": reading["unit"],
        "timestamp": reading["timestamp"],
        "zoneId": reading.get("locationId"),
        "batchId": None,
    }
    telemetry_event = build_contract_event("telemetry.ingested", telemetry_data)
    CONTRACT_TELEMETRY_EVENTS.append(telemetry_event)
    CONTRACT_EVENTS.append(telemetry_event)

    threshold_data = threshold_for_reading(reading)
    if threshold_data:
        threshold_event = build_contract_event("sensor.threshold.exceeded", threshold_data)
        CONTRACT_THRESHOLD_EVENTS.append(threshold_event)
        CONTRACT_EVENTS.append(threshold_event)

    DEVICE_STATUSES[reading["deviceId"]] = {
        "deviceId": reading["deviceId"],
        "status": DeviceAvailability.online.value,
        "timestamp": now_iso(),
        "previousStatus": None,
        "reason": "sensorReadingReceived",
    }


def check_partner_health(name: str, base_url: str) -> Dict:
    if not base_url:
        return {
            "name": name,
            "configured": False,
            "url": None,
            "ok": False,
            "statusCode": None,
            "error": "notConfigured",
        }

    url = f"{base_url}/health"
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
    except requests.Timeout:
        return {
            "name": name,
            "configured": True,
            "url": url,
            "ok": False,
            "statusCode": None,
            "error": "timeout",
        }
    except requests.RequestException as exc:
        return {
            "name": name,
            "configured": True,
            "url": url,
            "ok": False,
            "statusCode": None,
            "error": exc.__class__.__name__,
        }

    return {
        "name": name,
        "configured": True,
        "url": url,
        "ok": response.status_code == 200,
        "statusCode": response.status_code,
        "error": None if response.status_code == 200 else "healthCheckFailed",
    }


def load_registry_for_request() -> Dict:
    return load_device_registry(Path(DEVICE_REGISTRY_PATH))


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
    )


@app.post(
    "/readings",
    response_model=SensorReadingCreated,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_bearer_token)],
    responses={
        401: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
        429: {"model": ProblemDetails},
    },
)
def create_reading(payload: SensorReadingCreate, response: Response) -> SensorReadingCreated:
    # Ví dụ logic cảnh báo: nếu nhiệt độ >= 70 thì thêm header cảnh báo
    if payload.metric == SensorMetric.temperature and payload.value >= 70:
        response.headers["X-Warning"] = "high-temperature"

    reading_id = next_reading_id()
    created_at = now_iso()

    item = {
        "reading_id": reading_id,
        "device_id": payload.device_id,
        "metric": payload.metric.value,
        "value": payload.value,
        "unit": payload.unit.value if payload.unit else None,
        "timestamp": payload.timestamp,
        "created_at": created_at,
    }
    READINGS.append(item)

    return SensorReadingCreated(
        reading_id=reading_id,
        device_id=payload.device_id,
        metric=payload.metric,
        accepted=True,
        created_at=created_at,
    )


@app.get("/readings/latest", dependencies=[Depends(verify_bearer_token)])
def latest_readings(
    device_id: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
) -> Dict[str, List[Dict]]:
    items = READINGS

    if device_id:
        items = [item for item in items if item["device_id"] == device_id]

    return {"items": items[-limit:]}


@app.post(
    "/sensors/readings",
    response_model=ContractSensorReading,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_bearer_token)],
    responses={
        401: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
        429: {"model": ProblemDetails},
    },
)
def create_contract_sensor_reading(payload: ContractSensorReadingCreate) -> ContractSensorReading:
    reading = {
        "deviceId": payload.device_id,
        "sensorType": payload.sensor_type.value,
        "value": payload.value,
        "unit": payload.unit.value,
        "timestamp": payload.timestamp,
        "locationId": payload.location_id,
        "correlationId": payload.correlation_id,
        "id": str(uuid4()),
        "createdAt": now_iso(),
    }
    remember_contract_reading(reading)
    return ContractSensorReading.model_validate(reading)


@app.get(
    "/sensors/readings",
    response_model=ContractSensorReadingList,
    dependencies=[Depends(verify_bearer_token)],
)
def get_contract_sensor_readings(
    device_id: Optional[str] = Query(default=None, alias="deviceId"),
    sensor_type: Optional[SensorMetric] = Query(default=None, alias="sensorType"),
    limit: int = Query(default=20, ge=1, le=100),
) -> ContractSensorReadingList:
    items = CONTRACT_READINGS
    if device_id:
        items = [item for item in items if item["deviceId"] == device_id]
    if sensor_type:
        items = [item for item in items if item["sensorType"] == sensor_type.value]

    limited_items = items[-limit:]
    return ContractSensorReadingList(
        items=[ContractSensorReading.model_validate(item) for item in limited_items],
        total=len(items),
        nextCursor=None,
    )


@app.get(
    "/sensors/threshold-exceeded",
    response_model=ContractEventList,
    dependencies=[Depends(verify_bearer_token)],
)
def get_threshold_exceeded_events(
    severity: Optional[Severity] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> ContractEventList:
    items = CONTRACT_THRESHOLD_EVENTS
    if severity:
        items = [item for item in items if item["data"].get("severity") == severity.value]

    limited_items = items[-limit:]
    return ContractEventList(
        items=[ContractEvent.model_validate(item) for item in limited_items],
        total=len(items),
        nextCursor=None,
    )


@app.get(
    "/telemetry",
    response_model=ContractEventList,
    dependencies=[Depends(verify_bearer_token)],
)
def get_telemetry(
    device_id: Optional[str] = Query(default=None, alias="deviceId"),
    zone_id: Optional[str] = Query(default=None, alias="zoneId"),
    limit: int = Query(default=20, ge=1, le=100),
) -> ContractEventList:
    items = CONTRACT_TELEMETRY_EVENTS
    if device_id:
        items = [item for item in items if item["data"].get("deviceId") == device_id]
    if zone_id:
        items = [item for item in items if item["data"].get("zoneId") == zone_id]

    limited_items = items[-limit:]
    return ContractEventList(
        items=[ContractEvent.model_validate(item) for item in limited_items],
        total=len(items),
        nextCursor=None,
    )


@app.get(
    "/devices/{deviceId}/status",
    response_model=ContractDeviceStatus,
    dependencies=[Depends(verify_bearer_token)],
)
def get_device_status(deviceId: str) -> ContractDeviceStatus:
    device_status = DEVICE_STATUSES.get(deviceId)
    if not device_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=build_problem(
                status_code=status.HTTP_404_NOT_FOUND,
                title="Not Found",
                detail=f"Device {deviceId} does not exist",
                instance=f"/devices/{deviceId}/status",
                problem_type="https://iot.campus.local/errors/not-found",
            ),
        )

    return ContractDeviceStatus.model_validate(device_status)


@app.get(
    "/events",
    response_model=ContractEventList,
    dependencies=[Depends(verify_bearer_token)],
)
def get_iot_events(
    event_type: Optional[str] = Query(default=None, alias="eventType"),
    limit: int = Query(default=20, ge=1, le=100),
) -> ContractEventList:
    allowed_event_types = {
        "sensor.reading.created",
        "sensor.threshold.exceeded",
        "telemetry.ingested",
        "device.status.changed",
    }
    if event_type and event_type not in allowed_event_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=build_problem(
                status_code=status.HTTP_400_BAD_REQUEST,
                title="Bad Request",
                detail=f"eventType {event_type} is not supported",
                instance="/events",
                problem_type="https://iot.campus.local/errors/validation",
            ),
        )

    items = CONTRACT_EVENTS
    if event_type:
        items = [item for item in items if item["eventType"] == event_type]

    limited_items = items[-limit:]
    return ContractEventList(
        items=[ContractEvent.model_validate(item) for item in limited_items],
        total=len(items),
        nextCursor=None,
    )


@app.get(
    "/partners/health",
    response_model=PartnerHealthList,
    dependencies=[Depends(verify_bearer_token)],
)
def get_partner_health() -> PartnerHealthList:
    checks = [
        check_partner_health("core", CORE_SERVICE_URL),
        check_partner_health("analytics", ANALYTICS_SERVICE_URL),
    ]
    return PartnerHealthList(items=[PartnerHealth.model_validate(item) for item in checks])


@app.post("/iot/raw/process", dependencies=[Depends(verify_bearer_token)])
def process_iot_raw_payload(payload: Dict) -> Dict:
    processed = process_raw_sample(payload, load_registry_for_request())
    if processed.processed_event:
        PROCESSED_IOT_EVENTS.append(processed.processed_event)

    return {
        "rawEventId": processed.raw_event_id,
        "deviceId": processed.device_id,
        "status": processed.status,
        "alertLevel": processed.alert_level,
        "reason": processed.reason,
        "published": processed.processed_event is not None,
        "processedEvent": processed.processed_event,
        "contractEvents": processed.events,
    }


@app.get("/iot/processed-events", dependencies=[Depends(verify_bearer_token)])
def get_processed_iot_events(limit: int = Query(default=20, ge=1, le=100)) -> Dict:
    items = PROCESSED_IOT_EVENTS[-limit:]
    return {"items": items, "total": len(PROCESSED_IOT_EVENTS)}


@app.get("/readings/{reading_id}", dependencies=[Depends(verify_bearer_token)])
def get_reading(reading_id: str) -> Dict:
    for item in READINGS:
        if item["reading_id"] == reading_id:
            return item

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=build_problem(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail=f"Reading {reading_id} does not exist",
            instance=f"/readings/{reading_id}",
            problem_type="https://smart-campus.local/problems/not-found",
        ),
    )
