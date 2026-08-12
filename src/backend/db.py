"""
Acceso de solo lectura a starlink_health_db y station_config_db (ADR-04: ORM/
TCP nativo). A diferencia de src/consumer/db.py (que sí necesita un ORM
declarativo para el INSERT idempotente), acá se usa SQLAlchemy Core
(`text()`) para las consultas -- son SELECTs de agregación/paginación
variables según query params, más simples como SQL parametrizado directo que
como expresiones ORM. `NetworkMetric` (consumer) no se reusa acá a propósito:
mismo motivo que ADR-07 (microservicios desacoplados) -- el backend no debe
depender del paquete `consumer`.
"""

from __future__ import annotations

import socket
import time
from typing import Any

from sqlalchemy import Engine, create_engine, text

from . import config

# Columnas de metrics tal como las expone StarlinkMetrics (schema.py, ADR-01)
# -- usado para armar SELECTs dinámicos y para filtrar `fields=` (RF-25).
STARLINK_METRIC_FIELDS = (
    "latency_ms", "jitter_ms", "packet_loss_pct", "throughput_down_bps",
    "throughput_up_bps", "snr_low", "is_obstructed", "satellite_count",
    "handover_count", "outage_duration_ms", "tilt_angle_deg",
    "boresight_azimuth_deg", "boresight_elevation_deg",
    "desired_boresight_azimuth_deg", "desired_boresight_elevation_deg",
    "attitude_uncertainty_deg",
)

_starlink_engine: Engine | None = None
_station_config_engine: Engine | None = None


def starlink_engine() -> Engine:
    global _starlink_engine
    if _starlink_engine is None:
        dsn = (
            f"postgresql+psycopg2://{config.STARLINK_DB_USER}:{config.STARLINK_DB_PASSWORD}"
            f"@{config.STARLINK_DB_HOST}:{config.STARLINK_DB_PORT}/{config.STARLINK_DB_NAME}"
        )
        _starlink_engine = create_engine(dsn, pool_pre_ping=True)
    return _starlink_engine


def station_config_engine() -> Engine:
    global _station_config_engine
    if _station_config_engine is None:
        dsn = (
            f"postgresql+psycopg2://{config.STATION_CONFIG_DB_USER}:{config.STATION_CONFIG_DB_PASSWORD}"
            f"@{config.STATION_CONFIG_DB_HOST}:{config.STATION_CONFIG_DB_PORT}/{config.STATION_CONFIG_DB_NAME}"
        )
        _station_config_engine = create_engine(dsn, pool_pre_ping=True)
    return _station_config_engine


def ping(engine: Engine) -> dict[str, Any]:
    """Componente de GET /health (docs/07_API_REST.md §"Implementación
    FastAPI"): SELECT 1 con latencia medida. `status: down` en vez de
    propagar la excepción -- health nunca debe tirar 5xx por una DB caída."""
    try:
        t0 = time.monotonic()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "up", "latency_ms": round((time.monotonic() - t0) * 1000, 2)}
    except Exception as exc:  # noqa: BLE001 -- health check, cualquier falla es "down"
        return {"status": "down", "latency_ms": None, "error": str(exc)}


def ping_mqtt_broker(host: str, port: int, timeout_s: float = 2.0) -> dict[str, Any]:
    """Chequeo liviano de conectividad TCP al broker -- no abre una sesión
    MQTT completa solo para el healthcheck (evitaría mantener un cliente
    persistente extra en el backend)."""
    try:
        t0 = time.monotonic()
        with socket.create_connection((host, port), timeout=timeout_s):
            pass
        return {"status": "up", "latency_ms": round((time.monotonic() - t0) * 1000, 2)}
    except OSError as exc:
        return {"status": "down", "latency_ms": None, "error": str(exc)}


def last_write(engine: Engine, table: str) -> str | None:
    """MAX(time) de una hypertable -- usado para `last_write` en /health y
    `telemetry.last_starlink_metric` en /nodes."""
    with engine.connect() as conn:
        row = conn.execute(text(f"SELECT MAX(time) FROM {table}")).first()
    if row is None or row[0] is None:
        return None
    return row[0].isoformat().replace("+00:00", "Z")
