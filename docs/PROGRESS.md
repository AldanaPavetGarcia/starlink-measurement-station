# PROGRESS.md — Módulo Starlink (Aldana)

> Estado de avance real del módulo de conexión a la antena Starlink, alineado al roadmap de
> `CLAUDE.md` §1.1. Editar a mano o pedirle a Claude Code que lo actualice al cerrar una tarea.
> Convención: **[IND]** trabajo individual · **[INT]** integración con el módulo de Fede ·
> **[HW]** requiere hardware real.

**Última actualización:** semanas 1 a 21 tocadas del lado Starlink, con distinto
grado de cierre — ver el detalle semana por semana más abajo, esto es solo el
resumen ejecutivo. **Completas de punta a punta (código + tests + docs):**
semanas 1-9, 11-12, 15-16. **Con código escrito pero sin validar contra hardware
o Docker real** (sin acceso presencial al LIT ni espacio en disco suficiente en
esta sesión): semana 10 (extractor real), semana 21 (stress). **Bloqueadas por
Fede** (dominio meteo): partes de semanas 6, 13-14, 19-20. Semanas 22 y 24
directamente no tienen sentido todavía (requieren días de datos reales /
feedback del director, respectivamente).

Resumen por bloque de trabajo:
- **Semanas 1-8** (sesiones previas): mock stateful, broker, consumer,
  `starlink_health_db` + `station_config_db`, dashboard Grafana "Red Starlink".
- **Semana 9** (esta sesión): backend FastAPI completo (`GET /health`,
  `/metrics/starlink*`, `/nodes*`, `POST /ingest/starlink`) + `src/common/`
  (logging/MQTT compartidos, saca la duplicación entre mock y consumer).
- **Esquema v1.1** (sesión de relevamiento 04-06/8 + esta sesión): se cerraron
  las tres decisiones que habían quedado pendientes tras relevar la antena real
  del LIT — ADR-17 (`snr_db`→`snr_low`), ADR-16 (`handover_count`/
  `outage_duration_ms`), ADR-18 (`alignmentStats`, pedido del director). Primer
  bump de `SCHEMA_VERSION` del proyecto (1.0→1.1) — ver §Semana 10 para el
  detalle completo del relevamiento y "Pendiente — revisar con director" abajo.
- **Semana 10** (esta sesión, parcial): extractor real `src/acquisition/`
  escrito (vía `grpcurl`, enmienda a ADR-01) con su lógica de mapeo testeada
  contra JSON sintético — **sin validar contra la antena real**, pendiente de
  la próxima visita presencial.
- **Semanas 11-12** (esta sesión): suite de integración IT-01 automatizada,
  `pytest.ini`/`.coveragerc` (80% mínimo, 94.78% real), CI en GitHub Actions
  (`ci.yml` + `publish.yml` a GHCR).
- **Semanas 15-16** (esta sesión): corregido un hallazgo real de ADR-14 (el
  backend se había publicado solo en localhost sin cruzar la tabla de
  exposición de puertos que ya decía que debía ser accesible desde la
  intranet), mecanismo concreto de filtrado de IP documentado.
- **Semana 19-20/CA-08** (esta sesión): coherencia MQTT↔DER automatizada con
  tests (sin Docker), CA-01/CA-02 con herramientas listas para la próxima
  sesión con hardware/Docker real.
- **Semana 21** (esta sesión, sin ejecutar): `locustfile.py` de estrés escrito,
  necesita `TIME_WARP_FACTOR` alto + RPi5 real para que el resultado cuente.

180/180 tests pasando, 94.78% de cobertura (`.coveragerc` excluye los loops de
conexión MQTT de los `__main__.py`, validados con Docker real en vez de
mockeados). **Nada de esto se verificó contra Docker real en esta sesión** por
espacio en disco de la máquina compartida (2.6GB libres al momento de decidir
saltear esa verificación) — es el pendiente más importante para la próxima
sesión, junto con la visita presencial al LIT para el extractor real.

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
Próximo corte real: **semanas 11-12**, suites de integración automatizadas
(IT-01) + CI en GitHub Actions — hoy IT-01 sigue verificada a mano. El resto
de semanas 11-24 del roadmap siguen esperando, en su mayoría, a que Fede tenga
su mock/tópico meteo andando (`MeteoDB` real) o a hardware real presencial en
el LIT (semana 10, extractor `src/acquisition/` — mapeo campo a campo ya
documentado en §Semana 10, implementación pendiente de la próxima visita).

---

## Pendiente — revisar con director/co-director

**Nota 19/08/2026 — intento de pasar el Estado de los 18 ADR a "Aceptado":** según
Pavet García, el director (Henn) ya había dado por aprobados los 18 ADR de palabra en
una instancia presencial previa al inicio del repo (~27/06/2026). Se intentó reflejar
eso en `docs/05_ADR.md` (Estado: Propuesto → Aceptado) pero el hook de enforcement de
`adr-check` lo bloqueó: esa skill exige explícitamente que el campo Estado a "Aceptado"
lo escriba/confirme el director sobre el propio documento, no que se infiera de un
relato en el commit — sin importar que la aprobación verbal haya sido real. Se revirtió
y **los 18 ADR siguen en "Propuesto"** en `docs/05_ADR.md`. Queda como constancia
informal acá, pendiente de que el director lo confirme por escrito (email, comentario en
el doc, o editándolo él mismo) para poder aplicar el cambio.

Los siguientes puntos nuevos de esta sesión son candidatos concretos a confirmar aparte,
no solo formalidad:

- **ADR-17 (`snr_db`→`snr_low`) y bump de `SCHEMA_VERSION` a 1.1**: es el primer
  cambio de tipo incompatible del esquema del proyecto. Vale la pena que el
  director sepa que existe un payload "viejo" (v1.0) que el sistema ya rechaza
  explícitamente, por si hay algo externo (otro nodo del testbed, un script de
  otra sesión) que todavía lo genere.
- **ADR-18 (`alignmentStats`)**: implementa el pedido explícito del director de
  la sesión del 04/08 (procesar tilt/azimuth/elevación) — confirmar que los 6
  campos elegidos (se descartó `attitudeEstimationState`, ver ADR-18) cubren lo
  que tenía en mente, antes de considerar el pedido cerrado.
- **Enmienda de ADR-01 (extracción real vía `grpcurl`, no `grpcio`+
  `starlink-grpc-tools`)**: cambia el mecanismo técnico que `CLAUDE.md` §1.1
  describía explícitamente. No cambia la decisión de fondo (Protobuf→dict→
  Pydantic→JSON) pero es la clase de cambio que CLAUDE.md pide marcar, no
  pisar en silencio — ver ADR-01 en `docs/05_ADR.md`, sección "Enmienda".
- **Enmienda de ADR-14 (backend expuesto a la intranet del LIT, no solo
  localhost) + mecanismo de filtrado de IP (`ufw`)**: la tabla de exposición de
  puertos ya lo decía, pero el mecanismo concreto de filtrado nunca estaba
  especificado — confirmar que `ufw`/firewall del host es aceptable o si el
  director prefiere otro mecanismo (ej. VPN, reverse proxy con auth).

Ver "Coordinación pendiente con Fede" más abajo para los puntos que requieren
su confirmación en vez de la del director.

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

### Prueba en vivo — mock de Fede contra mi broker (14/8/2026, en el LIT)

Primera prueba real de la "Duda #1" resuelta el 11/8 en la práctica: Fede apuntó su
`MQTT_HOST` temporalmente (solo variable de entorno, sin tocar código, opción A ya
anotada abajo) a mi `mosquitto-broker` (levantado standalone en mi laptop,
`docker compose --profile mocks up -d broker`, `172.18.147.220:1883`, misma red del
LIT). **Confirmado con `mosquitto_sub`: sus mensajes llegan.** Payload en
`meteo/sensor/lit-cordoba-01` exactamente como documentado el 11/8 (`source` fijo
`"local_sensor"`, distinción real en `producer: "mock_bme280"`, `schema_version
"1.0"`, cada 60s, valores plausibles ~21°C/~62%HR/~1012hPa).

**Hallazgo nuevo, más grave que la nota que Fede ya tenía en su README sobre
`component`**: su mock y el mío publican al **mismo tópico exacto**
`system/status/<node_id>` porque los dos usan `node_id=lit-cordoba-01` para la misma
estación. No es solo que el valor de `component` difiera (`mock_bme280` vs.
`starlink_mock`/`sensor_gateway`) — es que con mensajes **retained**, el último que
publica pisa el retenido del otro módulo sin dejar rastro. Se vio en vivo: mi
retained `{"source":"starlink_mock","status":"offline"}` fue pisado por el
`online`/`offline` de su mock, en la misma sesión. Hoy, mirar
`system/status/lit-cordoba-01` no te dice el estado de "la estación" — te dice el
estado de *cualquiera de los dos módulos que haya publicado último*, indistinguible.

**Decidido con Fede el mismo día y ya implementado de mi lado**: separar el tópico
por dominio en vez de compartirlo plano, siguiendo el mismo esquema que ya usan los
tópicos de datos (`starlink/metrics/<node_id>` vs. `meteo/sensor/<node_id>`) —
`starlink/status/<node_id>` de mi lado, `meteo/status/<node_id>` del suyo. Resolver
solo el valor de `component`/`source` dentro del mismo tópico no alcanzaba (seguía
habiendo un único retained por tópico). Aplicado en `src/mock_starlink/__main__.py`,
`src/acquisition/__main__.py`, y documentado como enmienda en ADR-03/ADR-04
(`docs/05_ADR.md`) — ver detalle ahí. **Pendiente del lado de Fede**: actualizar su
`will_set()` de `system/status/<node_id>` a `meteo/status/<node_id>`.

### Semántica `source`/`producer` en `env_metrics` — decisión parcial (19/8/2026)

El mismatch anotado el 11/8 (`source` fijo `"local_sensor"` + `producer` distinguiendo
mock/real, sin calzar con el CHECK constraint de una sola columna) quedó sin cerrar
después de la prueba del 14/8 — nunca se escribió por ningún lado, aunque había una
conversación con Fede al respecto. Confirmado hoy el sentido de esa conversación:

- **`source`** = identidad puntual del componente que generó el dato (distingue
  mock de hardware real): `mock_bme280` / `esp32_bme280` / `mock_api` /
  `api_open_meteo` / `api_owm` / `api_smn`.
- **`producer`** = categoría del origen: `antenna` / `sensor` / `api`.

Esto invierte lo que hoy hace el código de Fede (`source: "local_sensor"` —
categoría, no identidad — y `producer: "mock_bme280"` — identidad, no categoría) y
tampoco coincide con el CHECK constraint actual de `env_metrics.source`
(`docs/06_DER.md`, una sola columna mezclando identidad y categoría) ni con
`EnvPayloadIn`/`EnvSource` (`docs/07_API_REST.md` §9.2, que además tiene un tercer
campo, `source_module`, a nivel de envelope — nunca llegó a tener columna propia en
el DER).

**Pendiente de resolver — no se tocó `docs/06_DER.md` ni `docs/07_API_REST.md`
todavía, queda para cuando se decida con Fede:**

1. **Dónde va `producer`**: ¿adentro de `metrics` (como ya lo tiene el código de
   Fede — menos cambios de su lado) o afuera, a nivel de envelope del mensaje (como
   `source_module` en el `EnvPayloadIn` ya escrito)?
2. **Qué hacer con `source_module`** (`docs/07_API_REST.md` §9.2, `POST /ingest/env`):
   ¿se renombra a `producer` y se alinea a esta decisión, o se trata como un diseño
   viejo/borrador a reemplazar directamente?
3. Lo que sí es seguro independientemente de 1 y 2: `env_metrics` necesita una
   columna `producer` nueva — hoy solo tiene `source` — y el CHECK constraint de
   `source` pasa a validar solo los 6 valores de identidad de arriba (no mezclar con
   categoría).

### Revisión del repo de Fede — `tesis-sensor-node` (11/8/2026)

Repo confirmado: `github.com/BlastNeos/tesis-sensor-node`, rama `development`, 3
commits (5/8 y 10/8/2026), sin CI, sin `docs/` versionados. Resuelve la Duda #1
que había quedado abierta en la sesión del 6/8 (ver memoria
`fede-integration-status`) y aporta datos concretos nuevos:

- **🔴 Duda #1 resuelta — su Mosquitto es una instancia propia y aislada**
  (`infrastructure/mosquitto/docker-compose.yml`, contenedor
  `tesis-mosquitto`), sin auth (`allow_anonymous true`, documentado como deuda
  temporal en su propio `mosquitto.conf`) y **no integrada al `docker-compose.yml`
  de este repo**. Confirmado: aunque el tópico esté bien, sus mensajes hoy **no
  llegan** a este consumer/broker compartidos. Hay que decidir juntos si su
  mock/firmware pasan a apuntar a este broker, o si se fusionan ambos compose
  (ver el punto de "repo neutral" más abajo, ya anotado antes de esta revisión).
- **Protocolo MQTT 3.1.1, no v5**: su cliente Python fija
  `mqtt.MQTTv311` a mano (`mocks/bme280/src/mqtt_publisher.py:17`) y la librería
  del firmware ESP32 (`256dpi/MQTT@2.5.3`) tampoco soporta v5 nativamente. ADR-09
  de este repo dice "Mosquitto v5.0" — si eso implica protocolo MQTT5 (no solo
  versión de software), hay un mismatch real a resolver antes de compartir broker.
- **Esquema del payload de `meteo/sensor/<node_id>` no calza 1:1 con
  `env_metrics.source`**: anida las métricas bajo `"metrics": {...}` (mismo
  patrón de diseño que `StarlinkPayloadIn`, buena señal de convergencia
  independiente), pero `source` siempre vale `"local_sensor"` fijo y quien
  distingue mock de hardware real es un campo separado `producer`
  (`mock_bme280` / `esp32_bme280`) — mientras que el enum de `source` ya
  documentado (`local_sensor`/`api_open_meteo`/`api_owm`/`api_smn`/
  `mock_bme280`/`mock_api`) espera que sea `source` mismo el que tome esos
  valores. `esp32_bme280` ni siquiera existe en ese enum. Hay que alinear esto
  en el ADR-01 de su lado (o en `EnvPayloadIn` cuando se escriba) antes de que
  `MeteoDB` intente mapear el campo equivocado.
- **Inconsistencia que Fede mismo dejó anotada como pregunta abierta en su
  README**: el campo `component` del mensaje de estado (LWT/heartbeat, hoy
  `meteo/status/<node_id>` de su lado — ver enmienda del 14/08 más abajo)
  difiere entre su mock (`mock_bme280`) y su firmware (`sensor_gateway`) —
  riesgo real de que se pisen el mensaje retained si corren simultáneo con el
  mismo `node_id`. **Sigue sin resolver incluso después de la enmienda del
  14/08** — esa enmienda separó el tópico por dominio (Starlink vs. meteo),
  no el choque mock-vs-firmware *dentro* del propio dominio de Fede, que es
  un problema distinto y todavía suyo por cerrar.
- **Su firmware ESP32 es un esqueleto sin validar contra hardware**
  (`firmware/esp32-bme280/`, WiFi/MQTT/NTP/sensor con backoff, estructuralmente
  completo) — su propio `test/README.md` admite "0 tests, ni siquiera de
  integración todavía". No bloquea empezar a integrar el mock (que sí
  funciona, dockerizado, 4 tests propios), pero si la idea es probar hardware
  real de los dos módulos juntos en el RPi5 (semana 10), el suyo está más
  atrás que el mío en ese frente específico.
- **No usa Pydantic ni logging estructurado** (solo `print()`/`dataclasses`,
  contradice la convención que se había acordado) — vale la pena mencionárselo
  antes de que escriba `EnvPayloadIn`/el consumer de su lado, no para
  imponerlo unilateralmente sino para que la decisión sea consciente.
- Su repo **sí existe** ahora (actualiza el punto de abajo, "modelo de repos")
  pero **no publica imagen a GHCR todavía** (sin CI configurado de su lado).

- **`MeteoDB` (`src/consumer/db.py`) es un stub, no una implementación real** —
  `ConsumerRouter` ya enruta `meteo/sensor/<node_id>` y `meteo/external/<node_id>`
  hacia ella (semana 6), pero solo loguea un WARNING y descarta el mensaje sin
  persistir. Cuando Fede tenga su mock/tópico meteo, hace falta reemplazar el
  stub por un gateway real a `meteo_db` (mismo patrón que `NetHealthDB`, ORM
  SQLAlchemy declarativo sobre el esquema `env_metrics` de `docs/06_DER.md`
  §3.3) — coordinar con él si prefiere escribirlo él mismo dado que es su
  dominio, o si conviene que yo lo arme siguiendo el mismo patrón que
  `NetworkMetric`. **Referencia concreta del payload real (revisión 11/8, ver
  arriba)**: `{node_id, timestamp, source, producer, schema_version, metrics:
  {temperature_c, humidity_pct, pressure_hpa, sensor_uid}}` — antes de escribir
  el mapeo, resolver primero el mismatch `source`/`producer` señalado arriba,
  para no construir `starlink_row`-equivalente sobre un campo que va a cambiar.
- **`POST /ingest/env` y `EnvPayloadIn` (`docs/07_API_REST.md` §9.2) tienen el mismo
  patrón `station_id`/`source_module` que se acaba de corregir del lado Starlink** —
  no se tocó porque es su esquema (BME280/ambiental), pero probablemente valga la pena
  que lo revise contra lo que realmente vaya a implementar, antes de que alguien copie
  ese modelo Pydantic tal cual a la semana 9.
- **Modelo de repos decidido: polyrepo + docker-compose.** Cada uno mantiene su propio
  repo (individualmente evaluable para la materia). Cada mock se publica como imagen
  Docker propia (GitHub Container Registry, gratis en repos públicos/con cuenta
  personal). Un `docker-compose.yml` de integración referencia ambas imágenes por tag —
  encaja con ADR-07/ADR-10 (microservicios y DBs ya son independientes por diseño).
  **Actualizado 11/8**: Fede ya tiene su repo (`github.com/BlastNeos/tesis-sensor-node`),
  pero todavía no publica imagen a GHCR (sin CI configurado de su lado) — coordinar
  antes de que el `docker-compose.yml` de este repo intente referenciar la suya.
- **Nomenclatura de tópicos**: `meteo/sensor/<node_id>` para BME280 (real y mock,
  mismo tópico). **Confirmado independientemente el 11/8** al revisar su repo — su
  mock y su firmware ya usan exactamente este nombre (`mocks/bme280/src/config.py`,
  `firmware/esp32-bme280/include/AppConfig.h`), sin haber visto este documento. El
  problema real que queda es que su broker es una instancia aislada (ver "Duda #1
  resuelta" arriba), no el nombre del tópico de métricas.
  **Actualización 14/8**: el tópico de LWT/heartbeats **cambió** — era
  `system/status/<node_id>` (único, compartido), pasó a `starlink/status/<node_id>`
  de mi lado / `meteo/status/<node_id>` del lado de Fede (enmienda ADR-03/ADR-04, ver
  arriba). Su mock/firmware todavía publican en el tópico viejo `system/status/<node_id>`
  — falta que actualice su `will_set()` al nuevo `meteo/status/<node_id>` de su lado.
- **Confirmar con Fede los valores por default que se completaron en ADR-02/ADR-03**
  (ver "Puntos abiertos... cerrados con Aldana" arriba): backoff exponencial del ESP32 y
  formato del mensaje LWT. Son parte de su firmware — necesitan su OK antes de darlos
  por definitivos.
- **Publicar `mock-starlink` a GHCR antes de la integración real de semana 6** —
  **cerrado del lado de la automatización**: `.github/workflows/publish.yml`
  (semana 11-12) hace build+push automático a GHCR en cada push a `main`
  (4 imágenes: `mock-starlink`, `starlink-consumer`, `starlink-backend`,
  `starlink-acquisition`). `docker-compose.yml` sigue usando `build:` local
  igual que antes (no referencia las imágenes de GHCR) — no se cambió porque
  eso sí depende de coordinar con Fede si el compose de integración va a vivir
  acá o en un repo neutral (ver punto siguiente). El workflow en sí no corrió
  todavía contra GitHub real (no hubo push a un remoto en esta sesión).
- **Decidir si el `docker-compose.yml` de integración (broker + ambos mocks) se queda
  en este repo o se muda a un repo neutral** una vez que Fede tenga el suyo — por ahora
  vive acá porque fue lo que hubo que levantar primero. Ahora son 4 servicios propios
  (`mock_starlink`/`acquisition`, `consumer`, `backend`) más `starlink_db`/
  `station_config_db`/`grafana` — cuanto más tiempo pase, más costoso migrar el compose
  a un repo neutral sin romper nada; vale la pena decidirlo pronto si la idea sigue en pie.
- **`GET /health` del backend (semana 9) reporta `db_meteo_data: not_configured`**
  (`src/backend/routers/health.py`) en vez de intentar conectarse a una `meteo_db`
  que todavía no existe — es una extensión del enum de estados que
  `docs/07_API_REST.md` no documenta (`up`/`down`/`degraded` son los únicos
  valores oficiales). Cuando Fede tenga `meteo_db` real, esto pasa a ser
  `up`/`down` normal — avisar si prefiere que el estado provisorio se llame
  distinto mientras tanto.
- **`/metrics/env*` y `POST /ingest/env` no están montados en el backend
  todavía** (`src/backend/__init__.py` lo documenta explícitamente) — cuando
  Fede tenga su esquema `env_metrics` real, falta escribir esos routers
  siguiendo el mismo patrón que `metrics_starlink.py`/`ingest.py` (reusar
  `EnvPayloadIn` si él lo define con Pydantic, mismo criterio que
  `POST /ingest/starlink` reusando `StarlinkPayloadIn`).

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

## Semana 9 — Backend FastAPI + logging estructurado `[INT — logging antes del hardware real]` ✅ COMPLETA (lado Starlink)

- [x] Implementar `GET /api/v1/metrics/starlink`, `/summary` y `/latest` —
      `src/backend/routers/metrics_starlink.py`, resolución automática
      raw/hourly/daily sobre `network_metrics`/`net_hourly`/`net_daily`
      (docs/07_API_REST.md), paginación por cursor temporal. También
      `GET /nodes`, `/nodes/{node_id}` (`routers/nodes.py`, join en Python
      entre `starlink_health_db` y `station_config_db` — Database per
      Service, ADR-10, no hay JOIN SQL cruzado entre bases) y
      `POST /ingest/starlink` (`routers/ingest.py`, detrás de
      `ENABLE_INGEST_ENDPOINT`, reusa `StarlinkPayloadIn`/`NetHealthDB`/
      `starlink_row` del consumer en vez de duplicar validación/INSERT).
      **No se montan** `/metrics/env*` ni `POST /ingest/env` (dominio de
      Fede) — `GET /health` reporta `db_meteo_data: not_configured` en vez
      de fallar o inventar un estado falso.
- [x] Asegurar autenticación por API Key en header `X-API-Key` —
      `src/backend/security.py`, dependency `require_api_key` en todos los
      routers protegidos, `GET /health` público (docs/07_API_REST.md §2.1).
- [x] Agregar logging estructurado (JSON logs) al script extractor, al
      consumer y al backend — extraído a `src/common/logging.py`
      (`JsonLogFormatter`/`setup_logging`) y `src/common/mqtt.py`
      (`connect_with_retry` con backoff exponencial, antes duplicado casi
      exacto entre `mock_starlink/__main__.py` y `consumer/__main__.py`).
      El backend usa el mismo envelope de error para todos los códigos del
      catálogo (`src/backend/errors.py`, §3.2/§3.3).
- [x] Loguear errores de conexión al broker y fallos de validación Pydantic
      con contexto (`node_id`, `timestamp`) — ya cubierto desde semana 6
      (`router.py`) y ahora también en el backend (`ApiError`/handlers).

**Verificación**: 137/137 tests pasando (`PYTHONPATH=src pytest tests/`),
incluida la suite nueva `tests/test_backend_api.py`/`test_backend_helpers.py`/
`test_common.py` — auth 401 sin tocar DB, envelope de error, `GET /health`
degradándose sin crashear cuando Postgres/Mosquitto no están disponibles
(verificado apuntando a un puerto sin nada escuchando, falla rápido por
`ECONNREFUSED`). **Pendiente**: verificación end-to-end real contra
`docker compose --profile mocks up --build` — no se ejecutó esta sesión por
espacio en disco de la máquina compartida (2.6GB libres, 89% usado, imágenes
de otros proyectos cacheadas); falta bajar `timescaledb:2.17.2-pg16` y
construir 3 imágenes nuevas (`mock-starlink`, `starlink-consumer`,
`starlink-backend`). Retomar en la próxima sesión con más espacio libre o
tras un `docker system prune` consciente.

## Semana 10 — Pasaje a hardware real (RPi5) `[HW]`

- [x] Confirmar disponibilidad de antena, RPi5 y tarjeta de memoria — RPi5 accesible
      físicamente en el LIT, hostname `raspberrypi`, IP de lab `172.18.147.143`,
      usuario `leonode`. Antena conectada a la RPi (según relevamiento visual);
      conectividad gRPC (`192.168.100.1:9200`) todavía sin confirmar, ver abajo.
- [x] ⚠️ Reemplazar el mock por la conexión real al gRPC de la antena
      (`192.168.100.1:9200`) — **código escrito, sin validar contra hardware
      real todavía** (sin acceso presencial al LIT en esta sesión).
      `src/acquisition/`: `grpc_client.py` (llama a `grpcurl` como
      subproceso — enmienda de ADR-01, ver `docs/05_ADR.md`, en vez de
      `grpcio`+`starlink-grpc-tools` como describía la decisión original),
      `starlink_extractor.py` (funciones puras `map_status`/
      `derive_jitter_loss`/`count_handovers`/`build_metrics`, testeadas con
      17 tests contra JSON sintético que imita la estructura documentada en
      el relevamiento del 04/08/2026 — **no** los JSON crudos reales, que
      solo existen en `~/starlink-relevamiento/` de la RPi5), `__main__.py`
      (loop de polling, mismo tópico/morfología que el mock, no tumba el
      contenedor ante `GrpcClientError`). `Dockerfile.acquisition` (instala
      el binario `grpcurl`, multi-arch amd64/arm64), servicio `acquisition`
      en `docker-compose.yml` bajo perfil **`real`** propio (nunca junto con
      `mocks` — dos productores del mismo tópico a la vez rompería
      ADR-01), `network_mode: host` (necesita alcanzar `192.168.100.1`).
- [x] Correr el script extractor sobre el Raspberry Pi 5 real — 12/08/2026,
      ver sesión abajo. Confirmado `grpcurl` preinstalado en la RPi5 y
      conectividad real a la antena (`192.168.100.1:9200`, server
      reflection responde). Capturado `get_status`/`get_history` reales vía
      SSH y corrido `build_metrics()`/`StarlinkPayloadIn.model_validate()`
      contra esos datos (offline, sin correr `__main__.py` como proceso
      continuo todavía).
- [x] (parcial) Validar el mapeo del extractor contra datos reales de la
      antena — **validación offline completa** (mapeo campo a campo +
      validación Pydantic end-to-end, ver sesión del 12/08 abajo), pero
      **todavía no la pila Docker completa corriendo en la RPi5** (Docker
      Engine no está instalado ahí, ver hallazgo abajo) ni las 72h de CA-01.
- [ ] Instalar Docker Engine en la RPi5, `docker compose --profile real up
      --build` ahí, verificar con `mosquitto_sub` que el payload publicado
      es indistinguible en forma del que publica el mock, y recién ahí
      arrancar las 72h de CA-01/CA-02 con `scripts/monitor_ca02.py`.
- [ ] Confirmar con Fede que ambos módulos funcionan simultáneamente sobre el RPi5

> 🔗 Milestone: fin del desarrollo desacoplado del hardware.

### 2026-08-04 — Sesión en el lab: acceso a la RPi5 y plan de relevamiento gRPC

**Contexto:** primera sesión físicamente en el LIT con acceso a la RPi5 conectada a
la antena real. Semana 9 (backend FastAPI) todavía no está cerrada — este trabajo
es exploratorio/relevamiento de solo lectura sobre la antena, no despliegue del
extractor de producción, así que se adelantó sin bloquear en eso. Falta avisarle a
Fede si se termina dejando algo corriendo en la RPi5 más allá de esta sesión de
pruebas (Semana 10 pide confirmar con él antes de correr ambos módulos juntos ahí).

**Acceso SSH:**
- Login por contraseña confirmado funcionando (`ssh leonode@172.18.147.143`) —
  se había interpretado como fallo por error, pero la sesión entraba
  correctamente (MOTD + `Last login` sin ningún mensaje de error).
- Se migró a autenticación por clave para uso repetible/no interactivo: par de
  claves ed25519 dedicado generado en la máquina de desarrollo
  (`~/.ssh/leonode_rpi_ed25519`, sin passphrase, comment
  `claude-code@starlink-pi-lab`, fingerprint `SHA256:ms86E7J1W9OdJ9XNfWvQOYiypd8KX2991V96ONs7oHY`).
  Pendiente: agregar la clave pública a `~/.ssh/authorized_keys` de `leonode` en
  la RPi5 (manual, con contraseña, no se comparte la contraseña con el asistente)
  y verificar login sin contraseña.
- Confirmado que la máquina de desarrollo tiene ruta de red hacia la RPi5
  (`ping 172.18.147.143` responde, misma red de lab) — el bloqueo era solo de
  credenciales, no de conectividad.

**Pendiente de verificar (conectividad RPi5 → antena, `192.168.100.1:9200`):**
checklist de diagnóstico acordado para cuando falle el ping a la antena desde la
RPi5: `ip addr`/`ip link` (¿la interfaz tiene IP en `192.168.100.0/24`? ¿está
`UP`?), `ip route` (¿existe ruta a `192.168.100.0/24`? si no aparece, es
`Network unreachable`, no timeout — apunta a problema de capa 2/DHCP, no de la
antena), `ip neigh`/`arping` si la ruta existe pero el ping igual falla. Causa más
probable si no hay IP en ese segmento: la RPi está conectada al router Starlink
sin *Bypass Mode* activado (los clientes reciben `192.168.1.x` y nunca ven
`192.168.100.1`), en vez de estar cableada directo vía el *Ethernet Adapter*
oficial de Starlink que bypassea el router.

**Plan de relevamiento gRPC (una vez confirmada la conectividad a la antena),
sin tocar `src/mock_starlink/` ni el pipeline de producción:**
- `grpcurl -plaintext 192.168.100.1:9200 list` / `list SpaceX.API.Device.Device`
  — la antena expone server reflection, no hace falta compilar `.proto` para
  explorar.
- `grpcurl -plaintext -d '{"get_status":{}}' ... Device/Handle`,
  `get_history`, `get_diagnostics` — las tres son de solo lectura, sin riesgo de
  tocar configuración de la antena.
- Alternativa más cercana al extractor final: `sparky8512/starlink-grpc-tools`
  (`dish_grpc_text.py`) con `grpcio` real, referenciado en ADR-01.
- Mapeo objetivo contra `src/mock_starlink/schema.py::StarlinkMetrics` (a
  confirmar campo por campo contra la respuesta real):
  `latency_ms` ← `pop_ping_latency_ms` directo · `jitter_ms` y
  `packet_loss_pct` derivados sobre la serie de `get_history` (no son campos
  nativos) · `throughput_down_bps`/`throughput_up_bps` ← `downlink_throughput_bps`/
  `uplink_throughput_bps` · `is_obstructed` ← `obstruction_stats.currently_obstructed`
  · `satellite_count` ← a confirmar si existe en este firmware.
  **⚠️ `snr_db` — riesgo concreto de ruptura de esquema por firmware** (anticipado
  en ADR-01/CLAUDE.md §1.1): firmwares recientes de Starlink reemplazaron el SNR
  numérico por un booleano `is_snr_above_noise_floor`. Falta confirmar en el
  `get_status` real de esta antena si sigue existiendo un campo numérico o hay
  que revisar `docs/03_SRS.md` §5.1 / `docs/06_DER.md` y decidir cómo se propaga
  (documentar como nuevo hallazgo, no pisar el esquema en silencio si cambió).

**Acceso por clave: confirmado.** `ssh leonode-rpi` (alias en `~/.ssh/config` de la
máquina de desarrollo) entra sin contraseña. Clave agregada a mano por Aldana en
`~/.ssh/authorized_keys` de la RPi5.

**Diagnóstico de red RPi5 → antena: conectividad confirmada, con una particularidad.**
`ip addr`/`ip route` en la RPi5 no muestran ninguna interfaz ni ruta explícita a
`192.168.100.0/24` — la única IP relevante es `eth0` con `100.94.223.114/10` vía
gateway DHCP `100.64.0.1` (rango CGNAT, coincide con el WAN-side típico de
**Starlink en Bypass Mode**, cableado directo antena↔RPi5 sin pasar por el router
Starlink). `ip route get 192.168.100.1` confirma que el kernel igual resuelve esa
ruta a través de `eth0 via 100.64.0.1` — el propio dish/gateway rutea internamente
el tráfico de management, así que **no hace falta una ruta /24 explícita en el
cliente**, es una particularidad del bypass mode, no un error. Puerto `9200/tcp`
abierto, `grpcurl` ya estaba instalado en la RPi5. `ping` tuvo 50% de pérdida en
la primera corrida (2/4, RTT ~1ms) — normal para una interfaz de diagnóstico que
no prioriza ICMP, no bloqueante para las llamadas gRPC (que respondieron 100%).

**Relevamiento gRPC real ejecutado** (solo lectura, sin tocar `src/mock_starlink/`
ni pipeline de producción). Server reflection confirma el servicio esperado:
`SpaceX.API.Device.Device` con métodos `Handle` y `Stream`. Se guardaron en la
RPi5 (`~/starlink-relevamiento/`): `get_status_full.json` (con `-emit-defaults`,
226 líneas), `get_diagnostics.json`, `get_history.json` (80K).

Mapeo verificado campo a campo contra `src/mock_starlink/schema.py::StarlinkMetrics`:

| Campo del esquema | Resultado del relevamiento |
|---|---|
| `latency_ms` | ✅ `dishGetStatus.popPingLatencyMs` (24.5 ms en la muestra), directo, sin transformar |
| `throughput_down_bps` / `throughput_up_bps` | ✅ `downlinkThroughputBps` / `uplinkThroughputBps` directos. Nota: la antena de prueba tenía `dlBandwidthRestrictedReason: LOW_SPEED_POLICY_LIMIT` y `mobilityClass: MOBILE` — valores bajos (~668 kbps/173 kbps) son de la política del plan, no del extractor |
| `jitter_ms` / `packet_loss_pct` | ✅ confirmados derivables — `get_history.dishGetHistory` expone `popPingLatencyMs` y `popPingDropRate` como series, tal cual asume el docstring del schema |
| `is_obstructed` | ✅ `obstructionStats.currentlyObstructed` existe (con `-emit-defaults`; sin ese flag protobuf-JSON omite el campo por estar en `false`, no es que falte). Falso positivo de riesgo descartado |
| `satellite_count` | ⚠️ confirmado ausente en `get_status` **y** en `get_diagnostics` en este hardware/firmware. Consistente con que el campo ya está modelado como opcional en el schema — no requiere acción, pero confirma que no hay que depender de él |
| `snr_db` | 🔴 **drift de esquema confirmado, tal como anticipaba el comentario de ADR-01 sobre cambios de firmware.** El firmware actual (`apiVersion: 42`, sw `2026.07.19.mr82648`) **no expone ningún campo numérico de SNR** — solo dos booleanos: `isSnrAboveNoiseFloor` e `isSnrPersistentlyLow`. `snr_db` tal como está definido en `schema.py`/`docs/03_SRS.md` §5.1/`docs/06_DER.md` no tiene de dónde salir en hardware real. **Pendiente decisión (no resuelto en esta sesión):** ¿reemplazar `snr_db` por un booleano tipo `snr_low` en el esquema (requiere nuevo ADR + tocar SRS/DER/schema.py), o mantener `snr_db` nullable y que el extractor real siempre mande `null` (rompe la equivalencia mock↔real 1:1 que pide ADR-01/CLAUDE.md §1.1, el mock seguiría generando un valor sintético que el hardware real nunca puede producir)? Avisado a Aldana, no se tocó código ni docs todavía. |

**Próximos pasos:** decidir el tratamiento de `snr_db` (posible nuevo ADR) ·
escribir el extractor real (`services/acquisition/starlink_extractor.py` o
similar) usando este mapeo · correr `pytest` contra los JSON crudos guardados
como fixtures de referencia antes de mandar nada al broker · avisar a Fede una
vez que el extractor real quede corriendo en la RPi5 compartida (Semana 10 pide
confirmar convivencia de ambos módulos ahí).

`get_diagnostics.json` re-confirmado por Aldana en su propia corrida del paso 10:
tampoco encontró `satellite_count`. Coincide con lo relevado arriba — dos
antenas/sesiones distintas, mismo resultado, refuerza que el campo simplemente
no está disponible en este hardware/firmware, no fue un error de la corrida.

### Pedido del director: procesar `alignmentStats` para Grafana — nueva decisión pendiente

El director sugirió que sería interesante para los dashboards de Grafana procesar
los datos de `dishGetStatus.alignmentStats` (ya capturados en `get_status_full.json`
del relevamiento de arriba):

```
alignmentStats: tiltAngleDeg, boresightAzimuthDeg, boresightElevationDeg,
                 attitudeEstimationState, attitudeUncertaintyDeg,
                 desiredBoresightAzimuthDeg, desiredBoresightElevationDeg
```

**Por qué encaja con el alcance del proyecto:** el objetivo central (CLAUDE.md §1)
es correlacionar clima/entorno físico con performance de red — la desviación entre
posición real (`boresightAzimuthDeg`/`boresightElevationDeg`) y objetivo
(`desiredBoresightAzimuthDeg`/`desiredBoresightElevationDeg`), o un `tiltAngleDeg`
que se corre con el viento, es exactamente ese tipo de correlato físico-ambiental
(ej. viento fuerte desalineando la antena → picos de latencia). No es scope creep,
es una instancia directa del objetivo del PI.

**Por qué NO se implementa todavía, tal como pide CLAUDE.md §2/§11:** son campos
nuevos que hoy no existen en `StarlinkMetrics` (`schema.py`), ni en
`docs/03_SRS.md` §5.1, ni en `network_metrics` (`docs/06_DER.md`). Agregarlos
cambia el paquete MQTT compartido con el consumer/DB/Grafana — requiere:
1. Un nuevo ADR (o extender ADR-01) documentando la decisión: ¿campos sueltos en
   `StarlinkMetrics`, o un sub-objeto `alignment` anidado en el payload?
2. Actualizar `docs/03_SRS.md` §5.1 y `docs/06_DER.md` (`network_metrics`,
   nuevas columnas + migración de la hypertable) en paralelo al schema.
3. Recién ahí: nuevo panel en `services/grafana/dashboards/red_starlink.json`
   (tilt/azimuth/elevación vs. tiempo, posible overlay con desviación real vs.
   deseada).

**Pendiente / TODO agregado:** valorar si conviene resolver esto junto con la
decisión de `snr_db` (ambas son "campos de hardware real que el mock actual no
contempla") en el mismo ADR de ajuste de esquema post-relevamiento, en vez de dos
ADRs separados — a discutir con el director/Fede antes de tocar código.

### 2026-08-11 — Cierre: schema_version 1.1, ADR-16/17/18 implementados

Se retomó el trabajo tras un corte de máquina entre sesiones. Se resolvieron las
tres decisiones de esquema que quedaron pendientes del relevamiento de arriba,
todas juntas en un solo pasaje (no separadas en el tiempo, ya que las tres tocan
el mismo payload/hypertable compartidos):

- **`snr_db` → `snr_low`**: se decidió ADR propio (**ADR-17**), no fusionarlo con
  el de `alignmentStats` — son motivaciones distintas (uno forzado por el
  firmware, el otro una feature pedida por el director) y separarlos da mejor
  trazabilidad para que el director los evalúe independientemente.
- **`alignmentStats`**: **ADR-18**, campos planos en `metrics` (no sub-objeto
  anidado — `network_metrics` es plana por naturaleza). Se descartó
  `attitudeEstimationState` (sin uso analítico).
- **`handover_count`/`outage_duration_ms`**: **ADR-16**, que ya estaba escrito
  en la sesión anterior sin commitear, ahora commiteado junto con los otros dos.

**Cambio de tipo incompatible** (`snr_db` float → `snr_low` bool) obligó a subir
`SCHEMA_VERSION` de `"1.0"` a `"1.1"` — primer bump de versión de esquema del
proyecto. `StarlinkPayloadIn.check_schema_version` rechaza `"1.0"` explícitamente
(UT-01-08).

Implementado en el mismo pasaje: `src/mock_starlink/schema.py` (`StarlinkMetrics`
con los 8 campos nuevos, `SCHEMA_VERSION="1.1"`), `src/mock_starlink/mock.py`
(`snr_low` reemplaza el random walk de `snr_db`; `handover_count`/
`outage_duration_ms` derivados del `handover_event` que ya existía
internamente; alineación como random walk lento alrededor de un apuntamiento
deseado fijo por nodo), `src/consumer/db.py` + `src/consumer/router.py`
(columnas nuevas en `NetworkMetric` y `_starlink_row`), `services/db/
init_starlink_health.sql` (columnas + CHECK constraints + agregados nuevos en
`net_hourly`/`net_daily`), `services/grafana/dashboards/red_starlink.json`
(paneles "Handovers por hora" y "Alineación de la antena" nuevos, `snr_low`
superpuesto al panel de obstrucción existente). Los cuatro documentos
autoritativos (SRS/ADR/DER/API REST) y el Plan de QA actualizados en el mismo
pasaje, antes que el código (`CLAUDE.md` §11).

**Hallazgo corregido durante la implementación** (no estaba en el relevamiento
original): el rango de `boresight_azimuth_deg`/`desired_boresight_azimuth_deg`
se definió primero como signado (-180..180), pero el valor de ejemplo elegido
(184.3°) lo excedía. Azimuth es convención de brújula (0-360°, no signado) —
se corrigió el rango a `[0, 360]` en `schema.py`, el DER y la API REST antes de
commitear, no se forzó el ejemplo a un valor artificial para que entrara en el
rango equivocado.

**Base de datos**: en Etapa 0 (datos sintéticos, ADR-08) no se migra con
`ALTER TABLE` — se recrean los volúmenes Docker (`docker compose --profile
mocks down -v`) y se re-backfillea con `TIME_WARP_FACTOR`. Documentado acá en
vez de escribir un script de migración que nadie va a correr contra datos
descartables.

79/79 tests pasando (`PYTHONPATH=src pytest tests/`, incluye 2 tests nuevos de
robustez del mock para handover/alineación); `mock.py` y `schema.py` siguen al
100% de cobertura. Verificación end-to-end contra Docker real (`docker compose
--profile mocks up --build` con volúmenes limpios) queda pendiente para la
próxima sesión con acceso a la máquina — ver checklist de verificación del plan
de esta sesión.

**Sigue pendiente** (no tocado en este pasaje): el extractor real
(`src/acquisition/`, semana 10) todavía no está escrito — el mapeo gRPC→schema
para los 8 campos nuevos queda documentado en el ADR-16/17/18 correspondiente,
a implementar cuando haya acceso presencial a la RPi5/antena.

### Relevamiento adicional: identidad del dish, handovers y superficie completa de la API

**`get_device_info`** (`~/starlink-relevamiento/get_device_info.json`): mismo
`deviceInfo` que ya aparece en `get_status` (`id: "ut01000000-00000000-007c263c"`
es el identificador único del terminal — no hay un "número de serie" separado).
No aporta campos nuevos sobre `get_status`, no hace falta usarlo en el extractor.

**Superficie completa de la API relevada vía reflection** (`grpcurl describe
SpaceX.API.Device.Request`, solo lectura, no ejecuta nada): el firmware expone
~90 tipos de operación además de `get_status`/`get_history`/`get_diagnostics`.
**Importante para cualquiera que siga probando en esta antena:** una parte grande
de esa superficie son operaciones que escriben/modifican el hardware físico
(`reboot`, `factory_reset`, `dish_factory_reset`, `dish_stow`, `reset_button`,
`dish_inhibit_rf`, `dish_inhibit_gps`, `software_update`, `set_trusted_keys`,
`wifi_set_config`, `dish_set_config`, `toggle_mode`, entre otras) —
**no se deben invocar** sobre la antena real del lab. Solo se probaron y se deben
seguir usando las de lectura (`get_*`, `dish_get_*`, `wifi_get_*`).
`get_persistent_stats` está en la lista pero devuelve `Unimplemented` en este
firmware — no confiar en esa llamada para este hardware/versión.

**Handovers ("cuándo cambia de conexión"):** confirmado que la API expone un
indicador explícito y oficial, sin necesidad de inferir nada:
- `get_history.dishGetHistory.outages[].didSwitch` (booleano) — indica si durante
  ese corte el dish cambió de satélite/haz. En la muestra: un corte de ~0.9s por
  `NO_PINGS` con `didSwitch: true`.
- `get_history.dishGetHistory.eventLog.events[]` — log más largo (desde el boot)
  con `severity`, `reason` (`EVENT_REASON_OUTAGE_NO_PINGS`,
  `EVENT_REASON_OUTAGE_NO_DOWNLINK`, `EVENT_REASON_OUTAGE_UNKNOWN`,
  `EVENT_REASON_OUTAGE_BOOTING`), `startTimestampNs`, `durationNs`. En la ventana
  capturada: ~40 eventos, mayoría cortes de 0.4-1.2s.

**Límite de alcance explícito:** la API no expone identidad del satélite (catálogo,
beam ID, etc.) — no es que falte cavar más, ya se relevó la superficie completa de
operaciones disponibles y ninguna la trae. Ir más allá para inferir esa lógica
interna caería en *"ingeniería inversa de mecanismos internos propietarios de
Starlink"*, marcado explícitamente **fuera de alcance** en CLAUDE.md §1.1. Lo que
sí es información oficial y está dentro de alcance es el efecto observable del
handover (`didSwitch`, causas de `eventLog`) — que es exactamente lo que hace
falta para calibrar `packet_loss_pct`/`jitter_ms` y, en particular, para dar
valores realistas al perfil `CHAOS_PROFILE: HANDOVER_HEAVY` del mock (ADR-06):
esta data real da una referencia concreta de frecuencia y duración de handovers
para no inventar los parámetros del random walk a ciegas.

### 2026-08-12 — Sesión en el lab: validación de campo del extractor real contra la antena

**Contexto:** primera sesión con acceso presencial simultáneo a RPi5 + antena +
tiempo para tocar código (a diferencia del 04/08, exploratorio). Antes de esto,
`src/acquisition/` estaba escrito pero nunca corrido contra hardware real.

**Conectividad confirmada:** SSH a la RPi5 (`leonode-rpi`, `raspberrypi`,
172.18.147.143) funcional. `grpcurl` preinstalado. `grpcurl -plaintext
192.168.100.1:9200 list` responde con `SpaceX.API.Device.Device` — la antena
está en Bypass Mode y alcanzable, tal como asume `grpc_client.py`.

**Metodología:** en vez de instalar Docker en la RPi5 y correr la pila
completa (Docker Engine no está instalado ahí todavía — ver pendiente abajo),
se capturó `get_status`/`get_history` reales vía `grpcurl` sobre SSH y se
corrieron `build_metrics()` + `StarlinkPayloadIn.model_validate()` de forma
offline contra esos datos, en la máquina de desarrollo. Validación más rápida
para una sesión acotada, y suficiente para encontrar y corregir los mismatches
reales sin arriesgar tocar la config de la RPi5 compartida con Fede.

**Tres mismatches encontrados entre lo asumido (relevamiento 04/08, ADR-16/17/18
tal como quedaron implementados el 11/08) y el firmware real
(`softwareVersion: 2026.07.27.mr83192.1`):**

| Campo | Asumido | Real | Corrección |
| --- | --- | --- | --- |
| `snr_low` | `dishGetStatus.isSnrPersistentlyLow` | No existe. Solo `isSnrAboveNoiseFloor` (semántica invertida) | `snr_low = not isSnrAboveNoiseFloor` |
| `is_obstructed` | `obstructionStats.currentlyObstructed` | No existe. Solo `fractionObstructed` (fracción continua 0-1) | `is_obstructed = fractionObstructed > 0` |
| `boresight_azimuth_deg` / `desired_boresight_azimuth_deg` | Convención de brújula 0-360 | Rango firmado -180..180 (ej. `-179.99922`) | Rango del campo cambiado a -180..180 en todo el esquema compartido |

El tercero era el más grave: rompía `StarlinkPayloadIn.model_validate()` en
cada poll con azimuth negativo, es decir **descartaba el payload real
completo**, no solo un campo — nunca hubiera llegado nada a la DB con la
antena real conectada.

**Corregido y verificado:** `src/acquisition/starlink_extractor.py`,
`src/mock_starlink/schema.py` (rango de azimuth), `src/mock_starlink/mock.py`
(generación del mock en el rango correcto), `services/db/init_starlink_health.sql`
(CHECK constraint), y los 4 documentos autoritativos (SRS/ADR/DER/API REST).
ADR-17 y ADR-18 llevan una sección "Hallazgo de campo (12/08/2026)" nueva
documentando la corrección sin reescribir la decisión original. Revalidado
`build_metrics()` contra el payload real capturado: pasa
`StarlinkPayloadIn.model_validate()` de punta a punta (antes fallaba). 183/183
tests, 94.79% cobertura.

**Pendiente para la próxima sesión en el lab** (no se hizo hoy, no se instaló
nada en la RPi5 más allá de usar `grpcurl` de solo lectura):
- Instalar Docker Engine + clonar el repo en la RPi5 (no estaba, `docker` no
  encontrado) — coordinar con Fede si conviene hacerlo juntos, ya que
  comparten el mismo RPi5.
- `docker compose --profile real up --build` con `DISH_GRPC_ADDR` real, y
  verificar con `mosquitto_sub` que el payload publicado por `acquisition`
  llega al broker con la misma forma que el del mock.
- Recién ahí arrancar la ventana de 72h de CA-01/CA-02 con
  `scripts/monitor_ca02.py`.
- Llevarle al director el hallazgo de `isSnrPersistentlyLow`/
  `currentlyObstructed`/rango de azimuth como enmienda a confirmar en
  ADR-17/ADR-18 (siguen "Propuesto").

### 2026-08-13 — Sesión en casa: endurecer el pipeline local con mocks

**Contexto:** mismo día que la sesión del LIT de arriba, pero ya sin acceso a
RPi5/antena (PRs #10/#11/#12 de esa sesión ya mergeados a `main`). Con la pila
`--profile mocks` levantada localmente, foco en ejercitar el pipeline con
`CHAOS_PROFILE` variados y en probar los endpoints del backend a fondo — no
tocar el mock ni el dashboard (`services/grafana/dashboards/red_starlink.json`
ya tenía los 7 paneles esperados, confirmado sin necesidad de editar nada ahí).

**Caos verificado end-to-end (no solo a nivel unitario):** se corrió
`mock_starlink` en tiempo real (`TIME_WARP_FACTOR=1`, no se usó backfill
acelerado — arranca 30 días atrás por diseño de ADR-08 y no aporta a una
sesión corta) con `CHAOS_PROFILE=STORM` y luego `HANDOVER_HEAVY`, verificando
en `starlink_health_db` que efectivamente aparecen `is_obstructed=true`,
`snr_low=true`, `packet_loss_pct` >5%, `handover_count`>0 y
`outage_duration_ms`>0 — sin `ValidationError` ni errores de deserialización
en los logs de `mock_starlink`/`consumer`. Los perfiles ya estaban cubiertos
estadísticamente por `tests/test_mock.py` (UT-04-02, etc.); esto agrega la
confirmación de que el pipeline completo (mock→broker→consumer→DB) los
absorbe sin romperse, que un test unitario del mock no puede probar.
`net_hourly`/`net_daily` se pueden poblar sin esperar el schedule de la
Continuous Aggregate Policy (1h/1día) llamando manualmente a
`CALL refresh_continuous_aggregate('net_hourly', NULL, NULL)` — útil para
verificación puntual; en producción sigue refrescando solo por policy.

**Bug real encontrado y corregido en el backend — fuga de path interno en
errores 400:** `GET /metrics/starlink` sin `start`/`end` devolvía un `detail`
que incluía el path del archivo y línea del handler dentro del contenedor
(`File "/app/src/backend/routers/metrics_starlink.py", line 78, in
get_starlink_metrics...`) en vez de un mensaje legible — `str(exc)` sobre el
`RequestValidationError` en FastAPI 0.141/Starlette 1.6 arrastra ese detalle.
Corregido en `src/backend/errors.py`
(`validation_exception_handler`/`_format_validation_errors`): arma el
`detail` desde `exc.errors()` en vez de `str(exc)`. No es una fuga grave hoy
(entorno local, sin exponerse a internet — ADR-14 recién exige postura Zero
Trust en el punto de exposición externa, que es Grafana, no el backend), pero
sí un detalle interno que no correspondía en un `detail` público — regresión
cubierta en `tests/test_backend_api.py::test_validation_error_detail_no_filtra_paths_internos`.

**Drift de documentación encontrado y corregido:** `docs/07_API_REST.md`
§2.1 documentaba el nombre de la variable de entorno de la API Key como
`API_KEY` (en el snippet de `security.py` y en la tabla de configuración) —
el código real (`src/backend/config.py`, `docker-compose.yml`, `.env.example`)
siempre usó `BACKEND_API_KEY`. Corregido el doc para que coincida con el
código real, sin cambiar comportamiento.

**Endpoints ejercitados manualmente con `curl` contra la pila local**
(`/health`, `/metrics/starlink` [+`/summary`, `/latest`], `/nodes`,
`/nodes/{node_id}`, `POST /ingest/starlink` con `ENABLE_INGEST_ENDPOINT=false`
por default): todos responden con el envelope y los códigos de
`docs/07_API_REST.md` §3 (401 sin key / con key incorrecta, 404
NODE_NOT_FOUND, 422 INGEST_DISABLED, 200 con el `status`/`version`/
`page_info`/`data` esperados). No se dejó `ENABLE_INGEST_ENDPOINT=true` en
`.env` al terminar.

**No verificado visualmente (sin navegador en este entorno):** los paneles
de Grafana no se revisaron por captura de pantalla — se verificó en cambio,
vía SQL, que las queries `rawSql` de los 7 paneles (incluidos los 3 de
ADR-16/18) devuelven filas no vacías y plausibles con los datos generados
en esta sesión. Falta la revisión visual real en el navegador (pendiente
para quien tenga la pila abierta en Grafana, http://localhost:3000).

184/184 tests (183 + 1 nuevo), 94.71% cobertura — sigue ≥90%. Sin PR todavía
para este cambio (`src/backend/errors.py`, `tests/test_backend_api.py`,
`docs/07_API_REST.md`) — pendiente de rama + PR según el ruleset de `main`.

## Semanas 11–12 — Suite de testing + CI `[IND]` ✅ COMPLETA (código; CI sin correr en GitHub real todavía)

- [x] Escribir/completar suites de integración (IT-01): mock → broker →
      consumer → DB — `tests/integration/test_it01_pipeline.py`, automatiza
      IT-01-01 (mensaje válido persiste), IT-01-02 (inválido no persiste),
      IT-01-03 (reentrega QoS 1 tras matar/reiniciar el consumer,
      `@pytest.mark.integration`), IT-01-04 (100 mensajes sin pérdida),
      IT-01-05 (múltiples nodos no se mezclan). Publica directo al broker
      (`tests/integration/conftest.py:mqtt_publisher`, no pasa por el mock)
      y verifica con `docker exec ... psql` — nunca TCP directo a Postgres
      (ADR-14: `starlink_health_db` no expone su puerto ni siquiera al
      host). Se saltea sola (`pytest.skip`) si el contenedor
      `starlink-health-db` no está corriendo, para que `pytest tests/` sin
      infraestructura levantada siga funcionando igual que antes.
- [x] Configurar `pytest-cov` con `--cov-fail-under=90` en tus módulos (subido
      de 80% a 90% el 12/08/2026, con 94.79% real ya alcanzado — margen
      suficiente sin aflojar el piso) —
      `pytest.ini` (`addopts`, corre por default) + `.coveragerc`
      (`omit = */__main__.py`: los loops de conexión MQTT de
      mock_starlink/consumer/acquisition son casi sin lógica propia y se
      validan con Docker real, no con paho-mqtt mockeado — mismo criterio
      que ya estaba documentado para `mock_starlink/__main__.py` desde
      antes de que existiera este archivo). Se sumaron tests nuevos
      (`tests/test_backend_db.py`, `test_backend_routers_db.py` con un
      Engine de SQLAlchemy mockeado — `tests/backend_fakes.py`) para subir
      la cobertura real de los routers del backend, no solo para pasar el
      número. **177 tests pasando, 94.78% de cobertura** — muy por encima
      del 80% mínimo.
- [x] Dejar el pipeline de GitHub Actions corriendo en cada push —
      `.github/workflows/ci.yml` (job `unit`: pytest + cobertura en cada
      push/PR; job `integration`: levanta `broker`/`starlink_db`/
      `station_config_db`/`consumer` reales y corre IT-01) y
      `.github/workflows/publish.yml` (build + push multi-arch amd64/arm64
      a GHCR de las 4 imágenes -- `mock-starlink`, `starlink-consumer`,
      `starlink-backend`, `starlink-acquisition` -- con tag por SHA y
      `latest` solo en `main`; cierra el pendiente "publicar mock-starlink a
      GHCR" del modelo polyrepo, ver "Coordinación pendiente con Fede").
      **Sin verificar corriendo en GitHub Actions real todavía** — no hay
      push a un remoto en esta sesión; revisar el primer run real (y que
      `GITHUB_TOKEN` tenga permiso `packages: write` en la config del repo)
      antes de dar el job `publish` por cerrado.

## Semanas 13–14 — Soporte a integración de APIs externas `[INT — Fede lidera]`

- [ ] Revisar que las fuentes meteorológicas externas no rompan el esquema del consumer compartido
- [ ] Ajustar si hace falta la routing logic de tópicos MQTT para la nueva fuente

## Semanas 15–16 — Resiliencia, seguridad y Continuous Aggregates `[IND]+[INT]` ✅ COMPLETA (lado Starlink)

- [x] Configurar Continuous Aggregates en TimescaleDB para acelerar consultas
      largas de Grafana — `net_hourly`/`net_daily` ya existían desde semana
      6-7; esta sesión se les agregaron los campos nuevos de la Fase 1
      (`sum_handover_count`, `sum_outage_duration_ms`, `avg_tilt_angle_deg`,
      ver `services/db/init_starlink_health.sql`). Verificado que el backend
      las usa (`src/backend/routers/metrics_starlink.py`,
      `resolution=auto`/`hourly`/`daily`) y que Grafana también (panel
      "Handovers por hora" nuevo, `services/grafana/dashboards/
      red_starlink.json`, consulta `net_hourly` directo).
- [x] Sumar manejo de caídas del broker (reconexión automática) — ya estaba
      en el mock desde semana 3 (`common.mqtt.connect_with_retry`, extraído
      en semana 9); `src/acquisition/__main__.py` (extractor real, semana
      10) lo hereda del mismo módulo compartido, sin reimplementarlo. Test
      de backoff exponencial con un broker falso que rechaza N conexiones
      antes de aceptar: `tests/test_common.py::
      test_connect_with_retry_reintenta_hasta_conectar`.
- [x] Colaborar en la postura Zero Trust (ADR-14): solo Grafana expuesto,
      filtrado de IP — **hallazgo corregido esta sesión**: en Fase 2 el
      backend se había publicado en `127.0.0.1` (asumiendo que solo Grafana
      debía exponerse), pero la tabla de exposición de puertos de ADR-14 ya
      decía explícitamente que el backend debe quedar accesible desde la
      intranet del LIT (⚠️, distinto del ✅ público de Grafana) — se
      corrigió `docker-compose.yml` para publicar el backend sin la
      restricción a localhost, en vez de dejar que la asunción pisara en
      silencio una decisión ya tomada (CLAUDE.md §2). Además, ADR-14
      mencionaba "filtrado de IP" en el resumen de `CLAUDE.md` §4 sin
      especificar nunca el mecanismo concreto — se agregó una sección nueva
      en ADR-14 (`docs/05_ADR.md`) documentando `ufw`/firewall del host
      (Docker no filtra por IP de origen sin plugins) + el ejemplo
      correspondiente en `README.md` "Seguridad en un despliegue real". Es
      una medida operativa (config del host, no de `docker-compose.yml`) —
      sin ejecutar contra la RPi5 real todavía (mismo motivo de siempre: sin
      acceso presencial al LIT en esta sesión).

## Semanas 17–18 — Frontend / videomonitoreo (opcional) `[INT]`

- [ ] Colaborar en el microservicio de streaming (mock Flask/MJPEG → cámara real)
- [ ] Verificar que no compita por ancho de banda con las mediciones de red

## Semanas 19–20 — Integración completa del sistema (E2E) `[INT]` — CA-08 automatizado, CA-01/CA-02 con herramienta lista

- [ ] Correr la suite E2E completa sobre la pila Docker de producción — la
      suite IT-01 (Fase 4/semana 11-12, `tests/integration/`) ya cubre el
      flujo mock→broker→consumer→DB; falta correrla de verdad contra Docker
      (pendiente por espacio en disco de esta sesión, ver semana 9) y sumar
      el resto de niveles del Plan de QA (`docs/08_Plan_QA.md` §4-6: IT-03
      backend, E2E, estrés) cuando haya pila real levantada.
- [x] Validar los Criterios de Aceptación relacionados a tu módulo — **CA-08
      automatizado** (`tests/test_ca08_schema_coherence.py`, 3 tests):
      compara `StarlinkMetrics.model_fields` contra las columnas reales de
      `network_metrics` en ambas direcciones (campo sin columna / columna
      sin campo) parseando `services/db/init_starlink_health.sql`, y
      verifica que `starlink_row` (consumer) mapee todos los campos a la
      fila de INSERT — no solo inspección de texto, corre un payload real
      a través de la función. Corre sin Docker, en segundos.
      **CA-01/CA-02 con herramienta lista, sin ejecutar todavía**: CA-01
      (mocks, dashboard visible en <2min) se valida con el mismo
      `docker compose --profile mocks up --build` ya usado en semanas 6-8
      (pendiente repetir esta sesión por espacio en disco). CA-02 (hardware
      real, "logs sin errores por 72h") tiene script nuevo,
      `scripts/monitor_ca02.py` — poll periódico a `GET /health` +
      `GET /metrics/starlink/latest` del backend, detecta tanto "el backend
      no responde" como "el extractor dejó de publicar" (gap > 10 min entre
      mediciones), log JSONL + resumen PASS/FAIL al final. Smoke-testeado
      contra un servidor HTTP falso en esta sesión (`_check_once` parsea
      correctamente ambas respuestas) — sin correr las 72h reales, que
      recién tienen sentido con el extractor validado en el LIT (semana 10).
- [x] Verificar coherencia total: paquete MQTT Starlink == esquema DER —
      mismo mecanismo que CA-08 arriba, es la misma verificación.

> 🔗 Milestone: sistema completo integrado, mock y real, corriendo end-to-end.

## Semana 21 — Pruebas de estrés (TIME_WARP + Locust) `[INT]` — script listo, sin ejecutar

- [ ] ⚠️ Ejecutar pruebas de estrés sobre el pipeline de red con Locust —
      **script escrito** (`tests/stress/locustfile.py`, `requirements-stress.txt`,
      adaptado del snippet de referencia de `docs/08_Plan_QA.md` §6.5 a la
      API real del backend), **no ejecutado**: necesita la pila levantada
      con `TIME_WARP_FACTOR` alto (perfil `stress`, ya existía en
      `docker-compose.yml` desde antes de esta sesión) y, para que el
      resultado valga para RNF-01, correr contra el RPi5 real — no la PC de
      desarrollo. Comando documentado en el docstring del propio archivo.
- [ ] Medir throughput máximo sostenible en el RPi5 sin pérdida de datos de
      red — depende de lo anterior.

## Semana 22 — Campaña inicial de medición `[INT]`

- [ ] Dejar corriendo el sistema real varios días para recolectar datos de red
- [ ] Primer análisis exploratorio: latencia/jitter/pérdida vs condiciones ambientales

## Semana 23 — Redacción de memoria y documentación `[IND]`

- [x] Documentar tu módulo: arquitectura, decisiones (ADRs relacionados a
      Starlink), procedimiento de despliegue — la parte "repo" ya está
      cerrada: `docs/05_ADR.md` (ADR-01 a ADR-18, todos con Contexto/
      Alternativas/Decisión/Pros-Contras), `README.md` (reescrito Fase 4,
      cubre despliegue completo con los 4 servicios propios). Lo que queda
      es prosa de la memoria en sí (documento académico aparte, fuera del
      repo) — no se redacta acá sin pedido explícito.
- [ ] Aportar figuras/gráficos de tus dashboards para la memoria técnica —
      necesita Grafana corriendo con datos reales para las capturas
      (imposible sin sesión de navegador/Docker en este entorno) — pendiente
      de la próxima sesión con acceso a la pila real.

## Semana 24 — Revisión final y cierre `[INT]`

- [ ] Completar tu parte de la checklist de QA de entrega final
- [ ] Correcciones finales sobre tu módulo según feedback del director/co-director

> 🔗 Milestone: cierre del Proyecto Integrador.

### 2026-08-19 — Intento de pasar el Estado de los 18 ADR a "Aceptado" (revertido)

Se intentó cambiar el campo "Estado" de los 18 ADR (`docs/05_ADR.md`, tabla resumen §2
y el atributo `Estado` de cada entrada individual) de "Propuesto" a "Aceptado", a pedido
de Pavet García, quien indicó que el director (Henn) ya los había dado por aprobados en
una instancia presencial previa al inicio del repo (~27/06/2026).

El hook de enforcement de la skill `adr-check` bloqueó el commit: su regla es explícita
("Nunca cambiar el campo 'Estado' de un ADR a 'Aceptado' — eso lo decide el director")
y no distingue el motivo — el registro formal de "Aceptado" tiene que originarse en una
acción explícita del director sobre el propio documento, no en un commit del agente que
infiere la aprobación a partir de lo que cuenta el alumno. El cambio se revirtió; **los
18 ADR siguen en "Propuesto"** en `docs/05_ADR.md`, sin tocar contenido de decisión,
contexto ni las enmiendas de campo ya documentadas (grpcurl en ADR-01, tópico status por
dominio en ADR-03/04, ADR-16/17/18).

Ver "Pendiente — revisar con director/co-director" (arriba) para la nota de constancia
informal y el camino para destrabarlo (confirmación escrita del director, o que él mismo
edite el campo).

### 2026-08-19/20 — Broker MQTT compartido desplegado en la VM de la cátedra

Ver `docs/01_ADR.md` de `starlink-station-stack` para la decisión completa (VM aloja
solo el broker, resto sigue en la RPi5 — RAM insuficiente ahí para la pila completa,
~1GB). Ejecutado y verificado hoy:

- Docker + Compose instalados en la VM (Debian 13/trixie — sin `docker-compose-plugin`
  en sus repos, se usó el paquete `docker-compose`, que igual instala Compose v2.26.1).
- Broker Mosquitto levantado con auth (`allow_anonymous false`), puerto externo `5883`.
- **2 bugs reales encontrados y corregidos en el despliegue** (no estaban probados
  hasta hoy, quedaron en `starlink-station-stack` commit `57aa2c5`):
  1. El healthcheck no pasaba credenciales → fallaba "not authorised" en loop infinito,
     contenedor nunca pasaba de `health: starting`. Corregido con
     `MQTT_HEALTHCHECK_USER`/`PASSWORD` vía `.env` propio de esa carpeta.
  2. El `passwordfile` con permisos `600` (dueño `federico.isaia.soria`, el usuario del
     host) no era legible por el proceso Mosquitto dentro del contenedor (UID distinto,
     `1883`) → "Unable to open pwfile", el contenedor crasheaba en loop. Se dejó en
     `644` como workaround funcional; **candidato a mejorar más adelante** (sacar
     el `:ro` de los mounts de `mosquitto.conf`/`passwordfile` para que el propio
     entrypoint del `chown` interno funcione, en vez de depender de permisos world-readable).
- **Verificado end-to-end desde afuera de la VM** (mi laptop, por internet, con un
  contenedor `eclipse-mosquitto` efímero): `mosquitto_pub`/`mosquitto_sub` con
  credenciales funcionan; sin credenciales, la conexión es rechazada
  ("not authorised") — confirma que la postura de seguridad (ADR-14, extendida acá)
  se cumple.

**Bloqueado — no pude completarlo yo**: apuntar la RPi5 al broker de la VM
(`MQTT_HOST=35.224.141.221`, `MQTT_PORT=5883` + credenciales en su `.env`, después
`docker compose restart acquisition consumer`). La RPi5 (`leonode-rpi`,
`172.18.147.143`) no es alcanzable desde esta sesión — "No route to host", es la red
del LIT y esta laptop no tiene una ruta hacia ahí ahora mismo (sin Tailscale local
tampoco, desinstalado antes en esta misma sesión a pedido de la usuaria). Pendiente de
que alguien lo haga estando en esa red, o de conseguir otra vía de acceso.

Ver también `starlink-station-stack/docs/INTEGRATION_CHECKLIST.md` para el estado
consolidado (ítems 1 y 2 del checklist pasan a ✅ con esto).
