"""
Suite UT-04 — Mock Stateful con Random Walk (ADR-06), tal como está especificada
en docs/08_Plan_QA.md.

Cómo correrla:
    PYTHONPATH=src pytest tests/test_mock.py -v
"""

import random

import pytest
from pydantic import ValidationError

from mock_starlink import CHAOS_PROFILES, SCHEMA_VERSION, StarlinkMockAgent, StarlinkPayloadIn


def test_ut_04_01_latencia_nunca_por_debajo_del_piso_fisico_leo():
    agent = StarlinkMockAgent("lit-cordoba-01", chaos_profile="CALM", rng=random.Random(1))
    for _ in range(10_000):
        payload = agent.generate_payload()
        assert payload["metrics"]["latency_ms"] >= 20.0


def test_ut_04_02_perfil_storm_inyecta_spikes_de_handover():
    agent = StarlinkMockAgent("lit-cordoba-01", chaos_profile="STORM", rng=random.Random(2))
    n = 1000
    spikes = sum(1 for _ in range(n) if agent.generate_payload()["metrics"]["latency_ms"] > 150)
    assert spikes / n >= 0.15


def test_ut_04_03_payload_generado_supera_validacion_pydantic():
    agent = StarlinkMockAgent("lit-cordoba-01", chaos_profile="STORM", rng=random.Random(3))
    errores = []
    for _ in range(1000):
        try:
            StarlinkPayloadIn.model_validate(agent.generate_payload())
        except ValidationError as exc:
            errores.append(exc)
    assert errores == []


def test_ut_04_04_schema_version_es_siempre_1_1():
    agent = StarlinkMockAgent("lit-cordoba-01", rng=random.Random(4))
    for _ in range(100):
        assert agent.generate_payload()["schema_version"] == SCHEMA_VERSION == "1.1"


# ---------------------------------------------------------------------------
# Casos adicionales de robustez del constructor / perfiles
# ---------------------------------------------------------------------------

def test_chaos_profile_invalido_rechazado():
    with pytest.raises(ValueError):
        StarlinkMockAgent("lit-cordoba-01", chaos_profile="TORNADO")


def test_time_warp_factor_invalido_rechazado():
    with pytest.raises(ValueError):
        StarlinkMockAgent("lit-cordoba-01", time_warp_factor=0)


@pytest.mark.parametrize("profile", CHAOS_PROFILES)
def test_todos_los_perfiles_generan_payloads_validos(profile):
    agent = StarlinkMockAgent("lit-cordoba-01", chaos_profile=profile, rng=random.Random(5))
    for _ in range(200):
        StarlinkPayloadIn.model_validate(agent.generate_payload())


def test_handover_count_y_outage_duration_correlacionan(): # ADR-16
    agent = StarlinkMockAgent("lit-cordoba-01", chaos_profile="HANDOVER_HEAVY", rng=random.Random(9))
    vio_handover = False
    for _ in range(500):
        m = agent.generate_payload()["metrics"]
        assert m["handover_count"] in (0, 1)
        if m["handover_count"] == 1:
            vio_handover = True
            assert 200.0 <= m["outage_duration_ms"] <= 1200.0
        else:
            assert m["outage_duration_ms"] == 0.0
    assert vio_handover, "HANDOVER_HEAVY debería producir al menos un handover en 500 ticks"


def test_alignment_fields_se_mantienen_dentro_de_rango(): # ADR-18
    agent = StarlinkMockAgent("lit-cordoba-01", chaos_profile="STORM", rng=random.Random(10))
    for _ in range(1000):
        m = agent.generate_payload()["metrics"]
        assert 0.0 <= m["boresight_azimuth_deg"] <= 360.0
        assert 0.0 <= m["boresight_elevation_deg"] <= 90.0
        assert 0.0 <= m["desired_boresight_azimuth_deg"] <= 360.0
        assert 0.0 <= m["desired_boresight_elevation_deg"] <= 90.0
        assert 0.0 <= m["tilt_angle_deg"] <= 90.0
        assert m["attitude_uncertainty_deg"] >= 0.0
    # el apuntamiento deseado es fijo por nodo (no cambia entre ticks)
    payload = agent.generate_payload()
    assert payload["metrics"]["desired_boresight_azimuth_deg"] == pytest.approx(
        agent._desired_azimuth_deg, abs=0.01
    )


def test_time_warp_factor_arranca_el_backfill_en_el_pasado():
    from datetime import datetime, timezone

    agent = StarlinkMockAgent("lit-cordoba-01", time_warp_factor=3600, rng=random.Random(6))
    assert agent.sim_time < datetime.now(timezone.utc)
    assert agent.interval_s == pytest.approx(60.0 / 3600)


def test_time_warp_factor_1_arranca_cerca_del_presente():
    from datetime import datetime, timedelta, timezone

    agent = StarlinkMockAgent("lit-cordoba-01", time_warp_factor=1, rng=random.Random(7))
    delta = datetime.now(timezone.utc) - agent.sim_time
    assert abs(delta.total_seconds()) < 5


def test_run_publica_y_avanza_el_tiempo_simulado():
    import asyncio

    agent = StarlinkMockAgent(
        "lit-cordoba-01", time_warp_factor=3600, rng=random.Random(8)
    )
    recibidos = []

    async def publish_callback(payload):
        recibidos.append(payload)
        if len(recibidos) >= 3:
            raise StopAsyncIteration

    async def main():
        await agent.run(publish_callback)

    with pytest.raises(StopAsyncIteration):
        asyncio.run(main())

    assert len(recibidos) == 3
    t0 = recibidos[0]["metrics"]
    assert set(t0.keys()) == {
        "latency_ms", "jitter_ms", "packet_loss_pct", "throughput_down_bps",
        "throughput_up_bps", "snr_low", "is_obstructed", "satellite_count",
        "handover_count", "outage_duration_ms", "tilt_angle_deg",
        "boresight_azimuth_deg", "boresight_elevation_deg",
        "desired_boresight_azimuth_deg", "desired_boresight_elevation_deg",
        "attitude_uncertainty_deg",
    }
    timestamps = [p["timestamp"] for p in recibidos]
    assert timestamps == sorted(timestamps)  # avanza monótonamente
