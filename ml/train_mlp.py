"""
Entrenamiento MLP (red neuronal) con PyTorch para predecir precio_ars.

Mismo gold Parquet que LightGBM, mismo split 80/20 con random_state=42
para comparación honesta en exactamente el mismo test set.

Diferencias vs LightGBM:
  - Las categorías (marca, provincia) necesitan Label Encoding numérico
  - modelo (auto) NO se usa — demasiada cardinalidad para tan pocos datos (D2-A)
  - Normalización del target para estabilizar el entrenamiento
"""

import io
import os
import pickle
from datetime import date

import pandas as pd
import polars as pl
import torch
import torch.nn as nn
from dotenv import load_dotenv
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

from etl.infra import get_s3_client

load_dotenv()

GOLD_BUCKET   = os.getenv("MINIO_BUCKET", "tasajusta-bronze")
MODELS_BUCKET = "tasajusta-models"

#  modelo NO incluido en MLP — ~50 categorías únicas con 2-3 ejemplos
# cada una. Con OHE serían 50 columnas de casi puro ruido para 156 filas.
FEATURE_COLS = [
    "marca", "provincia",
    "anio", "antiguedad",
    "km", "km_valido", "km_por_anio",
    "dolar_blue_venta",
]
CAT_COLS = ["marca", "provincia"]
TARGET   = "precio_ars"


# ── Arquitectura ─────────────────────────────────────────────────────────────

class PrecioMLP(nn.Module):
    """
    Red neuronal de 3 capas para regresión de precio.

    Arquitectura conservadora para dataset pequeño:
    input → 64 → 32 → 16 → 1
    Dropout para regularización (reduce overfitting).
    """
    def __init__(self, input_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(1)


# ── Helpers ───────────────────────────────────────────────────────────────────

def read_gold(s3_client, day: date) -> pd.DataFrame:
    key = f"gold/autos_usados/{day.isoformat()}.parquet"
    resp = s3_client.get_object(Bucket=GOLD_BUCKET, Key=key)
    return pl.read_parquet(io.BytesIO(resp["Body"].read())).to_pandas()


def encode(df: pd.DataFrame):
    """
    Label Encoding para categorías.
    Devuelve el DataFrame encodado y los encoders (necesarios para inferencia).
    """
    encoders = {}
    df = df.copy()
    for col in CAT_COLS:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        encoders[col] = le
    df["km_valido"] = df["km_valido"].astype(int)
    return df, encoders


def make_tensors(X: pd.DataFrame, y: pd.Series, scaler_X=None, scaler_y=None):
    """Convierte a tensores PyTorch y normaliza."""
    if scaler_X is None:
        scaler_X = StandardScaler()
        X_scaled = scaler_X.fit_transform(X)
    else:
        X_scaled = scaler_X.transform(X)

    if scaler_y is None:
        scaler_y = StandardScaler()
        y_scaled = scaler_y.fit_transform(y.values.reshape(-1, 1)).ravel()
    else:
        y_scaled = scaler_y.transform(y.values.reshape(-1, 1)).ravel()

    X_t = torch.tensor(X_scaled, dtype=torch.float32)
    y_t = torch.tensor(y_scaled, dtype=torch.float32)
    return X_t, y_t, scaler_X, scaler_y


def evaluate(model, X_t, y_real, scaler_y) -> dict:
    model.eval()
    with torch.no_grad():
        preds_scaled = model(X_t).numpy()
    preds = scaler_y.inverse_transform(preds_scaled.reshape(-1, 1)).ravel()
    mae  = mean_absolute_error(y_real, preds)
    rmse = mean_squared_error(y_real, preds) ** 0.5
    r2   = r2_score(y_real, preds)
    mape = (abs((y_real - preds) / y_real) * 100).mean()
    return {"MAE": mae, "RMSE": rmse, "R2": r2, "MAPE": mape}


def save_model(bundle: dict, s3_client, day: date) -> str:
    """
    Guarda un bundle con el modelo + scalers + encoders.
    Todo junto porque en inferencia necesitamos el mismo preprocesamiento.
    """
    key = f"mlp/model_mlp_{day.isoformat()}.pkl"
    try:
        s3_client.head_bucket(Bucket=MODELS_BUCKET)
    except Exception:
        s3_client.create_bucket(Bucket=MODELS_BUCKET)

    s3_client.put_object(
        Bucket=MODELS_BUCKET,
        Key=key,
        Body=pickle.dumps(bundle),
        ContentType="application/octet-stream",
    )
    return key


# ── Training loop ─────────────────────────────────────────────────────────────

def run(day: date | None = None) -> dict:
    day = day or date.today()
    print(f"=== Training MLP — {day} ===\n")

    s3 = get_s3_client()
    df = read_gold(s3, day)

    df_enc, encoders = encode(df)

    X = df_enc[FEATURE_COLS]
    y = df_enc[TARGET]

    # Mismo split que LightGBM — comparación honesta
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"Dataset: {len(df)} filas | Train: {len(X_train)} | Test: {len(X_test)}")
    print(f"Features: {len(FEATURE_COLS)} (sin 'modelo' — D2-A)\n")

    X_tr_t, y_tr_t, scaler_X, scaler_y = make_tensors(X_train, y_train)
    X_te_t, y_te_t, _, _               = make_tensors(X_test, y_test, scaler_X, scaler_y)

    model     = PrecioMLP(input_dim=len(FEATURE_COLS))
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_fn   = nn.MSELoss()

    EPOCHS = 500
    model.train()
    for epoch in range(1, EPOCHS + 1):
        optimizer.zero_grad()
        preds = model(X_tr_t)
        loss  = loss_fn(preds, y_tr_t)
        loss.backward()
        optimizer.step()

        if epoch % 100 == 0:
            print(f"  Epoch {epoch:4d}/{EPOCHS} — loss: {loss.item():.4f}")

    train_metrics = evaluate(model, X_tr_t, y_train.values, scaler_y)
    test_metrics  = evaluate(model, X_te_t, y_test.values,  scaler_y)

    print("\n── Train metrics ──────────────────────")
    for k, v in train_metrics.items():
        print(f"  {k}: {v:,.0f}" if k != "R2" else f"  {k}: {v:.3f}")

    print("\n── Test metrics ───────────────────────")
    for k, v in test_metrics.items():
        print(f"  {k}: {v:,.0f}" if k != "R2" else f"  {k}: {v:.3f}")

    gap = test_metrics["MAE"] - train_metrics["MAE"]
    print(f"\n── Overfitting gap (MAE test − train): ${gap:,.0f}")

    bundle = {
        "model_state": model.state_dict(),
        "input_dim":   len(FEATURE_COLS),
        "encoders":    encoders,
        "scaler_X":    scaler_X,
        "scaler_y":    scaler_y,
        "feature_cols": FEATURE_COLS,
    }
    key = save_model(bundle, s3, day)
    print(f"\nModelo guardado: s3://{MODELS_BUCKET}/{key}")
    print("=== Listo ===")

    return {"train": train_metrics, "test": test_metrics, "model_key": key}


if __name__ == "__main__":
    run()
