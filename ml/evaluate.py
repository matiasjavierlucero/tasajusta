"""
Comparación formal: LightGBM vs MLP en el mismo hold-out set.

Carga ambos modelos desde MinIO, reconstruye el mismo split 80/20
con random_state=42, y reporta las métricas lado a lado.
"""

import io
import os
import pickle
from datetime import date

import pandas as pd
import polars as pl
import torch
from dotenv import load_dotenv
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from etl.infra import get_s3_client
from ml.train_lgbm import prepare as lgbm_prepare, FEATURE_COLS as LGBM_FEATURES
from ml.train_mlp  import encode, make_tensors, PrecioMLP, FEATURE_COLS as MLP_FEATURES

load_dotenv()

GOLD_BUCKET   = os.getenv("MINIO_BUCKET", "tasajusta-bronze")
MODELS_BUCKET = "tasajusta-models"
TARGET        = "precio_ars"


def read_gold(s3_client, day: date) -> pd.DataFrame:
    key = f"gold/autos_usados/{day.isoformat()}.parquet"
    resp = s3_client.get_object(Bucket=GOLD_BUCKET, Key=key)
    return pl.read_parquet(io.BytesIO(resp["Body"].read())).to_pandas()


def load_lgbm(s3_client, day: date):
    key = f"lgbm/model_lgbm_{day.isoformat()}.pkl"
    resp = s3_client.get_object(Bucket=MODELS_BUCKET, Key=key)
    return pickle.loads(resp["Body"].read())


def load_mlp_bundle(s3_client, day: date) -> dict:
    key = f"mlp/model_mlp_{day.isoformat()}.pkl"
    resp = s3_client.get_object(Bucket=MODELS_BUCKET, Key=key)
    return pickle.loads(resp["Body"].read())


def metrics(y_true, y_pred) -> dict:
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred) ** 0.5
    r2   = r2_score(y_true, y_pred)
    mape = (abs((y_true - y_pred) / y_true) * 100).mean()
    return {"MAE": mae, "RMSE": rmse, "R2": r2, "MAPE": mape}


def run(day: date | None = None) -> None:
    day = day or date.today()
    print(f"=== Evaluación comparativa — {day} ===\n")

    s3  = get_s3_client()
    df  = read_gold(s3, day)

    # ── LightGBM ──────────────────────────────────────────────────────────────
    lgbm_model          = load_lgbm(s3_client=s3, day=day)
    X_lgbm, y           = lgbm_prepare(df.copy())
    _, X_lgbm_test, _, y_test = train_test_split(
        X_lgbm, y, test_size=0.2, random_state=42
    )
    lgbm_preds = lgbm_model.predict(X_lgbm_test)
    lgbm_m     = metrics(y_test.values, lgbm_preds)

    # ── MLP ───────────────────────────────────────────────────────────────────
    bundle          = load_mlp_bundle(s3, day)
    df_enc, _       = encode(df.copy())
    X_mlp           = df_enc[MLP_FEATURES]
    y_mlp           = df_enc[TARGET]
    _, X_mlp_test, _, y_mlp_test = train_test_split(
        X_mlp, y_mlp, test_size=0.2, random_state=42
    )

    model = PrecioMLP(input_dim=bundle["input_dim"])
    model.load_state_dict(bundle["model_state"])
    model.eval()

    X_te_t, _, _, _ = make_tensors(
        X_mlp_test, y_mlp_test,
        bundle["scaler_X"], bundle["scaler_y"]
    )
    with torch.no_grad():
        preds_scaled = model(X_te_t).numpy()
    mlp_preds = bundle["scaler_y"].inverse_transform(
        preds_scaled.reshape(-1, 1)
    ).ravel()
    mlp_m = metrics(y_mlp_test.values, mlp_preds)

    # ── Tabla comparativa ─────────────────────────────────────────────────────
    print(f"{'Métrica':<12} {'LightGBM':>14} {'MLP':>14} {'Ganador':>10}")
    print("─" * 54)

    for k in ["MAE", "RMSE", "R2", "MAPE"]:
        lv = lgbm_m[k]
        mv = mlp_m[k]

        # Para MAE/RMSE/MAPE: menor es mejor. Para R2: mayor es mejor.
        if k == "R2":
            winner = "LightGBM" if lv > mv else "MLP"
        else:
            winner = "LightGBM" if lv < mv else "MLP"

        if k == "R2":
            print(f"{k:<12} {lv:>14.3f} {mv:>14.3f} {winner:>10}")
        elif k == "MAPE":
            print(f"{k:<12} {lv:>13.1f}% {mv:>13.1f}% {winner:>10}")
        else:
            print(f"{k:<12} ${lv:>12,.0f} ${mv:>12,.0f} {winner:>10}")

    print("─" * 54)
    lgbm_wins = sum(
        1 for k in ["MAE", "RMSE", "MAPE"] if lgbm_m[k] < mlp_m[k]
    ) + (1 if lgbm_m["R2"] > mlp_m["R2"] else 0)

    winner = "LightGBM" if lgbm_wins >= 3 else "MLP"
    print(f"\n{'Modelo recomendado para producción:':<40} {winner}")
    print(f"(LightGBM ganó {lgbm_wins}/4 métricas)\n")

    print("Nota: con 152 filas ambos modelos overfittean.")
    print("Con 1000+ registros el gap train/test se cierra.")


if __name__ == "__main__":
    run()
