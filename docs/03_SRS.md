# PROYECTO INTEGRADOR

## Escuela de Ingeniería en Computación — FCEFyN / UNC

# Especificación de Requerimientos del Sistema

*Despliegue y extensión de una estación de medición para el análisis experimental de redes satelitales LEO comerciales, con integración de sensado ambiental, monitoreo remoto y visualización de datos.*

| **Campo** | **Detalle** |
| --- | --- |
| **Alumnos** | Aldana Micaela Pavet García (M. 43884931) [aldana.pavet.garcia@mi.unc.edu.ar](mailto:aldana.pavet.garcia@mi.unc.edu.ar) Federico Isaia Soria (M. 40574892) [federico.isaia.soria@mi.unc.edu.ar](mailto:federico.isaia.soria@mi.unc.edu.ar) |
| **Director** | Mgrt. Ing. Santiago Martin Henn |
| **Co-Director** | Dr. Renato Cherini |
| **Laboratorio** | Laboratorio de Informática y Telecomunicaciones (LIT) — FCEFyN/UNC |
| **Versión** | 1.0 |
| **Fecha** | 10 jun 2026 |

## 1. Introducción y Contexto

Este documento especifica los requerimientos funcionales y no funcionales del sistema que se desarrollará en el marco del Proyecto Integrador (PI). El proyecto propone el despliegue, puesta en servicio y extensión funcional de una estación de medición local para su integración en un testbed internacional de análisis de redes satelitales LEO comerciales (Starlink), desarrollado en colaboración con universidades de Canadá (University of Victoria, University of Manitoba, University of Waterloo y Memorial University).

La estación extenderá las capacidades básicas del testbed incorporando: un subsistema de sensado ambiental (temperatura, humedad, presión), almacenamiento persistente de series temporales, un backend de ingesta y consulta de datos, un frontend web de monitoreo y visualización, y capacidades opcionales de videomonitoreo del entorno físico de la antena.

Las pautas técnicas del director incluyen decisiones de diseño clave sobre morfología de paquetes, interfaces entre componentes, selección de lenguajes, desarrollo con mocks/datos sintéticos, contenerización completa con Docker y una estrategia de migración gradual de entorno local a nube.

## 2. Glosario y Acrónimos

| **Término / Acrónimo** | **Definición** |
| --- | --- |
| LEO | Low Earth Orbit — Órbita Terrestre Baja (< 2000 km) |
| LIT | Laboratorio de Informática y Telecomunicaciones (FCEFyN/UNC) |
| PI | Proyecto Integrador |
| Starlink | Constelación satelital LEO comercial operada por SpaceX |
| Testbed | Plataforma experimental de medición distribuida multi-nodo |
| BME280 | Sensor MEMS de temperatura, humedad y presión (Bosch) |
| RPi5 | Raspberry Pi 5 — computadora embebida de bajo costo |
| TimescaleDB | Extensión de PostgreSQL optimizada para series temporales |
| Grafana | Plataforma open-source de observabilidad y dashboards |
| MQTT | Message Queuing Telemetry Transport — protocolo de mensajería IoT |
| Mock | Script o componente que simula datos reales para desarrollo y pruebas |
| IF | Interfaz — contrato de comunicación entre dos componentes |
| RF | Requerimiento Funcional |
| RNF | Requerimiento No Funcional |
| API | Application Programming Interface |
| JSON | JavaScript Object Notation — formato de serialización de datos |
| SRS | Software Requirements Specification (este documento) |

## 3. Alcance del Sistema

### 3.1 Dentro del Alcance

- Despliegue físico de la terminal Starlink, Raspberry Pi 5 y hardware de sensado en el LIT.

- Desarrollo de scripts de medición de red (latencia, jitter, throughput, pérdidas) orquestados por cron.

- Diseño e implementación del subsistema embebido de sensado ambiental (temperatura, humedad, presión).

- Integración de APIs meteorológicas externas como fuente complementaria de datos.

- Diseño e implementación de la arquitectura de datos: broker de mensajes, bases de datos por servicio (Starlink Health y Meteo), persistencia con PostgreSQL + TimescaleDB.

- Contenerización completa de todos los servicios mediante Docker y Docker Compose.

- Desarrollo del backend REST/API para ingesta y consulta de series temporales.

- Desarrollo del frontend web de monitoreo y visualización (dashboards Grafana).

- Incorporación de cámara COTS de bajo costo para videomonitoreo del entorno físico (objetivo secundario).

- Documentación de arquitectura, interfaces, procedimientos de despliegue y plan de migración local → nube.

- Campaña inicial de medición para validar la operatividad integrada del sistema.

### 3.2 Fuera del Alcance

- Demostración de causalidad física concluyente entre variables meteorológicas y desempeño de red Starlink.

- Ingeniería inversa o inferencia de mecanismos internos propietarios del sistema Starlink.

- Análisis estadístico profundo o modelos predictivos sobre los datos recolectados.

- Gestión de múltiples nodos del testbed internacional (el PI cubre únicamente el nodo Córdoba).

- Desarrollo de aplicaciones móviles nativas.

## 4. Arquitectura General del Sistema

El sistema se organiza en cinco capas funcionales que se comunican a través de interfaces bien definidas. Cada capa puede desarrollarse, probarse y desplegarse de forma independiente mediante contenedores Docker.

| **Capa** | **Componentes** | **Tecnología Principal** |
| --- | --- | --- |
| 1 — Adquisición | Script telemetría Starlink, Script sensado BME280, APIs meteorológicas externas | Python 3, C/MicroPython (RPi5) |
| 2 — Mensajería | Message Broker (desacoplamiento productor-consumidor) | MQTT (Mosquitto) |
| 3 — Persistencia | DB Starlink Health, DB Meteo (una por servicio) | PostgreSQL + TimescaleDB |
| 4 — Backend | API REST para ingesta y consulta de series temporales | Python (FastAPI) o Node.js |
| 5 — Observabilidad | Dashboards de red, dashboards meteorológicos, widget videomonitoreo | Grafana |

Durante las etapas de desarrollo se reemplazarán los componentes de hardware real por mocks (scripts generadores de datos sintéticos) que publican en los mismos tópicos MQTT y siguen la misma morfología de paquetes. Esto permite desarrollar y validar toda la pila de software antes de contar con el hardware físico.

## 5. Morfología de Paquetes e Interfaces (IF)

Todos los mensajes intercambiados entre componentes utilizan JSON como formato de serialización. Se eligió JSON sobre alternativas binarias (Protobuf, MessagePack) por su facilidad de depuración y la naturaleza del volumen de datos (< 1 mensaje/segundo por fuente), donde el overhead de texto plano es despreciable frente a la ganancia en legibilidad y mantenibilidad.

### 5.1 Paquete de Telemetría de Red (Starlink)

Publicado en el tópico MQTT: starlink/metrics/<node_id>

| **Campo** | **Tipo** | **Descripción** | **Ejemplo** |
| --- | --- | --- | --- |
| timestamp | string (ISO 8601) | Instante UTC de la medición | "2026-06-01T14:30:00Z" |
| node_id | string | Identificador único del nodo | "lit-cordoba-01" |
| latency_ms | float | RTT promedio al servidor de referencia (ms) | 35.4 |
| jitter_ms | float | Variación del RTT (ms) | 4.2 |
| packet_loss_pct | float | Porcentaje de paquetes perdidos (0–100) | 0.5 |
| throughput_down_mbps | float | Velocidad de bajada medida (Mbps) | 187.3 |
| throughput_up_mbps | float | Velocidad de subida medida (Mbps) | 22.1 |
| obstruction_pct | float / null | Porcentaje de obstrucción del FOV (si disponible) | 1.2 |
| signal_quality | float / null | Calidad de señal reportada (0–1) | 0.95 |
| schema_version | string | Versión del esquema de paquete | "1.0" |

### 5.2 Paquete de Datos Ambientales (Sensor Local)

Publicado en el tópico MQTT: meteo/sensor/<node_id>

| **Campo** | **Tipo** | **Descripción** | **Ejemplo** |
| --- | --- | --- | --- |
| timestamp | string (ISO 8601) | Instante UTC de la medición | "2026-06-01T14:30:00Z" |
| node_id | string | Identificador del nodo sensor | "lit-cordoba-01" |
| source | string | Fuente del dato: 'local_sensor' o 'api_ext' | "local_sensor" |
| temperature_c | float | Temperatura en grados Celsius | 18.5 |
| humidity_pct | float | Humedad relativa (0–100) | 62.3 |
| pressure_hpa | float | Presión atmosférica en hPa | 1013.2 |
| sensor_id | string / null | Identificador del sensor físico | "BME280-01" |
| schema_version | string | Versión del esquema de paquete | "1.0" |

### 5.3 Paquete de Datos Meteorológicos Externos (API)

Publicado en el tópico MQTT: meteo/external/<node_id> — sincronizado por el servicio de integración de APIs.

| **Campo** | **Tipo** | **Descripción** | **Ejemplo** |
| --- | --- | --- | --- |
| timestamp | string (ISO 8601) | Instante UTC del pronóstico o reporte | "2026-06-01T14:00:00Z" |
| node_id | string | Nodo al que corresponde la ubicación | "lit-cordoba-01" |
| source | string | Nombre del proveedor externo | "open-meteo" |
| temperature_c | float / null | Temperatura reportada por API | 17.0 |
| humidity_pct | float / null | Humedad reportada por API | 65.0 |
| pressure_hpa | float / null | Presión reportada por API | 1012.0 |
| precipitation_mm | float / null | Precipitación acumulada (mm) | 0.0 |
| wind_speed_kmh | float / null | Velocidad del viento (km/h) | 12.5 |
| cloud_cover_pct | float / null | Cobertura de nubes (0–100) | 30.0 |
| schema_version | string | Versión del esquema | "1.0" |

## 6. Definición de Interfaces (IF)

Se documentan a continuación los contratos de comunicación entre los componentes principales del sistema.

| **IF #** | **Nombre** | **Origen** | **Destino** | **Protocolo / Formato** | **Descripción** |
| --- | --- | --- | --- | --- | --- |
| **IF-01** | Script → Broker | Script telemetría Starlink (o Mock) | MQTT Broker | MQTT / JSON | Publicación de paquete de red cada 60 s en tópico starlink/metrics/<node_id> |
| **IF-02** | Sensor → Broker | Script sensor BME280 (o Mock) | MQTT Broker | MQTT / JSON | Publicación de paquete ambiental cada 60 s en tópico meteo/sensor/<node_id> |
| **IF-03** | API Ext → Broker | Servicio integrador APIs climáticas | MQTT Broker | MQTT / JSON | Publicación de datos externos cada 15 min en tópico meteo/external/<node_id> |
| **IF-04** | Broker → Consumer | MQTT Broker | Consumer / Subscriber Python | MQTT / JSON | Entrega de mensajes a los servicios suscriptores según tópico |
| **IF-05** | Consumer → DB Red | Consumer de telemetría | DB Starlink Health | SQL / psycopg2 | INSERT de métricas de red en hypertable network_metrics |
| **IF-06** | Consumer → DB Meteo | Consumer ambiental/externo | DB Meteo | SQL / psycopg2 | INSERT de variables ambientales en hypertable env_metrics |
| **IF-07** | Backend → DB Red | Backend API REST | DB Starlink Health | SQL / ORM | SELECT con filtros de rango temporal para exposición vía API |
| **IF-08** | Backend → DB Meteo | Backend API REST | DB Meteo | SQL / ORM | SELECT con filtros de rango temporal para exposición vía API |
| **IF-09** | Grafana → DB | Grafana (datasource) | Ambas DBs (TimescaleDB) | PostgreSQL protocol | Consultas nativas Grafana a las bases de datos para dashboards |
| **IF-10** | Grafana → Backend | Grafana (datasource) | Backend API REST | HTTP / JSON | Consultas a endpoints REST opcionales para datos procesados o agregados |
| **IF-11** | Cámara → Backend | Cámara IP / COTS | Backend / Grafana | RTSP / HLS / MJPEG | Stream de video para widget de videomonitoreo en Grafana (objetivo secundario) |

## 7. Requerimientos Funcionales (RF)

Los requerimientos se clasifican por subsistema y se les asigna prioridad: **Alta** (esencial para el PI), **Media** (importante pero diferible) y **Baja** (objetivo secundario).

### 7.1 Adquisición — Script de Telemetría de Red

| **ID** | **Descripción** | **Prioridad** |
| --- | --- | --- |
| **RF-01** | El script de telemetría DEBE ejecutarse periódicamente (período configurable, por defecto 60 s) mediante un mecanismo de orquestación temporal (cron, scheduler Python o equivalente). | Alta |
| **RF-02** | El script DEBE medir latencia (RTT), jitter, pérdida de paquetes, throughput de bajada y subida utilizando herramientas de red estándar (ping, iperf3, speedtest-cli o equivalentes). | Alta |
| **RF-03** | El script DEBE incorporar, cuando esté disponible, métricas adicionales provistas por la API local de diagnóstico de la terminal Starlink (obstruction_pct, signal_quality). | Media |
| **RF-04** | El script DEBE publicar los resultados empaquetados en formato JSON (ver §5.1) en el broker MQTT en el tópico correspondiente. | Alta |
| **RF-05** | DEBE existir un Mock del script de telemetría que genere datos sintéticos plausibles (distribuciones estadísticas configurables) y publique en los mismos tópicos con la misma morfología. | Alta |

### 7.2 Adquisición — Subsistema de Sensado Ambiental

| **ID** | **Descripción** | **Prioridad** |
| --- | --- | --- |
| **RF-06** | El subsistema embebido DEBE leer temperatura, humedad y presión del sensor BME280 (u equivalente) conectado al Raspberry Pi 5 vía I2C o SPI. | Alta |
| **RF-07** | Las lecturas DEBEN realizarse a una frecuencia configurable (por defecto 60 s) y publicarse en el broker MQTT (ver §5.2). | Alta |
| **RF-08** | El driver del sensor DEBE incluir manejo básico de errores: reintento automático ante falla de lectura y registro de eventos de error. | Alta |
| **RF-09** | DEBE existir un Mock del sensor que genere datos sintéticos dentro de rangos realistas para Córdoba (ej. temperatura 0–40 °C, humedad 20–100 %, presión 950–1030 hPa). | Alta |
| **RF-10** | El subsistema DEBE incluir una rutina de calibración básica documentada (offset de temperatura, compensación de presión). | Media |

### 7.3 Adquisición — Integración de APIs Meteorológicas Externas

| **ID** | **Descripción** | **Prioridad** |
| --- | --- | --- |
| **RF-11** | El servicio integrador DEBE consultar al menos una API meteorológica externa gratuita (ej. Open-Meteo, OpenWeatherMap) con un período configurable (por defecto 15 min). | Media |
| **RF-12** | Los datos externos DEBEN normalizarse al esquema JSON unificado (ver §5.3) antes de publicarse en el broker MQTT. | Media |
| **RF-13** | El servicio DEBE manejar errores de red (timeout, rate limit) con retries con backoff exponencial y registro de eventos. | Media |
| **RF-14** | Se DEBE evaluar la factibilidad de integrar datos del observatorio hidrometeorológico de Córdoba como fuente adicional. | Baja |

### 7.4 Mensajería — Message Broker (MQTT)

| **ID** | **Descripción** | **Prioridad** |
| --- | --- | --- |
| **RF-15** | El broker MQTT (Mosquitto u equivalente) DEBE desacoplar a todos los productores de datos (scripts, sensores, APIs) de los consumidores (subscribers que persisten en base de datos). | Alta |
| **RF-16** | El broker DEBE soportar autenticación por usuario/contraseña para conexiones locales. | Alta |
| **RF-17** | Los tópicos DEBEN seguir la jerarquía definida: starlink/metrics/<node_id>, meteo/sensor/<node_id>, meteo/external/<node_id>. | Alta |
| **RF-18** | Los mensajes DEBEN publicarse con QoS 1 (at least once) para garantizar entrega ante desconexiones transitorias. | Alta |

### 7.5 Persistencia — Bases de Datos (Database per Service)

| **ID** | **Descripción** | **Prioridad** |
| --- | --- | --- |
| **RF-19** | DEBE desplegarse una instancia independiente de PostgreSQL + TimescaleDB para métricas de red (DB: starlink_health) y otra para datos ambientales (DB: meteo_data). Cada servicio accede únicamente a su propia base de datos. | Alta |
| **RF-20** | En DB starlink_health DEBE crearse una hypertable 'network_metrics' con los campos del esquema §5.1, particionada por tiempo con chunk_time_interval de 1 día. | Alta |
| **RF-21** | En DB meteo_data DEBE crearse una hypertable 'env_metrics' con los campos de los esquemas §5.2 y §5.3, con columna 'source' para distinguir origen. | Alta |
| **RF-22** | DEBEN definirse índices secundarios sobre node_id y source para acelerar consultas de filtrado frecuentes. | Media |
| **RF-23** | DEBE configurarse una política de retención de datos de al menos 6 meses de historia sin compresión activa. | Media |
| **RF-24** | DEBEN implementarse scripts de inicialización (init.sql) que creen esquemas, hypertables, índices y políticas, ejecutables idempotentemente. | Alta |

### 7.6 Backend — API REST

| **ID** | **Descripción** | **Prioridad** |
| --- | --- | --- |
| **RF-25** | El backend DEBE exponer endpoints REST para consulta de series temporales de red y ambientales, con filtros de rango temporal (start, end), node_id y source. | Alta |
| **RF-26** | DEBE existir un endpoint de health-check (GET /health) que retorne el estado de conectividad a ambas bases de datos y al broker MQTT. | Alta |
| **RF-27** | El backend DEBE validar los parámetros de entrada (tipos, rangos) y retornar errores HTTP apropiados (400, 404, 500) con mensajes descriptivos. | Alta |
| **RF-28** | El backend DEBE documentar su API mediante OpenAPI/Swagger, accesible en /docs. | Media |
| **RF-29** | DEBE soportar un endpoint de ingesta manual (POST) para inserción de datos de prueba, utilizable durante el desarrollo con mocks. | Media |

### 7.7 Observabilidad — Grafana y Dashboards

| **ID** | **Descripción** | **Prioridad** |
| --- | --- | --- |
| **RF-30** | Grafana DEBE estar configurado con datasource directo a ambas instancias de TimescaleDB. | Alta |
| **RF-31** | DEBE existir un dashboard 'Red Starlink' con paneles de series temporales para: latencia, jitter, pérdida de paquetes, throughput de bajada y subida. | Alta |
| **RF-32** | DEBE existir un dashboard 'Datos Ambientales' con paneles para: temperatura, humedad y presión (sensor local y API externa en la misma gráfica para comparación). | Alta |
| **RF-33** | DEBE existir un dashboard 'Correlación Red-Clima' que permita visualizar en el mismo eje temporal métricas de red y variables ambientales. | Alta |
| **RF-34** | DEBE existir un panel de 'Estado del Sistema' que muestre el estado de cada servicio (online/offline) y la última marca temporal de datos recibidos. | Alta |
| **RF-35** | Los dashboards DEBEN exportarse como JSON y versionarse junto al código del proyecto. | Media |
| **RF-36** | DEBE integrarse un widget o panel de videomonitoreo en Grafana para visualización del estado físico de la antena. En desarrollo puede mockearse con un loop de video o webcam local. | Baja |

### 7.8 Acceso Remoto y Operación

| **ID** | **Descripción** | **Prioridad** |
| --- | --- | --- |
| **RF-37** | El nodo RPi5 DEBE estar accesible remotamente mediante SSH con autenticación por clave pública, sin contraseña. | Alta |
| **RF-38** | DEBE implementarse un mecanismo de túnel inverso o equivalente (ej. reverse SSH, Tailscale, WireGuard) para garantizar acceso remoto desde fuera de la red local del LIT. | Alta |
| **RF-39** | Los scripts de medición DEBEN ejecutarse automáticamente al iniciar el sistema (systemd services o Docker restart policy: always). | Alta |
| **RF-40** | DEBE existir un mecanismo de watchdog que reinicie automáticamente cualquier servicio caído dentro de los 5 minutos siguientes al fallo. | Media |

## 8. Requerimientos No Funcionales (RNF)

### 8.1 Rendimiento y Escalabilidad

| **ID** | **Descripción** | **Prioridad** |
| --- | --- | --- |
| **RNF-01** | El sistema DEBE ser capaz de ingestar al menos 3 flujos de datos simultáneos (red, sensor local, API externa) con un throughput de hasta 10 mensajes/minuto cada uno, sin pérdida de datos bajo condiciones normales. | Alta |
| **RNF-02** | Las consultas de series temporales para rangos de hasta 30 días DEBEN retornar resultados en menos de 5 segundos desde Grafana. | Media |
| **RNF-03** | La arquitectura de contenedores DEBE permitir agregar nuevos nodos de medición (nuevas instancias de los scripts) sin modificar el código del broker, las bases de datos ni el backend. | Alta |

### 8.2 Disponibilidad y Recuperación ante Fallos

| **ID** | **Descripción** | **Prioridad** |
| --- | --- | --- |
| **RNF-04** | El sistema completo DEBE funcionar en modo autónomo (sin intervención manual) durante períodos de al menos 7 días consecutivos. | Alta |
| **RNF-05** | Ante un corte de energía y posterior reinicio del hardware, todos los servicios DEBEN recuperarse automáticamente en menos de 3 minutos. | Alta |
| **RNF-06** | El sistema DEBE tolerar pérdida de conectividad con la red exterior (acceso a APIs externas) sin interrumpir la adquisición y almacenamiento de datos locales. | Alta |
| **RNF-07** | Los datos DEBEN persistir ante reinicios de contenedores mediante volúmenes Docker persistentes en disco del RPi5. | Alta |

### 8.3 Portabilidad y Reproducibilidad (Docker)

| **ID** | **Descripción** | **Prioridad** |
| --- | --- | --- |
| **RNF-08** | TODOS los servicios (scripts, broker, bases de datos, backend, Grafana) DEBEN estar contenerizados con Docker y orquestados mediante un único docker-compose.yml. | Alta |
| **RNF-09** | El entorno de desarrollo local (PC del alumno con mocks) y el entorno de producción (RPi5 con hardware real) DEBEN utilizar el mismo docker-compose.yml, diferenciados únicamente por variables de entorno o archivos .env. | Alta |
| **RNF-10** | La migración de entorno local a nube DEBE requerir únicamente cambiar la variable de entorno DB_HOST (y equivalentes) de 'localhost' a la IP del servidor cloud, sin modificar código. | Alta |
| **RNF-11** | El proyecto DEBE incluir un archivo README.md con instrucciones de despliegue reproducibles desde cero en menos de 30 minutos para un operador con conocimientos de Docker. | Media |

### 8.4 Seguridad

| **ID** | **Descripción** | **Prioridad** |
| --- | --- | --- |
| **RNF-12** | Las credenciales de bases de datos, broker y APIs externas NO DEBEN estar hardcodeadas en el código fuente. DEBEN gestionarse mediante variables de entorno y archivos .env excluidos del control de versiones. | Alta |
| **RNF-13** | El acceso a Grafana DEBE requerir autenticación (usuario/contraseña). El usuario por defecto DEBE cambiarse en el primer despliegue. | Alta |
| **RNF-14** | Los puertos de bases de datos (5432) NO DEBEN exponerse públicamente en entornos de producción. Solo el backend REST y Grafana deben tener puertos mapeados externamente. | Alta |
| **RNF-15** | El acceso SSH al RPi5 DEBE desactivar la autenticación por contraseña y solo permitir autenticación por clave pública. | Alta |

### 8.5 Mantenibilidad y Observabilidad del Sistema

| **ID** | **Descripción** | **Prioridad** |
| --- | --- | --- |
| **RNF-16** | Todos los servicios DEBEN emitir logs estructurados (JSON o texto con nivel, timestamp y servicio) hacia stdout, colectables con docker logs. | Alta |
| **RNF-17** | El código Python DEBE seguir las convenciones PEP 8 y estar tipado (type hints). El código C/MicroPython para el sensor DEBE incluir comentarios de interfaz para cada función. | Media |
| **RNF-18** | Cada componente DEBE tener su propio Dockerfile con imagen base declarada explícitamente (sin 'latest'). Las versiones de dependencias DEBEN estar pinneadas. | Media |
| **RNF-19** | DEBEN existir tests de integración básicos que verifiquen el flujo completo Mock → Broker → Consumer → DB con datos sintéticos. | Media |

## 9. Selección de Lenguajes y Tecnologías

La selección de tecnologías sigue el principio de usar lo más adecuado para cada tarea, priorizando el ecosistema abierto, la compatibilidad con ARM (RPi5) y la madurez en producción.

| **Componente** | **Tecnología Seleccionada** | **Justificación** |
| --- | --- | --- |
| **Script telemetría de red** | Python 3 + subprocess / speedtest-cli / iperf3 | Amplio soporte de herramientas de red, facilidad de orquestación con cron/APScheduler, ecosistema maduro |
| **Driver sensor BME280** | Python 3 + adafruit-circuitpython-bme280 (RPi5) o MicroPython (ESP32) | Biblioteca oficial del fabricante, soporte I2C/SPI nativo en RPi5, alternativa embebida ligera |
| **Integrador APIs externas** | Python 3 + httpx / requests | Misma base del proyecto, manejo de async opcional con httpx para resiliencia |
| **Message Broker** | Eclipse Mosquitto (MQTT v3.1.1 / v5.0) | Estándar de facto IoT, muy ligero en recursos, imagen Docker oficial ARM-compatible |
| **Suscriptores / Consumers** | Python 3 + paho-mqtt | Biblioteca MQTT oficial Eclipse, integración simple con psycopg2 para persistencia |
| **Base de datos** | PostgreSQL 16 + TimescaleDB 2.x | Recomendación del director, estándar para series temporales, soporte nativo ARM, hypertables |
| **Backend API REST** | Python 3 + FastAPI | Alta performance, generación automática OpenAPI, async nativo, tipado con Pydantic |
| **Visualización / Dashboards** | Grafana OSS (última LTS) | Datasource nativo PostgreSQL/TimescaleDB, configuración como código (JSON), imagen Docker oficial |
| **Contenerización** | Docker Engine + Docker Compose v2 | Portabilidad entre entornos, soporte RPi5 (ARM64), gestión declarativa con compose |
| **Control de versiones** | Git + GitHub/GitLab | Versionado de código, Dockerfiles, scripts SQL y dashboards Grafana como código |
| **Formato de datos** | JSON (RFC 8259) | Legibilidad para debugging, sin necesidad de compilador de schema, suficiente para volumen < 1 msg/s |

## 10. Estrategia de Mocks y Desarrollo Local

El desarrollo con mocks permite construir y validar toda la pila de software (broker → consumer → base de datos → backend → Grafana) antes de disponer del hardware físico (antena Starlink, RPi5, sensor BME280). Los mocks son reemplazos directos de los productores reales.

### 10.1 Mock de Telemetría de Red (Starlink)

- Script Python que se ejecuta cada 60 s vía cron o APScheduler.

- Genera métricas con distribuciones plausibles: latencia ~ Normal(35, 5) ms; jitter ~ Exponential(2) ms; pérdida ~ Bernoulli(p=0.005) %; throughput_down ~ Normal(180, 30) Mbps.

- Inyecta ocasionalmente eventos de degradación (spikes de latencia > 200 ms, pérdidas > 5 %) para validar la detección en dashboards.

- Publica en MQTT tópico: starlink/metrics/lit-cordoba-01

### 10.2 Mock de Sensor Ambiental (BME280)

- Script Python que se ejecuta cada 60 s.

- Genera temperatura con variación sinusoidal diaria (10–35 °C para Córdoba), humedad correlacionada inversamente con temperatura, presión con deriva lenta.

- Incluye ruido gaussiano ±0.5 °C, ±2 % HR, ±0.5 hPa para simular variabilidad del sensor.

- Publica en MQTT tópico: meteo/sensor/lit-cordoba-01

### 10.3 Estrategia de Población de Bases de Datos

- Script de backfill: genera 30 días de datos históricos sintéticos e inserta directamente en las hypertables. Permite probar rangos temporales amplios en Grafana desde el inicio.

- Los mocks corren continuamente durante el desarrollo para simular operación en tiempo real.

- El switching mock → hardware real se realiza apagando el contenedor del mock y habilitando el servicio real: sin cambios de código.

## 11. Plan de Migración Local → Nube

La arquitectura basada en Docker garantiza que el path de migración sea determinístico y de bajo riesgo. El documento de migración es un entregable del PI con valor arquitectónico explícito.

| **Etapa** | **Entorno** | **Descripción** | **Criterio de Salida** |
| --- | --- | --- | --- |
| **Etapa 0** | PC Desarrollo (localhost) | Todo el sistema con mocks corriendo en Docker Compose. Sin hardware real. Verificación de esquemas, interfaces y dashboards. | Dashboards poblados con 30 días de datos sintéticos. Todos los RF-01 a RF-40 validables con mocks. |
| **Etapa 1** | RPi5 en LIT (on-premises) | Reemplazo de mocks por hardware real (Starlink + BME280). Mismo docker-compose.yml. Bases de datos locales en disco RPi5. | 72 h de operación continua sin intervención manual. Datos reales visibles en Grafana. |
| **Etapa 2** | Cloud (VPS/servidor universitario) | Las bases de datos se mueven a un servidor en la nube. El RPi5 actúa solo como nodo de adquisición y publicación MQTT. Solo cambia DB_HOST y MQTT_HOST en .env. | Migración completada con cero pérdida de datos. Acceso a Grafana desde internet. |
| **Etapa 3 (Futuro)** | Testbed Internacional | El nodo Córdoba se integra plenamente al testbed multi-nodo internacional. El backend es accesible por los socios. | Primer dataset conjunto Córdoba–Canadá publicado. |

La migración transparente es posible porque: (1) todo corre en contenedores con la misma imagen, (2) la configuración de conexión está externalizada en variables de entorno, y (3) TimescaleDB puede exportar/importar datos con pg_dump estándar para el traspaso de historia.

## 12. Requerimientos de Hardware

| **Componente** | **Especificación mínima** | **Observaciones** |
| --- | --- | --- |
| **Terminal Starlink** | Kit Starlink Residencial o Portátil + suscripción activa | Provisión: Universidades de Canadá o LIT |
| **Nodo de cómputo** | Raspberry Pi 5 (8 GB RAM recomendado) | Corre todos los contenedores Docker en producción |
| **Almacenamiento** | microSD o SSD NVMe 128 GB | Alta velocidad de escritura para TimescaleDB; SSD recomendado para durabilidad |
| **Sensor ambiental** | BME280 (temperatura, humedad, presión) módulo breakout | Conexión I2C o SPI; alimentado por GPIO del RPi5 |
| **Cámara (secundario)** | Cámara IP COTS o webcam USB ≥ 720p con soporte RTSP | Para videomonitoreo de la antena; opcional en Etapa 1 |
| **Conectividad local** | Switch o router Ethernet, cable CAT5e/6 entre terminal Starlink y RPi5 | Conexión LAN preferida sobre Wi-Fi para estabilidad de mediciones |
| **Alimentación** | UPS o batería de respaldo para RPi5 y terminal | Recomendado para garantizar continuidad ante cortes de energía |

## 13. Criterios de Aceptación del Sistema

El sistema se considerará funcional y apto para presentación del PI cuando se verifiquen los siguientes criterios:

| **#** | **Criterio** | **Evidencia esperada** |
| --- | --- | --- |
| **CA-01** | Flujo end-to-end con mocks validado | Script mock → MQTT → Consumer → TimescaleDB → Grafana: datos visibles en dashboard en < 2 min desde inicio. |
| **CA-02** | Flujo end-to-end con hardware real validado (Etapa 1) | Métricas reales de Starlink y BME280 visibles en Grafana. Logs sin errores por 72 h. |
| **CA-03** | Persistencia ante reinicios | docker-compose down && docker-compose up: todos los datos previos permanecen, todos los servicios vuelven en < 3 min. |
| **CA-04** | Dashboards de correlación operativos | Dashboard 'Correlación Red-Clima' muestra latencia Starlink y temperatura en el mismo eje temporal con datos reales. |
| **CA-05** | Acceso remoto seguro funcional | SSH sin contraseña y túnel remoto funcionando desde fuera de la red del LIT. Grafana accesible vía URL pública. |
| **CA-06** | Reproducibilidad del despliegue | Un tercero (director o evaluador) puede desplegar el sistema completo siguiendo el README en < 30 min en una máquina limpia. |
| **CA-07** | Plan de migración documentado | Documento de migración local → nube completo, con pasos verificados (al menos Etapas 0 y 1 ejecutadas). |
| **CA-08** | Interfaces documentadas | Documento de interfaces (o este SRS) disponible y consistente con el código en producción (morfología de paquetes coincide con lo implementado). |

## 14. Matriz de Trazabilidad

La siguiente tabla vincula los objetivos del PI con los requerimientos que los satisfacen.

| **Objetivo del PI** | **Requerimientos Relacionados** |
| --- | --- |
| Despliegue e integración de la estación de medición (OBJ-1) | RF-01, RF-02, RF-04, RF-37, RF-38, RF-39, RNF-04, RNF-05, RNF-08 |
| Diseño de arquitectura de adquisición y almacenamiento (OBJ-2) | RF-15 a RF-24, RNF-01, RNF-03, RNF-08 a RNF-10 |
| Subsistema embebido de sensado ambiental (OBJ-3) | RF-06, RF-07, RF-08, RF-09, RF-10 |
| Integración de fuentes externas de datos meteorológicos (OBJ-4) | RF-11, RF-12, RF-13, RF-14 |
| Documentación, validación y transferencia (OBJ-5) | RNF-11, RNF-16, RNF-17, CA-06, CA-07, CA-08 |
| Plataforma web de monitoreo y visualización (OBJ-SEC-1) | RF-25 a RF-29, RF-30 a RF-35, RNF-02 |
| Videomonitoreo del sitio (OBJ-SEC-2) | RF-36, IF-11 |
| Estrategia de migración local → nube (Pauta Director) | RNF-09, RNF-10, §11 completo, CA-07 |
| Desacoplamiento mediante Message Broker (Pauta Director) | RF-15 a RF-18, IF-01 a IF-04 |
| Desarrollo con Mocks / Dummy Data (Pauta Director) | RF-05, RF-09, §10 completo |

## 15. Historial de Revisiones

| **Versión** | **Fecha** | **Autores** | **Descripción del cambio** |
| --- | --- | --- | --- |
| **1.0** | Junio 2026 | Pavet García, Isaia Soria | Versión inicial del SRS, basada en propuesta de PI aprobada y pautas del director. |