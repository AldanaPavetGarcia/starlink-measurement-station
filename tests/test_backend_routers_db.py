"""
Tests de los routers del backend que sí tocan la DB (metrics_starlink.py,
nodes.py, ingest.py), con el Engine de SQLAlchemy mockeado (tests/backend_fakes.py)
-- no requieren Postgres real. Complementa tests/test_backend_api.py (que
solo cubre las rutas que fallan ANTES de tocar la DB: auth, INGEST_DISABLED).
"""

import os
from datetime import datetime, timezone

os.environ.setdefault("BACKEND_API_KEY", "test-api-key-fase4")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.config as config  # noqa: E402
import backend.db as db  # noqa: E402
import backend.routers.ingest as ingest_router  # noqa: E402
from backend.main import app  # noqa: E402
from tests.backend_fakes import FakeEngine  # noqa: E402

client = TestClient(app)
HEADERS = {"X-API-Key": os.environ["BACKEND_API_KEY"]}


@pytest.fixture(autouse=True)
def _enable_ingest_for_this_module(monkeypatch):
    """config.ENABLE_INGEST_ENDPOINT se lee de os.environ al importar
    backend.config (module-level) -- otro archivo de tests puede haber
    fijado ENABLE_INGEST_ENDPOINT=false primero y quedar cacheado. Se
    monkeypatchea el atributo directamente en vez de depender del orden de
    colección de pytest."""
    monkeypatch.setattr(config, "ENABLE_INGEST_ENDPOINT", True)


def _starlink_metric_row(**overrides) -> dict:
    row = {f: None for f in db.STARLINK_METRIC_FIELDS}
    row.update({
        "latency_ms": 24.5, "jitter_ms": 3.1, "packet_loss_pct": 0.1,
        "throughput_down_bps": 180_000_000, "throughput_up_bps": 20_000_000,
        "snr_low": False, "is_obstructed": False, "satellite_count": 14,
        "handover_count": 0, "outage_duration_ms": 0.0,
    })
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# GET /metrics/starlink (raw)
# ---------------------------------------------------------------------------

def test_get_starlink_metrics_raw_happy_path(monkeypatch):
    now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(db, "station_config_engine", lambda: FakeEngine([[{"node_id": "lit-test"}]]))
    monkeypatch.setattr(
        db, "starlink_engine",
        lambda: FakeEngine([[{**_starlink_metric_row(), "time": now, "node_id": "lit-test"}]]),
    )

    resp = client.get(
        "/api/v1/metrics/starlink",
        params={
            "node_id": "lit-test", "start": "2026-06-01T00:00:00Z", "end": "2026-06-01T02:00:00Z",
            "resolution": "raw",
        },
        headers=HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["resolution"] == "raw"
    assert body["count"] == 1
    assert body["data"][0]["node_id"] == "lit-test"
    assert body["data"][0]["latency_ms"] == 24.5
    assert body["page_info"]["has_more"] is False


def test_get_starlink_metrics_node_not_found(monkeypatch):
    monkeypatch.setattr(db, "station_config_engine", lambda: FakeEngine([[]]))  # sin filas -> no existe

    resp = client.get(
        "/api/v1/metrics/starlink",
        params={"node_id": "no-existe", "start": "2026-06-01T00:00:00Z", "end": "2026-06-02T00:00:00Z"},
        headers=HEADERS,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NODE_NOT_FOUND"


# ---------------------------------------------------------------------------
# GET /metrics/starlink/latest
# ---------------------------------------------------------------------------

def test_get_starlink_latest_sin_node_id(monkeypatch):
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(
        db, "starlink_engine",
        lambda: FakeEngine([[{**_starlink_metric_row(), "time": now, "node_id": "lit-a"}]]),
    )

    resp = client.get("/api/v1/metrics/starlink/latest", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"][0]["node_id"] == "lit-a"
    assert body["data"][0]["seconds_since_last"] >= 0


def test_get_starlink_latest_nodo_sin_datos_devuelve_404(monkeypatch):
    monkeypatch.setattr(db, "station_config_engine", lambda: FakeEngine([[{"node_id": "lit-test"}]]))
    monkeypatch.setattr(db, "starlink_engine", lambda: FakeEngine([[]]))

    resp = client.get("/api/v1/metrics/starlink/latest", params={"node_id": "lit-test"}, headers=HEADERS)
    assert resp.status_code == 404
    assert resp.json()["code"] == "NO_DATA_FOUND"


# ---------------------------------------------------------------------------
# GET /metrics/starlink/summary
# ---------------------------------------------------------------------------

def test_get_starlink_summary_happy_path(monkeypatch):
    monkeypatch.setattr(db, "station_config_engine", lambda: FakeEngine([[{"node_id": "lit-test"}]]))
    summary_row = {
        "sample_count": 100, "latency_avg": 34.9, "latency_min": 20.1, "latency_max": 412.3,
        "latency_p50": 33.2, "latency_p95": 95.7, "latency_p99": 287.4, "latency_std_dev": 18.6,
        "loss_avg": 0.3, "loss_max": 12.1, "loss_events_above_5pct": 2,
        "down_avg": 181_000_000, "down_min": 45_000_000, "down_max": 248_000_000,
        "up_avg": 21_200_000, "up_min": 8_000_000, "up_max": 29_500_000,
        "availability_pct": 98.6, "obstruction_events": 3,
    }
    monkeypatch.setattr(db, "starlink_engine", lambda: FakeEngine([[summary_row]]))

    resp = client.get(
        "/api/v1/metrics/starlink/summary",
        params={"node_id": "lit-test", "start": "2026-06-01T00:00:00Z", "end": "2026-06-02T00:00:00Z"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["sample_count"] == 100
    assert body["summary"]["latency_ms"]["avg"] == 34.9
    assert body["summary"]["obstruction_events"] == 3


def test_get_starlink_summary_sin_datos_devuelve_404(monkeypatch):
    monkeypatch.setattr(db, "station_config_engine", lambda: FakeEngine([[{"node_id": "lit-test"}]]))
    monkeypatch.setattr(db, "starlink_engine", lambda: FakeEngine([[{"sample_count": 0}]]))

    resp = client.get(
        "/api/v1/metrics/starlink/summary",
        params={"node_id": "lit-test", "start": "2026-06-01T00:00:00Z", "end": "2026-06-02T00:00:00Z"},
        headers=HEADERS,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NO_DATA_FOUND"


# ---------------------------------------------------------------------------
# GET /nodes, /nodes/{node_id}
# ---------------------------------------------------------------------------

def test_list_nodes_happy_path(monkeypatch):
    station_row = {
        "node_id": "lit-cordoba-01", "location_name": "LIT", "latitude": -31.4335,
        "longitude": -64.1878, "altitude_m": 490.0, "deployed_at": datetime.now(timezone.utc),
        "hardware_version": None, "status": "active", "notes": None,
    }
    monkeypatch.setattr(db, "station_config_engine", lambda: FakeEngine([[station_row]]))
    last_metric_row = {"node_id": "lit-cordoba-01", "last_time": datetime.now(timezone.utc)}
    monkeypatch.setattr(db, "starlink_engine", lambda: FakeEngine([[last_metric_row]]))

    resp = client.get("/api/v1/nodes", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["data"][0]["node_id"] == "lit-cordoba-01"
    assert body["data"][0]["telemetry"]["is_reporting"] is True


def test_get_node_not_found(monkeypatch):
    monkeypatch.setattr(db, "station_config_engine", lambda: FakeEngine([[]]))

    resp = client.get("/api/v1/nodes/no-existe", headers=HEADERS)
    assert resp.status_code == 404
    assert resp.json()["code"] == "NODE_NOT_FOUND"


def test_get_node_detalle_con_sensores(monkeypatch):
    station_row = {
        "node_id": "lit-cordoba-01", "location_name": "LIT", "latitude": -31.4335,
        "longitude": -64.1878, "altitude_m": 490.0, "deployed_at": datetime.now(timezone.utc),
        "hardware_version": None, "status": "active", "notes": None,
    }
    sensor_row = {
        "sensor_id": 1, "node_id": "lit-cordoba-01", "sensor_model": "BME280",
        "sensor_type": "multi", "bus_protocol": "I2C", "bus_address": "0x76",
        "calibration_offset": None, "calibration_scale": None,
        "last_calibrated_at": None, "registered_at": datetime.now(timezone.utc), "is_active": True,
    }
    monkeypatch.setattr(db, "station_config_engine", lambda: FakeEngine([[station_row], [sensor_row]]))

    resp = client.get("/api/v1/nodes/lit-cordoba-01", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["node_id"] == "lit-cordoba-01"
    assert len(body["sensors"]) == 1
    assert body["sensors"][0]["sensor_model"] == "BME280"
    assert "node_id" not in body["sensors"][0]  # se descarta, redundante con el padre


# ---------------------------------------------------------------------------
# POST /ingest/starlink -- NetHealthDB mockeado (no un Engine SQLAlchemy)
# ---------------------------------------------------------------------------

class _FakeNetHealthDB:
    def __init__(self):
        self.inserted: list[dict] = []
        self.raise_on_insert: Exception | None = None

    def insert(self, row: dict) -> None:
        if self.raise_on_insert:
            raise self.raise_on_insert
        self.inserted.append(row)


def _valid_ingest_payload(**overrides) -> dict:
    payload = {
        "schema_version": "1.1",
        "node_id": "lit-test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": {"latency_ms": 30.0, "snr_low": False},
    }
    payload.update(overrides)
    return payload


def test_ingest_starlink_happy_path(monkeypatch):
    fake_db = _FakeNetHealthDB()
    monkeypatch.setattr(ingest_router, "_get_net_db", lambda: fake_db)

    resp = client.post("/api/v1/ingest/starlink", json=_valid_ingest_payload(), headers=HEADERS)
    assert resp.status_code == 201
    body = resp.json()
    assert body["inserted"] == 1
    assert body["node_id"] == "lit-test"
    assert len(fake_db.inserted) == 1


def test_ingest_starlink_batch(monkeypatch):
    fake_db = _FakeNetHealthDB()
    monkeypatch.setattr(ingest_router, "_get_net_db", lambda: fake_db)

    batch = [_valid_ingest_payload(), _valid_ingest_payload()]
    resp = client.post("/api/v1/ingest/starlink", json=batch, headers=HEADERS)
    assert resp.status_code == 201
    assert resp.json()["inserted"] == 2
    assert len(fake_db.inserted) == 2


def test_ingest_starlink_payload_invalido_devuelve_400(monkeypatch):
    fake_db = _FakeNetHealthDB()
    monkeypatch.setattr(ingest_router, "_get_net_db", lambda: fake_db)

    resp = client.post(
        "/api/v1/ingest/starlink",
        json=_valid_ingest_payload(metrics={"latency_ms": -999}),
        headers=HEADERS,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "VALIDATION_ERROR"
    assert fake_db.inserted == []


def test_ingest_starlink_schema_version_vieja_devuelve_422(monkeypatch):
    fake_db = _FakeNetHealthDB()
    monkeypatch.setattr(ingest_router, "_get_net_db", lambda: fake_db)

    resp = client.post(
        "/api/v1/ingest/starlink",
        json=_valid_ingest_payload(schema_version="1.0"),
        headers=HEADERS,
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "SCHEMA_VERSION_MISMATCH"


def test_ingest_starlink_batch_too_large(monkeypatch):
    fake_db = _FakeNetHealthDB()
    monkeypatch.setattr(ingest_router, "_get_net_db", lambda: fake_db)

    batch = [_valid_ingest_payload() for _ in range(1001)]
    resp = client.post("/api/v1/ingest/starlink", json=batch, headers=HEADERS)
    assert resp.status_code == 422
    assert resp.json()["code"] == "BATCH_TOO_LARGE"


def test_ingest_starlink_db_unavailable_devuelve_503(monkeypatch):
    fake_db = _FakeNetHealthDB()
    fake_db.raise_on_insert = ConnectionError("db down")
    monkeypatch.setattr(ingest_router, "_get_net_db", lambda: fake_db)

    resp = client.post("/api/v1/ingest/starlink", json=_valid_ingest_payload(), headers=HEADERS)
    assert resp.status_code == 503
    assert resp.json()["code"] == "DB_UNAVAILABLE"
