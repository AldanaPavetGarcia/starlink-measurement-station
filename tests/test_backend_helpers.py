"""
Tests de las funciones puras de src/backend/routers/metrics_starlink.py
(parsing de node_id, selección de resolución auto) -- no requieren DB.
"""

import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("BACKEND_API_KEY", "test-api-key-fase2")

import pytest  # noqa: E402

from backend.errors import ApiError  # noqa: E402
from backend.routers.metrics_starlink import _parse_node_ids, _resolve_resolution  # noqa: E402


def test_parse_node_ids_single():
    assert _parse_node_ids("lit-cordoba-01") == ["lit-cordoba-01"]


def test_parse_node_ids_csv_con_espacios():
    assert _parse_node_ids("lit-01, lit-02 ,lit-03") == ["lit-01", "lit-02", "lit-03"]


def test_parse_node_ids_vacio_lanza_api_error():
    with pytest.raises(ApiError):
        _parse_node_ids("   ")


@pytest.mark.parametrize("span_hours,expected", [
    (1, "raw"),
    (6, "raw"),
    (6.01, "hourly"),
    (24 * 29, "hourly"),
    (24 * 30, "hourly"),
    (24 * 31, "daily"),
])
def test_resolve_resolution_auto(span_hours, expected):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=span_hours)
    assert _resolve_resolution("auto", start, end) == expected


@pytest.mark.parametrize("explicit", ["raw", "hourly", "daily"])
def test_resolve_resolution_explicita_no_se_recalcula(explicit):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(days=365)  # rango que en 'auto' daría 'daily'
    assert _resolve_resolution(explicit, start, end) == explicit
