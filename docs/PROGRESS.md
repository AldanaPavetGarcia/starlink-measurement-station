# PROGRESS.md — Módulo Starlink (Aldana)

> Estado de avance real del módulo de conexión a la antena Starlink, alineado al roadmap de
> `CLAUDE.md` §1.1. Editar a mano o pedirle a Claude Code que lo actualice al cerrar una tarea.
> Convención: **[IND]** trabajo individual · **[INT]** integración con el módulo de Fede ·
> **[HW]** requiere hardware real.

**Última actualización:** semana 1 completada.

---

## Semana 1 — Carpeta mock_starlink + esquema + tests `[IND]` ✅ COMPLETA

- [x] Crear la carpeta `src/mock_starlink/`
- [x] Estudiar el endpoint gRPC nativo de la antena (Dishy) en `192.168.100.1:9200` y el repo `starlink-grpc-tools`
- [x] Definir el esquema JSON del paquete de telemetría (ADR-01): `latency_ms`, `jitter_ms`, `packet_loss_pct`, `throughput_down/up_bps`, `snr_db`, `is_obstructed`, `satellite_count`
- [x] Escribir el validador Pydantic (`StarlinkPayloadIn`) sobre ese esquema
- [x] Escribir los primeros tests unitarios que validan el esquema (suite UT-01)

## Semana 2 — Tests unitarios + arquitectura de contratos `[IND]→[INT]`

- [ ] Ampliar la suite UT-01: 1000 payloads generados sin `ValidationError`
- [ ] Cubrir casos límite: campos nulos, `packet_loss_pct` fuera de rango, `schema_version` incorrecto
- [ ] Instalar y configurar entorno Python 3.11 (venv, grpcio, pydantic)
- [ ] Empezar, junto a Fede, la definición de arquitectura y contratos (ADR-01 a ADR-05)

## Semana 3 — Docker + broker MQTT `[INT — primera integración con Fede]`

- [ ] Levantar Eclipse Mosquitto (MQTT v5.0) vía Docker Compose (ADR-09, ADR-12) junto con Fede
- [ ] Definir el topic de publicación para métricas Starlink
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
