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
import os
import time

import paho.mqtt.client as mqtt


def set_credentials_if_present(client: mqtt.Client) -> bool:
    """El broker local (ADR-04/ADR-14) es `allow_anonymous true` -- nunca
    hizo falta esto hasta el bridge a la VM de cátedra (ADR-20), que sí
    exige credenciales. `MQTT_USERNAME`/`MQTT_PASSWORD` quedan sin default:
    si no están las dos, no se llama `username_pw_set` y el cliente conecta
    anónimo como siempre (no rompe el caso local). Devuelve si las aplicó,
    solo para logging del caller."""
    username = os.environ.get("MQTT_USERNAME")
    password = os.environ.get("MQTT_PASSWORD")
    if username and password:
        client.username_pw_set(username, password)
        return True
    return False


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
