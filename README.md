# starlink-measurement-station
Módulo de adquisición de telemetría de red Starlink (latencia, jitter, throughput, obstrucción) para una estación de medición integrada a un testbed internacional de redes LEO. Python · gRPC (Dishy) · Pydantic · MQTT (Mosquitto) · TimescaleDB · FastAPI · Grafana · Docker. Corre sobre Raspberry Pi 5. Proyecto Integrador, LIT — FCEFyN/UNC.

## Estado actual

En desarrollo. Semanas 1 a 5 cerradas (parte individual — ver `docs/PROGRESS.md` para
el detalle y lo pendiente de coordinar con Fede): esquema de datos (ADR-01) y
validador Pydantic alineado al DER (`network_metrics`), broker MQTT (Mosquitto), mock
stateful con random walk + inyección de caos (ADR-06) publicando al broker con
`TIME_WARP_FACTOR` (ADR-08), empaquetado como microservicio Docker (ADR-07). Suite de
tests (67/67), skill de control de consistencia ADR/DER/SRS/API (`adr-check`) activa.

## Broker MQTT (Mosquitto)

```bash
cp .env.example .env   # ajustar si hace falta
docker compose up -d
```

Levanta Mosquitto v5.0 (`eclipse-mosquitto:2.0.18`, ver ADR-09) en `localhost:1883`,
sin autenticación (broker no expuesto fuera de la red local/Docker, ver ADR-14). Config
en `services/broker/mosquitto.conf`.

## Mock Starlink

```bash
docker compose --profile mocks up -d --build
```

Levanta el broker y el mock (`mock_starlink`, ADR-06/07), que publica cada
`60/TIME_WARP_FACTOR` segundos en `starlink/metrics/<node_id>` y anuncia su estado
(online/offline, LWT) en `system/status/<node_id>`. Variables (`.env`):

| Variable | Default | Descripción |
|---|---|---|
| `STARLINK_NODE_ID` | `lit-cordoba-01` | `node_id` del payload |
| `CHAOS_PROFILE` | `CALM` | `CALM` / `STORM` / `HANDOVER_HEAVY` (ADR-06) |
| `TIME_WARP_FACTOR` | `1` | Acelera la cadencia de publicación para backfill (ADR-08). `1` = 1 msg/60s en tiempo real; valores más altos generan historia sintética más rápido (ver `docs/08_Plan_QA.md` §Stress test para ejemplos: `60`, `600`, `3600`). |

Para correrlo fuera de Docker (contra un broker ya levantado):

```bash
PYTHONPATH=src MQTT_HOST=localhost python -m mock_starlink
```

Verificar mensajes con `mosquitto_sub`:

```bash
mosquitto_sub -h localhost -t 'starlink/metrics/#' -v
mosquitto_sub -h localhost -t 'system/status/#' -v
```

## Estructura

```
src/mock_starlink/    # Paquete principal: esquema, mock stateful, entrypoint MQTT
tests/                # Suite de tests
Dockerfile            # Empaquetado del mock_starlink (ADR-07)
docker-compose.yml    # Broker + mock_starlink
services/broker/      # Config de Mosquitto
```

## Requisitos

- **Python 3.11** (ADR-05: versión pinneada para toda la capa RPi5). El entorno de
  producción/CI y el contenedor Docker (ADR-12) corren sobre 3.11; en una máquina de
  desarrollo que no tenga 3.11 instalado, 3.13 también funciona hoy (la suite de tests
  no usa nada específico de una versión), pero no reemplaza la validación real en el
  entorno pinneado antes de integrar con hardware o con el resto de la pila.

## Instalación

```bash
git clone <url-del-repo>
cd starlink-measurement-station
python3.11 -m venv .venv   # o python3 -m venv .venv si no tenés 3.11 instalado
source .venv/bin/activate
pip install -r requirements.txt
```

## Tests

Correr toda la suite (UT-01 esquema, UT-04 mock stateful):

```bash
PYTHONPATH=src pytest tests/ -v
```

Con reporte de cobertura:

```bash
PYTHONPATH=src pytest tests/ --cov=src/mock_starlink --cov-report=term-missing
```
