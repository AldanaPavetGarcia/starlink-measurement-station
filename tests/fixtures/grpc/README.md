# Fixtures gRPC — antena real (LIT)

Capturas reales de `grpcurl` contra la antena Starlink del LIT (`192.168.100.1:9200`),
tomadas por SSH durante la sesión de relevamiento del 04/08/2026 (ver
`docs/PROGRESS.md` §Semana 10). Sirven para testear `src/acquisition/starlink_extractor.py`
contra la forma real de la respuesta gRPC, no solo contra dicts sintéticos.

- `get_device_info.json`, `get_status.json`, `get_status_full.json`,
  `get_diagnostics.json`: snapshots puntuales.
- `get_history.json`: ventana de historial (`popPingLatencyMs`, `popPingDropRate`,
  `outages[]`, etc.) usada para `derive_jitter_loss`/`count_handovers`.

**Redactado (20/08/2026):** el campo `id`/`deviceId` (identificador de hardware real de
la antena) fue reemplazado por `ut01000000-00000000-00000000` en los 5 archivos antes de
commitear — el repo es público y ese ID es un identificador persistente del equipo físico
del LIT, sin valor para los tests. `location` ya viene con `enabled: false` y
lat/lon en 0 desde el original (GPS reporting deshabilitado en la antena), así que no hubo
que tocar eso.
