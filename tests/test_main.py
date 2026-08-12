"""
Tests de las piezas puras de src/mock_starlink/__main__.py (payload de status
LWT). El logging JSON compartido se probó en tests/test_common.py desde que
se extrajo a src/common/logging.py (semana 9, ver docs/PROGRESS.md). La
integración real contra un broker MQTT se probó manualmente
(docker compose --profile mocks up) — ver docs/PROGRESS.md.
"""

import json

from mock_starlink.__main__ import _status_payload


def test_status_payload_shape():
    payload = json.loads(_status_payload("lit-cordoba-01", "offline"))
    assert payload == {
        "node_id": "lit-cordoba-01",
        "source": "starlink_mock",
        "status": "offline",
    }
