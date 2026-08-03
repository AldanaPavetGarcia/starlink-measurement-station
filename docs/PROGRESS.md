# PROGRESS.md — Módulo Starlink (Aldana)

> Estado de avance real del módulo de conexión a la antena Starlink, alineado al roadmap de
> `CLAUDE.md` §1.1. Editar a mano o pedirle a Claude Code que lo actualice al cerrar una tarea.
> Convención: **[IND]** trabajo individual · **[INT]** integración con el módulo de Fede ·
> **[HW]** requiere hardware real.

**Última actualización:** semanas 1 a 8 completas del lado Starlink (semana 6 en
adelante, **solo lado Starlink** — ver justificación abajo; Fede todavía no arrancó
su módulo). Semanas 7 y 8: se creó `station_config_db` (tercera instancia de DB,
ver "Corregido esta sesión" — conflicto ADR-10 vs. DER sobre cuántas bases hay),
se validaron los índices/CHECK constraints de `network_metrics` contra ~2500 filas
backfillate reales, y se armó el dashboard "Red Starlink" en Grafana (datasource +
5 paneles provisionados como código, ADR-13), verificado con datos reales vía la
API de Grafana. Detalle completo en las secciones de semana 7/8 más abajo.

Semana 6: se decidió no bloquearse en la integración conjunta y construir el
consumer para el dominio `starlink/metrics/` con el dominio meteo ya enrutado pero
sin persistencia real (`MeteoDB` es un stub, `src/consumer/db.py`), listo para que
Fede lo complete cuando tenga su tópico y esquema. Implementado: `services/db/init_starlink_health.sql`
(hypertable `network_metrics` + `network_tests` + continuous aggregates
`net_hourly`/`net_daily`, copiado de `docs/06_DER.md` §7.1 con una corrección, ver
"Corregido esta sesión"), `src/consumer/` (`router.py`: `ConsumerRouter.route_message`
enruta por prefijo de tópico exactamente como especifica la suite UT-03 de
`docs/08_Plan_QA.md`; `db.py`: `NetHealthDB` con ORM SQLAlchemy declarativo
-- ADR-04 -- e INSERT idempotente vía `ON CONFLICT (time, node_id) DO NOTHING`
sobre la PK compuesta, necesario porque QoS 1/ADR-09 es *at-least-once* y el
consumer usa ACK manual + sesión persistente para forzar reentrega ante fallos
transitorios de DB; `__main__.py`: cliente MQTT con `manual_ack=True`, sesión
persistente MQTTv5 -- `clean_start=False` + `SessionExpiryInterval` infinito --
y logging JSON igual al de `mock_starlink`). Nuevo `Dockerfile.consumer` +
`requirements-consumer.txt`, y `starlink_db`/`consumer` sumados a
`docker-compose.yml` bajo el mismo perfil `mocks` que ya usaba el mock, con
`timescale/timescaledb:2.17.2-pg16` pinneado (verificado con `docker pull`, no
`:latest`, ADR-12). Verificado end-to-end real con `docker compose --profile mocks
up --build`: fila persistida en `network_metrics` (IT-01-01), reentrega QoS 1
confirmada matando y reiniciando el `consumer` mientras el mock seguía publicando
-- el broker retuvo el mensaje y apareció en la DB recién al reconectar (IT-01-03,
RNF-05). Tests nuevos: `tests/test_consumer_router.py` (suite UT-03 completa,
UT-03-01 a UT-03-05) y `tests/test_consumer_db.py`. 77/77 tests pasando
(`PYTHONPATH=src pytest tests/`).

ADR-01 a ADR-05 revisados y sus puntos abiertos cerrados (ver "Corregido esta
sesión") — **falta que Fede confirme los puntos de ADR-02/ADR-03 (BME280, backoff
ESP32, LWT) que se completaron con valores por default**. Mock stateful (ADR-06),
publisher MQTT con LWT y empaquetado Docker (ADR-07) implementados y verificados
contra un broker real (`docker compose --profile mocks up --build`, pub/sub y
`docker kill` para el LWT, todo a mano). `TIME_WARP_FACTOR` (ADR-08) funcionando.
Todo el drift de documentación detectado esta sesión (vocabulario SRS/DER/ADR-06,
backfill SRS §10.3 vs. ADR-08, fila iperf3 de ADR-04, "stateless" vs. mock
stateful, fixture del Plan de QA, vocabulario "fantasma" de `POST /ingest/starlink`
en `docs/07_API_REST.md`, y la estructura envelope + `metrics` anidado del payload,
ahora documentada explícitamente en ADR-01) se resolvió y documentó con
justificación — no quedó ningún punto abierto para el director de este lado. Sí
queda un punto de coordinación con Fede (mismo patrón `station_id`/`source_module`
en `POST /ingest/env`, ver abajo).
Próximo corte real: **semana 9**, endpoints FastAPI (`/metrics/starlink`,
`/summary`, `/latest`) + auth por API Key + logging estructurado en el backend.
Semanas 11-24 del roadmap siguen esperando, en su mayoría, a que Fede tenga su
mock/tópico meteo andando (`MeteoDB` real) o a hardware real (semana 10).

---

## Pendiente — revisar con director/co-director

Ninguno por ahora del lado de este módulo. Ver "Coordinación pendiente con Fede" más
abajo para los puntos que sí requieren su confirmación.

---

## Corregido esta sesión

- **Conflicto ADR-10 (Database per Service) vs. `docs/06_DER.md` §1 sobre
  cuántas bases de datos hay**: ADR-10 decía explícitamente "dos instancias"
  (`starlink_health_db`, `meteo_db`), pero el DER siempre listó tres
  (`starlink_health`, `meteo_data`, y `station_config` — con `station_metadata`/
  `sensor_catalog`). No estaba anotado como conflicto conocido en este archivo,
  así que no lo resolví por mi cuenta: se lo presenté al usuario (Aldana) en la
  sesión, decidió una tercera instancia liviana (`station_config_db`, PostgreSQL
  plano sin TimescaleDB — son catálogos chicos, no series temporales). ADR-10
  enmendado con la justificación completa (sigue "Propuesto", no se tocó el
  estado). Necesario para semana 7 (`station_metadata` es la tabla contra la
  que se valida la coherencia de `node_id`).

- **`add_continuous_aggregate_policy('net_daily', ...)` con una ventana de
  refresco inválida en `docs/06_DER.md` §7.1 y, por copia, en
  `services/db/init_starlink_health.sql`**: `start_offset => '2 days',
  end_offset => '1 day'` da una ventana de 1 bucket (`net_daily` usa
  `time_bucket('1 day', ...)`), y TimescaleDB exige al menos 2 buckets — falla
  en runtime con `ERROR: policy refresh window too small`, reproducido contra
  un servidor TimescaleDB real (semana 7). No es un problema de diseño, es un
  parámetro que nunca se había probado contra un servidor real. Se corrigió a
  `start_offset => '3 days'` (ventana de 2 buckets, misma proporción que
  `net_hourly`, que sí funcionaba) en ambos archivos, y se confirmó con
  volúmenes Docker limpios que el init script corre sin errores y ambas
  políticas (`net_hourly`, `net_daily`) quedan registradas
  (`timescaledb_information.jobs`).

- **`PRIMARY KEY (time, node_id)` faltante en el bloque SQL de referencia de
  `docs/06_DER.md` §7.1 (`network_metrics`, `network_tests`)**: la sección
  "Convenciones" del propio DER ya establecía PK compuesta `(time, node_id)`
  para toda hypertable, pero el `CREATE TABLE` de ejemplo no la declaraba —
  drift interno del documento contra sí mismo, no causado por el código. Se
  agregó la PK en el DER y en `services/db/init_starlink_health.sql` (la
  implementación real). Importa porque el consumer deduplica reentregas QoS 1
  (ADR-09, at-least-once) con `ON CONFLICT (time, node_id) DO NOTHING`, que
  necesita un índice único sobre esas columnas para funcionar — verificado
  end-to-end (ver semana 6 arriba).

- **ADR-10, sección "Consecuencias e Implicaciones", todavía describía el
  routing del consumer con la nomenclatura de tópicos vieja** (`tópicos con
  /net_health/ ... /meteo/`), previa a la corrección de la tabla de tópicos de
  ADR-04 (`docs/PROGRESS.md`, sesión anterior). Se actualizó a los prefijos
  reales (`starlink/`, `meteo/`), que es literalmente lo que implementa
  `src/consumer/router.py:ConsumerRouter` esta sesión.

- **Estructura del payload (envelope + `metrics` anidado) documentada explícitamente
  en ADR-01, y `docs/03_SRS.md` §5.1 corregido para reflejarla**: `schema.py` ya
  publicaba `{schema_version, node_id, timestamp, metrics: {latency_ms, ...}}`, pero
  ningún documento explicaba por qué la estructura es anidada, y la tabla del SRS
  §5.1 la mostraba como si fuera plana. Decisión (documentada en ADR-01, sección
  "Estructura concreta del payload"): se mantiene anidada — separa el ciclo de vida
  del envelope (identidad del paquete) del de `metrics` (puede evolucionar con
  nuevos firmwares de la antena) sin acoplar la validación de uno al otro, y ya está
  implementada, testeada y verificada end-to-end contra un broker real desde semana
  4-5 (revertir a plano hubiera significado invalidar esa verificación sin ninguna
  ganancia real). El SRS §5.1 se reescribió para mostrar la estructura envelope +
  `metrics` con un ejemplo JSON completo, en vez de la tabla plana anterior. No
  aplica a `network_metrics` ni a los GET de la API REST, que son planos por
  naturaleza (columnas SQL) — sin cambios ahí.

- **RF-03 (`docs/03_SRS.md`) todavía citaba `obstruction_pct, signal_quality`** en la
  descripción del requerimiento — mismo drift, distinta ubicación (no era la tabla
  §5.1 que ya se había corregido). Actualizado a `is_obstructed`, `snr_db`,
  `satellite_count`.

- **`docs/07_API_REST.md` — `POST /ingest/starlink` usaba un tercer vocabulario,
  inconsistente incluso con los GET del mismo documento**: el ejemplo de request body
  y el modelo Pydantic `StarlinkMetricsIn`/`StarlinkPayloadIn` (§9.1) usaban
  `station_id`, `source_module`, `pop_ping_latency_ms`, `pop_ping_drop_rate` (fracción
  0–1, no porcentaje), `downlink/uplink_throughput_bps` — ninguno de estos existe en
  `src/mock_starlink/schema.py`, y ni siquiera coincidían con los GET del propio
  `docs/07_API_REST.md` (`StarlinkMetricOut`), que ya usaban el vocabulario correcto
  del DER. Es el mismo vocabulario "fantasma" que tenía el fixture de
  `docs/08_Plan_QA.md` (ya corregido arriba) — parece un borrador viejo copiado a dos
  documentos. Se corrigió a `node_id`/`latency_ms`/`jitter_ms` (faltaba por completo)/
  `packet_loss_pct`/`throughput_down_bps`/`throughput_up_bps`, con los mismos bounds
  que `schema.py:StarlinkMetrics` (`snr_db` ge=-20/le=30, etc.), y se sacó
  `source_module` (no existe en el esquema real). No se tocó `POST /ingest/env` ni
  `EnvPayloadIn` (mismo patrón `station_id`/`source_module`) porque es el módulo de
  Fede — queda anotado en "Coordinación pendiente con Fede" abajo.

- **Drift de vocabulario/unidades SRS §5.1 y ADR-06 vs. DER/código**: se corrigió
  `docs/03_SRS.md` §5.1 y la tabla estadística de ADR-06 para usar
  `throughput_down/up_bps` (en vez de Mbps), `is_obstructed`/`snr_db` (en vez de
  `obstruction_pct`/`signal_quality`), y se agregó `satellite_count` (faltaba en
  ambos). Gana el DER/`schema.py` porque son más específicos técnicamente (bps en
  BIGINT porque Starlink puede superar 2 Gbps; `is_obstructed`/`snr_db` son los
  campos reales que expone el gRPC de la antena) y porque ya era el vocabulario que
  seguían 3 de los 4 documentos autoritativos más el código. La tabla de ADR-06
  además se amplió con filas de `snr_db` y `satellite_count` (no estaban) para que
  documente completo lo que `mock.py` ya calibra vía `CHAOS_PARAMS`.

- **`docs/03_SRS.md` §10.3 corregido para coincidir con ADR-08**: describía un
  "script de backfill" con INSERT SQL directo a las hypertables — la Alternativa A
  que ADR-08 rechaza explícitamente. Se reescribió para describir la ingesta
  orgánica E2E vía `TIME_WARP_FACTOR`, que es lo que está implementado desde semana 5.

- **Fila `nodo/lit-01/net_health/iperf_test` eliminada de la tabla de tópicos de
  ADR-04**: no estaba cubierta por el SRS ni por el "Alcance técnico" de
  `CLAUDE.md` §1.1 (solo telemetría pasiva vía gRPC, sin tests activos), rompía la
  convención domain-first del resto de la tabla, y de agregarse en el futuro
  correspondería a la tabla `network_tests` del DER (§3.2), no a `network_metrics`
  (que es a donde la enrutaba la fila eliminada). Comentario [^c5] marcado resuelto.

- **Aclaración "stateless" (ADR-12) vs. mock stateful (ADR-06)**: se agregó una
  aclaración en el Contexto de ADR-12 distinguiendo "stateless" a nivel de
  infraestructura (12-factor: ningún contenedor depende de un volumen local
  persistente, así que la migración local→nube funciona con solo cambiar `.env`) de
  "stateful" a nivel de lógica de generación de datos en memoria (ADR-06: el mock
  recuerda el último valor de latencia para el random walk, pero es estado
  transitorio de un proceso reiniciable, no estado de infraestructura). No era una
  contradicción real. Comentario [^c14] del director marcado resuelto.

- **Fixture de ejemplo en `docs/08_Plan_QA.md` corregido**: el bloque `conftest.py`
  de referencia usaba un tercer vocabulario (`station_id`, `source_module`,
  `pop_ping_latency_ms`, `pop_ping_drop_rate`, `downlink/uplink_throughput_bps`) que
  no se usa en ningún test real. Se actualizó al esquema real de `schema.py`
  (`node_id`, `metrics.latency_ms`/`jitter_ms`/`packet_loss_pct`/
  `throughput_down_up_bps`/`snr_db`/`is_obstructed`/`satellite_count`).

- **Drift de nomenclatura de tópicos MQTT (ADR-04 vs. resto)**: la tabla de tópicos de
  ADR-04 usaba `nodo/lit-01/net_health/starlink_grpc` / `nodo/lit-01/meteo/bme280_*`,
  mientras que `docs/03_SRS.md` (IF-01/02/03, RF-17), `docs/06_DER.md` y
  `docs/08_Plan_QA.md` ya usaban consistentemente `starlink/metrics/<node_id>` /
  `meteo/sensor/<node_id>` / `meteo/external/<node_id>`. Se corrigió ADR-04 para
  alinearlo con los otros tres documentos (eran 4 contra 1). También se unificaron los
  tópicos separados de BME280 real/mock en uno solo, consistente con la exigencia de
  ADR-01 de que mock y hardware real sean intercambiables 1:1. El tópico de
  `system_status/#` se renombró a `system/status/<node_id>` (mismo estilo domain-first)
  y se definió el mensaje LWT concreto (payload JSON, retain=true, QoS 1) en ADR-03.

- **Puntos abiertos de ADR-01 a ADR-05 cerrados con Aldana** ([^c0], [^c1], [^c2],
  [^c3], [^c4], [^c6] — ver sección "Resueltos" en `docs/05_ADR.md` → Comments):
  framing de Pydantic como Anti-Corruption Layer (ADR-01), aclaración de que el dict
  Python intermedio no es un formato de serialización (ADR-01), justificación de
  interfaces integradas del BME280 (ADR-02), parámetros de backoff exponencial del
  ESP32 (ADR-03), mensaje LWT concreto (ADR-03), y título de ADR-05 renombrado a
  "Selección de Lenguajes y Paradigma de Programación". Quedan pendientes en ADR-06 en
  adelante ([^c5], [^c7]–[^c14]), fuera del alcance de semana 2-3.

- **Imagen Docker de Mosquitto corregida**: `eclipse-mosquitto:2.0-alpine` (citada en
  ADR-09) no existe en Docker Hub — se corrigió a `eclipse-mosquitto:2.0.18` (misma
  familia alpine-based, ~22 MB), verificado con `docker pull` real.

- **Drift de nomenclatura `TIME_WARP_FACTOR` vs. `SIMULATION_SPEED_FACTOR`**: el
  párrafo de Decisión de ADR-08 y una tabla de `CLAUDE.md` usaban
  `SIMULATION_SPEED_FACTOR`, mientras que el título/índice de ADR-08 y otros 3
  documentos (`CLAUDE.md` ×2, `docs/08_Plan_QA.md`, este archivo) ya usaban
  `TIME_WARP_FACTOR`. Se corrigieron las 2 menciones sueltas para que gane
  `TIME_WARP_FACTOR` (3 documentos contra 1).

- **Drift de valores de `CHAOS_PROFILE`**: ADR-06 y `CLAUDE.md` usan
  `CALM/STORM/HANDOVER_HEAVY`; la tabla de variables de entorno de
  `docs/08_Plan_QA.md` usaba `NORMAL/STORM/OUTAGE`. Se corrigió esa tabla para que
  coincida con el ADR (gana por prioridad de `CLAUDE.md` §2: el ADR pesa más que el
  Plan de QA).

- **Resto de semana 3 + semana 4 + semana 5 implementadas** (`src/mock_starlink/mock.py`,
  `__main__.py`, `Dockerfile`, servicio `mock_starlink` en `docker-compose.yml`,
  `tests/test_mock.py` + `tests/test_main.py`): mock stateful con random walk e
  inyección de caos (ADR-06), publisher MQTT con LWT (ADR-03/09), `TIME_WARP_FACTOR`
  (ADR-08), empaquetado Docker (ADR-07). 67/67 tests, `mock.py` al 100% de cobertura;
  `__main__.py` parcialmente cubierto por unit tests (la lógica de conexión MQTT se
  probó manualmente contra un broker real, no con mocks de `paho-mqtt` — no se justificó
  la complejidad extra para esta etapa). Verificado end-to-end: `docker compose
  --profile mocks up --build`, payloads válidos en `starlink/metrics/<node_id>`, LWT
  online/offline en `system/status/<node_id>` (`docker kill` para forzar el offline).

- **Vocabulario de ADR-06 traducido al DER en la implementación**: `mock.py` genera
  `throughput_down/up_bps`, `is_obstructed` (umbral sobre un `obstruction_pct` interno
  no publicado, >10%) y `snr_db`, no el vocabulario Mbps/`obstruction_pct`/
  `signal_quality` de la tabla estadística de ADR-06/SRS — mismo criterio que ya se
  usa en el resto del proyecto (seguir al DER/`schema.py`). Ver nota nueva en
  "Pendiente — revisar con director/co-director".

- **Parámetros de `CHAOS_PROFILE` por perfil, sin especificar en ningún documento**:
  ADR-06 describe el mecanismo general de "evento de anomalía" pero no lo separa por
  perfil. Se calibró una tabla propia (documentada en el docstring de `mock.py`) para
  que `STORM` cumpla el umbral literal de UT-04-02 (`docs/08_Plan_QA.md`: ≥15% de
  spikes >150ms en 1000 muestras) — verificado con datos reales de la suite de tests
  (~20-22% en las corridas locales, con margen sobre el mínimo exigido).

---

## Coordinación pendiente con Fede

- **`MeteoDB` (`src/consumer/db.py`) es un stub, no una implementación real** —
  `ConsumerRouter` ya enruta `meteo/sensor/<node_id>` y `meteo/external/<node_id>`
  hacia ella (semana 6), pero solo loguea un WARNING y descarta el mensaje sin
  persistir. Cuando Fede tenga su mock/tópico meteo, hace falta reemplazar el
  stub por un gateway real a `meteo_db` (mismo patrón que `NetHealthDB`, ORM
  SQLAlchemy declarativo sobre el esquema `env_metrics` de `docs/06_DER.md`
  §3.3) — coordinar con él si prefiere escribirlo él mismo dado que es su
  dominio, o si conviene que yo lo arme siguiendo el mismo patrón que
  `NetworkMetric`.
- **`POST /ingest/env` y `EnvPayloadIn` (`docs/07_API_REST.md` §9.2) tienen el mismo
  patrón `station_id`/`source_module` que se acaba de corregir del lado Starlink** —
  no se tocó porque es su esquema (BME280/ambiental), pero probablemente valga la pena
  que lo revise contra lo que realmente vaya a implementar, antes de que alguien copie
  ese modelo Pydantic tal cual a la semana 9.
- **Modelo de repos decidido: polyrepo + docker-compose.** Cada uno mantiene su propio
  repo (individualmente evaluable para la materia). Cada mock se publica como imagen
  Docker propia (GitHub Container Registry, gratis en repos públicos/con cuenta
  personal). Un `docker-compose.yml` de integración referencia ambas imágenes por tag —
  encaja con ADR-07/ADR-10 (microservicios y DBs ya son independientes por diseño). Fede
  todavía no tiene su repo creado ni publica imagen — coordinar antes de que el
  `docker-compose.yml` de este repo intente referenciar la suya.
- **Confirmar con Fede la nomenclatura de tópicos corregida**: `meteo/sensor/<node_id>`
  para BME280 (real y mock, mismo tópico) y `system/status/<node_id>` para LWT/heartbeats
  — él todavía no vio ni confirmó este cambio.
- **Confirmar con Fede los valores por default que se completaron en ADR-02/ADR-03**
  (ver "Puntos abiertos... cerrados con Aldana" arriba): backoff exponencial del ESP32 y
  formato del mensaje LWT. Son parte de su firmware — necesitan su OK antes de darlos
  por definitivos.
- **Publicar `mock-starlink` a GHCR antes de la integración real de semana 6** — hoy
  `docker-compose.yml` lo construye local (`build:`), consistente con el modelo
  polyrepo pero todavía no publicado. No se armó CI/publicación automática en este
  tramo (es semana 11-12 del roadmap) — publicar a mano cuando haga falta.
- **Decidir si el `docker-compose.yml` de integración (broker + ambos mocks) se queda
  en este repo o se muda a un repo neutral** una vez que Fede tenga el suyo — por ahora
  vive acá porque fue lo que hubo que levantar primero.

---

## Semana 1 — Carpeta mock_starlink + esquema + tests `[IND]` ✅ COMPLETA

- [x] Crear la carpeta `src/mock_starlink/`
- [x] Estudiar el endpoint gRPC nativo de la antena (Dishy) en `192.168.100.1:9200` y el repo `starlink-grpc-tools`
- [x] Definir el esquema JSON del paquete de telemetría (ADR-01): `latency_ms`, `jitter_ms`, `packet_loss_pct`, `throughput_down/up_bps`, `snr_db`, `is_obstructed`, `satellite_count`
- [x] Escribir el validador Pydantic (`StarlinkPayloadIn`) sobre ese esquema
- [x] Escribir los primeros tests unitarios que validan el esquema (suite UT-01)

## Semana 2 — Tests unitarios + arquitectura de contratos `[IND]→[INT]`

- [x] Ampliar la suite UT-01: 1000 payloads generados sin `ValidationError`
- [x] Cubrir casos límite: campos nulos, `packet_loss_pct` fuera de rango, `schema_version` incorrecto
- [x] Instalar y configurar entorno Python 3.11 (venv, grpcio, pydantic) — ver nota
      sobre 3.11 vs. 3.13 en `README.md` §Requisitos
- [ ] Empezar, junto a Fede, la definición de arquitectura y contratos (ADR-01 a ADR-05)
      — pendiente, requiere coordinar con Fede (punto de corte de este avance individual)

**Hallazgos y correcciones durante esta etapa** (detectados al retomar el trabajo, no
parte del roadmap original, pero bloqueaban lo demás):

- `src/mock-starlink/` tenía guion medio; todo el resto del repo ya esperaba guion bajo
  (`mock_starlink`), por lo que la suite de tests ni se podía importar. Corregido
  (rename).
- `StarlinkMetrics` exigía como obligatorios varios campos que `docs/06_DER.md` ya
  marca `NULL='S'` (telemetría degradada: ping sin respuesta, API interna de la antena
  no accesible). Corregido — ver sección "Pendiente" más abajo por el drift de SRS que
  quedó sin resolver en el proceso.
- Se agregó la skill de proyecto `adr-check` (`.claude/skills/adr-check/`) + hook de
  enforcement (`.claude/settings.json`) para detectar este tipo de drift automáticamente
  a futuro, antes de que se acumule.

## Semana 3 — Docker + broker MQTT `[INT — primera integración con Fede]`

- [x] Levantar Eclipse Mosquitto (MQTT v5.0) vía Docker Compose (ADR-09, ADR-12) — hecho
      individualmente (`docker-compose.yml` + `services/broker/mosquitto.conf`),
      verificado con `docker compose up` + pub/sub manual; falta correrlo junto con Fede
- [x] Definir el topic de publicación para métricas Starlink — `starlink/metrics/<node_id>`
      (ADR-04 corregido para coincidir con SRS/DER/Plan QA, ver "Corregido esta sesión")
- [x] Modificar el script/mock para publicar el JSON al broker en vez de imprimir por consola —
      `src/mock_starlink/__main__.py`, cliente `paho-mqtt` con LWT y reconexión automática
- [x] Verificar mensajes con `mosquitto_sub` — hecho a mano contra un broker real
      (`docker compose --profile mocks up --build`), payloads y LWT (online/offline vía
      `docker kill`) confirmados
- [ ] Confirmar, junto con Fede, que ambos mocks publican y los datos llegan al broker —
      pendiente de que él tenga su parte lista

> 🔗 Milestone: primera vez que los dos módulos comparten el broker.

## Semana 4 — Mock de telemetría Starlink (stateful) `[IND]` ✅ COMPLETA

- [x] Implementar el Mock Stateful con Random Walk (ADR-06) en vez de números aleatorios puros —
      `src/mock_starlink/mock.py`, `StarlinkMockAgent.generate_payload()`
- [x] Agregar inyección de caos: obstrucciones, handovers, microcortes de conectividad —
      `CHAOS_PROFILE` (`CALM`/`STORM`/`HANDOVER_HEAVY`), ver tabla de parámetros por perfil
      en el docstring de `mock.py` (no especificada por ADR-06 a nivel de perfil, calibrada
      para satisfacer UT-04-02 de `docs/08_Plan_QA.md`: STORM ≥15% de spikes >150ms)
- [x] Empaquetar el mock como microservicio Docker independiente (ADR-07) — `Dockerfile`
      (`python:3.11-slim`, multi-arch) + servicio `mock_starlink` en `docker-compose.yml`,
      imagen `mock-starlink:dev` (nombrada para publicar a GHCR más adelante sin rename)
- [x] Publicar continuamente al broker respetando el esquema de semana 1 — validado con
      `StarlinkPayloadIn` en tests (0 errores en 1000+ payloads por perfil)

## Semana 5 — Mock Starlink (cont.) + preparación del consumer `[IND]` ✅ COMPLETA (con una salvedad)

- [x] Agregar el parámetro `TIME_WARP_FACTOR` al mock (ADR-08) para backfill acelerado —
      `time_warp_factor` en el constructor de `StarlinkMockAgent`; con `factor > 1` arranca
      el reloj simulado 30 días atrás (ejemplo de ADR-08) y avanza 60s simulados por tick,
      clampeado para nunca superar el "no future timestamp" del validador de `schema.py`
- [x] Dejar el mock corriendo de forma estable como base para el consumer conjunto — corre
      indefinidamente, reconexión automática al broker, no se cae ante errores de publish
- [ ] ⚠️ Ajustar frecuencia de muestreo para que sea coherente con lo que espera TimescaleDB —
      **parcial**: el mecanismo (`interval_s = 60/time_warp_factor`) está implementado y
      probado en aislamiento, pero no se puede validar contra un consumer/TimescaleDB reales
      todavía (no existen hasta semana 6-7). No se sobre-afirma como "tuneado" — retomar en
      semana 7 (índices) o semana 21 (stress test) con la DB real ya levantada.

## Semana 6 — Consumer MQTT conjunto `[INT — segunda integración con Fede]` — Starlink [IND] ✅, meteo pendiente de Fede

- [ ] ~~Diseñar junto a Fede el consumer que escucha ambos topics~~ — Fede todavía no
      arrancó su módulo (ver `docs/PROGRESS.md` arriba); se construyó solo con
      código, sin bloquear en una sesión de diseño conjunto que no podía pasar
      todavía. El router (`src/consumer/router.py:ConsumerRouter`) ya está
      preparado para el dominio meteo (`meteo/sensor/`, `meteo/external/`) —
      cuando Fede tenga su tópico, falta reemplazar `MeteoDB` (stub) por una
      implementación real, no rediseñar el routing.
- [x] Implementar Database per Service (ADR-10): `starlink_health_db` levantada
      (`starlink_db` en `docker-compose.yml`) — `meteo_db` queda para Fede.
- [x] Insertar métricas Starlink en la hypertable `network_metrics`
- [x] Manejar errores de deserialización sin tumbar el consumer (`ValidationError`
      de Pydantic se loguea y descarta; error de DB no propaga, retiene el ACK)
- [x] Probar el flujo end-to-end: mock → broker → consumer → TimescaleDB (verificado
      a mano con `docker compose --profile mocks up --build`, incluida reentrega
      QoS 1 con el consumer caído)

> 🔗 Milestone: dominio Starlink integrado end-to-end con persistencia real. La
> "segunda integración con Fede" propiamente dicha (escuchar su tópico real, no
> solo tenerlo enrutado) queda pendiente de que él tenga su mock/tópico meteo.

## Semana 7 — Validación en TimescaleDB `[IND]` ✅ COMPLETA

- [x] Crear los índices de `network_metrics` (`idx_netmet_node_time`, `idx_netmet_loss`,
      `idx_netmet_obstructed`) — ya los crea `services/db/init_starlink_health.sql`
      desde semana 6.
- [x] Probar consultas filtradas por `node_id` y rango temporal — `EXPLAIN ANALYZE`
      contra ~2500 filas backfillate (`TIME_WARP_FACTOR=3600` real, no INSERT SQL
      directo, ADR-08). `idx_netmet_loss` e `idx_netmet_obstructed` se usan siempre
      (Index Scan confirmado). `idx_netmet_node_time` se usa con ventanas temporales
      angostas; con una ventana amplia y un solo nodo el planner elige Seq Scan
      porque casi todas las filas matchean (selectividad ~100% con un solo nodo) —
      comportamiento correcto de Postgres, no un bug. El índice va a ganar
      relevancia real recién con más de un nodo (el "modo comparativo" que el
      propio DER cita como motivo del índice).
- [x] Verificar que `packet_loss_pct` respeta el CHECK constraint (0–100) — probado
      con INSERT directo (150 y throughput_down_bps=-100), ambos rechazados con
      `chk_netmet_loss`/`chk_netmet_down`; INSERT válido de control aceptado.
- [x] Confirmar que `node_id` coincide entre el payload MQTT y `station_metadata` —
      creada `station_config_db` (ver "Corregido esta sesión": ADR-10 tenía un
      conflicto con el DER sobre cuántas instancias de DB hay). `station_metadata`
      seedeada con `lit-cordoba-01`; confirmado que todo `node_id` presente en
      `network_metrics` está registrado ahí (sin huérfanos).

## Semana 8 — Dashboard Grafana `[IND]` ✅ COMPLETA

- [x] Conectar Grafana a `starlink_health_db` — `services/grafana/provisioning/datasources/starlink.yml`,
      datasource provisionado automáticamente al arrancar, `health check` = "Database
      Connection OK" verificado vía API real.
- [x] Armar panel de `latency_ms`, `jitter_ms` y `packet_loss_pct` en el tiempo —
      2 paneles (latencia+jitter juntos por unidad compartida "ms"; packet loss
      aparte por ser porcentaje).
- [x] Armar panel de `throughput_down/up_bps` (convertido a Mbps) — conversión
      `/1000000.0` en la query SQL del panel.
- [x] Agregar panel de `satellite_count` e `is_obstructed` para correlacionar
      eventos — panel único, `is_obstructed::int` superpuesto a `satellite_count`.
      Bonus fuera del checklist original pero ya nombrado en la taxonomía de
      dashboards de ADR-13 para "Red Starlink": histograma de distribución de
      latencia.
      Dashboard `services/grafana/dashboards/red_starlink.json`, con variable de
      plantilla `node_id` (multi-select, para cuando haya más de un nodo).
      Verificado con datos reales vía `/api/ds/query` (no pude abrir un browser en
      este entorno, pero confirmé que las queries devuelven series reales con
      valores correctos — latency_ms/jitter_ms multi-serie desde una sola query SQL).

## Semana 9 — Backend FastAPI + logging estructurado `[INT — logging antes del hardware real]`

- [ ] Implementar `GET /api/v1/metrics/starlink`, `/summary` y `/latest`
- [ ] Asegurar autenticación por API Key en header `X-API-Key`
- [ ] Agregar logging estructurado (JSON logs) al script extractor, al consumer y al backend
- [ ] Loguear errores de conexión al broker y fallos de validación Pydantic con contexto (`node_id`, `timestamp`)

## Semana 10 — Pasaje a hardware real (RPi5) `[HW]`

- [ ] Confirmar disponibilidad de antena, RPi5 y tarjeta de memoria
- [ ] Reemplazar el mock por la conexión real al gRPC de la antena (`192.168.100.1:9200`)
- [ ] Correr el script extractor sobre el Raspberry Pi 5 real
- [ ] Validar el flujo completo end-to-end con hardware físico
- [ ] Confirmar con Fede que ambos módulos funcionan simultáneamente sobre el RPi5

> 🔗 Milestone: fin del desarrollo desacoplado del hardware.

## Semanas 11–12 — Suite de testing + CI `[IND]`

- [ ] Escribir/completar suites de integración (IT-01): mock → broker → consumer → DB
- [ ] Configurar `pytest-cov` con `--cov-fail-under=80` en tus módulos
- [ ] Dejar el pipeline de GitHub Actions corriendo en cada push

## Semanas 13–14 — Soporte a integración de APIs externas `[INT — Fede lidera]`

- [ ] Revisar que las fuentes meteorológicas externas no rompan el esquema del consumer compartido
- [ ] Ajustar si hace falta la routing logic de tópicos MQTT para la nueva fuente

## Semanas 15–16 — Resiliencia, seguridad y Continuous Aggregates `[IND]+[INT]`

- [ ] Configurar Continuous Aggregates en TimescaleDB para acelerar consultas largas de Grafana
- [ ] Sumar manejo de caídas del broker (reconexión automática) en tu script extractor
- [ ] Colaborar en la postura Zero Trust (ADR-14): solo Grafana expuesto, filtrado de IP

## Semanas 17–18 — Frontend / videomonitoreo (opcional) `[INT]`

- [ ] Colaborar en el microservicio de streaming (mock Flask/MJPEG → cámara real)
- [ ] Verificar que no compita por ancho de banda con las mediciones de red

## Semanas 19–20 — Integración completa del sistema (E2E) `[INT]`

- [ ] Correr la suite E2E completa sobre la pila Docker de producción
- [ ] Validar los Criterios de Aceptación relacionados a tu módulo (CA-01, CA-08)
- [ ] Verificar coherencia total: paquete MQTT Starlink == esquema DER

> 🔗 Milestone: sistema completo integrado, mock y real, corriendo end-to-end.

## Semana 21 — Pruebas de estrés (TIME_WARP + Locust) `[INT]`

- [ ] Ejecutar pruebas de estrés sobre el pipeline de red con Locust
- [ ] Medir throughput máximo sostenible en el RPi5 sin pérdida de datos de red

## Semana 22 — Campaña inicial de medición `[INT]`

- [ ] Dejar corriendo el sistema real varios días para recolectar datos de red
- [ ] Primer análisis exploratorio: latencia/jitter/pérdida vs condiciones ambientales

## Semana 23 — Redacción de memoria y documentación `[IND]`

- [ ] Documentar tu módulo: arquitectura, decisiones (ADRs relacionados a Starlink), procedimiento de despliegue
- [ ] Aportar figuras/gráficos de tus dashboards para la memoria técnica

## Semana 24 — Revisión final y cierre `[INT]`

- [ ] Completar tu parte de la checklist de QA de entrega final
- [ ] Correcciones finales sobre tu módulo según feedback del director/co-director

> 🔗 Milestone: cierre del Proyecto Integrador.
