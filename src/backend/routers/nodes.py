"""
GET /nodes, /nodes/{node_id} (docs/07_API_REST.md §"Tag: nodes"). Fuente:
station_metadata + sensor_catalog en station_config_db (ADR-10, semana 7),
con `telemetry.last_starlink_metric` traído de starlink_health_db -- dos
conexiones distintas (Database per Service, ADR-10) combinadas en Python, no
un JOIN SQL cruzado entre bases.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text

from .. import db
from ..errors import ApiError
from ..security import require_api_key

router = APIRouter(prefix="/nodes", tags=["nodes"], dependencies=[Depends(require_api_key)])

_IS_REPORTING_WINDOW = timedelta(minutes=5)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _last_starlink_metrics(node_ids: list[str]) -> dict[str, datetime]:
    if not node_ids:
        return {}
    with db.starlink_engine().connect() as conn:
        rows = conn.execute(
            text(
                "SELECT node_id, MAX(time) AS last_time FROM network_metrics "
                "WHERE node_id = ANY(:ids) GROUP BY node_id"
            ),
            {"ids": node_ids},
        ).mappings().all()
    return {r["node_id"]: r["last_time"] for r in rows}


@router.get("")
def list_nodes(status_filter: str = Query("active", alias="status")) -> dict:
    with db.station_config_engine().connect() as conn:
        if status_filter == "all":
            rows = conn.execute(text("SELECT * FROM station_metadata ORDER BY node_id")).mappings().all()
        else:
            rows = conn.execute(
                text("SELECT * FROM station_metadata WHERE status = :s ORDER BY node_id"),
                {"s": status_filter},
            ).mappings().all()

    node_ids = [r["node_id"] for r in rows]
    last_metrics = _last_starlink_metrics(node_ids)
    now = datetime.now(timezone.utc)

    data = []
    for r in rows:
        node = dict(r)
        node["deployed_at"] = _iso(node["deployed_at"])
        last = last_metrics.get(node["node_id"])
        node["telemetry"] = {
            "last_starlink_metric": _iso(last) if last else None,
            # meteo es dominio de Fede, no implementado todavía (ver
            # docs/PROGRESS.md "Coordinación pendiente con Fede").
            "last_env_metric": None,
            "is_reporting": bool(last and (now - last) < _IS_REPORTING_WINDOW),
        }
        data.append(node)

    return {"status": "success", "count": len(data), "data": data}


@router.get("/{node_id}")
def get_node(node_id: str) -> dict:
    with db.station_config_engine().connect() as conn:
        node_row = conn.execute(
            text("SELECT * FROM station_metadata WHERE node_id = :id"), {"id": node_id}
        ).mappings().first()
        if node_row is None:
            raise ApiError(404, "NODE_NOT_FOUND", f"node_id no encontrado: {node_id}")

        sensor_rows = conn.execute(
            text("SELECT * FROM sensor_catalog WHERE node_id = :id ORDER BY sensor_id"),
            {"id": node_id},
        ).mappings().all()

    node = dict(node_row)
    node["deployed_at"] = _iso(node["deployed_at"])
    sensors = []
    for s in sensor_rows:
        sensor = dict(s)
        if sensor.get("last_calibrated_at"):
            sensor["last_calibrated_at"] = _iso(sensor["last_calibrated_at"])
        sensor.pop("registered_at", None)
        sensor.pop("node_id", None)
        sensors.append(sensor)
    node["sensors"] = sensors

    return {"status": "success", "data": node}
