import json
import logging
import os
import ssl
from pathlib import Path
from typing import Any

from paho.mqtt import client as mqtt

from iot_app.processor import load_device_registry, process_raw_sample, topic_for_event, validate_raw_payload


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
LOGGER = logging.getLogger("iot_app.mqtt_worker")


MQTT_HOST = os.getenv("MQTT_HOST", "")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "iot-ingestion-worker")
MQTT_INPUT_TOPIC = os.getenv("MQTT_INPUT_TOPIC", "smart-campus/raw/iot/environment")
MQTT_SENSOR_OUTPUT_TOPIC = os.getenv("MQTT_SENSOR_OUTPUT_TOPIC", "smart-campus/events/sensor")
MQTT_TELEMETRY_OUTPUT_TOPIC = os.getenv("MQTT_TELEMETRY_OUTPUT_TOPIC", "smart-campus/events/telemetry")
DEVICE_REGISTRY_PATH = os.getenv("DEVICE_REGISTRY_PATH", "data/IoT_device_registry.csv")
MQTT_PUBLISH_CONTRACT_EVENTS = os.getenv("MQTT_PUBLISH_CONTRACT_EVENTS", "false").lower() == "true"


def create_client() -> mqtt.Client:
    client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv5)
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
    return client


def main() -> None:
    if not MQTT_HOST:
        raise RuntimeError("MQTT_HOST is required when running the MQTT worker")

    registry = load_device_registry(Path(DEVICE_REGISTRY_PATH))
    LOGGER.info("loaded_registry count=%s path=%s", len(registry), DEVICE_REGISTRY_PATH)

    client = create_client()

    def on_connect(
        client: mqtt.Client,
        userdata: Any,
        flags: dict[str, Any],
        reason_code: Any,
        properties: Any = None,
    ) -> None:
        LOGGER.info("mqtt_connected reason_code=%s input_topic=%s", reason_code, MQTT_INPUT_TOPIC)
        client.subscribe(MQTT_INPUT_TOPIC, qos=1)

    def on_message(client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except json.JSONDecodeError:
            LOGGER.exception("invalid_json topic=%s", message.topic)
            return

        LOGGER.info(
            "raw_payload_json=%s",
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        )

        missing_fields = validate_raw_payload(payload)
        if missing_fields:
            LOGGER.error(
                "invalid_raw_payload error=missing_required_field missing_fields=%s raw_event_id=%s topic=%s",
                missing_fields,
                payload.get("event_id"),
                message.topic,
            )
            return

        processed = process_raw_sample(payload, registry)
        LOGGER.info(
            "processed_raw raw_event_id=%s device_id=%s status=%s alert_level=%s reason=%s contract_events=%s",
            processed.raw_event_id,
            processed.device_id,
            processed.status,
            processed.alert_level,
            processed.reason,
            len(processed.events),
        )

        if processed.processed_event:
            client.publish(
                MQTT_SENSOR_OUTPUT_TOPIC,
                json.dumps(processed.processed_event, separators=(",", ":")),
                qos=1,
            )
            LOGGER.info(
                "published_processed_event topic=%s event_id=%s status=%s",
                MQTT_SENSOR_OUTPUT_TOPIC,
                processed.processed_event["eventId"],
                processed.processed_event["status"],
            )
            LOGGER.info(
                "processed_event_json=%s",
                json.dumps(processed.processed_event, ensure_ascii=False, separators=(",", ":")),
            )

        if not MQTT_PUBLISH_CONTRACT_EVENTS:
            return

        for event in processed.events:
            topic = topic_for_event(event, MQTT_SENSOR_OUTPUT_TOPIC, MQTT_TELEMETRY_OUTPUT_TOPIC)
            client.publish(topic, json.dumps(event, separators=(",", ":")), qos=1)
            LOGGER.info("published_event topic=%s eventType=%s eventId=%s", topic, event["eventType"], event["eventId"])

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_forever()


if __name__ == "__main__":
    main()
