import os
import pickle
from contextlib import asynccontextmanager
from datetime import date

from dotenv import load_dotenv
from fastapi import FastAPI

from etl.infra import get_pg_connection, get_s3_client
from api.routes.predict import router as predict_router

load_dotenv()

MODELS_BUCKET = os.getenv("MODELS_BUCKET", "tasajusta-models")


@asynccontextmanager
async def lifespan(app: FastAPI):
    today = date.today().isoformat()
    s3    = get_s3_client()

    # Modelo
    try:
        key  = f"lgbm/model_lgbm_{today}.pkl"
        resp = s3.get_object(Bucket=MODELS_BUCKET, Key=key)
        app.state.model     = pickle.loads(resp["Body"].read())
        app.state.model_key = key
        print(f"Modelo cargado: {key}")
    except Exception as e:
        print(f"⚠ No se pudo cargar el modelo: {e}")
        app.state.model     = None
        app.state.model_key = None

    # Cotización blue
    try:
        conn = get_pg_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT venta FROM cotizaciones_dolar WHERE fecha = %s AND casa = 'blue'",
                (date.today(),),
            )
            row = cur.fetchone()
        conn.close()
        app.state.dolar_blue = float(row[0]) if row else None
    except Exception:
        app.state.dolar_blue = None

    yield

    app.state.model      = None
    app.state.model_key  = None
    app.state.dolar_blue = None


app = FastAPI(
    title="TasaJusta API",
    description="Predicción de precio justo de autos usados en Argentina",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(predict_router)
