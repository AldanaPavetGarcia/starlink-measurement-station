"""
Tests directos de src/backend/db.py: construcción de engines (lazy, no abre
conexión de red hasta el primer `.connect()`) y las tres funciones de
healthcheck (`ping`, `ping_mqtt_broker`, `last_write`) contra dobles
mínimos -- sin Postgres/Mosquitto reales.
"""

import os
import socket
import threading
from datetime import datetime, timezone

os.environ.setdefault("BACKEND_API_KEY", "test-api-key-fase4-db")

import backend.db as db  # noqa: E402
from tests.backend_fakes import FakeEngine  # noqa: E402


def test_starlink_engine_es_lazy_y_no_abre_conexion():
    """create_engine() no conecta hasta el primer uso -- construirlo no
    debería tocar la red ni lanzar aunque la DB no exista."""
    db._starlink_engine = None  # reset del singleton del módulo
    engine = db.starlink_engine()
    assert engine is not None
    assert db.starlink_engine() is engine  # memoizado


def test_station_config_engine_es_lazy_y_memoizado():
    db._station_config_engine = None
    engine = db.station_config_engine()
    assert db.station_config_engine() is engine


def test_ping_up():
    fake = FakeEngine([[{"?column?": 1}]])
    result = db.ping(fake)
    assert result["status"] == "up"
    assert result["latency_ms"] is not None


def test_ping_down_si_connect_lanza():
    class _BrokenEngine:
        def connect(self):
            raise ConnectionRefusedError("no hay nada escuchando")

    result = db.ping(_BrokenEngine())
    assert result["status"] == "down"
    assert result["latency_ms"] is None
    assert "no hay nada escuchando" in result["error"]


def test_ping_mqtt_broker_up():
    """Levanta un socket TCP local real de prueba -- no Mosquitto, solo algo
    que acepte la conexión para ejercitar la rama 'up'."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    host, port = server.getsockname()

    def _accept_once():
        try:
            conn, _ = server.accept()
            conn.close()
        except OSError:
            pass

    thread = threading.Thread(target=_accept_once, daemon=True)
    thread.start()
    try:
        result = db.ping_mqtt_broker(host, port, timeout_s=2.0)
    finally:
        server.close()
        thread.join(timeout=2)

    assert result["status"] == "up"
    assert result["latency_ms"] is not None


def test_ping_mqtt_broker_down_puerto_sin_nada_escuchando():
    result = db.ping_mqtt_broker("localhost", 1, timeout_s=0.5)
    assert result["status"] == "down"
    assert result["latency_ms"] is None


def test_last_write_con_filas():
    now = datetime.now(timezone.utc)
    fake = FakeEngine([[{"max": now}]])
    assert db.last_write(fake, "network_metrics") == now.isoformat().replace("+00:00", "Z")


def test_last_write_tabla_vacia_devuelve_none():
    fake = FakeEngine([[{"max": None}]])
    assert db.last_write(fake, "network_metrics") is None
