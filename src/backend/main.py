"""
App FastAPI del backend (semana 9, docs/07_API_REST.md). Entrypoint para
`uvicorn backend.main:app` (Dockerfile.backend).

Alcance de este módulo: /health, /metrics/starlink*, /nodes*,
/ingest/starlink. /metrics/env* y /ingest/env son dominio de Fede -- no
montados acá todavía (ver __init__.py y docs/PROGRESS.md).
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config
from .errors import (
    ApiError,
    api_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from .routers import health, ingest, metrics_starlink, nodes

app = FastAPI(
    title="Starlink Measurement Station API",
    version=config.VERSION,
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(health.router, prefix="/api/v1")
app.include_router(metrics_starlink.router, prefix="/api/v1")
app.include_router(nodes.router, prefix="/api/v1")
app.include_router(ingest.router, prefix="/api/v1")
