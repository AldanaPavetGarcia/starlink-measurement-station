# starlink-measurement-station
Módulo de adquisición de telemetría de red Starlink (latencia, jitter, throughput, obstrucción) para una estación de medición integrada a un testbed internacional de redes LEO. Python · gRPC (Dishy) · Pydantic · MQTT (Mosquitto) · TimescaleDB · FastAPI · Grafana · Docker. Corre sobre Raspberry Pi 5. Proyecto Integrador, LIT — FCEFyN/UNC.

## Estado actual

En desarrollo. Semanas 1 a 8 cerradas del lado individual de Aldana (ver
`docs/PROGRESS.md` para el detalle y lo pendiente de coordinar con Fede). Pipeline
completo corriendo end-to-end con mocks:

```
mock_starlink (Random Walk + caos) → Mosquitto (broker) → consumer → starlink_db (TimescaleDB) → Grafana
                                                                            ↑
                                                              station_config_db (catálogo de nodos)
```

- Esquema de datos (ADR-01) y validador Pydantic alineado al DER (`network_metrics`).
- Mock stateful con random walk + inyección de caos (ADR-06), `TIME_WARP_FACTOR` para
  backfill acelerado (ADR-08), empaquetado como microservicio Docker (ADR-07).
- Broker MQTT (Mosquitto v5.0, QoS 1, LWT).
- Consumer MQTT → TimescaleDB (ORM SQLAlchemy, ADR-04) con ACK manual: solo confirma
  el mensaje si quedó persistido o el error es permanente, fuerza reentrega QoS 1 ante
  fallos transitorios de DB. Dominio meteo (Fede) ya enrutado, pendiente de que él
  implemente su persistencia real.
- Tres bases de datos independientes (ADR-10): `starlink_health_db` (métricas de red),
  `station_config_db` (catálogo de nodos/sensores), y `meteo_db` (pendiente, Fede).
- Dashboard Grafana "Red Starlink" provisionado como código (ADR-13): latencia/jitter,
  packet loss, throughput, satélites/obstrucción, histograma de latencia.
- Suite de tests (77/77), skill de control de consistencia ADR/DER/SRS/API
  (`adr-check`) activa.

## Levantar todo el stack

```bash
cp .env.example .env   # los defaults ya sirven para desarrollo local
docker compose --profile mocks up --build
```

El perfil `mocks` es obligatorio — sin él, `docker compose up` solo levanta el broker.
Esto levanta: broker MQTT, mock Starlink, consumer, `starlink_db`, `station_config_db`
y Grafana.

- **Grafana**: [http://localhost:3000](http://localhost:3000) — usuario/contraseña por
  defecto `admin` / `grafana_dev_password` (`.env`). El dashboard "Red Starlink" ya
  está provisionado.
- **Bases de datos**: no exponen puerto al host a propósito (ADR-14 — solo el consumer
  y Grafana, dentro de la red Docker, necesitan acceder). Para consultarlas a mano:

  ```bash
  docker exec -it starlink-health-db psql -U starlink_app -d starlink_health \
    -c "SELECT * FROM network_metrics ORDER BY time DESC LIMIT 5;"
  docker exec -it station-config-db psql -U station_config_app -d station_config \
    -c "SELECT * FROM station_metadata;"
  ```

- **MQTT**: ver los paquetes viajando por el broker:

  ```bash
  docker exec -it mosquitto-broker mosquitto_sub -t 'starlink/metrics/#' -v
  docker exec -it mosquitto-broker mosquitto_sub -t 'system/status/#' -v
  ```

- **Bajar todo**: `docker compose --profile mocks down` (agregar `-v` para borrar
  también los datos persistidos en los volúmenes).

## Mock Starlink

Publica cada `60/TIME_WARP_FACTOR` segundos en `starlink/metrics/<node_id>` y anuncia
su estado (online/offline, LWT) en `system/status/<node_id>`. Variables (`.env`):

| Variable | Default | Descripción |
|---|---|---|
| `STARLINK_NODE_ID` | `lit-cordoba-01` | `node_id` del payload |
| `CHAOS_PROFILE` | `CALM` | `CALM` / `STORM` / `HANDOVER_HEAVY` (ADR-06) |
| `TIME_WARP_FACTOR` | `1` | Acelera la cadencia de publicación para backfill (ADR-08). `1` = 1 msg/60s en tiempo real; valores más altos generan historia sintética más rápido (ej. `3600` ≈ 60 msg/s reales, arranca 30 días "atrás" y avanza el reloj simulado). |

Para correrlo fuera de Docker (contra un broker ya levantado):

```bash
PYTHONPATH=src MQTT_HOST=localhost python -m mock_starlink
```

## Consumer

Se suscribe a `starlink/metrics/+`, `meteo/sensor/+` y `meteo/external/+`, valida cada
paquete Starlink con el mismo modelo Pydantic que publica el mock (`StarlinkPayloadIn`,
ADR-01 — nada de esquemas duplicados) e inserta en `network_metrics` vía ORM SQLAlchemy
(ADR-04), con `ON CONFLICT (time, node_id) DO NOTHING` para tolerar reentregas QoS 1
sin duplicar filas. Sesión MQTT persistente (`clean_start=False` + ACK manual): si la
inserción falla por un error transitorio de DB, el mensaje no se ACKea y el broker lo
reentrega; si el payload es inválido, se loguea y se descarta (no tiene sentido
reintentar un error permanente).

El dominio meteo ya está enrutado (`ConsumerRouter`) pero `MeteoDB` es un stub sin
persistencia real — pendiente de que Fede tenga su mock/tópico y complete su propio
gateway, siguiendo el mismo patrón que `NetHealthDB`.

Para correrlo fuera de Docker (contra un broker y una DB ya levantados):

```bash
PYTHONPATH=src MQTT_HOST=localhost STARLINK_DB_HOST=localhost python -m consumer
```

## Bases de datos

- **`starlink_health_db`** (TimescaleDB): hypertables `network_metrics` y
  `network_tests`, índices (`idx_netmet_node_time`, `idx_netmet_loss`,
  `idx_netmet_obstructed`), compresión, retención de 6 meses, continuous aggregates
  `net_hourly`/`net_daily`. Script: `services/db/init_starlink_health.sql`.
- **`station_config_db`** (PostgreSQL plano, sin TimescaleDB — son catálogos chicos, no
  series temporales): `station_metadata` (nodos registrados, seedeada con
  `lit-cordoba-01`) y `sensor_catalog` (sensores por nodo, FK a `station_metadata`).
  Script: `services/db/init_station_config.sql`.
- **`meteo_db`**: pendiente, módulo de Fede.

## Grafana

Datasource y dashboard provisionados como código (ADR-13), sin pasos manuales:

```
services/grafana/provisioning/datasources/starlink.yml   # datasource starlink_health_db
services/grafana/provisioning/dashboards/dashboards.yml  # provider de dashboards
services/grafana/dashboards/red_starlink.json            # dashboard "Red Starlink"
```

## Estructura

```
src/mock_starlink/    # Esquema Pydantic, mock stateful, entrypoint MQTT (ADR-01/06/07)
src/consumer/         # Router MQTT -> DB, gateway ORM, entrypoint MQTT (ADR-04/10)
tests/                # Suite de tests
Dockerfile            # Empaquetado del mock_starlink (ADR-07)
Dockerfile.consumer   # Empaquetado del consumer (ADR-07)
docker-compose.yml    # Broker, mock, consumer, DBs, Grafana
services/broker/      # Config de Mosquitto
services/db/          # Scripts de init SQL (starlink_health, station_config)
services/grafana/     # Provisioning de datasources y dashboards
```

## Requisitos

- **Python 3.11** (ADR-05: versión pinneada para toda la capa RPi5). El entorno de
  producción/CI y el contenedor Docker (ADR-12) corren sobre 3.11; en una máquina de
  desarrollo que no tenga 3.11 instalado, 3.13 también funciona hoy (la suite de tests
  no usa nada específico de una versión), pero no reemplaza la validación real en el
  entorno pinneado antes de integrar con hardware o con el resto de la pila.
- **Docker Engine + Docker Compose v2** (ADR-12) para levantar el stack completo.

## Instalación

```bash
git clone <url-del-repo>
cd starlink-measurement-station
python3.11 -m venv .venv   # o python3 -m venv .venv si no tenés 3.11 instalado
source .venv/bin/activate
pip install -r requirements.txt -r requirements-consumer.txt
```

## Tests

Correr toda la suite (UT-01 esquema, UT-03 router del consumer, UT-04 mock stateful):

```bash
PYTHONPATH=src pytest tests/ -v
```

Con reporte de cobertura:

```bash
PYTHONPATH=src pytest tests/ --cov=src --cov-report=term-missing
```
