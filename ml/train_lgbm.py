"""
Entrenamiento baseline: LightGBM para predecir precio_ars.

Lee el gold Parquet, entrena, evalúa y guarda el modelo en MinIO.
LightGBM maneja variables categóricas de forma nativa — no necesita OHE.
"""

import io
import os
import pickle
from datetime import date

import lightgbm as lgb
import pandas as pd
from dotenv import load_dotenv
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from etl.infra import get_s3_client

load_dotenv()

GOLD_BUCKET   = os.getenv("MINIO_BUCKET", "tasajusta-bronze")
MODELS_BUCKET = "tasajusta-models"

# Columnas categóricas que LightGBM maneja nativo
CAT_FEATURES = ["marca", "modelo", "provincia"]

# Features de entrada (todo excepto el target)
FEATURE_COLS = [
    "marca", "modelo", "provincia",
    "anio", "antiguedad",
    "km", "km_valido", "km_por_anio",
    "dolar_blue_venta",
]

TARGET = "precio_ars"


def read_gold(s3_client, day: date) -> pd.DataFrame:
    key = f"gold/autos_usados/{day.isoformat()}.parquet"
    resp = s3_client.get_object(Bucket=GOLD_BUCKET, Key=key)
    # Leer con pandas directamente desde bytes
    return pd.read_parquet(io.BytesIO(resp["Body"].read()))


def prepare(df: pd.DataFrame):
    """Separa features y target, tipea categoricals."""
    # [ENTREVISTA] LightGBM necesita dtype 'category' en pandas para
    # activar su encoding nativo — sin esto las trata como strings y falla
    for col in CAT_FEATURES:
        df[col] = df[col].astype("category")

    X = df[FEATURE_COLS]
    y = df[TARGET]
    return X, y


def train(X_train: pd.DataFrame, y_train: pd.Series) -> lgb.LGBMRegressor:
    """
    Hiperparámetros conservadores para dataset pequeño (156 filas).
    num_leaves bajo y min_child_samples alto para frenar el overfitting.
    """
    model = lgb.LGBMRegressor(
        n_estimators=300,
        num_leaves=15,          # árbol poco profundo — menos overfitting
        learning_rate=0.05,
        min_child_samples=5,    # mínimo de muestras por hoja
        subsample=0.8,          # usa 80% de filas por árbol
        colsample_bytree=0.8,   # usa 80% de features por árbol
        random_state=42,
        verbose=-1,
    )
    model.fit(
        X_train, y_train,
        categorical_feature=CAT_FEATURES,
    )
    return model


def evaluate(model, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    preds = model.predict(X_test)
    mae   = mean_absolute_error(y_test, preds)
    rmse  = mean_squared_error(y_test, preds) ** 0.5
    r2    = r2_score(y_test, preds)
    mape  = (abs((y_test - preds) / y_test) * 100).mean()
    return {"MAE": mae, "RMSE": rmse, "R2": r2, "MAPE": mape}


def save_model(model, s3_client, day: date) -> str:
    """Serializa el modelo con pickle y lo guarda en MinIO."""
    key = f"lgbm/model_lgbm_{day.isoformat()}.pkl"

    # Crear el bucket si no existe
    try:
        s3_client.head_bucket(Bucket=MODELS_BUCKET)
    except Exception:
        s3_client.create_bucket(Bucket=MODELS_BUCKET)

    s3_client.put_object(
        Bucket=MODELS_BUCKET,
        Key=key,
        Body=pickle.dumps(model),
        ContentType="application/octet-stream",
    )
    return key


def run(day: date | None = None) -> dict:
    day = day or date.today()
    print(f"=== Training LightGBM — {day} ===\n")

    s3 = get_s3_client()
    df = read_gold(s3, day)
    print(f"Dataset: {len(df)} filas, {len(FEATURE_COLS)} features → target: {TARGET}")

    X, y = prepare(df)

    # [ENTREVISTA] random_state=42 garantiza reproducibilidad — el mismo split
    # siempre, así podés comparar LightGBM vs MLP en exactamente el mismo test set
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"Train: {len(X_train)} filas | Test: {len(X_test)} filas\n")

    model = train(X_train, y_train)

    # Métricas en train (para detectar overfitting) y test (generalización real)
    train_metrics = evaluate(model, X_train, y_train)
    test_metrics  = evaluate(model, X_test, y_test)

    print("── Train metrics ──────────────────────")
    for k, v in train_metrics.items():
        print(f"  {k}: {v:,.0f}" if k != "R2" else f"  {k}: {v:.3f}")
        if k == "MAPE": print(f"      ({v:.1f}%)")

    print("\n── Test metrics ───────────────────────")
    for k, v in test_metrics.items():
        print(f"  {k}: {v:,.0f}" if k != "R2" else f"  {k}: {v:.3f}")
        if k == "MAPE": print(f"      ({v:.1f}%)")

    gap = test_metrics["MAE"] - train_metrics["MAE"]
    print(f"\n── Overfitting gap (MAE test − train): ${gap:,.0f}")
    if gap > train_metrics["MAE"] * 0.5:
        print("  ⚠ Gap > 50% del train MAE — overfitting significativo (esperado con 156 filas)")

    key = save_model(model, s3, day)
    print(f"\nModelo guardado: s3://{MODELS_BUCKET}/{key}")
    print("=== Listo ===")

    return {"train": train_metrics, "test": test_metrics, "model_key": key}


if __name__ == "__main__":
    run()
