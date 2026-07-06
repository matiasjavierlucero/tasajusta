"""
Batch scoring: predice el precio estimado para cada auto del gold parquet
y sube precio_estimado + oportunidad_score a Supabase.

score > 0.10 significa que el auto está publicado al menos 10% por debajo
del precio que el modelo estima → oportunidad de compra.

Corre después del retrain en CI (retrain.yml / etl-vehiculos.yml).
"""

import io
import os
import pickle
from datetime import date

import httpx
import pandas as pd
from dotenv import load_dotenv

from etl.infra import get_s3_client

load_dotenv()

GOLD_BUCKET   = os.getenv("MINIO_BUCKET", "tasajusta-datalake-966940665955")
MODELS_BUCKET = os.getenv("MODELS_BUCKET", "tasajusta-models-966940665955")
SUPABASE_URL  = os.getenv("SUPABASE_URL")
SUPABASE_KEY  = os.getenv("SUPABASE_SERVICE_KEY")

CAT_FEATURES = ["marca", "modelo", "provincia"]
FEATURE_COLS = [
    "marca", "modelo", "provincia",
    "anio", "antiguedad",
    "km", "km_valido", "km_por_anio",
    "dolar_blue_venta",
]

# Umbral mínimo para considerar una publicación como oportunidad
OPORTUNIDAD_THRESHOLD = 0.10


def latest_gold_date(s3_client) -> date:
    resp = s3_client.list_objects_v2(Bucket=GOLD_BUCKET, Prefix="gold/autos_usados/")
    keys = [o["Key"] for o in resp.get("Contents", [])]
    if not keys:
        raise FileNotFoundError("No hay archivos gold en S3")
    dates = [date.fromisoformat(k.split("/")[-1].replace(".parquet", "")) for k in keys]
    return max(dates)


def load_latest_model(s3_client):
    resp = s3_client.list_objects_v2(Bucket=MODELS_BUCKET, Prefix="lgbm/")
    keys = [o["Key"] for o in resp.get("Contents", [])]
    if not keys:
        raise FileNotFoundError("No hay modelos en S3")
    # los keys tienen formato lgbm/model_lgbm_YYYY-MM-DD.pkl → orden lexicográfico = cronológico
    latest_key = sorted(keys)[-1]
    print(f"Modelo: {latest_key}")
    obj = s3_client.get_object(Bucket=MODELS_BUCKET, Key=latest_key)
    return pickle.loads(obj["Body"].read())


def read_gold(s3_client, day: date) -> pd.DataFrame:
    key = f"gold/autos_usados/{day.isoformat()}.parquet"
    resp = s3_client.get_object(Bucket=GOLD_BUCKET, Key=key)
    return pd.read_parquet(io.BytesIO(resp["Body"].read()))


def compute_scores(df: pd.DataFrame, model) -> pd.DataFrame:
    X = df[FEATURE_COLS].copy()
    for col in CAT_FEATURES:
        X[col] = X[col].astype("category")

    df = df.copy()
    df["precio_estimado"] = model.predict(X).round(0).astype(int)

    # score positivo = está publicado por debajo del estimado = potencial oportunidad
    df["oportunidad_score"] = (
        (df["precio_estimado"] - df["precio_ars"]) / df["precio_estimado"]
    ).round(4)

    return df


def upsert_scores(df: pd.DataFrame) -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Sin credenciales Supabase — saltando upsert")
        return

    # Convertir explícitamente a tipos Python nativos para evitar problemas de serialización
    subset = df[["cod", "precio_estimado", "oportunidad_score"]].copy()
    subset["precio_estimado"]  = subset["precio_estimado"].astype(int)
    subset["oportunidad_score"] = subset["oportunidad_score"].astype(float)
    records = subset.to_dict(orient="records")

    resp = httpx.post(
        f"{SUPABASE_URL}/rest/v1/autos_usados",
        headers={
            "apikey":        SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type":  "application/json",
            "Prefer":        "resolution=merge-duplicates",
        },
        json=records,
        timeout=60,
    )
    if not resp.is_success:
        print(f"Error Supabase {resp.status_code}: {resp.text}")
    resp.raise_for_status()
    print(f"Upsert OK — {len(records)} registros actualizados en Supabase")


def run() -> None:
    s3  = get_s3_client()
    day = latest_gold_date(s3)
    print(f"=== Scoring oportunidades — {day} ===\n")

    model = load_latest_model(s3)
    df    = read_gold(s3, day)

    df = compute_scores(df, model)

    oportunidades = (df["oportunidad_score"] > OPORTUNIDAD_THRESHOLD).sum()
    print(f"Total autos: {len(df)}")
    print(f"Oportunidades (score > {OPORTUNIDAD_THRESHOLD*100:.0f}%): {oportunidades}")

    top = df.nlargest(5, "oportunidad_score")[["marca", "modelo", "anio", "precio_ars", "precio_estimado", "oportunidad_score"]]
    print("\nTop 5 oportunidades:")
    print(top.to_string(index=False))

    upsert_scores(df)
    print("\n=== Listo ===")


if __name__ == "__main__":
    run()
