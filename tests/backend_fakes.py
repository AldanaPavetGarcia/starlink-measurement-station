"""
Dobles mínimos del Engine/Connection de SQLAlchemy Core, para testear los
routers del backend (metrics_starlink.py, nodes.py) sin una Postgres real.
Cubre solo la superficie que el código de backend/db.py realmente usa
(`.connect()` como context manager, `.execute(query, params)` con
`.mappings().all()/.first()`, `.fetchall()`) -- no un mock genérico de
SQLAlchemy.

No reemplaza a la suite de integración (Fase 4, tests/integration/, IT-03)
que sí corre contra TimescaleDB/PostgreSQL real -- esto valida la lógica
Python de los routers (armado de queries, ramas de error, forma de la
respuesta), no que el SQL en sí sea válido contra Postgres.
"""

from __future__ import annotations

from typing import Any


class _FakeRow:
    """Soporta tanto acceso posicional (`row[0]`, como un Row real de
    SQLAlchemy) como acceso por clave (`row["campo"]`, como un `.mappings()`
    row) -- el código de backend/db.py y backend/routers/ usa ambos estilos
    según el caso, y `dict(row)` también tiene que funcionar (requiere
    `.keys()` + `__getitem__`)."""

    def __init__(self, data: dict):
        self._data = data
        self._order = list(data.keys())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._data[self._order[key]]
        return self._data[key]

    def keys(self):
        return self._data.keys()


class _FakeResult:
    def __init__(self, rows: list[dict]):
        self._rows = [_FakeRow(r) for r in rows]

    def mappings(self) -> "_FakeResult":
        return self

    def all(self) -> list[_FakeRow]:
        return list(self._rows)

    def first(self) -> _FakeRow | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[tuple]:
        return [tuple(r._data.values()) for r in self._rows]


class ScriptedConnection:
    """Devuelve, en orden, una lista de resultados pre-armados -- un elemento
    por cada `.execute()` que el código bajo test vaya a hacer. Falla fuerte
    (IndexError) si el código ejecuta más queries de las scripteadas: mejor
    que devolver silenciosamente una lista vacía y esconder un bug."""

    def __init__(self, scripted_rows: list[list[dict]]):
        self._scripted = list(scripted_rows)
        self.executed: list[tuple[str, dict]] = []

    def execute(self, query, params: dict | None = None) -> _FakeResult:
        self.executed.append((str(query), params or {}))
        rows = self._scripted.pop(0)
        return _FakeResult(rows)

    def __enter__(self) -> "ScriptedConnection":
        return self

    def __exit__(self, *exc) -> None:
        return None


class FakeEngine:
    def __init__(self, scripted_rows: list[list[dict]]):
        self._conn = ScriptedConnection(scripted_rows)

    def connect(self) -> ScriptedConnection:
        return self._conn
