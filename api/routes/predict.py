from datetime import date

import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from api.schemas import PredictRequest, PredictResponse
from ml.train_lgbm import CAT_FEATURES

router = APIRouter()


@router.get("/health")
def health(request: Request):
    state = request.app.state
    ok = state.model is not None
    return JSONResponse(
        status_code=200 if ok else 503,
        content={
            "status":     "ok" if ok else "sin modelo",
            "model_key":  state.model_key,
            "dolar_blue": state.dolar_blue,
            "started_at": getattr(state, "started_at", None),
        },
    )


@router.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest, request: Request):
    state = request.app.state

    if state.model is None:
        raise HTTPException(status_code=503, detail="Modelo no disponible")

    anio_actual = date.today().year
    antiguedad  = anio_actual - req.anio
    km_valido   = req.km > 1
    km_por_anio = req.km / max(antiguedad, 1)

    # dolar_blue puede ser None si no hay cotización hoy.
    # None en DataFrame crea dtype object → LightGBM lo rechaza. Usamos NaN (float).
    dolar_blue = float(state.dolar_blue) if state.dolar_blue is not None else float("nan")

    X = pd.DataFrame([{
        "marca":            req.marca,
        "modelo":           req.modelo,
        "provincia":        req.provincia,
        "anio":             float(req.anio),
        "antiguedad":       float(antiguedad),
        "km":               float(req.km),
        "km_valido":        bool(km_valido),
        "km_por_anio":      float(km_por_anio),
        "dolar_blue_venta": dolar_blue,
    }])

    for col in CAT_FEATURES:
        X[col] = X[col].astype("category")

    precio = int(state.model.predict(X)[0])
    state.predictions_served = getattr(state, "predictions_served", 0) + 1

    advertencia = None
    if antiguedad == 0:
        advertencia = "Auto del año actual — estimación menos confiable"

    return PredictResponse(
        precio_estimado_ars=precio,
        modelo_usado=state.model_key,
        dolar_blue_venta=state.dolar_blue,
        advertencia=advertencia,
    )
