"""
Tests de las piezas puras de src/mock_starlink/__main__.py (logging JSON,
payload de status LWT). La integración real contra un broker MQTT se probó
manualmente (docker compose --profile mocks up) — ver docs/PROGRESS.md.
"""

import json
import logging

from mock_starlink.__main__ import JsonLogFormatter, _status_payload


def test_status_payload_shape():
    payload = json.loads(_status_payload("lit-cordoba-01", "offline"))
    assert payload == {
        "node_id": "lit-cordoba-01",
        "source": "starlink_mock",
        "status": "offline",
    }


def test_json_log_formatter_emite_json_valido_con_campos_base():
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="mock_starlink", level=logging.INFO, pathname=__file__, lineno=1,
        msg="conectado al broker", args=(), exc_info=None,
    )
    record.node_id = "lit-cordoba-01"
    line = formatter.format(record)
    parsed = json.loads(line)
    assert parsed["level"] == "INFO"
    assert parsed["msg"] == "conectado al broker"
    assert parsed["node_id"] == "lit-cordoba-01"
