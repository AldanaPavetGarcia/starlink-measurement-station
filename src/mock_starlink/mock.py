"""
Mock stateful de telemetría Starlink (ADR-06): Random Walk + inyección de caos.

Traduce el modelo estadístico de ADR-06 (definido en vocabulario del SRS:
throughput_down/up_mbps, obstruction_pct, signal_quality) al vocabulario del DER
que ya sigue `schema.py` (throughput_down/up_bps, is_obstructed, snr_db,
satellite_count) — es el mismo drift ya anotado en docs/PROGRESS.md para
SRS/DER, extendido a ADR-06. `obstruction_pct` se mantiene como estado interno
(no se publica) y se traduce a `is_obstructed` con un umbral (>10%).

ADR-06 no especifica los parámetros de CHAOS_PROFILE por perfil (solo describe
el mecanismo general de "evento de anomalía") — CHAOS_PARAMS abajo es la
calibración propuesta, ajustada para satisfacer UT-04-02 de docs/08_Plan_QA.md
("perfil STORM, >=15% de 1000 muestras con latency_ms > 150").
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from .schema import SCHEMA_VERSION

CHAOS_PROFILES = ("CALM", "STORM", "HANDOVER_HEAVY")

# (p_handover_spike, p_obstruction_start, p_outage_start) por tick simulado (60s).
CHAOS_PARAMS = {
    "CALM": (0.01, 0.0, 0.0),
    "STORM": (0.20, 0.05, 0.01),
    "HANDOVER_HEAVY": (0.15, 0.01, 0.0),
}

_LATENCY_BASELINE_MS = 35.0
_LATENCY_FLOOR_MS = 20.0  # piso físico LEO (UT-04-01)
_BACKFILL_DAYS = 30  # ej. de ADR-08: "30 días de historia"


class StarlinkMockAgent:
    """Genera payloads de telemetría Starlink con memoria entre llamadas.

    `generate_payload()` es el método puro de test (no toca reloj ni red).
    `run(publish_callback)` es el loop async que efectivamente publica,
    respetando `time_warp_factor` (ADR-08) para backfill acelerado.
    """

    def __init__(
        self,
        node_id: str,
        chaos_profile: str = "CALM",
        time_warp_factor: int = 1,
        rng: Optional[random.Random] = None,
    ) -> None:
        if chaos_profile not in CHAOS_PROFILES:
            raise ValueError(
                f"CHAOS_PROFILE inválido: {chaos_profile!r} (válidos: {CHAOS_PROFILES})"
            )
        if time_warp_factor < 1:
            raise ValueError("time_warp_factor debe ser >= 1")

        self.node_id = node_id
        self.chaos_profile = chaos_profile
        self.time_warp_factor = time_warp_factor
        self.rng = rng if rng is not None else random.Random()
        self.interval_s = 60.0 / time_warp_factor

        now = datetime.now(timezone.utc)
        self.sim_time = now - timedelta(days=_BACKFILL_DAYS) if time_warp_factor > 1 else now

        # Estado interno del random walk / máquinas de estado de caos.
        self._latency_ms = _LATENCY_BASELINE_MS
        self._obstruction_ticks_remaining = 0
        self._outage_ticks_remaining = 0

    def generate_payload(self) -> dict:
        """Un tick del mock: actualiza el estado interno y arma el payload
        completo (dict, listo para json.dumps). No avanza `sim_time` — eso lo
        hace `run()`, para que llamar esto muchas veces seguidas (tests) no
        dispare el rechazo de "timestamp en el futuro" del validador."""
        rng = self.rng
        handover_p, obstruction_start_p, outage_start_p = CHAOS_PARAMS[self.chaos_profile]

        handover_event = rng.random() < handover_p

        # --- obstrucción (evento multi-tick) ---
        if self._obstruction_ticks_remaining <= 0 and rng.random() < obstruction_start_p:
            self._obstruction_ticks_remaining = rng.randint(3, 10)
        if self._obstruction_ticks_remaining > 0:
            obstruction_pct = rng.uniform(20, 80)
            self._obstruction_ticks_remaining -= 1
        else:
            obstruction_pct = rng.uniform(0, 3)
        is_obstructed = obstruction_pct > 10.0

        # --- latencia: random walk con reversión suave a la media ---
        self._latency_ms += rng.uniform(-2.5, 3.0)
        self._latency_ms += (_LATENCY_BASELINE_MS - self._latency_ms) * 0.05
        latency_ms = rng.uniform(150, 400) if handover_event else self._latency_ms
        latency_ms = max(_LATENCY_FLOOR_MS, latency_ms)

        # --- jitter ---
        jitter_ms = rng.uniform(50, 100) if handover_event else rng.expovariate(0.5)

        # --- packet loss / outage (evento multi-tick) ---
        if self._outage_ticks_remaining <= 0 and rng.random() < outage_start_p:
            self._outage_ticks_remaining = rng.randint(2, 5)
        if self._outage_ticks_remaining > 0:
            packet_loss_pct = 100.0
            self._outage_ticks_remaining -= 1
        elif is_obstructed:
            packet_loss_pct = rng.uniform(5, 40)
        elif rng.random() < 0.005:
            packet_loss_pct = rng.uniform(0.5, 2.0)
        else:
            packet_loss_pct = 0.0

        # --- throughput (degrada durante obstrucción) ---
        down_mbps = max(0.0, rng.gauss(180, 30))
        up_mbps = max(0.0, rng.gauss(22, 5))
        if is_obstructed:
            down_mbps = min(down_mbps, rng.uniform(5, 50))
            up_mbps = min(up_mbps, rng.uniform(1, 8))

        # --- snr (degrada durante obstrucción) ---
        snr_db = rng.gauss(9, 3)
        if is_obstructed:
            snr_db -= rng.uniform(10, 20)
        snr_db = max(-20.0, min(30.0, snr_db))

        # --- satellite_count (cae durante obstrucción/handover) ---
        satellite_count = round(rng.gauss(15, 3))
        if is_obstructed or handover_event:
            satellite_count -= rng.randint(3, 8)
        satellite_count = max(0, min(30, satellite_count))

        return {
            "schema_version": SCHEMA_VERSION,
            "node_id": self.node_id,
            "timestamp": self.sim_time.isoformat(),
            "metrics": {
                "latency_ms": round(latency_ms, 2),
                "jitter_ms": round(jitter_ms, 2),
                "packet_loss_pct": round(packet_loss_pct, 2),
                "throughput_down_bps": round(down_mbps * 1_000_000),
                "throughput_up_bps": round(up_mbps * 1_000_000),
                "snr_db": round(snr_db, 2),
                "is_obstructed": is_obstructed,
                "satellite_count": satellite_count,
            },
        }

    async def run(self, publish_callback) -> None:
        """Loop infinito: genera, publica, avanza el tiempo simulado 60s y
        duerme `interval_s` segundos reales (ADR-08). `publish_callback` es
        async y recibe el dict del payload — mantiene este módulo sin
        conocimiento de MQTT (eso vive en __main__.py)."""
        while True:
            payload = self.generate_payload()
            await publish_callback(payload)

            now = datetime.now(timezone.utc)
            self.sim_time = min(self.sim_time + timedelta(seconds=60), now - timedelta(seconds=1))
            await asyncio.sleep(self.interval_s)
