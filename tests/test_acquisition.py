"""
Tests de src/acquisition/: las funciones puras de mapeo (starlink_extractor)
contra JSON sintético, y grpc_client con subprocess.run mockeado (sin
ejecutar grpcurl real).

Los nombres y rangos de campo del fixture (`isSnrAboveNoiseFloor`, ausencia
de `obstructionStats.currentlyObstructed`/uso de `fractionObstructed`,
`boresightAzimuthDeg` en rango firmado -180..180) fueron confirmados contra
la antena real en el LIT el 12/08/2026 -- ver la cabecera de
starlink_extractor.py para el detalle completo.
"""

import subprocess

import pytest

from acquisition.grpc_client import GrpcClientError, get_diagnostics, get_status
from acquisition.starlink_extractor import build_metrics, count_handovers, derive_jitter_loss, map_status

# ---------------------------------------------------------------------------
# Fixtures sintéticas (estructura documentada, no datos reales)
# ---------------------------------------------------------------------------

STATUS_FIXTURE = {
    "dishGetStatus": {
        "popPingLatencyMs": 24.5,
        "downlinkThroughputBps": "668000",  # protobuf int64 como string
        "uplinkThroughputBps": "173000",
        "isSnrAboveNoiseFloor": True,  # snr_low = not isSnrAboveNoiseFloor (confirmado contra antena real)
        "alignmentStats": {
            "tiltAngleDeg": 2.1,
            "boresightAzimuthDeg": -175.7,  # rango firmado -180..180, confirmado 12/08/2026
            "boresightElevationDeg": 51.7,
            "desiredBoresightAzimuthDeg": -176.0,
            "desiredBoresightElevationDeg": 52.0,
            "attitudeUncertaintyDeg": 0.3,
        },
    }
}

# dishGetDiagnostics.alerts usa serialización dispersa (proto3): solo
# aparecen las claves en `true` -- confirmado contra la antena real
# (`alerts: {}` cuando no hay ningún alerta activo, 20/08/2026).
DIAGNOSTICS_NO_OBSTRUCCION = {"dishGetDiagnostics": {"alerts": {}}}
DIAGNOSTICS_OBSTRUIDA = {"dishGetDiagnostics": {"alerts": {"obstructed": True}}}

HISTORY_FIXTURE = {
    "dishGetHistory": {
        "popPingLatencyMs": [20.1, 22.3, 25.6, 19.8],
        "popPingDropRate": [0.0, 0.0, 0.01, 0.0],
        "outages": [
            {"cause": "OUTAGE_CAUSE_NO_PINGS", "startTimestampNs": "1000000000",
             "durationNs": "900000000", "didSwitch": True},
            {"cause": "OUTAGE_CAUSE_NO_PINGS", "startTimestampNs": "500000000",
             "durationNs": "400000000", "didSwitch": False},
        ],
    }
}


# ---------------------------------------------------------------------------
# map_status
# ---------------------------------------------------------------------------

def test_map_status_campos_directos():
    m = map_status(STATUS_FIXTURE, DIAGNOSTICS_NO_OBSTRUCCION)
    assert m["latency_ms"] == 24.5
    assert m["throughput_down_bps"] == 668000.0
    assert m["throughput_up_bps"] == 173000.0
    assert m["snr_low"] is False
    assert m["is_obstructed"] is False
    assert m["tilt_angle_deg"] == 2.1
    assert m["boresight_azimuth_deg"] == -175.7
    assert m["desired_boresight_azimuth_deg"] == -176.0


def test_map_status_snr_low_es_el_inverso_de_snr_above_noise_floor():
    """ADR-17 asumía isSnrPersistentlyLow; el firmware real solo tiene
    isSnrAboveNoiseFloor (semántica invertida) -- confirmado 12/08/2026."""
    fixture = {"dishGetStatus": {"isSnrAboveNoiseFloor": False}}
    assert map_status(fixture)["snr_low"] is True


def test_map_status_is_obstructed_true_con_alert_activo():
    """dishGetDiagnostics.alerts.obstructed=True es la única señal de estado
    *actual* de obstrucción (corregido 20/08/2026, ver docstring del
    módulo) -- distinto de obstructionStats.fractionObstructed, que es
    acumulado y ya no se usa para esto."""
    assert map_status(STATUS_FIXTURE, DIAGNOSTICS_OBSTRUIDA)["is_obstructed"] is True


def test_map_status_is_obstructed_false_cuando_alerts_no_tiene_la_clave():
    """Serialización dispersa: alerts={} (sin ningún alerta activo) significa
    is_obstructed=False, no None -- el objeto diagnostics sí llegó."""
    assert map_status(STATUS_FIXTURE, DIAGNOSTICS_NO_OBSTRUCCION)["is_obstructed"] is False


def test_map_status_is_obstructed_none_sin_diagnostics():
    """Sin diagnostics (llamada a get_diagnostics falló ese ciclo), no se
    inventa un valor -- None, no el proxy viejo de fractionObstructed."""
    assert map_status(STATUS_FIXTURE)["is_obstructed"] is None
    assert map_status({"dishGetStatus": {}})["is_obstructed"] is None


def test_map_status_satellite_count_siempre_none():
    """Confirmado ausente en get_status Y get_diagnostics en este
    hardware/firmware (dos corridas independientes) -- no depender de él."""
    assert map_status(STATUS_FIXTURE)["satellite_count"] is None


def test_map_status_dict_vacio_no_lanza():
    m = map_status({})
    assert m["latency_ms"] is None
    assert m["is_obstructed"] is None
    assert m["satellite_count"] is None


# ---------------------------------------------------------------------------
# derive_jitter_loss
# ---------------------------------------------------------------------------

def test_derive_jitter_loss_con_datos():
    jitter_ms, packet_loss_pct = derive_jitter_loss(HISTORY_FIXTURE)
    assert jitter_ms is not None and jitter_ms > 0
    assert packet_loss_pct == pytest.approx(0.25, abs=0.01)  # mean([0,0,0.01,0])*100


def test_derive_jitter_loss_historial_vacio_devuelve_none():
    assert derive_jitter_loss({}) == (None, None)
    assert derive_jitter_loss({"dishGetHistory": {}}) == (None, None)


def test_derive_jitter_loss_una_sola_muestra_no_alcanza_para_stdev():
    history = {"dishGetHistory": {"popPingLatencyMs": [20.0], "popPingDropRate": []}}
    jitter_ms, packet_loss_pct = derive_jitter_loss(history)
    assert jitter_ms is None
    assert packet_loss_pct is None


# ---------------------------------------------------------------------------
# count_handovers (ADR-16)
# ---------------------------------------------------------------------------

def test_count_handovers_desde_cero_cuenta_todo_el_historial():
    count, duration_ms = count_handovers(HISTORY_FIXTURE, since_ns=0)
    assert count == 1  # solo el outage con didSwitch=true
    assert duration_ms == pytest.approx(900.0)


def test_count_handovers_filtra_por_timestamp_del_ultimo_poll():
    count, duration_ms = count_handovers(HISTORY_FIXTURE, since_ns=2_000_000_000)
    assert count == 0
    assert duration_ms == 0.0


def test_count_handovers_ignora_outages_sin_didswitch():
    history = {"dishGetHistory": {"outages": [
        {"startTimestampNs": "100", "durationNs": "500000000", "didSwitch": False},
    ]}}
    count, duration_ms = count_handovers(history, since_ns=0)
    assert count == 0
    assert duration_ms == 0.0


def test_count_handovers_historial_vacio():
    assert count_handovers({}, since_ns=0) == (0, 0.0)


# ---------------------------------------------------------------------------
# build_metrics -- combinación completa, forma StarlinkMetrics-compatible
# ---------------------------------------------------------------------------

def test_build_metrics_tiene_las_claves_esperadas():
    metrics = build_metrics(STATUS_FIXTURE, HISTORY_FIXTURE, since_ns=0, diagnostics=DIAGNOSTICS_NO_OBSTRUCCION)
    assert set(metrics.keys()) == {
        "latency_ms", "jitter_ms", "packet_loss_pct", "throughput_down_bps",
        "throughput_up_bps", "snr_low", "is_obstructed", "satellite_count",
        "handover_count", "outage_duration_ms", "tilt_angle_deg",
        "boresight_azimuth_deg", "boresight_elevation_deg",
        "desired_boresight_azimuth_deg", "desired_boresight_elevation_deg",
        "attitude_uncertainty_deg",
    }
    assert metrics["handover_count"] == 1
    assert metrics["is_obstructed"] is False


def test_build_metrics_sin_diagnostics_deja_is_obstructed_en_none():
    """`diagnostics` es opcional (default None) -- no rompe callers viejos."""
    metrics = build_metrics(STATUS_FIXTURE, HISTORY_FIXTURE, since_ns=0)
    assert metrics["is_obstructed"] is None


def test_build_metrics_pasa_la_validacion_pydantic():
    """El mapeo real tiene que producir algo aceptable por StarlinkPayloadIn
    -- es la garantía concreta de equivalencia mock<->real de ADR-01."""
    from datetime import datetime, timezone

    from mock_starlink.schema import SCHEMA_VERSION, StarlinkPayloadIn

    metrics = build_metrics(STATUS_FIXTURE, HISTORY_FIXTURE, since_ns=0, diagnostics=DIAGNOSTICS_NO_OBSTRUCCION)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "node_id": "lit-cordoba-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }
    StarlinkPayloadIn.model_validate(payload)  # no debería lanzar


# ---------------------------------------------------------------------------
# grpc_client -- subprocess mockeado, sin ejecutar grpcurl real
# ---------------------------------------------------------------------------

class _FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_get_status_parsea_stdout_json(monkeypatch):
    import json as json_mod

    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **k: _FakeCompletedProcess(returncode=0, stdout=json_mod.dumps(STATUS_FIXTURE)),
    )
    assert get_status("192.168.100.1:9200") == STATUS_FIXTURE


def test_get_status_rc_distinto_de_cero_lanza_grpc_client_error(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **k: _FakeCompletedProcess(returncode=1, stderr="connection refused"),
    )
    with pytest.raises(GrpcClientError, match="connection refused"):
        get_status("192.168.100.1:9200")


def test_get_status_grpcurl_ausente_lanza_grpc_client_error(monkeypatch):
    def _raise(*a, **k):
        raise FileNotFoundError("grpcurl")
    monkeypatch.setattr(subprocess, "run", _raise)
    with pytest.raises(GrpcClientError, match="grpcurl no está instalado"):
        get_status("192.168.100.1:9200")


def test_get_status_timeout_lanza_grpc_client_error(monkeypatch):
    def _raise(*a, **k):
        raise subprocess.TimeoutExpired(cmd="grpcurl", timeout=5)
    monkeypatch.setattr(subprocess, "run", _raise)
    with pytest.raises(GrpcClientError, match="timeout"):
        get_status("192.168.100.1:9200")


def test_get_status_json_invalido_lanza_grpc_client_error(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **k: _FakeCompletedProcess(returncode=0, stdout="esto no es json"),
    )
    with pytest.raises(GrpcClientError, match="JSON válido"):
        get_status("192.168.100.1:9200")


def test_get_diagnostics_parsea_stdout_json_y_pide_el_request_correcto(monkeypatch):
    import json as json_mod

    captured = {}

    def _fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _FakeCompletedProcess(returncode=0, stdout=json_mod.dumps(DIAGNOSTICS_OBSTRUIDA))

    monkeypatch.setattr(subprocess, "run", _fake_run)
    assert get_diagnostics("192.168.100.1:9200") == DIAGNOSTICS_OBSTRUIDA
    assert '{"get_diagnostics": {}}' in captured["cmd"]
