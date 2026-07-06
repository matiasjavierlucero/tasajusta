"""
Transform: bronze → silver para autos usados de Kavak.

Lee kavak_autos/YYYY-MM-DD.json, aplica la misma limpieza que DeRuedas
(precio 0 → null, año fuera de rango → null, km 0 en no-nuevo → null),
y escribe Parquet a silver/kavak_autos/.
"""

import io
import json
import os
from datetime import date

from dotenv import load_dotenv

from etl.infra import get_s3_client
from etl.transform_autos import transform

load_dotenv()

BRONZE_BUCKET = os.getenv("MINIO_BUCKET", "tasajusta-bronze")
SILVER_BUCKET = os.getenv("MINIO_BUCKET", "tasajusta-bronze")


def read_bronze(s3_client, day: date) -> dict:
    key  = f"kavak_autos/{day.isoformat()}.json"
    resp = s3_client.get_object(Bucket=BRONZE_BUCKET, Key=key)
    return json.loads(resp["Body"].read())


def save_to_silver(df, s3_client, day: date) -> str:
    key    = f"silver/kavak_autos/{day.isoformat()}.parquet"
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
    print(f"Transformando Kavak del {day}...")

    s3  = get_s3_client()
    raw = read_bronze(s3, day)
    print(f"  → Bronze leído: {len(raw['data'])} registros.")

    df = transform(raw, day)
    print(f"  → Después de limpiar: {len(df)} registros.")
    print(f"  → Nulos precio_ars: {df['precio_ars'].null_count()}")
    print(f"  → Nulos anio:       {df['anio'].null_count()}")
    print(f"  → Nulos km:         {df['km'].null_count()}")

    key = save_to_silver(df, s3, day)
    print(f"  → Guardado en s3://{SILVER_BUCKET}/{key}")
    print("Listo.")


if __name__ == "__main__":
    run()
