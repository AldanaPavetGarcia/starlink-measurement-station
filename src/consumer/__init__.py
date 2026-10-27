"""Consumer MQTT -> TimescaleDB (Database per Service, ADR-10).

Procesa únicamente el dominio Starlink (`starlink/metrics/<node_id>` ->
`starlink_health_db`). Desde ADR-21 (26/10/2026) el dominio meteo
(`meteo/sensor/`, `meteo/external/`) tiene su propio consumer y su propia DB
en el repo de Fede (`tesis-sensor-node/services/meteo_consumer`).
"""
