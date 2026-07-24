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
| **ADR-10** | Patrón Database per Service | Persistencia | Dos instancias independientes: starlink_health_db y meteo_db | **Propuesto** |
| **ADR-11** | Motor de Base de Datos de Series Temporales | Persistencia | PostgreSQL 16 + extensión TimescaleDB sobre InfluxDB y Postgres puro | **Propuesto** |
| **ADR-12** | Contenerización de Infraestructura | Persistencia | Docker Engine + Docker Compose V2; todo contenerizado | **Propuesto** |
| **ADR-13** | Plataforma de Visualización y Dashboards | Observabilidad | Grafana OSS sobre desarrollo frontend a medida | **Propuesto** |
| **ADR-14** | Postura de Seguridad y Exposición de Puertos | Observabilidad | Zero Trust local: solo puerto Grafana expuesto externamente + filtrado de IP | **Propuesto** |
| **ADR-15** | Mock de Videomonitoreo (Streaming) | Observabilidad | Microservicio Flask/MJPEG a 5 FPS sobre placeholder estático | **Propuesto** |

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

- El firmware del ESP32 incluye el mecanismo Last Will and Testament (LWT) de MQTT: si el ESP32 se cuelga, el broker emite automáticamente un mensaje de alerta en el tópico `system/status/<node_id>` (mismo esquema domain-first que el resto de los tópicos, ver ADR-04). Payload JSON: `{"node_id": "...", "source": "esp32_bme280|starlink_grpc|starlink_mock|...", "status": "offline"}`, `retain=true` (un nuevo suscriptor ve el último estado sin esperar el próximo heartbeat), QoS 1. Todo productor (real o mock) configura su propio LWT con este mismo formato al conectarse al broker.

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
| nodo/lit-01/net_health/iperf_test | Script iPerf3 activo[^c5] | Consumer Router | starlink_health_db → hypertable network_metrics |
| system/status/<node_id> | Cualquier servicio (heartbeats, LWT) | Grafana + Alertmanager | No persiste — alerting en tiempo real |

> Alineado con `docs/03_SRS.md` §5.1 (IF-01, IF-02, IF-03, RF-17), `docs/06_DER.md` y
> `docs/08_Plan_QA.md` (UT-03, IT-01/IT-02) — esos cuatro documentos ya usaban esta
> convención de forma consistente; esta tabla era la que estaba desactualizada. Nota:
> `bme280_hardware`/`bme280_mock` se unifican en un solo tópico porque ADR-01 exige que
> el hardware real y el mock sean intercambiables 1:1 sin cambios downstream (mismo
> tópico, misma morfología de paquete). `system/status/<node_id>` sigue el mismo estilo
> domain-first; no está cubierto por el SRS (es un tópico operativo, no de datos de
> medición) pero no contradice RF-17, que solo obliga la jerarquía de los tres tópicos
> de datos.
>
> La fila `net_health/iperf_test` queda pendiente de revisión — no está cubierta por el
> SRS ni por el "Alcance técnico" de `CLAUDE.md` §1.1, y su propósito no está claro (ver
> comentario [^c5] y `docs/PROGRESS.md`).

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
| latency_ms | Normal(35, 5) ms con Random Walk Δ ∈ [-2.5, +3.0] | 20–80 ms | Handover: spike a 150–400 ms con p=0.05 |
| jitter_ms | Exponential(λ=0.5) | 0–15 ms | Handover: jitter > 50 ms |
| packet_loss_pct | Bernoulli(p=0.005) × 100 | 0–2 % | Obstrucción: 5–40 %; Caída: 100 % por 2–5 min |
| throughput_down_mbps | Normal(180, 30) Mbps | 80–300 Mbps | Degradación: < 50 Mbps durante obstrucción |
| throughput_up_mbps | Normal(22, 5) Mbps | 8–40 Mbps | Idem throughput down, correlacionado |
| obstruction_pct | Uniforme(0, 3) % en estado normal | 0–3 % | Evento físico: 20–80 % durante obstrucción simulada |

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

Los mocks operan con una variable de entorno TIME_WARP_FACTOR (ej. 60). Un factor de 60 significa que los mocks publican 1 msg/s en lugar de 1 msg/min, generando 1 hora de datos en 1 minuto real. El consumer procesa estos mensajes usando exactamente el mismo código de producción. En 30 minutos se pueden cargar 30 días de historia[^c9].

### Pros y Contras

| **Aspecto** | **PRO ✅ / CONTRA ⚠️** | **Detalle** |
| --- | --- | --- |
| **Validación E2E completa** | ✅ PRO | Prueba que todos los chunks de TimescaleDB se crean correctamente, que los índices funcionan, y que la política de compresión se activa en datos > 7 días. |
| **Prueba de write throughput** | ✅ PRO | Con factor 60, el consumer recibe ~3 msg/s. Un stress test con factor 300 (5 msg/s) valida el rendimiento del sistema bajo carga pico. |
| **Cero deuda técnica** | ✅ PRO | No existen scripts SQL extra que mantener. El código de los mocks es el único generador de datos sintéticos. |
| **Complejidad de temporalidad** | ⚠️ CONTRA | Los timestamps en los mensajes deben ser sintéticos (pasado ajustado), no el tiempo real del sistema. Requiere que el mock genere timestamps calculados hacia atrás.[^c10] |
| **Carga en la RPi5** | ⚠️ CONTRA | Un factor muy alto (> 200[^c11]) puede saturar el CPU del RPi5. En desarrollo local (PC), sin limitación práctica. |

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
| Last Will and Testament (LWT) | Si un productor se cuelga sin desconectarse limpiamente, el broker publica automáticamente un mensaje de alerta en el tópico de estado del sistema. | client.will_set('system/status/<node_id>', ...) |
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

| **Criterio** | **Alt. A — Base de Datos Monolítica Unificada** | **Alt. B — Database per Service (dos instancias) ** |
| --- | --- | --- |
| Aislamiento de fallos | ❌ Una query costosa en la tabla de clima puede bloquear la inserción de métricas de red | ✅ Un problema en meteo_db no afecta starlink_health_db. Fallo aislado. |
| Control de acceso (RBAC) | ⚠️ Se puede implementar con esquemas y roles SQL, pero en la misma instancia | ✅ Credenciales completamente separadas por base de datos. Principio de Menor Privilegio nativo. |
| Escalabilidad diferencial | ❌ Escalar la DB escala ambos dominios juntos (desperdicio) | ✅ Se puede mover starlink_health_db a un servidor más potente sin mover meteo_db |
| Backups focalizados | ❌ Backup completo de toda la DB aunque solo cambie un dominio | ✅ pg_dump de starlink_health_db de forma independiente y frecuente sin afectar meteo_db |
| JOIN cruzado entre dominios | ✅ Posible con SQL estándar | ❌ No posible a nivel SQL. Se resuelve en la capa de presentación (Grafana Data Blending). |
| Complejidad de despliegue | ✅ Un solo contenedor PostgreSQL | ⚠️ Dos contenedores PostgreSQL. Manejable con Docker Compose. |

### Decisión

**✅ Decisión: Alternativa B — Database per Service. Dos instancias TimescaleDB independientes.**

starlink_health_db: almacena todas las métricas de red (latencia, jitter, throughput, packet loss, obstruction). meteo_db: almacena todos los datos ambientales (sensor local BME280, APIs externas). Cada instancia tiene sus propias credenciales, volumen Docker y configuración de TimescaleDB. La correlación entre dominios se realiza en Grafana mediante Data Blending (Outer Join by Time).

### Consecuencias e Implicaciones

- El consumer MQTT (el router de base de datos) analiza el tópico de cada mensaje entrante para decidir a qué base de datos insertar. La lógica es simple: tópicos con /net_health/ van a starlink_health_db; tópicos con /meteo/ van a meteo_db.

- Grafana se configura con dos datasources independientes: uno apuntando a starlink_health_db y otro a meteo_db. Los dashboards de correlación usan el operador de transformación Outer Join by Time para alinear ambas series.

- Los scripts de inicialización SQL (init.sql) son separados por base de datos y se ejecutan como parte de la configuración del contenedor Docker.

- En la migración a nube (Fase 2), las dos bases de datos pueden migrarse independientemente o a servidores distintos, maximizando la flexibilidad operativa.

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

Adicionalmente, la directriz explícita del director exige que la migración de entorno local a nube sea transparente, consistiendo idealmente en solo cambiar variables de entorno (IP del servidor, credenciales[^c14]) sin reescribir código.

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

Cada microservicio tiene su propio Dockerfile. Un único docker-compose.yml orquesta todos los servicios: broker MQTT, dos instancias TimescaleDB, consumer router, backend FastAPI, Grafana, mocks. Las imágenes base son slim/alpine para minimizar el tamaño. Las versiones de dependencias están pinneadas (no se usa :latest en producción).

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

# APÉNDICES

## Apéndice A — Mapa de Dependencias entre ADRs

El siguiente grafo muestra las relaciones de dependencia entre las 15 decisiones documentadas. Una flecha ADR-X → ADR-Y indica que ADR-Y depende de la decisión tomada en ADR-X.

| **ADR Base** | **ADRs que dependen de él** |
| --- | --- |
| ADR-01 (Serialización JSON+Pydantic) | ADR-04, ADR-06, ADR-07, ADR-08, ADR-11 |
| ADR-02 (Sensor BME280 digital) | ADR-03, ADR-05, ADR-07 |
| ADR-03 (ESP32 como Gateway) | ADR-04, ADR-05, ADR-07 |
| ADR-04 (MQTT + ORM) | ADR-09, ADR-10, ADR-12 |
| ADR-05 (Python + C++) | ADR-06, ADR-07, ADR-08, ADR-09, ADR-12 |
| ADR-09 (Mosquitto MQTT) | ADR-10, ADR-12 |
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

## Comments

### Pendientes

[^c9] ALDANA MICAELA PAVET GARCÍA: Cuanto espacio demanda eso, rever mensajes a probar
[^c14] SANTIAGO MARTIN HENN: poner algo de que las apps que desarrollan van a ser "stateless"
[^c13] SANTIAGO MARTIN HENN: parte del mismo
[^c10] ALDANA MICAELA PAVET GARCÍA: Sacar o explicar bien
[^c7] ALDANA MICAELA PAVET GARCÍA: Mock para validar funcionamiento antes de conectar
[^c8] ALDANA MICAELA PAVET GARCÍA: No es necesario por objetivo
[^c12] SANTIAGO MARTIN HENN: No?
[^c5] ALDANA MICAELA PAVET GARCÍA: No queda claro, para qué? (ver `docs/PROGRESS.md`, fila `net_health/iperf_test` de ADR-04)
[^c11] ALDANA MICAELA PAVET GARCÍA: 200 que?

### Resueltos

[^c6] ALDANA MICAELA PAVET GARCÍA: Paradigma de programación — resuelto: título de ADR-05 renombrado a "Selección de Lenguajes y Paradigma de Programación".
[^c2] ALDANA MICAELA PAVET GARCÍA: Explicar que se elige porque viene integrado con interfaces — resuelto: agregado a la Decisión de ADR-02.
[^c1] ALDANA MICAELA PAVET GARCÍA: Anticorrupción, acl — resuelto: agregado párrafo de framing ACL (Anti-Corruption Layer) en la Justificación de ADR-01.
[^c3] ALDANA MICAELA PAVET GARCÍA: Definir — resuelto: parámetros de backoff exponencial definidos en ADR-03 (delay inicial 1s, factor x2, tope 60s, reintentos indefinidos).
[^c0] ALDANA MICAELA PAVET GARCÍA: No es formato de serialización, es una estructura de datos — resuelto: reformulada la Decisión de ADR-01 para aclarar que el dict Python es una estructura en memoria, no un formato de serialización.
[^c4] ALDANA MICAELA PAVET GARCÍA: Definir — resuelto: mensaje LWT definido en ADR-03 (`system/status/<node_id>`, payload JSON, retain=true, QoS 1); tópico alineado en la tabla de ADR-04.