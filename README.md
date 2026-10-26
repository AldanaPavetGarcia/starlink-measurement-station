# starlink-measurement-station

[![CI](https://github.com/AldanaPavetGarcia/starlink-measurement-station/actions/workflows/ci.yml/badge.svg)](https://github.com/AldanaPavetGarcia/starlink-measurement-station/actions/workflows/ci.yml)

Módulo de adquisición de telemetría de red Starlink (latencia, jitter, throughput, obstrucción) para una estación de medición integrada a un testbed internacional de redes LEO. Python · gRPC (Dishy) · Pydantic · MQTT (Mosquitto) · TimescaleDB · FastAPI · Grafana · Docker. Corre sobre Raspberry Pi 5. Proyecto Integrador, LIT — FCEFyN/UNC.

## Estado actual

En desarrollo. Semanas 1 a 12 cerradas del lado individual de Aldana (ver
`docs/PROGRESS.md` para el detalle y lo pendiente de coordinar con Fede). Pipeline
completo corriendo end-to-end con mocks (perfil `mocks`) o contra hardware real
(perfil `real`, semana 10 — la pila completa corre en la RPi5 del LIT contra la
antena real desde el 14/08/2026, ver §Extractor real). El módulo meteo de Fede se
suma a esta pila desde `starlink-station-stack` (ADR-21, ver §Con el módulo meteo):

```
mock_starlink (Random Walk + caos)  ─┐
      o acquisition (antena real)   ─┴─▶ Mosquitto (broker) → consumer → starlink_db (TimescaleDB) ─┬─▶ Grafana
                                                                                                      └─▶ backend (FastAPI)
                                                                              ↑
                                                                station_config_db (catálogo de nodos)
```

- Esquema de datos v1.1 (ADR-01/16/17/18) y validador Pydantic alineado al DER
  (`network_metrics`): `snr_low` (booleano, reemplaza `snr_db` — el firmware real no
  expone SNR numérico), `handover_count`/`outage_duration_ms`, y los campos de
  orientación física de la antena (`tilt_angle_deg`, `boresight_*`, etc.).
- Mock stateful con random walk + inyección de caos (ADR-06), `TIME_WARP_FACTOR` para
  backfill acelerado (ADR-08), empaquetado como microservicio Docker (ADR-07).
- Broker MQTT (Mosquitto v5.0, QoS 1, LWT).
- Consumer MQTT → TimescaleDB (ORM SQLAlchemy, ADR-04) con ACK manual: solo confirma
  el mensaje si quedó persistido o el error es permanente, fuerza reentrega QoS 1 ante
  fallos transitorios de DB. Solo procesa `starlink/metrics/+`: el dominio meteo
  tiene su propio consumer y su propia DB en el repo de Fede (ADR-21).
- Tres bases de datos independientes (ADR-10): `starlink_health_db` (métricas de red),
  `station_config_db` (catálogo de nodos/sensores), y `meteo_data` (de Fede, en
  `tesis-sensor-node`; acá solo se lee desde Grafana y `/health`, ADR-21).
- Backend API REST (FastAPI, semana 9): `GET /health`, `GET /metrics/starlink*`,
  `GET /nodes*`, `POST /ingest/starlink` (testing/backfill). Auth por `X-API-Key`.
- Extractor real (semana 10): reemplaza al mock contra la antena física vía `grpcurl`
  (server reflection) — mismo tópico/morfología de paquete. Mapeo validado
  campo a campo contra la antena real el 12/08/2026 y corriendo como servicio
  Docker continuo en la RPi5 desde el 14/08/2026 (ver `docs/PROGRESS.md`).
- Dashboard Grafana "Red Starlink" provisionado como código (ADR-13): latencia/jitter,
  packet loss, throughput, satélites/obstrucción/SNR bajo, handovers por hora,
  alineación de la antena, histograma de latencia. Dashboard "Correlación Red-Clima"
  (RF-33, CA-04) que cruza `starlink_health_db` con `meteo_data` de Fede (ADR-21).
- Suite de tests (190 pasando, ~95% de cobertura sobre el código unit-testeable — ver
  `.coveragerc`), suite de integración IT-01 automatizada (`tests/integration/`, corre
  contra Docker real), CI en GitHub Actions (`.github/workflows/`). Skill de control de
  consistencia ADR/DER/SRS/API (`adr-check`) activa.

## Levantar todo el stack

**¿Dónde corre esto?** El perfil `mocks` es para desarrollo/testing — corre en
cualquier máquina (tu laptop, para probar en casa sin hardware). El perfil `real`
es el despliegue de producción y **corre entero en la RPi5 del LIT** — no solo
`acquisition`, sino toda la pila (broker, DBs, backend, Grafana) en la misma
máquina, para no depender de que tu laptop esté prendida durante las 72h de
CA-01/CA-02 (ver `CLAUDE.md` §6, plan de migración Local → Nube).

```bash
cp .env.example .env   # los defaults ya sirven para desarrollo local
docker compose --profile mocks up --build
```

Perfiles disponibles (`docker-compose.yml`) — sin uno de estos, `docker compose up`
solo levanta el broker:

| Perfil | Para qué | Dónde corre | Servicios |
|---|---|---|---|
| `mocks` | Desarrollo local, sin hardware | Cualquier máquina (tu laptop) | broker, `mock_starlink`, `consumer`, `starlink_db`, `station_config_db`, `backend`, `grafana` |
| `real` | Producción con hardware real | **Solo la RPi5 del LIT** (única con ruta a `192.168.100.1:9200`) | `acquisition` en vez de `mock_starlink`, **más** el resto del stack de `mocks` (broker/DBs/backend/grafana) levantado ahí mismo — **nunca junto con** el contenedor `mock_starlink`, dos productores del mismo tópico rompería ADR-01 |
| `stress` | Pruebas de carga (semana 21) | Cualquier máquina | mismo set que `mocks`, pensado para correr con `TIME_WARP_FACTOR` alto |

- **Grafana**: [http://localhost:3000](http://localhost:3000) — usuario/contraseña por
  defecto `admin` / `grafana_dev_password` (`.env`). El dashboard "Red Starlink" ya
  está provisionado.
- **Backend API**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
  (Swagger UI) — publicado a la intranet del LIT (ADR-14: tabla de exposición de
  puertos, distinto de Grafana que es público). En producción, restringir el acceso
  por IP a nivel de firewall/router queda fuera de este `docker-compose.yml`. Requiere
  `X-API-Key: <BACKEND_API_KEY del .env>` en casi todos los endpoints (`GET /health`
  es público).
- **Bases de datos**: no exponen puerto al host a propósito (ADR-14 — solo el consumer,
  el backend y Grafana, dentro de la red Docker, necesitan acceder). Para consultarlas
  a mano:

  ```bash
  docker exec -it starlink-health-db psql -U starlink_app -d starlink_health \
    -c "SELECT * FROM network_metrics ORDER BY time DESC LIMIT 5;"
  docker exec -it station-config-db psql -U station_config_app -d station_config \
    -c "SELECT * FROM station_metadata;"
  ```

- **MQTT**: ver los paquetes viajando por el broker:

  ```bash
  docker exec -it mosquitto-broker mosquitto_sub -t 'starlink/metrics/#' -v
  docker exec -it mosquitto-broker mosquitto_sub -t 'starlink/status/#' -v
  ```

- **Bajar todo**: `docker compose --profile mocks down` (agregar `-v` para borrar
  también los datos persistidos en los volúmenes).

### Seguridad en un despliegue real (RPi5 en el LIT)

`docker-compose.yml` solo controla qué puertos se publican, no *quién* puede
alcanzarlos — el filtrado de IP (ADR-14) es una configuración del host, no de
Docker. En una RPi5 real, después de levantar el stack:

```bash
sudo ufw allow from <subred-LIT>/24 to any port 3000 proto tcp   # Grafana
sudo ufw allow from <subred-LIT>/24 to any port 8000 proto tcp   # Backend
sudo ufw deny 3000/tcp
sudo ufw deny 8000/tcp
```

Ver la sección "Mecanismo concreto de filtrado de IP" de ADR-14 en
`docs/05_ADR.md` para el detalle y el caso de acceso remoto puntual del
director/co-director.

### Con el módulo meteo (unión con Fede)

Este repo no levanta nada del dominio meteo (ADR-21). La DB `meteo_data` y su
consumer viven en [`tesis-sensor-node`](https://github.com/BlastNeos/tesis-sensor-node)
y se suman a esta pila con el compose de integración de
[`starlink-station-stack`](https://github.com/AldanaPavetGarcia/starlink-station-stack)
(`infra/rpi5-union/`), que se une a la red Docker `starlink-station-net` de esta pila.
Un solo broker: el de este repo.

Los tres repos clonados lado a lado:

```bash
# 1. Esta pila, con METEO_DB_* y STARLINK_NETWORK_NAME en el .env (ver .env.example):
#    METEO_DB_HOST=meteo_db  METEO_DB_PORT=5432  METEO_DB_NAME=meteo_data
#    METEO_DB_USER=meteo_app METEO_DB_PASSWORD=meteo_dev_password
docker compose --profile mocks up -d --build          # en la PC
# en la RPi5 (perfil real, sin mock_starlink):
# docker compose up -d --build broker acquisition starlink_db station_config_db consumer backend grafana

# 2. La pila meteo de Fede, desde starlink-station-stack:
cd ../starlink-station-stack/infra/rpi5-union
cp .env.example .env                                  # TESIS_SENSOR_NODE_DIR apunta al clon de Fede
docker compose up -d --build                          # con el ESP32 real
docker compose --profile meteo-mocks up -d --build    # o con los mocks de Fede
```

Sin `METEO_DB_HOST` esta pila funciona igual sola: `/health` reporta
`db_meteo_data: not_configured` y los paneles de "Correlación Red-Clima" quedan vacíos.
Verificación paso a paso y vuelta atrás: `docs/E2E_RPI5.md` de `starlink-station-stack`.

## Mock Starlink

Publica cada `60/TIME_WARP_FACTOR` segundos en `starlink/metrics/<node_id>` y anuncia
su estado (online/offline, LWT) en `starlink/status/<node_id>` (antes `system/status/<node_id>`,
ver enmienda de ADR-03/ADR-04 del 14/08/2026 en `docs/05_ADR.md`). Variables (`.env`):

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

Se suscribe solo a `starlink/metrics/+` (ADR-21), valida cada
paquete Starlink con el mismo modelo Pydantic que publica el mock (`StarlinkPayloadIn`,
ADR-01 — nada de esquemas duplicados) e inserta en `network_metrics` vía ORM SQLAlchemy
(ADR-04), con `ON CONFLICT (time, node_id) DO NOTHING` para tolerar reentregas QoS 1
sin duplicar filas. Sesión MQTT persistente (`clean_start=False` + ACK manual): si la
inserción falla por un error transitorio de DB, el mensaje no se ACKea y el broker lo
reentrega; si el payload es inválido, se loguea y se descarta (no tiene sentido
reintentar un error permanente).

Los tópicos `meteo/*` no son de este consumer: los procesa el `meteo_consumer` de
Fede (`tesis-sensor-node`), que escribe en su propia DB `meteo_data` (ADR-21). Si
llega alguno acá, `ConsumerRouter` lo loguea como tópico desconocido y lo descarta.

Para correrlo fuera de Docker (contra un broker y una DB ya levantados):

```bash
PYTHONPATH=src MQTT_HOST=localhost STARLINK_DB_HOST=localhost python -m consumer
```

## Backend API REST

FastAPI, contrato completo en `docs/07_API_REST.md`. Endpoints montados (dominio
Starlink únicamente — `/metrics/env*`/`POST /ingest/env` son de Fede, no montados):

| Endpoint | Auth | Descripción |
|---|---|---|
| `GET /api/v1/health` | No | Estado de `starlink_health_db` + broker MQTT (TCP check liviano). `db_meteo_data`: `up` (con `last_write` de `env_metrics`) o `down` si `METEO_DB_HOST` está configurado, `not_configured` si no (ADR-21). |
| `GET /api/v1/metrics/starlink` | Sí | Serie temporal, `resolution=auto` elige entre `network_metrics` (raw), `net_hourly`, `net_daily` según el rango. |
| `GET /api/v1/metrics/starlink/summary` | Sí | Estadísticas agregadas del período (avg/p50/p95/p99, disponibilidad, eventos de obstrucción). |
| `GET /api/v1/metrics/starlink/latest` | Sí | Última medición por nodo. |
| `GET /api/v1/nodes`, `/nodes/{node_id}` | Sí | Catálogo de `station_metadata` + `sensor_catalog`, con `telemetry.last_starlink_metric` cruzado desde `starlink_health_db`. |
| `POST /api/v1/ingest/starlink` | Sí | Ingesta manual (testing/backfill) — desactivada por default, `ENABLE_INGEST_ENDPOINT=true` para habilitarla. |

Variables (`.env`): `BACKEND_API_KEY` (generar con
`python -c "import secrets; print(secrets.token_hex(32))"`), `BACKEND_PORT`
(default `8000`), `ENABLE_INGEST_ENDPOINT` (default `false`).

Para correrlo fuera de Docker:

```bash
PYTHONPATH=src STARLINK_DB_HOST=localhost STATION_CONFIG_DB_HOST=localhost \
  BACKEND_API_KEY=dev-key uvicorn backend.main:app --reload
```

## Extractor real (acquisition)

Reemplaza a `mock_starlink` contra la antena física (`192.168.100.1:9200`) — mismo
tópico MQTT y misma morfología de paquete (ADR-01), el consumer/DB/Grafana no notan
el cambio. Usa `grpcurl` (server reflection) en vez de bindings `grpcio` compilados —
ver la enmienda de ADR-01 en `docs/05_ADR.md`. Corre bajo el perfil `real`,
**solo en la RPi5** (única máquina con ruta a la antena), **nunca junto con** el
contenedor `mock_starlink` del perfil `mocks`.

✅ Mapeo (`starlink_extractor.py`) validado el 12/08/2026 contra un payload real
capturado de la antena (`grpcurl` vía SSH a la RPi5) — encontró y corrigió 3
mismatches con lo asumido en ADR-16/17/18 (`snr_low`, `is_obstructed`, rango de
`boresight_azimuth_deg`), ver `docs/PROGRESS.md` §Semana 10 para el detalle.
✅ Corriendo como servicio Docker continuo en la RPi5 desde el 14/08/2026, con el
resto de la pila en la misma máquina (corrida de 72h de CA-01/CA-02 y su estado en
`docs/PROGRESS.md`).

```bash
# en la RPi5: los 7 servicios de producción, nombrados explícitamente (activa sus
# perfiles sin levantar mock_starlink):
docker compose up -d --build broker acquisition starlink_db station_config_db consumer backend grafana
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
- **`meteo_data`** (TimescaleDB, de Fede): `env_metrics` con PK
  `(time, node_id, source, producer)`, `source` ∈ {`real`, `mock`}. No se crea en este
  repo: el script es `tesis-sensor-node/infrastructure/meteo-db/init_meteo_data.sql`
  (ADR-21, `docs/06_DER.md` §4).

## Grafana

Datasource y dashboard provisionados como código (ADR-13), sin pasos manuales:

```
services/grafana/provisioning/datasources/starlink.yml   # datasource starlink_health_db
services/grafana/provisioning/datasources/meteo.yml      # datasource meteo_data (DB de Fede, METEO_DB_*)
services/grafana/provisioning/dashboards/dashboards.yml  # provider de dashboards
services/grafana/dashboards/red_starlink.json            # dashboard "Red Starlink"
services/grafana/dashboards/correlacion_red_clima.json   # dashboard "Correlación Red-Clima" (RF-33, CA-04)
```

## Estructura

```
src/mock_starlink/    # Esquema Pydantic, mock stateful, entrypoint MQTT (ADR-01/06/07)
src/consumer/         # Router MQTT -> DB, gateway ORM, entrypoint MQTT (ADR-04/10)
src/backend/          # API REST FastAPI (docs/07_API_REST.md)
src/acquisition/      # Extractor real vía grpcurl (semana 10)
src/common/           # Logging JSON y reconexión MQTT compartidos
tests/                # Suite de tests unitarios
tests/integration/    # Suite IT-01 (requiere Docker real, se saltea sola si no está)
Dockerfile              # Empaquetado del mock_starlink (ADR-07)
Dockerfile.consumer     # Empaquetado del consumer (ADR-07)
Dockerfile.backend      # Empaquetado del backend
Dockerfile.acquisition  # Empaquetado del extractor real (instala grpcurl)
docker-compose.yml    # Broker, mock/acquisition, consumer, backend, DBs, Grafana
services/broker/      # Config de Mosquitto
services/db/          # Scripts de init SQL (starlink_health, station_config)
services/grafana/     # Provisioning de datasources y dashboards
.github/workflows/    # CI (unit + integration) y publish (imágenes a GHCR)
```

## Requisitos

- **Python 3.11** (ADR-05: versión pinneada para toda la capa RPi5). El entorno de
  producción/CI y el contenedor Docker (ADR-12) corren sobre 3.11; en una máquina de
  desarrollo que no tenga 3.11 instalado, 3.13 también funciona hoy (la suite de tests
  no usa nada específico de una versión), pero no reemplaza la validación real en el
  entorno pinneado antes de integrar con hardware o con el resto de la pila.
- **Docker Engine + Docker Compose v2** (ADR-12) para levantar el stack completo.
- **`grpcurl`** solo si vas a correr `src/acquisition/` fuera de Docker (Docker ya lo
  instala en `Dockerfile.acquisition`).

## Instalación

```bash
git clone <url-del-repo>
cd starlink-measurement-station
python3.11 -m venv .venv   # o python3 -m venv .venv si no tenés 3.11 instalado
source .venv/bin/activate
pip install -r requirements.txt -r requirements-consumer.txt \
  -r requirements-backend.txt -r requirements-acquisition.txt
```

## Tests

Correr toda la suite (unitarios + integración, esta última se saltea sola sin Docker):

```bash
PYTHONPATH=src:. pytest tests/
```

`PYTHONPATH` necesita `.` además de `src` porque algunos tests del backend se importan
como paquete `tests.*` (`tests/backend_fakes.py`, dobles de SQLAlchemy). La cobertura
mínima (80%, `.coveragerc` excluye los loops de conexión MQTT de los `__main__.py` —
se validan con Docker real, no mockeando todo el stack de `paho-mqtt`) ya corre por
default vía `pytest.ini`.

Solo la suite unitaria (sin tocar Docker, más rápida):

```bash
PYTHONPATH=src:. pytest tests/ --ignore=tests/integration
```

Solo la suite de integración IT-01 (requiere `docker compose --profile mocks up -d
broker starlink_db station_config_db consumer` primero):

```bash
PYTHONPATH=src:. pytest tests/integration/ -v --no-cov -o addopts=""
```
