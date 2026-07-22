# CLAUDE.md — Contexto del Proyecto Integrador

> Este archivo es leído automáticamente por Claude Code al iniciar sesiones en este repo.
> Contiene el contexto que normalmente vive en las conversaciones web (claude.ai), para que
> Claude Code no tenga que redescubrirlo cada vez. Mantenerlo actualizado a medida que se
> tomen nuevas decisiones — es un documento vivo, igual que el ADR.

## 1. Qué es este proyecto

**Proyecto Integrador (PI)** — Escuela de Ingeniería en Computación, FCEFyN/UNC.

**Título:** Despliegue y extensión de una estación de medición para el análisis experimental
de redes satelitales LEO comerciales (Starlink), con integración de sensado ambiental,
monitoreo remoto y visualización de datos.

**Objetivo central:** integrar un nodo de medición local (Córdoba, LIT) a un testbed
internacional colaborativo (University of Victoria, University of Manitoba, University of
Waterloo, Memorial University) que mide performance de red Starlink, y extenderlo con:
- Sensado ambiental (temperatura, humedad, presión) correlacionable con métricas de red.
- Backend de ingesta/consulta de series temporales.
- Dashboards de visualización (Grafana).
- Videomonitoreo opcional del entorno físico de la antena.

**Alumnos:** Aldana Micaela Pavet García, Federico Isaia Soria
**Director:** Mgrt. Ing. Santiago Martin Henn | **Co-director:** Dr. Renato Cherini
**Laboratorio:** LIT — FCEFyN/UNC

### Fuera de alcance (importante no sobre-construir)
- Demostrar causalidad física entre clima y performance de red (solo correlación observacional).
- Ingeniería inversa de mecanismos internos propietarios de Starlink.
- Análisis estadístico profundo / modelos predictivos.
- Gestión de otros nodos del testbed (este PI cubre únicamente el nodo Córdoba).
- Apps móviles nativas.

## 1.1 Mi foco de trabajo en este repo

**Soy Aldana. Trabajo específicamente en el módulo de conexión a la antena Starlink**
(Capa 1 — Adquisición, componente "script telemetría Starlink" / `mock_starlink`). Fede
Isaia Soria trabaja en el módulo de sensado ambiental (BME280/ESP32). El resto del sistema
(broker, consumer, DB, backend, Grafana) es compartido o de responsabilidad conjunta.

**Importante:** mi módulo no es un proyecto aislado — es una pieza de un objetivo mayor (la
estación de medición completa integrada al testbed internacional, ver §1). Cuando trabajo en
este repo, las decisiones de mi módulo tienen que seguir siendo compatibles con las
interfaces compartidas (esquema MQTT, contrato con el consumer, esquema DER) para no romper
la integración con el módulo de Fede ni con el resto de la pila.

### Alcance técnico del módulo Starlink

- Extracción de datos desde la antena (Dishy McFlatface) vía su servidor gRPC local
  (`192.168.100.1:9200`), usando Protobuf nativo (ver ADR-01). Referencia de la comunidad:
  repositorio `starlink-grpc-tools` (Sparky8512, GitHub).
- Conversión Protobuf → dict Python → validación Pydantic (`StarlinkPayloadIn`) → JSON
  (ADR-01). **No** introducir Protobuf ni otro formato binario aguas abajo de este punto.
- Esquema del paquete (campos clave): `latency_ms`, `jitter_ms`, `packet_loss_pct`,
  `throughput_down_bps`, `throughput_up_bps`, `snr_db`, `is_obstructed`, `satellite_count`,
  `schema_version` — debe coincidir exactamente con `docs/03_SRS.md` §5.1 y `docs/06_DER.md`
  (`network_metrics`). Cualquier cambio de esquema se propaga a ambos documentos.
- Publicación en el tópico MQTT `starlink/metrics/<node_id>`, QoS 1.
- Mock stateful con Random Walk + inyección de caos (obstrucciones, handovers, microcortes) —
  ADR-06 — empaquetado como microservicio Docker independiente (ADR-07), parametrizable con
  `CHAOS_PROFILE` y `TIME_WARP_FACTOR` (ADR-08) para backfill acelerado.
- Manejo de errores de conexión (antena no disponible, timeout gRPC, reconexión automática al
  broker, cambios de firmware que rompan el esquema Protobuf) sin colapsar el contenedor —
  logging estructurado (JSON logs) + reintento.
- Intercambiable 1:1 con hardware real: mismo tópico, misma morfología de paquete — el
  consumer/DB/Grafana no notan el switch mock → antena real (§5 de este documento).

### Roadmap de mi módulo (24 semanas, alineado al Gantt del proyecto)

Convención: **[IND]** = trabajo individual sobre mi módulo. **[INT]** = punto de integración
con el módulo de Fede o con la pila compartida — coordinar antes de tocar código compartido.
**[HW]** = ya requiere hardware real (antena/RPi5), no mocks.

| Semana(s) | Foco | Tipo |
|---|---|---|
| 1 | Carpeta `src/mock_starlink/`, estudio del gRPC de la antena, esquema JSON del paquete (ADR-01), validador `StarlinkPayloadIn` (Pydantic), primeros tests (suite UT-01) | [IND] |
| 2 | Ampliar UT-01 (1000 payloads sin `ValidationError`, casos límite: nulos, `packet_loss_pct` fuera de rango, `schema_version` incorrecto). Setup Python 3.11 (venv, grpcio, pydantic). Arranca junto a Fede la definición de ADR-01 a ADR-05 | [IND]→[INT] |
| 3 | Broker MQTT (Mosquitto v5.0) por Docker Compose junto con Fede, definir tópico Starlink, publicar JSON al broker (no consola), verificar con `mosquitto_sub`/MQTT Explorer | **[INT] — primera integración con Fede** |
| 4 | Mock stateful con Random Walk (ADR-06), inyección de caos, empaquetado como microservicio Docker (ADR-07), publicación continua | [IND] |
| 5 | Ajuste de frecuencia de muestreo, `TIME_WARP_FACTOR` (ADR-08), dejar el mock estable para el consumer conjunto | [IND] |
| 6 | Consumer MQTT conjunto con Fede: escucha ambos tópicos, Database per Service (ADR-10), insertar en `network_metrics`, manejo de errores de deserialización, flujo E2E mock→broker→consumer→TimescaleDB | **[INT] — segunda integración, con persistencia real** |
| 7 | Índices de `network_metrics` (`idx_netmet_node_time`, `idx_netmet_loss`, `idx_netmet_obstructed`), consultas filtradas, CHECK constraint de `packet_loss_pct`, coherencia `node_id` con `station_metadata` | [IND] |
| 8 | Dashboard Grafana conectado a `starlink_health_db`: paneles de latencia/jitter/pérdida, throughput, `satellite_count`/`is_obstructed` | [IND] |
| 9 | Endpoints `GET /api/v1/metrics/starlink`, `/summary`, `/latest`; auth por API Key (`X-API-Key`); logging estructurado en extractor, consumer y backend | **[INT] — logging antes del hardware real** |
| 10 | **Pasaje a hardware real**: reemplazar el mock por conexión gRPC real (`192.168.100.1:9200`), correr en RPi5, validar E2E físico, confirmar con Fede que ambos módulos conviven en el mismo RPi5 | **[HW] — fin del desarrollo desacoplado de hardware** |
| 11–12 | Suites de integración (IT-01), `pytest-cov --cov-fail-under=80`, CI en GitHub Actions | [IND] |
| 13–14 | Soporte a Fede en integración de APIs externas: no romper el esquema del consumer compartido, ajustar routing MQTT si hace falta | [INT — Fede lidera] |
| 15–16 | Continuous Aggregates en TimescaleDB, reconexión automática del broker en el extractor, colaborar en postura Zero Trust (ADR-14) | [IND]+[INT] |
| 17–18 | (Opcional/secundario) Colaborar en streaming de videomonitoreo, verificar que no compita por ancho de banda con las mediciones de red | [INT] |
| 19–20 | Suite E2E completa sobre pila de producción, validar **CA-01 y CA-08** para mi módulo, coherencia total paquete MQTT ↔ esquema DER | **[INT] — sistema integrado end-to-end** |
| 21 | Pruebas de estrés (Locust) sobre el pipeline de red, throughput máximo sostenible en RPi5 sin pérdida de datos | [INT] |
| 22 | Campaña inicial de medición, primer análisis exploratorio latencia/jitter/pérdida vs. clima | [INT] |
| 23 | Documentar mi módulo: arquitectura, ADRs relacionados a Starlink, despliegue; figuras de mis dashboards para la memoria | [IND] |
| 24 | Checklist de QA de entrega final (mi parte), correcciones según feedback del director/co-director | [INT] — **cierre del PI** |

**Al iniciar cualquier sesión de trabajo sobre este módulo**, ubicar en qué semana/etapa
estamos (preguntar si no es evidente por el estado del código) y verificar contra esta tabla
qué tareas corresponden y si hay una integración pendiente con el módulo de Fede antes de
avanzar solo.

## 2. Documentos fuente (autoritativos)

Los documentos formales del proyecto están en `docs/` (ver §7). Ante cualquier duda de
diseño, **estos documentos son la fuente de verdad**, priorizados en este orden:

1. `docs/05_ADR.md` — decisiones arquitectónicas y su razonamiento (por qué, no qué).
2. `docs/03_SRS.md` — requerimientos funcionales/no funcionales, criterios de aceptación.
3. `docs/06_DER.md` — modelo de datos, esquema SQL, hypertables.
4. `docs/07_API_REST.md` — contrato de la API.
5. `docs/08_Plan_QA.md` — estrategia y suites de testing.
6. `docs/01_Propuesta.md` — contexto académico original, motivación, alcance, cronograma.

Si una instrucción de esta sesión contradice un ADR sin justificación explícita, avisar
antes de proceder — probablemente sea una decisión que hay que registrar como nuevo ADR,
no un cambio silencioso.

## 3. Arquitectura del sistema (resumen)

Sistema en 5 capas, cada una en contenedor Docker independiente:

| Capa | Componentes | Tecnología |
|---|---|---|
| 1 — Adquisición | Script telemetría Starlink, script BME280, APIs meteo externas | Python 3.11, C++ (ESP32/Arduino) |
| 2 — Mensajería | Message broker | MQTT — Eclipse Mosquitto v5.0 |
| 3 — Persistencia | DB Starlink Health, DB Meteo (una por servicio) | PostgreSQL 16 + TimescaleDB 2.x |
| 4 — Backend | API REST ingesta/consulta series temporales | Python + FastAPI |
| 5 — Observabilidad | Dashboards red, clima, videomonitoreo | Grafana OSS (LTS) |

**Todo se desarrolla primero con mocks** (datos sintéticos) antes de tener hardware real —
ver §5. El diseño explícitamente permite reemplazar mock → hardware real sin cambiar código
downstream (mismo tópico MQTT, misma morfología de paquete).

### Flujo de datos
```
[Antena Starlink / gRPC:9200]  [ESP32 + BME280]  [APIs meteo externas]
         │ Protobuf                  │ MQTT               │ HTTP
         ▼                           ▼                     ▼
   [dict Python → Pydantic] ──▶ [MQTT Broker: Mosquitto, QoS 1] ◀──
                                       │
                          ┌────────────┴────────────┐
                          ▼                          ▼
                 [Consumer → starlink_health_db]  [Consumer → meteo_db]
                       (PostgreSQL+TimescaleDB)   (PostgreSQL+TimescaleDB)
                          │                          │
                          └──────────┬───────────────┘
                                     ▼
                          [Backend API REST (FastAPI)]
                                     │
                                     ▼
                          [Grafana — dashboards + videomonitoreo]
```

## 4. Decisiones arquitectónicas clave (ADR) — QUÉ y POR QUÉ

Todas con estado **Propuesto** al 11/jun/2026 (verificar `docs/05_ADR.md` por si cambió el estado).
Detalle completo y alternativas rechazadas: `docs/05_ADR.md`, Apéndice B.

| ID | Decisión | Resumen |
|---|---|---|
| ADR-01 | **Serialización híbrida**: Protobuf (antena) → dict Python → **Pydantic** (validación) → **JSON** (todo lo downstream) | Se rechazó Protobuf end-to-end (no integra bien con Grafana/TimescaleDB) y JSON puro sin validación (riesgo de corromper la DB silenciosamente). |
| ADR-02 | Sensor **BME280** (I2C digital) | Sobre analógicos: sin ADC externo, calibrado de fábrica, menor sensibilidad a EMI de la antena. |
| ADR-03 | **ESP32 como Sensor Gateway Node**, MQTT nativo | El RPi5 nunca toca el hardware del sensor directamente; desacoplamiento físico completo. |
| ADR-04 | **MQTT** (sensores→broker, QoS 1) + **ORM/TCP** (consumer→DB) | Rechazado REST HTTP síncrono para IoT (pérdida de datos ante microcortes) y conexión SQL directa desde el sensor (viola menor privilegio). |
| ADR-05 | **Python 3.11** como lenguaje único de la capa RPi5; **C++ (Arduino IDE)** solo para el ESP32 | Se descartó stack híbrido de 3 lenguajes por ser inmanejable para el equipo. |
| ADR-06 | Mock de telemetría Starlink: **Stateful, Random Walk + inyección de caos** (`CHAOS_PROFILE`: CALM/STORM/HANDOVER_HEAVY) | Sobre replay de CSV (estático) o ruido puro (sin inercia temporal, gráficos inútiles). |
| ADR-07 | Mocks **desacoplados como microservicios Docker independientes** (`mock_bme280`, `mock_api_ext`) | Un mock unificado no valida la arquitectura real de productores concurrentes (viola SRP). |
| ADR-08 | Backfill vía **ingesta orgánica E2E** con `SIMULATION_SPEED_FACTOR` (ej. 60x) | Los INSERT masivos por SQL solo prueban que existen tablas, no el pipeline completo. |
| ADR-09 | **Eclipse Mosquitto (MQTT v5.0)**, QoS 1, `clean_session=False`, LWT configurado | Sobre RabbitMQ (pesado para RPi5) y Redis Pub/Sub (sin persistencia offline). |
| ADR-10 | **Database per Service**: `starlink_health_db` y `meteo_db` separadas | Evita cascading failure; correlación se hace en Grafana vía Data Blending (Outer Join by Time). |
| ADR-11 | **PostgreSQL 16 + TimescaleDB 2.x** | Recomendación explícita del director. Hypertables, compresión columnar, continuous aggregates, retención automática. Sobre InfluxDB (curva de Flux) y Postgres puro (index thrashing a escala). |
| ADR-12 | **Docker Engine + Docker Compose v2**, todo contenerizado, imágenes slim/alpine, versiones pinneadas | Habilita migración local→nube determinística (ver §6). |
| ADR-13 | **Grafana OSS** para visualización, dashboards como código (JSON provisioning) | Se descartó frontend a medida (React/Vue): semanas de desarrollo sin valor directo para la investigación de redes. |
| ADR-14 | **Postura Zero Trust local**: solo el puerto de Grafana se expone externamente, con filtrado de IP | — |
| ADR-15 | Mock de videomonitoreo: **microservicio Flask con stream MJPEG a 5 FPS, JPEG quality 50** | Consumo estimado 200–400 kbps (~0.2% del ancho de banda Starlink), despreciable para las mediciones. Sobre placeholder JPG estático (no valida streaming real). |

## 5. Estrategia de mocks (desarrollo sin hardware)

El sistema completo se desarrolla y valida ANTES de contar con hardware físico:

- **Mock Starlink** (`mock_starlink`): script Python, stateful, cada 60s. Latencia ~N(35,5)ms,
  jitter ~Exp(2)ms, pérdida ~Bernoulli(0.005), throughput_down ~N(180,30)Mbps. Inyecta
  degradaciones ocasionales (spikes >200ms, pérdidas >5%) vía `CHAOS_PROFILE`.
- **Mock BME280** (`mock_bme280`): cada 60s. Temperatura sinusoidal diaria (10–35°C, Córdoba),
  humedad inversamente correlacionada, presión con deriva lenta, + ruido gaussiano.
- **Backfill**: mismo código de producción, acelerado con `SIMULATION_SPEED_FACTOR` (no scripts
  SQL de seeding separados — eso no valida el pipeline real).
- **Switching mock → hardware real**: apagar contenedor mock, encender servicio real. **Sin
  cambios de código** — mismo tópico MQTT, misma morfología de paquete (ADR-01).

Cuando trabajes en cualquier componente de adquisición, asumí por defecto que se está
desarrollando/testeando contra mocks salvo que se indique lo contrario.

## 6. Plan de migración Local → Nube

| Etapa | Entorno | Criterio de salida |
|---|---|---|
| 0 | PC desarrollo, Docker Compose, solo mocks | Dashboards con 30 días de datos sintéticos; RF-01 a RF-40 validables |
| 1 | RPi5 en LIT (on-premises), hardware real | 72h operación continua sin intervención manual |
| 2 | Cloud (VPS/servidor universitario), RPi5 solo adquiere/publica MQTT | Cero pérdida de datos; solo cambian `DB_HOST`/`MQTT_HOST` en `.env` |
| 3 (futuro) | Testbed internacional multi-nodo | Primer dataset conjunto Córdoba–Canadá |

La migración es de bajo riesgo porque: todo corre en contenedores idénticos, la config de
conexión está externalizada en `.env`, y TimescaleDB exporta/importa con `pg_dump` estándar.

## 7. Estructura de repo esperada

```
docs/
  01_Propuesta.md
  03_SRS.md
  05_ADR.md
  06_DER.md
  07_API_REST.md
  08_Plan_QA.md
services/
  acquisition/          # scripts telemetría Starlink + cliente BME280/ESP32
  mocks/
    mock_starlink/
    mock_bme280/
    mock_api_ext/
    mock_video/         # Flask MJPEG stream, ver ADR-15
  broker/                # config Mosquitto
  consumer/              # MQTT → TimescaleDB (router por dominio: red / meteo)
  backend/               # FastAPI
  grafana/
    provisioning/
      datasources/
      dashboards/
docker-compose.yml
.env.example
README.md
```
(Ajustar si el repo real difiere — este es el layout implícito en el SRS/ADR, no un mandato rígido.)

## 8. API REST — resumen de endpoints

Base: `/api/v1`. Auth: API Key en header (ver `docs/07_API_REST.md` §2). Envelope de
respuesta estandarizado con éxito/error consistente (§3 del documento).

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| GET | `/health` | Estado del sistema y conectividad a DBs | No |
| GET | `/metrics/starlink` | Series temporales telemetría Starlink | Sí |
| GET | `/metrics/starlink/summary` | Estadísticas agregadas (avg, p95, min, max) | Sí |
| GET | `/metrics/starlink/latest` | Última medición por nodo | Sí |
| GET | `/metrics/env` | Series temporales ambientales | Sí |
| GET | `/metrics/env/summary` | Estadísticas ambientales agregadas | Sí |
| GET | `/metrics/env/latest` | Última medición ambiental por nodo/fuente | Sí |
| GET | `/nodes` | Lista de nodos registrados y su estado | Sí |
| GET | `/nodes/{node_id}` | Detalle de un nodo | Sí |
| POST | `/ingest/starlink` | Ingesta manual — solo testing/mocks (desactivable) | Sí |
| POST | `/ingest/env` | Ingesta manual ambiental — solo testing/mocks | Sí |

## 9. Modelo de datos — resumen

Dos DBs separadas (ADR-10), ambas PostgreSQL+TimescaleDB:

- **starlink_health_db**: `network_metrics` (hypertable), `network_tests`, continuous
  aggregates `net_hourly` / `net_daily`.
- **meteo_db**: `env_metrics` (hypertable), continuous aggregate `env_hourly`.
- Metadata compartida/relacional: `station_metadata`, `sensor_catalog`.

Detalle de columnas, tipos, índices y políticas de retención: `docs/06_DER.md`.

## 10. Criterios de aceptación del sistema (CA-01 a CA-08)

Resumen — ver `docs/03_SRS.md` §13 para el detalle de evidencia esperada:

- **CA-01/02**: flujo end-to-end validado con mocks y luego con hardware real (72h sin errores).
- **CA-03**: persistencia ante `docker-compose down/up` (< 3 min de recuperación).
- **CA-04**: dashboard de correlación Red-Clima con datos reales.
- **CA-05**: acceso remoto seguro (SSH sin contraseña, Grafana accesible vía URL pública).
- **CA-06**: reproducibilidad — un tercero despliega todo siguiendo el README en < 30 min.
- **CA-07**: plan de migración documentado y con Etapas 0 y 1 ejecutadas.
- **CA-08**: interfaces documentadas y consistentes con el código en producción.

## 11. Convenciones para trabajar en este repo

- **Stack por defecto**: Python 3.11 en todo lo que no sea firmware ESP32 (C++/Arduino IDE).
- **Todo se conteneriza.** Nuevo servicio = nuevo Dockerfile + entrada en `docker-compose.yml`.
  Imágenes base slim/alpine, versiones pinneadas (nunca `:latest` en producción).
- **JSON validado con Pydantic** es el formato de intercambio interno (ADR-01) — no introducir
  Protobuf ni otro formato binario más allá del límite antena↔extractor.
- **MQTT QoS 1**, tópicos jerárquicos (`starlink/metrics/<node_id>`, `meteo/sensor/<node_id>`),
  `clean_session=False` en consumers, LWT en productores.
- **Config de conexión siempre en `.env`**, nunca hardcodeada — es la base de la migración
  local→nube sin cambios de código.
- Antes de agregar una dependencia o cambiar una decisión ya tomada en el ADR, marcarlo
  explícitamente como candidato a nuevo ADR (no pisar silenciosamente una decisión "Propuesta"
  o "Aceptada").
- El plan de pruebas (`docs/08_Plan_QA.md`) define niveles: unitarias (pytest), integración,
  E2E contra criterios de aceptación del SRS, y pruebas de estrés (Locust) usando el mismo
  mecanismo de aceleración temporal que el backfill (§5).

## 12. Decisiones pendientes / abiertas

Todos los ADR están en estado **Propuesto**, no **Aceptado** (al 11/jun/2026) — confirmar con
el director antes de asumirlos como definitivos si hay ambigüedad. Comentarios abiertos en el
ADR (ver `docs/05_ADR.md`, sección "Comments") incluyen pedidos de aclaración sobre: tamaño de
mensajes, si las apps deben ser explícitamente "stateless", y definiciones pendientes en varias
secciones — revisar antes de dar por cerrado un diseño.

---
*Última actualización de este archivo: generado a partir de la Propuesta de PI, el SRS v1.0,
el ADR Log v2.0, el DER, la Especificación de API REST y el Plan de Pruebas y QA del proyecto.
Si el proyecto avanza y estos documentos cambian, regenerar o editar este archivo a mano.*
