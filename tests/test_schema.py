"""
Suite UT-01 — Validación del esquema de telemetría Starlink (ADR-01).

Cubre:
  1. Un payload válido "de referencia" se acepta tal cual.
  2. 1000 payloads válidos generados aleatoriamente no producen ValidationError.
  3. satellite_count es opcional (con y sin el campo, ambos válidos).
  4. Casos límite / inválidos: rangos fuera de límite, tipos incorrectos,
     schema_version incorrecta, timestamp sin timezone, timestamp en el
     futuro, valores NaN/Infinity, node_id con formato inválido.

Cómo correrla:
    pytest tests/test_schema.py -v
    pytest tests/test_schema.py --cov=src/mock_starlink --cov-report=term-missing
"""

import math
import random
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from mock_starlink import StarlinkPayloadIn, SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def payload_valido(**overrides):
    """Payload de referencia, válido según el esquema del ADR-01.
    `overrides` permite pisar campos de nivel superior o de `metrics`."""
    base = {
        "schema_version": SCHEMA_VERSION,
        "node_id": "lit-cordoba-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "latency_ms": 42.7,
            "jitter_ms": 5.3,
            "packet_loss_pct": 0.8,
            "throughput_down_bps": 185_340_000,
            "throughput_up_bps": 12_450_000,
            "snr_db": 9.2,
            "is_obstructed": False,
            "satellite_count": 14,
        },
    }
    metrics_overrides = overrides.pop("metrics", {})
    base["metrics"].update(metrics_overrides)
    base.update(overrides)
    return base


def payload_aleatorio(rng: random.Random):
    """Genera un payload válido con valores aleatorios dentro de rangos
    realistas, para el test de volumen (1000 iteraciones)."""
    return payload_valido(
        node_id=rng.choice(["lit-cordoba-01", "lit-cordoba-02", "nodo-test-3"]),
        timestamp=(datetime.now(timezone.utc) - timedelta(seconds=rng.randint(0, 3600))).isoformat(),
        metrics={
            "latency_ms": rng.uniform(15, 400),
            "jitter_ms": rng.uniform(0, 50),
            "packet_loss_pct": rng.uniform(0, 100),
            "throughput_down_bps": rng.uniform(0, 300_000_000),
            "throughput_up_bps": rng.uniform(0, 40_000_000),
            "snr_db": rng.uniform(-10, 15),
            "is_obstructed": rng.choice([True, False]),
            "satellite_count": rng.choice([None, rng.randint(0, 30)]),
        },
    )


# ---------------------------------------------------------------------------
# 1. Payload de referencia
# ---------------------------------------------------------------------------

def test_payload_valido_de_referencia_es_aceptado():
    payload = StarlinkPayloadIn.model_validate(payload_valido())
    assert payload.schema_version == SCHEMA_VERSION
    assert payload.node_id == "lit-cordoba-01"
    assert payload.metrics.satellite_count == 14


# ---------------------------------------------------------------------------
# 2. Test de volumen: 1000 payloads generados sin ValidationError
# ---------------------------------------------------------------------------

def test_1000_payloads_generados_no_producen_validation_error():
    rng = random.Random(42)  # semilla fija -> test reproducible
    errores = []
    for i in range(1000):
        data = payload_aleatorio(rng)
        try:
            StarlinkPayloadIn.model_validate(data)
        except ValidationError as e:
            errores.append((i, str(e)))

    assert not errores, (
        f"{len(errores)}/1000 payloads generados fallaron la validación. "
        f"Primer error: {errores[0] if errores else None}"
    )


# ---------------------------------------------------------------------------
# 3. satellite_count es opcional
# ---------------------------------------------------------------------------

def test_satellite_count_ausente_es_valido():
    data = payload_valido()
    del data["metrics"]["satellite_count"]
    payload = StarlinkPayloadIn.model_validate(data)
    assert payload.metrics.satellite_count is None


def test_satellite_count_null_explicito_es_valido():
    payload = StarlinkPayloadIn.model_validate(payload_valido(metrics={"satellite_count": None}))
    assert payload.metrics.satellite_count is None


def test_satellite_count_negativo_es_invalido():
    with pytest.raises(ValidationError):
        StarlinkPayloadIn.model_validate(payload_valido(metrics={"satellite_count": -1}))


# ---------------------------------------------------------------------------
# 4. Casos límite — campos de metrics fuera de rango
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("campo,valor_invalido", [
    ("packet_loss_pct", -0.1),
    ("packet_loss_pct", 100.1),
    ("packet_loss_pct", 150),
    ("latency_ms", -1),
    ("latency_ms", 5001),
    ("jitter_ms", -0.01),
    ("snr_db", -21),
    ("snr_db", 31),
    ("throughput_down_bps", -1),
    ("throughput_up_bps", -1),
])
def test_metricas_fuera_de_rango_son_rechazadas(campo, valor_invalido):
    with pytest.raises(ValidationError):
        StarlinkPayloadIn.model_validate(payload_valido(metrics={campo: valor_invalido}))


@pytest.mark.parametrize("campo", [
    "latency_ms", "jitter_ms", "packet_loss_pct",
    "throughput_down_bps", "throughput_up_bps", "snr_db",
])
def test_nan_es_rechazado_en_campos_numericos(campo):
    with pytest.raises(ValidationError):
        StarlinkPayloadIn.model_validate(payload_valido(metrics={campo: math.nan}))


@pytest.mark.parametrize("campo", [
    "latency_ms", "jitter_ms", "throughput_down_bps", "throughput_up_bps",
])
def test_infinity_es_rechazado_en_campos_con_validador_explicito(campo):
    with pytest.raises(ValidationError):
        StarlinkPayloadIn.model_validate(payload_valido(metrics={campo: math.inf}))


@pytest.mark.parametrize("campo_nullable", [
    "latency_ms", "jitter_ms", "packet_loss_pct",
    "throughput_down_bps", "throughput_up_bps", "snr_db", "is_obstructed",
])
def test_campos_nullable_del_der_aceptan_ausencia(campo_nullable):
    """docs/06_DER.md marca estos campos NULL='S' (la medición puede fallar,
    ej. ping sin respuesta o API interna de la antena no accesible): el
    paquete se acepta igual, con el campo ausente."""
    data = payload_valido()
    del data["metrics"][campo_nullable]
    payload = StarlinkPayloadIn.model_validate(data)
    assert getattr(payload.metrics, campo_nullable) is None


@pytest.mark.parametrize("campo_nullable", [
    "latency_ms", "jitter_ms", "packet_loss_pct",
    "throughput_down_bps", "throughput_up_bps", "snr_db", "is_obstructed",
])
def test_campos_nullable_del_der_aceptan_null_explicito(campo_nullable):
    payload = StarlinkPayloadIn.model_validate(
        payload_valido(metrics={campo_nullable: None})
    )
    assert getattr(payload.metrics, campo_nullable) is None


# ---------------------------------------------------------------------------
# 5. Casos límite — nivel superior del paquete
# ---------------------------------------------------------------------------

def test_schema_version_incorrecta_es_rechazada():
    with pytest.raises(ValidationError, match="schema_version"):
        StarlinkPayloadIn.model_validate(payload_valido(schema_version="0.9"))


def test_schema_version_faltante_es_rechazada():
    data = payload_valido()
    del data["schema_version"]
    with pytest.raises(ValidationError):
        StarlinkPayloadIn.model_validate(data)


@pytest.mark.parametrize("node_id_invalido", [
    "",                      # vacío
    "LIT-CORDOBA-01",        # mayúsculas
    "lit_cordoba_01",        # guion bajo en vez de guion medio
    "-lit-cordoba-01",       # empieza con guion
    "lit-cordoba-01-",       # termina con guion
    "lit cordoba 01",        # espacios
    "a" * 65,                # excede longitud máxima
])
def test_node_id_con_formato_invalido_es_rechazado(node_id_invalido):
    with pytest.raises(ValidationError):
        StarlinkPayloadIn.model_validate(payload_valido(node_id=node_id_invalido))


def test_timestamp_sin_timezone_es_rechazado():
    """Un timestamp naive (sin tzinfo) es ambiguo -> se rechaza explícitamente
    en vez de asumir UTC silenciosamente."""
    data = payload_valido(timestamp="2026-07-05T14:32:10.123")
    with pytest.raises(ValidationError, match="zona horaria"):
        StarlinkPayloadIn.model_validate(data)


def test_timestamp_muy_en_el_futuro_es_rechazado():
    futuro = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    with pytest.raises(ValidationError, match="futuro"):
        StarlinkPayloadIn.model_validate(payload_valido(timestamp=futuro))


def test_timestamp_con_pequeno_desfasaje_es_tolerado():
    """Tolera hasta 30s de futuro para no romper por relojes NTP no sincronizados."""
    casi_ahora = (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat()
    payload = StarlinkPayloadIn.model_validate(payload_valido(timestamp=casi_ahora))
    assert payload.timestamp is not None


def test_metrics_faltante_es_rechazado():
    data = payload_valido()
    del data["metrics"]
    with pytest.raises(ValidationError):
        StarlinkPayloadIn.model_validate(data)


def test_campo_extra_desconocido_no_rompe_la_validacion():
    """Por defecto Pydantic ignora campos extra no declarados; se deja
    documentado el comportamiento actual (no se exige `extra='forbid'`)."""
    data = payload_valido()
    data["campo_no_definido_en_el_adr"] = "algo"
    StarlinkPayloadIn.model_validate(data)  # no debería lanzar
    