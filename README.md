# starlink-measurement-station
Módulo de adquisición de telemetría de red Starlink (latencia, jitter, throughput, obstrucción) para una estación de medición integrada a un testbed internacional de redes LEO. Python · gRPC (Dishy) · Pydantic · MQTT (Mosquitto) · TimescaleDB · FastAPI · Grafana · Docker. Corre sobre Raspberry Pi 5. Proyecto Integrador, LIT — FCEFyN/UNC.

## Estado actual

En desarrollo. Semanas 1 a 12 cerradas del lado individual de Aldana (ver
`docs/PROGRESS.md` para el detalle y lo pendiente de coordinar con Fede). Pipeline
completo corriendo end-to-end con mocks (perfil `mocks`) o contra hardware real
(perfil `real`, semana 10 — código escrito, todavía sin validar contra la antena
física):

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
  fallos transitorios de DB. Dominio meteo (Fede) ya enrutado, pendiente de que él
  implemente su persistencia real.
- Tres bases de datos independientes (ADR-10): `starlink_health_db` (métricas de red),
  `station_config_db` (catálogo de nodos/sensores), y `meteo_db` (pendiente, Fede).
- Backend API REST (FastAPI, semana 9): `GET /health`, `GET /metrics/starlink*`,
  `GET /nodes*`, `POST /ingest/starlink` (testing/backfill). Auth por `X-API-Key`.
- Extractor real (semana 10): reemplaza al mock contra la antena física vía `grpcurl`
  (server reflection) — mismo tópico/morfología de paquete, sin validar contra
  hardware todavía (sin acceso presencial al LIT en la última sesión).
- Dashboard Grafana "Red Starlink" provisionado como código (ADR-13): latencia/jitter,
  packet loss, throughput, satélites/obstrucción/SNR bajo, handovers por hora,
  alineación de la antena, histograma de latencia.
- Suite de tests (177 pasando, ~95% de cobertura sobre el código unit-testeable — ver
  `.coveragerc`), suite de integración IT-01 automatizada (`tests/integration/`, corre
  contra Docker real), CI en GitHub Actions (`.github/workflows/`). Skill de control de
  consistencia ADR/DER/SRS/API (`adr-check`) activa.

## Levantar todo el stack

```bash
cp .env.example .env   # los defaults ya sirven para desarrollo local
docker compose --profile mocks up --build
```

Perfiles disponibles (`docker-compose.yml`) — sin uno de estos, `docker compose up`
solo levanta el broker:

| Perfil | Para qué | Servicios |
|---|---|---|
| `mocks` | Desarrollo local, sin hardware | broker, `mock_starlink`, `consumer`, `starlink_db`, `station_config_db`, `backend`, `grafana` |
| `real` | Hardware real (RPi5 + antena en `192.168.100.1:9200`) | `acquisition` en vez de `mock_starlink` — **nunca junto con `mocks`**, dos productores del mismo tópico rompería ADR-01 |
| `stress` | Pruebas de carga (semana 21) | mismo set que `mocks`, pensado para correr con `TIME_WARP_FACTOR` alto |

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
  docker exec -it mosquitto-broker mosquitto_sub -t 'system/status/#' -v
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

## Backend API REST

FastAPI, contrato completo en `docs/07_API_REST.md`. Endpoints montados (dominio
Starlink únicamente — `/metrics/env*`/`POST /ingest/env` son de Fede, no montados):

| Endpoint | Auth | Descripción |
|---|---|---|
| `GET /api/v1/health` | No | Estado de `starlink_health_db` + broker MQTT (TCP check liviano). `db_meteo_data` reporta `not_configured` — dominio de Fede, todavía no implementado. |
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
**nunca junto con `mocks`**.

⚠️ Escrito y con tests unitarios sobre la lógica de mapeo (`tests/test_acquisition.py`,
JSON sintético), pero **sin validar contra la antena real todavía** — pendiente de la
próxima visita presencial al LIT (ver `docs/PROGRESS.md` §Semana 10 para el checklist).

```bash
docker compose --profile real up --build acquisition
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
