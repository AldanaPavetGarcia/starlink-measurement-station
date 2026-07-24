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


def test_ut_04_04_schema_version_es_siempre_1_0():
    agent = StarlinkMockAgent("lit-cordoba-01", rng=random.Random(4))
    for _ in range(100):
        assert agent.generate_payload()["schema_version"] == SCHEMA_VERSION


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
        "throughput_up_bps", "snr_db", "is_obstructed", "satellite_count",
    }
    timestamps = [p["timestamp"] for p in recibidos]
    assert timestamps == sorted(timestamps)  # avanza monótonamente
