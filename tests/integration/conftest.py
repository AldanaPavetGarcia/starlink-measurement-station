"""
Fixtures compartidas de la suite de integración IT-01 (docs/08_Plan_QA.md §4.2).

Requiere la pila real levantada (`docker compose --profile mocks up -d
broker starlink_db` -- sin el mock_starlink corriendo, para no competir con
los mensajes de prueba que publica cada test). Se saltea automáticamente si
Docker o los contenedores no están disponibles, para que `pytest tests/`
(sin infraestructura) siga funcionando -- ver `pytest.ini`.

Nunca conecta directo por TCP a Postgres (ADR-14: starlink_health_db no
expone su puerto ni siquiera al host) -- usa `docker exec ... psql`, mismo
método ya usado a mano en sesiones anteriores (ver docs/PROGRESS.md).
"""

from __future__ import annotations

import json
import subprocess
import time

import pytest

BROKER_HOST = "localhost"
BROKER_PORT = 1883
DB_CONTAINER = "starlink-health-db"
DB_NAME = "starlink_health"
DB_USER = "starlink_app"


def _docker_available() -> bool:
    try:
        subprocess.run(["docker", "info"], capture_output=True, timeout=5, check=True)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False
    return True


def _container_running(name: str) -> bool:
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", name],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def _stack_ready() -> bool:
    return _docker_available() and _container_running(DB_CONTAINER)


@pytest.fixture(scope="session", autouse=True)
def _skip_if_no_stack():
    if not _stack_ready():
        pytest.skip(
            f"suite de integración IT-01 requiere la pila real levantada "
            f"(docker compose --profile mocks up -d broker starlink_db) -- "
            f"contenedor '{DB_CONTAINER}' no está corriendo",
            allow_module_level=True,
        )


def db_query(sql: str) -> str:
    """Ejecuta `sql` vía `docker exec ... psql -t -A -c` (sin exponer el
    puerto de Postgres al host, ADR-14) y devuelve stdout crudo."""
    result = subprocess.run(
        ["docker", "exec", DB_CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", sql],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"psql falló: {result.stderr}")
    return result.stdout.strip()


def db_count(node_id: str) -> int:
    out = db_query(f"SELECT COUNT(*) FROM network_metrics WHERE node_id = '{node_id}';")
    return int(out)


@pytest.fixture
def mqtt_publisher():
    """Cliente MQTT mínimo para publicar mensajes de prueba directo al
    tópico, sin pasar por el mock (los tests IT-01 controlan el payload
    exacto que quieren probar, incluidos los inválidos de IT-01-02)."""
    import paho.mqtt.client as mqtt

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=30)
    client.loop_start()

    def _publish(topic: str, payload: dict, qos: int = 1) -> None:
        info = client.publish(topic, json.dumps(payload), qos=qos)
        info.wait_for_publish(timeout=5)

    yield _publish

    client.loop_stop()
    client.disconnect()


def wait_until(predicate, timeout_s: float = 5.0, interval_s: float = 0.2) -> bool:
    """Poll simple -- evita sleeps fijos que son o muy cortos (flaky) o muy
    largos (suite lenta) para una condición que en la práctica resuelve en
    milisegundos la mayoría de las veces."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval_s)
    return predicate()
