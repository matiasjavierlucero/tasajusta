"""
Load: silver → Postgres para autos usados de DeRuedas.

Lee el Parquet de MinIO silver y hace upsert en Postgres.
Idempotencia: ON CONFLICT (cod) DO UPDATE — correr dos veces no duplica.
"""

import io
import os
from datetime import date

import polars as pl
from dotenv import load_dotenv

from etl.infra import get_pg_connection, get_s3_client

load_dotenv()

SILVER_BUCKET = os.getenv("MINIO_BUCKET", "tasajusta-bronze")


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS autos_usados (
    cod          VARCHAR(20)   PRIMARY KEY,
    fecha        DATE          NOT NULL,
    marca        VARCHAR(50)   NOT NULL,
    modelo       VARCHAR(100)  NOT NULL,
    condicion    VARCHAR(30),
    provincia    VARCHAR(100),
    precio_ars   BIGINT,
    anio         SMALLINT,
    km           BIGINT,
    url          TEXT,
    scraped_at   TIMESTAMPTZ
);
"""

UPSERT_SQL = """
INSERT INTO autos_usados
    (cod, fecha, marca, modelo, condicion, provincia, precio_ars, anio, km, url, scraped_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (cod) DO UPDATE SET
    fecha      = EXCLUDED.fecha,
    precio_ars = EXCLUDED.precio_ars,
    km         = EXCLUDED.km,
    scraped_at = EXCLUDED.scraped_at;
"""


def read_silver(s3_client, day: date) -> pl.DataFrame:
    """Lee el Parquet de la capa silver."""
    key = f"silver/autos_usados/{day.isoformat()}.parquet"
    resp = s3_client.get_object(Bucket=SILVER_BUCKET, Key=key)
    return pl.read_parquet(io.BytesIO(resp["Body"].read()))


def load_to_postgres(df: pl.DataFrame, conn) -> int:
    """Hace upsert de todas las filas del DataFrame en Postgres."""
    rows = [
        (
            row["cod"],
            row["fecha"],
            row["marca"],
            row["modelo"],
            row["condicion"],
            row["provincia"],
            row["precio_ars"],
            row["anio"],
            row["km"],
            row["url"],
            row["scraped_at"],
        )
        for row in df.to_dicts()
    ]

    with conn.cursor() as cur:
        cur.execute(CREATE_TABLE_SQL)
        cur.executemany(UPSERT_SQL, rows)
        conn.commit()

    return len(rows)


def run(day: date | None = None) -> None:
    day = day or date.today()
    print(f"Cargando autos usados del {day} a Postgres...")

    s3 = get_s3_client()
    df = read_silver(s3, day)
    print(f"  → {len(df)} filas leídas de silver.")

    with get_pg_connection() as conn:
        n = load_to_postgres(df, conn)

    print(f"  → {n} filas upserted en autos_usados.")
    print("Listo.")


if __name__ == "__main__":
    run()
