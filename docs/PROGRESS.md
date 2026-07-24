# PROGRESS.md — Módulo Starlink (Aldana)

> Estado de avance real del módulo de conexión a la antena Starlink, alineado al roadmap de
> `CLAUDE.md` §1.1. Editar a mano o pedirle a Claude Code que lo actualice al cerrar una tarea.
> Convención: **[IND]** trabajo individual · **[INT]** integración con el módulo de Fede ·
> **[HW]** requiere hardware real.

**Última actualización:** semana 2 completada. ADR-01 a ADR-05 revisados y sus puntos
abiertos cerrados del lado de Aldana (ver "Corregido esta sesión") — **falta que Fede
confirme los puntos de ADR-02/ADR-03 (BME280, backoff ESP32, LWT) que se completaron
con valores por default**. Arrancando semana 3 (broker MQTT): `docker-compose.yml` y
`services/broker/mosquitto.conf` ya creados y verificados localmente (`docker compose
up` levanta el broker, pub/sub probado a mano) — falta correr la integración real con
el mock y con el productor de Fede.

---

## Pendiente — revisar con director/co-director

- **Drift entre `docs/03_SRS.md` §5.1 y `docs/06_DER.md` (network_metrics) / código**:
  el SRS describe el paquete de telemetría Starlink con otro vocabulario y unidades
  (`throughput_down_mbps`/`throughput_up_mbps` en Mbps, `obstruction_pct` y
  `signal_quality` en vez de `is_obstructed`/`snr_db`), que no coincide con el DER ni
  con `src/mock_starlink/schema.py` (que sigue al DER: `throughput_down/up_bps` en bps,
  `is_obstructed` booleano, `snr_db` en dB). Es un drift preexistente, no introducido
  por ningún cambio reciente de código — detectado por la skill `adr-check`. No se
  resuelve unilateralmente: queda anotado acá para que el director/co-director defina
  cuál de los dos documentos se actualiza (ver `CLAUDE.md` §12, "Decisiones
  pendientes").

- **Alcance de `net_health/iperf_test` en ADR-04**: la tabla de tópicos de ADR-04 tiene
  una fila para un test activo con iPerf3 que no está cubierta por el SRS y cuyo alcance
  no quedó claro (comentario propio [^c5] en el ADR: "no queda claro, para qué?"). No
  forma parte del "Alcance técnico del módulo Starlink" descrito en `CLAUDE.md` §1.1
  (que solo cubre telemetría pasiva vía gRPC). Definir con el director si iPerf3 activo
  entra en el alcance del PI o si esa fila se elimina del ADR.

- **Decisión pendiente del director sobre "stateless" (ADR-12, [^c14]) vs. mock stateful
  (ADR-06)**: el director dejó un comentario pidiendo aclarar que "las apps van a ser
  stateless", lo cual en principio choca con que ADR-06 define el mock de Starlink como
  explícitamente stateful (random walk con memoria del último valor). No es
  necesariamente una contradicción real: "stateful" en ADR-06 describe la lógica de
  generación de datos dentro del proceso en memoria (para que los gráficos tengan
  inercia temporal realista), mientras que "stateless" en el sentido de infraestructura
  (12-factor apps) se refiere a que el contenedor no depende de un volumen local
  persistente para funcionar — puede reiniciarse sin coordinación especial porque el
  estado que importa (las métricas ya generadas) vive en la base de datos, no en el
  mock. Falta dejarlo explícito por escrito en el ADR para que no quede ambiguo — no
  resuelto todavía.

- **ADR-06 (tabla estadística del mock) tiene el mismo drift de vocabulario que ya
  estaba anotado arriba entre SRS/DER**: usa `throughput_down/up_mbps`,
  `obstruction_pct` y `signal_quality` (vocabulario del SRS) en vez de
  `throughput_down/up_bps`, `is_obstructed` y `snr_db` (vocabulario del DER y de
  `schema.py`). No es un conflicto nuevo, es el mismo — se extiende la nota para que
  el director sepa que también afecta a ADR-06. La implementación del mock stateful
  sigue al DER/`schema.py` (ya es el estándar de facto del proyecto).

- **`docs/03_SRS.md` §10.3 contradice a ADR-08 sobre el mecanismo de backfill**: el SRS
  describe un "script de backfill" que inserta directamente en las hypertables vía SQL
  — exactamente la Alternativa A que ADR-08 rechaza explícitamente a favor de la
  ingesta orgánica E2E vía `TIME_WARP_FACTOR`. La implementación de semana 5 sigue a
  ADR-08 (es lo que pide el roadmap de `CLAUDE.md` §1.1); queda anotado para que el
  director defina si el SRS se actualiza.

- **El fixture de ejemplo embebido en `docs/08_Plan_QA.md` (bloque `conftest.py`) usa
  un tercer vocabulario** (`station_id`, `source_module`, `pop_ping_latency_ms`,
  `pop_ping_drop_rate`, `downlink/uplink_throughput_bps`) que no coincide ni con el DER
  ni con `schema.py` ni con el resto del propio Plan de QA (las tablas UT-01/UT-04 sí
  usan `node_id`/`metrics.latency_ms`/etc.). Parece un borrador viejo — no se usa como
  referencia para la implementación.

---

## Corregido esta sesión

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

---

## Coordinación pendiente con Fede

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
- [ ] Modificar el script/mock para publicar el JSON al broker en vez de imprimir por consola
- [ ] Verificar mensajes con `mosquitto_sub` / MQTT Explorer
- [ ] Confirmar, junto con Fede, que ambos mocks publican y los datos llegan al broker

> 🔗 Milestone: primera vez que los dos módulos comparten el broker.

## Semana 4 — Mock de telemetría Starlink (stateful) `[IND]`

- [ ] Implementar el Mock Stateful con Random Walk (ADR-06) en vez de números aleatorios puros
- [ ] Agregar inyección de caos: obstrucciones, handovers, microcortes de conectividad
- [ ] Empaquetar el mock como microservicio Docker independiente (ADR-07)
- [ ] Publicar continuamente al broker respetando el esquema de semana 1

## Semana 5 — Mock Starlink (cont.) + preparación del consumer `[IND]`

- [ ] Ajustar frecuencia de muestreo para que sea coherente con lo que espera TimescaleDB
- [ ] Agregar el parámetro `TIME_WARP_FACTOR` al mock (ADR-08) para backfill acelerado
- [ ] Dejar el mock corriendo de forma estable como base para el consumer conjunto

## Semana 6 — Consumer MQTT conjunto `[INT — segunda integración con Fede]`

- [ ] Diseñar junto a Fede el consumer que escucha ambos topics (Starlink y BME280/meteo)
- [ ] Implementar Database per Service (ADR-10): `starlink_health_db` y `meteo_db` separadas
- [ ] Insertar métricas Starlink en la hypertable `network_metrics`
- [ ] Manejar errores de deserialización sin tumbar el consumer
- [ ] Probar el flujo end-to-end: mock → broker → consumer → TimescaleDB

> 🔗 Milestone: convergen ambos módulos por segunda vez, ahora con persistencia real.

## Semana 7 — Validación en TimescaleDB `[IND]`

- [ ] Crear los índices de `network_metrics` (`idx_netmet_node_time`, `idx_netmet_loss`, `idx_netmet_obstructed`)
- [ ] Probar consultas filtradas por `node_id` y rango temporal
- [ ] Verificar que `packet_loss_pct` respeta el CHECK constraint (0–100)
- [ ] Confirmar que `node_id` coincide entre el payload MQTT y `station_metadata`

## Semana 8 — Dashboard Grafana `[IND]`

- [ ] Conectar Grafana a `starlink_health_db`
- [ ] Armar panel de `latency_ms`, `jitter_ms` y `packet_loss_pct` en el tiempo
- [ ] Armar panel de `throughput_down/up_bps` (convertido a Mbps)
- [ ] Agregar panel de `satellite_count` e `is_obstructed` para correlacionar eventos

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
