DER & Diccionario de Datos — Estación StarlinkPI — FCEFyN / UNC

**PROYECTO INTEGRADOR**

Escuela de Ingeniería en Computación — FCEFyN / UNC

**Diseño de Base de Datos**

*Diagrama Entidad-Relación (DER) **&** Diccionario de Datos*

*PostgreSQL 16 + TimescaleDB 2.x — Esquema relacional exacto, tipos SQL,claves, índices, Continuous Aggregates y políticas de retención*

| **Campo** | **Detalle** |
| --- | --- |
| **Alumnos** | Aldana M. Pavet García (43884931)  │  Federico Isaia Soria (40574892) |
| **Director** | Mgrt. Ing. Santiago Martin Henn |
| **Co-Director** | Dr. Renato Cherini |
| **Referencia SRS** | SRS v1.0 — RF-19 a RF-24, RNF-02, RNF-07 |
| **Referencia ADR** | ADR-10 (Database per Service) · ADR-11 (TimescaleDB) · ADR-08 (Población) |
| **Versión** | 1.0 — Junio 2026 |

# **Índice**

	**Índice**	**2**

	**1. Introducción y Contexto**	**3**

	**2. Convenciones y Tipos de Datos SQL**	**4**

	2.1 Nomenclatura	4

	2.2 Tipos de Datos — Tabla de Referencia	4

	2.3 Convenciones de Hypertables (TimescaleDB)	5

	3.1 Tabla: network_metrics  [HYPERTABLE]	6

	Índices de network_metrics	8

	Políticas de TimescaleDB — network_metrics	8

	3.2 Tabla: network_tests  [HYPERTABLE]	9

	CHECK constraint en network_tests	10

	3.3 Continuous Aggregate: net_hourly	10

	3.4 Continuous Aggregate: net_daily	12

	4.1 Tabla: env_metrics  [HYPERTABLE]	14

	Restricciones CHECK y políticas — env_metrics	16

	4.2 Continuous Aggregate: env_hourly	16

	5.1 Tabla: station_metadata	19

	5.2 Tabla: sensor_catalog	20

	**6. Resumen Completo de Índices**	**23**

	**7. Scripts de Inicialización SQL**	**24**

	7.1 init_starlink_health.sql	24

	7.2 init_meteo_data.sql	26

	**8. Queries de Referencia para Grafana**	**28**

	8.1 Dashboard 'Red Starlink' — Series temporales de latencia	28

	8.2 Dashboard 'Correlación Red-Clima' — Datos cruzados (Data Blending)	28

	8.3 Panel 'Estado del Sistema' — Último dato por servicio	28

	**9. Trazabilidad DER ↔ SRS y ADR**	**30**

# **1. Introducción y Contexto**

Este documento define el esquema relacional completo del sistema de persistencia de la estación de medición. Especifica de forma exacta: tablas (hypertables de TimescaleDB), columnas con sus tipos SQL precisos, restricciones de integridad (PK, FK, CHECK, NOT NULL), índices secundarios, políticas de particionado temporal y vistas materializadas continuas (Continuous Aggregates).

El diseño implementa el patrón Database per Service (ADR-10): cada dominio de datos tiene su propia instancia de PostgreSQL + TimescaleDB con credenciales independientes. Ningún servicio accede a la base de datos de otro, garantizando aislamiento de fallos y escalabilidad independiente.

| **Base de datos** | **Dominio de datos** | **Tablas base** | **Continuous Aggregates** |
| --- | --- | --- | --- |
| **starlink_health** | Telemetría de red satelital Starlink | network_metrics, network_tests | net_hourly, net_daily |
| **meteo_data** | Datos ambientales locales y externos | env_metrics | env_hourly |
| **station_config** | Metadatos de nodos y sensores | station_metadata, sensor_catalog | — (sin CAGG) |

# **2. Convenciones y Tipos de Datos SQL**

## **2.1 Nomenclatura**

- Tablas en snake_case plural: network_metrics, env_metrics, sensor_catalog.

- Columnas con unidades físicas en el nombre: latency_ms, pressure_hpa, throughput_down_bps.

- **PK de hypertables siempre compuesta: **(time, node_id) — el orden importa: time primero para el particionado de TimescaleDB.

- **PK de tablas relacionales: **SERIAL o BIGSERIAL (autoincremental).

- Constraints con nombre explícito: prefijos chk_, fk_, uq_, idx_.

- Continuous Aggregates: sufijos _hourly, _daily sobre la tabla base.

## **2.2 Tipos de Datos — Tabla de Referencia**

| **Tipo SQL** | **JSON equiv.** | **Rango / Precisión** | **Uso en el proyecto** |
| --- | --- | --- | --- |
| TIMESTAMPTZ | string ISO 8601 | Precisión microsegundos, timezone-aware | Columna time en TODAS las hypertables. Almacenada internamente en UTC. Grafana convierte a zona local en display. |
| FLOAT8 | number | ±1.8×10³⁰⁸, 15-16 dígitos significativos | Latencia (ms), SNR (dB), temperatura (°C), humedad (%), presión (hPa). Suficiente para todas las métricas físicas del proyecto. |
| BIGINT | number (int) | ±9.2×10¹⁸ | Throughput en bps: puede superar 2×10⁹ bps (>2 Gbps) con Starlink V3. BIGINT es obligatorio aquí; INT4 desbordaría. |
| INTEGER | number (int) | ±2.1×10⁹ | Contadores de paquetes, wind_direction_deg, sensor_id FK. Uso donde el rango de INT4 es suficiente. |
| SMALLINT | number (int) | −32.768 a +32.767 | satellite_count (típicamente 0–40). Ahorra 2 bytes por fila respecto a INTEGER. |
| BOOLEAN | boolean | TRUE / FALSE (1 byte en disco) | is_obstructed (FOV de la antena), is_active (sensor habilitado). |
| VARCHAR(N) | string | Hasta N caracteres UTF-8 | node_id VARCHAR(64), source VARCHAR(32), schema_version VARCHAR(16). Longitudes definidas con margen sobre el máximo observado en producción. |
| TEXT | string (largo) | Sin límite práctico (hasta 1 GB) | raw_output en network_tests, notes en station_metadata. Equivale a VARCHAR sin límite en PostgreSQL. |
| SERIAL | — (generado) | Autoincremental INT4 (1 a 2.1×10⁹) | sensor_id PK en sensor_catalog. Alias para INTEGER DEFAULT nextval('seq'). |

## **2.3 Convenciones de Hypertables (TimescaleDB)**

- **chunk_time_interval = 1 día: **cada chunk contiene 24 horas de datos. Optimizado para RPi5 con 8 GB RAM: el chunk activo cabe en buffer cache.

- **PK compuesta (time, node_id): **obligatoria en TimescaleDB. El índice clustered resultante ordena físicamente los datos por tiempo DESC dentro de cada node_id, maximizando la eficiencia de range scans.

- **Compresión columnar: **activada automáticamente para chunks > 7 días. El segmentby='node_id' garantiza que TimescaleDB agrupe columnas del mismo nodo, maximizando la ratio de compresión (típicamente 10:1 en series temporales).

- **Retención: **add_retention_policy elimina chunks crudos > 6 meses. Los datos históricos comprimidos permanecen según se configure.

| **Base de datos: starlink_health — Telemetría de red satelital Starlink** |
| --- |

## **3.1 Tabla: network_metrics  [HYPERTABLE]**

Tabla principal de telemetría. Almacena todas las métricas de rendimiento de la red Starlink medidas en el nodo. Particionada por time con intervalos de 1 día. Corresponde a los datos del tópico MQTT starlink/metrics/<node_id> (IF-01 del SRS).

| *  Esta es la hypertable central del proyecto. Su esquema debe permanecer estable — agregar columnas es seguro, renombrar o eliminar requiere migraciones con pg_dump.* |
| --- |

| **PK = Clave primaria (primary key)** | **FK = Clave foránea (foreign key)** | **IDX = Columna indexada** | **CAGG = Continuous Aggregate** | NULL? = S:sí / N:no |
| --- | --- | --- | --- | --- |

| **Campo** | **Tipo SQL** | **NULL** | **Rol** | **Descripción** | **Ejemplo** | **RFs** |
| --- | --- | --- | --- | --- | --- | --- |
| **time** | TIMESTAMPTZ | N | PK | Timestamp UTC de la medición. Debe ser generado en el cliente (script Python) con datetime.utcnow(), NO en la base de datos. TimescaleDB particiona por esta columna. | 2026-06-01 14:30:00+00 | RF-01, RF-04 |
| **node_id** | VARCHAR(64) | N | PK IDX | Identificador único del nodo de medición. Debe coincidir exactamente con el node_id del MQTT payload y con station_metadata.node_id. Forma la clave primaria compuesta junto a time. | lit-cordoba-01 | RF-01, RF-19 |
| **latency_ms** | FLOAT8 | S | IDX | RTT (Round Trip Time) promedio medido con ping o herramienta equivalente hacia el PoP (Point of Presence) de Starlink. En milisegundos. NULL si la medición falló (conectividad interrumpida). | 35.4 | RF-02 |
| **jitter_ms** | FLOAT8 | S |  | Variación del RTT entre muestras consecutivas. Calculado como desviación estándar de las muestras de ping. En milisegundos. Alta correlación esperada con condiciones climáticas adversas. | 4.2 | RF-02 |
| **packet_loss_pct** | FLOAT8 | S |  | Porcentaje de paquetes perdidos en el intervalo de medición. Rango: 0.0–100.0. CHECK constraint: >= 0 AND <= 100. | 0.5 | RF-02 |
| **throughput_down_bps** | BIGINT | S |  | Velocidad de descarga medida en bits por segundo. BIGINT obligatorio: Starlink puede superar 2 Gbps en el futuro. En Grafana se convierte a Mbps dividiendo por 1,000,000. | 187300000 | RF-02 |
| **throughput_up_bps** | BIGINT | S |  | Velocidad de subida medida en bits por segundo. Típicamente 10–30 Mbps en Starlink residencial. | 22100000 | RF-02 |
| **snr_db** | FLOAT8 | S |  | Signal-to-Noise Ratio reportado por el endpoint gRPC interno de la terminal Starlink. En decibelios. NULL si la API interna no está accesible. | 9.0 | RF-03 |
| **is_obstructed** | BOOLEAN | S |  | TRUE si la terminal reporta obstrucción del campo visual (FOV) en el momento de la medición. Obtenido del endpoint gRPC interno. NULL si no disponible. | false | RF-03 |
| **satellite_count** | SMALLINT | S |  | Cantidad de satélites Starlink en vista en el momento de la medición. Obtenido del endpoint gRPC interno. Rango típico: 0–40. | 12 | RF-03 |
| **schema_version** | VARCHAR(16) | N |  | Versión del esquema JSON del paquete de origen. Permite detectar incompatibilidades entre versiones del script y del consumer. Valor actual: '1.0'. | 1.0 | RF-04 |

### **Índices de network_metrics**

| **Nombre del índice** | **Definición SQL** | **Justificación** |
| --- | --- | --- |
| **idx_netmet_node_time** | CREATE INDEX ON network_metrics (node_id, time DESC); | Acelera filtros por nodo con rango temporal (consulta principal de Grafana: WHERE node_id='x' AND time > now()-'7d') |
| **idx_netmet_loss** | CREATE INDEX ON network_metrics (packet_loss_pct) WHERE packet_loss_pct > 1.0; | Índice parcial para búsquedas de eventos de degradación (alertas de Grafana: pérdida > 1%). |
| **idx_netmet_obstructed** | CREATE INDEX ON network_metrics (time DESC) WHERE is_obstructed = TRUE; | Índice parcial para correlacionar obstrucciones con condiciones climáticas. Solo indexa filas relevantes. |

### **Políticas de TimescaleDB — network_metrics**

| -- Hypertable: particionado por día SELECT create_hypertable('network_metrics', 'time',     chunk_time_interval => INTERVAL '1 day',     if_not_exists       => TRUE); -- Compresión columnar: chunks > 7 días ALTER TABLE network_metrics SET (     timescaledb.compress,     timescaledb.compress_segmentby = 'node_id',   -- agrupa por nodo para mejor ratio     timescaledb.compress_orderby   = 'time DESC'  -- ordena por tiempo dentro del segmento ); SELECT add_compression_policy('network_metrics', INTERVAL '7 days'); -- Retención: elimina chunks crudos > 6 meses SELECT add_retention_policy('network_metrics', INTERVAL '6 months'); -- CHECK constraints ALTER TABLE network_metrics     ADD CONSTRAINT chk_netmet_loss         CHECK (packet_loss_pct IS NULL OR (packet_loss_pct >= 0 AND packet_loss_pct <= 100)),     ADD CONSTRAINT chk_netmet_throughput_down         CHECK (throughput_down_bps IS NULL OR throughput_down_bps >= 0),     ADD CONSTRAINT chk_netmet_throughput_up         CHECK (throughput_up_bps IS NULL OR throughput_up_bps >= 0); |
| --- |

## **3.2 Tabla: network_tests  [HYPERTABLE]**

Almacena resultados de tests de red individuales y detallados (iperf3, speedtest, traceroute). Complementa network_metrics con contexto granular por tipo de test. Referencia el mismo node_id que network_metrics.

| **Campo** | **Tipo SQL** | **NULL** | **Rol** | **Descripción** | **Ejemplo** | **RFs** |
| --- | --- | --- | --- | --- | --- | --- |
| **time** | TIMESTAMPTZ | N | PK | Timestamp UTC del inicio del test. PK1 de la hypertable. | 2026-06-01 14:30:05+00 | RF-02 |
| **node_id** | VARCHAR(64) | N | PK IDX | Identificador del nodo que ejecutó el test. PK2 de la hypertable. | lit-cordoba-01 | RF-19 |
| **test_type** | VARCHAR(32) | N | IDX | Tipo de test ejecutado. Valores permitidos: 'ping', 'iperf3_tcp', 'iperf3_udp', 'speedtest', 'traceroute', 'dns_lookup'. CHECK constraint sobre este campo. | iperf3_tcp | RF-02 |
| **target_host** | VARCHAR(256) | N |  | Host o IP del servidor destino del test. Para iperf3: IP del servidor de referencia. Para speedtest: URL del servidor seleccionado. | speedtest.cablevision.ar | RF-02 |
| **result_primary** | FLOAT8 | S |  | Métrica principal del test. Semántica dependiente del test_type: para ping=RTT_ms, para iperf3=throughput_bps, para speedtest=download_bps. | 187500000.0 | RF-02 |
| **result_secondary** | FLOAT8 | S |  | Métrica secundaria: para ping=jitter_ms, para iperf3_udp=jitter_ms, para speedtest=upload_bps. | 4.1 | RF-02 |
| **samples** | INTEGER | S |  | Cantidad de muestras tomadas en el test. Para ping: número de paquetes. Para iperf3: duración del test en segundos (convención). | 30 | RF-02 |
| **raw_output** | TEXT | S |  | Salida JSON o texto crudo de la herramienta. Útil para debugging post-hoc. Comprimido automáticamente por TimescaleDB. | { "end": { "sum": ... } } | RF-02 |
| **tool_version** | VARCHAR(16) | S |  | Versión de la herramienta de medición usada. Permite detectar cambios de comportamiento entre versiones. | 3.14 | RF-02 |

### **CHECK constraint en network_tests**

| ALTER TABLE network_tests     ADD CONSTRAINT chk_nettest_type         CHECK (test_type IN ('ping','iperf3_tcp','iperf3_udp','speedtest','traceroute','dns_lookup')); |
| --- |

## **3.3 Continuous Aggregate: net_hourly**

Vista materializada continua sobre network_metrics. Precalcula promedios, máximos y mínimos por hora y por nodo. TimescaleDB la actualiza automáticamente en background (política configurada para lag de 1 hora). Grafana la consulta en rangos > 24 horas para evitar sobrecarga al procesar millones de filas crudas.

| **Campo** | **Tipo SQL** | **NULL** | **Rol** | **Descripción** | **Ejemplo** | **RFs** |
| --- | --- | --- | --- | --- | --- | --- |
| **bucket** | TIMESTAMPTZ | N | CAGG PK | Inicio del bucket de 1 hora generado por time_bucket('1 hour', time). PK1 de la vista materializada. | 2026-06-01 14:00:00+00 | RNF-02 |
| **node_id** | VARCHAR(64) | N | CAGG PK | Nodo de medición. PK2 de la vista. | lit-cordoba-01 | RNF-02 |
| **avg_latency_ms** | FLOAT8 | S | CAGG | AVG(latency_ms) en el bucket. NULL si no hubo muestras válidas en la hora. | 34.7 | RNF-02 |
| **max_latency_ms** | FLOAT8 | S | CAGG | MAX(latency_ms) — latencia pico de la hora. Útil para detectar handovers satelitales. | 210.3 | RNF-02 |
| **min_latency_ms** | FLOAT8 | S | CAGG | MIN(latency_ms) — mejor caso en la hora. | 22.1 | RNF-02 |
| **p95_latency_ms** | FLOAT8 | S | CAGG | Percentil 95 de latencia en el bucket. Calculado con percentile_cont(0.95) WITHIN GROUP. | 89.5 | RNF-02 |
| **avg_jitter_ms** | FLOAT8 | S | CAGG | AVG(jitter_ms) — jitter medio horario. | 3.8 | RNF-02 |
| **avg_packet_loss_pct** | FLOAT8 | S | CAGG | AVG(packet_loss_pct) — pérdida media en la hora. | 0.3 | RNF-02 |
| **avg_throughput_down_bps** | FLOAT8 | S | CAGG | AVG(throughput_down_bps) — throughput de bajada medio horario. | 182000000 | RNF-02 |
| **avg_throughput_up_bps** | FLOAT8 | S | CAGG | AVG(throughput_up_bps) — throughput de subida medio horario. | 21500000 | RNF-02 |
| **sample_count** | BIGINT | N | CAGG | COUNT(*) — número de muestras en el bucket. sample_count < 50 indica huecos de datos en la hora. | 58 | RNF-02 |

| -- Continuous Aggregate: net_hourly CREATE MATERIALIZED VIEW net_hourly WITH (timescaledb.continuous) AS SELECT     time_bucket('1 hour', time)                             AS bucket,     node_id,     AVG(latency_ms)                                         AS avg_latency_ms,     MAX(latency_ms)                                         AS max_latency_ms,     MIN(latency_ms)                                         AS min_latency_ms,     percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95_latency_ms,     AVG(jitter_ms)                                          AS avg_jitter_ms,     AVG(packet_loss_pct)                                    AS avg_packet_loss_pct,     AVG(throughput_down_bps)                                AS avg_throughput_down_bps,     AVG(throughput_up_bps)                                  AS avg_throughput_up_bps,     COUNT(*)                                                AS sample_count FROM network_metrics GROUP BY bucket, node_id WITH NO DATA;  -- se llena mediante backfill o ingesta orgánica -- Política de refresco automático (lag: datos de más de 1h, ventana: 3h hacia atrás) SELECT add_continuous_aggregate_policy('net_hourly',     start_offset  => INTERVAL '3 hours',     end_offset    => INTERVAL '1 hour',     schedule_interval => INTERVAL '1 hour'); |
| --- |

## **3.4 Continuous Aggregate: net_daily**

Vista materializada diaria para rangos > 7 días en Grafana. Calcula disponibilidad del enlace como porcentaje de muestras con pérdida < 5%. TimescaleDB la actualiza a medianoche UTC.

| **Campo** | **Tipo SQL** | **NULL** | **Rol** | **Descripción** | **Ejemplo** | **RFs** |
| --- | --- | --- | --- | --- | --- | --- |
| **bucket** | TIMESTAMPTZ | N | CAGG PK | Inicio del bucket de 1 día (UTC) generado por time_bucket('1 day', time). | 2026-06-01 00:00:00+00 | RNF-02 |
| **node_id** | VARCHAR(64) | N | CAGG PK | Nodo de medición. | lit-cordoba-01 | RNF-02 |
| **avg_latency_ms** | FLOAT8 | S | CAGG | Latencia media diaria en ms. | 35.1 | RNF-02 |
| **p95_latency_ms** | FLOAT8 | S | CAGG | Percentil 95 diario de latencia. | 95.2 | RNF-02 |
| **max_latency_ms** | FLOAT8 | S | CAGG | Latencia pico del día. | 412.0 | RNF-02 |
| **avg_packet_loss_pct** | FLOAT8 | S | CAGG | Pérdida media diaria. | 0.4 | RNF-02 |
| **availability_pct** | FLOAT8 | S | CAGG | Porcentaje de muestras con packet_loss_pct < 5. Define disponibilidad del enlace. Fórmula: 100.0 * SUM(CASE WHEN loss<5 THEN 1 ELSE 0 END) / COUNT(*). | 98.6 | RNF-02 |
| **avg_throughput_down_bps** | FLOAT8 | S | CAGG | Throughput de bajada medio diario. | 179000000 | RNF-02 |
| **avg_throughput_up_bps** | FLOAT8 | S | CAGG | Throughput de subida medio diario. | 20800000 | RNF-02 |
| **sample_count** | BIGINT | N | CAGG | Número total de muestras en el día. Ideal >= 1400 (24h × 60 min). | 1438 | RNF-02 |

| **Base de datos: meteo_data — Datos ambientales y meteorológicos** |
| --- |

## **4.1 Tabla: env_metrics  [HYPERTABLE]**

Tabla unificada para todos los datos ambientales. Consolida tres fuentes en una sola hypertable mediante la columna source como tercera parte de la PK. Esta decisión simplifica el schema evitando 3 tablas separadas con estructura casi idéntica, y permite comparar fuentes con una sola query SQL (WHERE node_id='x' AND time > ..., agrupando por source en Grafana).

| *  La columna source forma parte de la PK compuesta para evitar conflictos de unicidad cuando el sensor local y una API externa publican en el mismo minuto. El consumer Python debe garantizar que source sea siempre uno de los valores permitidos.* |
| --- |

| **PK = Clave primaria (primary key)** | **FK = Clave foránea (foreign key)** | **IDX = Columna indexada** | **CAGG = Continuous Aggregate** | NULL? = S:sí / N:no |
| --- | --- | --- | --- | --- |

| **Campo** | **Tipo SQL** | **NULL** | **Rol** | **Descripción** | **Ejemplo** | **RFs** |
| --- | --- | --- | --- | --- | --- | --- |
| **time** | TIMESTAMPTZ | N | PK | Timestamp UTC de la medición o del reporte de la API externa. PK1 de la hypertable. Para APIs externas: timestamp del período reportado (no de la consulta). | 2026-06-01 14:30:00+00 | RF-07, RF-12 |
| **node_id** | VARCHAR(64) | N | PK IDX | Identificador del nodo al que corresponde la ubicación geográfica. PK2. | lit-cordoba-01 | RF-19, RF-21 |
| **source** | VARCHAR(32) | N | PK IDX | Origen del dato. Valores permitidos: 'local_sensor' (BME280 físico o mock), 'api_open_meteo' (Open-Meteo API), 'api_owm' (OpenWeatherMap), 'api_smn' (SMN Argentina). CHECK constraint obligatorio. | local_sensor | RF-12, RF-21 |
| **temperature_c** | FLOAT8 | S |  | Temperatura ambiente en grados Celsius. NULL si el sensor no pudo leer el valor. CHECK: > -50 AND < 80 (rango físico razonable para Córdoba, Argentina). | 18.5 | RF-06, RF-07 |
| **humidity_pct** | FLOAT8 | S |  | Humedad relativa en porcentaje. Rango: 0.0–100.0. NULL si no disponible. CHECK: >= 0 AND <= 100. | 62.3 | RF-06, RF-07 |
| **pressure_hpa** | FLOAT8 | S |  | Presión atmosférica en hectopascales. Rango típico en Córdoba: 950–1030 hPa. CHECK: > 800 AND < 1100. | 1013.2 | RF-06, RF-07 |
| **precipitation_mm** | FLOAT8 | S |  | Precipitación acumulada en el período (mm). Solo disponible en fuentes API. NULL para sensor local (BME280 no mide precipitaciones). CHECK: >= 0. | 0.0 | RF-12 |
| **wind_speed_kmh** | FLOAT8 | S |  | Velocidad del viento en km/h. Solo disponible en fuentes API. CHECK: >= 0. | 12.5 | RF-12 |
| **wind_direction_deg** | INTEGER | S |  | Dirección del viento en grados (0–359). 0=Norte, 90=Este. CHECK: >= 0 AND < 360. | 270 | RF-12 |
| **cloud_cover_pct** | FLOAT8 | S |  | Cobertura de nubes en porcentaje (0–100). Solo disponible en fuentes API. Altamente relevante para correlación con obstrucción de la antena. | 30.0 | RF-12 |
| **sensor_id** | INTEGER | S | FK | FK a sensor_catalog.sensor_id. Identifica el sensor físico que tomó la lectura. NULL para fuentes API (no provienen de hardware local). | 1 | RF-21 |
| **schema_version** | VARCHAR(16) | N |  | Versión del esquema JSON del paquete de origen. | 1.0 | RF-12 |

### **Restricciones CHECK y políticas — env_metrics**

| -- PK compuesta en 3 columnas (time + node_id + source) -- TimescaleDB crea automáticamente un UNIQUE index en la PK de la hypertable. SELECT create_hypertable('env_metrics', 'time',     chunk_time_interval => INTERVAL '1 day',     if_not_exists       => TRUE); -- CHECK constraints de dominio ALTER TABLE env_metrics     ADD CONSTRAINT chk_env_source         CHECK (source IN ('local_sensor','api_open_meteo','api_owm','api_smn','mock_bme280','mock_api')),     ADD CONSTRAINT chk_env_temperature         CHECK (temperature_c IS NULL OR (temperature_c > -50 AND temperature_c < 80)),     ADD CONSTRAINT chk_env_humidity         CHECK (humidity_pct IS NULL OR (humidity_pct >= 0 AND humidity_pct <= 100)),     ADD CONSTRAINT chk_env_pressure         CHECK (pressure_hpa IS NULL OR (pressure_hpa > 800 AND pressure_hpa < 1100)),     ADD CONSTRAINT chk_env_precipitation         CHECK (precipitation_mm IS NULL OR precipitation_mm >= 0),     ADD CONSTRAINT chk_env_wind_speed         CHECK (wind_speed_kmh IS NULL OR wind_speed_kmh >= 0),     ADD CONSTRAINT chk_env_wind_dir         CHECK (wind_direction_deg IS NULL OR (wind_direction_deg >= 0 AND wind_direction_deg < 360)); -- Compresión + retención ALTER TABLE env_metrics SET (     timescaledb.compress,     timescaledb.compress_segmentby = 'node_id, source',     timescaledb.compress_orderby   = 'time DESC'); SELECT add_compression_policy('env_metrics', INTERVAL '7 days'); SELECT add_retention_policy('env_metrics', INTERVAL '12 months');  -- más largo que red |
| --- |

## **4.2 Continuous Aggregate: env_hourly**

Vista materializada horaria sobre env_metrics. Calcula promedios y totales acumulados por hora, nodo y fuente. Incluye la columna source en la PK para comparar lecturas del sensor local vs. APIs externas en el mismo panel de Grafana (campo dashboard 'Datos Ambientales' — RF-32).

| **Campo** | **Tipo SQL** | **NULL** | **Rol** | **Descripción** | **Ejemplo** | **RFs** |
| --- | --- | --- | --- | --- | --- | --- |
| **bucket** | TIMESTAMPTZ | N | CAGG PK | Inicio del bucket de 1 hora. PK1. | 2026-06-01 14:00:00+00 | RNF-02 |
| **node_id** | VARCHAR(64) | N | CAGG PK | Nodo de medición. PK2. | lit-cordoba-01 | RNF-02 |
| **source** | VARCHAR(32) | N | CAGG PK | Origen de los datos (local_sensor, api_open_meteo, etc.). PK3. | local_sensor | RNF-02 |
| **avg_temperature_c** | FLOAT8 | S | CAGG | Temperatura media horaria. NULL si sin muestras. | 18.2 | RNF-02 |
| **max_temperature_c** | FLOAT8 | S | CAGG | Temperatura máxima en el bucket. | 19.1 | RNF-02 |
| **min_temperature_c** | FLOAT8 | S | CAGG | Temperatura mínima en el bucket. | 17.8 | RNF-02 |
| **avg_humidity_pct** | FLOAT8 | S | CAGG | Humedad media horaria. | 63.1 | RNF-02 |
| **avg_pressure_hpa** | FLOAT8 | S | CAGG | Presión media horaria. | 1013.0 | RNF-02 |
| **total_precipitation_mm** | FLOAT8 | S | CAGG | Precipitación acumulada en el bucket. SUM(precipitation_mm). | 0.0 | RNF-02 |
| **avg_wind_speed_kmh** | FLOAT8 | S | CAGG | Velocidad media del viento en el bucket. | 13.2 | RNF-02 |
| **sample_count** | BIGINT | N | CAGG | Número de muestras. Para local_sensor: idealmente 1 muestra/min = 60 por hora. | 60 | RNF-02 |

| -- Continuous Aggregate: env_hourly CREATE MATERIALIZED VIEW env_hourly WITH (timescaledb.continuous) AS SELECT     time_bucket('1 hour', time)   AS bucket,     node_id,     source,     AVG(temperature_c)            AS avg_temperature_c,     MAX(temperature_c)            AS max_temperature_c,     MIN(temperature_c)            AS min_temperature_c,     AVG(humidity_pct)             AS avg_humidity_pct,     AVG(pressure_hpa)             AS avg_pressure_hpa,     SUM(precipitation_mm)         AS total_precipitation_mm,     AVG(wind_speed_kmh)           AS avg_wind_speed_kmh,     COUNT(*)                      AS sample_count FROM env_metrics GROUP BY bucket, node_id, source WITH NO DATA; SELECT add_continuous_aggregate_policy('env_hourly',     start_offset  => INTERVAL '3 hours',     end_offset    => INTERVAL '1 hour',     schedule_interval => INTERVAL '1 hour'); |
| --- |

| **Base de datos: station_config — Metadatos de nodos y sensores** |
| --- |

## **5.1 Tabla: station_metadata**

Catálogo maestro de nodos del testbed. Contiene la información geográfica y operativa de cada estación de medición. Esta tabla es de solo lectura en producción: se modifica solo cuando se agrega un nuevo nodo o cambia su estado. No es una hypertable (no tiene series temporales).

| **Campo** | **Tipo SQL** | **NULL** | **Rol** | **Descripción** | **Ejemplo** | **RFs** |
| --- | --- | --- | --- | --- | --- | --- |
| **node_id** | VARCHAR(64) | N | PK | Identificador único del nodo. Formato recomendado: <institución>-<ciudad>-<número>. Usado como FK implícita en TODAS las hypertables de las otras dos bases de datos. | lit-cordoba-01 | RF-24 |
| **location_name** | VARCHAR(128) | N |  | Nombre legible del sitio de instalación. Visible en la interfaz de Grafana. | Laboratorio LIT — FCEFyN, UNC, Córdoba | RF-24 |
| **latitude** | FLOAT8 | N |  | Latitud decimal WGS-84 del punto de instalación de la antena. CHECK: >= -90 AND <= 90. | -31.4335 | RF-24 |
| **longitude** | FLOAT8 | N |  | Longitud decimal WGS-84. CHECK: >= -180 AND <= 180. | -64.1878 | RF-24 |
| **altitude_m** | FLOAT8 | S |  | Altitud en metros sobre el nivel del mar. Dato opcional pero relevante para correlación con presión atmosférica. | 490.0 | RF-24 |
| **deployed_at** | TIMESTAMPTZ | N |  | Fecha y hora UTC de despliegue del nodo. Se registra una sola vez. | 2026-08-01 10:00:00+00 | RF-24 |
| **hardware_version** | VARCHAR(32) | S |  | Versión del hardware de la estación (RPi5 rev, versión del kit Starlink). | RPi5-8GB-StarV3 | RF-24 |
| **status** | VARCHAR(32) | N | IDX | Estado operativo del nodo. Valores: 'active', 'inactive', 'maintenance'. CHECK constraint sobre valores válidos. | active | RF-34, RF-24 |
| **notes** | TEXT | S |  | Notas de instalación, incidencias históricas, cambios de hardware. Campo libre para el operador. | Antena orientada 15° al norte para evitar obstrucción del techo | RF-24 |

## **5.2 Tabla: sensor_catalog**

Registro de todos los sensores físicos conectados a cada nodo. Permite trazar cada lectura en env_metrics a un sensor específico mediante la FK sensor_id. Soporta múltiples sensores del mismo tipo en el mismo nodo (ej: dos BME280 en ubicaciones distintas).

| **Campo** | **Tipo SQL** | **NULL** | **Rol** | **Descripción** | **Ejemplo** | **RFs** |
| --- | --- | --- | --- | --- | --- | --- |
| **sensor_id** | SERIAL | N | PK | Identificador autoincremental del sensor. Referenciado como FK en env_metrics.sensor_id. | 1 | RF-24 |
| **node_id** | VARCHAR(64) | N | FK IDX | Nodo al que pertenece el sensor. FK hacia station_metadata.node_id. ON DELETE RESTRICT para evitar borrar nodos con sensores activos. | lit-cordoba-01 | RF-24 |
| **sensor_model** | VARCHAR(64) | N |  | Modelo del sensor. Ejemplos: 'BME280', 'SHT31', 'BMP390', 'ESP32-S3-DevKit'. | BME280 | RF-06 |
| **sensor_type** | VARCHAR(32) | N | IDX | Tipo de magnitud medida. Valores: 'temperature', 'humidity', 'pressure', 'multi' (para sensores que miden varias magnitudes como el BME280). | multi | RF-06 |
| **bus_protocol** | VARCHAR(8) | N |  | Protocolo de comunicación con el nodo. Valores: 'I2C', 'SPI', 'UART', 'WiFi' (para ESP32), 'USB'. | I2C | RF-06 |
| **bus_address** | VARCHAR(4) | S |  | Dirección del bus en hexadecimal. Para I2C: '0x76' o '0x77'. NULL para sensores WiFi (ESP32). | 0x76 | RF-06 |
| **calibration_offset** | FLOAT8 | S |  | Offset de calibración aplicado a las lecturas. La calibración se suma al valor crudo antes de publicar: valor_final = valor_crudo + offset. | 0.5 | RF-10 |
| **calibration_scale** | FLOAT8 | S |  | Factor de escala de calibración: valor_final = (valor_crudo + offset) * scale. NULL equivale a 1.0 (sin escala). | 1.0 | RF-10 |
| **last_calibrated_at** | TIMESTAMPTZ | S |  | Fecha y hora UTC de la última calibración del sensor. NULL si nunca fue calibrado explícitamente. | 2026-08-01 11:00:00+00 | RF-10 |
| **registered_at** | TIMESTAMPTZ | N |  | Fecha y hora UTC de registro del sensor en el sistema. Generado automáticamente con DEFAULT now(). | 2026-08-01 10:30:00+00 | RF-24 |
| **is_active** | BOOLEAN | N | IDX | TRUE si el sensor está habilitado para recolección. FALSE si está en mantenimiento o reemplazado. | true | RF-08 |

| -- FK constraint explícita (sensor_catalog → station_metadata) ALTER TABLE sensor_catalog     ADD CONSTRAINT fk_sensor_node         FOREIGN KEY (node_id)         REFERENCES station_metadata(node_id)         ON DELETE RESTRICT    -- no permite borrar un nodo con sensores         ON UPDATE CASCADE;    -- si cambia el node_id, se propaga -- Índice compuesto para listado de sensores activos por nodo CREATE INDEX idx_sensor_node_active ON sensor_catalog (node_id, is_active)     WHERE is_active = TRUE; |
| --- |

# **6. Resumen Completo de Índices**

La siguiente tabla consolida todos los índices del sistema, su tipo, objetivo de rendimiento y la consulta de Grafana que optimizan.

| **Índice** | **Tabla / Base de datos** | **Tipo** | **Columnas** | **Consulta optimizada** |
| --- | --- | --- | --- | --- |
| **PK (time, node_id)** | network_metrics (starlink_health) | CLUSTERED B-Tree | time DESC, node_id | WHERE node_id='x' AND time > now()-'7d' — consulta principal de Grafana |
| **idx_netmet_node_time** | network_metrics (starlink_health) | B-Tree | node_id, time DESC | Filtros multi-nodo en modo comparativo del dashboard |
| **idx_netmet_loss** | network_metrics (starlink_health) | Parcial B-Tree | packet_loss_pct WHERE > 1.0 | Alertas de Grafana: pérdida > 1% — solo indexa filas relevantes |
| **idx_netmet_obstructed** | network_metrics (starlink_health) | Parcial B-Tree | time WHERE is_obstructed=TRUE | Correlación obstrucción-clima para dashboard RF-33 |
| **PK (time, node_id, source)** | env_metrics (meteo_data) | CLUSTERED B-Tree | time DESC, node_id, source | WHERE node_id='x' AND source='local_sensor' AND time > ... — dashboard ambiental |
| **idx_env_node_source** | env_metrics (meteo_data) | B-Tree | node_id, source, time DESC | Comparación sensor local vs. APIs externas en el mismo panel (RF-32) |
| **idx_env_precip** | env_metrics (meteo_data) | Parcial B-Tree | time WHERE precipitation_mm > 0 | Búsqueda de eventos de lluvia para correlación con degradación de red |
| **PK (node_id)** | station_metadata (station_config) | B-Tree único | node_id | Lookup de metadatos del nodo — tabla pequeña, raramente accedida |
| **idx_sensor_node_active** | sensor_catalog (station_config) | Parcial B-Tree | node_id WHERE is_active=TRUE | Listado de sensores activos para UI de configuración del nodo |

# **7. Scripts de Inicialización SQL**

Los siguientes scripts se ejecutan automáticamente al crear los contenedores Docker. Son idempotentes: pueden ejecutarse múltiples veces sin errores. Corresponden al requerimiento RF-24.

## **7.1 init_starlink_health.sql**

| -- ============================================================ -- init_starlink_health.sql — DB: starlink_health -- Idempotente: IF NOT EXISTS en todos los CREATE -- ============================================================ -- Extensión TimescaleDB (ya incluida en la imagen Docker) CREATE EXTENSION IF NOT EXISTS timescaledb; -- ── Tabla base de telemetría de red ────────────────────────── CREATE TABLE IF NOT EXISTS network_metrics (     time                 TIMESTAMPTZ        NOT NULL,     node_id              VARCHAR(64)        NOT NULL,     latency_ms           FLOAT8,     jitter_ms            FLOAT8,     packet_loss_pct      FLOAT8,     throughput_down_bps  BIGINT,     throughput_up_bps    BIGINT,     snr_db               FLOAT8,     is_obstructed        BOOLEAN,     satellite_count      SMALLINT,     schema_version       VARCHAR(16)        NOT NULL DEFAULT '1.0',     CONSTRAINT chk_netmet_loss         CHECK (packet_loss_pct IS NULL OR (packet_loss_pct >= 0 AND packet_loss_pct <= 100)),     CONSTRAINT chk_netmet_down         CHECK (throughput_down_bps IS NULL OR throughput_down_bps >= 0),     CONSTRAINT chk_netmet_up         CHECK (throughput_up_bps IS NULL OR throughput_up_bps >= 0) ); SELECT create_hypertable('network_metrics','time',     chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE); -- Índices secundarios CREATE INDEX IF NOT EXISTS idx_netmet_node_time     ON network_metrics (node_id, time DESC); CREATE INDEX IF NOT EXISTS idx_netmet_loss     ON network_metrics (packet_loss_pct)     WHERE packet_loss_pct > 1.0; CREATE INDEX IF NOT EXISTS idx_netmet_obstructed     ON network_metrics (time DESC)     WHERE is_obstructed = TRUE; -- Compresión ALTER TABLE network_metrics SET (     timescaledb.compress,     timescaledb.compress_segmentby = 'node_id',     timescaledb.compress_orderby   = 'time DESC'); SELECT add_compression_policy('network_metrics',     INTERVAL '7 days', if_not_exists => TRUE); -- Retención de datos crudos SELECT add_retention_policy('network_metrics',     INTERVAL '6 months', if_not_exists => TRUE); -- ── Tabla de tests detallados ───────────────────────────────── CREATE TABLE IF NOT EXISTS network_tests (     time            TIMESTAMPTZ  NOT NULL,     node_id         VARCHAR(64)  NOT NULL,     test_type       VARCHAR(32)  NOT NULL,     target_host     VARCHAR(256) NOT NULL,     result_primary  FLOAT8,     result_secondary FLOAT8,     samples         INTEGER,     raw_output      TEXT,     tool_version    VARCHAR(16),     CONSTRAINT chk_nettest_type         CHECK (test_type IN ('ping','iperf3_tcp','iperf3_udp','speedtest','traceroute','dns_lookup')) ); SELECT create_hypertable('network_tests','time',     chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE); -- ── Continuous Aggregates ───────────────────────────────────── CREATE MATERIALIZED VIEW IF NOT EXISTS net_hourly WITH (timescaledb.continuous) AS SELECT time_bucket('1 hour', time) AS bucket, node_id,     AVG(latency_ms)                                             AS avg_latency_ms,     MAX(latency_ms)                                             AS max_latency_ms,     MIN(latency_ms)                                             AS min_latency_ms,     percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)   AS p95_latency_ms,     AVG(jitter_ms)                                             AS avg_jitter_ms,     AVG(packet_loss_pct)                                       AS avg_packet_loss_pct,     AVG(throughput_down_bps)                                   AS avg_throughput_down_bps,     AVG(throughput_up_bps)                                     AS avg_throughput_up_bps,     COUNT(*)                                                   AS sample_count FROM network_metrics GROUP BY bucket, node_id WITH NO DATA; SELECT add_continuous_aggregate_policy('net_hourly',     start_offset => INTERVAL '3 hours', end_offset => INTERVAL '1 hour',     schedule_interval => INTERVAL '1 hour', if_not_exists => TRUE); CREATE MATERIALIZED VIEW IF NOT EXISTS net_daily WITH (timescaledb.continuous) AS SELECT time_bucket('1 day', time) AS bucket, node_id,     AVG(latency_ms)                                             AS avg_latency_ms,     MAX(latency_ms)                                             AS max_latency_ms,     percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)   AS p95_latency_ms,     AVG(packet_loss_pct)                                       AS avg_packet_loss_pct,     100.0 * SUM(CASE WHEN packet_loss_pct < 5 THEN 1 ELSE 0 END)::float / COUNT(*) AS availability_pct,     AVG(throughput_down_bps)                                   AS avg_throughput_down_bps,     AVG(throughput_up_bps)                                     AS avg_throughput_up_bps,     COUNT(*)                                                   AS sample_count FROM network_metrics GROUP BY bucket, node_id WITH NO DATA; SELECT add_continuous_aggregate_policy('net_daily',     start_offset => INTERVAL '2 days', end_offset => INTERVAL '1 day',     schedule_interval => INTERVAL '1 day', if_not_exists => TRUE); |
| --- |

## **7.2 init_meteo_data.sql**

| -- ============================================================ -- init_meteo_data.sql — DB: meteo_data -- ============================================================ CREATE EXTENSION IF NOT EXISTS timescaledb; CREATE TABLE IF NOT EXISTS env_metrics (     time                TIMESTAMPTZ  NOT NULL,     node_id             VARCHAR(64)  NOT NULL,     source              VARCHAR(32)  NOT NULL,     temperature_c       FLOAT8,     humidity_pct        FLOAT8,     pressure_hpa        FLOAT8,     precipitation_mm    FLOAT8,     wind_speed_kmh      FLOAT8,     wind_direction_deg  INTEGER,     cloud_cover_pct     FLOAT8,     sensor_id           INTEGER,     schema_version      VARCHAR(16)  NOT NULL DEFAULT '1.0',     CONSTRAINT chk_env_source         CHECK (source IN ('local_sensor','api_open_meteo','api_owm','api_smn','mock_bme280','mock_api')),     CONSTRAINT chk_env_temp   CHECK (temperature_c   IS NULL OR (temperature_c   > -50  AND temperature_c   < 80)),     CONSTRAINT chk_env_hum    CHECK (humidity_pct    IS NULL OR (humidity_pct    >= 0   AND humidity_pct    <= 100)),     CONSTRAINT chk_env_press  CHECK (pressure_hpa    IS NULL OR (pressure_hpa    > 800  AND pressure_hpa    < 1100)),     CONSTRAINT chk_env_precip CHECK (precipitation_mm IS NULL OR precipitation_mm >= 0),     CONSTRAINT chk_env_wind   CHECK (wind_speed_kmh  IS NULL OR wind_speed_kmh   >= 0),     CONSTRAINT chk_env_wdir   CHECK (wind_direction_deg IS NULL OR (wind_direction_deg >= 0 AND wind_direction_deg < 360)) ); SELECT create_hypertable('env_metrics','time',     chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE); CREATE INDEX IF NOT EXISTS idx_env_node_source     ON env_metrics (node_id, source, time DESC); CREATE INDEX IF NOT EXISTS idx_env_precip     ON env_metrics (time DESC)     WHERE precipitation_mm > 0; ALTER TABLE env_metrics SET (     timescaledb.compress,     timescaledb.compress_segmentby = 'node_id, source',     timescaledb.compress_orderby   = 'time DESC'); SELECT add_compression_policy('env_metrics',     INTERVAL '7 days', if_not_exists => TRUE); SELECT add_retention_policy('env_metrics',     INTERVAL '12 months', if_not_exists => TRUE); CREATE MATERIALIZED VIEW IF NOT EXISTS env_hourly WITH (timescaledb.continuous) AS SELECT time_bucket('1 hour', time) AS bucket, node_id, source,     AVG(temperature_c)    AS avg_temperature_c,     MAX(temperature_c)    AS max_temperature_c,     MIN(temperature_c)    AS min_temperature_c,     AVG(humidity_pct)     AS avg_humidity_pct,     AVG(pressure_hpa)     AS avg_pressure_hpa,     SUM(precipitation_mm) AS total_precipitation_mm,     AVG(wind_speed_kmh)   AS avg_wind_speed_kmh,     COUNT(*)              AS sample_count FROM env_metrics GROUP BY bucket, node_id, source WITH NO DATA; SELECT add_continuous_aggregate_policy('env_hourly',     start_offset => INTERVAL '3 hours', end_offset => INTERVAL '1 hour',     schedule_interval => INTERVAL '1 hour', if_not_exists => TRUE); |
| --- |

# **8. Queries de Referencia para Grafana**

Las siguientes queries SQL están optimizadas para el datasource PostgreSQL/TimescaleDB de Grafana. La macro $__timeFilter(time) es reemplazada automáticamente por Grafana con el rango temporal seleccionado en el dashboard.

## **8.1 Dashboard 'Red Starlink' — Series temporales de latencia**

| -- Panel: Latencia media y pico por hora (usa CAGG net_hourly) SELECT     bucket                          AS time,     avg_latency_ms                  AS "Latencia media (ms)",     max_latency_ms                  AS "Latencia pico (ms)",     p95_latency_ms                  AS "Latencia p95 (ms)" FROM net_hourly WHERE     node_id = '$node_id'  -- variable de Grafana     AND $__timeFilter(bucket) ORDER BY bucket ASC; -- Panel: Throughput en Mbps (conversión de bps a Mbps en la query) SELECT     bucket                                  AS time,     avg_throughput_down_bps / 1e6          AS "Bajada (Mbps)",     avg_throughput_up_bps   / 1e6          AS "Subida (Mbps)" FROM net_hourly WHERE node_id = '$node_id' AND $__timeFilter(bucket) ORDER BY bucket ASC; |
| --- |

## **8.2 Dashboard 'Correlación Red-Clima' — Datos cruzados (Data Blending)**

Grafana Data Blending permite combinar dos datasources (starlink_health_db + meteo_db) en el mismo panel usando 'Outer Join by Time'. Cada query va en un datasource separado, la unión la hace Grafana en el browser.

| -- Query A — Datasource: starlink_health SELECT bucket AS time, avg_latency_ms AS "Latencia (ms)" FROM net_hourly WHERE node_id = '$node_id' AND $__timeFilter(bucket) ORDER BY bucket; -- Query B — Datasource: meteo_data SELECT bucket AS time, avg_temperature_c AS "Temperatura (°C)", avg_humidity_pct AS "Humedad (%)" FROM env_hourly WHERE node_id = '$node_id' AND source = 'local_sensor' AND $__timeFilter(bucket) ORDER BY bucket; -- Grafana une A y B por "time" con Outer Join → panel combinado RF-33 |
| --- |

## **8.3 Panel 'Estado del Sistema' — Último dato por servicio**

| -- Última medición recibida por cada source (detecta servicios caídos) SELECT source, MAX(time) AS "Último dato recibido", COUNT(*) AS "Muestras últimas 24h" FROM env_metrics WHERE node_id = '$node_id' AND time > now() - INTERVAL '24 hours' GROUP BY source ORDER BY source; -- Servicio de red SELECT 'Starlink telemetry' AS service, MAX(time) AS "Último dato" FROM network_metrics WHERE node_id = '$node_id'; |
| --- |

# **9. Trazabilidad DER ↔ SRS y ADR**

| **Tabla / Vista** | **Base de datos** | **RFs cubiertos** | **ADRs que la motivan** | **Interfaz MQTT (SRS §6)** |
| --- | --- | --- | --- | --- |
| **network_metrics** | starlink_health | RF-19, RF-20, RF-22, RF-23 | ADR-10, ADR-11, ADR-01 | IF-01 → IF-05 |
| **network_tests** | starlink_health | RF-02, RF-19 | ADR-10, ADR-11 | IF-01 → IF-05 |
| **net_hourly, net_daily** | starlink_health | RNF-02, RF-35 | ADR-11, ADR-13 | — (vista sobre IF-05) |
| **env_metrics** | meteo_data | RF-19, RF-21, RF-22, RF-23 | ADR-10, ADR-11, ADR-02, ADR-03 | IF-02, IF-03 → IF-06 |
| **env_hourly** | meteo_data | RNF-02, RF-32, RF-33 | ADR-11, ADR-13 | — (vista sobre IF-06) |
| **station_metadata** | station_config | RF-24, RF-34 | ADR-10 | — (catálogo estático) |
| **sensor_catalog** | station_config | RF-06, RF-08, RF-10, RF-24 | ADR-02, ADR-03 | — (catálogo estático) |

*— Fin del documento —*

Pavet García & Isaia Soria  |  Dir. Henn / Co-Dir. Cherini