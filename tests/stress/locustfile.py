"""
Prueba de estrés (Semana 21, docs/08_Plan_QA.md §6.5 — ST-01 a ST-05):
simula clientes Grafana consultando el backend REST mientras el mock (o el
extractor real) inyecta mensajes a alta velocidad (`TIME_WARP_FACTOR`).
Replica el escenario real: la RPi5 ingesta datos Y sirve consultas
simultáneamente.

Adaptado del snippet de referencia del Plan de QA a la API real:
- `API_KEY` -> `BACKEND_API_KEY` (mismo nombre que `src/backend/config.py`).
- Sin tarea de `/metrics/env` -- dominio de Fede, no montado en el backend
  todavía (ver `src/backend/__init__.py`).
- Se agregó `/metrics/starlink/summary` (no estaba en el snippet original).

⚠️ No ejecutado en esta sesión (necesita `docker compose --profile stress
up` corriendo, ver docs/PROGRESS.md por la limitación de espacio en disco
de la sesión). Ejecución documentada abajo.

Ejecución (una vez levantada la pila con TIME_WARP_FACTOR alto):

    # Terminal 1: mock con TIME_WARP alto, perfil "stress"
    TIME_WARP_FACTOR=3600 docker compose --profile stress up -d

    # Terminal 2: Locust, 10 usuarios concurrentes, 5 minutos
    BACKEND_API_KEY=<la del .env> locust -f tests/stress/locustfile.py \
        --headless -u 10 -r 2 --run-time 5m \
        --host http://localhost:8000 --html reports/stress_report.html

    # Mientras corre, en otra terminal: docker stats (uso de CPU/RAM real
    # del RPi5, no de la PC de desarrollo -- el número que vale para RNF-01
    # es el del hardware real, ver docs/08_Plan_QA.md §6.4)
"""

import os
from datetime import datetime, timedelta, timezone

from locust import HttpUser, between, task

BACKEND_API_KEY = os.environ.get("BACKEND_API_KEY", "test-key")
NODE_ID = os.environ.get("STARLINK_NODE_ID", "lit-cordoba-01")

# Rango relativo a "ahora" (no hardcodeado): un dashboard de Grafana real usa
# ventanas relativas, no fechas fijas -- un rango fijo queda viejo apenas pasa
# el momento en que se escribió y el backend responde legítimamente "sin
# datos" (404 NO_DATA_FOUND en /summary) apenas la ejecución real deja de
# caer justo en esa ventana. Encontrado corriendo el stress test 19-20/8/2026
# (15/15 fallos en /summary con el rango viejo hardcodeado).
#
# Ojo con calcular esto una sola vez a nivel de módulo: Locust importa el
# archivo una vez al arrancar, así que un `_START`/`_END` calculado acá
# quedaría clavado al instante de arranque del proceso -- en una corrida de
# varios minutos, para cuando el test lleva un rato corriendo, `_END` ya
# quedó "en el pasado" respecto al momento real de cada request, y las filas
# nuevas insertadas después de ese instante congelado quedan fuera de la
# ventana (89% de fallos en /summary al re-correr con esto congelado, 0% en
# /metrics/starlink porque ese endpoint tolera `data: []` vacío en vez de
# marcarlo error -- ver `_window()` abajo, se recalcula en cada request).
def _window() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return start, now.strftime("%Y-%m-%dT%H:%M:%SZ")


class GrafanaUser(HttpUser):
    """Simula un panel de Grafana refrescando cada ~30s (mismo intervalo
    que `refresh` en `services/grafana/dashboards/red_starlink.json`)."""

    wait_time = between(25, 35)
    headers = {"X-API-Key": BACKEND_API_KEY}

    @task(5)
    def query_starlink_7d(self):
        """Consulta más frecuente: 7 días de latencia (usa CAGG net_hourly,
        RNF-02 -- debe responder en <3s incluso bajo carga)."""
        start, end = _window()
        self.client.get(
            f"/api/v1/metrics/starlink"
            f"?node_id={NODE_ID}"
            f"&start={start}&end={end}"
            f"&resolution=hourly",
            headers=self.headers, name="/metrics/starlink [7d hourly]",
        )

    @task(2)
    def query_summary(self):
        start, end = _window()
        self.client.get(
            f"/api/v1/metrics/starlink/summary"
            f"?node_id={NODE_ID}&start={start}&end={end}",
            headers=self.headers, name="/metrics/starlink/summary [7d]",
        )

    @task(1)
    def health_check(self):
        self.client.get("/api/v1/health", name="/health")

    @task(1)
    def query_latest(self):
        self.client.get(
            f"/api/v1/metrics/starlink/latest?node_id={NODE_ID}",
            headers=self.headers, name="/metrics/starlink/latest",
        )
