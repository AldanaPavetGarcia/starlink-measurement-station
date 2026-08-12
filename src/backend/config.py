"""
Configuración del backend, siempre desde variables de entorno (ADR-12,
CLAUDE.md §11: "config de conexión siempre en .env, nunca hardcodeada").
"""

import os

VERSION = "1.0.0"  # versión del backend (docs/07_API_REST.md §3.1) -- distinta
# de SCHEMA_VERSION del payload MQTT (mock_starlink.schema), no confundir.

API_KEY = os.environ.get("BACKEND_API_KEY", "")
ENABLE_INGEST_ENDPOINT = os.environ.get("ENABLE_INGEST_ENDPOINT", "false").lower() == "true"

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

STARLINK_DB_HOST = os.environ.get("STARLINK_DB_HOST", "localhost")
STARLINK_DB_PORT = os.environ.get("STARLINK_DB_PORT", "5432")
STARLINK_DB_NAME = os.environ.get("STARLINK_DB_NAME", "starlink_health")
STARLINK_DB_USER = os.environ.get("STARLINK_DB_USER", "starlink_app")
STARLINK_DB_PASSWORD = os.environ.get("STARLINK_DB_PASSWORD", "")

STATION_CONFIG_DB_HOST = os.environ.get("STATION_CONFIG_DB_HOST", "localhost")
STATION_CONFIG_DB_PORT = os.environ.get("STATION_CONFIG_DB_PORT", "5432")
STATION_CONFIG_DB_NAME = os.environ.get("STATION_CONFIG_DB_NAME", "station_config")
STATION_CONFIG_DB_USER = os.environ.get("STATION_CONFIG_DB_USER", "station_config_app")
STATION_CONFIG_DB_PASSWORD = os.environ.get("STATION_CONFIG_DB_PASSWORD", "")

# Semana 9 (backend): raw < 6h, hourly < 30d, daily >= 30d -- ver
# docs/07_API_REST.md "Lógica de selección automática de Continuous Aggregate".
AUTO_RESOLUTION_RAW_MAX_HOURS = 6
AUTO_RESOLUTION_HOURLY_MAX_DAYS = 30
