"""
Módulo Starlink — adquisición y validación de telemetría de red satelital
para la estación de medición del Proyecto Integrador.

Ver docs/ADR-01 para la definición del esquema de datos.
"""

from .schema import StarlinkMetrics, StarlinkPayloadIn, SCHEMA_VERSION
from .mock import StarlinkMockAgent, CHAOS_PROFILES

__all__ = [
    "StarlinkMetrics",
    "StarlinkPayloadIn",
    "SCHEMA_VERSION",
    "StarlinkMockAgent",
    "CHAOS_PROFILES",
]