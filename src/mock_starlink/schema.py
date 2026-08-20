"""
Esquema y validador Pydantic del paquete de telemetría Starlink (ADR-01).

Corresponde a la definición final documentada en el informe de relevamiento:
- schema_version, node_id, timestamp como metadatos.
- metrics como objeto anidado con las métricas de red.
- packet_loss_pct y jitter_ms se calculan en el extractor (no son campos
  nativos del gRPC), pero acá solo se valida el paquete ya construido.
- Todos los campos de métricas salvo node_id/timestamp/schema_version son
  opcionales (Optional, default None), reflejando docs/06_DER.md
  (network_metrics, columna NULL='S'): la medición puede fallar (ping sin
  respuesta, API interna de la antena no accesible) sin que el paquete
  completo se descarte — se propaga con esos campos en null en vez de
  romper la ingesta.
- satellite_count además no está garantizado en todo el hardware ni
  referenciado por ningún requerimiento del SRS.
- No existe campo `source` (mock/real): decisión de alcance, el mock es
  solo una herramienta de desarrollo que no convive con datos reales.

schema_version 1.1 (ADR-16/17/18, agosto 2026, relevamiento contra hardware
real en el LIT):
- `snr_db` (float) reemplazado por `snr_low` (bool, ADR-17) — el firmware
  real (apiVersion 42) no expone SNR numérico, solo `isSnrAboveNoiseFloor`
  (confirmado en campo el 12/08/2026; `isSnrPersistentlyLow`, asumido en el
  relevamiento del 04/08, no existe). `snr_low = not isSnrAboveNoiseFloor`.
  Cambio de tipo incompatible con 1.0, por eso `check_schema_version`
  rechaza explícitamente la versión vieja.
- `handover_count`/`outage_duration_ms` agregados (ADR-16), derivados de
  `get_history.dishGetHistory.outages[].didSwitch` real.
- Campos de `alignmentStats` agregados (ADR-18, pedido del director):
  `tilt_angle_deg`, `boresight_azimuth_deg`, `boresight_elevation_deg`,
  `desired_boresight_azimuth_deg`, `desired_boresight_elevation_deg`,
  `attitude_uncertainty_deg`. Los dos campos de azimuth usan rango firmado
  (-180..180, no brújula 0-360) — corregido el 12/08/2026 tras confirmar
  contra la antena real que el firmware devuelve valores como -179.99922;
  la convención 0-360 asumida originalmente en ADR-18 nunca se validó
  contra hardware y quedaba falsa en la práctica.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

SCHEMA_VERSION = "1.1"


class StarlinkMetrics(BaseModel):
    """Métricas de red propiamente dichas, ya calculadas por el extractor."""

    latency_ms: Optional[float] = Field(
        default=None, ge=0, le=5000,
        description="Latencia de ping al POP (pop_ping_latency_ms), directo del gRPC. "
                    "Null si la medición falló (conectividad interrumpida, DER NULL='S')."
    )
    jitter_ms: Optional[float] = Field(
        default=None, ge=0, le=2000,
        description="Calculado en el extractor a partir de la variación entre "
                    "muestras consecutivas de get_history. No es un campo nativo del gRPC. "
                    "Null si no se pudo calcular (DER NULL='S')."
    )
    packet_loss_pct: Optional[float] = Field(
        default=None, ge=0, le=100,
        description="Derivado como total_ping_drop / samples sobre get_history. "
                    "Null si la medición falló (DER NULL='S')."
    )
    throughput_down_bps: Optional[float] = Field(
        default=None, ge=0,
        description="downlink_throughput_bps, sin convertir (bps, no Mbps). "
                    "Null si la medición falló (DER NULL='S')."
    )
    throughput_up_bps: Optional[float] = Field(
        default=None, ge=0,
        description="uplink_throughput_bps, sin convertir (bps, no Mbps). "
                    "Null si la medición falló (DER NULL='S')."
    )
    snr_low: Optional[bool] = Field(
        default=None,
        description="`not isSnrAboveNoiseFloor` del get_status real (ADR-17). "
                    "Reemplaza snr_db (float) desde schema_version 1.1 -- el "
                    "firmware real no expone SNR numérico. Null si la API interna "
                    "de la antena no está accesible (DER NULL='S')."
    )
    is_obstructed: Optional[bool] = Field(
        default=None,
        description="`dishGetDiagnostics.alerts.obstructed` del extractor real "
                    "(ADR-19, corregido 20/08/2026) -- único flag de estado "
                    "*actual*; `obstructionStats.fractionObstructed` de "
                    "`get_status` es una fracción ACUMULADA desde que arrancó la "
                    "ventana de validación, no sirve para 'ahora mismo' (se usaba "
                    "así hasta esta corrección, con umbral >0 daba True casi "
                    "siempre). Null si `get_diagnostics` no está accesible "
                    "(DER NULL='S')."
    )
    satellite_count: Optional[int] = Field(
        default=None, ge=0,
        description="Opcional: no confiable en todo el hardware ni referenciado "
                    "en el SRS. No bloquea el paquete si falta (DER NULL='S')."
    )
    handover_count: Optional[int] = Field(
        default=None, ge=0,
        description="Cantidad de eventos de handover (didSwitch=true) desde la "
                    "medición anterior (ADR-16). 0 es el valor normal; null solo "
                    "si la medición falló (get_history no accesible)."
    )
    outage_duration_ms: Optional[float] = Field(
        default=None, ge=0,
        description="Milisegundos totales de corte asociados a handover_count, "
                    "en el mismo intervalo (ADR-16). 0.0 es el valor normal; null "
                    "solo si la medición falló."
    )
    tilt_angle_deg: Optional[float] = Field(
        default=None, ge=0, le=90,
        description="alignmentStats.tiltAngleDeg (ADR-18). Null si no disponible."
    )
    boresight_azimuth_deg: Optional[float] = Field(
        default=None, ge=-180, le=180,
        description="alignmentStats.boresightAzimuthDeg, apuntamiento real (ADR-18). "
                    "Rango firmado (-180..180), confirmado contra la antena real el "
                    "12/08/2026 -- la convención de brújula 0-360 asumida originalmente "
                    "nunca se validó contra hardware y era incorrecta. Null si no "
                    "disponible."
    )
    boresight_elevation_deg: Optional[float] = Field(
        default=None, ge=0, le=90,
        description="alignmentStats.boresightElevationDeg, apuntamiento real "
                    "(ADR-18). Null si no disponible."
    )
    desired_boresight_azimuth_deg: Optional[float] = Field(
        default=None, ge=-180, le=180,
        description="alignmentStats.desiredBoresightAzimuthDeg, apuntamiento "
                    "objetivo (ADR-18). Rango firmado (-180..180), ver "
                    "boresight_azimuth_deg. Null si no disponible."
    )
    desired_boresight_elevation_deg: Optional[float] = Field(
        default=None, ge=0, le=90,
        description="alignmentStats.desiredBoresightElevationDeg, apuntamiento "
                    "objetivo (ADR-18). Null si no disponible."
    )
    attitude_uncertainty_deg: Optional[float] = Field(
        default=None, ge=0,
        description="alignmentStats.attitudeUncertaintyDeg (ADR-18). Null si no "
                    "disponible."
    )

    @field_validator(
        "latency_ms", "jitter_ms", "throughput_down_bps", "throughput_up_bps",
        "outage_duration_ms", "tilt_angle_deg", "boresight_azimuth_deg",
        "boresight_elevation_deg", "desired_boresight_azimuth_deg",
        "desired_boresight_elevation_deg", "attitude_uncertainty_deg",
    )
    @classmethod
    def reject_nan_inf(cls, v: float) -> float:
        """Rechaza NaN/Infinity, que json.dumps no serializa bien y romperían
        tanto el broker MQTT como los CHECK constraints de TimescaleDB."""
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError("el valor no puede ser NaN ni infinito")
        return v


class StarlinkPayloadIn(BaseModel):
    """Paquete completo tal como se publica en el tópico MQTT de Starlink."""

    schema_version: str = Field(..., description="Versión del esquema, ej. '1.1'.")
    node_id: str = Field(
        ..., min_length=1, max_length=64,
        pattern=r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$",
        description="Debe coincidir con station_metadata.node_id (DER)."
    )
    timestamp: datetime = Field(
        ..., description="Generado en el cliente (extractor), no en la DB."
    )
    metrics: StarlinkMetrics

    @field_validator("schema_version")
    @classmethod
    def check_schema_version(cls, v: str) -> str:
        if v != SCHEMA_VERSION:
            raise ValueError(f"schema_version no soportada: {v!r} (esperada {SCHEMA_VERSION!r})")
        return v

    @field_validator("timestamp")
    @classmethod
    def check_timestamp_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp debe incluir información de zona horaria (UTC)")
        return v.astimezone(timezone.utc)

    @model_validator(mode="after")
    def check_timestamp_not_future(self) -> "StarlinkPayloadIn":
        """Tolera un pequeño desfasaje de reloj (ej. NTP no sincronizado),
        pero rechaza timestamps claramente inválidos."""
        skew = (self.timestamp - datetime.now(timezone.utc)).total_seconds()
        if skew > 30:
            raise ValueError(f"timestamp está {skew:.1f}s en el futuro, revisar reloj del nodo")
        return self


# ---------------------------------------------------------------------------
# Ejemplo de uso / smoke test manual
# ---------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    ejemplo_valido = {
        "schema_version": "1.1",
        "node_id": "lit-cordoba-01",
        "timestamp": "2026-07-05T14:32:10.123+00:00",
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

    payload = StarlinkPayloadIn.model_validate(ejemplo_valido)
    print("Paquete válido:")
    print(payload.model_dump_json(indent=2))

    # Caso sin satellite_count (debe seguir siendo válido, es opcional)
    ejemplo_sin_satelites = {**ejemplo_valido, "metrics": {**ejemplo_valido["metrics"]}}
    del ejemplo_sin_satelites["metrics"]["satellite_count"]
    StarlinkPayloadIn.model_validate(ejemplo_sin_satelites)
    print("\nOK: paquete sin satellite_count también es válido (campo opcional).")

    # Caso inválido: packet_loss_pct fuera de rango
    try:
        invalido = {**ejemplo_valido, "metrics": {**ejemplo_valido["metrics"], "packet_loss_pct": 150}}
        StarlinkPayloadIn.model_validate(invalido)
    except Exception as e:
        print(f"\nOK: paquete inválido correctamente rechazado -> {e}")
        