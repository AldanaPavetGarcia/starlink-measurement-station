"""
Mapeo gRPC (protobuf-JSON vía grpcurl) -> campos de StarlinkMetrics (ADR-01).
Funciones puras (dict de entrada, dict/tupla de salida), sin tocar red --
testeables sin la antena real, contra JSON sintético.

Validado campo a campo contra la antena real en el LIT el 12/08/2026 (sesión
presencial, `grpcurl` vía SSH a la RPi5 -- ver `docs/PROGRESS.md` §Semana 10).
El relevamiento previo del 04/08 asumía `isSnrPersistentlyLow` y
`obstructionStats.currentlyObstructed`; ninguno de los dos existe en este
firmware (`softwareVersion: 2026.07.27.mr83192.1`) -- corregido acá para
`snr_low` e `is_obstructed`. `boresightAzimuthDeg`/`desiredBoresightAzimuthDeg`
vinieron en rango firmado (-180..180, ej. -179.99922), no en la convención de
brújula 0-360 asumida originalmente -- corregido en `schema.py` (ADR-18,
rango ahora -180..180) tras confirmar contra la antena real.

Mapeo confirmado contra la antena real:
- latency_ms          <- dishGetStatus.popPingLatencyMs (directo)
- throughput_down_bps  <- dishGetStatus.downlinkThroughputBps (directo)
- throughput_up_bps    <- dishGetStatus.uplinkThroughputBps (directo)
- is_obstructed        <- **corregido 20/08/2026** (bug real encontrado en
                           visita al LIT): `dishGetDiagnostics.alerts.obstructed`
                           -- el único flag de estado *actual*. La versión
                           anterior usaba `obstructionStats.fractionObstructed
                           > 0` de `get_status`, pero ese campo es una
                           fracción ACUMULADA desde que arrancó la ventana de
                           validación (`validS`, horas/días de uptime), no el
                           estado ahora mismo -- con umbral `>0` daba
                           `is_obstructed=True` casi siempre una vez que hubo
                           cualquier obstrucción alguna vez (medido: 8358 de
                           8359 muestras reales en 6 días, con
                           `fractionObstructed` de apenas 0.04% acumulado --
                           no era obstrucción real, era el proxy equivocado).
                           `alerts` usa serialización JSON dispersa (proto3,
                           confirmado contra la antena real): solo aparecen
                           las claves en `true`, así que la ausencia de
                           `"obstructed"` en el dict significa `false`, no
                           "sin dato" -- salvo que falte el objeto
                           `dishGetDiagnostics` entero (llamada no
                           disponible), ahí no hay señal confiable y se
                           devuelve `None`. **Sin verificar todavía contra un
                           evento de obstrucción real** (la antena no tuvo
                           ninguno durante la visita) -- confirmar la próxima
                           vez que haya nubes bajas/algo bloqueando la vista.
- satellite_count      <- siempre None (confirmado ausente en get_status Y
                           get_diagnostics en este hardware/firmware, dos
                           corridas independientes -- no es un bug del mapeo)
- snr_low (ADR-17)     <- `not dishGetStatus.isSnrAboveNoiseFloor` (el campo
                           real es el inverso semántico de lo que asumía
                           ADR-17; `isSnrPersistentlyLow` no existe)
- alignmentStats (ADR-18) <- dishGetStatus.alignmentStats.* (directo, pero
  ver advertencia de rango de azimuth arriba)
- jitter_ms/packet_loss_pct <- derivados de dishGetHistory (stdev de
  popPingLatencyMs y promedio de popPingDropRate*100 respectivamente,
  confirmados presentes y con esa forma en la antena real)
- handover_count/outage_duration_ms (ADR-16) <- dishGetHistory.outages[]
  filtrados por startTimestampNs posterior al último poll y didSwitch=true
  (estructura confirmada contra la antena real)
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


def _obstructed_from_diagnostics(diagnostics: Optional[dict]) -> Optional[bool]:
    """Ver la nota de `is_obstructed` en el docstring del módulo. `None` si
    no se pudo llamar a `get_diagnostics` en este ciclo (antena no
    disponible momentáneamente) -- no se inventa un valor."""
    if diagnostics is None:
        return None
    alerts = (diagnostics.get("dishGetDiagnostics", {}) or {}).get("alerts", {}) or {}
    return bool(alerts.get("obstructed", False))


def map_status(status: dict, diagnostics: Optional[dict] = None) -> dict:
    """Campos derivables directamente de `get_status` + `get_diagnostics`
    (sin estado entre polls). `diagnostics` es opcional para no romper
    callers/tests que sólo tienen `get_status` -- sin él, `is_obstructed`
    queda en `None` en vez de inventar un valor con el proxy viejo."""
    s = status.get("dishGetStatus", {}) or {}
    alignment = s.get("alignmentStats", {}) or {}

    snr_above_floor = s.get("isSnrAboveNoiseFloor")

    return {
        "latency_ms": _num(s.get("popPingLatencyMs")),
        "throughput_down_bps": _num(s.get("downlinkThroughputBps")),
        "throughput_up_bps": _num(s.get("uplinkThroughputBps")),
        "is_obstructed": _obstructed_from_diagnostics(diagnostics),
        "satellite_count": None,
        "snr_low": (not snr_above_floor) if snr_above_floor is not None else None,
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


def build_metrics(status: dict, history: dict, since_ns: int, diagnostics: Optional[dict] = None) -> dict:
    """Combina las cuatro fuentes en un único dict, con la misma forma que
    `StarlinkMetrics` (schema.py) espera en `metrics`. `diagnostics` es
    opcional (ver `map_status`)."""
    metrics = map_status(status, diagnostics)
    jitter_ms, packet_loss_pct = derive_jitter_loss(history)
    handover_count, outage_duration_ms = count_handovers(history, since_ns)

    metrics["jitter_ms"] = jitter_ms
    metrics["packet_loss_pct"] = packet_loss_pct
    metrics["handover_count"] = handover_count
    metrics["outage_duration_ms"] = outage_duration_ms
    return metrics
