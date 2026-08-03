"""
Router de tópicos MQTT -> Database per Service (ADR-04, ADR-10).

`ConsumerRouter.route_message` es el punto de entrada único del consumer:
decide, según el prefijo del tópico, a qué DB gateway (NetHealthDB/MeteoDB)
enrutar el payload ya parseado (dict, no bytes -- decodificar el JSON crudo
de MQTT es responsabilidad de `__main__.py`, para que esta función sea
testeable con dicts sin necesidad de un broker real, ver suite UT-03 de
docs/08_Plan_QA.md).

Contrato de retorno -- `route_message` devuelve `True` cuando el mensaje MQTT
puede ACKearse (fue persistido, o el error es permanente y reintentar no
ayuda: JSON/esquema inválido, tópico desconocido) y `False` cuando el ACK
debe retenerse para forzar reentrega QoS 1 (RF-18): el mensaje era válido
pero la DB falló de forma transitoria (UT-03-05, RNF-05).
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from pydantic import ValidationError

from mock_starlink.schema import StarlinkPayloadIn

logger = logging.getLogger("consumer")

TOPIC_PREFIX_STARLINK = "starlink/metrics/"
TOPIC_PREFIX_METEO_SENSOR = "meteo/sensor/"
TOPIC_PREFIX_METEO_EXTERNAL = "meteo/external/"


class _InsertDB(Protocol):
    def insert(self, row: dict[str, Any]) -> None: ...


def _starlink_row(payload: StarlinkPayloadIn) -> dict[str, Any]:
    m = payload.metrics
    return {
        "time": payload.timestamp,
        "node_id": payload.node_id,
        "latency_ms": m.latency_ms,
        "jitter_ms": m.jitter_ms,
        "packet_loss_pct": m.packet_loss_pct,
        "throughput_down_bps": m.throughput_down_bps,
        "throughput_up_bps": m.throughput_up_bps,
        "snr_db": m.snr_db,
        "is_obstructed": m.is_obstructed,
        "satellite_count": m.satellite_count,
        "schema_version": payload.schema_version,
    }


class ConsumerRouter:
    def __init__(self, net_db: _InsertDB, meteo_db: _InsertDB) -> None:
        self.net_db = net_db
        self.meteo_db = meteo_db

    def route_message(self, topic: str, payload: dict[str, Any]) -> bool:
        if topic.startswith(TOPIC_PREFIX_STARLINK):
            return self._route_starlink(topic, payload)
        if topic.startswith(TOPIC_PREFIX_METEO_SENSOR) or topic.startswith(TOPIC_PREFIX_METEO_EXTERNAL):
            return self._route_meteo(topic, payload)

        logger.warning("tópico desconocido, mensaje descartado", extra={"topic": topic})
        return True

    def _route_starlink(self, topic: str, payload: dict[str, Any]) -> bool:
        try:
            validated = StarlinkPayloadIn.model_validate(payload)
        except ValidationError as exc:
            logger.error(
                "paquete Starlink inválido, no se persiste",
                extra={"topic": topic, "rc": str(exc)},
            )
            return True

        try:
            self.net_db.insert(_starlink_row(validated))
        except Exception as exc:  # noqa: BLE001 -- cualquier falla de DB es transitoria
            logger.error(
                "fallo al insertar en network_metrics, se retiene el ACK MQTT",
                extra={"topic": topic, "node_id": validated.node_id, "rc": str(exc)},
            )
            return False
        return True

    def _route_meteo(self, topic: str, payload: dict[str, Any]) -> bool:
        try:
            self.meteo_db.insert(payload)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "fallo al insertar en env_metrics, se retiene el ACK MQTT",
                extra={"topic": topic, "rc": str(exc)},
            )
            return False
        return True
