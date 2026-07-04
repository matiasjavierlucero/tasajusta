"""
Load: silver → Supabase para cotizaciones del dólar.

Dos estrategias según el entorno:
- SUPABASE_SERVICE_KEY presente → REST API (HTTPS 443). Funciona desde cualquier red,
  incluyendo GitHub Actions donde el puerto 5432 no es alcanzable via IPv4.
- Sin esa variable → Postgres directo (dev local con Docker).

Idempotencia: ON CONFLICT (fecha, casa) DO UPDATE / Prefer: resolution=merge-duplicates.
"""

import io
import os
from datetime import date

import httpx
import polars as pl
from dotenv import load_dotenv

from etl.infra import get_pg_connection, get_s3_client

load_dotenv()

SILVER_BUCKET    = os.getenv("MINIO_BUCKET", "tasajusta-bronze")
SUPABASE_URL     = os.getenv("SUPABASE_URL")
SUPABASE_SVC_KEY = os.getenv("SUPABASE_SERVICE_KEY")


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
    key    = f"silver/dolar/{day.isoformat()}.parquet"
    resp   = s3_client.get_object(Bucket=SILVER_BUCKET, Key=key)
    buffer = io.BytesIO(resp["Body"].read())
    return pl.read_parquet(buffer)


def load_via_rest(df: pl.DataFrame) -> int:
    """Upsert usando la REST API de Supabase (PostgREST). No requiere conectividad Postgres."""
    rows = [
        {
            "fecha":      str(row["fecha"]),
            "casa":       row["casa"],
            "nombre":     row["nombre"],
            "compra":     row["compra"],
            "venta":      row["venta"],
            "fetched_at": row["fetched_at"],
        }
        for row in df.to_dicts()
    ]

    # [ENTREVISTA] Prefer: resolution=merge-duplicates → PostgREST traduce esto
    # a ON CONFLICT DO UPDATE. Sin ese header, un registro duplicado devuelve 409.
    resp = httpx.post(
        f"{SUPABASE_URL}/rest/v1/cotizaciones_dolar",
        headers={
            "apikey":        SUPABASE_SVC_KEY,
            "Authorization": f"Bearer {SUPABASE_SVC_KEY}",
            "Content-Type":  "application/json",
            "Prefer":        "resolution=merge-duplicates",
        },
        json=rows,
        timeout=30,
    )
    resp.raise_for_status()
    return len(rows)


def load_to_postgres(df: pl.DataFrame, conn) -> int:
    rows = [
        (row["fecha"], row["casa"], row["nombre"], row["compra"], row["venta"], row["fetched_at"])
        for row in df.to_dicts()
    ]
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLE_SQL)
        cur.executemany(UPSERT_SQL, rows)
        conn.commit()
    return len(rows)


def run(day: date | None = None) -> None:
    day = day or date.today()
    print(f"Cargando cotizaciones del {day}...")

    s3 = get_s3_client()
    df = read_silver(s3, day)
    print(f"  → {len(df)} filas leídas de silver.")

    if SUPABASE_URL and SUPABASE_SVC_KEY:
        print("  → Usando Supabase REST API.")
        n = load_via_rest(df)
    else:
        print("  → Usando Postgres directo (dev local).")
        with get_pg_connection() as conn:
            n = load_to_postgres(df, conn)

    print(f"  → {n} filas upserted en cotizaciones_dolar.")
    print("Listo.")


if __name__ == "__main__":
    run()
