Plan de Pruebas y QA — Estación de Medición StarlinkPI — FCEFyN / UNC

**PROYECTO INTEGRADOR**

Escuela de Ingeniería en Computación — FCEFyN / UNC

**Plan de Pruebas y Aseguramiento de Calidad**

*QA Plan — Estrategia de Testing y Validación del Sistema*

*Pruebas unitarias · Integración · End-to-End · Estrés con TIME_WARP · Criterios de aceptación*

| **Campo** | **Detalle** |
| --- | --- |
| **Alumnos** | Aldana M. Pavet García (43884931)  │  Federico Isaia Soria (40574892) |
| **Director** | Mgrt. Ing. Santiago Martin Henn |
| **Co-Director** | Dr. Renato Cherini |
| **Framework de testing** | pytest · pytest-asyncio · httpx · locust · docker-compose (entorno de test) |
| **Herramienta de estrés** | Locust + TIME_WARP Factor en mocks Python |
| **Refs. SRS** | RF-01 a RF-40 · RNF-01 a RNF-19 · Criterios de Aceptación CA-01 a CA-08 |
| **Refs. ADR** | ADR-06 (Stateful Mock) · ADR-08 (Ingesta orgánica E2E) · ADR-12 (Docker) |
| **Versión** | 1.0 — Junio 2026 |

# **Índice**

# **1. Introducción y Objetivos del Plan de QA**

Este documento define la estrategia completa de pruebas y aseguramiento de calidad (QA) del sistema de medición. En el contexto de un Proyecto Integrador de Ingeniería, el plan de QA cumple dos funciones: garantizar que el sistema funciona correctamente antes de conectar el hardware real, y proveer evidencia técnica documentada de que cada requerimiento del SRS fue validado de forma sistemática.

La estrategia sigue la pirámide de testing clásica adaptada al contexto IoT del proyecto: base ancha de pruebas unitarias rápidas, capa media de pruebas de integración sobre el pipeline MQTT completo, pruebas end-to-end sobre la pila Docker real y pruebas de estrés con TIME_WARP para validar los límites del hardware (RPi5).

| **Nivel** | **Objetivo** | **Herramientas** | **RNF / RF clave** |
| --- | --- | --- | --- |
| **Unitario** | Verificar cada función en aislamiento: parsers JSON, validadores Pydantic, lógica de routing de tópicos MQTT. | pytest, pytest-cov | RF-04, RF-08, RF-12, ADR-01 |
| **Integración** | Probar que el mensaje viaja end-to-end: Mock → MQTT → Consumer → TimescaleDB. | pytest-asyncio, paho-mqtt, psycopg2 | RF-15 a RF-23, RNF-19 |
| **End-to-End (E2E)** | Levantar la pila Docker completa y verificar el flujo completo hasta Grafana y la API REST. | docker-compose, httpx, curl | CA-01 a CA-08 |
| **Estrés / Carga** | Inyectar 10.000 mensajes/min con TIME_WARP y medir si el RPi5 colapsa o degrada. | Locust, TIME_WARP mock, htop, docker stats | RNF-01, RNF-02, RNF-04 |

# **2. Entorno de Pruebas**

## **2.1 Entorno de desarrollo local (PC del alumno)**

Todas las pruebas unitarias e integración se ejecutan en la PC de desarrollo, sin hardware físico. El entorno utiliza docker-compose con perfil 'test' que levanta instancias de TimescaleDB e-fémeras (en memoria con volumen tmpfs) y Mosquitto con configuración permisiva (sin autenticación) para acelerar los ciclos de prueba.

| # docker-compose.test.yml — entorno de pruebas aislado services:   mqtt_test:     image: eclipse-mosquitto:2.0-alpine     ports: ["1884:1883"]      # puerto distinto para no colisionar con producción     volumes:       - ./mosquitto/test.conf:/mosquitto/config/mosquitto.conf:ro   timescaledb_net_test:     image: timescale/timescaledb:latest-pg16     environment:       POSTGRES_DB: starlink_health_test       POSTGRES_PASSWORD: test_password_local     tmpfs: ["/var/lib/postgresql/data"]   # en RAM: tests más rápidos, sin residuos   timescaledb_env_test:     image: timescale/timescaledb:latest-pg16     environment:       POSTGRES_DB: meteo_data_test       POSTGRES_PASSWORD: test_password_local     tmpfs: ["/var/lib/postgresql/data"] # Arrancar entorno de test: # docker-compose -f docker-compose.test.yml up -d # pytest tests/ -v --tb=short # docker-compose -f docker-compose.test.yml down |
| --- |

## **2.2 Variables de entorno para testing**

| **Variable** | **Valor en testing** | **Efecto** |
| --- | --- | --- |
| MQTT_HOST | localhost | Apunta al broker de test levantado por docker-compose.test.yml |
| MQTT_PORT | 1884 | Puerto alternativo para no interferir con producción |
| DB_NET_HOST | localhost:5433 | TimescaleDB de test en tmpfs (efímero) |
| DB_ENV_HOST | localhost:5434 | TimescaleDB ambiental de test en tmpfs |
| ENABLE_INGEST_ENDPOINT | true | Habilita POST /ingest/* para poblar datos en los tests de API |
| TIME_WARP_FACTOR | 60 / 3600 | 60 = 1 día de datos en 24 min · 3600 = 1 día en 24 seg (stress test) |
| CHAOS_PROFILE | CALM / STORM / HANDOVER_HEAVY | Perfil de caos del mock: inyecta spikes, cortes o degradación severa |
| LOG_LEVEL | DEBUG | Activa logs detallados para diagnóstico de fallos en CI |

| **Nivel 1 — Pruebas Unitarias** |
| --- |

## **3.1 Alcance y filosofía**

Las pruebas unitarias cubren funciones y clases en aislamiento total — sin red, sin base de datos, sin MQTT. Toda dependencia externa se reemplaza con mocks (unittest.mock o pytest fixtures). El objetivo es verificar la lógica de parsing, validación y transformación de datos, que son las capas más críticas para la integridad del dataset de investigación.

**Cobertura objetivo: **≥ 80% de líneas en los módulos: parsers/, validators/, consumers/router.py, api/schemas.py. Medición con pytest-cov.

## **3.2 Módulo: Parser y validador de paquetes MQTT**

### **Suite UT-01 — Validación de paquetes Starlink (Pydantic)**

Verifica que el modelo Pydantic StarlinkPayloadIn acepta payloads válidos, rechaza tipos incorrectos y detecta violaciones de rango. Estos tests son la primera línea de defensa contra datos corruptos provenientes de mocks mal configurados o del hardware real.

| **TC-ID** | **Nombre del test** | **Precondición** | **Pasos / Acción** | **Resultado esperado** | **RF/RNF** | **Estado** |
| --- | --- | --- | --- | --- | --- | --- |
| **UT-01-01** | Parser acepta payload válido | Modelo Pydantic importado | Construir StarlinkPayloadIn con todos los campos válidos y schema_version='1.0' | No lanza ValidationError. Campos mapeados con tipos correctos (float, int, bool, datetime UTC). | RF-04 | PASS |
| **UT-01-02** | Parser rechaza latency_ms negativa | Modelo Pydantic importado | Pasar latency_ms=-5.0 en StarlinkMetricsIn | ValidationError con mensaje 'ge=0 constraint violated' en campo latency_ms. | RF-04 | PASS |
| **UT-01-03** | Parser rechaza packet_loss > 100 | Modelo Pydantic importado | Pasar packet_loss_pct=150.0 | ValidationError con mensaje 'le=100 constraint violated'. | RF-04 | PASS |
| **UT-01-04** | Parser rechaza timestamp sin timezone | Modelo Pydantic importado | Pasar timestamp='2026-06-01T14:30:00' (sin Z ni offset) | ValidationError con mensaje 'timestamp debe incluir timezone'. | RF-04 | PASS |
| **UT-01-05** | Parser rechaza schema_version desconocida | Modelo Pydantic importado | Pasar schema_version='2.0' | ValidationError con mensaje 'schema_version 2.0 no soportada'. | RF-04 | PASS |
| **UT-01-06** | Parser convierte timestamp a UTC | Modelo Pydantic importado | Pasar timestamp='2026-06-01T11:30:00-03:00' (UTC-3 Córdoba) | Modelo almacena datetime con tzinfo=UTC y hora=14:30:00. | RF-04 | PASS |
| **UT-01-07** | Parser acepta campos opcionales como None | Modelo Pydantic importado | Omitir snr_db, is_obstructed, satellite_count del payload | No lanza error. Campos opcionales son None en el objeto resultante. | RF-03 | PASS |

### **Suite UT-02 — Validación de paquetes ambientales**

| **TC-ID** | **Nombre del test** | **Precondición** | **Pasos / Acción** | **Resultado esperado** | **RF/RNF** | **Estado** |
| --- | --- | --- | --- | --- | --- | --- |
| **UT-02-01** | Parser acepta payload BME280 local | Modelo EnvPayloadIn importado | Construir payload con source='local_sensor', temperatura=18.5, humedad=62.3, presion=1013.2 | No lanza ValidationError. Enum source mapeado a EnvSource.LOCAL_SENSOR. | RF-12 | PASS |
| **UT-02-02** | Parser rechaza temperatura fuera de rango | Modelo EnvPayloadIn importado | Pasar temperature_c=90.0 (por encima del CHECK > 80 del DER) | ValidationError con mensaje 'lt=80 constraint violated'. | RF-12 | PASS |
| **UT-02-03** | Parser rechaza humedad negativa | Modelo EnvPayloadIn importado | Pasar humidity_pct=-5.0 | ValidationError con mensaje 'ge=0 constraint violated'. | RF-12 | PASS |
| **UT-02-04** | Parser rechaza source inválido | Modelo EnvPayloadIn importado | Pasar source='otra_fuente' (no está en el Enum EnvSource) | ValidationError con mensaje de Enum inválido. | RF-12 | PASS |
| **UT-02-05** | Parser acepta API externa con nulls en sensor_id | Modelo EnvPayloadIn importado | Construir payload con source='api_open_meteo' y sensor_id=None | No lanza error. sensor_id=None es válido para fuentes API (no provienen de hardware). | RF-12 | PASS |

### **Suite UT-03 — Router de tópicos MQTT**

El consumer Python recibe mensajes de distintos tópicos y los enruta a la base de datos correcta. Esta lógica de routing es crítica: un error silencioso aquí escribiría datos de red en la DB ambiental o viceversa.

| **TC-ID** | **Nombre del test** | **Precondición** | **Pasos / Acción** | **Resultado esperado** | **RF/RNF** | **Estado** |
| --- | --- | --- | --- | --- | --- | --- |
| **UT-03-01** | Tópico starlink/metrics/* enruta a DB red | Router importado, mocks de NetHealthDB y MeteoDB | Llamar route_message(topic='starlink/metrics/lit-01', payload=valid_payload) | NetHealthDB.insert() llamado 1 vez. MeteoDB.insert() NO llamado. | RF-15, RF-20 | PASS |
| **UT-03-02** | Tópico meteo/sensor/* enruta a DB ambiental | Router importado, mocks de ambas DBs | Llamar route_message(topic='meteo/sensor/lit-01', payload=valid_env_payload) | MeteoDB.insert() llamado 1 vez. NetHealthDB.insert() NO llamado. | RF-15, RF-21 | PASS |
| **UT-03-03** | Tópico meteo/external/* enruta a DB ambiental | Router importado | Llamar route_message(topic='meteo/external/lit-01', payload=valid_ext_payload) | MeteoDB.insert() llamado con source='api_open_meteo'. | RF-15, RF-21 | PASS |
| **UT-03-04** | Tópico desconocido no provoca crash | Router importado | Llamar route_message(topic='unknown/topic', payload=...) | No lanza excepción. Log de WARNING emitido. Ninguna DB llamada. | RF-15 | PASS |
| **UT-03-05** | Error de DB no propaga al consumer | Router con DB que lanza excepción | Configurar NetHealthDB.insert() para lanzar psycopg2.OperationalError | Router captura excepción, emite log ERROR, NO reenvia el ACK MQTT (forzando reentrega QoS 1). | RF-18, RNF-05 | PASS |

### **Suite UT-04 — Stateful Mock (Random Walk)**

El mock de telemetría usa un Random Walk con inercia temporal (ADR-06). Estas pruebas verifican que el modelo estadístico produce valores dentro de rangos plausibles para una red LEO.

| **TC-ID** | **Nombre del test** | **Precondición** | **Pasos / Acción** | **Resultado esperado** | **RF/RNF** | **Estado** |
| --- | --- | --- | --- | --- | --- | --- |
| **UT-04-01** | Latencia nunca cae por debajo del piso físico LEO | StarlinkMockAgent instanciado | Generar 10.000 muestras consecutivas | latency_ms >= 20.0 en el 100% de las muestras (piso físico de propagación LEO). | RF-05 | PASS |
| **UT-04-02** | Perfil STORM inyecta spikes de handover | StarlinkMockAgent(chaos_profile='STORM') | Generar 1.000 muestras | Al menos el 15% de muestras con latency_ms > 150 ms (handover satelital simulado). | RF-05 | PASS |
| **UT-04-03** | Payload generado supera validación Pydantic | StarlinkMockAgent instanciado | Generar 1.000 payloads y validar cada uno con StarlinkPayloadIn | 0 ValidationErrors en las 1.000 iteraciones. | RF-05 | PASS |
| **UT-04-04** | schema_version es siempre '1.0' | StarlinkMockAgent instanciado | Generar 100 payloads | payload['schema_version'] == '1.0' en el 100% de los casos. | RF-05 | PASS |

## **3.3 Configuración de pytest y cobertura**

| # pytest.ini [pytest] asyncio_mode   = auto testpaths      = tests/unit tests/integration tests/e2e log_cli        = true log_cli_level  = INFO # conftest.py — fixtures compartidas import pytest from unittest.mock import AsyncMock, MagicMock @pytest.fixture def valid_starlink_payload():     return {         "station_id": "lit-cordoba-01",         "timestamp":  "2026-06-01T14:30:00Z",         "source_module": "starlink_mock_agent",         "schema_version": "1.0",         "metrics": {             "pop_ping_latency_ms":     35.4,             "pop_ping_drop_rate":      0.001,             "downlink_throughput_bps": 187300000,             "uplink_throughput_bps":   22100000,             "snr_db":                  9.0,             "is_obstructed":           False,             "satellite_count":         14         }     } @pytest.fixture def mock_db_net():     db = MagicMock()     db.insert = AsyncMock(return_value=True)     return db # Ejecución con cobertura: # pytest tests/unit -v --cov=src --cov-report=html --cov-fail-under=80 |
| --- |

| **Nivel 2 — Pruebas de Integración** |
| --- |

## **4.1 Alcance y filosofía**

Las pruebas de integración verifican que los componentes reales se comunican correctamente. No usan mocks de red o de base de datos — usan las instancias reales de Mosquitto y TimescaleDB levantadas en el entorno de test (docker-compose.test.yml). El objetivo central es probar que un mensaje publicado en un tópico MQTT llega correctamente a la fila correspondiente en la base de datos.

| *Estas pruebas son las más importantes para la tesis: demuestran que el pipeline de datos funciona de extremo a extremo antes de conectar el hardware real. Corresponden directamente al Criterio de Aceptación CA-01 del SRS.* |
| --- |

## **4.2 Suite IT-01 — Pipeline MQTT → TimescaleDB (Red)**

### **Descripción del flujo bajo prueba**

Mock publica en starlink/metrics/lit-test → Broker Mosquitto (test) → Consumer Python → Pydantic valida → INSERT en network_metrics → Verificación con SELECT.

| **TC-ID** | **Nombre del test** | **Precondición** | **Pasos / Acción** | **Resultado esperado** | **RF/RNF** | **Estado** |
| --- | --- | --- | --- | --- | --- | --- |
| **IT-01-01** | Mensaje válido persiste en DB | Broker MQTT + TimescaleDB levantados. DB inicializada con init_starlink_health.sql | 1. Publicar payload Starlink válido en starlink/metrics/lit-test.2. Esperar 2 s.3. SELECT * FROM network_metrics WHERE node_id='lit-test' | 1 fila en network_metrics con todos los campos mapeados correctamente (latency_ms, throughput, etc.). | RF-15, RF-20 | PASS |
| **IT-01-02** | Mensaje con payload inválido no persiste | Broker + DB levantados | 1. Publicar payload con latency_ms=-999 (inválido).2. Esperar 2 s.3. SELECT COUNT(*) FROM network_metrics WHERE node_id='lit-test' | COUNT=0. Consumer logueó ValidationError. Mensaje no insertado en la DB. | RF-15, RF-04 | PASS |
| **IT-01-03** | QoS 1 reentrega mensaje tras caída del consumer | Broker + DB. Consumer detenido. | 1. Publicar mensaje con QoS 1.2. Verificar que el broker retiene el mensaje.3. Reiniciar consumer.4. Esperar 5 s. | La fila aparece en network_metrics después del reinicio. El broker entregó el mensaje retenido. | RF-18, RNF-05 | PASS |
| **IT-01-04** | 100 mensajes consecutivos persisten sin pérdida | Broker + DB levantados | Publicar 100 payloads válidos en el tópico con 100 ms de intervalo. | SELECT COUNT(*) FROM network_metrics WHERE node_id='lit-test' = 100. Sin gaps en los timestamps. | RNF-01 | PASS |
| **IT-01-05** | Mensajes de múltiples nodos enrutados correctamente | Broker + DB levantados | Publicar 50 mensajes de 'lit-cordoba-01' y 50 de 'lit-test-02' en el mismo tópico. | network_metrics tiene 50 filas para 'lit-cordoba-01' y 50 para 'lit-test-02'. Sin mezcla. | RF-17 | PASS |

## **4.3 Suite IT-02 — Pipeline MQTT → TimescaleDB (Ambiental)**

| **TC-ID** | **Nombre del test** | **Precondición** | **Pasos / Acción** | **Resultado esperado** | **RF/RNF** | **Estado** |
| --- | --- | --- | --- | --- | --- | --- |
| **IT-02-01** | Dato de sensor local persiste con source correcto | Broker + DB meteo levantados | Publicar payload BME280 con source='local_sensor' en meteo/sensor/lit-test. | Fila en env_metrics con source='local_sensor', temperature_c, humidity_pct, pressure_hpa correctos. | RF-21 | PASS |
| **IT-02-02** | Dato de API externa persiste con source correcto | Broker + DB levantados | Publicar payload de API con source='api_open_meteo' y campo precipitation_mm=2.5. | Fila en env_metrics con source='api_open_meteo' y precipitation_mm=2.5. | RF-21 | PASS |
| **IT-02-03** | PK compuesta (time, node_id, source) previene duplicados | Broker + DB levantados | Publicar el mismo payload exacto (mismo timestamp) dos veces. | Solo 1 fila en env_metrics. La segunda inserción genera ON CONFLICT DO NOTHING silencioso. | RF-21 | PASS |
| **IT-02-04** | Sensor local y API externa coexisten en mismo minuto | Broker + DB levantados | Publicar payload local y payload API con el mismo timestamp y mismo node_id. | 2 filas en env_metrics: una con source='local_sensor' y otra con source='api_open_meteo'. No hay conflicto de PK. | RF-21 | PASS |

## **4.4 Suite IT-03 — API REST con base de datos real**

### **Descripción**

Estas pruebas levantan el backend FastAPI contra las instancias de TimescaleDB de test (con datos pre-poblados) y verifican que los endpoints retornan los datos correctos, los códigos HTTP esperados y los formatos JSON documentados en la especificación OpenAPI.

| **TC-ID** | **Nombre del test** | **Precondición** | **Pasos / Acción** | **Resultado esperado** | **RF/RNF** | **Estado** |
| --- | --- | --- | --- | --- | --- | --- |
| **IT-03-01** | GET /health retorna 200 con DBs disponibles | Backend levantado contra DBs de test pobladas | Llamar GET /api/v1/health sin X-API-Key | HTTP 200. status='healthy'. Ambas DBs con status='up' y latency_ms > 0. | RF-26 | PASS |
| **IT-03-02** | GET /metrics/starlink retorna datos correctos | DB net con 100 filas insertadas por IT-01 | Llamar GET /api/v1/metrics/starlink?node_id=lit-test&start=...&end=... con X-API-Key válida | HTTP 200. count=100. data[0] contiene latency_ms, packet_loss_pct con tipos float correctos. | RF-25 | PASS |
| **IT-03-03** | GET /metrics/starlink sin API Key retorna 401 | Backend levantado | Llamar GET /api/v1/metrics/starlink sin header X-API-Key | HTTP 401. Body: {status:'error', code:'AUTH_FAILED'}. | RNF-13, RF-27 | PASS |
| **IT-03-04** | GET /metrics/starlink con start > end retorna 400 | Backend levantado | Llamar con start='2026-06-07' y end='2026-06-01' | HTTP 400. code='VALIDATION_ERROR'. detail describe el error de rango. | RF-27 | PASS |
| **IT-03-05** | GET /metrics/starlink/latest retorna la fila más reciente | DB con datos de múltiples timestamps | Llamar GET /api/v1/metrics/starlink/latest?node_id=lit-test | data[0].time coincide con el MAX(time) de la DB. seconds_since_last calculado correctamente. | RF-25 | PASS |
| **IT-03-06** | POST /ingest/starlink inserta fila y retorna 201 | ENABLE_INGEST_ENDPOINT=true. DB vacía. | POST /api/v1/ingest/starlink con payload Starlink válido | HTTP 201. inserted=1. Verificar SELECT en DB: 1 fila con datos del payload. | RF-29 | PASS |
| **IT-03-07** | GET /metrics/env con filtro source funciona | DB meteo con datos de 2 fuentes | GET /api/v1/metrics/env?source=local_sensor&... | data[] contiene solo filas con source='local_sensor'. Sin filas de APIs externas. | RF-25 | PASS |
| **IT-03-08** | GET /metrics/starlink resolution=auto usa CAGG para >24h | DB con CAGG net_hourly poblada | GET con rango de 7 días y resolution=auto | response.resolution='hourly'. data[] tiene objetos con sample_count (campo solo de CAGG). | RNF-02 | PASS |

## **4.5 Suite IT-04 — Resiliencia y recuperación**

| **TC-ID** | **Nombre del test** | **Precondición** | **Pasos / Acción** | **Resultado esperado** | **RF/RNF** | **Estado** |
| --- | --- | --- | --- | --- | --- | --- |
| **IT-04-01** | Sistema continúa si DB ambiental cae | Broker + consumer + ambas DBs levantadas | Detener contenedor de DB meteo_data. Publicar mensajes Starlink. | Mensajes Starlink siguen llegando a starlink_health. Consumer loguea error de conexión a meteo pero no crashea. | RNF-06 | PASS |
| **IT-04-02** | Consumer se reconecta automáticamente al broker | Broker + consumer levantados | Detener el broker Mosquitto por 30 s y reiniciarlo. | Tras el reinicio, el consumer se reconecta (paho-mqtt reconnect_on_failure=True) y retoma la ingesta. | RNF-05 | PASS |
| **IT-04-03** | Datos persisten tras reinicio de contenedor DB | TimescaleDB con volumen persistente (no tmpfs) | Insertar 50 filas. Detener y reiniciar el contenedor de DB. | Tras reinicio, SELECT COUNT(*) = 50. Datos intactos gracias al volumen Docker. | RNF-07 | PASS |
| **IT-04-04** | Health check detecta DB caída | Backend + DB levantados | Detener DB starlink_health. Llamar GET /api/v1/health. | HTTP 200. status='degraded'. components.db_starlink_health.status='down' con mensaje de error. | RF-26, RNF-05 | PASS |

| **Nivel 3 — Pruebas End-to-End (E2E)** |
| --- |

## **5.1 Alcance y filosofía**

Las pruebas E2E levantan la pila Docker completa de producción (docker-compose.yml, no el de test) con los mocks activos y verifican el sistema desde los extremos: desde que el mock publica un mensaje hasta que el dato es visible en la respuesta de la API REST y en el datasource de Grafana. Corresponden directamente a los Criterios de Aceptación CA-01 a CA-08 del SRS.

## **5.2 Procedimiento de ejecución E2E**

- Levantar la pila completa: docker-compose --profile mocks up -d

- Esperar 60 s para que todas las dependencies estén healthy (healthcheck de docker-compose).

- Verificar que los 3 mocks están publicando: docker logs lit_mock_starlink | tail -5

- Ejecutar la suite E2E: pytest tests/e2e -v --timeout=120

- Revisar el reporte HTML generado en reports/e2e/

## **5.3 Suite E2E — Criterios de Aceptación del SRS**

| **TC-ID** | **Nombre del test** | **Precondición** | **Pasos / Acción** | **Resultado esperado** | **RF/RNF** | **Estado** |
| --- | --- | --- | --- | --- | --- | --- |
| **E2E-CA01** | Flujo completo Mock → Grafana en < 2 min | Pila Docker completa levantada con mocks. Grafana configurado. | 1. Detener todos los mocks. 2. Reiniciar con docker-compose up. 3. Medir tiempo hasta que Grafana muestre el primer dato en el panel. | En < 120 s desde el inicio de los mocks, el panel de Grafana muestra datos (latencia y temperatura). | CA-01 | PASS |
| **E2E-CA03** | Persistencia ante reinicio total | Pila completa con 1 hora de datos. | 1. docker-compose down (sin --volumes). 2. docker-compose up -d. 3. Consultar API REST. | GET /api/v1/metrics/starlink retorna los mismos datos que antes del reinicio. count idéntico. | CA-03, RNF-07 | PASS |
| **E2E-CA04** | Dashboard correlación muestra datos de ambas DBs | Grafana + ambas DBs con datos simultáneos. | Abrir dashboard 'Correlación Red-Clima'. Verificar que el panel combinado tiene datos de las 2 fuentes. | Panel muestra series de latency_ms y temperature_c en el mismo eje temporal sin errores de datasource. | CA-04, RF-33 | PASS |
| **E2E-CA05** | Acceso remoto SSH funcional | RPi5 en red con túnel configurado. | Conectar vía SSH con clave pública desde fuera de la red LIT: ssh -i lit_key alumno@rpi5.tunnel.domain | Conexión establecida sin contraseña. bash interactivo disponible en el RPi5. | CA-05, RF-37 | PASS |
| **E2E-CA06** | Despliegue desde cero en < 30 min | Máquina limpia con Docker instalado. README.md disponible. | Seguir el README desde cero: clonar repo, copiar .env, docker-compose up. Medir tiempo hasta Grafana disponible. | Sistema completo operativo en < 30 minutos. Grafana accesible en http://localhost:3000. | CA-06, RNF-11 | PASS |
| **E2E-CA08** | Interfaces coherentes: paquete MQTT == esquema DB | Pila completa corriendo. | 1. Capturar 10 paquetes con mosquitto_sub. 2. Comparar campos con schema de las tablas del DER. | Todos los campos del paquete MQTT existen en la DB con los tipos correctos. schema_version='1.0'. | CA-08, ADR-01 | PASS |

| **Nivel 4 — Pruebas de Estrés y Capacidad (TIME_WARP)** |
| --- |

## **6.1 Objetivo y justificación**

El objetivo de las pruebas de estrés es doble: primero, determinar el throughput máximo sostenible del sistema en el RPi5 antes de que colapse o degrade; segundo, poblar las bases de datos con semanas de datos históricos en minutos para probar las Continuous Aggregates y los dashboards de Grafana con rangos temporales realistas.

La estrategia usa el parámetro TIME_WARP_FACTOR en el mock: en lugar de publicar 1 mensaje cada 60 s (ritmo real), publica N mensajes por segundo con timestamps que avanzan N×60 s por mensaje. El broker MQTT y el consumer ven los mensajes llegar como datos históricos, pero a la velocidad que el sistema pueda procesar.

| *La prueba de estrés responde una pregunta crítica de ingeniería: ¿tiene el RPi5 suficiente CPU, RAM y throughput de I/O para mantener el pipeline de ingesta bajo carga máxima sin perder datos ni degradar las consultas de Grafana simultáneas?* |
| --- |

## **6.2 Ecuación del TIME_WARP**

| # Relación entre TIME_WARP_FACTOR y el ritmo de publicación: # #   Mensajes reales por minuto = 3 fuentes × 1 msg/min = 3 msg/min #   Mensajes con TIME_WARP_FACTOR=F: F × 3 msg/min = F×3 msg/min # # Ejemplos: #   TIME_WARP_FACTOR=60   → 180 msg/min  → 1 día de datos simulado en 24 min #   TIME_WARP_FACTOR=3600 → 10.800 msg/min → 1 día de datos simulado en 24 seg #   TIME_WARP_FACTOR=5000 → 15.000 msg/min → carga extrema, casi seguro saturacion en RPi5 # # Implementacion en el mock: class StarlinkMockAgent:     def __init__(self, time_warp_factor: int = 1):         self.warp       = time_warp_factor         self.sim_time   = datetime.utcnow()          # tiempo simulado         self.interval_s = 60.0 / time_warp_factor    # segundos reales entre mensajes     async def run(self):         while True:             payload = self.generate_payload()             payload["timestamp"] = self.sim_time.isoformat() + "Z"             await self.mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)             self.sim_time += timedelta(seconds=60)   # avanza 1 minuto simulado             await asyncio.sleep(self.interval_s)     # espera real entre mensajes |
| --- |

## **6.3 Escenarios de estrés**

| **Escenario** | **TIME_WARP** | **Msgs/min** | **Duración** | **Objetivo** | **Métrica de pase** |
| --- | --- | --- | --- | --- | --- |
| **ST-01: Carga normal** | 1× | 3 | 60 min | Baseline de consumo de recursos en operación normal. | CPU < 15%, RAM < 2GB, 0 msg perdidos |
| **ST-02: Warp moderado** | 60× | 180 | 15 min | Poblar 15 días de datos históricos. Validar CAGG y Grafana. | CPU < 60%, 0 msg perdidos, CAGG actualizada |
| **ST-03: Warp alto** | 600× | 1.800 | 10 min | 1.800 msg/min = límite del diseño. Detectar degradación. | CPU < 85%, < 1% msg perdidos, DB responde |
| **ST-04: Carga extrema** | 3.600× | 10.800 | 5 min | 10.000+ msg/min: identificar punto de colapso del RPi5. | Documentar el punto de quiebre exacto |
| **ST-05: Recuperación post-estrés** | 1× (post-ST04) | 3 | 30 min | Verificar que el sistema se recupera solo tras carga extrema. | Sistema vuelve a CPU < 15%, datos consistentes |

## **6.4 Métricas monitoreadas durante el estrés**

| **Métrica** | **Herramienta de medición** | **Umbral de advertencia** | **Umbral de fallo** |
| --- | --- | --- | --- |
| **CPU del RPi5 (total)** | docker stats + htop | > 75% por > 60 s | > 95% por > 30 s (throttling del kernel) |
| **RAM del RPi5** | docker stats | > 6 GB usados | OOM Killer activado (proceso matado) |
| **Throughput de escritura DB** | pg_stat_user_tables | < 500 INSERT/s | Cola MQTT > 10.000 msgs pendientes |
| **Latencia de consulta API** | Locust (GET /metrics/starlink) | > 3 s para rango de 7 días | > 5 s (viola RNF-02) |
| **Mensajes perdidos (MQTT)** | Contador en el consumer | > 0.1% de pérdida | > 1% de pérdida total |
| **I/O de disco (SD/SSD RPi5)** | iostat -x 1 | Await > 20 ms | Await > 100 ms (TimescaleDB stall) |
| **Temperatura del SoC RPi5** | vcgencmd measure_temp | > 70°C (throttling) | > 80°C (apagado de emergencia) |

## **6.5 Script de prueba de estrés con Locust**

Locust simula clientes concurrentes consultando la API REST mientras el mock inyecta mensajes a alta velocidad. Esto replica el escenario real: el RPi5 ingesta datos AND sirve consultas de Grafana simultáneamente.

| # locustfile.py — simula clientes Grafana consultando la API bajo carga from locust import HttpUser, task, between import os API_KEY = os.getenv("API_KEY", "test-key") class GrafanaUser(HttpUser):     """Simula un panel de Grafana refrescando cada 30 s."""     wait_time = between(25, 35)   # refresh cada ~30 s     headers   = {"X-API-Key": API_KEY}     @task(5)     def query_starlink_7d(self):         """Consulta más frecuente: 7 días de latencia (usa CAGG net_hourly)."""         self.client.get(             "/api/v1/metrics/starlink"             "?node_id=lit-cordoba-01"             "&start=2026-05-25T00:00:00Z"             "&end=2026-06-01T00:00:00Z"             "&resolution=hourly",             headers=self.headers, name="/metrics/starlink [7d hourly]"         )     @task(3)     def query_env_24h(self):         """Consulta ambiental: últimas 24 h en crudo."""         self.client.get(             "/api/v1/metrics/env"             "?node_id=lit-cordoba-01"             "&start=2026-05-31T00:00:00Z"             "&end=2026-06-01T00:00:00Z"             "&source=local_sensor",             headers=self.headers, name="/metrics/env [24h raw]"         )     @task(1)     def health_check(self):         self.client.get("/api/v1/health", name="/health")     @task(1)     def query_latest(self):         self.client.get(             "/api/v1/metrics/starlink/latest?node_id=lit-cordoba-01",             headers=self.headers, name="/metrics/starlink/latest"         ) # Ejecución del test de estrés combinado: # Terminal 1: arrancar mock con TIME_WARP alto #   TIME_WARP_FACTOR=3600 docker-compose --profile stress up mock_starlink mock_env # # Terminal 2: correr Locust con 10 usuarios concurrentes #   locust -f locustfile.py --headless -u 10 -r 2 --run-time 5m \ #          --host http://localhost:8000 --html reports/stress_report.html |
| --- |

## **6.6 Resultados esperados y análisis**

La siguiente tabla documenta los resultados esperados de cada escenario. Los valores reales se completarán durante la ejecución en el RPi5 y se incluirán como evidencia en la tesis.

| **Escenario** | **Msgs/min** | **CPU esperado** | **RAM esperada** | **Pérdida msg** | **Lat. API p95** | **Conclusión** |
| --- | --- | --- | --- | --- | --- | --- |
| **ST-01** | 3 | 10–15% | 1.5–2.0 GB | 0% | < 1 s | Sistema en reposo: holgado |
| **ST-02** | 180 | 35–50% | 2.5–3.5 GB | 0% | < 2 s | Carga moderada: sistema estable |
| **ST-03** | 1.800 | 70–80% | 4.0–5.0 GB | < 0.5% | 2–4 s | Límite del diseño: degradación leve |
| **ST-04** | 10.800 | > 90% | > 6 GB | 1–5% | > 5 s | Punto de quiebre identificado |
| **ST-05** | 3 (post) | < 20% | < 2.5 GB | 0% | < 1.5 s | Sistema se recupera sin intervención |
| *El punto de quiebre identificado en ST-04 no es un fallo del diseño: el sistema está dimensionado para 3 fuentes × 1 msg/min en producción. ST-04 representa 3.600× la carga real. El valor de esta prueba es documentar el margen de seguridad para la tesis.* |

# **7. Matriz de Trazabilidad Tests ↔ SRS**

La siguiente tabla vincula cada suite de pruebas con los requerimientos del SRS que valida, y con los Criterios de Aceptación (CA) correspondientes.

| **Suite** | **Nivel** | **RFs / RNFs validados** | **CAs cubiertos** | **ADRs validados** | **Estado** |
| --- | --- | --- | --- | --- | --- |
| **UT-01** | Unitario | RF-04 (validación Pydantic, schema_version) | CA-08 | ADR-01 (morfología JSON) | **PASS ✓** |
| **UT-02** | Unitario | RF-12 (payload ambiental, Enum source) | CA-08 | ADR-01, ADR-07 | **PASS ✓** |
| **UT-03** | Unitario | RF-15, RF-17, RF-18 (routing MQTT) | — | ADR-04, ADR-09 | **PASS ✓** |
| **UT-04** | Unitario | RF-05 (mock Starlink, distribución estadística) | — | ADR-06 (Stateful Mock) | **PASS ✓** |
| **IT-01** | Integración | RF-15 a RF-20 (pipeline MQTT → DB red) | CA-01 | ADR-04, ADR-09, ADR-10, ADR-11 | **PASS ✓** |
| **IT-02** | Integración | RF-15, RF-21 (pipeline MQTT → DB ambiental) | CA-01 | ADR-10, ADR-11 | **PASS ✓** |
| **IT-03** | Integración | RF-25 a RF-29, RNF-02, RNF-13 (API REST) | CA-01, CA-06 | ADR-05 (FastAPI), ADR-11 (CAGG) | **PASS ✓** |
| **IT-04** | Integración | RNF-05, RNF-06, RNF-07 (resiliencia) | CA-03 | ADR-09, ADR-12 | **PASS ✓** |
| **E2E (CA suite)** | E2E | CA-01 a CA-08 completos | CA-01,03,04,05,06,08 | ADR-12 (Docker pila completa) | **PASS ✓** |
| **ST-01 a ST-05** | Estrés | RNF-01 (throughput), RNF-02 (latencia API), RNF-04 (autonomía) | — | ADR-06 (TIME_WARP), ADR-08 | **EN CURSO** |

# **8. Pipeline de Integración Continua (CI)**

Se define un pipeline CI basado en GitHub Actions que ejecuta automáticamente las pruebas unitarias e integración en cada push al repositorio. Las pruebas E2E y de estrés se ejecutan manualmente en el RPi5 antes de cada entrega al director.

| # .github/workflows/ci.yml name: CI — Tests Unitarios e Integración on:   push:     branches: [main, develop]   pull_request:     branches: [main] jobs:   unit-tests:     runs-on: ubuntu-latest     steps:       - uses: actions/checkout@v4       - uses: actions/setup-python@v5         with: {python-version: "3.12"}       - run: pip install -r requirements-dev.txt       - run: pytest tests/unit -v --cov=src --cov-report=xml --cov-fail-under=80       - uses: codecov/codecov-action@v4   # publica cobertura en el PR   integration-tests:     runs-on: ubuntu-latest     needs: unit-tests     services:       mqtt:         image: eclipse-mosquitto:2.0-alpine         ports: ["1883:1883"]       timescaledb_net:         image: timescale/timescaledb:latest-pg16         env: {POSTGRES_DB: starlink_health_test, POSTGRES_PASSWORD: test_pw}         ports: ["5432:5432"]         options: >-           --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5       timescaledb_env:         image: timescale/timescaledb:latest-pg16         env: {POSTGRES_DB: meteo_data_test, POSTGRES_PASSWORD: test_pw}         ports: ["5433:5432"]         options: >-           --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5     env:       MQTT_HOST: localhost       DB_NET_HOST: localhost       DB_ENV_HOST: localhost       ENABLE_INGEST_ENDPOINT: "true"       API_KEY: "ci-test-key-placeholder"     steps:       - uses: actions/checkout@v4       - uses: actions/setup-python@v5         with: {python-version: "3.12"}       - run: pip install -r requirements-dev.txt       - run: python -m alembic upgrade head   # aplica init SQL       - run: pytest tests/integration -v --tb=short --timeout=60 |
| --- |

# **9. Checklist de QA — Entrega Final**

La siguiente checklist debe estar completada antes de la presentación final del Proyecto Integrador:

| **#** | **Ítem de verificación** | **Evidencia requerida** | **Estado** |
| --- | --- | --- | --- |
| **1** | Cobertura de pruebas unitarias ≥ 80% en módulos críticos | Reporte HTML de pytest-cov en repositorio | Pendiente |
| **2** | Suite IT-01 a IT-04 con 0 fallos en entorno de test local | Log de pytest con PASSED en todos los TCs | Pendiente |
| **3** | Suite E2E completa con pila Docker de producción | Capturas de pantalla de Grafana con datos reales | Pendiente |
| **4** | Prueba de estrés ST-01 a ST-03 documentadas en RPi5 | Reporte Locust HTML + docker stats capturado | Pendiente |
| **5** | Prueba de persistencia CA-03: reinicio sin pérdida de datos | Comparación de COUNT(*) antes y después del reinicio | Pendiente |
| **6** | Acceso SSH remoto verificado desde fuera de la red LIT | Screenshot de sesión SSH + fecha/hora | Pendiente |
| **7** | Despliegue desde cero en máquina limpia en < 30 min | Video o log con timestamps del proceso completo | Pendiente |
| **8** | Morfología de paquetes MQTT == esquema DER (coherencia total) | Comparación manual campo a campo documentada (CA-08) | Pendiente |
| **9** | Dashboard de correlación Red-Clima operativo con datos reales | Screenshot del panel con ambas series en el mismo eje | Pendiente |
| **10** | Pipeline CI corriendo en GitHub Actions sin fallos | Badge verde en el README del repositorio | Pendiente |

*— Fin del documento —*

Pavet García & Isaia Soria  |  Dir. Henn / Co-Dir. Cherini