---
name: adr-check
description: Verifica que el código, los tópicos MQTT, los endpoints REST o cualquier tabla de datos sean consistentes con los cuatro documentos autoritativos del proyecto (docs/05_ADR.md, docs/06_DER.md, docs/03_SRS.md, docs/07_API_REST.md). Usar antes de modificar src/mock_starlink/schema.py, cualquier tópico MQTT, cualquier endpoint de la API, o directamente cualquiera de esos cuatro documentos; y antes de abrir un PR o hacer commit que toque src/ o docs/{05_ADR,06_DER,03_SRS,07_API_REST}.md.
---

# ADR / DER / SRS / API — Control de consistencia

Este proyecto (Proyecto Integrador, estación de medición Starlink + ambiental) define
su arquitectura y contratos de datos en **cuatro documentos autoritativos**, no en uno
solo. Un cambio en el código, o incluso en un solo documento, puede dejar a los otros
tres desincronizados sin que nadie lo note hasta que alguien intenta correr los tests
o integrar con el otro módulo (Fede). Esta skill existe para detectar ese drift *antes*
de que se acumule, no para diseñar arquitectura nueva.

Los cuatro documentos, en el orden de prioridad que fija `CLAUDE.md` §2:

1. `docs/05_ADR.md` — decisiones arquitectónicas (el *por qué*).
2. `docs/03_SRS.md` — requerimientos funcionales/no funcionales (el *qué*, a nivel de
   producto).
3. `docs/06_DER.md` — modelo de datos, esquema SQL, hypertables (el *qué*, a nivel de
   persistencia).
4. `docs/07_API_REST.md` — contrato de la API (el *qué*, a nivel de interfaz externa).

## Tabla de correspondencia (área de código → documentos que la gobiernan)

| Área de código | ADR | DER | SRS | API REST |
|---|---|---|---|---|
| `src/mock_starlink/schema.py` (payload MQTT Starlink) | ADR-01 | `network_metrics` §3.1 | §5.1 | — |
| Tópicos MQTT / QoS / LWT (Starlink y BME280) | ADR-04, ADR-09 | — | IF-01 | — |
| Mock stateful / inyección de caos / `CHAOS_PROFILE` / `TIME_WARP_FACTOR` | ADR-06, ADR-07, ADR-08 | — | — | — |
| Endpoints y contrato REST (`/metrics/starlink*`, `/metrics/env*`, `/nodes*`, auth, envelope) | — | — | RFs de consulta | `docs/07_API_REST.md` completo |
| Esquema/paquete BME280 (módulo de Fede) | ADR-02, ADR-03 | `env_metrics` | §5.2 | — |
| Base de datos / hypertables en general | ADR-10, ADR-11 | Cualquier tabla | — | — |

Si el área tocada no aparece en la tabla, buscar de todas formas cualquier mención
directa en los cuatro documentos antes de asumir que no aplica ninguno.

## Regla general: recorrer las 4 columnas, siempre

**No alcanza con revisar el documento "obvio" para el cambio.** El drift real más
grave que este proyecto tuvo hasta ahora fue entre SRS §5.1 y el DER (`network_metrics`)
— nombres, unidades y tipos de campo completamente distintos (`throughput_down_mbps`
vs. `throughput_down_bps`, `obstruction_pct`/`signal_quality` vs. `is_obstructed`/
`snr_db`) — y ninguno de los dos lo causó el código. Por eso, para cualquier área
tocada, leer y comparar contra los **cuatro** documentos de la fila correspondiente,
incluidas las columnas marcadas "—" (confirmar activamente que no aplica, no asumirlo
por la tabla).

## Procedimiento

1. **Determinar el diff a revisar.** Si se invoca on-demand, usar `git diff main...HEAD`
   o los archivos editados en la sesión actual. Si se invoca desde el hook de
   enforcement, el diff ya viene dado (staged para commit, o rama completa para PR).
2. **Ubicar la fila de la tabla** para cada archivo tocado y leer las secciones exactas
   de los cuatro documentos que aplican (citar archivo:línea al reportar, no
   parafrasear de memoria).
3. **Comparar exhaustivamente**: nombres de campo, tipos, unidades, rangos, nullability,
   nombres de tópicos MQTT, rutas y códigos de la API, envelope de respuesta, QoS,
   `clean_session`, LWT — lo que sea relevante al área. Comparar también los documentos
   **entre sí**, no solo cada uno contra el código.
4. **Clasificar cada hallazgo:**
   - **(a) Bug / drift sin intención de diseño** — el código no hace lo que su propio
     comentario o el doc dicen que debería hacer, y no hay ninguna señal de que sea un
     cambio deliberado. → Proponer corregir el código para que coincida con el doc.
   - **(b) Cambio de diseño intencional** — el desarrollador está introduciendo a
     propósito un comportamiento distinto al documentado. → El/los documento(s)
     tienen que reflejarlo: si el ADR relevante sigue en estado "Propuesto", se puede
     enmendar directamente; si es una decisión nueva no cubierta por ningún ADR
     existente, crear una entrada nueva en `docs/05_ADR.md` siguiendo el formato de las
     entradas existentes (Contexto, Decisión, Alternativas rechazadas, Estado:
     Propuesto). **Nunca dejar la discrepancia sin reflejar en los docs.**
   - **(c) Conflicto preexistente entre documentos** (el código no lo causó — ej. SRS
     vs. DER) — no hay un "documento correcto" obvio para copiar. → Antes de bloquear,
     revisar si `docs/PROGRESS.md` ya tiene una nota reconociendo ese conflicto puntual
     (buscar una sección tipo "Pendiente — revisar con director" que mencione los
     mismos documentos/campos). **Si ya está anotado ahí, no bloquear** — dejarlo pasar
     con un aviso informativo (no bloqueante) de que es un issue ya trackeado. Si NO
     está anotado todavía, ahí sí bloquear y señalar explícitamente para el
     director/co-director (ver `CLAUDE.md` §12, "Decisiones pendientes"), pidiendo que
     se dockumente en `docs/PROGRESS.md` antes de reintentar. Nunca resolverlo
     unilateralmente editando SRS o DER para que coincidan.
5. **Reportar** agrupado por clasificación (a)/(b)/(c), citando archivo:línea de cada
   documento y del código involucrado.

## Reglas al escribir en `docs/05_ADR.md`

- Nunca cambiar el campo "Estado" de un ADR a "Aceptado" — eso lo decide el director.
  Toda entrada nueva o enmendada queda en "Propuesto".
- Seguir el formato de las entradas existentes (ver ADR-01 a ADR-15 como referencia de
  estilo: Decisión, Resumen, Alternativas rechazadas).
- Si la escritura es automática (disparada por el hook de enforcement, no por este
  skill invocado a mano), dejar un comentario visible junto al texto tocado:
  `<!-- actualizado automáticamente por adr-check, revisar -->`.

## Qué NO hace esta skill

- No diseña arquitectura nueva ni toma decisiones de producto — solo detecta
  inconsistencia y, cuando corresponde, refleja una decisión ya tomada por quien
  escribió el código.
- No resuelve conflictos preexistentes entre documentos por su cuenta (caso c).
- No toca nada de Semana 3 en adelante relacionado con el módulo de Fede sin
  coordinar — si el área tocada es compartida (broker, consumer, DB), señalarlo como
  punto de coordinación en vez de decidir solo.
