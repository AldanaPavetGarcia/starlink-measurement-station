"""
Tests unitarios de src/consumer/db.py: construcción del DSN desde variables de
entorno (ADR-12 -- config de conexión siempre en .env, nunca hardcodeada).
"""

from consumer.db import NetHealthDB


def test_from_env_builds_postgresql_dsn(monkeypatch):
    monkeypatch.setenv("STARLINK_DB_HOST", "db-test-host")
    monkeypatch.setenv("STARLINK_DB_PORT", "5555")
    monkeypatch.setenv("STARLINK_DB_NAME", "starlink_health_test")
    monkeypatch.setenv("STARLINK_DB_USER", "test_user")
    monkeypatch.setenv("STARLINK_DB_PASSWORD", "test_pw")

    db = NetHealthDB.from_env()
    url = db._engine.url

    assert url.drivername == "postgresql+psycopg2"
    assert url.host == "db-test-host"
    assert url.port == 5555
    assert url.database == "starlink_health_test"
    assert url.username == "test_user"
    assert url.password == "test_pw"
    db.dispose()


def test_from_env_defaults_when_unset(monkeypatch):
    for var in ("STARLINK_DB_HOST", "STARLINK_DB_PORT", "STARLINK_DB_NAME", "STARLINK_DB_USER", "STARLINK_DB_PASSWORD"):
        monkeypatch.delenv(var, raising=False)

    db = NetHealthDB.from_env()
    url = db._engine.url

    assert url.host == "localhost"
    assert url.port == 5432
    assert url.database == "starlink_health"
    assert url.username == "starlink_app"
    db.dispose()
