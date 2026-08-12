"""
Suite UT-03 — Router de tópicos MQTT (docs/08_Plan_QA.md §4.1).

Cubre UT-03-01 a UT-03-05: enrutamiento por dominio (starlink/meteo, ADR-10),
tópico desconocido sin crash, y que un error de DB no propague (retiene el
ACK MQTT en vez de tumbar el consumer, RF-18/RNF-05).
"""

from datetime import datetime, timezone

import pytest

from consumer.router import ConsumerRouter


class FakeDB:
    """Doble de NetHealthDB/MeteoDB: registra llamadas, opcionalmente falla."""

    def __init__(self, raises: Exception | None = None):
        self.raises = raises
        self.calls: list[dict] = []

    def insert(self, row):
        if self.raises is not None:
            raise self.raises
        self.calls.append(row)


def payload_valido(**overrides):
    base = {
        "schema_version": "1.1",
        "node_id": "lit-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "latency_ms": 42.7,
            "jitter_ms": 5.3,
            "packet_loss_pct": 0.8,
            "throughput_down_bps": 185340000,
            "throughput_up_bps": 12450000,
            "snr_low": False,
            "is_obstructed": False,
            "satellite_count": 14,
            "handover_count": 0,
            "outage_duration_ms": 0.0,
            "tilt_angle_deg": 2.1,
            "boresight_azimuth_deg": -175.7,
            "boresight_elevation_deg": 51.7,
            "desired_boresight_azimuth_deg": -176.0,
            "desired_boresight_elevation_deg": 52.0,
            "attitude_uncertainty_deg": 0.3,
        },
    }
    base.update(overrides)
    return base


def test_ut_03_01_starlink_topic_routes_to_net_db():
    net_db, meteo_db = FakeDB(), FakeDB()
    router = ConsumerRouter(net_db=net_db, meteo_db=meteo_db)

    ok = router.route_message("starlink/metrics/lit-01", payload_valido())

    assert ok is True
    assert len(net_db.calls) == 1
    assert net_db.calls[0]["node_id"] == "lit-01"
    assert len(meteo_db.calls) == 0


def test_ut_03_02_meteo_sensor_topic_routes_to_meteo_db():
    net_db, meteo_db = FakeDB(), FakeDB()
    router = ConsumerRouter(net_db=net_db, meteo_db=meteo_db)

    ok = router.route_message("meteo/sensor/lit-01", {"source": "local_sensor"})

    assert ok is True
    assert len(meteo_db.calls) == 1
    assert len(net_db.calls) == 0


def test_ut_03_03_meteo_external_topic_routes_to_meteo_db_with_source():
    net_db, meteo_db = FakeDB(), FakeDB()
    router = ConsumerRouter(net_db=net_db, meteo_db=meteo_db)

    ok = router.route_message("meteo/external/lit-01", {"source": "api_open_meteo"})

    assert ok is True
    assert meteo_db.calls[0]["source"] == "api_open_meteo"
    assert len(net_db.calls) == 0


def test_ut_03_04_unknown_topic_does_not_crash(caplog):
    net_db, meteo_db = FakeDB(), FakeDB()
    router = ConsumerRouter(net_db=net_db, meteo_db=meteo_db)

    with caplog.at_level("WARNING", logger="consumer"):
        ok = router.route_message("unknown/topic", {"anything": True})

    assert ok is True
    assert len(net_db.calls) == 0
    assert len(meteo_db.calls) == 0
    assert any(r.levelname == "WARNING" for r in caplog.records)


def test_ut_03_05_db_error_does_not_propagate_and_withholds_ack(caplog):
    net_db = FakeDB(raises=ConnectionError("db unreachable"))
    meteo_db = FakeDB()
    router = ConsumerRouter(net_db=net_db, meteo_db=meteo_db)

    with caplog.at_level("ERROR", logger="consumer"):
        ok = router.route_message("starlink/metrics/lit-01", payload_valido())

    assert ok is False
    assert any(r.levelname == "ERROR" for r in caplog.records)


def test_invalid_payload_is_logged_and_acked_not_retried(caplog):
    """IT-01-02: payload inválido no persiste, pero tampoco debe reintentarse
    para siempre (es un error permanente, no transitorio)."""
    net_db, meteo_db = FakeDB(), FakeDB()
    router = ConsumerRouter(net_db=net_db, meteo_db=meteo_db)

    with caplog.at_level("ERROR", logger="consumer"):
        ok = router.route_message(
            "starlink/metrics/lit-01", payload_valido(metrics={"latency_ms": -999})
        )

    assert ok is True
    assert len(net_db.calls) == 0
    assert any(r.levelname == "ERROR" for r in caplog.records)


def test_multiple_nodes_route_independently():
    """IT-01-05 a nivel de router: mensajes de distintos nodos no se mezclan."""
    net_db, meteo_db = FakeDB(), FakeDB()
    router = ConsumerRouter(net_db=net_db, meteo_db=meteo_db)

    router.route_message("starlink/metrics/lit-cordoba-01", payload_valido(node_id="lit-cordoba-01"))
    router.route_message("starlink/metrics/lit-test-02", payload_valido(node_id="lit-test-02"))

    node_ids = {row["node_id"] for row in net_db.calls}
    assert node_ids == {"lit-cordoba-01", "lit-test-02"}
