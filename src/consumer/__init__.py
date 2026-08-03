"""Consumer MQTT -> TimescaleDB (Database per Service, ADR-10).

Semana 6 (CLAUDE.md §1.1): implementa por ahora únicamente el dominio Starlink
(`starlink/metrics/<node_id>` -> `starlink_health_db`). El dominio meteo
(`meteo/sensor/`, `meteo/external/`) queda enrutado pero sin persistencia real
-- es el módulo de Fede -- ver `MeteoDB` en `db.py`.
"""
