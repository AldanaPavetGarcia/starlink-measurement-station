"""
Tests de src/common/: logging JSON compartido (extraído de
mock_starlink/__main__.py en semana 9 cuando el consumer lo duplicó sin
ninguna diferencia real, ver docs/PROGRESS.md) y reconexión MQTT con backoff
exponencial.
"""

import json
import logging

import pytest

from common.logging import JsonLogFormatter, setup_logging
from common.mqtt import connect_with_retry, set_credentials_if_present


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


def test_json_log_formatter_ignora_claves_no_promovidas():
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="consumer", level=logging.WARNING, pathname=__file__, lineno=1,
        msg="fallo transitorio", args=(), exc_info=None,
    )
    record.algo_no_promovido = "no debería aparecer"
    parsed = json.loads(formatter.format(record))
    assert "algo_no_promovido" not in parsed


def test_setup_logging_devuelve_logger_nombrado_con_handler_json():
    logger = setup_logging("test-service-xyz")
    assert logger.name == "test-service-xyz"
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0].formatter, JsonLogFormatter)


class _FakeMqttClient:
    """Doble mínimo de paho.mqtt.client.Client: falla connect() un número
    fijo de veces antes de aceptar, sin dormir realmente entre reintentos."""

    def __init__(self, fail_times: int):
        self.fail_times = fail_times
        self.attempts = 0
        self.connected_kwargs = None

        self.credentials = None

    def username_pw_set(self, username, password):
        self.credentials = (username, password)

    def connect(self, host, port, keepalive=60, **kwargs):
        self.attempts += 1
        if self.attempts <= self.fail_times:
            raise OSError("connection refused (fake)")
        self.connected_kwargs = kwargs


def test_connect_with_retry_reintenta_hasta_conectar(monkeypatch, caplog):
    monkeypatch.setattr("common.mqtt.time.sleep", lambda _: None)  # no dormir de verdad
    client = _FakeMqttClient(fail_times=3)
    logger = logging.getLogger("test-connect-retry")

    with caplog.at_level("WARNING"):
        connect_with_retry(client, "broker-test", 1883, logger)

    assert client.attempts == 4
    assert sum(1 for r in caplog.records if r.levelname == "WARNING") == 3


def test_connect_with_retry_pasa_connect_kwargs():
    """El consumer necesita pasar clean_start/properties (sesión persistente,
    ADR-09) sin que connect_with_retry tenga que conocer ese detalle."""
    monkeypatch_sleep = pytest.MonkeyPatch()
    monkeypatch_sleep.setattr("common.mqtt.time.sleep", lambda _: None)
    try:
        client = _FakeMqttClient(fail_times=0)
        logger = logging.getLogger("test-connect-retry-kwargs")
        connect_with_retry(client, "broker-test", 1883, logger, clean_start=False, properties="fake-props")
        assert client.connected_kwargs == {"clean_start": False, "properties": "fake-props"}
    finally:
        monkeypatch_sleep.undo()


def test_set_credentials_if_present_con_ambas_variables(monkeypatch):
    """El broker local (ADR-04/ADR-14) es anónimo -- esto solo importa para
    el bridge a la VM de cátedra (ADR-20), donde sí hace falta auth."""
    monkeypatch.setenv("MQTT_USERNAME", "rpi5-bridge")
    monkeypatch.setenv("MQTT_PASSWORD", "secreto")
    client = _FakeMqttClient(fail_times=0)
    assert set_credentials_if_present(client) is True
    assert client.credentials == ("rpi5-bridge", "secreto")


def test_set_credentials_if_present_sin_variables_no_llama_nada(monkeypatch):
    monkeypatch.delenv("MQTT_USERNAME", raising=False)
    monkeypatch.delenv("MQTT_PASSWORD", raising=False)
    client = _FakeMqttClient(fail_times=0)
    assert set_credentials_if_present(client) is False
    assert client.credentials is None


def test_set_credentials_if_present_solo_una_variable_no_alcanza(monkeypatch):
    """No tiene sentido intentar autenticar con solo la mitad de las
    credenciales -- se deja conectar anónimo, como si no hubiera nada."""
    monkeypatch.setenv("MQTT_USERNAME", "rpi5-bridge")
    monkeypatch.delenv("MQTT_PASSWORD", raising=False)
    client = _FakeMqttClient(fail_times=0)
    assert set_credentials_if_present(client) is False
    assert client.credentials is None
