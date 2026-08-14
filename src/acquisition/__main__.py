"""
Entrypoint del extractor real: reemplaza a mock_starlink en producción
(`python -m acquisition`, CLAUDE.md §1.1 "pasaje a hardware real"). Mismo
tópico MQTT y misma morfología de paquete que el mock (ADR-01) -- el
consumer/DB/Grafana no notan el switch.

⚠️ No corrido contra la antena real en esta sesión (sin acceso presencial al
LIT) -- ver advertencia en starlink_extractor.py. Validar en la próxima
visita antes de dejarlo corriendo para las 72h de CA-01.
"""

import json
import os
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from pydantic import ValidationError

from common import connect_with_retry, setup_logging
from mock_starlink.schema import SCHEMA_VERSION, StarlinkPayloadIn

from . import grpc_client
from .grpc_client import GrpcClientError
from .starlink_extractor import build_metrics

TOPIC_METRICS = "starlink/metrics/{node_id}"
# Enmienda 14/08/2026 (ADR-03/ADR-04): era "system/status/{node_id}", compartido
# con el módulo de sensado ambiental -- dos productores de dominios distintos
# bajo el mismo node_id se pisaban el mensaje retained entre sí (confirmado en
# una prueba de integración en vivo con el mock de Fede, ver docs/PROGRESS.md).
TOPIC_STATUS = "starlink/status/{node_id}"


def _status_payload(node_id: str, status: str) -> str:
    return json.dumps({"node_id": node_id, "source": "starlink_acquisition", "status": status})


def _poll_once(addr: str, node_id: str, since_ns: int, logger) -> tuple[dict, int] | tuple[None, int]:
    """Una consulta a la antena + armado del payload. Nunca lanza --
    cualquier falla (antena no disponible, timeout, esquema inválido) se
    loguea y se propaga como `(None, since_ns)` para que el loop principal
    la salte sin tumbar el contenedor (CLAUDE.md §1.1)."""
    try:
        status = grpc_client.get_status(addr)
        history = grpc_client.get_history(addr)
    except GrpcClientError as exc:
        logger.warning("no se pudo consultar la antena, se salta este ciclo", extra={"rc": str(exc)})
        return None, since_ns

    now = datetime.now(timezone.utc)
    now_ns = int(now.timestamp() * 1_000_000_000)
    metrics = build_metrics(status, history, since_ns)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "node_id": node_id,
        "timestamp": now.isoformat(),
        "metrics": metrics,
    }
    try:
        StarlinkPayloadIn.model_validate(payload)
    except ValidationError as exc:
        logger.error(
            "payload construido desde la antena no pasó la validación, se descarta",
            extra={"node_id": node_id, "rc": str(exc)},
        )
        return None, now_ns

    return payload, now_ns


def main() -> None:
    logger = setup_logging("acquisition")

    mqtt_host = os.environ.get("MQTT_HOST", "localhost")
    mqtt_port = int(os.environ.get("MQTT_PORT", "1883"))
    node_id = os.environ.get("STARLINK_NODE_ID", "lit-cordoba-01")
    dish_addr = os.environ.get("DISH_GRPC_ADDR", "192.168.100.1:9200")
    poll_interval_s = float(os.environ.get("POLL_INTERVAL_S", "60"))

    status_topic = TOPIC_STATUS.format(node_id=node_id)
    metrics_topic = TOPIC_METRICS.format(node_id=node_id)

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"acquisition-{node_id}",
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

    connect_with_retry(client, mqtt_host, mqtt_port, logger)
    client.loop_start()

    logger.info(
        f"acquisition arrancando: node_id={node_id} dish_addr={dish_addr} "
        f"poll_interval_s={poll_interval_s}"
    )

    since_ns = 0  # primer poll: cuenta todo el historial disponible como handovers (ver docstring)
    try:
        while True:
            payload, since_ns = _poll_once(dish_addr, node_id, since_ns, logger)
            if payload is not None:
                info = client.publish(metrics_topic, json.dumps(payload), qos=1)
                if info.rc != mqtt.MQTT_ERR_SUCCESS:
                    logger.warning(
                        "fallo al publicar payload", extra={"topic": metrics_topic, "rc": str(info.rc)}
                    )
            time.sleep(poll_interval_s)
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
