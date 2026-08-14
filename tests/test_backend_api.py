"""
Tests del backend FastAPI (semana 9, docs/07_API_REST.md) que NO requieren
DB/broker real: auth, envelope de error, y el healthcheck degradándose sin
tumbarse cuando las DBs no están disponibles. Los endpoints que sí necesitan
datos reales (network_metrics, station_metadata) quedan para la suite de
integración (Fase 4, tests/integration/), consistente con IT-03 de
docs/08_Plan_QA.md.

BACKEND_API_KEY se fija ANTES de importar backend.main (config.py lee env
vars al importarse) -- no puede ir en un fixture normal de pytest porque
correría después del import a nivel de módulo.
"""

import os

os.environ.setdefault("BACKEND_API_KEY", "test-api-key-fase2")
os.environ.setdefault("ENABLE_INGEST_ENDPOINT", "false")
# Apuntar a un puerto que casi seguro no tiene nada escuchando, para que
# db.ping()/ping_mqtt_broker() fallen rápido (ECONNREFUSED) en vez de colgar
# el test esperando un timeout de conexión largo.
os.environ.setdefault("STARLINK_DB_HOST", "localhost")
os.environ.setdefault("STARLINK_DB_PORT", "59999")
os.environ.setdefault("STATION_CONFIG_DB_HOST", "localhost")
os.environ.setdefault("STATION_CONFIG_DB_PORT", "59999")
os.environ.setdefault("MQTT_HOST", "localhost")
os.environ.setdefault("MQTT_PORT", "59999")

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402

client = TestClient(app)
API_KEY = os.environ["BACKEND_API_KEY"]


# ---------------------------------------------------------------------------
# GET /health -- público, siempre 200, se degrada sin tumbarse
# ---------------------------------------------------------------------------

def test_health_no_requiere_api_key():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200


def test_health_degradado_si_las_dbs_no_estan_disponibles():
    """Sin Postgres/Mosquitto reales escuchando (ver env vars arriba), el
    healthcheck debe reportar 'degraded', no crashear ni devolver 5xx."""
    resp = client.get("/api/v1/health")
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["components"]["db_starlink_health"]["status"] == "down"
    assert body["components"]["mqtt_broker"]["status"] == "down"
    assert body["components"]["db_meteo_data"]["status"] == "not_configured"


# ---------------------------------------------------------------------------
# Auth (docs/07_API_REST.md §2.1) -- 401 antes de tocar cualquier DB
# ---------------------------------------------------------------------------

def test_metrics_starlink_sin_api_key_devuelve_401():
    resp = client.get(
        "/api/v1/metrics/starlink",
        params={"node_id": "lit-test", "start": "2026-06-01T00:00:00Z", "end": "2026-06-02T00:00:00Z"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["status"] == "error"
    assert body["code"] == "AUTH_FAILED"


def test_metrics_starlink_con_api_key_incorrecta_devuelve_401():
    resp = client.get(
        "/api/v1/metrics/starlink",
        params={"node_id": "lit-test", "start": "2026-06-01T00:00:00Z", "end": "2026-06-02T00:00:00Z"},
        headers={"X-API-Key": "clave-incorrecta"},
    )
    assert resp.status_code == 401


def test_nodes_sin_api_key_devuelve_401():
    resp = client.get("/api/v1/nodes")
    assert resp.status_code == 401


def test_ingest_starlink_sin_api_key_devuelve_401():
    resp = client.post("/api/v1/ingest/starlink", json={})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Envelope de error (docs/07_API_REST.md §3.2) -- forma consistente
# ---------------------------------------------------------------------------

def test_envelope_de_error_tiene_las_claves_esperadas():
    resp = client.get("/api/v1/metrics/starlink")  # sin auth ni params
    body = resp.json()
    assert set(body.keys()) == {"status", "code", "detail", "timestamp", "path"}
    assert body["status"] == "error"
    assert body["path"] == "/api/v1/metrics/starlink"


def test_query_params_faltantes_devuelve_400_validation_error():
    """node_id/start/end son requeridos -- FastAPI los rechaza como
    RequestValidationError, que el handler global traduce a 400
    VALIDATION_ERROR en vez del 422 default de FastAPI (docs §3.3)."""
    resp = client.get("/api/v1/metrics/starlink", headers={"X-API-Key": API_KEY})
    assert resp.status_code == 400
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_validation_error_detail_no_filtra_paths_internos():
    """Hallazgo 13/8/2026 (docs/PROGRESS.md): `str(RequestValidationError)`
    en FastAPI 0.141/Starlette 1.6 incluye el path del archivo y línea del
    handler dentro del contenedor -- una fuga de detalle interno (ADR-14).
    El handler global arma el `detail` a partir de `exc.errors()` en cambio,
    para dar un mensaje legible sin exponer la ruta del filesystem."""
    resp = client.get("/api/v1/metrics/starlink", headers={"X-API-Key": API_KEY})
    detail = resp.json()["detail"]
    assert "File \"" not in detail
    assert "src/backend" not in detail
    assert "start" in detail and "end" in detail


def test_start_posterior_a_end_devuelve_400_validation_error():
    resp = client.get(
        "/api/v1/metrics/starlink",
        params={"node_id": "lit-test", "start": "2026-06-07T00:00:00Z", "end": "2026-06-01T00:00:00Z"},
        headers={"X-API-Key": API_KEY},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# POST /ingest/starlink -- INGEST_DISABLED no necesita tocar la DB
# ---------------------------------------------------------------------------

def test_ingest_disabled_por_default():
    resp = client.post(
        "/api/v1/ingest/starlink",
        json={"node_id": "lit-test"},
        headers={"X-API-Key": API_KEY},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "INGEST_DISABLED"


# ---------------------------------------------------------------------------
# Docs OpenAPI (RF implícito de docs/07_API_REST.md §1: Swagger UI en /api/v1/docs)
# ---------------------------------------------------------------------------

def test_openapi_json_disponible():
    resp = client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    assert resp.json()["info"]["title"] == "Starlink Measurement Station API"
