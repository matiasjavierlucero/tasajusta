"""
Load: silver → Supabase para vehículos usados de DeRuedas.

Dos estrategias según el entorno:
- SUPABASE_SERVICE_KEY presente → REST API (HTTPS 443). Funciona desde cualquier red,
  incluyendo GitHub Actions donde el puerto 5432 no es alcanzable via IPv4.
- Sin esa variable → Postgres directo (dev local con Docker).

Idempotencia: ON CONFLICT (cod) DO UPDATE / Prefer: resolution=merge-duplicates.
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
    scraped_at   TIMESTAMPTZ,
    segmento     SMALLINT      NOT NULL DEFAULT 0
);
"""

UPSERT_SQL = """
INSERT INTO autos_usados
    (cod, fecha, marca, modelo, condicion, provincia, precio_ars, anio, km, url, scraped_at, segmento)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (cod) DO UPDATE SET
    fecha      = EXCLUDED.fecha,
    precio_ars = EXCLUDED.precio_ars,
    km         = EXCLUDED.km,
    scraped_at = EXCLUDED.scraped_at,
    segmento   = EXCLUDED.segmento;
"""


def read_silver(s3_client, day: date) -> pl.DataFrame:
    key  = f"silver/autos_usados/{day.isoformat()}.parquet"
    resp = s3_client.get_object(Bucket=SILVER_BUCKET, Key=key)
    return pl.read_parquet(io.BytesIO(resp["Body"].read()))


def load_via_rest(df: pl.DataFrame) -> int:
    """Upsert usando la REST API de Supabase (PostgREST). No requiere conectividad Postgres."""
    rows = [
        {
            "cod":        row["cod"],
            "fecha":      str(row["fecha"]),
            "marca":      row["marca"],
            "modelo":     row["modelo"],
            "condicion":  row["condicion"],
            "provincia":  row["provincia"],
            "precio_ars": row["precio_ars"],
            "anio":       row["anio"],
            "km":         row["km"],
            "url":        row["url"],
            "scraped_at": row["scraped_at"],
            "segmento":   int(row["segmento"]),
        }
        for row in df.to_dicts()
    ]

    # Supabase REST API hace upsert via Prefer: resolution=merge-duplicates
    resp = httpx.post(
        f"{SUPABASE_URL}/rest/v1/autos_usados",
        headers={
            "apikey":        SUPABASE_SVC_KEY,
            "Authorization": f"Bearer {SUPABASE_SVC_KEY}",
            "Content-Type":  "application/json",
            "Prefer":        "resolution=merge-duplicates",
        },
        json=rows,
        timeout=60,
    )
    resp.raise_for_status()
    return len(rows)


def load_to_postgres(df: pl.DataFrame, conn) -> int:
    rows = [
        (
            row["cod"], row["fecha"], row["marca"], row["modelo"],
            row["condicion"], row["provincia"], row["precio_ars"],
            row["anio"], row["km"], row["url"], row["scraped_at"],
            int(row["segmento"]),
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
    print(f"Cargando vehículos usados del {day}...")

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

    print(f"  → {n} filas upserted en autos_usados.")
    print("Listo.")


if __name__ == "__main__":
    run()
