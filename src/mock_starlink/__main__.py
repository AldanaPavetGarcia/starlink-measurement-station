"""
Entrypoint del mock_starlink: conecta al broker MQTT y corre el
StarlinkMockAgent para siempre (`python -m mock_starlink`).

Cubre los requisitos de CLAUDE.md §1.1 para este componente: reconexión
automática al broker sin tumbar el contenedor, y logging estructurado (JSON)
de errores de conexión/publicación.
"""

import asyncio
import json
import logging
import os
import sys
import time

import paho.mqtt.client as mqtt

from .mock import CHAOS_PROFILES, StarlinkMockAgent

TOPIC_METRICS = "starlink/metrics/{node_id}"
TOPIC_STATUS = "system/status/{node_id}"


class JsonLogFormatter(logging.Formatter):
    """Formatter mínimo sin dependencias nuevas: una línea JSON por log."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }
        for key in ("node_id", "topic", "rc"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload)


def _setup_logging() -> logging.Logger:
    logger = logging.getLogger("mock_starlink")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
    return logger


def _status_payload(node_id: str, status: str) -> str:
    return json.dumps({"node_id": node_id, "source": "starlink_mock", "status": status})


def _connect_with_retry(client: mqtt.Client, host: str, port: int, logger: logging.Logger) -> None:
    delay = 1.0
    while True:
        try:
            client.connect(host, port, keepalive=60)
            return
        except OSError as exc:
            logger.warning(
                "no se pudo conectar al broker, reintentando",
                extra={"rc": str(exc)},
            )
            time.sleep(delay)
            delay = min(delay * 2, 30.0)


def main() -> None:
    logger = _setup_logging()

    mqtt_host = os.environ.get("MQTT_HOST", "localhost")
    mqtt_port = int(os.environ.get("MQTT_PORT", "1883"))
    node_id = os.environ.get("STARLINK_NODE_ID", "lit-cordoba-01")
    chaos_profile = os.environ.get("CHAOS_PROFILE", "CALM")
    time_warp_factor = int(os.environ.get("TIME_WARP_FACTOR", "1"))

    if chaos_profile not in CHAOS_PROFILES:
        logger.error(f"CHAOS_PROFILE inválido: {chaos_profile!r} (válidos: {CHAOS_PROFILES})")
        raise SystemExit(1)

    status_topic = TOPIC_STATUS.format(node_id=node_id)
    metrics_topic = TOPIC_METRICS.format(node_id=node_id)

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"mock-starlink-{node_id}",
        protocol=mqtt.MQTTv5,
    )
    client.reconnect_delay_set(min_delay=1, max_delay=60)
    client.will_set(status_topic, payload=_status_payload(node_id, "offline"), qos=1, retain=True)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info("conectado al broker", extra={"node_id": node_id})
            client.publish(status_topic, _status_payload(node_id, "online"), qos=1, retain=True)
        else:
            logger.error("conexión rechazada por el broker", extra={"rc": str(reason_code)})

    def on_disconnect(client, userdata, flags, reason_code, properties):
        logger.warning("desconectado del broker, reconectando", extra={"rc": str(reason_code)})

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    _connect_with_retry(client, mqtt_host, mqtt_port, logger)
    client.loop_start()

    logger.info(
        f"mock_starlink arrancando: node_id={node_id} chaos_profile={chaos_profile} "
        f"time_warp_factor={time_warp_factor}"
    )

    agent = StarlinkMockAgent(node_id, chaos_profile=chaos_profile, time_warp_factor=time_warp_factor)

    async def publish_callback(payload: dict) -> None:
        info = client.publish(metrics_topic, json.dumps(payload), qos=1)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.warning("fallo al publicar payload", extra={"topic": metrics_topic, "rc": str(info.rc)})

    try:
        asyncio.run(agent.run(publish_callback))
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
