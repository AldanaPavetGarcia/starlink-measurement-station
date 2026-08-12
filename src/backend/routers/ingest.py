"""
POST /ingest/starlink (docs/07_API_REST.md §"Tag: ingest"): ingesta manual
solo para testing/mocks/backfill (RF-29, ADR-08), desactivable con
ENABLE_INGEST_ENDPOINT=false (default). Reusa StarlinkPayloadIn
(mock_starlink.schema, ADR-01) y NetHealthDB/starlink_row (consumer.db,
consumer.router) en vez de reimplementar la misma validación/INSERT
idempotente que el consumer ya tiene probado end-to-end -- a diferencia de
las consultas de lectura del resto del backend, acá SÍ conviene reusar el
código del consumer porque es literalmente la misma operación de escritura.
"""

from __future__ import annotations

from typing import Union

from fastapi import APIRouter, Body, Depends
from pydantic import ValidationError

from consumer.db import NetHealthDB
from consumer.router import starlink_row
from mock_starlink.schema import StarlinkPayloadIn

from .. import config
from ..errors import ApiError
from ..security import require_api_key

router = APIRouter(prefix="/ingest", tags=["ingest"], dependencies=[Depends(require_api_key)])

_MAX_BATCH = 1000
_net_db: NetHealthDB | None = None


def _get_net_db() -> NetHealthDB:
    global _net_db
    if _net_db is None:
        _net_db = NetHealthDB.from_env()
    return _net_db


def _is_schema_version_error(exc: ValidationError) -> bool:
    return any(err["loc"] == ("schema_version",) for err in exc.errors())


@router.post("/starlink", status_code=201)
def ingest_starlink(payload: Union[dict, list[dict]] = Body(...)) -> dict:
    if not config.ENABLE_INGEST_ENDPOINT:
        raise ApiError(422, "INGEST_DISABLED", "POST /ingest/* deshabilitado (ENABLE_INGEST_ENDPOINT=false)")

    items = payload if isinstance(payload, list) else [payload]
    if len(items) > _MAX_BATCH:
        raise ApiError(422, "BATCH_TOO_LARGE", f"máximo {_MAX_BATCH} objetos por request, recibidos {len(items)}")

    validated: list[StarlinkPayloadIn] = []
    for item in items:
        try:
            validated.append(StarlinkPayloadIn.model_validate(item))
        except ValidationError as exc:
            if _is_schema_version_error(exc):
                raise ApiError(422, "SCHEMA_VERSION_MISMATCH", str(exc)) from exc
            raise ApiError(400, "VALIDATION_ERROR", str(exc)) from exc

    net_db = _get_net_db()
    try:
        for p in validated:
            net_db.insert(starlink_row(p))
    except Exception as exc:  # noqa: BLE001 -- cualquier falla de DB acá es DB_UNAVAILABLE
        raise ApiError(503, "DB_UNAVAILABLE", str(exc)) from exc

    last = validated[-1]
    return {
        "status": "success",
        "inserted": len(validated),
        "node_id": last.node_id,
        "timestamp": last.timestamp.isoformat().replace("+00:00", "Z"),
    }
