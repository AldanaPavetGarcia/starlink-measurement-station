"""
Auth por API Key en header (docs/07_API_REST.md §2.1). GET /health es el
único endpoint público -- no depende de `require_api_key`.
"""

from fastapi import Security
from fastapi.security.api_key import APIKeyHeader

from . import config
from .errors import ApiError

API_KEY_NAME = "X-API-Key"
_api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def require_api_key(api_key: str = Security(_api_key_header)) -> str:
    """Dependency inyectable en todos los endpoints protegidos (§2.1)."""
    if not config.API_KEY:
        # Falla ruidosa y explícita: correr sin BACKEND_API_KEY configurada
        # dejaría toda la API abierta en silencio -- peor que romper el arranque.
        raise RuntimeError("BACKEND_API_KEY no configurada en variables de entorno")
    if api_key != config.API_KEY:
        raise ApiError(401, "AUTH_FAILED", "API key inválida o ausente")
    return api_key
