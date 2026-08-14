"""
Envelope de error único (docs/07_API_REST.md §3.2/§3.3) para todos los
endpoints. `ApiError` es la excepción que levantan los routers; el
exception_handler registrado en main.py la traduce al JSON estándar
{status, code, detail, timestamp, path}.
"""

from datetime import datetime, timezone

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class ApiError(HTTPException):
    """Excepción con `code` (catálogo de docs/07_API_REST.md §3.3), además del
    HTTP status. Se levanta en los routers; el handler global la envuelve."""

    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


def _error_body(code: str, detail: str, path: str) -> dict:
    return {
        "status": "error",
        "code": code,
        "detail": detail,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "path": path,
    }


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, str(exc.detail), request.url.path),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Cubre HTTPException "genéricas" (ej. 404 de rutas inexistentes) que no
    pasaron por ApiError, para que TODO error respete el mismo envelope."""
    code = "AUTH_FAILED" if exc.status_code == status.HTTP_401_UNAUTHORIZED else "INTERNAL_ERROR"
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(code, detail, request.url.path),
    )


def _format_validation_errors(exc: Exception) -> str:
    """Arma un `detail` legible a partir de `exc.errors()` (lista de dicts
    {loc, msg, type} de Pydantic/FastAPI). `str(exc)` se evitó a propósito:
    en FastAPI 0.141/Starlette 1.6 incluye el path del archivo y número de
    línea del handler dentro del contenedor (ver docs/PROGRESS.md, hallazgo
    12/8/2026) -- una fuga de detalle interno que no corresponde exponer en
    una respuesta pública (ADR-14, postura Zero Trust)."""
    errors = getattr(exc, "errors", None)
    if not callable(errors):
        return "parámetros de query inválidos"
    parts = []
    for e in errors():
        loc = ".".join(str(part) for part in e.get("loc", ()) if part != "query")
        parts.append(f"{loc}: {e.get('msg', 'inválido')}" if loc else e.get("msg", "inválido"))
    return "; ".join(parts) if parts else "parámetros de query inválidos"


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """RequestValidationError de FastAPI (query params faltantes/mal
    tipados) -> VALIDATION_ERROR, no el 422 default de FastAPI."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=_error_body("VALIDATION_ERROR", _format_validation_errors(exc), request.url.path),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body("INTERNAL_ERROR", "error interno del backend", request.url.path),
    )
