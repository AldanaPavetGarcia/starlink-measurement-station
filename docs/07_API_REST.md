Especificación API REST — Estación StarlinkPI — FCEFyN / UNC

**PROYECTO INTEGRADOR**

Escuela de Ingeniería en Computación — FCEFyN / UNC

**Especificación de la API REST**

*OpenAPI 3.1 — FastAPI Backend*

*Endpoints, parámetros, esquemas JSON, códigos de respuesta,autenticación y decisiones de diseño*

| **Campo** | **Detalle** |
| --- | --- |
| **Alumnos** | Aldana M. Pavet García (43884931)  │  Federico Isaia Soria (40574892) |
| **Director** | Mgrt. Ing. Santiago Martin Henn |
| **Co-Director** | Dr. Renato Cherini |
| **Framework** | Python 3 + FastAPI — documentación OpenAPI auto-generada en /api/v1/docs |
| **Autenticación** | API Key estática en header X-API-Key (configurable en .env) |
| **Consumidores** | Grafana OSS (datasource SimpleJSON / HTTP) · Testbed internacional (futuro) |
| **Refs. SRS** | RF-25, RF-26, RF-27, RF-28, RF-29 · RNF-12, RNF-13, RNF-14 |
| **Versión** | 1.0 — Junio 2026 |

# **Índice**

	**Índice**	**2**

	**1. Introducción y Decisiones de Diseño**	**3**

	1.1 Principios de Diseño	3

	1.2 Resumen de Endpoints	3

	**2. Autenticación**	**5**

	2.1 Esquema: API Key en Header	5

	Ejemplo de request autenticado	5

	Implementación FastAPI (security.py)	5

	2.2 Evolución de Autenticación (Roadmap)	6

	**3. Formatos Globales**	**7**

	3.1 Envelope de Respuesta Exitosa	7

	3.2 Envelope de Error	7

	3.3 Catálogo de Códigos de Error	7

	Descripción	9

	Autenticación	9

	Parámetros de query	9

	Respuesta exitosa — HTTP 200	9

	Respuesta degradada — HTTP 200 (componente caído)	10

	Implementación FastAPI	10

	Descripción	11

	Parámetros de query	11

	Respuesta exitosa — HTTP 200	12

	Lógica de selección automática de Continuous Aggregate (resolution=auto)	13

	Descripción	13

	Parámetros de query	13

	Respuesta exitosa — HTTP 200	14

	Descripción	15

	Parámetros de query	15

	Respuesta exitosa — HTTP 200	15

	Descripción	16

	Parámetros de query	16

	Respuesta exitosa — HTTP 200	17

	Parámetros de query	18

	Respuesta exitosa — HTTP 200	18

	Parámetros de query	19

	Respuesta exitosa — HTTP 200	19

	Descripción	1

	Parámetros de query	1

	Respuesta exitosa — HTTP 200	1

	Parámetros de path	1

	Respuesta exitosa — HTTP 200	1

	Descripción	1

	Request Body — application/json	1

	Respuesta exitosa — HTTP 201	1

	Request Body — application/json	1

	Respuesta exitosa — HTTP 201	1

	**9. Esquemas Pydantic (Validación de Request y Response)**	**1**

	9.1 Modelos de Telemetría Starlink	1

	9.2 Modelos de Datos Ambientales	1

	**10. Configuración del Datasource HTTP en Grafana**	**1**

	10.1 Configuración del Datasource Infinity (API REST)	1

	10.2 Ejemplo de Panel Grafana con query a la API	1

	**11. Fragmento OpenAPI 3.1 (YAML)**	**1**

	**12. Trazabilidad Endpoints ↔ SRS, DER y ADR**	**1**

	**13. Historial de Revisiones**	**1**

# **1. Introducción y Decisiones de Diseño**

Este documento especifica todos los endpoints de la API REST del backend del sistema de medición. El backend está implementado en Python 3 con FastAPI, que genera automáticamente la documentación OpenAPI 3.1 interactiva (Swagger UI) en /api/v1/docs y la especificación JSON en /api/v1/openapi.json.

La API cumple dos roles: ser el datasource HTTP de los dashboards Grafana del LIT, y proveer acceso a los datos de medición al testbed internacional de universidades canadienses en etapas futuras. En la Etapa 1 (on-premises en el RPi5), la API es interna; en la Etapa 2 (cloud), queda expuesta con el mismo contrato de datos, cambiando únicamente la URL base.

## **1.1 Principios de Diseño**

- **Versionado en URL: **prefijo /api/v1/ en todos los endpoints. Permite agregar /api/v2/ sin romper clientes existentes.

- **Solo lectura (GET): **la ingesta de datos va por MQTT → consumer Python → TimescaleDB (ADR-04). La API no recibe datos de los scripts, solo los sirve.

- **POST /ingest solo para testing: **un endpoint de ingesta manual para poblar la base de datos con datos de prueba durante el desarrollo con mocks (RF-29). Desactivable con variable de entorno ENABLE_INGEST_ENDPOINT=false.

- **JSON canónico coherente: **la morfología de los objetos de respuesta es consistente con los paquetes MQTT definidos en el SRS §5 y con las columnas del DER.

- **Paginación por cursor temporal: **no por offset (OFFSET/LIMIT). El cursor es el timestamp del último elemento recibido, lo que garantiza eficiencia con hypertables de TimescaleDB.

- **Errores descriptivos: **todos los errores retornan un objeto JSON {detail, code, timestamp} para facilitar el debugging desde Grafana y desde los clientes del testbed.

## **1.2 Resumen de Endpoints**

| **Método** | **Ruta** | **Descripción** | **Auth** | **Tag** |
| --- | --- | --- | --- | --- |
| GET | /api/v1/health | Estado del sistema y conectividad a las DBs | No | system |
| GET | /api/v1/metrics/starlink | Series temporales de telemetría Starlink | **Sí** | starlink |
| GET | /api/v1/metrics/starlink/summary | Estadísticas agregadas (avg, p95, min, max) | **Sí** | starlink |
| GET | /api/v1/metrics/starlink/latest | Última medición recibida por nodo | **Sí** | starlink |
| GET | /api/v1/metrics/env | Series temporales de datos ambientales | **Sí** | meteo |
| GET | /api/v1/metrics/env/summary | Estadísticas ambientales agregadas | **Sí** | meteo |
| GET | /api/v1/metrics/env/latest | Última medición ambiental por nodo y fuente | **Sí** | meteo |
| GET | /api/v1/nodes | Lista de nodos registrados y su estado | **Sí** | nodes |
| GET | /api/v1/nodes/{node_id} | Detalle de un nodo específico | **Sí** | nodes |
| POST | /api/v1/ingest/starlink | Ingesta manual — solo testing/mocks (desactivable) | **Sí** | ingest |
| POST | /api/v1/ingest/env | Ingesta manual ambiental — solo testing/mocks | **Sí** | ingest |

# **2. Autenticación**

## **2.1 Esquema: API Key en Header**

Todos los endpoints excepto GET /api/v1/health requieren autenticación mediante una API Key estática enviada en el header HTTP X-API-Key. La clave se configura en el archivo .env y se inyecta al contenedor Docker como variable de entorno (ADR-12, RNF-12). No se hardcodea en el código fuente.

| **Aspecto** | **Detalle** |
| --- | --- |
| **Header name** | X-API-Key |
| **Valor** | Clave aleatoria generada con: python -c "import secrets; print(secrets.token_hex(32))" |
| **Configuración** | Variable de entorno API_KEY en archivo .env (nunca en código fuente ni en repositorio Git) |
| **Endpoint público** | GET /api/v1/health — no requiere X-API-Key (permite monitoreo externo de disponibilidad) |
| **Respuesta si falla** | HTTP 401 Unauthorized — {"detail": "API key inválida o ausente", "code": "AUTH_FAILED"} |

### **Ejemplo de request autenticado**

| # Consulta de métricas Starlink desde Grafana (datasource HTTP) curl -X GET \   "http://rpi5-lit.local:8000/api/v1/metrics/starlink?node_id=lit-cordoba-01&start=2026-06-01T00:00:00Z&end=2026-06-07T23:59:59Z" \   -H "X-API-Key: a3f8b2c1d9e4f7a0b5c2d8e1f6a3b0c7d4e9f2a5b8c1d6e3f0a7b4c9d2e5f8a1" \   -H "Accept: application/json" |
| --- |

### **Implementación FastAPI (security.py)**

| from fastapi import Security, HTTPException, status from fastapi.security.api_key import APIKeyHeader import os API_KEY_NAME = "X-API-Key" api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False) async def require_api_key(api_key: str = Security(api_key_header)):     """Dependency inyectable en todos los endpoints protegidos."""     expected = os.getenv("API_KEY")     if not expected:         raise RuntimeError("API_KEY no configurada en variables de entorno")     if api_key != expected:         raise HTTPException(             status_code=status.HTTP_401_UNAUTHORIZED,             detail={"detail": "API key inválida o ausente", "code": "AUTH_FAILED",                     "timestamp": datetime.utcnow().isoformat() + "Z"}         )     return api_key # Uso en un router: # @router.get("/metrics/starlink", dependencies=[Depends(require_api_key)]) |
| --- |

## **2.2 Evolución de Autenticación (Roadmap)**

| **Etapa** | **Auth** | **Cuándo aplica** |
| --- | --- | --- |
| **Etapa 1 — Local** | API Key en X-API-Key | RPi5 en LIT. Red universitaria cerrada. Grafana en el mismo entorno Docker. |
| **Etapa 2 — Cloud** | API Key + HTTPS (TLS via nginx/Caddy) | API expuesta públicamente. Se agrega reverse proxy con certificado TLS automático (Let's Encrypt). |
| **Etapa 3 — Testbed** | JWT Bearer token por institución | Universidades de Canadá consumen la API. Cada institución tiene su propio token con claims de node_id. |

# **3. Formatos Globales**

## **3.1 Envelope de Respuesta Exitosa**

Todas las respuestas exitosas (2xx) siguen el mismo envelope JSON para facilitar el parsing en Grafana y en los clientes del testbed:

| {   "status":   "success",   "version":  "1.0",   "node_id":  "lit-cordoba-01",   "count":    150,   "page_info": {     "has_more":    true,     "next_cursor": "2026-06-04T12:35:00Z",     "limit":       500   },   "data": [ /* array de objetos de datos */ ] } |
| --- |

## **3.2 Envelope de Error**

Todos los errores (4xx y 5xx) retornan el mismo objeto. FastAPI mapea automáticamente las excepciones HTTPException a este formato mediante un exception_handler global:

| {   "status":    "error",   "code":      "VALIDATION_ERROR",   "detail":    "El parámetro 'start' debe ser anterior a 'end'.",   "timestamp": "2026-06-01T14:30:00Z",   "path":      "/api/v1/metrics/starlink" } |
| --- |

## **3.3 Catálogo de Códigos de Error**

| **HTTP** | **code (JSON)** | **Cuándo se emite** | **RF** | **Acción cliente** |
| --- | --- | --- | --- | --- |
| **200** | — | Petición procesada correctamente. | RF-25 | Leer data[] |
| **201** | — | Recurso creado (POST /ingest exitoso). | RF-29 | — |
| **400** | VALIDATION_ERROR | Parámetros inválidos (start > end, node_id con caracteres ilegales, limit fuera de rango). | RF-27 | Corregir parámetros |
| **400** | DATE_RANGE_TOO_LARGE | Rango temporal supera el máximo permitido (90 días para raw, sin límite para CAGG). | RF-27 | Reducir rango o usar /summary |
| **400** | INVALID_TIMESTAMP | Timestamps no son ISO 8601 válido o sin timezone. | RF-27 | Usar formato Z (UTC) |
| **401** | AUTH_FAILED | Header X-API-Key ausente o con valor incorrecto. | RNF-13 | Revisar configuración de API Key |
| **404** | NODE_NOT_FOUND | El node_id no existe en station_metadata. | RF-27 | Verificar node_id con GET /nodes |
| **404** | NO_DATA_FOUND | El rango temporal no contiene datos para ese nodo (datos aún no recolectados). | RF-27 | Ajustar rango temporal |
| **422** | INGEST_DISABLED | POST /ingest/* llamado con ENABLE_INGEST_ENDPOINT=false. | RF-29 | Habilitar en .env si es testing |
| **422** | SCHEMA_VERSION_MISMATCH | El campo schema_version del payload no coincide con la versión soportada por el backend. | RF-27 | Actualizar cliente o backend |
| **503** | DB_UNAVAILABLE | El backend no puede conectarse a TimescaleDB (DB caída, timeout de conexión). | RNF-05 | Reintentar con backoff |
| **500** | INTERNAL_ERROR | Error inesperado en el backend (bug, excepción no capturada). Logueado en stderr del contenedor. | RF-27 | Revisar docker logs |

| **Tag: system — Monitoreo del sistema** |
| --- |

| **GET** | **/api/v1/health** | Estado del sistema y conectividad a las bases de datos | *Tag: system* |
| --- | --- | --- | --- |

### **Descripción**

Endpoint público (sin autenticación). Verifica la conectividad del backend con ambas instancias de TimescaleDB y con el broker MQTT. Diseñado para: healthcheck de Docker Compose (depends_on + healthcheck), monitoreo externo de disponibilidad (uptime robots), y panel de estado de Grafana (RF-34). Retorna siempre HTTP 200 con el estado de cada componente — incluso cuando algún componente está degradado.

| *Grafana puede consultar este endpoint cada 30 s para alimentar el panel de estado. La ausencia de error HTTP 200 (ej. timeout o 5xx) indica que el backend en sí está caído.* |
| --- |

### **Autenticación**

No requerida. Acceso público. Permite que herramientas de monitoreo externas (uptime checkers, el equipo de Canadá) verifiquen disponibilidad sin necesidad de gestionar API Keys.

### **Parámetros de query**

Ninguno.

### **Respuesta exitosa — HTTP 200**

| {   "status":    "healthy",          // "healthy" │ "degraded" │ "unhealthy"   "version":   "1.0.0",           // versión del backend   "timestamp": "2026-06-01T14:30:00Z",   "uptime_seconds": 86412,   "components": {     "db_starlink_health": {       "status":       "up",        // "up" │ "down" │ "degraded"       "latency_ms":   2.1,         // tiempo de respuesta del último ping a la DB       "last_write":   "2026-06-01T14:29:01Z"  // último INSERT exitoso     },     "db_meteo_data": {       "status":       "up",       "latency_ms":   1.8,       "last_write":   "2026-06-01T14:28:55Z"     },     "mqtt_broker": {       "status":       "up",       "latency_ms":   0.4,       "last_message": "2026-06-01T14:29:59Z"  // último mensaje recibido por el consumer     }   } } |
| --- |

### **Respuesta degradada — HTTP 200 (componente caído)**

| {   "status": "degraded",   "components": {     "db_starlink_health": { "status": "up",   "latency_ms": 2.3 },     "db_meteo_data":      { "status": "down", "latency_ms": null,                             "error": "connection refused on port 5433" },     "mqtt_broker":        { "status": "up",   "latency_ms": 0.5 }   } } |
| --- |

### **Implementación FastAPI**

| @router.get("/health", tags=["system"], summary="Estado del sistema") async def health_check(db_net: AsyncSession = Depends(get_db_net),                        db_env: AsyncSession = Depends(get_db_env)):     components = {}     overall = "healthy"     for name, session in [("db_starlink_health", db_net), ("db_meteo_data", db_env)]:         try:             t0 = time.monotonic()             await session.execute(text("SELECT 1"))             components[name] = {"status": "up", "latency_ms": round((time.monotonic()-t0)*1000, 2)}         except Exception as e:             components[name] = {"status": "down", "latency_ms": None, "error": str(e)}             overall = "degraded"     return {"status": overall, "version": settings.VERSION,             "timestamp": datetime.utcnow().isoformat()+"Z", "components": components} |
| --- |

| **HTTP Status** | **Descripción** |
| --- | --- |
| **200** | Sistema sano o degradado — siempre 200, el estado real va en el body (status: healthy/degraded/unhealthy) |
| **500** | El propio backend crasheó — el proceso del contenedor no responde |

| **Tag: starlink — Telemetría de red satelital** |
| --- |

| **GET** | **/api/v1/metrics/starlink** | Series temporales de telemetría Starlink | *Tag: starlink* |
| --- | --- | --- | --- |

### **Descripción**

Retorna la serie temporal de métricas de red Starlink para un nodo y rango temporal dados. Fuente: hypertable network_metrics de la DB starlink_health (DER §3.1). Para rangos > 24 horas, el backend consulta automáticamente las Continuous Aggregates net_hourly o net_daily según el parámetro resolution, devolviendo datos pre-agregados en lugar de datos crudos (optimiza el rendimiento de Grafana para gráficos de largo plazo).

| *Grafana usa el parámetro $__interval para determinar la resolución adecuada. Se recomienda configurar el datasource HTTP de Grafana para pasar resolution=auto y dejar que el backend elija entre raw, hourly o daily.* |
| --- |

### **Parámetros de query**

| **Parámetro** | **Tipo** | **Req.** | **Default** | **Descripción** | **Ejemplo** |
| --- | --- | --- | --- | --- | --- |
| **node_id** | string | **Sí** | — | ID del nodo de medición. Debe existir en station_metadata. Acepta lista separada por comas para comparación multi-nodo. | lit-cordoba-01 |
| **start** | datetime (ISO 8601) | **Sí** | — | Inicio del rango temporal, inclusive. Formato ISO 8601 con timezone. Se recomienda usar UTC (sufijo Z). Si se omite timezone, se asume UTC. | 2026-06-01T00:00:00Z |
| **end** | datetime (ISO 8601) | **Sí** | — | Fin del rango temporal, inclusive. Debe ser posterior a start. Rango máximo para datos crudos (resolution=raw): 90 días. | 2026-06-07T23:59:59Z |
| **resolution** | enum | No | auto | Resolución de los datos: 'raw' (datos crudos de network_metrics), 'hourly' (CAGG net_hourly), 'daily' (CAGG net_daily), 'auto' (el backend elige según el rango: raw<6h, hourly<30d, daily>=30d). | hourly |
| **fields** | string (CSV) | No | all | Campos a incluir en la respuesta. Permite reducir el payload. Valores válidos: latency_ms, jitter_ms, packet_loss_pct, throughput_down_bps, throughput_up_bps, snr_db, is_obstructed. 'all' retorna todos. | latency_ms,packet_loss_pct |
| **limit** | integer | No | 500 | Máximo de registros por página. Rango: 1–5000. Si hay más datos, la respuesta incluye page_info.next_cursor para paginación. | 1000 |
| **cursor** | datetime (ISO 8601) | No | — | Cursor de paginación: timestamp del último elemento de la página anterior. Obtenido de page_info.next_cursor en la respuesta anterior. | 2026-06-04T12:35:00Z |

### **Respuesta exitosa — HTTP 200**

| {   "status":  "success",   "version": "1.0",   "node_id": "lit-cordoba-01",   "resolution": "hourly",   "count":   168,   "page_info": {     "has_more":    false,     "next_cursor": null,     "limit":       500   },   "data": [     {       "time":                "2026-06-01T00:00:00Z",   // TIMESTAMPTZ en UTC       "node_id":             "lit-cordoba-01",       "latency_ms":          34.7,       "jitter_ms":           3.2,       "packet_loss_pct":     0.1,       "throughput_down_bps": 182000000,       "throughput_up_bps":   21500000,       "snr_db":              9.1,       "is_obstructed":       false,       "satellite_count":     14,       // Campos extra presentes solo en resolution=hourly o daily:       "max_latency_ms":      89.5,       "min_latency_ms":      22.1,       "p95_latency_ms":      68.2,       "sample_count":        58        // muestras en el bucket     }     // ... más objetos   ] } |
| --- |

### **Lógica de selección automática de Continuous Aggregate (resolution=auto)**

| **Rango solicitado** | **Fuente SQL** | **Objeto retornado** |
| --- | --- | --- |
| **<**** 6 horas** | network_metrics (datos crudos) | Fila raw: latency_ms, jitter_ms, is_obstructed, etc. |
| **6 horas – 30 días** | net_hourly (CAGG 1 hora) | Agrega: avg/max/min/p95_latency, avg_packet_loss, avg_throughput, sample_count |
| **>****= 30 días** | net_daily (CAGG 1 día) | Agrega: avg/max/p95_latency, availability_pct, avg_throughput, sample_count |

| **HTTP Status** | **Descripción** |
| --- | --- |
| **200** | Datos retornados correctamente (data[] puede ser vacío si no hay datos en el rango). |
| **400** | VALIDATION_ERROR — parámetros inválidos (start > end, limit fuera de rango, node_id con caracteres ilegales). |
| **400** | DATE_RANGE_TOO_LARGE — rango supera 90 días con resolution=raw. Usar resolution=hourly o daily para rangos mayores. |
| **400** | INVALID_TIMESTAMP — formato de fecha no es ISO 8601 válido. |
| **401** | AUTH_FAILED — API Key ausente o inválida. |
| **404** | NODE_NOT_FOUND — el node_id no existe en station_metadata. |
| **503** | DB_UNAVAILABLE — no se puede conectar a starlink_health TimescaleDB. |

| **GET** | **/api/v1/metrics/starlink/summary** | Estadísticas agregadas de red para un período | *Tag: starlink* |
| --- | --- | --- | --- |

### **Descripción**

Retorna un único objeto con estadísticas descriptivas (promedio, mínimo, máximo, percentil 95, disponibilidad) calculadas sobre el período completo indicado. Útil para el panel de resumen del dashboard (single-stat panels en Grafana) y para que el testbed internacional obtenga KPIs del enlace sin procesar series completas.

### **Parámetros de query**

| **Parámetro** | **Tipo** | **Req.** | **Default** | **Descripción** | **Ejemplo** |
| --- | --- | --- | --- | --- | --- |
| **node_id** | string | **Sí** | — | ID del nodo de medición. | lit-cordoba-01 |
| **start** | datetime (ISO 8601) | **Sí** | — | Inicio del período de cálculo. | 2026-06-01T00:00:00Z |
| **end** | datetime (ISO 8601) | **Sí** | — | Fin del período de cálculo. | 2026-06-07T23:59:59Z |

### **Respuesta exitosa — HTTP 200**

| {   "status":  "success",   "node_id": "lit-cordoba-01",   "period": {     "start": "2026-06-01T00:00:00Z",     "end":   "2026-06-07T23:59:59Z",     "days":  7   },   "sample_count":      10082,   "data_completeness_pct": 98.4,   // (sample_count / expected_samples) * 100   "summary": {     "latency_ms": {       "avg": 34.9,  "min": 20.1,  "max": 412.3,       "p50": 33.2,  "p95": 95.7,  "p99": 287.4,       "std_dev": 18.6     },     "packet_loss_pct": {       "avg": 0.3,   "max": 12.1,  "events_above_5pct": 14     },     "throughput_down_bps": {       "avg": 181000000,  "min": 45000000,  "max": 248000000     },     "throughput_up_bps": {       "avg": 21200000,   "min": 8000000,   "max": 29500000     },     "availability_pct": 98.6,     "obstruction_events": 23   } } |
| --- |

| **HTTP Status** | **Descripción** |
| --- | --- |
| **200** | Estadísticas calculadas. |
| **400** | VALIDATION_ERROR — parámetros inválidos. |
| **401** | AUTH_FAILED. |
| **404** | NODE_NOT_FOUND o NO_DATA_FOUND (rango sin datos). |
| **503** | DB_UNAVAILABLE. |

| **GET** | **/api/v1/metrics/starlink/latest** | Última medición recibida por nodo | *Tag: starlink* |
| --- | --- | --- | --- |

### **Descripción**

Retorna la medición más reciente registrada para el nodo solicitado. Consulta: SELECT * FROM network_metrics WHERE node_id=? ORDER BY time DESC LIMIT 1. Principal uso: panel de estado en tiempo real de Grafana (RF-34) y heartbeat check del sistema de medición.

### **Parámetros de query**

| **Parámetro** | **Tipo** | **Req.** | **Default** | **Descripción** | **Ejemplo** |
| --- | --- | --- | --- | --- | --- |
| **node_id** | string | No | all | Filtrar por un nodo específico. Sin parámetro, retorna la última medición de todos los nodos activos. | lit-cordoba-01 |

### **Respuesta exitosa — HTTP 200**

| {   "status": "success",   "data": [     {       "node_id":             "lit-cordoba-01",       "time":                "2026-06-01T14:29:01Z",       "latency_ms":          33.8,       "packet_loss_pct":     0.0,       "throughput_down_bps": 187000000,       "throughput_up_bps":   22100000,       "is_obstructed":       false,       "seconds_since_last":  59    // edad del dato en segundos (útil para detectar gap)     }   ] } |
| --- |

| **HTTP Status** | **Descripción** |
| --- | --- |
| **200** | Última medición retornada. |
| **401** | AUTH_FAILED. |
| **404** | NODE_NOT_FOUND. |
| **503** | DB_UNAVAILABLE. |

| **Tag: meteo — Datos ambientales y meteorológicos** |
| --- |

| **GET** | **/api/v1/metrics/env** | Series temporales de datos ambientales | *Tag: meteo* |
| --- | --- | --- | --- |

### **Descripción**

Análogo a GET /metrics/starlink pero para la DB meteo_data. Retorna datos de la hypertable env_metrics o de la CAGG env_hourly según el rango y la resolución solicitada. La columna source permite filtrar entre el sensor local (BME280), APIs meteorológicas externas (Open-Meteo, OpenWeatherMap) o mocks. Para el dashboard de correlación (RF-33), Grafana llama en paralelo a este endpoint y a /metrics/starlink, combinando los resultados con Data Blending.

### **Parámetros de query**

| **Parámetro** | **Tipo** | **Req.** | **Default** | **Descripción** | **Ejemplo** |
| --- | --- | --- | --- | --- | --- |
| **node_id** | string | **Sí** | — | ID del nodo de medición. | lit-cordoba-01 |
| **start** | datetime (ISO 8601) | **Sí** | — | Inicio del rango temporal, inclusive. | 2026-06-01T00:00:00Z |
| **end** | datetime (ISO 8601) | **Sí** | — | Fin del rango temporal, inclusive. | 2026-06-07T23:59:59Z |
| **source** | enum (CSV) | No | all | Filtrar por fuente: 'local_sensor', 'api_open_meteo', 'api_owm', 'api_smn'. Acepta lista separada por comas. 'all' incluye todas las fuentes. | local_sensor,api_open_meteo |
| **fields** | string (CSV) | No | all | Campos de datos ambientales a incluir. Valores: temperature_c, humidity_pct, pressure_hpa, precipitation_mm, wind_speed_kmh, wind_direction_deg, cloud_cover_pct. | temperature_c,humidity_pct,pressure_hpa |
| **resolution** | enum | No | auto | 'raw' (datos crudos), 'hourly' (CAGG env_hourly), 'auto' (raw < 6h, hourly >= 6h). | hourly |
| **limit** | integer | No | 500 | Máximo de registros por página. Rango: 1–5000. | 1000 |
| **cursor** | datetime (ISO 8601) | No | — | Cursor de paginación temporal. | 2026-06-04T12:00:00Z |

### **Respuesta exitosa — HTTP 200**

| {   "status":     "success",   "node_id":    "lit-cordoba-01",   "resolution": "hourly",   "count":      336,   "page_info": { "has_more": false, "next_cursor": null, "limit": 500 },   "data": [     {       "time":             "2026-06-01T00:00:00Z",       "node_id":          "lit-cordoba-01",       "source":           "local_sensor",     // distingue BME280 de APIs externas       "temperature_c":    14.2,       "humidity_pct":     72.1,       "pressure_hpa":     1014.5,       "precipitation_mm": null,               // no disponible en sensor local       "wind_speed_kmh":   null,       "wind_direction_deg": null,       "cloud_cover_pct":  null,       // Presentes solo si resolution=hourly:       "max_temperature_c":  15.1,       "min_temperature_c":  13.8,       "sample_count":       60     },     {       "time":             "2026-06-01T00:00:00Z",       "node_id":          "lit-cordoba-01",       "source":           "api_open_meteo",   // mismo timestamp, fuente diferente       "temperature_c":    13.8,       "humidity_pct":     75.0,       "pressure_hpa":     1014.0,       "precipitation_mm": 0.0,       "wind_speed_kmh":   8.5,       "wind_direction_deg": 270,       "cloud_cover_pct":  15.0     }   ] } |
| --- |

| **HTTP Status** | **Descripción** |
| --- | --- |
| **200** | Datos ambientales retornados. |
| **400** | VALIDATION_ERROR — source inválido, rango fuera de límites. |
| **401** | AUTH_FAILED. |
| **404** | NODE_NOT_FOUND o NO_DATA_FOUND. |
| **503** | DB_UNAVAILABLE — meteo_data DB no accesible. |

| **GET** | **/api/v1/metrics/env/summary** | Estadísticas descriptivas ambientales para un período | *Tag: meteo* |
| --- | --- | --- | --- |

### **Parámetros de query**

| **Parámetro** | **Tipo** | **Req.** | **Default** | **Descripción** | **Ejemplo** |
| --- | --- | --- | --- | --- | --- |
| **node_id** | string | **Sí** | — | ID del nodo. | lit-cordoba-01 |
| **start** | datetime (ISO 8601) | **Sí** | — | Inicio del período. | 2026-06-01T00:00:00Z |
| **end** | datetime (ISO 8601) | **Sí** | — | Fin del período. | 2026-06-07T23:59:59Z |
| **source** | enum (CSV) | No | all | Fuente(s) a incluir en el cálculo. | local_sensor |

### **Respuesta exitosa — HTTP 200**

| {   "status":  "success",   "node_id": "lit-cordoba-01",   "period":  { "start": "2026-06-01T00:00:00Z", "end": "2026-06-07T23:59:59Z", "days": 7 },   "by_source": {     "local_sensor": {       "sample_count": 10020,       "temperature_c":  { "avg": 18.3, "min": 8.1,  "max": 34.7, "std_dev": 6.2 },       "humidity_pct":   { "avg": 62.1, "min": 22.3, "max": 98.5, "std_dev": 14.8 },       "pressure_hpa":   { "avg": 1013.2, "min": 1001.5, "max": 1021.3 },       "rain_events":    4     },     "api_open_meteo": {       "sample_count": 672,       "temperature_c":  { "avg": 17.9, "min": 7.8,  "max": 34.1 },       "total_precipitation_mm": 12.4,       "avg_wind_speed_kmh": 14.2,       "avg_cloud_cover_pct": 38.5     }   } } |
| --- |

| **HTTP Status** | **Descripción** |
| --- | --- |
| **200** | Estadísticas ambientales calculadas por fuente. |
| **400** | VALIDATION_ERROR. |
| **401** | AUTH_FAILED. |
| **404** | NODE_NOT_FOUND o NO_DATA_FOUND. |
| **503** | DB_UNAVAILABLE. |

| **GET** | **/api/v1/metrics/env/latest** | Última medición ambiental por nodo y fuente | *Tag: meteo* |
| --- | --- | --- | --- |

### **Parámetros de query**

| **Parámetro** | **Tipo** | **Req.** | **Default** | **Descripción** | **Ejemplo** |
| --- | --- | --- | --- | --- | --- |
| **node_id** | string | No | all | ID del nodo. Sin parámetro, retorna la última medición de todos los nodos. | lit-cordoba-01 |
| **source** | enum | No | all | Filtrar por fuente. | local_sensor |

### **Respuesta exitosa — HTTP 200**

| {   "status": "success",   "data": [     {       "node_id": "lit-cordoba-01", "source": "local_sensor",       "time": "2026-06-01T14:28:55Z",       "temperature_c": 19.8, "humidity_pct": 61.2, "pressure_hpa": 1012.8,       "seconds_since_last": 65     },     {       "node_id": "lit-cordoba-01", "source": "api_open_meteo",       "time": "2026-06-01T14:00:00Z",       "temperature_c": 19.1, "humidity_pct": 63.0,       "precipitation_mm": 0.0, "wind_speed_kmh": 11.2,       "seconds_since_last": 1735     }   ] } |
| --- |

| **HTTP Status** | **Descripción** |
| --- | --- |
| **200** | Última medición por fuente. |
| **401** | AUTH_FAILED. |
| **404** | NODE_NOT_FOUND. |
| **503** | DB_UNAVAILABLE. |

| **Tag: nodes — Catálogo de nodos de medición** |
| --- |

| **GET** | **/api/v1/nodes** | Lista de nodos registrados y su estado operativo | *Tag: nodes* |
| --- | --- | --- | --- |

### **Descripción**

Retorna el catálogo completo de nodos registrados en station_metadata. Incluye el estado de actividad y los datos de última medición para cada nodo (join con las últimas entradas de network_metrics y env_metrics). Grafana usa este endpoint para poblar las variables de dashboard (variables de tipo Query en Grafana que listan los node_ids disponibles).

### **Parámetros de query**

| **Parámetro** | **Tipo** | **Req.** | **Default** | **Descripción** | **Ejemplo** |
| --- | --- | --- | --- | --- | --- |
| **status** | enum | No | active | Filtrar nodos por estado: 'active', 'inactive', 'maintenance', 'all'. | active |

### **Respuesta exitosa — HTTP 200**

| {   "status": "success",   "count":  1,   "data": [     {       "node_id":          "lit-cordoba-01",       "location_name":    "Laboratorio LIT — FCEFyN, UNC, Córdoba",       "latitude":         -31.4335,       "longitude":        -64.1878,       "altitude_m":       490.0,       "status":           "active",       "hardware_version": "RPi5-8GB-StarV3",       "deployed_at":      "2026-08-01T10:00:00Z",       "telemetry": {         "last_starlink_metric": "2026-06-01T14:29:01Z",         "last_env_metric":      "2026-06-01T14:28:55Z",         "is_reporting":         true    // true si last_metric < 5 min       }     }   ] } |
| --- |

| **HTTP Status** | **Descripción** |
| --- | --- |
| **200** | Lista de nodos. |
| **401** | AUTH_FAILED. |
| **503** | DB_UNAVAILABLE. |

| **GET** | **/api/v1/nodes/{node_id}** | Detalle completo de un nodo y sus sensores | *Tag: nodes* |
| --- | --- | --- | --- |

### **Parámetros de path**

| **Parámetro** | **Tipo** | **Descripción** |
| --- | --- | --- |
| **node_id** | string | Identificador del nodo. Debe existir en station_metadata. |

### **Respuesta exitosa — HTTP 200**

| {   "status":  "success",   "data": {     "node_id":       "lit-cordoba-01",     "location_name": "Laboratorio LIT — FCEFyN, UNC, Córdoba",     "latitude":      -31.4335,     "longitude":     -64.1878,     "status":        "active",     "deployed_at":   "2026-08-01T10:00:00Z",     "notes":         "Antena orientada 15° al norte",     "sensors": [       {         "sensor_id":     1,         "sensor_model":  "BME280",         "sensor_type":   "multi",         "bus_protocol":  "I2C",         "bus_address":   "0x76",         "is_active":     true,         "last_calibrated_at": "2026-08-01T11:00:00Z"       }     ]   } } |
| --- |

| **HTTP Status** | **Descripción** |
| --- | --- |
| **200** | Detalle del nodo y sus sensores. |
| **401** | AUTH_FAILED. |
| **404** | NODE_NOT_FOUND — el node_id no existe en station_metadata. |
| **503** | DB_UNAVAILABLE. |

| **Tag: ingest — Ingesta manual (solo testing/mocks)** |
| --- |

| *Estos endpoints se activan ÚNICAMENTE con ENABLE_INGEST_ENDPOINT=true en el archivo .env. En producción (Etapa 1 y 2) deben estar desactivados: la ingesta real va por MQTT → consumer Python. Su propósito exclusivo es facilitar el desarrollo con mocks y los tests de integración E2E (RF-29, ADR-08).* |
| --- |

| **POST** | **/api/v1/ingest/starlink** | Ingesta manual de métricas Starlink (solo testing) | *Tag: ingest* |
| --- | --- | --- | --- |

### **Descripción**

Recibe un payload JSON con el esquema de telemetría Starlink (idéntico al paquete MQTT IF-01), lo valida con Pydantic y lo inserta directamente en la hypertable network_metrics. Permite poblar la base de datos sin necesidad de levantar el mock MQTT, útil para tests de integración y para el script de backfill histórico (ADR-08, estrategia de Time Warp).

### **Request Body — application/json**

| // Acepta objeto único O array de hasta 1000 objetos (inserción en batch) {   "station_id":     "lit-cordoba-01",          // mapeado a node_id en la DB   "timestamp":      "2026-06-01T14:30:00Z",   "source_module":  "starlink_mock_agent",   "schema_version": "1.0",   "metrics": {     "pop_ping_latency_ms":    35.4,     "pop_ping_drop_rate":     0.001,     "downlink_throughput_bps": 187300000,     "uplink_throughput_bps":   22100000,     "snr_db":                  9.0,     "is_obstructed":           false,     "satellite_count":         14   } } // O array para inserción en batch: [   { "station_id": "lit-cordoba-01", "timestamp": "2026-06-01T14:30:00Z", "metrics": { ... } },   { "station_id": "lit-cordoba-01", "timestamp": "2026-06-01T14:31:00Z", "metrics": { ... } } ] |
| --- |

### **Respuesta exitosa — HTTP 201**

| {   "status":   "success",   "inserted": 1,         // cantidad de filas insertadas   "node_id":  "lit-cordoba-01",   "timestamp": "2026-06-01T14:30:00Z" } |
| --- |

| **HTTP Status** | **Descripción** |
| --- | --- |
| **201** | Datos insertados en network_metrics correctamente. |
| **400** | VALIDATION_ERROR — payload no cumple el esquema Pydantic (tipo incorrecto, rango fuera de bounds). |
| **401** | AUTH_FAILED. |
| **422** | INGEST_DISABLED — ENABLE_INGEST_ENDPOINT=false en producción. |
| **422** | SCHEMA_VERSION_MISMATCH — campo schema_version no soportado. |
| **422** | BATCH_TOO_LARGE — más de 1000 objetos en un solo request. |
| **503** | DB_UNAVAILABLE. |

| **POST** | **/api/v1/ingest/env** | Ingesta manual de datos ambientales (solo testing) | *Tag: ingest* |
| --- | --- | --- | --- |

### **Request Body — application/json**

| {   "station_id":     "lit-cordoba-01",   "timestamp":      "2026-06-01T14:30:00Z",   "source_module":  "mock_bme280",   "schema_version": "1.0",   "metrics": {     "temperature_c":    18.5,     "humidity_pct":     62.3,     "pressure_hpa":     1013.2,     "precipitation_mm": null,     "wind_speed_kmh":   null,     "wind_direction_deg": null,     "cloud_cover_pct":  null,     "source":           "local_sensor"     // campo que mapea a env_metrics.source   } } |
| --- |

### **Respuesta exitosa — HTTP 201**

| { "status": "success", "inserted": 1, "node_id": "lit-cordoba-01", "source": "local_sensor" } |
| --- |

| **HTTP Status** | **Descripción** |
| --- | --- |
| **201** | Datos insertados en env_metrics correctamente. |
| **400** | VALIDATION_ERROR — temperatura fuera de rango CHECK, humidity_pct > 100, etc. |
| **401** | AUTH_FAILED. |
| **422** | INGEST_DISABLED. |
| **503** | DB_UNAVAILABLE. |

# **9. Esquemas Pydantic (Validación de Request y Response)**

Todos los modelos de entrada y salida están definidos como clases Pydantic v2. FastAPI los registra automáticamente en el schema OpenAPI. Los mismos modelos se usan en el consumer MQTT para garantizar coherencia entre los paquetes MQTT y la API.

## **9.1 Modelos de Telemetría Starlink**

| from pydantic import BaseModel, Field, field_validator from datetime import datetime from typing import Optional class StarlinkMetricsIn(BaseModel):     """Métricas crudas del enlace Starlink — usado en POST /ingest/starlink."""     pop_ping_latency_ms:     Optional[float] = Field(None, ge=0, le=10000)     pop_ping_drop_rate:      Optional[float] = Field(None, ge=0, le=1)     downlink_throughput_bps: Optional[int]   = Field(None, ge=0)     uplink_throughput_bps:   Optional[int]   = Field(None, ge=0)     snr_db:                  Optional[float] = Field(None, ge=0)     is_obstructed:           Optional[bool]  = None     satellite_count:         Optional[int]   = Field(None, ge=0, le=100) class StarlinkPayloadIn(BaseModel):     """Envelope del paquete de ingesta — coherente con el paquete MQTT IF-01."""     station_id:     str = Field(..., min_length=3, max_length=64,                                 pattern=r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")     timestamp:      datetime     source_module:  str = Field(..., max_length=64)     schema_version: str = Field(default="1.0")     metrics:        StarlinkMetricsIn     @field_validator("schema_version")     @classmethod     def check_schema_version(cls, v):         if v not in {"1.0"}:             raise ValueError(f"schema_version '{v}' no soportada. Versiones válidas: ['1.0']")         return v     @field_validator("timestamp")     @classmethod     def ensure_utc(cls, v: datetime) -> datetime:         """Convierte a UTC si tiene timezone; rechaza naive datetimes."""         if v.tzinfo is None:             raise ValueError("timestamp debe incluir timezone (usar formato ISO 8601 con Z o +00:00)")         return v.astimezone(timezone.utc) class StarlinkMetricOut(BaseModel):     """Objeto de salida en GET /metrics/starlink — coherente con DER §3.1."""     time:                 datetime     node_id:              str     latency_ms:           Optional[float]     jitter_ms:            Optional[float]     packet_loss_pct:      Optional[float]     throughput_down_bps:  Optional[int]     throughput_up_bps:    Optional[int]     snr_db:               Optional[float]     is_obstructed:        Optional[bool]     satellite_count:      Optional[int]     # Campos adicionales presentes solo en resolution=hourly/daily:     max_latency_ms:       Optional[float] = None     min_latency_ms:       Optional[float] = None     p95_latency_ms:       Optional[float] = None     sample_count:         Optional[int]   = None     class Config:         from_attributes = True   # permite crear desde objetos SQLAlchemy |
| --- |

## **9.2 Modelos de Datos Ambientales**

| class EnvSource(str, Enum):     """Valores válidos de source — coherentes con CHECK constraint de env_metrics."""     LOCAL_SENSOR    = "local_sensor"     API_OPEN_METEO  = "api_open_meteo"     API_OWM         = "api_owm"     API_SMN         = "api_smn"     MOCK_BME280     = "mock_bme280"     MOCK_API        = "mock_api" class EnvMetricsIn(BaseModel):     temperature_c:      Optional[float] = Field(None, gt=-50, lt=80)     humidity_pct:       Optional[float] = Field(None, ge=0, le=100)     pressure_hpa:       Optional[float] = Field(None, gt=800, lt=1100)     precipitation_mm:   Optional[float] = Field(None, ge=0)     wind_speed_kmh:     Optional[float] = Field(None, ge=0)     wind_direction_deg: Optional[int]   = Field(None, ge=0, lt=360)     cloud_cover_pct:    Optional[float] = Field(None, ge=0, le=100)     source:             EnvSource       = EnvSource.LOCAL_SENSOR class EnvPayloadIn(BaseModel):     station_id:     str      = Field(..., min_length=3, max_length=64)     timestamp:      datetime     source_module:  str      = Field(..., max_length=64)     schema_version: str      = Field(default="1.0")     metrics:        EnvMetricsIn |
| --- |

# **10. Configuración del Datasource HTTP en Grafana**

Grafana se conecta a la API REST mediante el datasource de tipo 'Infinity' (plugin recomendado para APIs REST) o mediante queries directas a TimescaleDB. Para el caso de uso del PI, la recomendación es usar TimescaleDB directamente como datasource PostgreSQL nativo (más eficiente para series temporales), y reservar la API REST para el testbed internacional y para los endpoints de /health y /nodes que Grafana usa para el panel de estado.

## **10.1 Configuración del Datasource Infinity (API REST)**

| **Campo** | **Valor** |
| --- | --- |
| **Name** | Starlink API |
| **Type** | Infinity (plugin) |
| **Base URL** | http://api_backend:8000 (Etapa 1, red Docker interna) |
| **Auth Header Name** | X-API-Key |
| **Auth Header Value** | ${GRAFANA_API_KEY} — variable de entorno de Grafana (nunca en texto claro) |
| **Timeout** | 30 s — queries de summary sobre rangos largos pueden tardar |

## **10.2 Ejemplo de Panel Grafana con query a la API**

| // Panel type: Time Series // Datasource: Infinity // URL: /api/v1/metrics/starlink // Method: GET // Query params (bindings con variables de Grafana): //   node_id  = $node_id        (variable del dashboard) //   start    = ${__from:date:iso}  (inicio del time picker) //   end      = ${__to:date:iso}    (fin del time picker) //   resolution = auto //   fields   = latency_ms,packet_loss_pct // Columnas mapeadas en Grafana Infinity: // time            → campo de tiempo (tipo: datetime) // latency_ms      → serie "Latencia (ms)" // packet_loss_pct → serie "Pérdida de paquetes (%)" |
| --- |

# **11. Fragmento OpenAPI 3.1 (YAML)**

FastAPI genera automáticamente el documento OpenAPI completo en GET /api/v1/openapi.json. El siguiente fragmento YAML ilustra la especificación canónica del endpoint principal como referencia para la integración con el testbed internacional:

| openapi: "3.1.0" info:   title: "Starlink Measurement Station API"   description: >     API REST de lectura para la estación de medición satelital LEO del LIT (FCEFyN/UNC).     Provee series temporales de telemetría Starlink y datos ambientales.   version: "1.0.0"   contact:     name: "LIT — FCEFyN/UNC"     email: "lit@efn.uncor.edu" servers:   - url: "http://rpi5-lit.local:8000"     description: "Etapa 1 — On-premises LIT"   - url: "https://starlink-api.lit.efn.uncor.edu"     description: "Etapa 2 — Cloud (futuro)" security:   - ApiKeyAuth: [] components:   securitySchemes:     ApiKeyAuth:       type: apiKey       in: header       name: X-API-Key   schemas:     StarlinkMetricOut:       type: object       properties:         time:                { type: string, format: date-time }         node_id:             { type: string }         latency_ms:          { type: number, nullable: true }         packet_loss_pct:     { type: number, minimum: 0, maximum: 100, nullable: true }         throughput_down_bps: { type: integer, nullable: true }         throughput_up_bps:   { type: integer, nullable: true }         snr_db:              { type: number, nullable: true }         is_obstructed:       { type: boolean, nullable: true }     ErrorResponse:       type: object       required: [status, code, detail, timestamp]       properties:         status:    { type: string, enum: [error] }         code:      { type: string }         detail:    { type: string }         timestamp: { type: string, format: date-time }         path:      { type: string } paths:   /api/v1/health:     get:       tags: [system]       summary: "Estado del sistema"       security: []    # endpoint público, sin auth       responses:         "200":           description: "Estado del sistema (sano o degradado)"   /api/v1/metrics/starlink:     get:       tags: [starlink]       summary: "Series temporales de telemetría Starlink"       parameters:         - name: node_id           in: query           required: true           schema: { type: string }         - name: start           in: query           required: true           schema: { type: string, format: date-time }         - name: end           in: query           required: true           schema: { type: string, format: date-time }         - name: resolution           in: query           schema: { type: string, enum: [raw, hourly, daily, auto], default: auto }         - name: limit           in: query           schema: { type: integer, minimum: 1, maximum: 5000, default: 500 }       responses:         "200":           description: "Series temporales de métricas de red"           content:             application/json:               schema:                 type: object                 properties:                   status:  { type: string }                   count:   { type: integer }                   data:                     type: array                     items: { $ref: "#/components/schemas/StarlinkMetricOut" }         "400": { $ref: "#/components/responses/ValidationError" }         "401": { $ref: "#/components/responses/Unauthorized" }         "404": { $ref: "#/components/responses/NotFound" }         "503": { $ref: "#/components/responses/ServiceUnavailable" } |
| --- |

# **12. Trazabilidad Endpoints ↔ SRS, DER y ADR**

| **Endpoint** | **RFs cumplidos** | **DER — Tablas consultadas** | **ADRs relacionados** | **IF SRS §6** |
| --- | --- | --- | --- | --- |
| **GET /health** | RF-26 | network_metrics, env_metrics | ADR-12 (Docker), ADR-09 | — |
| **GET /metrics/starlink** | RF-25, RF-27, RF-28 | network_metrics, net_hourly, net_daily | ADR-11 (CAGG), ADR-10 | IF-07, IF-09 |
| **GET /metrics/starlink/summary** | RF-25, RF-27 | net_hourly, net_daily | ADR-11 | IF-07, IF-09 |
| **GET /metrics/starlink/latest** | RF-25, RF-34 | network_metrics | ADR-10, ADR-13 | IF-07, IF-09 |
| **GET /metrics/env** | RF-25, RF-27 | env_metrics, env_hourly | ADR-11, ADR-10 | IF-08, IF-09 |
| **GET /metrics/env/summary** | RF-25, RF-32, RF-33 | env_hourly | ADR-11 | IF-08, IF-09 |
| **GET /metrics/env/latest** | RF-25, RF-34 | env_metrics | ADR-13 | IF-08, IF-09 |
| **GET /nodes** | RF-25, RF-34 | station_metadata, network_metrics, env_metrics | ADR-10 | IF-07, IF-08 |
| **GET /nodes/{node_id}** | RF-25 | station_metadata, sensor_catalog | ADR-10 | — |
| **POST /ingest/starlink** | RF-29 | network_metrics | ADR-08, ADR-01 (Pydantic) | IF-05 |
| **POST /ingest/env** | RF-29 | env_metrics | ADR-08, ADR-01 (Pydantic) | IF-06 |

# **13. Historial de Revisiones**

| **Versión** | **Fecha** | **Autores** | **Descripción** |
| --- | --- | --- | --- |
| 1.0 | Junio 2026 | Pavet García, Isaia Soria | Versión inicial. 12 endpoints definidos. Autenticación API Key. Esquemas Pydantic v2. Fragmento OpenAPI 3.1. Configuración Grafana Infinity datasource. |

*— Fin del documento —*

Pavet García & Isaia Soria  |  Dir. Henn / Co-Dir. Cherini