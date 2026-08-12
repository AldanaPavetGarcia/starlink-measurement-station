"""
Suite IT-01 — Pipeline MQTT → TimescaleDB (docs/08_Plan_QA.md §4.2),
automatizada. Hasta esta sesión se verificaba a mano (`docker compose
--profile mocks up --build` + inspección manual, ver docs/PROGRESS.md
semanas 6-8) -- estos tests reproducen exactamente esos mismos pasos.

Requiere: `docker compose --profile mocks up -d broker starlink_db
station_config_db consumer` corriendo (sin mock_starlink, para no competir
con los payloads de prueba de cada test -- ver conftest.py). Se saltea sola
si esos contenedores no están arriba.

⚠️ No ejecutada en esta sesión (espacio en disco de la máquina compartida,
ver docs/PROGRESS.md §Semana 9) -- revisar/correr en la próxima sesión con
la pila levantada antes de dar por cerrada la Fase 4.
"""

import subprocess
import time
import uuid
from datetime import datetime, timezone

import pytest

from tests.integration.conftest import db_count, wait_until

TOPIC = "starlink/metrics/{node_id}"


def _valid_payload(node_id: str, **metrics_overrides) -> dict:
    metrics = {
        "latency_ms": 35.4, "jitter_ms": 4.2, "packet_loss_pct": 0.1,
        "throughput_down_bps": 180_000_000, "throughput_up_bps": 20_000_000,
        "snr_low": False, "is_obstructed": False, "satellite_count": 14,
        "handover_count": 0, "outage_duration_ms": 0.0,
        "tilt_angle_deg": 2.0, "boresight_azimuth_deg": 180.0,
        "boresight_elevation_deg": 50.0, "desired_boresight_azimuth_deg": 180.0,
        "desired_boresight_elevation_deg": 50.0, "attitude_uncertainty_deg": 0.2,
    }
    metrics.update(metrics_overrides)
    return {
        "schema_version": "1.1",
        "node_id": node_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }


def _fresh_node_id(prefix: str = "it01-test") -> str:
    """node_id único por test corrido -- evita que corridas anteriores
    dejen filas viejas que inflen los COUNT(*) de este test."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# IT-01-01 — Mensaje válido persiste en DB
# ---------------------------------------------------------------------------

def test_it_01_01_mensaje_valido_persiste_en_db(mqtt_publisher):
    node_id = _fresh_node_id()
    mqtt_publisher(TOPIC.format(node_id=node_id), _valid_payload(node_id), qos=1)

    assert wait_until(lambda: db_count(node_id) == 1, timeout_s=5.0), (
        "el mensaje publicado no apareció en network_metrics dentro de 5s"
    )


# ---------------------------------------------------------------------------
# IT-01-02 — Mensaje inválido no persiste
# ---------------------------------------------------------------------------

def test_it_01_02_mensaje_invalido_no_persiste(mqtt_publisher):
    node_id = _fresh_node_id()
    payload_invalido = _valid_payload(node_id, latency_ms=-999)
    mqtt_publisher(TOPIC.format(node_id=node_id), payload_invalido, qos=1)

    time.sleep(2)  # ventana suficiente para que el consumer procese y descarte
    assert db_count(node_id) == 0


# ---------------------------------------------------------------------------
# IT-01-04 — 100 mensajes consecutivos persisten sin pérdida
# ---------------------------------------------------------------------------

def test_it_01_04_cien_mensajes_consecutivos_sin_perdida(mqtt_publisher):
    node_id = _fresh_node_id()
    for _ in range(100):
        mqtt_publisher(TOPIC.format(node_id=node_id), _valid_payload(node_id), qos=1)
        time.sleep(0.1)

    assert wait_until(lambda: db_count(node_id) == 100, timeout_s=15.0), (
        f"esperaba 100 filas, hay {db_count(node_id)}"
    )


# ---------------------------------------------------------------------------
# IT-01-05 — Mensajes de múltiples nodos enrutados correctamente
# ---------------------------------------------------------------------------

def test_it_01_05_multiples_nodos_no_se_mezclan(mqtt_publisher):
    node_a, node_b = _fresh_node_id("it01-a"), _fresh_node_id("it01-b")

    for _ in range(50):
        mqtt_publisher(TOPIC.format(node_id=node_a), _valid_payload(node_a), qos=1)
        mqtt_publisher(TOPIC.format(node_id=node_b), _valid_payload(node_b), qos=1)

    assert wait_until(lambda: db_count(node_a) == 50, timeout_s=15.0)
    assert wait_until(lambda: db_count(node_b) == 50, timeout_s=15.0)


# ---------------------------------------------------------------------------
# IT-01-03 — QoS 1 reentrega mensaje tras caída del consumer
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_it_01_03_qos1_reentrega_tras_caida_del_consumer(mqtt_publisher):
    """Más invasivo que el resto (mata y reinicia el contenedor consumer) --
    marcado aparte para poder excluirlo con `-m "not integration"` si se
    quiere correr el resto de IT-01 sin tocar contenedores en ejecución."""
    node_id = _fresh_node_id("it01-qos1")

    subprocess.run(["docker", "stop", "starlink-consumer"], check=True, timeout=15)
    try:
        mqtt_publisher(TOPIC.format(node_id=node_id), _valid_payload(node_id), qos=1)
        time.sleep(1)
        assert db_count(node_id) == 0, "no debería haber nada persistido con el consumer caído"
    finally:
        subprocess.run(["docker", "start", "starlink-consumer"], check=True, timeout=15)

    assert wait_until(lambda: db_count(node_id) == 1, timeout_s=20.0), (
        "el broker debería haber reentregado el mensaje QoS 1 retenido al reconectar el consumer"
    )
