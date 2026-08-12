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

from locust import HttpUser, between, task

BACKEND_API_KEY = os.environ.get("BACKEND_API_KEY", "test-key")
NODE_ID = os.environ.get("STARLINK_NODE_ID", "lit-cordoba-01")


class GrafanaUser(HttpUser):
    """Simula un panel de Grafana refrescando cada ~30s (mismo intervalo
    que `refresh` en `services/grafana/dashboards/red_starlink.json`)."""

    wait_time = between(25, 35)
    headers = {"X-API-Key": BACKEND_API_KEY}

    @task(5)
    def query_starlink_7d(self):
        """Consulta más frecuente: 7 días de latencia (usa CAGG net_hourly,
        RNF-02 -- debe responder en <3s incluso bajo carga)."""
        self.client.get(
            f"/api/v1/metrics/starlink"
            f"?node_id={NODE_ID}"
            f"&start=2026-05-25T00:00:00Z&end=2026-06-01T00:00:00Z"
            f"&resolution=hourly",
            headers=self.headers, name="/metrics/starlink [7d hourly]",
        )

    @task(2)
    def query_summary(self):
        self.client.get(
            f"/api/v1/metrics/starlink/summary"
            f"?node_id={NODE_ID}&start=2026-05-25T00:00:00Z&end=2026-06-01T00:00:00Z",
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
