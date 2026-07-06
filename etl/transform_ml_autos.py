"""
Transform: bronze → silver para autos usados de MercadoLibre.

Reutiliza la función transform() de transform_autos.py — mismas limpiezas,
mismo schema de salida. Solo cambian los paths de S3.
"""

import io
import json
import os
from datetime import date

import polars as pl
from dotenv import load_dotenv

from etl.infra import get_s3_client
from etl.transform_autos import transform

load_dotenv()

BRONZE_BUCKET = os.getenv("MINIO_BUCKET", "tasajusta-bronze")
SILVER_BUCKET = os.getenv("MINIO_BUCKET", "tasajusta-bronze")


def read_bronze(s3_client, day: date) -> dict:
    key  = f"ml_autos_usados/{day.isoformat()}.json"
    resp = s3_client.get_object(Bucket=BRONZE_BUCKET, Key=key)
    return json.loads(resp["Body"].read())


def save_to_silver(df: pl.DataFrame, s3_client, day: date) -> str:
    key    = f"silver/ml_autos_usados/{day.isoformat()}.parquet"
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
    print(f"Transformando autos ML del {day}...")

    s3  = get_s3_client()
    raw = read_bronze(s3, day)
    print(f"  → Bronze leído: {len(raw['data'])} registros.")

    df = transform(raw, day)
    print(f"  → Después de limpiar: {len(df)} registros.")

    key = save_to_silver(df, s3, day)
    print(f"  → Guardado en s3://{SILVER_BUCKET}/{key}")
    print("Listo.")


if __name__ == "__main__":
    run()
