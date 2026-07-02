"""
Transform: bronze → silver para cotizaciones del dólar.

Lee el JSON crudo de MinIO bronze, lo normaliza con Polars,
y escribe Parquet a MinIO silver.
"""

import io
import json
import os
from datetime import date

import polars as pl
from dotenv import load_dotenv

from etl.infra import get_s3_client

load_dotenv()

BRONZE_BUCKET = os.getenv("MINIO_BUCKET", "tasajusta-bronze")
SILVER_BUCKET = os.getenv("MINIO_BUCKET", "tasajusta-bronze")


def read_bronze(s3_client, day: date) -> dict:
    """Lee el JSON crudo de la capa bronze."""
    key = f"dolar/{day.isoformat()}.json"
    resp = s3_client.get_object(Bucket=BRONZE_BUCKET, Key=key)
    return json.loads(resp["Body"].read())


def transform(raw: dict, day: date) -> pl.DataFrame:
    """
    Convierte el JSON crudo en un DataFrame limpio y tipado.

    Columnas de salida:
      - fecha        : Date   — el día de la cotización
      - casa         : String — identificador de la casa (blue, oficial, etc.)
      - nombre       : String — nombre legible
      - compra       : Float64
      - venta        : Float64
      - fetched_at   : String — timestamp UTC de la ingesta (del bronze)
    """
    registros = raw["data"]
    fetched_at = raw["fetched_at"]

    df = (
        pl.DataFrame(registros)
        .select([
            pl.lit(day).alias("fecha").cast(pl.Date),
            pl.col("casa").cast(pl.String),
            pl.col("nombre").cast(pl.String),
            pl.col("compra").cast(pl.Float64),
            pl.col("venta").cast(pl.Float64),
        ])
        .with_columns(
            pl.lit(fetched_at).alias("fetched_at")
        )
    )

    return df


def save_to_silver(df: pl.DataFrame, s3_client, day: date) -> str:
    """Escribe el DataFrame como Parquet en la capa silver."""
    key = f"silver/dolar/{day.isoformat()}.parquet"

    buffer = io.BytesIO()
    df.write_parquet(buffer)
    buffer.seek(0)

    s3_client.put_object(
        Bucket=SILVER_BUCKET,
        Key=key,
        Body=buffer.getvalue(),
        ContentType="application/octet-stream",
    )
    return key


def run(day: date | None = None) -> None:
    day = day or date.today()
    print(f"Transformando cotizaciones del {day}...")

    s3 = get_s3_client()

    raw = read_bronze(s3, day)
    print(f"  → Bronze leído: {len(raw['data'])} cotizaciones.")

    df = transform(raw, day)
    print(f"  → DataFrame transformado:\n{df}")

    key = save_to_silver(df, s3, day)
    print(f"  → Guardado en s3://{SILVER_BUCKET}/{key}")
    print("Listo.")


if __name__ == "__main__":
    run()
