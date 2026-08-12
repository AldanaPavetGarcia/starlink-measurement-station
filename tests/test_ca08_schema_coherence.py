"""
CA-08 (docs/03_SRS.md §13, ADR-01): "interfaces documentadas y consistentes
con el código en producción" -- automatiza el chequeo estructural entre el
esquema del paquete MQTT (`StarlinkMetrics`, ADR-01) y las columnas reales
de `network_metrics` (`services/db/init_starlink_health.sql`).

E2E-CA08 (docs/08_Plan_QA.md) captura paquetes reales de un broker en vivo
y los compara contra la DB -- válido, pero requiere la pila completa
corriendo. Este test cubre la misma clase de drift (un campo que existe en
uno de los dos lados y no en el otro) sin necesitar Docker: parsea el SQL de
`CREATE TABLE network_metrics` como texto y lo compara contra
`StarlinkMetrics.model_fields`. No reemplaza a E2E-CA08 (no valida tipos SQL
reales, CHECK constraints, ni que el consumer efectivamente mapee cada
campo -- ver `src/consumer/router.py:starlink_row` para eso), pero atrapa en
segundos el error más común: agregar/renombrar un campo en un solo lado.
"""

import re
from pathlib import Path

from mock_starlink.schema import StarlinkMetrics

SQL_PATH = Path(__file__).parent.parent / "services" / "db" / "init_starlink_health.sql"

# Campos del envelope (StarlinkPayloadIn, no de StarlinkMetrics) que sí
# tienen columna propia en network_metrics -- se excluyen de la comparación
# 1:1 de StarlinkMetrics.model_fields porque viven en otro modelo Pydantic.
ENVELOPE_COLUMNS = {"time", "node_id", "schema_version"}


def _parse_network_metrics_columns() -> set[str]:
    """Extrae los nombres de columna del bloque `CREATE TABLE
    network_metrics (...)` de services/db/init_starlink_health.sql -- una
    columna por línea, primer identificador de cada línea hasta la primera
    palabra clave estructural (PRIMARY KEY / CONSTRAINT)."""
    sql = SQL_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"CREATE TABLE IF NOT EXISTS network_metrics \((.*?)\n\);",
        sql, re.DOTALL,
    )
    assert match, f"no se encontró el bloque CREATE TABLE network_metrics en {SQL_PATH}"

    columns = set()
    for line in match.group(1).splitlines():
        line = line.strip().rstrip(",")
        if not line or line.startswith("--"):
            continue
        first_word = line.split()[0]
        # A partir de PRIMARY KEY / CONSTRAINT, el resto del bloque son
        # constraints (incluida la línea CHECK(...) suelta que sigue a cada
        # CONSTRAINT) -- no columnas. Corta el parseo ahí, no solo esa línea.
        if first_word.upper() in ("PRIMARY", "CONSTRAINT", "UNIQUE", "FOREIGN", "CHECK"):
            break
        columns.add(first_word)
    return columns


def test_db_tiene_una_columna_por_cada_campo_de_starlinkmetrics():
    db_columns = _parse_network_metrics_columns()
    schema_fields = set(StarlinkMetrics.model_fields.keys())

    missing_in_db = schema_fields - db_columns
    assert not missing_in_db, (
        f"campo(s) de StarlinkMetrics sin columna en network_metrics: {missing_in_db} "
        f"-- actualizar services/db/init_starlink_health.sql (y docs/06_DER.md)"
    )


def test_starlinkmetrics_cubre_todas_las_columnas_de_metricas_de_la_db():
    """La otra dirección: una columna de network_metrics que no sea del
    envelope y que StarlinkMetrics no declare es, con la misma probabilidad,
    un campo que se sacó del schema.py y se olvidó sacar de la DB (o
    viceversa) -- ambas direcciones importan para CA-08."""
    db_columns = _parse_network_metrics_columns()
    schema_fields = set(StarlinkMetrics.model_fields.keys())

    extra_in_db = db_columns - schema_fields - ENVELOPE_COLUMNS
    assert not extra_in_db, (
        f"columna(s) en network_metrics sin campo correspondiente en StarlinkMetrics: "
        f"{extra_in_db} -- ¿falta agregarlas a src/mock_starlink/schema.py, o sobran en la DB?"
    )


def test_starlink_row_mapea_todos_los_campos_de_metrics():
    """`starlink_row` (src/consumer/router.py) es el punto real donde
    metrics.<campo> -> fila de INSERT. Si un campo nuevo se agrega a
    StarlinkMetrics pero no a starlink_row, el consumer lo descartaría en
    silencio -- se ejercita con un payload de ejemplo, no solo se inspecciona
    el código fuente como texto (más robusto ante refactors)."""
    from datetime import datetime, timezone

    from consumer.router import starlink_row
    from mock_starlink.schema import SCHEMA_VERSION, StarlinkPayloadIn

    ejemplo = {f: None for f in StarlinkMetrics.model_fields}
    payload = StarlinkPayloadIn.model_validate({
        "schema_version": SCHEMA_VERSION,
        "node_id": "lit-test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": ejemplo,
    })

    row = starlink_row(payload)
    schema_fields = set(StarlinkMetrics.model_fields.keys())
    missing_in_row = schema_fields - set(row.keys())
    assert not missing_in_row, (
        f"campo(s) de StarlinkMetrics que starlink_row no mapea a la fila de INSERT: "
        f"{missing_in_row} -- el consumer los descartaría en silencio"
    )
