"""
GET /health (docs/07_API_REST.md §"Tag: system"): público, siempre HTTP 200,
el estado real va en el body -- ni Docker healthcheck ni Grafana deberían
tratar un componente caído como que el backend en sí está caído.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from .. import config, db

router = APIRouter(tags=["system"])


@router.get("/health", summary="Estado del sistema")
def health_check() -> dict:
    components = {
        "db_starlink_health": db.ping(db.starlink_engine()),
        "mqtt_broker": db.ping_mqtt_broker(config.MQTT_HOST, config.MQTT_PORT),
        # meteo_data es dominio de Fede (CLAUDE.md §1.1) -- todavía no hay
        # meteo_db real (src/consumer/db.py:MeteoDB es un stub), así que se
        # reporta "not_configured" en vez de fallar o inventar un "up" falso.
        # Ver docs/PROGRESS.md "Coordinación pendiente con Fede".
        "db_meteo_data": {"status": "not_configured"},
    }

    down = [c for c in components.values() if c.get("status") == "down"]
    overall = "healthy" if not down else "degraded"

    if components["db_starlink_health"]["status"] == "up":
        components["db_starlink_health"]["last_write"] = db.last_write(
            db.starlink_engine(), "network_metrics"
        )

    return {
        "status": overall,
        "version": config.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "components": components,
    }
