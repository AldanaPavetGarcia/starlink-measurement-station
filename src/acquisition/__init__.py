"""
Extractor real de telemetría Starlink (Semana 10, CLAUDE.md §1.1 "fin del
desarrollo desacoplado del hardware"). Reemplaza a src/mock_starlink/ en
producción -- mismo tópico MQTT, misma morfología de paquete (ADR-01).

Separado en dos capas a propósito, para poder escribir/testear casi todo sin
acceso a la antena real (ver docs/PROGRESS.md, sesión de retomada tras corte
de máquina):
- `grpc_client.py`: la única parte que toca la red (gRPC de la antena vía
  grpcurl). No testeada contra hardware real en esta sesión -- sin acceso
  presencial al LIT, ver docstring del módulo.
- `starlink_extractor.py`: funciones puras (dict -> dict) que hacen el mapeo
  gRPC -> StarlinkMetrics, testeables con JSON sintético que imita la
  estructura real documentada en el relevamiento del 04/08/2026.
"""
