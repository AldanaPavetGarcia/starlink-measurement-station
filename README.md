# starlink-measurement-station
Módulo de adquisición de telemetría de red Starlink (latencia, jitter, throughput, obstrucción) para una estación de medición integrada a un testbed internacional de redes LEO. Python · gRPC (Dishy) · Pydantic · MQTT (Mosquitto) · TimescaleDB · FastAPI · Grafana · Docker. Corre sobre Raspberry Pi 5. Proyecto Integrador, LIT — FCEFyN/UNC.

## Estado actual

En desarrollo. Etapa actual: definición del esquema de datos (ADR-01) y validador Pydantic, sin MQTT ni Docker todavía (ver [cronograma](#) / checklist del proyecto).

## Estructura

```
src/mock_starlink/    # Paquete principal: esquema, mock, extractor
tests/                # Suite de tests
```

## Requisitos

- Python 3.11+

## Instalación

```bash
git clone <url-del-repo>
cd starlink-measurement-station
pip install -r requirements.txt
```

## Tests

Correr la suite de tests unitarios (UT-01):

```bash
PYTHONPATH=src pytest tests/test_schema.py -v
```

Con reporte de cobertura:

```bash
PYTHONPATH=src pytest tests/test_schema.py --cov=src/mock_starlink --cov-report=term-missing
```
