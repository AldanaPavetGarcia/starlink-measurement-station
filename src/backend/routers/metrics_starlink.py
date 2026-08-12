"""
GET /metrics/starlink, /summary, /latest (docs/07_API_REST.md §"Tag:
starlink"). Fuente: network_metrics + CAGGs net_hourly/net_daily
(docs/06_DER.md §3.1/§3.3/§3.4), ya provisionadas por
services/db/init_starlink_health.sql desde semana 6-7.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text

from .. import config, db
from ..errors import ApiError
from ..security import require_api_key

router = APIRouter(
    prefix="/metrics/starlink",
    tags=["starlink"],
    dependencies=[Depends(require_api_key)],
)

# Columnas agregadas por net_hourly/net_daily (docs/06_DER.md §3.3/§3.4).
# `fields=` (RF-25) solo filtra sobre resolution=raw -- en hourly/daily
# siempre se devuelve la fila agregada completa (simplificación documentada,
# el CAGG no tiene una columna por cada campo crudo para filtrar 1:1).
_HOURLY_COLUMNS = (
    "avg_latency_ms", "max_latency_ms", "min_latency_ms", "p95_latency_ms",
    "avg_jitter_ms", "avg_packet_loss_pct", "avg_throughput_down_bps",
    "avg_throughput_up_bps", "sum_handover_count", "sum_outage_duration_ms",
    "avg_tilt_angle_deg", "sample_count",
)
_DAILY_COLUMNS = (
    "avg_latency_ms", "max_latency_ms", "p95_latency_ms", "avg_packet_loss_pct",
    "availability_pct", "avg_throughput_down_bps", "avg_throughput_up_bps",
    "sum_handover_count", "sum_outage_duration_ms", "avg_tilt_angle_deg",
    "sample_count",
)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_node_ids(node_id: str) -> list[str]:
    ids = [n.strip() for n in node_id.split(",") if n.strip()]
    if not ids:
        raise ApiError(400, "VALIDATION_ERROR", "node_id no puede estar vacío")
    return ids


def _assert_nodes_exist(node_ids: list[str]) -> None:
    with db.station_config_engine().connect() as conn:
        rows = conn.execute(
            text("SELECT node_id FROM station_metadata WHERE node_id = ANY(:ids)"),
            {"ids": node_ids},
        ).fetchall()
    found = {r[0] for r in rows}
    missing = set(node_ids) - found
    if missing:
        raise ApiError(404, "NODE_NOT_FOUND", f"node_id no encontrado: {', '.join(sorted(missing))}")


def _resolve_resolution(resolution: str, start: datetime, end: datetime) -> str:
    if resolution != "auto":
        return resolution
    span = end - start
    if span <= timedelta(hours=config.AUTO_RESOLUTION_RAW_MAX_HOURS):
        return "raw"
    if span <= timedelta(days=config.AUTO_RESOLUTION_HOURLY_MAX_DAYS):
        return "hourly"
    return "daily"


@router.get("")
def get_starlink_metrics(
    node_id: str = Query(...),
    start: datetime = Query(...),
    end: datetime = Query(...),
    resolution: str = Query("auto", pattern="^(raw|hourly|daily|auto)$"),
    fields: str = Query("all"),
    limit: int = Query(500, ge=1, le=5000),
    cursor: Optional[datetime] = Query(None),
) -> dict:
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if start >= end:
        raise ApiError(400, "VALIDATION_ERROR", "'start' debe ser anterior a 'end'")

    node_ids = _parse_node_ids(node_id)
    _assert_nodes_exist(node_ids)

    resolved = _resolve_resolution(resolution, start, end)

    if resolved == "raw" and (end - start) > timedelta(days=90):
        raise ApiError(
            400, "DATE_RANGE_TOO_LARGE",
            "rango supera 90 días con resolution=raw; usar resolution=hourly o daily",
        )

    if resolved == "raw":
        table, time_col = "network_metrics", "time"
        selectable = db.STARLINK_METRIC_FIELDS
        if fields != "all":
            requested = {f.strip() for f in fields.split(",")}
            selectable = tuple(f for f in db.STARLINK_METRIC_FIELDS if f in requested)
    elif resolved == "hourly":
        table, time_col, selectable = "net_hourly", "bucket", _HOURLY_COLUMNS
    else:
        table, time_col, selectable = "net_daily", "bucket", _DAILY_COLUMNS

    columns_sql = ", ".join(f'"{c}"' for c in selectable)
    where = [f"{time_col} >= :start", f"{time_col} <= :end", "node_id = ANY(:node_ids)"]
    params: dict = {"start": start, "end": end, "node_ids": node_ids, "limit": limit + 1}
    if cursor is not None:
        where.append(f"{time_col} > :cursor")
        params["cursor"] = cursor

    query = text(
        f"SELECT {time_col} AS time, node_id, {columns_sql} FROM {table} "
        f"WHERE {' AND '.join(where)} ORDER BY {time_col} ASC LIMIT :limit"
    )
    with db.starlink_engine().connect() as conn:
        rows = conn.execute(query, params).mappings().all()

    has_more = len(rows) > limit
    rows = rows[:limit]
    data = [{**dict(r), "time": _iso(r["time"])} for r in rows]
    next_cursor = data[-1]["time"] if has_more and data else None

    return {
        "status": "success",
        "version": "1.1",
        "node_id": node_id,
        "resolution": resolved,
        "count": len(data),
        "page_info": {"has_more": has_more, "next_cursor": next_cursor, "limit": limit},
        "data": data,
    }


@router.get("/summary")
def get_starlink_summary(
    node_id: str = Query(...),
    start: datetime = Query(...),
    end: datetime = Query(...),
) -> dict:
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if start >= end:
        raise ApiError(400, "VALIDATION_ERROR", "'start' debe ser anterior a 'end'")

    node_ids = _parse_node_ids(node_id)
    _assert_nodes_exist(node_ids)

    query = text(
        """
        SELECT
            COUNT(*) AS sample_count,
            AVG(latency_ms) AS latency_avg, MIN(latency_ms) AS latency_min,
            MAX(latency_ms) AS latency_max,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY latency_ms) AS latency_p50,
            percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) AS latency_p95,
            percentile_cont(0.99) WITHIN GROUP (ORDER BY latency_ms) AS latency_p99,
            STDDEV(latency_ms) AS latency_std_dev,
            AVG(packet_loss_pct) AS loss_avg, MAX(packet_loss_pct) AS loss_max,
            SUM(CASE WHEN packet_loss_pct > 5 THEN 1 ELSE 0 END) AS loss_events_above_5pct,
            AVG(throughput_down_bps) AS down_avg, MIN(throughput_down_bps) AS down_min,
            MAX(throughput_down_bps) AS down_max,
            AVG(throughput_up_bps) AS up_avg, MIN(throughput_up_bps) AS up_min,
            MAX(throughput_up_bps) AS up_max,
            100.0 * SUM(CASE WHEN packet_loss_pct < 5 THEN 1 ELSE 0 END)::float
                / NULLIF(COUNT(*), 0) AS availability_pct,
            SUM(CASE WHEN is_obstructed THEN 1 ELSE 0 END) AS obstruction_events
        FROM network_metrics
        WHERE time >= :start AND time <= :end AND node_id = ANY(:node_ids)
        """
    )
    with db.starlink_engine().connect() as conn:
        row = conn.execute(query, {"start": start, "end": end, "node_ids": node_ids}).mappings().first()

    if row is None or row["sample_count"] == 0:
        raise ApiError(404, "NO_DATA_FOUND", "no hay datos para ese nodo/rango")

    days = (end - start).total_seconds() / 86400
    # 60s por defecto (ADR-06/CLAUDE.md §5) -- aproximación, no exacta si
    # TIME_WARP_FACTOR != 1 estuvo activo en el rango consultado.
    expected_samples = max(1, int((end - start).total_seconds() / 60))
    completeness = min(100.0, 100.0 * row["sample_count"] / expected_samples)

    return {
        "status": "success",
        "node_id": node_id,
        "period": {"start": _iso(start), "end": _iso(end), "days": round(days, 2)},
        "sample_count": row["sample_count"],
        "data_completeness_pct": round(completeness, 1),
        "summary": {
            "latency_ms": {
                "avg": row["latency_avg"], "min": row["latency_min"], "max": row["latency_max"],
                "p50": row["latency_p50"], "p95": row["latency_p95"], "p99": row["latency_p99"],
                "std_dev": row["latency_std_dev"],
            },
            "packet_loss_pct": {
                "avg": row["loss_avg"], "max": row["loss_max"],
                "events_above_5pct": row["loss_events_above_5pct"],
            },
            "throughput_down_bps": {
                "avg": row["down_avg"], "min": row["down_min"], "max": row["down_max"],
            },
            "throughput_up_bps": {
                "avg": row["up_avg"], "min": row["up_min"], "max": row["up_max"],
            },
            "availability_pct": row["availability_pct"],
            "obstruction_events": row["obstruction_events"],
        },
    }


@router.get("/latest")
def get_starlink_latest(node_id: Optional[str] = Query(None)) -> dict:
    node_ids = _parse_node_ids(node_id) if node_id else None
    if node_ids:
        _assert_nodes_exist(node_ids)

    columns_sql = ", ".join(f'"{c}"' for c in db.STARLINK_METRIC_FIELDS)
    where = "WHERE node_id = ANY(:node_ids)" if node_ids else ""
    query = text(
        f"SELECT DISTINCT ON (node_id) time, node_id, {columns_sql} "
        f"FROM network_metrics {where} ORDER BY node_id, time DESC"
    )
    params = {"node_ids": node_ids} if node_ids else {}
    with db.starlink_engine().connect() as conn:
        rows = conn.execute(query, params).mappings().all()

    if node_ids and not rows:
        raise ApiError(404, "NO_DATA_FOUND", "no hay mediciones para ese nodo todavía")

    now = datetime.now(timezone.utc)
    data = []
    for r in rows:
        row = dict(r)
        t = row.pop("time")
        row["time"] = _iso(t)
        row["seconds_since_last"] = int((now - t).total_seconds())
        data.append(row)

    return {"status": "success", "data": data}
