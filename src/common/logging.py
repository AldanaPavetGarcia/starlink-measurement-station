"""
Logging estructurado (JSON) compartido por todos los servicios de la capa
RPi5 (CLAUDE.md §11: "logging estructurado en extractor, consumer y
backend"). Un formatter mínimo sin dependencias nuevas -- una línea JSON por
log, pensada para agregarse fácil con `docker logs` / futura integración con
un colector externo (Loki, etc.) sin cambiar el código de logging.
"""

import json
import logging
import sys

# Claves de `extra={...}` que se promueven al JSON de salida si están
# presentes en el LogRecord. Común a mock_starlink/consumer/backend/
# acquisition -- cada servicio pasa las que le apliquen vía `extra=`.
_PROMOTED_KEYS = ("node_id", "topic", "rc")


class JsonLogFormatter(logging.Formatter):
    """Formatter mínimo sin dependencias nuevas: una línea JSON por log."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }
        for key in _PROMOTED_KEYS:
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload)


def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """Logger nombrado (`name` = nombre del servicio: 'mock_starlink',
    'consumer', 'backend', 'acquisition') con salida JSON a stdout. Se llama
    una sola vez por proceso, en el entrypoint (`__main__.py`/`main.py`)."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
    return logger
