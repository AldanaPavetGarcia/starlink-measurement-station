"""
Utilidades compartidas entre servicios de la capa RPi5 (mock_starlink,
consumer, backend, acquisition -- CLAUDE.md §1.1, semana 9).

Extraído de src/mock_starlink/__main__.py (semana 3-4) cuando el consumer
duplicó el mismo JsonLogFormatter/_setup_logging/_connect_with_retry sin
ninguna diferencia real -- ver docs/PROGRESS.md. No depende de mock_starlink
ni de consumer en ningún sentido, para no crear un acoplamiento circular.
"""

from .logging import JsonLogFormatter, setup_logging
from .mqtt import connect_with_retry

__all__ = ["JsonLogFormatter", "setup_logging", "connect_with_retry"]
