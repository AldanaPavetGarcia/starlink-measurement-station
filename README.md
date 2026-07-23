# starlink-measurement-station
Módulo de adquisición de telemetría de red Starlink (latencia, jitter, throughput, obstrucción) para una estación de medición integrada a un testbed internacional de redes LEO. Python · gRPC (Dishy) · Pydantic · MQTT (Mosquitto) · TimescaleDB · FastAPI · Grafana · Docker. Corre sobre Raspberry Pi 5. Proyecto Integrador, LIT — FCEFyN/UNC.

## Estado actual

En desarrollo. Semana 2 cerrada: esquema de datos (ADR-01) y validador Pydantic
alineado al DER (`network_metrics`), suite de tests (53/53, 100% cobertura) y skill de
control de consistencia ADR/DER/SRS/API (`adr-check`) activa. Todavía sin MQTT ni
Docker (ver [cronograma](#) / checklist del proyecto).

## Estructura

```
src/mock_starlink/    # Paquete principal: esquema, mock, extractor
tests/                # Suite de tests
```

## Requisitos

- **Python 3.11** (ADR-05: versión pinneada para toda la capa RPi5). El entorno de
  producción/CI y el contenedor Docker (ADR-12) corren sobre 3.11; en una máquina de
  desarrollo que no tenga 3.11 instalado, 3.13 también funciona hoy (la suite de tests
  no usa nada específico de una versión), pero no reemplaza la validación real en el
  entorno pinneado antes de integrar con hardware o con el resto de la pila.

## Instalación

```bash
git clone <url-del-repo>
cd starlink-measurement-station
python3.11 -m venv .venv   # o python3 -m venv .venv si no tenés 3.11 instalado
source .venv/bin/activate
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
