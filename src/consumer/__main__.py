"""
Entrypoint del consumer: se suscribe a los tópicos de datos del broker MQTT y
enruta cada mensaje a la DB que corresponda vía ConsumerRouter (`python -m
consumer`).

Cubre los requisitos de CLAUDE.md §1.1 / docs/03_SRS.md para este componente:
reconexión automática (RNF-05), sesión persistente + QoS 1 con ACK manual
(ADR-09, RF-18: un mensaje solo se ACKea si quedó persistido o el error es
permanente -- ver router.py), y logging estructurado (JSON) de errores de
conexión y de deserialización/validación sin tumbar el contenedor.
"""

import json
import os

import paho.mqtt.client as mqtt
from paho.mqtt.properties import PacketTypes, Properties

from common import connect_with_retry, setup_logging

from .db import MeteoDB, NetHealthDB
from .router import ConsumerRouter

TOPIC_STARLINK = "starlink/metrics/+"
TOPIC_METEO_SENSOR = "meteo/sensor/+"
TOPIC_METEO_EXTERNAL = "meteo/external/+"

# ADR-09: sesión persistente -- el consumer no debe perder mensajes QoS 1
# publicados mientras estaba caído. 0xFFFFFFFF = la sesión no expira (MQTTv5).
_SESSION_NEVER_EXPIRES = 0xFFFFFFFF


def main() -> None:
    logger = setup_logging("consumer")

    mqtt_host = os.environ.get("MQTT_HOST", "localhost")
    mqtt_port = int(os.environ.get("MQTT_PORT", "1883"))

    router = ConsumerRouter(net_db=NetHealthDB.from_env(), meteo_db=MeteoDB())

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="consumer-starlink-health",
        protocol=mqtt.MQTTv5,
        manual_ack=True,
    )
    client.reconnect_delay_set(min_delay=1, max_delay=60)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info("conectado al broker")
            client.subscribe(
                [(TOPIC_STARLINK, 1), (TOPIC_METEO_SENSOR, 1), (TOPIC_METEO_EXTERNAL, 1)]
            )
        else:
            logger.error("conexión rechazada por el broker", extra={"rc": str(reason_code)})

    def on_disconnect(client, userdata, flags, reason_code, properties):
        logger.warning("desconectado del broker, reconectando", extra={"rc": str(reason_code)})

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
        except json.JSONDecodeError as exc:
            logger.error(
                "mensaje MQTT con JSON inválido, descartado",
                extra={"topic": msg.topic, "rc": str(exc)},
            )
            client.ack(msg.mid, msg.qos)
            return

        should_ack = router.route_message(msg.topic, payload)
        if should_ack:
            client.ack(msg.mid, msg.qos)
        # si should_ack es False, no se ACKea: el broker reentrega el mensaje
        # QoS 1 (RF-18) cuando el consumer vuelva a conectar.

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    connect_properties = Properties(PacketTypes.CONNECT)
    connect_properties.SessionExpiryInterval = _SESSION_NEVER_EXPIRES
    connect_with_retry(
        client, mqtt_host, mqtt_port, logger,
        clean_start=False, properties=connect_properties,
    )

    logger.info("consumer arrancando", extra={"topic": TOPIC_STARLINK})
    client.loop_forever()


if __name__ == "__main__":
    main()
