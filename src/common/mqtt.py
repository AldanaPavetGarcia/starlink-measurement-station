"""
Reconexión automática al broker MQTT, compartida entre productores
(mock_starlink, futuro acquisition real) y el consumer -- CLAUDE.md §1.1
"Semanas 15-16": "sumar manejo de caídas del broker (reconexión automática)
en tu script extractor" ya no hay que reimplementarlo, se hereda de acá.

Backoff exponencial con techo (1s -> 30s), igual en ambos lados -- la única
diferencia real entre mock_starlink y consumer era la sesión persistente
(`clean_start=False` + `Properties`, ADR-09), que ahora se pasa como
`**connect_kwargs` en vez de duplicar la función completa.
"""

import logging
import time

import paho.mqtt.client as mqtt


def connect_with_retry(
    client: mqtt.Client,
    host: str,
    port: int,
    logger: logging.Logger,
    **connect_kwargs,
) -> None:
    """Bloquea reintentando `client.connect(host, port, keepalive=60,
    **connect_kwargs)` con backoff exponencial (1s -> 30s) hasta conectar.
    `connect_kwargs` permite pasar `clean_start`/`properties` (sesión
    persistente del consumer, ADR-09) sin que el mock los necesite."""
    delay = 1.0
    while True:
        try:
            client.connect(host, port, keepalive=60, **connect_kwargs)
            return
        except OSError as exc:
            logger.warning(
                "no se pudo conectar al broker, reintentando",
                extra={"rc": str(exc)},
            )
            time.sleep(delay)
            delay = min(delay * 2, 30.0)
