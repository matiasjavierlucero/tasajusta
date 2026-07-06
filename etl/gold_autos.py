"""
Gold: silver → gold para autos usados.

Feature engineering para ML:
  - antiguedad     : año del scraping − anio
  - km_valido      : True si km real, False si era proxy (km = 1)
  - km             : imputado con mediana por marca cuando km_valido = False (D1-A)
  - km_por_anio    : km / max(antiguedad, 1)
  - dolar_blue     : cotización blue de venta del día de scraping

Target: precio_ars
"""

import io
import os
from datetime import date

import httpx
import polars as pl
from dotenv import load_dotenv

from etl.infra import get_s3_client

load_dotenv()

SILVER_BUCKET  = os.getenv("MINIO_BUCKET", "tasajusta-bronze")
GOLD_BUCKET    = os.getenv("MINIO_BUCKET", "tasajusta-bronze")
SUPABASE_URL   = os.getenv("SUPABASE_URL")
SUPABASE_KEY   = os.getenv("SUPABASE_SERVICE_KEY")
DATABASE_URL   = os.getenv("DATABASE_URL")


def latest_silver_date(s3_client) -> date:
    resp = s3_client.list_objects_v2(Bucket=SILVER_BUCKET, Prefix="silver/autos_usados/")
    keys = [o["Key"] for o in resp.get("Contents", [])]
    if not keys:
        raise FileNotFoundError("No hay archivos silver en S3")
    dates = [date.fromisoformat(k.split("/")[-1].replace(".parquet", "")) for k in keys]
    return max(dates)


def read_silver(s3_client, day: date) -> pl.DataFrame:
    # DeRuedas corre los domingos, Kavak los días de semana.
    # Cada fuente busca su silver más reciente — no requieren la misma fecha.
    def _read_latest(prefix: str, preferred_day: date) -> pl.DataFrame | None:
        # 1. Intentar el día exacto
        key = f"{prefix}/{preferred_day.isoformat()}.parquet"
        try:
            resp = s3_client.get_object(Bucket=SILVER_BUCKET, Key=key)
            return pl.read_parquet(io.BytesIO(resp["Body"].read()))
        except Exception:
            pass
        # 2. Fallback al archivo más reciente disponible
        try:
            listing = s3_client.list_objects_v2(Bucket=SILVER_BUCKET, Prefix=f"{prefix}/")
            keys = sorted(
                o["Key"] for o in listing.get("Contents", [])
                if o["Key"].endswith(".parquet")
            )
            if not keys:
                return None
            resp = s3_client.get_object(Bucket=SILVER_BUCKET, Key=keys[-1])
            return pl.read_parquet(io.BytesIO(resp["Body"].read()))
        except Exception:
            return None

    dr = _read_latest("silver/autos_usados", day)
    kv = _read_latest("silver/kavak_autos",  day)

    if dr is None:
        raise FileNotFoundError("No hay silver de DeRuedas disponible")

    if kv is not None:
        print(f"  → DeRuedas: {len(dr)} filas | Kavak: {len(kv)} filas")
        return pl.concat([dr, kv], how="diagonal")

    print(f"  → DeRuedas: {len(dr)} filas (sin silver Kavak)")
    return dr


def get_dolar_blue(day: date) -> float | None:
    """Devuelve la cotización blue de venta del día.

    Usa REST API cuando está disponible (GitHub Actions), psycopg2 en dev local.
    """
    if SUPABASE_URL and SUPABASE_KEY:
        resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/cotizaciones_dolar",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            params={"fecha": f"eq.{day.isoformat()}", "casa": "eq.blue", "select": "venta"},
            timeout=10,
        )
        resp.raise_for_status()
        rows = resp.json()
        return float(rows[0]["venta"]) if rows else None

    # Dev local — conexión directa a Postgres
    from etl.infra import get_pg_connection
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT venta FROM cotizaciones_dolar WHERE fecha = %s AND casa = 'blue'",
                (day,),
            )
            row = cur.fetchone()
    return float(row[0]) if row else None


def build_features(df: pl.DataFrame, dolar_blue: float | None, day: date) -> pl.DataFrame:
    """
    Transforma el silver DataFrame en features listas para ML.

    Pasos:
      1. Descartamos filas sin precio (target nulo = inutilizable)
      2. Flag km_valido + imputación con mediana por marca
      3. antiguedad, km_por_anio
      4. dolar_blue_venta como feature macro
      5. Selección de columnas finales
    """
    anio_scraping = day.year

    # 1. Necesitamos el target — sin precio no hay nada que aprender
    df = df.filter(pl.col("precio_ars").is_not_null())

    # 2. km = 1 es proxy de "no informado" — marcamos y luego imputamos
    df = df.with_columns(
        (pl.col("km") > 1).alias("km_valido")
    )

    # Mediana de km real por marca (solo filas con km_valido)
    mediana_por_marca = (
        df.filter(pl.col("km_valido"))
        .group_by("marca")
        .agg(pl.col("km").median().alias("km_mediana"))
    )
    df = df.join(mediana_por_marca, on="marca", how="left")

    # Imputar km proxy con la mediana de la misma marca
    df = df.with_columns(
        pl.when(pl.col("km_valido"))
        .then(pl.col("km"))
        .otherwise(pl.col("km_mediana"))
        .alias("km")
    ).drop("km_mediana")

    # 3. Features derivadas
    df = df.with_columns([
        (pl.lit(anio_scraping) - pl.col("anio")).alias("antiguedad"),
    ]).with_columns(
        # max(antiguedad, 1) evita división por cero en autos 0km del año actual
        (pl.col("km") / pl.col("antiguedad").clip(lower_bound=1)).alias("km_por_anio")
    )

    # 4. Contexto macro: cotización blue del día
    df = df.with_columns(
        pl.lit(dolar_blue).alias("dolar_blue_venta")
    )

    # 5. Columnas finales — cod es el identificador para el scoring, no es feature del modelo
    return df.select([
        "cod",
        "marca",
        "modelo",
        "provincia",
        "anio",
        "antiguedad",
        "km",
        "km_valido",
        "km_por_anio",
        "dolar_blue_venta",
        "precio_ars",   # target — al final por convención
    ])


def save_to_gold(df: pl.DataFrame, s3_client, day: date) -> str:
    key = f"gold/autos_usados/{day.isoformat()}.parquet"
    buffer = io.BytesIO()
    df.write_parquet(buffer)
    buffer.seek(0)
    s3_client.put_object(
        Bucket=GOLD_BUCKET,
        Key=key,
        Body=buffer.getvalue(),
        ContentType="application/octet-stream",
    )
    return key


def run(day: date | None = None) -> None:
    s3  = get_s3_client()
    day = day or latest_silver_date(s3)
    print(f"Feature engineering gold — {day}...")

    df = read_silver(s3, day)
    print(f"  → Silver leído: {len(df)} filas.")

    dolar = get_dolar_blue(day)
    if dolar is None:
        print("  ⚠ Sin cotización blue para hoy — dolar_blue_venta = null.")
    else:
        print(f"  → Dólar blue: ${dolar:,.0f}")

    gold = build_features(df, dolar, day)
    print(f"  → Gold: {len(gold)} filas, {len(gold.columns)} features.")
    print(f"  → Schema:\n{gold.schema}")

    key = save_to_gold(gold, s3, day)
    print(f"  → Guardado en s3://{GOLD_BUCKET}/{key}")
    print("Listo.")


if __name__ == "__main__":
    run()
