"""
Acceso a starlink_health_db (ADR-10, ADR-11) vía ORM SQLAlchemy sobre TCP/IP
nativo de PostgreSQL (ADR-04: "CONSUMER -> BASE DE DATOS: ORM SQLAlchemy").

NetHealthDB inserta en la hypertable `network_metrics` (docs/06_DER.md §3.1,
`services/db/init_starlink_health.sql`) mapeada acá como `NetworkMetric`. El
INSERT usa ON CONFLICT DO NOTHING sobre la PK (time, node_id): QoS 1 (ADR-09)
garantiza *at-least-once*, no *exactly-once*, así que una reentrega del broker
no debe duplicar filas. `NetworkMetric` solo mapea columnas para el ORM: la
tabla/hypertable ya la crea `init_starlink_health.sql` (create_hypertable no es
algo que `Base.metadata.create_all()` sepa hacer), por eso nunca se llama
`create_all()` acá.

MeteoDB es un stub: el dominio ambiental es responsabilidad de Fede (CLAUDE.md
§1.1) y su esquema (`env_metrics`, PK time+node_id+source) todavía no tiene
implementación propia. Existe acá solo para que ConsumerRouter (router.py)
pueda enrutar por dominio sin acoplarse a si meteo ya está implementado o no.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Engine, Float, SmallInteger, String, create_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

logger = logging.getLogger("consumer")


class Base(DeclarativeBase):
    pass


class NetworkMetric(Base):
    """Mapeo ORM de `network_metrics` (docs/06_DER.md §3.1). Mismos nombres,
    tipos y nullability que `services/db/init_starlink_health.sql`."""

    __tablename__ = "network_metrics"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    node_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float)
    jitter_ms: Mapped[Optional[float]] = mapped_column(Float)
    packet_loss_pct: Mapped[Optional[float]] = mapped_column(Float)
    throughput_down_bps: Mapped[Optional[int]] = mapped_column(BigInteger)
    throughput_up_bps: Mapped[Optional[int]] = mapped_column(BigInteger)
    snr_db: Mapped[Optional[float]] = mapped_column(Float)
    is_obstructed: Mapped[Optional[bool]] = mapped_column(Boolean)
    satellite_count: Mapped[Optional[int]] = mapped_column(SmallInteger)
    schema_version: Mapped[str] = mapped_column(String(16))


class NetHealthDB:
    """Gateway de persistencia para starlink_health_db (network_metrics)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @classmethod
    def from_env(cls) -> "NetHealthDB":
        host = os.environ.get("STARLINK_DB_HOST", "localhost")
        port = os.environ.get("STARLINK_DB_PORT", "5432")
        name = os.environ.get("STARLINK_DB_NAME", "starlink_health")
        user = os.environ.get("STARLINK_DB_USER", "starlink_app")
        password = os.environ.get("STARLINK_DB_PASSWORD", "")
        dsn = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
        return cls(create_engine(dsn, pool_pre_ping=True))

    def insert(self, row: dict[str, Any]) -> None:
        """Inserta una fila en network_metrics. Deja propagar excepciones de
        conexión/DB: el llamador (router.py) decide qué hacer con el ACK MQTT
        (UT-03-05, RF-18, RNF-05)."""
        stmt = pg_insert(NetworkMetric).values(**row).on_conflict_do_nothing(
            index_elements=["time", "node_id"]
        )
        with Session(self._engine) as session:
            session.execute(stmt)
            session.commit()

    def dispose(self) -> None:
        self._engine.dispose()


class MeteoDB:
    """Stub del gateway de meteo_db. No persiste -- ver docstring del módulo."""

    def insert(self, row: dict[str, Any]) -> None:
        logger.warning(
            "meteo_db.insert no implementado todavía (módulo de Fede), "
            "mensaje descartado sin persistir",
            extra={"node_id": row.get("node_id")},
        )
