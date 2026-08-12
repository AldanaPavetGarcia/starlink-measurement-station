#!/usr/bin/env python3
"""
Monitoreo para CA-02 (docs/03_SRS.md §13): "Métricas reales de Starlink y
BME280 visibles en Grafana. Logs sin errores por 72 h" -- flujo end-to-end
con hardware real (Etapa 1).

72h no es algo que un test de pytest pueda "correr" (ni tendría sentido
bloquear una suite de CI por 3 días) -- este es un script standalone para
dejar corriendo en la RPi5 real durante la ventana de validación, no una
suite automatizada más. Poll periódico a `GET /health` del backend
(`docs/07_API_REST.md`), log de una línea JSON por chequeo, y un resumen
final PASS/FAIL contra el criterio de aceptación.

Solo usa la librería estándar a propósito: tiene que poder correr en la
RPi5 sin depender de que el entorno virtual del proyecto esté activado (es
un script operativo, no parte de la suite de tests).

Uso:
    python3 scripts/monitor_ca02.py --url http://localhost:8000 \
        --api-key <BACKEND_API_KEY del .env> --duration-hours 72 \
        --interval-minutes 5 --log ca02_monitor.jsonl

    # Corrida corta de prueba (no cuenta para CA-02, es solo para verificar
    # que el script funciona antes de dejarlo las 72h reales):
    python3 scripts/monitor_ca02.py --url http://localhost:8000 \
        --api-key <clave> --duration-hours 0.05 --interval-minutes 1
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone


def _check_once(url: str, api_key: str, timeout_s: float = 10.0) -> dict:
    """Un chequeo: GET /health y GET /metrics/starlink/latest (confirma no
    solo que el backend responde, sino que hay datos frescos -- CA-02 exige
    "métricas reales... visibles", no solo "el proceso sigue vivo")."""
    result = {"timestamp": datetime.now(timezone.utc).isoformat(), "ok": False}

    try:
        with urllib.request.urlopen(f"{url}/api/v1/health", timeout=timeout_s) as resp:
            health = json.loads(resp.read())
        result["health_status"] = health.get("status")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        result["error"] = f"GET /health falló: {exc}"
        return result

    try:
        req = urllib.request.Request(
            f"{url}/api/v1/metrics/starlink/latest", headers={"X-API-Key": api_key}
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            latest = json.loads(resp.read())
        data = latest.get("data") or []
        if not data:
            result["error"] = "GET /metrics/starlink/latest sin datos (data=[])"
            return result
        seconds_since_last = data[0].get("seconds_since_last")
        result["seconds_since_last_metric"] = seconds_since_last
        # Con polling cada 60s (default del extractor real), un gap > 10 min
        # (600s) indica que el extractor dejó de publicar -- no es solo
        # "el backend responde", es "la telemetría sigue fluyendo".
        if seconds_since_last is not None and seconds_since_last > 600:
            result["error"] = f"último dato hace {seconds_since_last}s (> 600s)"
            return result
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
        result["error"] = f"GET /metrics/starlink/latest falló: {exc}"
        return result

    result["ok"] = result["health_status"] in ("healthy", "degraded")
    if result["health_status"] == "degraded":
        result["warning"] = "status=degraded -- revisar qué componente está down"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", required=True, help="URL base del backend, ej. http://localhost:8000")
    parser.add_argument("--api-key", required=True, help="BACKEND_API_KEY del .env")
    parser.add_argument("--duration-hours", type=float, default=72.0)
    parser.add_argument("--interval-minutes", type=float, default=5.0)
    parser.add_argument("--log", default="ca02_monitor.jsonl", help="Archivo de log JSONL")
    args = parser.parse_args()

    deadline = time.monotonic() + args.duration_hours * 3600
    total_checks = 0
    failed_checks = 0

    print(f"CA-02: monitoreando {args.url} por {args.duration_hours}h, log en {args.log}")

    with open(args.log, "a", encoding="utf-8") as log_file:
        while time.monotonic() < deadline:
            check = _check_once(args.url, args.api_key)
            total_checks += 1
            if not check["ok"]:
                failed_checks += 1
                print(f"⚠️  {check['timestamp']}: {check.get('error', 'chequeo falló')}")
            log_file.write(json.dumps(check) + "\n")
            log_file.flush()
            time.sleep(args.interval_minutes * 60)

    print(f"\n=== Resumen CA-02 ===\nChequeos: {total_checks}  Fallidos: {failed_checks}")
    if failed_checks == 0:
        print("✅ PASS -- CA-02: sin errores durante la ventana de monitoreo")
        return 0
    print(f"❌ FAIL -- {failed_checks}/{total_checks} chequeos con error, revisar {args.log}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
