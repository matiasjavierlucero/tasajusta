"""
Load: silver → Postgres para cotizaciones del dólar.

Lee el Parquet de MinIO silver y hace upsert en Postgres.
Idempotencia: ON CONFLICT (fecha, casa) DO UPDATE — correr dos veces no duplica.
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
CREATE TABLE IF NOT EXISTS cotizaciones_dolar (
    fecha       DATE         NOT NULL,
    casa        VARCHAR(50)  NOT NULL,
    nombre      VARCHAR(100),
    compra      FLOAT,
    venta       FLOAT,
    fetched_at  TIMESTAMPTZ,
    PRIMARY KEY (fecha, casa)
);
"""


UPSERT_SQL = """
INSERT INTO cotizaciones_dolar (fecha, casa, nombre, compra, venta, fetched_at)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (fecha, casa) DO UPDATE SET
    nombre     = EXCLUDED.nombre,
    compra     = EXCLUDED.compra,
    venta      = EXCLUDED.venta,
    fetched_at = EXCLUDED.fetched_at;
"""



def read_silver(s3_client, day: date) -> pl.DataFrame:
    """Lee el Parquet de la capa silver."""
    key = f"silver/dolar/{day.isoformat()}.parquet"
    resp = s3_client.get_object(Bucket=SILVER_BUCKET, Key=key)

    # Leemos el contenido en memoria y se lo pasamos a Polars
    buffer = io.BytesIO(resp["Body"].read())
    return pl.read_parquet(buffer)


def load_to_postgres(df: pl.DataFrame, conn) -> int:
    """Hace upsert de todas las filas del DataFrame en Postgres."""
    rows = [
        (
            row["fecha"],
            row["casa"],
            row["nombre"],
            row["compra"],
            row["venta"],
            row["fetched_at"],
        )
        for row in df.to_dicts()
    ]

    with conn.cursor() as cur:
        cur.execute(CREATE_TABLE_SQL)
        # executemany ejecuta el mismo SQL para cada fila — más eficiente que
        # un loop de execute() individuales para inserts en batch.
        cur.executemany(UPSERT_SQL, rows)
        conn.commit()

    return len(rows)


def run(day: date | None = None) -> None:
    day = day or date.today()
    print(f"Cargando cotizaciones del {day} a Postgres...")

    s3 = get_s3_client()
    df = read_silver(s3, day)
    print(f"  → {len(df)} filas leídas de silver.")

    with get_pg_connection() as conn:
        n = load_to_postgres(df, conn)

    print(f"  → {n} filas upserted en cotizaciones_dolar.")
    print("Listo.")


if __name__ == "__main__":
    run()
