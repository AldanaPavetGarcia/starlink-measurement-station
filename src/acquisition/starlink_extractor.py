"""
Mapeo gRPC (protobuf-JSON vía grpcurl) -> campos de StarlinkMetrics (ADR-01).
Funciones puras (dict de entrada, dict/tupla de salida), sin tocar red --
testeables sin la antena real, contra JSON sintético que imita la estructura
documentada en el relevamiento del 04/08/2026 (`docs/PROGRESS.md` §Semana 10).

⚠️ Sin acceso presencial a la RPi5/antena en esta sesión, este mapeo no se
validó contra los JSON crudos reales (`~/starlink-relevamiento/*.json` en la
RPi5) -- solo contra la estructura y nombres de campo tal como quedaron
documentados a mano en el relevamiento. Confirmar campo a campo en la
próxima visita al LIT antes de dar por cerrado el extractor (`__main__.py`
ya deja este módulo aislado justo para que ese chequeo sea rápido: correr
`map_status`/`derive_jitter_loss`/`count_handovers` contra los JSON reales
guardados y comparar a mano).

Mapeo confirmado en el relevamiento:
- latency_ms          <- dishGetStatus.popPingLatencyMs (directo)
- throughput_down_bps  <- dishGetStatus.downlinkThroughputBps (directo)
- throughput_up_bps    <- dishGetStatus.uplinkThroughputBps (directo)
- is_obstructed        <- dishGetStatus.obstructionStats.currentlyObstructed
- satellite_count      <- siempre None (confirmado ausente en get_status Y
                           get_diagnostics en este hardware/firmware, dos
                           corridas independientes -- no es un bug del mapeo)
- snr_low (ADR-17)     <- dishGetStatus.isSnrPersistentlyLow
- alignmentStats (ADR-18) <- dishGetStatus.alignmentStats.* (directo)
- jitter_ms/packet_loss_pct <- derivados de dishGetHistory (no son campos
  nativos del gRPC, confirmado derivables pero la fórmula exacta no se
  validó contra datos reales, ver advertencia arriba)
- handover_count/outage_duration_ms (ADR-16) <- dishGetHistory.outages[]
  filtrados por startTimestampNs posterior al último poll y didSwitch=true
"""

from __future__ import annotations

import statistics
from typing import Any, Optional


def _num(value: Any) -> Optional[float]:
    """Protobuf-JSON serializa int64 como string (para no perder precisión
    en JS) -- normaliza str/int/float/None a float."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def map_status(status: dict) -> dict:
    """Campos derivables directamente de un único `get_status` (sin estado
    entre polls)."""
    s = status.get("dishGetStatus", {}) or {}
    obstruction = s.get("obstructionStats", {}) or {}
    alignment = s.get("alignmentStats", {}) or {}

    return {
        "latency_ms": _num(s.get("popPingLatencyMs")),
        "throughput_down_bps": _num(s.get("downlinkThroughputBps")),
        "throughput_up_bps": _num(s.get("uplinkThroughputBps")),
        "is_obstructed": obstruction.get("currentlyObstructed"),
        "satellite_count": None,
        "snr_low": s.get("isSnrPersistentlyLow"),
        "tilt_angle_deg": _num(alignment.get("tiltAngleDeg")),
        "boresight_azimuth_deg": _num(alignment.get("boresightAzimuthDeg")),
        "boresight_elevation_deg": _num(alignment.get("boresightElevationDeg")),
        "desired_boresight_azimuth_deg": _num(alignment.get("desiredBoresightAzimuthDeg")),
        "desired_boresight_elevation_deg": _num(alignment.get("desiredBoresightElevationDeg")),
        "attitude_uncertainty_deg": _num(alignment.get("attitudeUncertaintyDeg")),
    }


def derive_jitter_loss(history: dict) -> tuple[Optional[float], Optional[float]]:
    """jitter_ms: desviación estándar de la serie de latencias de
    `popPingLatencyMs` (variación entre muestras consecutivas, como describe
    el docstring de schema.py). packet_loss_pct: promedio de
    `popPingDropRate` (fracción 0-1 por muestra, se asume) convertido a
    porcentaje. Ambos None si la serie viene vacía (sin datos suficientes
    para derivar, no se inventa un 0)."""
    h = history.get("dishGetHistory", {}) or {}

    latencies = [v for v in (_num(x) for x in (h.get("popPingLatencyMs") or [])) if v is not None]
    jitter_ms = round(statistics.stdev(latencies), 2) if len(latencies) >= 2 else None

    drop_rates = [v for v in (_num(x) for x in (h.get("popPingDropRate") or [])) if v is not None]
    packet_loss_pct = round(100.0 * statistics.mean(drop_rates), 2) if drop_rates else None

    return jitter_ms, packet_loss_pct


def count_handovers(history: dict, since_ns: int) -> tuple[int, float]:
    """ADR-16: cuenta los `outages` con `didSwitch=true` cuyo
    `startTimestampNs` es posterior al timestamp del poll anterior, y suma
    su `durationNs` en milisegundos. `since_ns=0` (primer poll del proceso,
    sin estado previo) cuenta todo el historial disponible -- aceptable
    porque es un único pico inicial, no se repite en polls siguientes."""
    h = history.get("dishGetHistory", {}) or {}
    outages = h.get("outages") or []

    count = 0
    total_duration_ns = 0
    for outage in outages:
        start_ns = int(_num(outage.get("startTimestampNs")) or 0)
        if start_ns <= since_ns:
            continue
        if not outage.get("didSwitch"):
            continue
        count += 1
        total_duration_ns += int(_num(outage.get("durationNs")) or 0)

    return count, round(total_duration_ns / 1_000_000, 2)


def build_metrics(status: dict, history: dict, since_ns: int) -> dict:
    """Combina las tres fuentes en un único dict, con la misma forma que
    `StarlinkMetrics` (schema.py) espera en `metrics`."""
    metrics = map_status(status)
    jitter_ms, packet_loss_pct = derive_jitter_loss(history)
    handover_count, outage_duration_ms = count_handovers(history, since_ns)

    metrics["jitter_ms"] = jitter_ms
    metrics["packet_loss_pct"] = packet_loss_pct
    metrics["handover_count"] = handover_count
    metrics["outage_duration_ms"] = outage_duration_ms
    return metrics
