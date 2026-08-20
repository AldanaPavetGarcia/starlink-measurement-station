# PROYECTO INTEGRADOR

## Escuela de Ingeniería en Computación — FCEFyN / UNC

# Registro de decisiones de Arquitectura

| **Campo** | **Detalle** |
| --- | --- |
| **Proyecto** | Despliegue y extensión de estación de medición para análisis experimental de redes satelitales LEO comerciales (Starlink), con integración de sensado ambiental, monitoreo remoto y visualización de datos. |
| **Alumnos** | Aldana Micaela Pavet García (M. 43884931) [aldana.pavet.garcia@mi.unc.edu.ar](mailto:aldana.pavet.garcia@mi.unc.edu.ar) Federico Isaia Soria (M. 40574892) [federico.isaia.soria@mi.unc.edu.ar](mailto:federico.isaia.soria@mi.unc.edu.ar) |
| **Director** | Mgrt. Ing. Santiago Martin Henn |
| **Co-Director** | Dr. Renato Cherini |
| **Laboratorio** | Laboratorio de Informática y Telecomunicaciones (LIT) — FCEFyN/UNC |
| **Versión ADR Log** | 2.0 (consolidación y ampliación del borrador inicial v1.0) |
| **Fecha** | 11 jun 2026 |
| **Estado del documento** | Activo — se actualiza a medida que el proyecto avanza de fase |

## 1. Introducción y Propósito del Documento

Un Architecture Decision Record (ADR) es un documento de corta extensión pero alta densidad informativa que captura una decisión de diseño arquitectónico relevante junto a su contexto, las alternativas evaluadas y las consecuencias esperadas. A diferencia de la documentación técnica tradicional, el ADR no describe cómo funciona el sistema, sino por qué está construido de esa manera.

Este ADR Log consolida y amplía el conjunto de decisiones de diseño tomadas durante el desarrollo del Proyecto Integrador, organizadas por fases según las directrices del director. Cada ADR sigue la estructura canónica propuesta por Michael Nygard (2011) y adoptada ampliamente en ingeniería de software moderna:

| **Sección del ADR** | **Propósito** |
| --- | --- |
| **Contexto** | Describe la situación técnica o de negocio que motiva la decisión. Es el «por qué ahora». |
| **Marco Teórico y Bibliografía** | Fundamenta la decisión en la literatura académica, papers o estándares industriales reconocidos. |
| **Alternativas Consideradas** | Enumera todas las opciones técnicas evaluadas seriamente, con sus características clave. |
| **Decisión** | Anuncia inequívocamente qué alternativa fue elegida y por qué se rechazaron las demás. |
| **Justificación (Pros ****&**** Contras)** | Analiza las ventajas, desventajas y mitigaciones de la decisión tomada. |
| **Consecuencias e Implicaciones** | Describe el impacto en el resto del sistema: qué se facilita, qué se complica, qué se cierra. |
| **Estado** | Propuesto / Aceptado / Obsoleto / Superado por ADR-XX |

Este documento es de carácter vivo: cada ADR puede ser superado por uno posterior si las circunstancias cambian. Un ADR obsoleto no se elimina; se marca como tal y se referencia el nuevo, preservando la trazabilidad de las razones históricas.

## 2. Resumen Ejecutivo del ADR Log

| **ID** | **Título** | **Fase** | **Decisión Principal** | **Estado** |
| --- | --- | --- | --- | --- |
| **ADR-01** | Morfología de Paquetes y Serialización | Diseño | Sistema Híbrido: Protobuf (extracción) + JSON validado (transporte interno) | **Propuesto** |
| **ADR-02** | Tipo de Sensores Ambientales | Diseño / HW | Sensores Digitales I2C (BME280) sobre analógicos | **Propuesto** |
| **ADR-03** | Arquitectura de Integración del Sensor (Gateway) | Diseño / HW | ESP32 con MQTT nativo como Sensor Gateway Node | **Propuesto** |
| **ADR-04** | Protocolo de Comunicación entre Componentes | Diseño / IF | MQTT para sensores → broker; ORM sobre TCP para consumer → DB | **Propuesto** |
| **ADR-05** | Lenguajes de Programación | Diseño / Impl. | Python 3 como lenguaje primario; C++ (Arduino IDE) para microcontroladores | **Propuesto** |
| **ADR-06** | Mock de Telemetría Starlink | Simulación | Stateful Mock con Random Walk e inyección de caos | **Propuesto** |
| **ADR-07** | Mocks de Sensores Ambientales y APIs Externas | Simulación | Mocks desacoplados como microservicios Docker independientes | **Propuesto** |
| **ADR-08** | Estrategia de Población de Bases de Datos | Simulación | Ingesta orgánica E2E + variable TIME_WARP_FACTOR para backfill | **Propuesto** |
| **ADR-09** | Message Broker | Persistencia | Eclipse Mosquitto (MQTT v5.0) | **Propuesto** |
| **ADR-10** | Patrón Database per Service | Persistencia | Tres instancias independientes: starlink_health_db, meteo_db y station_config_db | **Propuesto** |
| **ADR-11** | Motor de Base de Datos de Series Temporales | Persistencia | PostgreSQL 16 + extensión TimescaleDB sobre InfluxDB y Postgres puro | **Propuesto** |
| **ADR-12** | Contenerización de Infraestructura | Persistencia | Docker Engine + Docker Compose V2; todo contenerizado | **Propuesto** |
| **ADR-13** | Plataforma de Visualización y Dashboards | Observabilidad | Grafana OSS sobre desarrollo frontend a medida | **Propuesto** |
| **ADR-14** | Postura de Seguridad y Exposición de Puertos | Observabilidad | Zero Trust local: solo puerto Grafana expuesto externamente + filtrado de IP | **Propuesto** |
| **ADR-15** | Mock de Videomonitoreo (Streaming) | Observabilidad | Microservicio Flask/MJPEG a 5 FPS sobre placeholder estático | **Propuesto** |
| **ADR-16** | Exposición de Eventos de Handover Satelital | Esquema / HW real | Campos agregados `handover_count`/`outage_duration_ms` en `metrics` | **Propuesto** |
| **ADR-17** | Reemplazo de `snr_db` por `snr_low` | Esquema / HW real | Booleano `snr_low` (← `not isSnrAboveNoiseFloor`; `isSnrPersistentlyLow` no existe en el firmware real, hallazgo 12/08) sobre float inexistente en firmware real | **Propuesto** |
| **ADR-18** | Exposición de `alignmentStats` (Orientación Física de la Antena) | Esquema / HW real | Campos planos de tilt/azimuth/elevación en `metrics`, sin sub-objeto anidado | **Propuesto** |
| **ADR-19** | Corrección de la fuente de `is_obstructed` | Esquema / HW real | `dishGetDiagnostics.alerts.obstructed` (llamada gRPC nueva) sobre `obstructionStats.fractionObstructed > 0`, que era acumulado y no el estado actual (hallazgo 20/08) | **Propuesto** |
| **ADR-20** | Bridge MQTT saliente hacia el broker compartido de la VM de cátedra | Persistencia / IF | Bridge `out` de Mosquitto sobre `starlink/#`, credenciales en `conf.d/` gitignored, salida por el enlace Starlink (`eth0`) | **Propuesto** |

# FASE 1 — Diseño y Definición de Contratos

## ADR-01 — Morfología de Paquetes y Formato de Serialización

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-01 |
| **Estado** | Propuesto |
| **Fecha** | Junio 2026 |
| **Supercede a** | — |
| **Impacta en** | ADR-04, ADR-06, ADR-07, ADR-08, ADR-11 |

### Contexto y Motivación

La antena Starlink (Dishy McFlatface) expone localmente un servidor gRPC en la dirección IP 192.168.100.1, puerto 9200. gRPC usa Protocol Buffers (Protobuf) como mecanismo de serialización nativo. Cualquier integración con la antena comienza, obligatoriamente, en el mundo binario de los Protobufs.

Al mismo tiempo, el resto del sistema (broker MQTT, bases de datos PostgreSQL, Grafana, mocks de desarrollo) vive en el ecosistema de texto y APIs web, donde JSON es el estándar de facto. La tensión arquitectónica es: ¿se mantiene el formato binario a lo largo de toda la cadena, o se convierte a JSON en algún punto? ¿Y en qué punto exacto?

La decisión del formato de datos es de alta consecuencia porque afecta: la complejidad de los scripts de extracción, la complejidad de los mocks de desarrollo, la forma en que TimescaleDB almacena y consulta los datos, la observabilidad de los mensajes en el broker MQTT, y la curva de aprendizaje del equipo.

### Marco Teórico y Bibliografía

- Maeda et al. — «Evaluation of Data Serialization Formats in IoT Systems»: compara JSON, Protobuf, CBOR y MessagePack en entornos con restricciones de ancho de banda. Conclusión: Protobuf reduce el tamaño de payload entre un 30–70 % respecto a JSON, pero el overhead de CPU para compresión/descompresión en dispositivos embebidos puede eliminar esa ventaja en redes locales de alta velocidad.

- Sparky8512 — Repositorio starlink-grpc-tools (GitHub, 2021): referencia académica para la comunidad investigadora de Starlink. Provee wrappers Python que abstraen el Protobuf nativo de la antena en diccionarios Python manejables.

- RFC 8259 (JSON): define el estándar de intercambio de datos JSON. Universalmente soportado, sin necesidad de compilador de esquemas.

- Pydantic v2 (Docs): librería Python de validación de datos que permite definir esquemas estrictos sobre JSON, obteniendo las garantías de tipado de Protobuf sobre la legibilidad de JSON.

### Alternativas Consideradas

#### Alternativa A — JSON Puro (End-to-End)

Ignorar que la antena habla Protobuf y usar el wrapper de Python (starlink-grpc-tools) para convertir inmediatamente a JSON sin ningún paso intermedio de validación formal. Todos los componentes del sistema hablan JSON nativo.

| **Aspecto** | **Evaluación** |
| --- | --- |
| Simplicidad de implementación | ✅ Muy alta — un solo formato en todo el sistema |
| Legibilidad de mensajes en el broker | ✅ Alta — debuggeable con cualquier cliente MQTT |
| Eficiencia de red (ancho de banda) | ⚠️ Moderada — JSON ~2–3x más grande que Protobuf |
| Tipado y validación de datos | ❌ Sin garantías — un bug puede corromper la DB silenciosamente |
| Compatibilidad con mocks | ✅ Perfecta — los mocks emiten strings JSON directamente |
| Complejidad de mantenimiento | ✅ Baja |

#### Alternativa B — Protobuf End-to-End

Mantener el formato Protobuf nativo de la antena a lo largo de toda la cadena: MQTT transporta mensajes binarios Protobuf, la base de datos almacena blobs binarios, Grafana consume vía un plugin binario.

| **Aspecto** | **Evaluación** |
| --- | --- |
| Eficiencia de red y almacenamiento | ✅ Muy alta — payloads 30–70 % más pequeños que JSON |
| Tipado fuerte nativo | ✅ Muy alta — el .proto es el contrato fuerte por diseño |
| Legibilidad y debuggabilidad | ❌ Nula — mensajes binarios ilegibles sin herramientas específicas |
| Complejidad de los mocks | ❌ Alta — requiere compilar archivos .proto para cada iteración |
| Compatibilidad con TimescaleDB/Grafana | ❌ Requiere plugins adicionales y consultas complejas |
| Curva de aprendizaje del equipo | ❌ Alta — Protobuf IDL es un lenguaje adicional a dominar |

#### Alternativa C — Sistema Híbrido con Validación Estricta (SELECCIONADA)

Usar el wrapper Protobuf de la antena como entrada, convertir a diccionario Python en memoria, validar con Pydantic (tipado estricto, cotas de valores, campos obligatorios) y serializar a JSON para todo el transporte interno (MQTT) y almacenamiento (TimescaleDB).

### Decisión

**✅ Decisión: Alternativa C — Sistema Híbrido (Protobuf → dict Python en memoria → Pydantic → JSON)**

(El paso intermedio es una estructura de datos en memoria, no un formato de serialización — el dict nunca se serializa ni se transmite tal cual, solo existe dentro del proceso Python hasta llegar a Pydantic.)

Se extrae el dato en Protobuf nativo de la antena usando starlink-grpc-tools. Inmediatamente se convierte a dict Python. Pydantic valida el esquema (tipos, rangos, campos requeridos) antes de que el dato toque cualquier sistema downstream. La salida es JSON para MQTT, PostgreSQL y todos los componentes internos.

### Estructura concreta del payload: envelope + `metrics` anidado

El JSON del paquete Starlink tiene dos niveles, no es una tabla plana de campos al mismo nivel: un envelope con metadatos de identificación (`schema_version`, `node_id`, `timestamp`) y un objeto anidado `metrics` con las métricas de red (`latency_ms`, `jitter_ms`, `packet_loss_pct`, `throughput_down_bps`, `throughput_up_bps`, `snr_low`, `is_obstructed`, `satellite_count`, `handover_count`, `outage_duration_ms`, `tilt_angle_deg`, `boresight_azimuth_deg`, `boresight_elevation_deg`, `desired_boresight_azimuth_deg`, `desired_boresight_elevation_deg`, `attitude_uncertainty_deg`):

```json
{
  "schema_version": "1.1",
  "node_id": "lit-cordoba-01",
  "timestamp": "2026-06-01T14:30:00Z",
  "metrics": {
    "latency_ms": 35.4,
    "jitter_ms": 4.2,
    "packet_loss_pct": 0.5,
    "throughput_down_bps": 187300000,
    "throughput_up_bps": 22100000,
    "snr_low": false,
    "is_obstructed": false,
    "satellite_count": 14,
    "handover_count": 0,
    "outage_duration_ms": 0.0,
    "tilt_angle_deg": 2.1,
    "boresight_azimuth_deg": -175.7,
    "boresight_elevation_deg": 51.7,
    "desired_boresight_azimuth_deg": -176.0,
    "desired_boresight_elevation_deg": 52.0,
    "attitude_uncertainty_deg": 0.3
  }
}
```

Motivo: separa el ciclo de vida del envelope (identidad del paquete, rara vez cambia) del ciclo de vida de `metrics` (sí puede evolucionar — nuevos campos de telemetría con futuros firmwares de la antena) sin acoplar la validación de uno al otro. Ya implementado así en `src/mock_starlink/schema.py` (`StarlinkPayloadIn.metrics: StarlinkMetrics`) y verificado end-to-end contra un broker real (`docker compose --profile mocks up`, semana 4-5). Esta estructura gobierna el paquete MQTT y el body de `POST /ingest/starlink` — no aplica a las filas de `network_metrics` ni a la salida de los GET de la API REST, que son planas por naturaleza (columnas SQL). Campos de `snr_low` en adelante agregados por ADR-16/17/18 (agosto 2026, `schema_version` 1.0→1.1).

### Enmienda: mecanismo de extracción real — `grpcurl` en vez de `grpcio`+`starlink-grpc-tools`

Este ADR (párrafo de Decisión, arriba) describe la extracción vía `starlink-grpc-tools`, que usa `grpcio` con bindings Python compilados contra los `.proto` de la comunidad. Al implementar `src/acquisition/` (Semana 10) se optó en cambio por **`grpcurl`** (invocado como subproceso, `src/acquisition/grpc_client.py`), aprovechando que la antena expone *server reflection* — confirmado en el relevamiento presencial del 04/08/2026 (`docs/PROGRESS.md` §Semana 10: `grpcurl -plaintext 192.168.100.1:9200 list` funciona sin compilar nada).

**No cambia la decisión de fondo de este ADR** (Protobuf nativo → dict Python → Pydantic → JSON) — solo el mecanismo de la primera flecha. Motivo del cambio: reflection en runtime evita vendorizar/mantener los `.proto` propietarios de Starlink en este repo, es el método ya validado a mano contra la antena real durante el relevamiento (mismo comando, mismo resultado), y no depende de que `starlink-grpc-tools` mantenga sus wrappers actualizados contra cambios de firmware. Contra: un proceso `grpcurl` por llamada tiene más overhead que una llamada gRPC nativa in-process — aceptable dado el intervalo de polling de 60s (RF-01), muy por debajo de cualquier límite de throughput relevante.

⚠️ Sin acceso presencial a la RPi5/antena en la sesión donde se escribió `src/acquisition/`, este cambio de mecanismo no se validó todavía contra hardware real — queda pendiente de confirmar en la próxima visita al LIT (ver `docs/PROGRESS.md` §Semana 10).

### Justificación — Rechazo de Alternativas

**Rechazo de Alternativa A (JSON Puro):** el JSON no validado permite que errores de tipo (ej. un string '15ms' donde se espera float 15.0) lleguen silenciosamente a la base de datos, corrompiendo las series temporales. La pérdida de datos silenciosa es inaceptable en un proyecto de medición científica. Pydantic resuelve esto sin los costos operativos de Protobuf.

**Rechazo de Alternativa B (Protobuf End-to-End):** el costo de desarrollo se multiplica: cada mock debe compilar un archivo .proto, cada cambio de esquema requiere recompilar. En una tesis con ciclos de iteración cortos y dos desarrolladores, esto es overhead inaceptable. Además, TimescaleDB no tiene soporte nativo para consultas sobre campos Protobuf binarios.

**Rol de Pydantic como Anti-Corruption Layer:** en términos de Domain-Driven Design (Evans, 2003), la validación Pydantic cumple el rol de un Anti-Corruption Layer (ACL) entre el dominio externo (el firmware propietario de la antena, con su propio vocabulario y formato Protobuf, fuera de nuestro control y sujeto a cambios de firmware) y el dominio interno del sistema (el modelo `StarlinkPayloadIn`, que es la Single Source of Truth de la morfología de paquetes). Ningún dato cruza esa frontera sin pasar por la validación: si el firmware cambia un tipo o un rango de valores, la excepción de Pydantic lo detiene ahí, antes de que corrompa el modelo interno o la base de datos.

### Pros y Contras de la Decisión Tomada

| **Dimensión** | **PRO ✅** | **CONTRA ⚠️** | **Mitigación** |
| --- | --- | --- | --- |
| Legibilidad | JSON legible en logs, broker y DB. Debug inmediato sin herramientas especiales. | — | — |
| Tipado y Seguridad | Pydantic garantiza tipos, rangos y campos obligatorios antes de persistir. | — | — |
| Compatibilidad con Mocks | Los mocks emiten strings JSON directamente. Sin compilación de esquemas. | — | — |
| Tamaño de Payload | — | JSON consume ~2–3x más bytes que Protobuf equivalente. | Compresión gzip en transmisión cloud. Irrelevante en LAN local (< 1 msg/min). |
| Compatibilidad con TimescaleDB | Columnas JSONB con índices GIN para queries sobre campos internos. | — | — |
| Performance de CPU | — | Parsear JSON consume más CPU que Protobuf binario. | Despreciable: la Raspberry Pi 5 tiene capacidad de sobra para < 1 msg/seg. |
| Evolución del esquema | Cambiar un campo JSON requiere solo editar el modelo Pydantic. | — | — |
| Onboarding de nuevos contribuyentes | JSON + Pydantic son conocidos por cualquier desarrollador Python. | — | — |

### Consecuencias e Implicaciones

- Todo componente que produzca datos (script real, mock, integrador de API) DEBE serializar su salida como JSON válido siguiendo el esquema definido en la SRS (§5).

- El modelo Pydantic es el contrato único de verdad (Single Source of Truth) para la morfología de paquetes. Cualquier cambio de esquema se hace en el modelo y se propaga automáticamente.

- TimescaleDB almacenará los campos como columnas nativas (no como JSONB) para optimizar las queries de Grafana. La conversión Python dict → columnas SQL la hace el ORM (SQLAlchemy).

- Los mocks son simplificaciones válidas: pueden omitir la capa Pydantic y emitir JSON directamente si los datos sintéticos son trivialmente correctos.

## ADR-02 — Tipo de Sensores Ambientales: Analógicos vs. Digitales

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-02 |
| **Estado** | Propuesto |
| **Impacta en** | ADR-03, ADR-05, ADR-07 |

### Contexto y Motivación

El sistema requiere medir temperatura, humedad relativa y presión atmosférica en el entorno físico de la antena Starlink. La primera decisión de hardware es fundamental: ¿cómo debe ser el sensor que transforma la variable física en un número digital procesable por el software?

Esta decisión impacta directamente en la complejidad del driver de software, la precisión de las mediciones, la sensibilidad al ruido electromagnético del entorno (una antena Starlink emite señales de radiofrecuencia en el rango de las bandas Ku/Ka, que pueden interferir con señales analógicas de baja amplitud) y la robustez ante fallas eléctricas.

### Marco Teórico

- Teorema de Nyquist-Shannon: la frecuencia de muestreo de un ADC debe ser al menos el doble de la componente de frecuencia máxima de la señal analógica. Al usar el BME280 (sensor digital), el ADC interno del chip ya resuelve este problema por diseño.

- Interferencia Electromagnética (EMI): cables que transportan señales analógicas de baja amplitud (milivoltios) actúan como antenas y captan ruido RF del entorno. Los sensores digitales envían señales de nivel lógico (0 V / 3.3 V o 5 V) inmunes a este tipo de interferencia.

- Hoja de datos Bosch BME280: precisión de temperatura ±0.5 °C, humedad ±3 % RH, presión ±1 hPa. Calibración de fábrica almacenada en EEPROM interna del chip.

### Alternativas Consideradas

| **Criterio de Comparación** | **Alt. A — Sensores Analógicos (LM35, NTC, LDR)** | **Alt. B — Sensores Digitales I2C (BME280) ✅** |
| --- | --- | --- |
| Señal de salida | Voltaje continuo proporcional (mV) | Datos digitales procesados (protocolo I²C/SPI) |
| ADC externo requerido | Sí — el RPi5 no tiene ADC nativo (requiere chip MCP3008 adicional) | No — ADC integrado en el chip del sensor |
| Sensibilidad a EMI/ruido RF | Alta — cables analógicos captan interferencia de la antena Starlink | Muy baja — señal digital de nivel lógico, inmune a EMI |
| Calibración | Manual — requiere curva matemática en software; deriva con temperatura y tiempo | De fábrica (Bosch) — coeficientes en EEPROM interna del chip |
| Variables medidas | 1 por sensor (necesita 3 sensores distintos) | 3 en 1 solo chip: temperatura, humedad Y presión |
| Complejidad del driver | Alta — lectura ADC, conversión matemática, filtros anti-aliasing en software | Baja — librería Adafruit abstrae todo en 3 líneas de Python |
| Puntos de falla potenciales | Chip ADC externo + 3 sensores + cables analógicos + código de calibración | 1 solo chip; falla de hardware resulta en excepción Python tratable |
| Costo de reemplazo | Bajo por unidad, pero requiere resolver el ADC externo | Módulo breakout BME280 ≈ USD 5–10. Reemplazo plug-and-play |
| Precisión en condiciones reales | Variable — depende de calidad del ADC, blindaje de cables, temperatura ambiente | Garantizada por datasheet en todo el rango operativo |

### Decisión

**✅ Decisión: Alternativa B — Sensores Digitales I2C, específicamente el BME280 de Bosch**

Se selecciona el sensor digital BME280 conectado vía bus I²C al Raspberry Pi 5. Un único chip provee las tres variables requeridas (T, HR, P) con calibración de fábrica garantizada y sin necesidad de hardware ADC externo. Pesa también en la decisión que el BME280 ya viene con interfaces integradas y estandarizadas en ambos niveles: hardware (bus I²C nativo, sin ADC ni circuitería de acondicionamiento de señal externa) y software (librería `adafruit-circuitpython-bme280` ya publicada y mantenida), evitando desarrollar un driver propio desde cero como requeriría un sensor analógico.

### Pros y Contras

| **Categoría** | **PRO ✅ / CONTRA ⚠️** | **Detalle** |
| --- | --- | --- |
| **Precisión** | ✅ PRO | Calibración Bosch de fábrica. Sin deriva de calibración en el tiempo operativo del proyecto (< 2 años). |
| **Simplicidad HW** | ✅ PRO | Conexión SDA+SCL+VCC+GND al RPi5. Cuatro cables. Sin ADC externo, sin soldadura compleja. |
| **Robustez EMI** | ✅ PRO | Señal digital de nivel lógico. Inmune a la interferencia RF de la antena Starlink. |
| **Integración SW** | ✅ PRO | Librería adafruit-circuitpython-bme280: tres líneas de Python para obtener T, HR y P. |
| **Consolidación** | ✅ PRO | Un solo módulo mide tres variables. Reduce puntos de falla y cables en la instalación. |
| **Limitación de dirección I²C** | ⚠️ CONTRA | El BME280 solo tiene dos posibles direcciones I²C (0x76 y 0x77). No pueden conectarse más de 2 en el mismo bus sin un multiplexor TCA9548A. Suficiente para el PI actual. |
| **Sensibilidad a humedad extrema** | ⚠️ CONTRA | Por encima del 90 % HR el sensor puede saturarse. Mitigación: encapsulado físico con membrana Gore-Tex en instalación outdoor. |

### Consecuencias e Implicaciones

- La librería adafruit-circuitpython-bme280 se incluye en el requirements.txt del microservicio de sensado.

- El driver debe manejar la excepción OSError del bus I²C (sensor desconectado) con reintento automático y registro de evento de error, sin colapsar el contenedor.

- El mock del BME280 (ADR-07) genera datos con las mismas distribuciones estadísticas que el hardware real, permitiendo validar el sistema antes de la instalación física.

- En el escenario del ESP32 como gateway (ADR-03), el BME280 se conecta al bus I²C del ESP32, no del RPi5 directamente.

## ADR-03 — Integración Arquitectónica del Sensor: Raspberry Pi Directo vs. ESP32 Gateway

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-03 |
| **Estado** | Propuesto |
| **Depende de** | ADR-02 |
| **Impacta en** | ADR-04, ADR-05, ADR-07 |

### Contexto y Motivación

Una vez decidido usar el BME280, surge la pregunta arquitectónica: ¿quién lee físicamente el sensor? El Raspberry Pi 5 puede leerlo directamente vía sus pines GPIO/I²C. Pero esto genera riesgos prácticos importantes: el calor disipado por el procesador del RPi5 contamina la lectura de temperatura; si el sensor sufre un cortocircuito eléctrico, puede dañar el RPi5 y sus datos históricos; y Linux no garantiza determinismo en el muestreo a intervalos exactos.

El patrón de diseño IoT conocido como 'Microcontroller Gateway Node' propone usar un microcontrolador barato y dedicado para la lectura de periféricos lentos, liberando al nodo Edge (RPi5) para tareas de alto nivel.

### Alternativas Consideradas

| **Criterio** | **Alt. A — RPi5 directo por I²C** | **Alt. B — Arduino Uno + Serial Bridge** | **Alt. C — ESP32 con MQTT nativo ✅** |
| --- | --- | --- | --- |
| Aislamiento térmico | ❌ El RPi5 calienta hasta 80°C bajo estrés. Contamina T. | ✅ Sensor alejado del RPi5 | ✅ Sensor alejado + desacoplado físicamente |
| Determinismo de muestreo | ⚠️ Linux no es RTOS; jitter posible en lecturas | ✅ Loop de Arduino determinista | ✅ Loop de ESP32 determinista |
| Protección eléctrica del RPi5 | ❌ Un cortocircuito en el sensor puede dañar el RPi5 | ✅ Arduino actúa como fusible de USD 5 | ✅ ESP32 actúa como fusible de USD 5 |
| Dependencia de script intermediario | No aplica | ❌ Requiere script Python puente Serial → MQTT en RPi5 | ✅ El ESP32 publica MQTT directamente por Wi-Fi |
| Desacoplamiento físico | ❌ Requiere cable I²C al RPi5 | ⚠️ Requiere cable USB al RPi5 | ✅ Solo necesita Wi-Fi compartida. Sin cables entre nodos |
| Complejidad de firmware | No aplica | Baja — Serial.println() en C++ | Baja — misma IDE Arduino, añade Wi-Fi + PubSubClient |
| Costo de hardware adicional | USD 0 (usa GPIO del RPi5) | ~USD 5 (Arduino Nano) | ~USD 5–10 (ESP32 DevKit) |

### Decisión

**✅ Decisión: Alternativa C — ESP32 como Sensor Gateway Node con MQTT nativo**

El ESP32 lee el BME280 vía I²C local, construye el paquete JSON (librería ArduinoJson) y publica directamente en el broker MQTT del RPi5 vía Wi-Fi. El RPi5 nunca toca el hardware del sensor. Este diseño implementa el patrón Microcontroller Gateway Node con desacoplamiento físico completo.

### Pros y Contras

| **Categoría** | **PRO ✅ / CONTRA ⚠️** | **Detalle** |
| --- | --- | --- |
| **Aislamiento térmico** | ✅ PRO | El sensor está físicamente alejado del RPi5. La temperatura que mide corresponde al ambiente de la antena, no al procesador. |
| **Protección eléctrica** | ✅ PRO | Un fallo eléctrico destruye el ESP32 (USD 5–10), no el RPi5 con su disco y datos históricos. |
| **Desacoplamiento absoluto** | ✅ PRO | El ESP32 solo necesita Wi-Fi. El sensor puede estar a metros de la RPi5 sin cableado entre nodos. |
| **Determinismo de muestreo** | ✅ PRO | El loop() de ESP32 ejecuta cada 60 000 ms con jitter < 1 ms. Linux (RPi5) puede tener jitter de decenas de ms bajo carga. |
| **Integración con arquitectura MQTT** | ✅ PRO | El ESP32 es un productor MQTT nativo. Encaja perfectamente con el broker central (ADR-09) sin scripts intermediarios. |
| **Dependencia del router Wi-Fi** | ⚠️ CONTRA | Si el router falla, el ESP32 no puede publicar. Mitigación: el firmware implementa reconnect() automático con backoff exponencial (delay inicial 1 s, factor x2 por intento fallido, tope de 60 s, reintentos indefinidos — mismo esquema que usan los SDKs de AWS IoT/Azure) y el broker maneja el Last Will and Testament. |
| **Gestión de credenciales Wi-Fi** | ⚠️ CONTRA | Las credenciales de red deben estar en el firmware del ESP32. Mitigación: uso de un archivo de configuración compilado no versionado (credentials.h en .gitignore). |
| **MQTT sin TLS en red local** | ⚠️ CONTRA | MQTT sobre puerto 1883 sin cifrado en la LAN del laboratorio. Aceptable en red local aislada; se evaluará TLS para la fase cloud. |

### Consecuencias e Implicaciones

- Mecanismo de Last Will and Testament (LWT) de MQTT, compartido por todos los productores (real o mock, de cualquier módulo): si un productor se cuelga sin desconectarse limpiamente, el broker emite automáticamente un mensaje de alerta con `retain=true` (un nuevo suscriptor ve el último estado sin esperar el próximo heartbeat), QoS 1. **Enmienda 14/08/2026** (ver `docs/PROGRESS.md` → "Coordinación pendiente con Fede", prueba de integración en vivo con su mock): el tópico originalmente definido acá era único y compartido, `system/status/<node_id>` — se descubrió que dos productores de dominios distintos (`starlink_mock` y `mock_bme280` de Fede) publicando bajo el mismo `node_id` se pisaban el mensaje retained entre sí, porque MQTT solo retiene un mensaje por tópico. Corregido para seguir el mismo esquema domain-first que ya usan los tópicos de datos (`starlink/metrics/<node_id>` vs. `meteo/sensor/<node_id>`, ver ADR-04): **`starlink/status/<node_id>`** para productores del módulo Starlink (`starlink_mock`, `starlink_acquisition`) y **`meteo/status/<node_id>`** para productores del módulo ambiental (`esp32_bme280`, `mock_bme280`). Payload JSON sin cambios: `{"node_id": "...", "source": "esp32_bme280|starlink_grpc|starlink_mock|...", "status": "offline"}`. Todo productor configura su propio LWT con este formato, en el tópico de su dominio.

- El tópico MQTT del ESP32 sigue la jerarquía definida: meteo/sensor/<node_id>.

- El mock del BME280 (ADR-07) publica en el mismo tópico con idéntica morfología. El consumer no distingue entre dato real y sintético; solo el campo source del JSON lo indica.

- Para la Fase 2 (hardware real), el ESP32 se configura con la IP del broker en la red del LIT. No se requieren cambios de código en el consumer ni en el broker.

## ADR-04 — Protocolo de Comunicación e Interfaces entre Componentes

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-04 |
| **Estado** | Propuesto |
| **Impacta en** | ADR-09, ADR-10, ADR-12 |

### Contexto y Motivación

Con los microservicios definidos (script Starlink, sensor ESP32/BME280, integrador de APIs externas, consumer, bases de datos, backend API, Grafana), es necesario decidir cómo estos componentes se comunican entre sí. La elección del protocolo de comunicación determina el nivel de acoplamiento temporal, espacial y de comportamiento entre servicios.

El sistema involucra comunicaciones de naturalezas radicalmente distintas: publicaciones de telemetría de baja frecuencia (1 msg/min), lecturas de base de datos ad-hoc para dashboards Grafana, y solicitudes HTTP de la API REST. No existe un único protocolo óptimo para todos estos casos.

### Marco Teórico

- Richardson, Chris — «Microservices Patterns»: el patrón Event-Driven Architecture con Pub/Sub es el estándar para arquitecturas desacopladas donde los productores no deben conocer a los consumidores.

- ISO/IEC 20922 (MQTT v3.1.1): estándar internacional que define el protocolo MQTT como mecanismo de mensajería M2M para entornos con redes poco confiables y dispositivos con recursos limitados.

- Richardson — «Database per Service»: los servicios no deben compartir base de datos. La comunicación entre el producer y la DB debe pasar por un intermediario (el consumer/subscriber) que actúa como gateway de persistencia.

### Alternativas Consideradas por Tipo de Comunicación

| **Caso de Uso** | **Alt. A — REST HTTP Síncrono** | **Alt. B — MQTT Asíncrono Pub/Sub ✅** | **Alt. C — Conexión SQL Directa** |
| --- | --- | --- | --- |
| Sensor/Script → Sistema | ⚠️ Si el receptor cae, el dato se pierde (timeout) | ✅ El broker retiene mensajes hasta que el consumer reconecta | ❌ Acopla el sensor a la estructura interna de la DB |
| Consumer → Base de Datos | No aplica | No aplica — MQTT no habla SQL | ✅ Directo pero frágil sin ORM. Se usa ORM (SQLAlchemy) |
| Frontend (Grafana) → DB | No aplica | No aplica | ✅ Grafana tiene datasource nativo PostgreSQL |
| Acoplamiento temporal | ❌ Alto — ambos extremos deben estar vivos simultáneamente | ✅ Bajo — el broker actúa como buffer desacoplado | ⚠️ Medio — requiere pool de conexiones |
| Tolerancia a fallos de red | ❌ Un microcorte pierde el request | ✅ QoS 1 garantiza entrega even con desconexiones | ⚠️ Requiere retry manual |

### Decisión

**✅ Decisión: Arquitectura Políglota de Interfaces**

SENSORES/SCRIPTS → BROKER: MQTT (QoS 1, tópicos jerarquizados). 

CONSUMER → BASE DE DATOS: ORM SQLAlchemy sobre TCP/IP nativo de PostgreSQL. GRAFANA → BASE DE DATOS: datasource nativo PostgreSQL directo. 

USUARIO → DATOS: API REST FastAPI (para acceso programático externo, monitoreo y endpoints de health-check).

### Jerarquía Oficial de Tópicos MQTT

La taxonomía de tópicos establece el enrutamiento semántico de todos los mensajes en el sistema:

| **Tópico MQTT** | **Productor** | **Consumidor** | **Base de Datos Destino** |
| --- | --- | --- | --- |
| starlink/metrics/<node_id> | Script gRPC Starlink (real o mock) | Consumer Router | starlink_health_db → hypertable network_metrics |
| meteo/sensor/<node_id> | ESP32 + BME280 (real o mock) | Consumer Router | meteo_db → hypertable env_metrics |
| meteo/external/<node_id> | Integrador API (Open-Meteo) | Consumer Router | meteo_db → hypertable env_metrics |
| starlink/status/<node_id> | Productores Starlink, real o mock (heartbeats, LWT) | Grafana + Alertmanager | No persiste — alerting en tiempo real |
| meteo/status/<node_id> | Productores ambientales, real o mock (heartbeats, LWT) | Grafana + Alertmanager | No persiste — alerting en tiempo real |

> Alineado con `docs/03_SRS.md` §5.1 (IF-01, IF-02, IF-03, RF-17), `docs/06_DER.md` y
> `docs/08_Plan_QA.md` (UT-03, IT-01/IT-02) — esos cuatro documentos ya usaban esta
> convención de forma consistente; esta tabla era la que estaba desactualizada. Nota:
> `bme280_hardware`/`bme280_mock` se unifican en un solo tópico porque ADR-01 exige que
> el hardware real y el mock sean intercambiables 1:1 sin cambios downstream (mismo
> tópico, misma morfología de paquete). **Enmienda 14/08/2026**: `starlink/status/<node_id>`
> y `meteo/status/<node_id>` reemplazan al tópico único `system/status/<node_id>` que
> tenía esta tabla originalmente — no era realmente domain-first pese a lo que decía esta
> nota, y una prueba de integración en vivo con el módulo de Fede confirmó que dos
> productores de dominios distintos bajo el mismo `node_id` se pisaban el retained entre
> sí (ver ADR-03, sección "Consecuencias e Implicaciones", y `docs/PROGRESS.md`). Ninguno
> de los dos tópicos de status está cubierto por el SRS (son tópicos operativos, no de
> datos de medición) pero no contradicen RF-17, que solo obliga la jerarquía de los tres
> tópicos de datos.
>
> Se eliminó la fila `nodo/lit-01/net_health/iperf_test` (Script iPerf3 activo): no
> está cubierta por el SRS ni por el "Alcance técnico" de `CLAUDE.md` §1.1 (telemetría
> pasiva vía gRPC, sin tests activos), rompía la convención domain-first del resto de
> la tabla, y de existir en el futuro debería enrutarse a `network_tests`
> (`docs/06_DER.md` §3.2, pensada justamente para iperf3/speedtest/traceroute), no a
> `network_metrics`. Queda fuera de alcance del PI actual — ver comentario resuelto
> [^c5] y `docs/PROGRESS.md`.

### Pros y Contras de la Arquitectura Políglota

| **Aspecto** | **PRO ✅ / CONTRA ⚠️** | **Detalle** |
| --- | --- | --- |
| **Desacoplamiento** | ✅ PRO | Los productores no conocen la existencia de la DB. Solo saben que existe un broker. Agregar nuevas fuentes de datos no requiere tocar el consumer. |
| **Resiliencia QoS 1** | ✅ PRO | Si el consumer cae, el broker retiene los mensajes (sesión persistente). Al reconectar, entrega los mensajes sin pérdida. |
| **Enrutamiento por tópico** | ✅ PRO | El consumer implementa el patrón Database per Service (ADR-10) analizando el tópico de cada mensaje para decidir a qué DB lo inserta. |
| **Complejidad operativa** | ⚠️ CONTRA | Más componentes = más superficie de falla. Mitigación: healthcheck de Docker y restart: unless-stopped en todos los servicios. |
| **Latencia adicional (MQTT broker)** | ⚠️ CONTRA | El broker añade ~1–5 ms de latencia en la ruta del dato. Completamente despreciable para datos de telemetría a 1 msg/min. |

## ADR-05 — Selección de Lenguajes y Paradigma de Programación

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-05 |
| **Estado** | Propuesto |
| **Impacta en** | ADR-06, ADR-07, ADR-08, ADR-09, ADR-12 |

### Contexto y Motivación

La arquitectura de microservicios en Docker permite usar el lenguaje más apropiado para cada tarea específica (programación políglota). Sin embargo, la proliferación de lenguajes eleva el costo de mantenimiento y la carga cognitiva del equipo. Se debe encontrar el equilibrio entre especialización y pragmatismo.

El equipo está compuesto por dos desarrolladores con experiencia primaria en Python. El ecosistema académico del testbed internacional (universidades canadienses socias) también usa Python como lenguaje base. El microcontrolador (ESP32) exige C++ por su naturaleza de hardware embebido.

### Alternativas Consideradas

| **Alternativa** | **Stack** | **Fortaleza Principal** | **Debilidad Principal** |
| --- | --- | --- | --- |
| A — Python puro (End-to-End) | Python 3.11 + asyncio + FastAPI + SQLAlchemy | Máxima coherencia del equipo. Ecosistema de librerías insuperable para Data Science e IoT. | GIL limita paralelismo real (mitigable con asyncio y multiprocessing). |
| B — Stack Híbrido (C++ + Python + Node.js) | C++ para hardware, Node.js para API REST, Python para data | Lenguaje óptimo para cada tarea. Performance máxima. | Tres stacks, tres conjuntos de dependencias, tres curvas de aprendizaje. Inmanejable en 2 personas. |
| C — Golang | Go para todos los microservicios | Performance de sistema, concurrencia nativa con goroutines, binarios Docker ultra livianos. | El equipo no tiene experiencia en Go. Las librerías gRPC de Starlink y para TimescaleDB son mejores en Python. Curva de aprendizaje inaceptable en el tiempo del PI. |
| D — Python (Edge) + C++ (Microcontrolador) ✅ | Python 3.11 para todos los microservicios del RPi5, C++ (Arduino IDE) para ESP32 | Python donde hay ecosistema maduro, C++ donde es obligatorio (hardware embebido). | El equipo debe mantener dos contextos de lenguaje, pero el C++ está acotado al firmware del microcontrolador. |

### Decisión

**✅ Decisión: Alternativa D — Python 3.11 como lenguaje primario + C++ (Arduino IDE) para el ESP32**

Python es el lenguaje único de toda la capa de software del Raspberry Pi 5: scripts de extracción Starlink, consumer MQTT, backend FastAPI, mocks de desarrollo. C++ (con Arduino IDE y sus librerías) es el lenguaje del microcontrolador ESP32, donde es la única opción viable para acceder al hardware nativo.

### Justificación detallada — Rechazo de Alternativas

**Rechazo de B (Stack Híbrido):** la ganancia de performance de Node.js para la API REST frente a FastAPI (Python) es marginal para el volumen de este proyecto (< 100 requests/hora). El costo de mantener Node.js y Python en paralelo — dos package managers, dos ecosistemas de testing, dos conjuntos de reglas de linting — es desproporcionado.

**Rechazo de C (Golang):** la migración del ecosistema Starlink (grpcio, starlink-grpc-tools) a Go requeriría reimplementar los wrappers Protobuf desde cero. El paper de referencia del testbed internacional menciona explícitamente Python como lenguaje de las herramientas de medición de red. Alejarse de Python introduce riesgo de incompatibilidad con el consorcio.

### Resolución de la Limitación del GIL de Python

El Global Interpreter Lock (GIL) de CPython impide que múltiples hilos Python ejecuten bytecode en paralelo real en el mismo proceso. Esto es un riesgo concreto: si el script de iPerf3 (que puede durar 30 segundos) bloquea el hilo principal, la lectura del sensor o la publicación MQTT se retrasará.

Resolución arquitectónica adoptada:

- Toda operación de I/O de red (ping, iPerf3, grpc) usa asyncio con await. El event loop de Python gestiona la concurrencia de I/O sin bloquear.

- Tareas CPU-intensivas que no pueden ser async se delegan a procesos independientes con multiprocessing.Process(), evitando el GIL por completo (cada proceso tiene su propio intérprete).

- Cada microservicio es un contenedor Docker independiente. El paralelismo real se logra a nivel de proceso del sistema operativo (Linux fork), donde el GIL no es relevante.

# FASE 2 — Simulación (Mocks) y Desarrollo Local

## ADR-06 — Mock de Telemetría Starlink: Generación de Datos Sintéticos

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-06 |
| **Estado** | Propuesto |
| **Depende de** | ADR-01, ADR-04, ADR-05 |
| **Impacta en** | ADR-08, ADR-11, ADR-13 |

### Contexto y Motivación

La antena Starlink física no está disponible[^c7] durante la fase de desarrollo de software. Sin embargo, toda la pila de software (consumer MQTT, bases de datos, dashboards Grafana, backend API) debe ser construida, probada y validada antes de la instalación del hardware real. El mock de telemetría de red es el componente que hace posible este desarrollo desacoplado del hardware.

Un mock trivial (números aleatorios) no sirve para validar la calidad de los dashboards Grafana ni para probar la respuesta del sistema ante condiciones anómalas reales (handovers satelitales, obstrucciones, microcortes). El mock debe simular el comportamiento dinámico[^c8] de una red LEO real para que los gráficos sean analíticamente útiles.

### Marco Teórico

- Ohs et al. (2025) — «PhantomLink: Emulating Virtual End-to-End Links on Ground and in Orbit»: referenciado explícitamente en la propuesta de tesis. Subraya la necesidad de emuladores que respeten el comportamiento físico de los enlaces LEO, incluyendo la variabilidad de latencia durante handovers entre satélites.

- Caminata Aleatoria (Random Walk / Proceso de Wiener Discreto): modelo matemático estándar para simular variaciones con inercia temporal. La latencia de red no salta abruptamente entre valores no correlacionados; varía con continuidad suave, lo que Random Walk captura naturalmente.

- Chaos Engineering (Netflix Simian Army, 2011): metodología de inyección deliberada de fallas en sistemas distribuidos para verificar resiliencia. Aplicado aquí al inyectar eventos de obstrucción y handover satelital programáticamente.

### Alternativas Consideradas

| **Aspecto** | **Alt. A — Replay de CSV histórico** | **Alt. B — Generación aleatoria pura** | **Alt. C — Stateful Mock con Random Walk ✅** |
| --- | --- | --- | --- |
| Realismo temporal | ✅ Alto — datos reales históricos | ❌ Ninguno — ruido blanco sin inercia | ✅ Alto — variaciones graduales con inercia estadística |
| Flexibilidad de testing | ❌ Bajo — limitado al rango del CSV disponible | ⚠️ Medio — cualquier valor, pero irreal | ✅ Muy alto — se pueden configurar perfiles de red (buena, mala, tormenta) |
| Prueba de edge cases | ❌ Solo si el CSV los tiene | ⚠️ Posible pero imposible de controlar | ✅ Inyección determinista de handovers, obstrucciones, caídas |
| Utilidad analítica para Grafana | ✅ Alta si el CSV es denso | ❌ Gráficos de ruido blanco no interpretables | ✅ Gráficos con tendencias, correlaciones y anomalías visibles |
| Requerimiento de datos externos | ❌ Necesita acceso a datasets de red reales del testbed | ✅ Ninguno | ✅ Ninguno — autocontenido |
| Complejidad de implementación | Baja | Muy baja | Media — requiere modelado estadístico |

### Decisión

**✅ Decisión: Alternativa C — Stateful Mock con Random Walk e Inyección de Caos Configurable**

El mock mantiene un estado interno (latencia actual, estado de obstrucción, contador de handover). Genera variaciones graduales con Random Walk. Un perfil de 'caos' configurable vía variable de entorno CHAOS_PROFILE (CALM / STORM / HANDOVER_HEAVY) permite simular distintos escenarios operativos. Publica cada 60 s en MQTT respetando la morfología JSON definida en ADR-01.

### Parámetros estadísticos del modelo

| **Variable** | **Distribución Base** | **Rango Normal** | **Evento de Anomalía** |
| --- | --- | --- | --- |
| latency_ms | Normal(35, 5) ms con Random Walk Δ ∈ [-2.5, +3.0] y reversión suave a la media | 20–80 ms | Handover: spike a 150–400 ms (probabilidad por perfil, ver `CHAOS_PROFILE`) |
| jitter_ms | Exponential(λ=0.5) | 0–15 ms | Handover: jitter 50–100 ms |
| packet_loss_pct | Bernoulli(p=0.005) × 100 | 0–2 % | Obstrucción: 5–40 %; Caída (outage multi-tick): 100 % por 2–5 min |
| throughput_down_bps | Normal(180, 30) Mbps, publicado en bps | 80–300 Mbps | Degradación: 5–50 Mbps durante obstrucción |
| throughput_up_bps | Normal(22, 5) Mbps, publicado en bps | 8–40 Mbps | Degradación: 1–8 Mbps durante obstrucción, correlacionado con down |
| snr_low | Booleano, probabilidad base baja por perfil (reemplaza el random walk de `snr_db`, ADR-17) | Mayormente False | Probabilidad de True sube marcadamente durante obstrucción/handover |
| is_obstructed | Derivado de un estado interno de obstrucción no publicado (`obstruction_pct` uniforme 0–3 % en estado normal) > 10 % | — | TRUE durante evento de obstrucción (3–10 ticks consecutivos, 20–80 % interno) |
| satellite_count | Normal(15, 3), clamp 0–30 | 10–20 | Cae 3–8 satélites durante obstrucción u handover |
| handover_count | 1 si hubo `handover_event` en el tick, 0 si no (ADR-16) | 0 | 1 durante handover — el mock nunca genera más de un evento por tick |
| outage_duration_ms | Uniform(200, 1200) ms si hubo `handover_event`, 0.0 si no (ADR-16, calibrado contra `eventLog` real del relevamiento) | 0.0 | 200–1200 ms durante handover |
| tilt_angle_deg / boresight_azimuth_deg / boresight_elevation_deg | Random walk lento alrededor de un `desired_boresight_*` fijo por nodo (ADR-18) | Desviación mínima en estado normal | Desviación real↔deseada se agranda durante handover/obstrucción (viento simulado) |

> Tabla corregida al vocabulario del DER/`schema.py` (bps en vez de Mbps,
> `is_obstructed`/`snr_low` en vez de `obstruction_pct`/`signal_quality`,
> `satellite_count` agregado) — mismo drift que ya se había corregido en
> `docs/03_SRS.md` §5.1, extendido acá. Refleja la calibración real de
> `src/mock_starlink/mock.py` (`CHAOS_PARAMS`), no solo el mecanismo
> general descrito en la Decisión de este ADR. `snr_low`, `handover_count`,
> `outage_duration_ms` y los campos de alineación agregados por
> ADR-16/17/18 (agosto 2026), reemplazando/extendiendo la fila original de
> `snr_db`. Ver `docs/PROGRESS.md`.

### Pros y Contras

| **Aspecto** | **PRO ✅ / CONTRA ⚠️** | **Detalle** |
| --- | --- | --- |
| **Validación de dashboards** | ✅ PRO | Los gráficos de Grafana muestran tendencias, correlaciones y anomalías reales en lugar de ruido blanco incomprensible. |
| **Prueba de alertas Grafana** | ✅ PRO | Inyectando una obstrucción deliberada (CHAOS_PROFILE=STORM), se puede verificar si las alertas de Grafana se disparan correctamente. |
| **Validación de resiliencia** | ✅ PRO | Simulando una caída total (packet_loss=100% por 5 min) se verifica que el buffer MQTT del broker retiene los mensajes y que la DB recibe todos al reconectar. |
| **Complejidad de implementación** | ⚠️ CONTRA | Requiere diseñar el modelo estadístico y validarlo contra datos reales de Starlink de la literatura. Estimado: 2–3 días de desarrollo. |
| **Precisión vs. realidad** | ⚠️ CONTRA | El modelo no captura todos los efectos físicos de una red LEO real (efecto Doppler, variación de elevación del satélite). Suficiente para validar la arquitectura del sistema. |

## ADR-07 — Mocks de Sensores Ambientales y APIs Externas

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-07 |
| **Estado** | Propuesto |
| **Depende de** | ADR-02, ADR-03, ADR-04, ADR-05 |

### Contexto y Motivación

El sistema integra dos fuentes de datos ambientales: el sensor físico BME280 (lectura local) y APIs meteorológicas externas (Open-Meteo, eventualmente el observatorio de Córdoba). Ninguna de estas fuentes está disponible durante el desarrollo de software. Se necesitan mocks que simulen ambas.

La pregunta arquitectónica central es: ¿deben ser un solo mock unificado, o mocks independientes como microservicios separados?

### Alternativas Consideradas

| **Criterio** | **Alt. A — Mock Unificado (un solo script)** | **Alt. B — Mocks Desacoplados como microservicios Docker ✅** |
| --- | --- | --- |
| Fidelidad arquitectónica | ❌ Un solo proceso simula lo que en producción son 3 microservicios independientes | ✅ Idéntica arquitectura que el sistema real. Los contenedores son reemplazables 1:1 |
| Prueba de resiliencia | ❌ No permite apagar el 'sensor' sin apagar la 'API' | ✅ Se puede detener el mock del BME280 y verificar que el resto sigue operando |
| Prueba de concurrencia | ❌ Los productores no compiten realmente por el broker | ✅ Los contenedores son productores genuinamente concurrentes que compiten por el broker |
| Adherencia a principio SRP | ❌ Un script mezcla responsabilidades de hardware local y API web | ✅ Separación de responsabilidades estricta (SOLID) |
| Complejidad de orquestación | ✅ Un solo servicio en docker-compose.yml | ⚠️ N servicios en docker-compose.yml (manejable con Compose V2) |

### Decisión

**✅ Decisión: Alternativa B — Mocks Desacoplados como Microservicios Docker Independientes**

Cada fuente de datos tiene su propio contenedor: mock_bme280 (simula el ESP32 + sensor), mock_api_ext (simula Open-Meteo). Ambos publican en el broker MQTT respetando la morfología ADR-01. Son reemplazados 1:1 por los servicios reales en la Fase de Producción sin cambios en el consumer ni el broker.

### Modelo de datos sintéticos — Mock BME280

El mock genera datos con realismo físico para el entorno de Córdoba, Argentina:

- Temperatura: ciclo diurno sinusoidal. Mínima nocturna ~10 °C (invierno) / 20 °C (verano); máxima diurna ~25 °C (invierno) / 38 °C (verano). Ruido gaussiano σ = 0.3 °C para simular variabilidad del sensor.

- Humedad relativa: correlacionada inversamente con temperatura (baja de noche cuando baja T; sube de día). Ruido gaussiano σ = 1.5 %.

- Presión atmosférica: deriva lenta Normal(1013.25, 2.0) hPa con variación por frente climático simulado (caída de 5–15 hPa en 6 h).

### Modelo de datos sintéticos — Mock API Externa

- Simula la respuesta JSON de Open-Meteo para la ubicación del LIT (Córdoba, -31.41°, -64.18°).

- Incluye campos adicionales que el sensor local no provee: velocidad y dirección del viento, precipitación acumulada, cobertura de nubes, índice UV.

- El mock introduce ocasionalmente simulación de rate limiting (HTTP 429) y timeout para probar la resiliencia del integrador de APIs.

### Pros y Contras

| **Aspecto** | **PRO ✅ / CONTRA ⚠️** | **Detalle** |
| --- | --- | --- |
| **Prueba de resiliencia** | ✅ PRO | Apagar el mock del BME280 y verificar que el consumer, la DB y Grafana no colapsan (solo dejan de recibir esa fuente). |
| **Prueba de rate limiting** | ✅ PRO | El mock de API externa puede simular HTTP 429, validando que el integrador implementa backoff exponencial correctamente. |
| **Switching mock → hardware** | ✅ PRO | En producción, se detiene el contenedor del mock y se habilita el servicio real. Sin cambios en el consumer ni el broker. |
| **Overhead de Docker** | ⚠️ CONTRA | Dos contenedores adicionales consumen ~50–100 MB RAM extra en la PC de desarrollo. Irrelevante en hardware moderno. |

## ADR-08 — Estrategia de Población de Bases de Datos (Dummy Data)

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-08 |
| **Estado** | Propuesto |
| **Depende de** | ADR-06, ADR-07, ADR-11 |

### Contexto y Motivación

Para que Grafana muestre dashboards analíticamente útiles (con tendencias, correlaciones y rangos temporales amplios), las bases de datos deben contener un volumen significativo de datos históricos. Esperar semanas a que los mocks llenen la DB a 1 msg/min es inviable para el ciclo de desarrollo.

Además, el proceso de población de la DB no debe ser un artefacto de desarrollo desechable; debe validar la integridad de todo el pipeline de ingesta (desde el formato JSON hasta las hypertables de TimescaleDB).

### Alternativas Consideradas

| **Criterio** | **Alt. A — Scripts SQL de Seeding directos (INSERT masivo)** | **Alt. B — Ingesta Orgánica E2E con TIME_WARP_FACTOR ✅** |
| --- | --- | --- |
| Validación del pipeline | ❌ Solo prueba que la tabla existe. No valida el ORM, la deserialización JSON, ni el consumer. | ✅ Valida el flujo completo: MQTT → Consumer → ORM → TimescaleDB. |
| Detección de memory leaks | ❌ No — la inserción SQL directa no usa el código de producción | ✅ Sí — una ejecución larga del consumer expone leaks de memoria y de conexión. |
| Realismo temporal de los datos | ⚠️ Depende de la calidad del SQL generado manualmente | ✅ Los datos tienen la misma distribución estadística que los mocks, garantizando realismo. |
| Velocidad de llenado de la DB | ✅ Muy rápido — se puede insertar 30 días en segundos | ⚠️ Lento si TIME_WARP_FACTOR = 1 (tiempo real). Resuelto con warp > 1. |
| Mantenibilidad | ❌ El SQL manual se desincroniza del esquema si este evoluciona | ✅ Los mocks ya incorporan el esquema actualizado. Sin deuda técnica. |

### Decisión

**✅ Decisión: Alternativa B — Ingesta Orgánica End-to-End con variable TIME_WARP_FACTOR**

Los mocks operan con una variable de entorno TIME_WARP_FACTOR (ej. 60). Un factor de 60 significa que los mocks publican 1 msg/s en lugar de 1 msg/min, generando 1 hora de datos en 1 minuto real. El consumer procesa estos mensajes usando exactamente el mismo código de producción. En 30 minutos se pueden cargar 30 días de historia[^c9] — a razón de 1 msg/min simulado (30 días × 1440 msg/día = 43.200 mensajes), con las 17 columnas numéricas de `network_metrics` (`docs/06_DER.md` §3.1) eso son unos **~9-15 MB sin comprimir** (estimación analítica a partir del ancho de fila real de la tabla, no una medición `du -sh` sobre datos generados — la compresión columnar de ADR-11 activa automáticamente a partir de los 7 días, así que el número final en disco es menor). Medición real todavía pendiente de correr el backfill de verdad (ver Semana 21, sin ejecutar, `docs/PROGRESS.md`).

### Pros y Contras

| **Aspecto** | **PRO ✅ / CONTRA ⚠️** | **Detalle** |
| --- | --- | --- |
| **Validación E2E completa** | ✅ PRO | Prueba que todos los chunks de TimescaleDB se crean correctamente, que los índices funcionan, y que la política de compresión se activa en datos > 7 días. |
| **Prueba de write throughput** | ✅ PRO | Con factor 60, el consumer recibe ~3 msg/s. Un stress test con factor 300 (5 msg/s) valida el rendimiento del sistema bajo carga pico. |
| **Cero deuda técnica** | ✅ PRO | No existen scripts SQL extra que mantener. El código de los mocks es el único generador de datos sintéticos. |
| **Complejidad de temporalidad** | ⚠️ CONTRA | Los timestamps en los mensajes deben ser sintéticos (pasado ajustado), no el tiempo real del sistema. Requiere que el mock genere timestamps calculados hacia atrás.[^c10] Implementado tal cual: `sim_time` arranca en `now - 30 días` cuando `time_warp_factor > 1`, y avanza 60s simulados por cada `interval_s = 60/time_warp_factor` segundos reales, acotado a nunca superar `now` (`src/mock_starlink/mock.py:49,81,228`). |
| **Carga en la RPi5** | ⚠️ CONTRA | Un factor muy alto (> 200[^c11]) puede saturar el CPU del RPi5 — **sin base empírica medida todavía**: no se corrió ningún test de estrés real contra la RPi5 que confirme ese umbral de 200 en particular (el stress test planeado usa `TIME_WARP_FACTOR=3600`, ver Semana 21 de `docs/PROGRESS.md`, sin ejecutar). El número queda como estimación no verificada hasta correr ese test. |

# FASE 3 — Persistencia y Contenerización

## ADR-09 — Selección del Message Broker: MQTT vs. AMQP vs. Redis Pub/Sub

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-09 |
| **Estado** | Propuesto |
| **Impacta en** | ADR-10, ADR-12 |

### Contexto y Motivación

El message broker es la pieza central de la arquitectura orientada a eventos. Su selección determina la resiliencia, el consumo de recursos en el RPi5 (donde RAM y CPU son finitos), la complejidad de configuración y la garantía de entrega de mensajes ante fallos parciales del sistema.

### Marco Teórico

- Luzuriaga et al. — «Performance Evaluation of MQTT and AMQP Protocols in IoT»: demuestra empíricamente que MQTT consume entre un 15–30 % menos de ancho de banda que AMQP para payloads < 2 KB a intervalos > 1 segundo.

- OASIS MQTT v5.0 (Standard, 2019): la versión 5 de MQTT incorpora Session Expiry Interval, Shared Subscriptions, y el campo Reason Code, resolviendo limitaciones históricas de MQTT v3.1.1.

- Redis PERSIST Command: Redis puede configurarse para persistir mensajes en disco (AOF/RDB), pero su modelo Pub/Sub por defecto es fire-and-forget sin persistencia de mensajes para clientes desconectados.

### Comparación de Alternativas

| **Criterio** | **Alt. A — RabbitMQ (AMQP)** | **Alt. B — Eclipse Mosquitto (MQTT) ✅** | **Alt. C — Redis Pub/Sub** |
| --- | --- | --- | --- |
| Consumo de RAM base | ~150–300 MB (runtime Erlang + OTP) | ~5–15 MB (escrito en C, Alpine) | ~50–100 MB (pero Redis también se usa como caché en otros proyectos) |
| Persistencia de mensajes para clientes offline | ✅ Cola persistente en disco por diseño | ✅ QoS 1 + sesión persistente (clean_session=False) | ❌ Por defecto: sin persistencia. Requiere config adicional. |
| Protocolo estándar para IoT | ⚠️ AMQP es estándar enterprise, no IoT específico | ✅ MQTT es el estándar IoT (ISO/IEC 20922) | ❌ No es un broker de mensajería IoT |
| Last Will and Testament (LWT) | ⚠️ Parcialmente (no nativo) | ✅ Función nativa del protocolo MQTT | ❌ No disponible |
| Compatibilidad ESP32 (Arduino) | ❌ No hay librería [^c12]AMQP estable para Arduino | ✅ PubSubClient: librería MQTT nativa para Arduino/ESP32 | ❌ No existe cliente Redis nativo para Arduino |
| Imagen Docker para ARM64 (RPi5) | ✅ Disponible pero pesada | ✅ eclipse-mosquitto:2.0.18 (~22 MB) | ✅ redis:alpine (~30 MB) |
| Curva de aprendizaje | Alta (exchanges, queues, bindings, vhosts) | Baja (topics, QoS, retained messages) | Baja (SUBSCRIBE/PUBLISH), pero diferente a MQTT |

### Decisión

**✅ Decisión: Alternativa B — Eclipse Mosquitto con protocolo MQTT v5.0**

Mosquitto se despliega como contenedor Docker usando la imagen eclipse-mosquitto:2.0.18. Todos los productores (scripts Python y ESP32) usan QoS 1 (at least once). Los consumers usan clean_session=False para recibir mensajes acumulados durante desconexiones. El LWT se configura en cada productor para notificación automática de fallos.

### Funciones Críticas de MQTT utilizadas

| **Función MQTT** | **Propósito en el Sistema** | **Configuración** |
| --- | --- | --- |
| QoS Level 1 (At least once) | Garantiza que ningún mensaje de telemetría se pierde si el consumer o el broker se reinicia transitoriamente. | qos=1 en todos los publish() y subscribe() |
| Persistent Session (clean_session=False) | El broker retiene mensajes no entregados para el consumer cuando este se desconecta y los entrega al reconectar. | client.connect(...) con clean_session=False en el consumer |
| Last Will and Testament (LWT) | Si un productor se cuelga sin desconectarse limpiamente, el broker publica automáticamente un mensaje de alerta en el tópico de estado del sistema, separado por dominio (enmienda 14/08/2026, ver ADR-03/ADR-04). | client.will_set('starlink/status/<node_id>', ...) / client.will_set('meteo/status/<node_id>', ...) |
| Retained Messages | El último valor de métricas clave queda retenido en el broker. Un nuevo suscriptor recibe inmediatamente el estado más reciente sin esperar el próximo ciclo. | retain=True en métricas de estado del sistema |

### Pros y Contras

| **Aspecto** | **PRO ✅ / CONTRA ⚠️** | **Detalle** |
| --- | --- | --- |
| **Peso en el sistema** | ✅ PRO | ~5 MB de imagen Docker, ~5–15 MB de RAM en ejecución. Imperceptible en el RPi5. |
| **Compatibilidad ESP32** | ✅ PRO | La librería PubSubClient para Arduino implementa MQTT v3.1.1 de forma estable. El ESP32 es un productor MQTT de primera clase. |
| **Entrega garantizada ante fallos** | ✅ PRO | QoS 1 + sesión persistente: si la DB cae 5 minutos, los mensajes se acumulan en el broker y se entregan al reconectar. |
| **Aislamiento de la DB respecto al sensor** | ✅ PRO | El ESP32 nunca tiene credenciales SQL. Solo conoce la IP del broker. Principio de Menor Privilegio aplicado. |
| **Sin duplicación garantizada** | ⚠️ CONTRA | QoS 1 garantiza at least once, no exactly once. El consumer DEBE ser idempotente (insertar con ON CONFLICT DO NOTHING) para evitar duplicados si el broker reenvía un mensaje ya procesado. |
| **Autenticación por defecto desactivada** | ⚠️ CONTRA | Mosquitto por defecto acepta conexiones anónimas. En producción se activa autenticación usuario/contraseña vía mosquitto_passwd. Configurable como variable de entorno. |

## ADR-10 — Patrón Database per Service

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-10 |
| **Estado** | Propuesto |
| **Marco teórico** | Richardson — «Microservices Patterns»; Evans — «Domain-Driven Design» |
| **Impacta en** | ADR-11, ADR-12, ADR-13 |

### Contexto y Motivación

El sistema recolecta dos dominios de datos fundamentalmente distintos: telemetría de red (alta importancia para el consorcio internacional, requiere alta disponibilidad de escritura) y datos ambientales (alta importancia para la hipótesis de correlación, tolerante a escrituras diferidas). Si ambos comparten una única base de datos, una operación costosa sobre uno puede impactar al otro.

### Alternativas Consideradas

| **Criterio** | **Alt. A — Base de Datos Monolítica Unificada** | **Alt. B — Database per Service (tres instancias) ** |
| --- | --- | --- |
| Aislamiento de fallos | ❌ Una query costosa en la tabla de clima puede bloquear la inserción de métricas de red | ✅ Un problema en meteo_db no afecta starlink_health_db. Fallo aislado. |
| Control de acceso (RBAC) | ⚠️ Se puede implementar con esquemas y roles SQL, pero en la misma instancia | ✅ Credenciales completamente separadas por base de datos. Principio de Menor Privilegio nativo. |
| Escalabilidad diferencial | ❌ Escalar la DB escala ambos dominios juntos (desperdicio) | ✅ Se puede mover starlink_health_db a un servidor más potente sin mover meteo_db |
| Backups focalizados | ❌ Backup completo de toda la DB aunque solo cambie un dominio | ✅ pg_dump de starlink_health_db de forma independiente y frecuente sin afectar meteo_db |
| JOIN cruzado entre dominios | ✅ Posible con SQL estándar | ❌ No posible a nivel SQL. Se resuelve en la capa de presentación (Grafana Data Blending). |
| Complejidad de despliegue | ✅ Un solo contenedor PostgreSQL | ⚠️ Tres contenedores PostgreSQL. Manejable con Docker Compose. |

### Decisión

**✅ Decisión: Alternativa B — Database per Service. Tres instancias PostgreSQL independientes.**

starlink_health_db (TimescaleDB): métricas de red (latencia, jitter, throughput, packet loss, obstruction). meteo_db (TimescaleDB): datos ambientales (sensor local BME280, APIs externas). **station_config_db (PostgreSQL 16 plano, sin extensión TimescaleDB)**: catálogo de nodos y sensores (`station_metadata`, `sensor_catalog`, docs/06_DER.md §5.1-§5.2) — agregada esta sesión (semana 7), ver nota abajo. Cada instancia tiene sus propias credenciales, volumen Docker y configuración. La correlación entre dominios de series temporales se realiza en Grafana mediante Data Blending (Outer Join by Time).

> **Corrección semana 7 (`docs/PROGRESS.md`):** esta sección decía "dos instancias" y no mencionaba `station_config_db`, pese a que `docs/06_DER.md` §1 ya listaba tres bases de datos (`starlink_health`, `meteo_data`, `station_config`) desde antes de esta sesión — drift entre ADR-10 y el DER, sin nota previa en `docs/PROGRESS.md`, detectado al implementar la validación de coherencia de `node_id` de semana 7. Se resolvió a favor de una tercera instancia porque: (1) el DER ya especificaba su esquema completo (tablas relacionales chicas, sin hypertable, `sin CAGG`), (2) `station_metadata`/`sensor_catalog` no pertenecen exclusivamente a ningún dominio — son metadata de referencia consultada tanto por Starlink (`node_id`) como por el módulo de Fede (`sensor_catalog` referencia BME280) — meterlas en cualquiera de las otras dos violaría el aislamiento de fallos que es la motivación central de este mismo ADR, y (3) no es TimescaleDB: son tablas de catálogo "solo lectura en producción" (docs/06_DER.md §5.1), no series temporales, así que no necesita hypertables/compresión/retención — un PostgreSQL simple alcanza y es más liviano.

### Consecuencias e Implicaciones

- El consumer MQTT (el router de base de datos) analiza el tópico de cada mensaje entrante para decidir a qué base de datos insertar. La lógica es simple: tópicos que empiezan con `starlink/` van a starlink_health_db; tópicos que empiezan con `meteo/` van a meteo_db (implementado en `src/consumer/router.py:ConsumerRouter`, semana 6 — ver `docs/PROGRESS.md`). Corregido de la redacción anterior (`/net_health/`, `/meteo/`), que citaba una nomenclatura de tópicos previa a la corrección de ADR-04 y ya no existía en ningún documento. `station_config_db` no participa del routing MQTT — se consulta directamente (lookup de catálogo), no recibe mensajes.

- Grafana se configura con datasources independientes: starlink_health_db y (cuando exista) meteo_db. Los dashboards de correlación usan el operador de transformación Outer Join by Time para alinear ambas series. `station_config_db` no necesita datasource propio en Grafana por ahora (no hay paneles que la consulten todavía).

- Los scripts de inicialización SQL (init.sql) son separados por base de datos y se ejecutan como parte de la configuración del contenedor Docker (`services/db/init_starlink_health.sql`, `services/db/init_station_config.sql`).

- `network_metrics.node_id` y `sensor_catalog.node_id` referencian `station_metadata.node_id` como FK implícita (no hay FK real entre bases de datos distintas — Postgres no lo permite entre instancias separadas): la coherencia se valida por convención/testing, no por constraint. `sensor_catalog` sí tiene una FK real a `station_metadata` porque ambas viven en `station_config_db`.

- En la migración a nube (Fase 2), las tres bases de datos pueden migrarse independientemente o a servidores distintos, maximizando la flexibilidad operativa.

## ADR-11 — Motor de Base de Datos: InfluxDB vs. PostgreSQL puro vs. PostgreSQL + TimescaleDB

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-11 |
| **Estado** | Propuesto |
| **Marco teórico** | Jensen et al. — «Time-Series Data Management in IoT Applications»; Documentación oficial TimescaleDB |
| **Impacta en** | ADR-10, ADR-12, ADR-13 |

### Contexto y Motivación

Las series temporales tienen características de acceso muy distintas a los datos OLTP tradicionales: se escriben secuencialmente en el tiempo, rara vez se modifican, se consultan principalmente por rango temporal, y se acumulan indefinidamente. Un motor de base de datos no especializado en series temporales degradará su rendimiento de escritura con el crecimiento del volumen de datos, un problema conocido como 'Index Thrashing' o 'Write Amplification'.

La selección del motor impacta directamente en la sostenibilidad del nodo Edge (RPi5) durante meses de operación continua.

### Comparación de Alternativas

| **Criterio** | **Alt. A — InfluxDB 2.x** | **Alt. B — PostgreSQL 16 puro** | **Alt. C — PostgreSQL 16 + TimescaleDB 2.x ✅** |
| --- | --- | --- | --- |
| Lenguaje de consulta | Flux (propio de InfluxDB) o InfluxQL | ANSI SQL estándar | ANSI SQL estándar + funciones TimescaleDB |
| Curva de aprendizaje del equipo | Alta — Flux es un lenguaje funcional con sintaxis propia | Muy baja — SQL es conocido por el equipo | Muy baja — SQL más funciones adicionales opcionales |
| Compatibilidad con Grafana | ✅ Datasource oficial InfluxDB en Grafana | ✅ Datasource PostgreSQL nativo en Grafana | ✅ Datasource PostgreSQL nativo (TimescaleDB es Postgres) |
| Rendimiento de escritura con alto volumen | ✅ Excelente — diseñado nativamente para writes de alta frecuencia | ❌ Index Thrashing con B-Tree al crecer la tabla a millones de filas | ✅ Muy bueno — hypertables particionan automáticamente, writes en chunk más nuevo (siempre pequeño) |
| Consultas relacionales (JOIN con metadatos) | ❌ No soporta JOINs SQL estándar | ✅ JOINs SQL completos | ✅ JOINs SQL completos (es Postgres internamente) |
| Compresión nativa de datos históricos | ✅ Compresión automática configurable | ❌ Sin compresión nativa de series temporales | ✅ Compresión columnar nativa (hasta 90 % de ahorro en disco) |
| Continuous Aggregates (pre-cómputo) | ✅ Tasks automáticas en InfluxDB | ⚠️ Vistas materializadas manuales sin refresco automático | ✅ Continuous Aggregates con política de refresco automático |
| Soporte ARM64 (RPi5) | ✅ Imagen oficial disponible | ✅ Imagen oficial disponible | ✅ timescale/timescaledb:latest-pg16 disponible en ARM64 |

### Decisión

**✅ Decisión: Alternativa C — PostgreSQL 16 + extensión TimescaleDB 2.x**

Recomendación explícita del director del proyecto. TimescaleDB extiende PostgreSQL con hypertables (particionado automático por tiempo), compresión columnar nativa, continuous aggregates con refresco automático y políticas de retención de datos. El equipo usa ANSI SQL estándar sin aprender lenguajes nuevos.

### Gestión del Ciclo de Vida del Dato (ILM)

TimescaleDB provee tres mecanismos que se configuran para gestionar el crecimiento de datos en el disco limitado del RPi5:

| **Mecanismo** | **Configuración Adoptada** | **Efecto Esperado** |
| --- | --- | --- |
| Hypertables (particionado) | chunk_time_interval = 1 día | Cada write cae en el chunk del día actual (siempre pequeño en RAM). Sin Index Thrashing. |
| Continuous Aggregates | Vista horaria de promedios de latencia, jitter, T, HR, P. Refresco automático cada 1 hora. | Grafana consulta la vista materializada (rápida) en lugar de la tabla cruda (lenta) para rangos > 1 día. |
| Compresión columnar nativa | Activada para chunks > 7 días de antigüedad. | Reducción de ~70–90 % del espacio en disco para datos históricos. Datos comprimidos aún consultables. |
| Política de retención (DROP CHUNKS) | Datos crudos con más de 6 meses se eliminan automáticamente. Los continuous aggregates (promedios horarios) se conservan indefinidamente. | El disco no se satura durante la vida del proyecto. El historial analítico se preserva indefinidamente a resolución horaria. |

## ADR-12 — Contenerización con Docker: Bare Metal vs. Docker

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-12 |
| **Estado** | Propuesto |
| **Impacta en** | Todos los ADRs de todas las fases |

### Contexto y Motivación

El proyecto se desarrolla en las PCs personales de los alumnos (Windows/macOS/Linux) y debe desplegarse en un Raspberry Pi 5 ARM64 en el LIT, y eventualmente en un servidor cloud. [^c13]Sin un mecanismo de empaquetado del entorno de ejecución, el síndrome 'Works on my machine' es un riesgo crítico.

Adicionalmente, la directriz explícita del director exige que la migración de entorno local a nube sea transparente, consistiendo idealmente en solo cambiar variables de entorno (IP del servidor, credenciales) sin reescribir código. En ese sentido, todas las apps del proyecto son **stateless a nivel de infraestructura (12-factor)**: ningún contenedor depende de un volumen local persistente para funcionar — pueden reiniciarse o reprogramarse sin coordinación especial porque el estado que importa (las métricas ya generadas) vive en la base de datos, no en el proceso. Esto no contradice que el mock de Starlink sea "stateful" en el sentido de ADR-06 (mantiene en memoria el último valor de latencia para el random walk): es estado transitorio de generación de datos dentro de un proceso reiniciable, no estado de infraestructura del que dependa la migración local→nube.[^c14]

### Alternativas Consideradas

| **Criterio** | **Alt. A — Instalación directa (Bare Metal)** | **Alt. B — Docker + Docker Compose V2 ✅** |
| --- | --- | --- |
| Reproducibilidad entre entornos | ❌ Diferencias sutiles de versión entre PC de desarrollo y RPi5 pueden causar bugs no reproducibles | ✅ La imagen Docker incluye exactamente las mismas versiones de todas las dependencias en todos los entornos |
| Migración local → nube | ❌ Reinstalar manualmente todos los paquetes en el servidor cloud. Alta probabilidad de inconsistencias. | ✅ Copiar docker-compose.yml al servidor cloud + cambiar .env. Un solo comando: docker compose up -d. |
| Aislamiento de procesos | ❌ Un proceso puede corromper las dependencias de otro (conflictos de pip) | ✅ Cada contenedor tiene su propio sistema de archivos y dependencias. Aislamiento absoluto. |
| Auto-recuperación ante cortes de energía | ⚠️ Requiere configurar systemd services manualmente para cada proceso | ✅ restart: unless-stopped en docker-compose.yml. Todo el sistema arranca automáticamente al volver la energía. |
| Límites de recursos (RAM/CPU) | ❌ Un proceso puede consumir toda la RAM del RPi5 (OOM Killer) | ✅ deploy.resources.limits en docker-compose.yml. Postgres limitado a 1 GB RAM máximo. |
| Healthchecks y dependencias ordenadas | ❌ No hay mecanismo nativo para esperar a que Postgres esté listo antes de arrancar el consumer | ✅ healthcheck + condition: service_healthy en docker-compose.yml |
| Overhead de recursos | ✅ Sin overhead de contenedores (~0 MB RAM extra) | ⚠️ Docker daemon consume ~50–100 MB RAM. Aceptable en RPi5 con 8 GB RAM. |

### Decisión

**✅ Decisión: Alternativa B — Docker Engine + Docker Compose V2. Todo contenerizado.**

Cada microservicio tiene su propio Dockerfile. Un único docker-compose.yml orquesta todos los servicios: broker MQTT, dos instancias TimescaleDB (starlink_health_db, meteo_db) + una instancia PostgreSQL plana (station_config_db, ADR-10), consumer router, backend FastAPI, Grafana, mocks. Las imágenes base son slim/alpine para minimizar el tamaño. Las versiones de dependencias están pinneadas (no se usa :latest en producción).

### Pros y Contras

| **Aspecto** | **PRO ✅ / CONTRA ⚠️** | **Detalle** |
| --- | --- | --- |
| **Infraestructura como Código** | ✅ PRO | docker-compose.yml y los Dockerfiles viven en el repositorio Git. El estado completo del sistema es reproducible desde el código. |
| **Migración transparente** | ✅ PRO | Cambiar de localhost a IP cloud requiere editar únicamente el archivo .env. Cero cambios de código. |
| **Red privada Docker interna** | ✅ PRO | Los contenedores se comunican por nombre de servicio (ej. mqtt_broker, timescaledb_net) en una red bridge aislada. Seguridad por defecto. |
| **Reinicio automático** | ✅ PRO | restart: unless-stopped asegura que todo el sistema vuelve a operar automáticamente tras un corte de energía en el LIT. |
| **Límites de RAM para Postgres** | ✅ PRO | deploy.resources.limits.memory: 1g previene que TimescaleDB consuma toda la RAM del RPi5 bajo carga pesada. |
| **Complejidad de networking en Docker** | ⚠️ CONTRA | La comunicación entre el ESP32 (fuera de Docker) y el broker (dentro de Docker) requiere que el puerto 1883 esté mapeado al host (ports: '1883:1883'). Documentado explícitamente en el README. |
| **Imágenes ARM64 para todos los servicios** | ⚠️ CONTRA | En PC de desarrollo (x86_64), las imágenes son las estándar. En el RPi5 (ARM64) deben ser versiones ARM. Las imágenes oficiales de Mosquitto, TimescaleDB y Grafana soportan multi-arch; se verifica con docker buildx inspect. |

# FASE 4 — Observabilidad y Monitoreo Proactivo

## ADR-13 — Plataforma de Visualización: Frontend Propio vs. Grafana

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-13 |
| **Estado** | Propuesto |
| **Impacta en** | ADR-14, ADR-15 |

### Contexto y Motivación

Una plataforma de visualización convierte los millones de filas de TimescaleDB en conocimiento accionable. La selección de esta capa impacta directamente en cuánto tiempo el equipo puede dedicar a la investigación en lugar de al desarrollo de frontend, y en la calidad de los dashboards para la presentación del PI.

### Alternativas Consideradas

| **Criterio** | **Alt. A — Frontend React/Vue a medida** | **Alt. B — Grafana OSS ✅** |
| --- | --- | --- |
| Tiempo de desarrollo hasta primer dashboard funcional | Semanas — requiere diseño UI, API REST, estado global, gráficos con D3/Recharts | Horas — datasource PostgreSQL + panel TimeSeries preconstruido |
| Soporte nativo para TimescaleDB | ❌ Requiere API REST intermediaria que consulte la DB | ✅ Datasource PostgreSQL nativo. Macros $__timeFilter(), $__interval automáticos |
| Sistema de alertas integrado | ❌ Requiere implementar alertas desde cero | ✅ Alertmanager integrado con webhooks, email y bots de mensajería |
| Dashboards como código (exportación JSON) | ❌ El estado de la UI no es versionable fácilmente | ✅ Cada dashboard se exporta como JSON versionable en Git |
| Aprovisionamiento automático al arrancar | ❌ Requiere script de setup manual o API de la app | ✅ Grafana provee directorio /etc/grafana/provisioning/ para cargar datasources y dashboards automáticamente |
| Costo de desarrollo acorde al PI | ❌ Desproporcionado. El PI evalúa redes satelitales, no UI/UX web. | ✅ Proporcional. El PI es de ingeniería de redes e IoT. |

### Decisión

**✅ Decisión: Alternativa B — Grafana OSS LTS**

Grafana se despliega como contenedor Docker con aprovisionamiento automático: los datasources (starlink_health_db y meteo_db) y los dashboards iniciales se cargan desde archivos JSON en el directorio de provisioning al arrancar el contenedor. Los dashboards se versionan en Git junto al código del proyecto.

### Taxonomía de Dashboards

| **Dashboard** | **Tipo de Paneles** | **Propósito** |
| --- | --- | --- |
| Estado del Sistema (NOC) | Stat panels (semáforos verde/rojo), Gauge de disco, Tabla de última actualización por servicio | Vista instantánea de la salud operativa de la estación. Primer dashboard que abre el operador al comenzar una sesión. |
| Red Starlink | Time Series (latencia, jitter, packet loss, throughput). Histograma de distribución de latencia. | Análisis del comportamiento de la red Starlink a lo largo del tiempo. Permite identificar períodos de degradación. |
| Datos Ambientales | Time Series superpuestos: sensor BME280 (color 1) vs. API externa (color 2) para T, HR y P. Barra de precipitación. | Comparación entre medición local y pronóstico/reporte de API externa. Valida la precisión del sensor BME280. |
| Correlación Red-Clima | Gráfico de doble eje Y: latencia Starlink (eje izquierdo, ms) vs. temperatura/humedad/presión (eje derecho). Scatter plot latencia vs. temperatura. | El panel científico central de la tesis. Permite visualizar heurísticamente si las variaciones de clima coinciden temporalmente con variaciones de desempeño de red. |
| Análisis Histórico | Continuous Aggregates: promedios horarios de latencia, throughput y temperatura en rangos de 1–6 meses. Heatmap diario de latencia. | Análisis de tendencias de largo plazo. Queries sobre la vista materializada de TimescaleDB para máxima performance. |

### Sistema de Alertas en Grafana

Grafana se configura con las siguientes reglas de alerta automáticas:

- Latencia > 200 ms sostenida por 5 minutos → alerta de degradación de red.

- Packet loss > 5 % por 3 minutos consecutivos → alerta de posible obstrucción física.

- Ausencia de datos en cualquier tópico por más de 10 minutos → alerta de servicio caído.

- Disco del host > 80 % → alerta de capacidad de almacenamiento.

Las alertas se envían a un webhook de Discord o Telegram configurado en el Contact Point de Grafana. Esto transforma la estación de un registro pasivo de datos en un centinela activo.

## ADR-14 — Postura de Seguridad y Exposición de Puertos en Docker

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-14 |
| **Estado** | Propuesto |
| **Principio** | Defense in Depth — Principio de Menor Privilegio — Zero Trust (local) |

### Contexto y Motivación

El RPi5 estará conectado a la red del LIT (intranet universitaria) y potencialmente tendrá acceso desde internet para el acceso remoto del equipo de investigación. La exposición innecesaria de puertos de bases de datos o del broker MQTT a la red externa es un riesgo de seguridad inaceptable.

### Política de Exposición de Puertos

| **Servicio** | **Puerto interno** | **Exposición externa** | **Justificación** |
| --- | --- | --- | --- |
| TimescaleDB starlink_health_db | 5432 | ❌ NO expuesto (sin ports en compose) | Solo el consumer y Grafana (dentro de la red Docker) necesitan acceder. Nunca accesible desde la intranet o internet. |
| TimescaleDB meteo_db | 5433 | ❌ NO expuesto (sin ports en compose) | Idem. Acceso exclusivo desde dentro de la red Docker. |
| MQTT Broker (Mosquitto) | 1883 | ⚠️ Expuesto SOLO en la intranet del LIT | El ESP32 (fuera de Docker) necesita conectarse al broker. Expuesto al host del RPi5, no a internet. |
| Backend FastAPI | 8000 | ⚠️ Expuesto a la intranet del LIT | Acceso para integración y consultas ad-hoc del equipo de investigación desde la red local. |
| Grafana | 3000 | ✅ Expuesto públicamente (con autenticación) | Interfaz de visualización. Requiere usuario y contraseña. El usuario admin por defecto se cambia en el primer despliegue. |

### Medidas de Seguridad Adicionales

- Grafana: autenticación obligatoria (usuario/contraseña). El usuario admin se reemplaza en el primer despliegue. Se desactiva la opción allow_sign_up para evitar auto-registro de usuarios.

- MQTT Broker: autenticación por usuario/contraseña activada mediante mosquitto_passwd. Las credenciales se inyectan como secretos Docker (no hardcodeadas en docker-compose.yml).

- Variables de entorno y secretos: todas las credenciales (contraseñas de DB, API keys externas) se gestionan mediante archivo .env excluido del control de versiones (.gitignore). En producción cloud, se usan Docker Secrets o el sistema de secretos del proveedor cloud.

- Acceso remoto SSH: autenticación exclusiva por clave pública. Autenticación por contraseña desactivada en sshd_config (PasswordAuthentication no).

- Resolución DNS interna Docker: Grafana apunta a los contenedores de DB por nombre de servicio (ej. timescaledb_net:5432), no por IP. No hay IPs hardcodeadas en ninguna configuración.

### Mecanismo concreto de filtrado de IP (Semana 15-16)

`CLAUDE.md` §4 resume ADR-14 como "Zero Trust local: solo puerto Grafana expuesto externamente **+ filtrado de IP**", pero hasta esta sesión el ADR nunca especificaba *cómo* — la tabla de arriba dice "✅ Expuesto públicamente (con autenticación)" sin mecanismo de filtrado. Se cierra ese punto abierto:

**Etapa 1 (on-premises, RPi5 en el LIT):** filtrado a nivel de firewall del host, no en `docker-compose.yml` (Docker no filtra por IP de origen sin plugins adicionales). `ufw`/`iptables` en la RPi5 restringe el puerto 3000 a: la subred de la intranet del LIT (acceso del equipo desde dentro del laboratorio) + IPs puntuales del director/co-director si necesitan acceso remoto puntual. Ejemplo de regla (documentado, no ejecutado — requiere acceso a la RPi5 real, ver `docs/PROGRESS.md` §Semana 10):

```bash
sudo ufw allow from <subred-LIT>/24 to any port 3000 proto tcp
sudo ufw allow from <IP-director> to any port 3000 proto tcp
sudo ufw deny 3000/tcp   # regla de default-deny, después de los allow puntuales
```

**Etapa 2 (cloud):** el filtrado pasa al security group / firewall del proveedor cloud (mismo mecanismo, distinta herramienta) — no cambia el principio, solo dónde se aplica la regla, consistente con el plan de migración de `CLAUDE.md` §6 ("solo cambian `DB_HOST`/`MQTT_HOST` en `.env`", acá también cambia dónde vive la regla de firewall, no el diseño).

Es una medida operativa (configuración del host/red), no algo que `docker-compose.yml` pueda expresar — por eso no hay cambio de código correspondiente, solo esta documentación y la referencia en `README.md`.

## ADR-15 — Mock de Videomonitoreo: Placeholder Estático vs. Streaming MJPEG Activo

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-15 |
| **Estado** | Propuesto |
| **Impacta en** | ADR-12, ADR-13 |
| **Nota** | Objetivo secundario del PI. Se implementa si el tiempo lo permite después de completar los objetivos primarios. |

### Contexto y Motivación

La propuesta del PI incluye video monitoreo de la antena para detectar obstrucciones físicas (acumulación de nieve, ramas, aves). La cámara física (COTS) no está disponible en la fase de mocks. Se necesita un mock de stream de video que permita integrar y validar el panel de videomonitoreo en Grafana antes de contar con el hardware.

### Alternativas Consideradas

| **Criterio** | **Alt. A — Imagen JPG estática (placeholder)** | **Alt. B — Microservicio Flask con stream MJPEG a 5 FPS ✅** |
| --- | --- | --- |
| Validación del panel Grafana | ⚠️ Solo valida que el panel renderiza HTML. No valida streaming real. | ✅ Valida que Grafana puede consumir un stream de video continuo sin afectar los otros paneles. |
| Stress test del frontend | ❌ No genera carga de red continua | ✅ El stream continuo permite medir si el ancho de banda del video afecta las mediciones de red de Starlink. |
| Fidelidad con el sistema real | ❌ Muy baja — una cámara IP real no es una imagen estática | ✅ Alta — MJPEG es el protocolo estándar de cámaras IP. El panel de Grafana no cambia al conectar la cámara real. |
| Impacto en recursos del sistema | ✅ Nulo — una imagen JPG no consume CPU/RAM | ⚠️ El servidor MJPEG consume CPU para la codificación de frames y ancho de banda LAN. Mitigado con 5 FPS y JPEG quality 50. |
| Complejidad de implementación | Muy baja | Media — ~50 líneas de Python con Flask + OpenCV |

### Decisión

**✅ Decisión: Alternativa B — Microservicio Flask con stream MJPEG a 5 FPS controlados**

Un contenedor Docker independiente corre un servidor Flask que lee un video MP4 de muestra en loop infinito y lo transmite como stream MJPEG en /video_feed. Limitado a 5 FPS y JPEG quality 50 para minimizar el impacto en el ancho de banda medido de Starlink. El panel de Grafana consume este stream vía iframe HTML.

### Justificación de la limitación a 5 FPS

El ancho de banda consumido por el stream de video impacta directamente en las mediciones de throughput de Starlink que el sistema intenta medir. Si el stream consume 5 Mbps de ancho de banda, el script de medición de throughput verá 5 Mbps menos de lo real.

A 5 FPS con JPEG quality 50 y resolución 720p, el stream consume aproximadamente 200–400 kbps, lo cual es menor al 0.2 % del ancho de banda típico de Starlink (~180 Mbps). Este nivel es estadísticamente despreciable para las mediciones de red.

### Ruta de reemplazo por cámara real

- En producción (Fase de hardware real), el contenedor del mock de video se detiene.

- Se configura la cámara IP COTS con soporte RTSP o MJPEG.

- El panel de Grafana apunta a la nueva URL de stream (RTSP/MJPEG de la cámara real).

- No se requieren cambios en ningún otro componente del sistema.

## ADR-16 — Exposición de Eventos de Handover Satelital en el Esquema de Telemetría

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-16 |
| **Estado** | Propuesto |
| **Fecha** | Agosto 2026 |
| **Depende de** | ADR-01, ADR-06 |
| **Impacta en** | ADR-08, ADR-11, ADR-13 |

### Contexto y Motivación

El relevamiento contra la antena real del LIT (sesión de laboratorio del 04/08/2026, detalle completo en `docs/PROGRESS.md` §Semana 10) confirmó que el gRPC de la terminal expone un indicador explícito y oficial de cambio de satélite/haz: `get_history.dishGetHistory.outages[].didSwitch` (booleano por corte), acompañado de `eventLog.events[].reason` con categorías de causa (`EVENT_REASON_OUTAGE_NO_PINGS`, `EVENT_REASON_OUTAGE_NO_DOWNLINK`, etc.) y duración en nanosegundos.

El mock ya modela esto internamente: `StarlinkMockAgent.generate_payload()` (`src/mock_starlink/mock.py`) calcula un `handover_event` booleano por tick (`CHAOS_PARAMS`, ADR-06) que usa para inflar `latency_ms`/`jitter_ms` y degradar `satellite_count` — pero nunca lo expone como campo propio del payload. Sin un campo dedicado, Grafana solo puede *inferir* handovers heurísticamente a partir de picos de latencia/jitter, lo cual es ambiguo (una tormenta u obstrucción puede producir el mismo patrón visual, ADR-06 §Parámetros estadísticos) y no permite un panel de eventos confiable. El director del PI pidió explícitamente poder exponer esta información en el dashboard de Grafana.

Nota de alcance: este ADR resuelve únicamente la exposición del *efecto observable* del handover (ocurrencia + duración del corte asociado). No expone identidad de satélite/beam — la API no lo provee, y hacerlo caería en ingeniería inversa de mecanismos internos propietarios de Starlink, marcado fuera de alcance en CLAUDE.md §1.1.

### Alternativas Consideradas

| **Aspecto** | **Alt. A — Booleano `is_handover`** | **Alt. B — Conteo + duración agregados ✅** |
| --- | --- | --- |
| Fidelidad a la señal real de la API | ⚠️ Colapsa a un solo bit por medición; si hay más de un `outage` con `didSwitch=true` en la ventana de polling (60 s), se pierde esa multiplicidad | ✅ `handover_count` conserva cuántos hubo; `outage_duration_ms` conserva el impacto agregado en tiempo de corte |
| Complejidad del extractor real | ✅ Trivial: `any(o.didSwitch for o in outages_en_la_ventana)` | ⚠️ Requiere que el extractor lleve estado (timestamp del último poll) para filtrar `outages`/`eventLog` por ventana y sumarizar — primer caso de estado explícito entre polls en el extractor (`get_status` es stateless por diseño) |
| Equivalencia con el mock | ✅ Directa — el mock ya tiene `handover_event` booleano por tick | ✅ También directa — un tick del mock nunca genera más de un evento, así que `handover_count` cae naturalmente en {0, 1} sin cambiar el modelo de generación |
| Utilidad analítica en Grafana | ⚠️ Solo permite un marcador binario superpuesto (como ya hace el panel 4 con `is_obstructed`) | ✅ Permite un panel de barras "handovers por hora" (`SUM(handover_count)` vía continuous aggregate) y correlacionar la duración real del corte con el impacto en `packet_loss_pct`/`latency_ms` — más rico para el objetivo de correlación del PI (CLAUDE.md §1) |
| Costo de esquema (DB/DER) | ✅ Una columna `BOOLEAN` | ⚠️ Dos columnas (`SMALLINT` + `FLOAT8`), mismo orden de magnitud que el resto de `network_metrics` |

### Decisión

**✅ Decisión: Alternativa B — Campos agregados `handover_count` y `outage_duration_ms`**

Se agregan dos campos nuevos a `metrics` (`StarlinkPayloadIn`, ADR-01):

- **`handover_count`** (integer / null): cantidad de eventos de handover (`didSwitch=true`) detectados desde la medición anterior.
- **`outage_duration_ms`** (float / null): milisegundos totales de corte asociados a esos eventos, en el mismo intervalo.

**Semántica NULL vs. cero** (mismo patrón que el resto de `metrics`, ADR-01/DER): `NULL` significa que la medición no está disponible (falló la consulta a `get_history`); `0` es el valor normal cuando no hubo ningún handover en el intervalo. `0` **no** es "sin dato" — es exactamente lo que reportan la mayoría de los ciclos de medición.

### Derivación en el extractor real

`get_history.dishGetHistory.outages[]` trae `cause`, `startTimestampNs`, `durationNs`, `didSwitch` por corte. En cada poll (cada 60 s por defecto), el extractor filtra los `outages` con `startTimestampNs` posterior al timestamp del poll anterior y `didSwitch=true`; `handover_count` es la cantidad de esos, `outage_duration_ms` es la suma de sus `durationNs` convertida a milisegundos. Requiere que el extractor guarde el timestamp del último poll entre invocaciones — alcance de implementación de la Semana 10 (`src/acquisition/`, todavía no escrito), no de este ADR.

### Derivación en el mock

`StarlinkMockAgent` ya calcula `handover_event` por tick. Se expone como:
`handover_count = 1 if handover_event else 0`;
`outage_duration_ms = uniform(200, 1200) if handover_event else 0.0` — rango calibrado contra las duraciones reales observadas en el relevamiento del lab (`eventLog` real: cortes de ~220 ms a ~1180 ms), no un valor inventado.

### Pros y Contras

| **Aspecto** | **PRO ✅ / CONTRA ⚠️** | **Detalle** |
| --- | --- | --- |
| **Panel dedicado en Grafana** | ✅ PRO | Permite un panel de eventos de handover independiente del de latencia/jitter, sin depender de heurísticas de picos. |
| **Correlación cuantitativa** | ✅ PRO | `outage_duration_ms` da una medida directa del costo real del handover en tiempo de corte, no solo su ocurrencia. |
| **Calibración de ADR-06** | ✅ PRO | Los rangos observados en la antena real (`didSwitch`/`eventLog`) sirven de referencia concreta para calibrar `CHAOS_PROFILE: HANDOVER_HEAVY`, en vez de parámetros elegidos a ciegas. |
| **Estado entre polls en el extractor real** | ⚠️ CONTRA | Es la primera vez que el extractor necesita memoria entre invocaciones (timestamp del último poll). Mitigado: alcance acotado a esta única responsabilidad, no cambia el resto del diseño stateless de `get_status`. |
| **Dos columnas nuevas en `network_metrics`** | ⚠️ CONTRA | Hypertable ya en producción eventualmente — agregar columnas es seguro (no requiere migración destructiva, ver nota de `docs/06_DER.md` §3.1), pero sigue siendo cambio de esquema compartido con el consumer de Fede. |

## ADR-17 — Reemplazo de `snr_db` por `snr_low`: SNR Numérico No Disponible en Firmware Real

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-17 |
| **Estado** | Propuesto |
| **Fecha** | Agosto 2026 |
| **Depende de** | ADR-01 |
| **Impacta en** | ADR-06, ADR-11, ADR-13 |

### Contexto y Motivación

`StarlinkMetrics.snr_db` (`src/mock_starlink/schema.py`) se definió en Semana 1 como float
en decibelios, asumiendo que el gRPC de la terminal expone un SNR numérico — supuesto
razonable en ese momento (firmwares antiguos de Starlink sí lo exponían, y así lo
documentaba la referencia de la comunidad `starlink-grpc-tools`), pero nunca verificado
contra hardware real hasta ahora.

El relevamiento del 04/08/2026 (`docs/PROGRESS.md` §Semana 10, antena con `apiVersion: 42`,
software `2026.07.19.mr82648`) confirmó que el `get_status` real **no expone ningún campo
numérico de SNR**. En su lugar, `dishGetStatus` trae dos booleanos: `isSnrAboveNoiseFloor`
e `isSnrPersistentlyLow`. Esto rompe directamente la exigencia de ADR-01/`CLAUDE.md` §1.1 de
que el mock y el hardware real sean intercambiables 1:1 (mismo tópico, misma morfología de
paquete): el mock puede seguir generando un `snr_db` sintético indefinidamente, pero el
extractor real jamás tendría de dónde sacar ese valor.

### Alternativas Consideradas

| **Aspecto** | **Alt. A — Mantener `snr_db` nullable, real siempre `null`** | **Alt. B — `snr_low: bool` ✅** | **Alt. C — Ambos booleanos (`snr_low` + `snr_above_floor`)** |
| --- | --- | --- | --- |
| Fidelidad a la API real | ⚠️ El campo existe en el esquema pero es un valor sintético que el hardware real no puede producir jamás — no es "a veces null", es "siempre null en producción" | ✅ Mapea 1:1 con `isSnrPersistentlyLow`, campo real y estable del firmware actual | ✅ También mapea 1:1, con ambos indicadores |
| Cumple ADR-01 (equivalencia mock↔real) | ⚠️ Viola la equivalencia: el mock produce algo que el real nunca producirá | ✅ Mock y real generan/mapean el mismo campo | ✅ Igual que B |
| Utilidad analítica adicional | — | — | ⚠️ `isSnrAboveNoiseFloor` es casi redundante con lo que ya capturan `packet_loss_pct`/`is_obstructed` ante un corte total de señal — no aporta una señal nueva relevante para Grafana |
| Simplicidad del esquema | ✅ Sin cambios | ✅ Un campo booleano, mismo nivel de simplicidad que `is_obstructed` | ⚠️ Dos campos booleanos con solape conceptual, sin justificar el costo extra |
| Costo de migración (schema/DER/mock/tests) | ✅ Ninguno | ⚠️ Cambio de tipo incompatible: requiere bump de `SCHEMA_VERSION` (1.0→1.1) | ⚠️ Igual que B, más un campo extra sin ganancia clara |

### Decisión

**✅ Decisión: Alternativa B — Reemplazar `snr_db: Optional[float]` por `snr_low: Optional[bool]`**

`snr_low` mapea directamente `isSnrPersistentlyLow` del `get_status` real. `True` indica
señal persistentemente baja (degradación sostenida, no un pico transitorio). Se descarta
modelar también `isSnrAboveNoiseFloor` (Alt. C) por su solape con `packet_loss_pct`/
`is_obstructed` — un campo booleano alcanza y mantiene el esquema simple, consistente con
el criterio ya aplicado en ADR-16 (preferir el mínimo de campos que capture la señal real
sin redundancia).

**Cambio de tipo incompatible → bump de `SCHEMA_VERSION` a `1.1`.** A diferencia de ADR-16
(agregar campos nuevos es compatible hacia atrás, un consumer viejo simplemente los
ignora), reemplazar un `float` por un `bool` en el mismo nombre de campo no lo es — un
consumer que todavía espera `snr_db` numérico rompería de forma confusa ante un booleano.
`StarlinkPayloadIn.check_schema_version` debe rechazar explícitamente `"1.0"` a partir de
esta versión, en vez de fallar silenciosamente aguas abajo.

**Semántica NULL**: igual que el resto de `metrics` — `NULL` si `get_status` no fue
accesible; en el mock, `snr_low` es siempre no-nulo (el mock nunca modela "falla al leer la
API interna" como escenario de caos separado, ver ADR-06).

### Derivación en el extractor real

`not dishGetStatus.isSnrAboveNoiseFloor` — ver hallazgo de campo abajo. (La decisión
original de este ADR asumía mapeo directo desde `isSnrPersistentlyLow`; corregido.)

### Derivación en el mock

`StarlinkMockAgent` reemplaza el random walk gaussiano de `snr_db` por una probabilidad de
`snr_low=True` calibrada por `CHAOS_PROFILE` (sube durante obstrucción/handover, igual que
antes degradaba el valor numérico) — ver tabla `CHAOS_PARAMS` actualizada en el docstring de
`src/mock_starlink/mock.py`.

### Hallazgo de campo (12/08/2026) — `isSnrPersistentlyLow` no existe en el firmware real

La Decisión de este ADR (arriba) eligió mapear `snr_low` directo desde `isSnrPersistentlyLow`
y descartó `isSnrAboveNoiseFloor` (Alt. C) por redundancia — basado en el relevamiento del
04/08/2026, que reportaba ambos booleanos presentes en `dishGetStatus`. En la sesión
presencial del 12/08/2026 en el LIT, `grpcurl` contra la antena real (mismo hardware,
`softwareVersion 2026.07.27.mr83192.1`) mostró que **`isSnrPersistentlyLow` no está presente
en la respuesta real** — solo `isSnrAboveNoiseFloor`. El relevamiento del 04/08 estaba
equivocado en ese punto específico (posible confusión con la documentación de la comunidad
`starlink-grpc-tools`, que sí lista `isSnrPersistentlyLow` para otras variantes de firmware).

Corregido en `src/acquisition/starlink_extractor.py` y `src/mock_starlink/schema.py`:
`snr_low = not isSnrAboveNoiseFloor` (inversión semántica — `isSnrAboveNoiseFloor=true`
significa señal buena). No cambia la Alternativa elegida (sigue siendo un único booleano,
Alt. B) ni el `SCHEMA_VERSION` — solo el campo gRPC de origen.

### Pros y Contras

| **Aspecto** | **PRO ✅ / CONTRA ⚠️** | **Detalle** |
| --- | --- | --- |
| **Equivalencia mock↔real restaurada** | ✅ PRO | Es exactamente la garantía que ADR-01/`CLAUDE.md` §1.1 exige y que `snr_db` float rompía en silencio. |
| **Pérdida de granularidad** | ⚠️ CONTRA | Se pierde la escala continua en dB que tenía el mock — pero era sintética, nunca reflejó una medición real posible. |
| **Panel de Grafana a rehacer** | ⚠️ CONTRA | El panel de obstrucción que hoy no grafica `snr_db` como serie separada pasa a superponer `snr_low` como marcador 0/1, igual patrón que `is_obstructed`. |
| **Bump de `SCHEMA_VERSION`** | ⚠️ CONTRA (mitigado) | Único cambio de versión de esquema hasta ahora — documentado como el primer caso real de incompatibilidad, valida que el mecanismo de `check_schema_version` funciona como se diseñó. |

## ADR-18 — Exposición de `alignmentStats`: Orientación Física de la Antena en el Esquema de Telemetría

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-18 |
| **Estado** | Propuesto |
| **Fecha** | Agosto 2026 |
| **Depende de** | ADR-01 |
| **Impacta en** | ADR-06, ADR-11, ADR-13 |

### Contexto y Motivación

Durante el relevamiento del 04/08/2026, el director pidió explícitamente evaluar exponer en
Grafana los datos de `dishGetStatus.alignmentStats` (ya capturados sin usar en
`get_status_full.json`, ver `docs/PROGRESS.md` §Semana 10): `tiltAngleDeg`,
`boresightAzimuthDeg`, `boresightElevationDeg`, `attitudeEstimationState`,
`attitudeUncertaintyDeg`, `desiredBoresightAzimuthDeg`, `desiredBoresightElevationDeg`.

Encaja directamente con el objetivo central del proyecto (`CLAUDE.md` §1): correlacionar
clima/entorno físico con performance de red. La desviación entre posición real
(`boresightAzimuthDeg`/`boresightElevationDeg`) y objetivo
(`desiredBoresightAzimuthDeg`/`desiredBoresightElevationDeg`), o un `tiltAngleDeg` que se
corre con el viento, es un correlato físico-ambiental directo (ej. viento fuerte
desalineando la antena → picos de latencia) — no es scope creep, es una instancia concreta
del objetivo del PI, no una funcionalidad nueva sin relación.

### Alternativas Consideradas

| **Aspecto** | **Alt. A — Sub-objeto `alignment` anidado** | **Alt. B — Campos planos en `metrics` ✅** | **Alt. C — No implementar (fuera de alcance)** |
| --- | --- | --- | --- |
| Consistencia con `network_metrics` (DER) | ⚠️ La hypertable es plana por naturaleza (columnas SQL) — un sub-objeto en el payload obliga al consumer a aplanarlo igual antes del INSERT, sin ninguna ganancia | ✅ Mapeo directo payload→columna, mismo patrón que el resto de `metrics` | — |
| Costo de implementación | ⚠️ Requiere lógica de aplanado extra en `src/consumer/db.py` | ✅ Ninguno adicional sobre lo que ya hace `NetHealthDB.insert` | ✅ Ninguno |
| Valor para el objetivo del PI | ✅ | ✅ | ⚠️ Descarta un correlato físico-ambiental directo pedido explícitamente por el director |
| Separación de ciclos de vida (payload) | ✅ Aísla campos "experimentales" del resto de `metrics`, similar al argumento de ADR-01 para separar envelope de `metrics` | ⚠️ Mezclados con el resto de campos de red — pero `metrics` ya es "todo lo que sabe la antena sobre sí misma", no solo red pura (ej. `is_obstructed` tampoco es una métrica de red) | — |

### Decisión

**✅ Decisión: Alternativa B — Campos planos en `metrics`, sin sub-objeto anidado**

Se agregan seis campos opcionales a `StarlinkMetrics`:

- `tilt_angle_deg`, `boresight_azimuth_deg`, `boresight_elevation_deg`,
  `desired_boresight_azimuth_deg`, `desired_boresight_elevation_deg`,
  `attitude_uncertainty_deg` (todos `float`, grados).

**Se descarta `attitudeEstimationState`** (enum string de estado del algoritmo de
estimación de actitud, ej. `ATTITUDE_ESTIMATION_STATE_STABLE`): no tiene uso analítico
directo para el objetivo de correlación del PI — es metadato interno del algoritmo de
alineación, no una medida física correlacionable con clima. Queda registrado como
alternativa rechazada (Apéndice B) para no volver a evaluarlo sin justificación nueva.

**Límite de alcance explícito** (mismo criterio que ADR-16): se expone la orientación física
observable de la antena, información oficial de la API. No se intenta inferir mecanismos
internos del algoritmo de tracking — seguiría fuera de alcance de `CLAUDE.md` §1.1.

### Derivación en el extractor real

`dishGetStatus.alignmentStats.{tiltAngleDeg, boresightAzimuthDeg, boresightElevationDeg,
desiredBoresightAzimuthDeg, desiredBoresightElevationDeg, attitudeUncertaintyDeg}`,
directos, sin transformar.

### Derivación en el mock

`StarlinkMockAgent` modela un random walk lento para `boresight_azimuth/elevation_deg`
alrededor de un `desired_boresight_*` fijo por nodo, con la desviación agrandándose durante
`handover_event`/obstrucción (viento/movimiento físico simulado) — ver `CHAOS_PARAMS`
actualizado en `src/mock_starlink/mock.py`.

### Hallazgo de campo (12/08/2026) — corrección de rango de `boresightAzimuthDeg`

La decisión original de este ADR (agosto 2026, relevamiento del 04/08) asumía convención de
brújula (0-360, no signado) para `boresight_azimuth_deg`/`desired_boresight_azimuth_deg`, sin
haberla validado todavía contra la antena real. En la sesión presencial del 12/08/2026 en el
LIT, `grpcurl` contra `dishGetStatus` real devolvió valores como `boresightAzimuthDeg:
-179.98016` — el firmware usa rango firmado (-180..180), no brújula 0-360. La convención
0-360 nunca fue correcta, era una suposición sin validar que rompía la validación Pydantic en
cada poll con azimuth negativo (esencialmente siempre, dado que el apuntamiento observado
oscila cerca del límite ±180).

Corregido en `src/mock_starlink/schema.py` (`ge=-180, le=180`), `docs/06_DER.md` (CHECK
constraint y `services/db/init_starlink_health.sql`), y `docs/07_API_REST.md`. El mock
(`src/mock_starlink/mock.py`) también se ajustó para generar valores en el rango correcto. Sin
impacto en `SCHEMA_VERSION` (el tipo del campo no cambia, solo su rango válido).

### Pros y Contras

| **Aspecto** | **PRO ✅ / CONTRA ⚠️** | **Detalle** |
| --- | --- | --- |
| **Correlato físico-ambiental directo** | ✅ PRO | Pedido explícito del director, encaja con el objetivo central del PI sin expandir su alcance. |
| **Panel nuevo en Grafana** | ✅ PRO | Tilt/azimuth/elevación vs. tiempo, con overlay de desviación real vs. deseada — insumo directo para la campaña de medición de Semana 22. |
| **Seis columnas nuevas en `network_metrics`** | ⚠️ CONTRA | Mismo criterio de ADR-16: agregar columnas a una hypertable es seguro (no requiere migración destructiva), pero es el ADR con más columnas nuevas de una sola vez del proyecto. |
| **Sin impacto en `SCHEMA_VERSION`** | ✅ PRO | A diferencia de ADR-17, son campos nuevos (compatibles hacia atrás) — no fuerza el bump por sí solo, aunque se aplica igual porque ADR-17 se implementa en el mismo pasaje. |

## ADR-19 — Corrección de la Fuente de `is_obstructed`: Estado Actual vs. Fracción Acumulada

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-19 |
| **Estado** | Propuesto |
| **Fecha** | Agosto 2026 |
| **Depende de** | ADR-01 |
| **Impacta en** | ADR-06, ADR-11, ADR-13 |

### Contexto y Motivación

La visita presencial al LIT del 20/08/2026, con seis días de datos reales acumulados desde la
semana 10 (ver `docs/PROGRESS.md`), mostró un hallazgo llamativo: 8358 de 8359 muestras reales
tenían `is_obstructed=true`, con la antena en una ubicación sin obstrucción visible aparente.
Investigado en el momento, no era un dato real — era un bug de mapeo.

La implementación original (semana 10, sesión del 12/08) derivaba `is_obstructed` de
`dishGetStatus.obstructionStats.fractionObstructed > 0`, documentado en su momento como
"la única señal disponible, ya que el firmware no expone un booleano `currently_obstructed`"
(confirmado ausente ese día). Esa parte seguía siendo cierta el 20/08 (reconfirmado en vivo
contra la antena, firmware ya en `2026.08.10.mr84226`) — pero el campo elegido como proxy no
era el correcto: `fractionObstructed` es la fracción de muestras obstruidas **acumulada desde
que arrancó la ventana de validación de la antena** (`obstructionStats.validS`, del orden de
horas o días de uptime continuo), no el estado instantáneo. Con el umbral `>0` usado, cualquier
obstrucción que hubiera ocurrido en algún momento de esa ventana — un pájaro cruzando, un
segundo de nubes bajas — dejaba el booleano en `True` durante todo el resto de la ventana,
aunque el cielo estuviera despejado en el momento de cada medición puntual. El valor medido en
vivo (`fractionObstructed=0.00038`, 0.04%) confirma esto: es un número minúsculo, consistente
con cielo mayormente despejado, pero el umbral `>0` lo convertía en `True` de todas formas.

### Alternativas Consideradas

| **Aspecto** | **Alt. A — Subir el umbral de `fractionObstructed`** | **Alt. B — `dishGetDiagnostics.alerts.obstructed` ✅** | **Alt. C — Dejar `is_obstructed` en `null` siempre** |
| --- | --- | --- | --- |
| Semántica correcta ("obstruido ahora") | ⚠️ Sigue siendo una fracción acumulada — cualquier umbral es arbitrario y no representa el instante de la medición | ✅ Flag de estado actual, exactamente lo que pide el DER (§3.1) y el objetivo de correlación del PI | — |
| Validado contra la antena real | ⚠️ No hay forma de calibrar un umbral "correcto" sin inventar un valor sin base empírica | ✅ Confirmado en vivo el 20/08/2026: `is_obstructed=False` con la antena despejada | — |
| Costo de implementación | ✅ Cambio de una constante | ⚠️ Requiere una cuarta llamada gRPC por ciclo de polling (`get_diagnostics`), con su propio manejo de fallo | ✅ Ninguno |
| Valor para el objetivo del PI | ⚠️ Sigue siendo una aproximación cuestionable para correlacionar con clima | ✅ Dato confiable para CA-04/campaña de medición (Semana 22) | ❌ Pierde el campo por completo, contradice RF-03 |

### Decisión

**✅ Decisión: Alternativa B — `dishGetDiagnostics.alerts.obstructed`**

Se agrega `get_diagnostics()` a `src/acquisition/grpc_client.py` (tercera llamada de lectura,
junto a `get_status`/`get_history` — dentro del alcance ya declarado en `CLAUDE.md` §1.1).
`map_status()`/`build_metrics()` (`src/acquisition/starlink_extractor.py`) toman `diagnostics`
como parámetro opcional: si la llamada falla ese ciclo (antena momentáneamente no disponible),
`is_obstructed` queda en `None` para ese payload en vez de tumbar el ciclo completo o inventar
un valor — mismo criterio de degradación ya establecido para el resto de `metrics`.

`dishGetDiagnostics.alerts` usa serialización JSON dispersa (proto3): solo aparecen las claves
en `TRUE` (confirmado contra la antena real, `alerts: {}` cuando no hay ningún alerta activo).
La ausencia de la clave `"obstructed"` en el dict significa `False`, no "sin dato" — eso solo
ocurre si el objeto `dishGetDiagnostics` entero está ausente (llamada fallida).

**Sin verificar todavía contra un evento de obstrucción real** — la antena no tuvo ninguno
durante la visita del 20/08. Queda pendiente confirmar la próxima vez que haya condiciones
reales de obstrucción (nubes bajas, algo bloqueando la vista momentáneamente).

### Pros y Contras

| **Aspecto** | **PRO ✅ / CONTRA ⚠️** | **Detalle** |
| --- | --- | --- |
| **Corrige un dato incorrecto en la campaña de medición en curso** | ✅ PRO | Semana 22 (`docs/PROGRESS.md`) venía acumulando `is_obstructed=true` casi constante — dato inutilizable para la memoria hasta esta corrección. |
| **Cuarta llamada gRPC por ciclo de polling** | ⚠️ CONTRA | Overhead adicional de `grpcurl` como subproceso (mismo patrón que `get_status`/`get_history`) — aceptable dado el intervalo de 60s (RF-01), igual criterio que la enmienda de mecanismo de ADR-01. |
| **Semántica dispersa de `alerts` sin verificar contra un evento real positivo** | ⚠️ CONTRA | El caso `obstructed=True` está testeado con datos sintéticos (`tests/test_acquisition.py`), no contra una obstrucción real capturada en el LIT — riesgo bajo pero real de que la inferencia "ausencia=False" no se sostenga en algún caso de borde del firmware. |
| **`schema.py` sin cambios de tipo/rango** | ✅ PRO | `is_obstructed` sigue siendo `Optional[bool]` — no fuerza bump de `SCHEMA_VERSION`, a diferencia de ADR-17. |

## ADR-20 — Bridge MQTT Saliente hacia el Broker Compartido de la VM de Cátedra

| **Atributo** | **Valor** |
| --- | --- |
| **ID** | ADR-20 |
| **Estado** | Propuesto |
| **Fecha** | Agosto 2026 |
| **Depende de** | ADR-04, ADR-09 |
| **Impacta en** | ADR-14 |

### Contexto y Motivación

El director (Santiago) ofreció una VM de la cátedra (`35.224.141.221`, IP pública) para
alojar infraestructura compartida entre este módulo y el de Fede, con el objetivo
concreto de exponer un front público con QR (ver `docs/PROGRESS.md`, visita del
20/08/2026). `starlink-station-stack` (repo neutral de integración) ya desplegó ahí un
broker Mosquitto con autenticación (`docs/01_ADR.md` de ese repo) — el problema que
faltaba resolver era cómo hacer que la telemetría real de este módulo (que se genera en
la RPi5, dentro de la red del LIT) llegue a ese broker compartido.

El primer intento (sesión anterior, 19/8) falló: la RPi5 no alcanzaba la VM por el
puerto `5883`. Diagnosticado en esta visita: **no es un problema de conectividad, es de
routing**. La red del LIT/UNC solo permite salida a internet por los puertos 80/443
(confirmado contra un servidor de control neutral, `portquiz.net`, que rechaza el mismo
tráfico por el mismo camino). Pero la RPi5 tiene un segundo uplink: el propio terminal
Starlink que está midiendo, conectado por `eth0`, con salida a internet sin esa
restricción — la ruta por defecto simplemente no lo estaba usando (métrica de `wlan0`
más baja que la de `eth0`).

El código Python de este módulo (`src/common/mqtt.py`) no soporta autenticación MQTT
(nunca hizo falta, el broker local es `allow_anonymous true` por diseño — ADR-04/ADR-14),
pero el broker de la VM exige credenciales. Cambiar `src/` para soportar dos brokers con
credenciales distintas (local sin auth, remoto con auth) hubiera acoplado la lógica de
publicación del extractor/mock a una decisión de despliegue que no le corresponde.

### Alternativas Consideradas

| **Aspecto** | **Alt. A — `src/common/mqtt.py` publica a ambos brokers** | **Alt. B — Bridge de Mosquitto (broker→broker) ✅** | **Alt. C — Apuntar `MQTT_HOST` directo a la VM, sin broker local** |
| --- | --- | --- | --- |
| Cambios en `src/` | ⚠️ Requiere soportar credenciales opcionales, reintentos y buffer offline para un segundo destino — duplica lógica que Mosquitto ya resuelve | ✅ Ninguno | ⚠️ Requiere agregar `username_pw_set` (ADR-04 nunca lo necesitó) |
| Riesgo sobre la corrida de CA-02 en curso | ⚠️ Cualquier bug en la lógica nueva de publicación doble puede afectar la ingesta local que ya lleva 5+ días sin errores | ✅ El pipeline local (mock/acquisition → broker local → consumer) no se toca | ❌ Pierde el broker local (`allow_anonymous`, sin latencia de red) como fuente para el consumer/backend que corren en la misma RPi5 |
| Resiliencia ante caída de la VM/ruta a internet | ⚠️ A programar a mano | ✅ Mosquitto ya maneja reconexión y `cleansession false` para el bridge, mismo patrón que cualquier cliente | ❌ Sin broker local, una caída de la VM tumba la ingesta completa, no solo la replicación |
| Complejidad operativa | ⚠️ Media (código nuevo) | ⚠️ Media (config de bridge + credenciales fuera del repo) | ✅ Baja, pero al costo de acoplar toda la pila local a la disponibilidad de la VM |

### Decisión

**✅ Decisión: Alternativa B — Bridge de Mosquitto (broker local → broker de la VM)**

`services/broker/mosquitto.conf` agrega `include_dir /mosquitto/config/conf.d`, y el
bridge real (`connection vm-bridge`, `topic starlink/# out 1`, `bridge_protocol_version
mqttv50`) vive en `services/broker/conf.d/bridge.conf` — **no versionado** (repo público,
`mosquitto.conf` no soporta variables de entorno para inyectar credenciales en runtime).
Se agrega `services/broker/conf.d/bridge.conf.example` como plantilla versionada.

El bridge es `out` únicamente (no `both`): el broker local sigue siendo la única fuente
de verdad para el consumer/backend que corren en la misma RPi5 — la VM recibe una copia,
no participa en el pipeline local.

**Ruta de red**: `ip route add 35.224.141.221 via 100.64.0.1 dev eth0` (persistida vía
NetworkManager en la conexión del uplink Starlink) — quirúrgica, solo ese destino sale
por `eth0`; todo el resto del tráfico de la RPi5 (incluido el propio SSH de gestión)
sigue por `wlan0` sin cambios.

### Pros y Contras

| **Aspecto** | **PRO ✅ / CONTRA ⚠️** | **Detalle** |
| --- | --- | --- |
| **Desbloquea el front público con QR pedido por el director** | ✅ PRO | Es el primer paso concreto para que la telemetría real llegue a infraestructura con IP pública. |
| **Cero cambios en `src/`** | ✅ PRO | Mosquitto resuelve auth/reconexión/buffer del lado del broker, sin acoplar el código de la aplicación a una decisión de despliegue. |
| **La telemetría de red sale por el mismo enlace que está midiendo** | ⚠️ CONTRA | Consideración metodológica, no técnica: el tráfico del bridge (~500 bytes cada 60s, despreciable frente al ancho de banda del enlace) viaja por el propio Starlink bajo medición. Documentado para la memoria, no afecta la validez de las métricas (el tráfico de control es órdenes de magnitud menor al de la medición). |
| **Ruta de red no estándar, dependiente de que la RPi5 mantenga ambos uplinks** | ⚠️ CONTRA | Si el enlace Starlink cae, el bridge también cae (aunque el pipeline local sigue funcionando sin él) — es una dependencia nueva, documentada, no una falla silenciosa. |
| **Credenciales fuera del repo (gitignored)** | ✅ PRO | Mismo patrón ya validado en `starlink-station-stack/infra/mosquitto-vm/` (passwordfile) — consistente, no una solución ad-hoc nueva. |

# APÉNDICES

## Apéndice A — Mapa de Dependencias entre ADRs

El siguiente grafo muestra las relaciones de dependencia entre las 20 decisiones documentadas. Una flecha ADR-X → ADR-Y indica que ADR-Y depende de la decisión tomada en ADR-X.

| **ADR Base** | **ADRs que dependen de él** |
| --- | --- |
| ADR-01 (Serialización JSON+Pydantic) | ADR-04, ADR-06, ADR-07, ADR-08, ADR-11, ADR-16, ADR-17, ADR-18, ADR-19 |
| ADR-02 (Sensor BME280 digital) | ADR-03, ADR-05, ADR-07 |
| ADR-03 (ESP32 como Gateway) | ADR-04, ADR-05, ADR-07 |
| ADR-04 (MQTT + ORM) | ADR-09, ADR-10, ADR-12, ADR-20 |
| ADR-05 (Python + C++) | ADR-06, ADR-07, ADR-08, ADR-09, ADR-12 |
| ADR-06 (Mock Starlink Random Walk) | ADR-16, ADR-17, ADR-18 |
| ADR-09 (Mosquitto MQTT) | ADR-10, ADR-12, ADR-20 |
| ADR-10 (Database per Service) | ADR-11, ADR-12, ADR-13 |
| ADR-11 (TimescaleDB) | ADR-12, ADR-13 |
| ADR-12 (Docker) | Todos los ADRs son impactados por la contenerización |
| ADR-13 (Grafana) | ADR-14, ADR-15 |

## Apéndice B — Registro de Decisiones Rechazadas

Este apéndice consolida las alternativas que fueron evaluadas seriamente pero no seleccionadas, como referencia para futuras revisiones.

| **Alternativa Rechazada** | **En ADR** | **Razón Principal de Rechazo** |
| --- | --- | --- |
| Protobuf End-to-End | ADR-01 | Sobrecarga de compilación de esquemas en el ciclo de desarrollo con mocks. Incompatible con TimescaleDB/Grafana nativamente. |
| JSON Puro sin validación (Pydantic) | ADR-01 | Sin garantías de tipado. Riesgo de corrupción silenciosa de la DB ante errores en los datos. |
| Sensores Analógicos (LM35, NTC) | ADR-02 | Requieren ADC externo no disponible en RPi5. Alta sensibilidad a EMI de la antena Starlink. |
| Arduino Uno + Serial Bridge | ADR-03 | Requiere script Python intermediario en RPi5. Dependencia de cable USB físico. |
| REST HTTP Síncrono para IoT | ADR-04 | Acoplamiento temporal. Un microcorte en el receptor implica pérdida irreversible del dato. |
| Conexión SQL directa desde el sensor | ADR-04 | Viola el principio de Menor Privilegio. El sensor conoce credenciales SQL internas. |
| Stack Híbrido C++ + Python + Node.js | ADR-05 | Tres stacks, tres curvas de aprendizaje, tres ecosistemas de dependencias. Inmanejable para el equipo del PI. |
| Golang para microservicios | ADR-05 | Sin experiencia del equipo. Librerías del ecosistema Starlink (grpcio) son mejores en Python. |
| Replay de CSV histórico (mock Starlink) | ADR-06 | Acoplado a un dataset estático. Sin capacidad de inyectar edge cases específicos bajo demanda. |
| Generación aleatoria pura (mock Starlink) | ADR-06 | Ruido blanco sin inercia temporal. Gráficos de Grafana inútiles para validación visual. |
| Mock Unificado (un solo script) | ADR-07 | No valida la arquitectura real de múltiples productores concurrentes. Viola SRP de SOLID. |
| Scripts SQL de seeding (INSERT masivo) | ADR-08 | Solo prueba la existencia de tablas. No valida el pipeline de ingesta E2E. |
| RabbitMQ (AMQP) | ADR-09 | ~300 MB RAM base. Overkill para el RPi5. Sin librería AMQP estable para ESP32. |
| Redis Pub/Sub | ADR-09 | Sin persistencia de mensajes para clientes offline por defecto. Pérdida de datos durante reinicios del consumer. |
| Base de Datos Monolítica Unificada | ADR-10 | Riesgo de cascading failure. Operaciones costosas sobre clima pueden bloquear inserciones de red. |
| InfluxDB 2.x | ADR-11 | Lenguaje Flux propio con alta curva de aprendizaje. Sin soporte nativo de JOINs SQL para metadatos relacionales. |
| PostgreSQL puro (sin TimescaleDB) | ADR-11 | Index Thrashing al acumular millones de filas. Performance de escritura degradada en el tiempo. |
| Instalación directa (Bare Metal) | ADR-12 | Síndrome 'works on my machine'. Migración a nube manual y propensa a errores. |
| Frontend React/Vue a medida | ADR-13 | Semanas de desarrollo UI sin valor directo para la investigación de redes del PI. |
| Placeholder estático (imagen JPG) | ADR-15 | No valida el stream de video real ni el impacto en el ancho de banda de las mediciones. |
| Booleano `is_handover` (handover) | ADR-16 | Colapsa a un bit por medición; pierde multiplicidad de handovers en la ventana de polling y no permite panel de conteo agregado en Grafana. |
| Mantener `snr_db` nullable, real siempre `null` | ADR-17 | El hardware real nunca podría producir un valor no-nulo — rompe la equivalencia mock↔real 1:1 de ADR-01 de forma permanente, no ocasional. |
| Ambos booleanos (`snr_low` + `snr_above_floor`) | ADR-17 | `isSnrAboveNoiseFloor` es casi redundante con `packet_loss_pct`/`is_obstructed` ante un corte total de señal; no justifica el campo extra. |
| Sub-objeto `alignment` anidado en el payload | ADR-18 | `network_metrics` es plana por naturaleza (columnas SQL); anidar obliga al consumer a aplanar sin ninguna ganancia real. |
| Exponer `attitudeEstimationState` | ADR-18 | Enum string de estado interno del algoritmo de tracking, sin uso analítico directo para el objetivo de correlación clima-red del PI. |
| Subir el umbral de `obstructionStats.fractionObstructed` en vez de cambiar de fuente | ADR-19 | Sigue siendo una fracción acumulada desde que arrancó la ventana de validación de la antena, no el estado instantáneo — cualquier umbral es arbitrario y no representa el momento de la medición. |
| Dejar `is_obstructed` en `null` siempre (real) | ADR-19 | Pierde el campo por completo para el módulo real, contradice RF-03 y descarta un correlato directo con el objetivo del PI. |

## Comments

### Pendientes

[^c9] ALDANA MICAELA PAVET GARCÍA: Cuanto espacio demanda eso, rever mensajes a probar
      — **Parcial (19-20/8)**: estimación analítica agregada donde estaba el
      comentario (~9-15 MB sin comprimir para 30 días). Sigue faltando la medición
      real (`du -sh` sobre el volumen después de correr el backfill de verdad,
      Semana 21 — sin ejecutar todavía).
[^c13] SANTIAGO MARTIN HENN: parte del mismo
[^c8] ALDANA MICAELA PAVET GARCÍA: No es necesario por objetivo — sigue siendo una
      decisión de alcance de Pavet García (¿vale la pena que el mock simule
      comportamiento dinámico o alcanzaba con algo más simple para el objetivo del
      PI?), no algo que se resuelva con evidencia — pendiente de que ella lo decida.
[^c12] SANTIAGO MARTIN HENN: No?
[^c11] ALDANA MICAELA PAVET GARCÍA: 200 que? — **Aclarado (19-20/8)** dónde estaba el
      comentario: no hay base empírica real para el umbral "200", queda marcado como
      estimación sin verificar hasta correr el stress test real (Semana 21).
      **Sigue pendiente** correr ese test para confirmar o corregir el número.

### Resueltos

[^c7] ALDANA MICAELA PAVET GARCÍA: Mock para validar funcionamiento antes de conectar
      — **Resuelto (19-20/8)**: la antena real ya está conectada y funcionando desde
      el 14/8/2026 (`docs/PROGRESS.md`, semana 10) — el mock cumplió exactamente el
      propósito que describía este comentario, validar la pila completa antes de
      tener hardware real.
[^c10] ALDANA MICAELA PAVET GARCÍA: Sacar o explicar bien — **Resuelto (19-20/8)**: la
      frase original era correcta, solo faltaba explicarla — se agregó la referencia
      exacta al código real que implementa el cálculo hacia atrás
      (`src/mock_starlink/mock.py:49,81,228`), donde estaba el comentario.

[^c14] SANTIAGO MARTIN HENN: poner algo de que las apps que desarrollan van a ser "stateless" — resuelto: aclarado en el Contexto de ADR-12 que es "stateless" a nivel de infraestructura (12-factor, sin volúmenes locales persistentes), lo cual no contradice que el mock de Starlink sea "stateful" a nivel de lógica de generación de datos en memoria (ADR-06).
[^c5] ALDANA MICAELA PAVET GARCÍA: No queda claro, para qué? (ver `docs/PROGRESS.md`, fila `net_health/iperf_test` de ADR-04) — resuelto: fuera del "Alcance técnico" de `CLAUDE.md` §1.1 (solo telemetría pasiva vía gRPC); la fila se eliminó de la tabla de tópicos de ADR-04. De agregarse iPerf3 activo en el futuro, correspondería a `network_tests` (DER §3.2), no a `network_metrics`.
[^c6] ALDANA MICAELA PAVET GARCÍA: Paradigma de programación — resuelto: título de ADR-05 renombrado a "Selección de Lenguajes y Paradigma de Programación".
[^c2] ALDANA MICAELA PAVET GARCÍA: Explicar que se elige porque viene integrado con interfaces — resuelto: agregado a la Decisión de ADR-02.
[^c1] ALDANA MICAELA PAVET GARCÍA: Anticorrupción, acl — resuelto: agregado párrafo de framing ACL (Anti-Corruption Layer) en la Justificación de ADR-01.
[^c3] ALDANA MICAELA PAVET GARCÍA: Definir — resuelto: parámetros de backoff exponencial definidos en ADR-03 (delay inicial 1s, factor x2, tope 60s, reintentos indefinidos).
[^c0] ALDANA MICAELA PAVET GARCÍA: No es formato de serialización, es una estructura de datos — resuelto: reformulada la Decisión de ADR-01 para aclarar que el dict Python es una estructura en memoria, no un formato de serialización.
[^c4] ALDANA MICAELA PAVET GARCÍA: Definir — resuelto: mensaje LWT definido en ADR-03 (`starlink/status/<node_id>` / `meteo/status/<node_id>` desde la enmienda del 14/08/2026, antes `system/status/<node_id>`; payload JSON, retain=true, QoS 1); tópico alineado en la tabla de ADR-04.