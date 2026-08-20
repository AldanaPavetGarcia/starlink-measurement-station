"""
Cliente hacia el servidor gRPC local de la antena (192.168.100.1:9200, ADR-01)
vía `grpcurl`, en vez de bindings grpcio compilados contra un .proto propio.

Por qué `grpcurl` y no grpcio+.proto: la antena expone server reflection
(confirmado en el relevamiento del 04/08/2026, `docs/PROGRESS.md` §Semana 10
-- `grpcurl -plaintext 192.168.100.1:9200 list` funciona sin compilar nada).
Usar reflection en runtime evita vendorizar/mantener los .proto propietarios
de Starlink en este repo (el mismo motivo por el que CLAUDE.md §1.1 marca
"ingeniería inversa de mecanismos internos propietarios" fuera de alcance --
acá no hace falta ni eso, el propio servidor describe su esquema). Es
literalmente el mismo método ya validado a mano contra la antena real.

Requiere el binario `grpcurl` en el PATH del contenedor (instalado en
Dockerfile.acquisition, ya estaba preinstalado en la RPi5 del LIT según el
relevamiento).
"""

from __future__ import annotations

import json
import subprocess

SERVICE_METHOD = "SpaceX.API.Device.Device/Handle"


class GrpcClientError(RuntimeError):
    """La llamada a la antena falló: no disponible, timeout, grpcurl ausente,
    o respuesta no parseable. El llamador decide cómo degradar (RF de
    CLAUDE.md §1.1: no debe tumbar el contenedor)."""


def _call(addr: str, request_body: dict, timeout_s: float = 5.0) -> dict:
    try:
        result = subprocess.run(
            [
                "grpcurl", "-plaintext", "-max-time", str(timeout_s),
                "-d", json.dumps(request_body), addr, SERVICE_METHOD,
            ],
            capture_output=True, text=True, timeout=timeout_s + 2,
        )
    except FileNotFoundError as exc:
        raise GrpcClientError("grpcurl no está instalado en el contenedor") from exc
    except subprocess.TimeoutExpired as exc:
        raise GrpcClientError(f"timeout llamando a la antena en {addr}") from exc

    if result.returncode != 0:
        raise GrpcClientError(
            f"grpcurl falló contra {addr} (rc={result.returncode}): {result.stderr.strip()}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GrpcClientError(f"respuesta de grpcurl no es JSON válido: {exc}") from exc


def get_status(addr: str) -> dict:
    """`dishGetStatus` completo: latencia, throughput, obstrucción, snr,
    alignmentStats -- ver `starlink_extractor.map_status`."""
    return _call(addr, {"get_status": {}})


def get_history(addr: str) -> dict:
    """`dishGetHistory`: series de latencia/drop rate + outages/eventLog --
    ver `starlink_extractor.derive_jitter_loss` / `count_handovers`."""
    return _call(addr, {"get_history": {}})


def get_diagnostics(addr: str) -> dict:
    """`dishGetDiagnostics`: incluye `alerts.obstructed`, el único flag de
    estado *actual* de obstrucción que expone el firmware -- a diferencia de
    `obstructionStats.fractionObstructed` en `get_status`, que es una
    fracción acumulada desde que arrancó la ventana de validación (horas/
    días), no el estado ahora mismo. Ver `starlink_extractor.map_status`."""
    return _call(addr, {"get_diagnostics": {}})
