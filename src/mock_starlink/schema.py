"""
Esquema y validador Pydantic del paquete de telemetría Starlink (ADR-01).

Corresponde a la definición final documentada en el informe de relevamiento:
- schema_version, node_id, timestamp como metadatos.
- metrics como objeto anidado con las 8 métricas de red.
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
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

SCHEMA_VERSION = "1.0"


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
    snr_db: Optional[float] = Field(
        default=None, ge=-20, le=30,
        description="snr del get_status. Rango amplio para tolerar condiciones "
                    "de señal muy pobre sin rechazar el paquete. Null si la API "
                    "interna de la antena no está accesible (DER NULL='S')."
    )
    is_obstructed: Optional[bool] = Field(
        default=None,
        description="Basado en currently_obstructed. obstruction_detail se "
                    "descartó por estar deprecado en firmwares recientes. Null si "
                    "la API interna de la antena no está accesible (DER NULL='S')."
    )
    satellite_count: Optional[int] = Field(
        default=None, ge=0,
        description="Opcional: no confiable en todo el hardware ni referenciado "
                    "en el SRS. No bloquea el paquete si falta (DER NULL='S')."
    )

    @field_validator("latency_ms", "jitter_ms", "throughput_down_bps", "throughput_up_bps")
    @classmethod
    def reject_nan_inf(cls, v: float) -> float:
        """Rechaza NaN/Infinity, que json.dumps no serializa bien y romperían
        tanto el broker MQTT como los CHECK constraints de TimescaleDB."""
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError("el valor no puede ser NaN ni infinito")
        return v


class StarlinkPayloadIn(BaseModel):
    """Paquete completo tal como se publica en el tópico MQTT de Starlink."""

    schema_version: str = Field(..., description="Versión del esquema, ej. '1.0'.")
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
        "schema_version": "1.0",
        "node_id": "lit-cordoba-01",
        "timestamp": "2026-07-05T14:32:10.123+00:00",
        "metrics": {
            "latency_ms": 42.7,
            "jitter_ms": 5.3,
            "packet_loss_pct": 0.8,
            "throughput_down_bps": 185340000,
            "throughput_up_bps": 12450000,
            "snr_db": 9.2,
            "is_obstructed": False,
            "satellite_count": 14,
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
        