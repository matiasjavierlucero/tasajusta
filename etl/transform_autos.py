"""
Transform: bronze → silver para autos usados de DeRuedas.

Lee el JSON crudo de MinIO bronze (autos_usados/YYYY-MM-DD.json),
limpia y tipea con Polars, y escribe Parquet a silver.

Limpieza aplicada:
  - precio_ars = 0 → nulo (datos inválidos del sitio)
  - anio fuera de rango [1990, año actual] → nulo
  - km = 0 para año < 2024 → nulo (sospechoso)
  - duplicados por (marca, modelo, cod) → se elimina la primera ocurrencia
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

ANIO_MIN = 1990



def read_bronze(s3_client, day: date) -> dict:
    """Lee el JSON crudo de la capa bronze."""
    key = f"autos_usados/{day.isoformat()}.json"
    resp = s3_client.get_object(Bucket=BRONZE_BUCKET, Key=key)
    return json.loads(resp["Body"].read())


def transform(raw: dict, day: date) -> pl.DataFrame:
    """
    Convierte el JSON crudo en un DataFrame limpio y tipado.

    Columnas de salida:
      - fecha         : Date    — día del scraping
      - marca         : String
      - modelo        : String
      - condicion     : String  — "Usado", "Nuevo", etc.
      - provincia     : String
      - cod           : String  — ID único del listing en DeRuedas
      - precio_ars    : Int64   — null si era 0 (publicación sin precio)
      - anio          : Int32   — null si fuera de rango [ANIO_MIN, hoy]
      - km            : Int64   — null si 0 y el auto no es 0km
      - url           : String
      - scraped_at    : String  — timestamp UTC del scraping (del bronze)
    """
    registros = raw["data"]
    scraped_at = raw["scraped_at"]
    anio_max = day.year

    df = (
        pl.DataFrame(registros)
        .select([
            pl.lit(day).alias("fecha").cast(pl.Date),
            pl.col("marca").cast(pl.String),
            pl.col("modelo").cast(pl.String),
            pl.col("condicion").cast(pl.String),
            pl.col("provincia").cast(pl.String),
            pl.col("cod").cast(pl.String),
            pl.col("precio_ars").cast(pl.Int64),
            pl.col("anio").cast(pl.Int32),
            pl.col("km").cast(pl.Int64),
            pl.col("url").cast(pl.String),
        ])
        .with_columns(pl.lit(scraped_at).alias("scraped_at"))
        # precio = 0 → null (publicación sin precio cargado)
        .with_columns(
            pl.when(pl.col("precio_ars") == 0)
            .then(None)
            .otherwise(pl.col("precio_ars"))
            .alias("precio_ars")
        )
        # anio fuera de rango → null
        .with_columns(
            pl.when(
                (pl.col("anio") < ANIO_MIN) | (pl.col("anio") > anio_max)
            )
            .then(None)
            .otherwise(pl.col("anio"))
            .alias("anio")
        )
        # km = 0 en un auto que no es 0km → null
        .with_columns(
            pl.when(
                (pl.col("km") == 0) & (pl.col("condicion") != "Nuevo")
            )
            .then(None)
            .otherwise(pl.col("km"))
            .alias("km")
        )
        # eliminar duplicados por cod (mismo auto, duplicado en múltiples marcas)
        .unique(subset=["cod"], keep="first")
    )

    return df


def save_to_silver(df: pl.DataFrame, s3_client, day: date) -> str:
    """Escribe el DataFrame como Parquet en la capa silver."""
    key = f"silver/autos_usados/{day.isoformat()}.parquet"

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
    print(f"Transformando autos usados del {day}...")

    s3 = get_s3_client()

    raw = read_bronze(s3, day)
    total_bronze = len(raw["data"])
    print(f"  → Bronze leído: {total_bronze} registros.")

    df = transform(raw, day)
    print(f"  → Después de limpiar: {len(df)} registros.")
    print(f"  → Nulos precio_ars:  {df['precio_ars'].null_count()}")
    print(f"  → Nulos anio:        {df['anio'].null_count()}")
    print(f"  → Nulos km:          {df['km'].null_count()}")
    print(f"  → Schema:\n{df.schema}")

    key = save_to_silver(df, s3, day)
    print(f"  → Guardado en s3://{SILVER_BUCKET}/{key}")
    print("Listo.")


if __name__ == "__main__":
    run()
