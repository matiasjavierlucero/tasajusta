import os
import pickle
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI

from etl.infra import get_pg_connection, get_s3_client
from api.routes.predict import router as predict_router
from api.routes.metrics import router as metrics_router
from api.routes.agent import router as agent_router

load_dotenv()

MODELS_BUCKET = os.getenv("MODELS_BUCKET", "tasajusta-models")


@asynccontextmanager
async def lifespan(app: FastAPI):
    today = date.today().isoformat()
    s3    = get_s3_client()

    # Modelo — busca el más reciente disponible, no estrictamente hoy
    try:
        objects = s3.list_objects_v2(Bucket=MODELS_BUCKET, Prefix="lgbm/model_lgbm_")
        keys    = sorted(o["Key"] for o in objects.get("Contents", []))
        if not keys:
            raise FileNotFoundError("No hay modelos en el bucket")
        key  = keys[-1]   # el más reciente por orden lexicográfico (fecha en el nombre)
        resp = s3.get_object(Bucket=MODELS_BUCKET, Key=key)
        app.state.model     = pickle.loads(resp["Body"].read())
        app.state.model_key = key
        print(f"Modelo cargado: {key}")
    except Exception as e:
        print(f"⚠ No se pudo cargar el modelo: {e}")
        app.state.model     = None
        app.state.model_key = None

    # Cotización blue — usa la más reciente disponible (no necesariamente hoy)
    try:
        conn = get_pg_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT venta FROM cotizaciones_dolar WHERE casa = 'blue' ORDER BY fecha DESC LIMIT 1"
            )
            row = cur.fetchone()
        conn.close()
        app.state.dolar_blue = float(row[0]) if row else None
    except Exception:
        app.state.dolar_blue = None

    app.state.started_at         = datetime.now(timezone.utc).isoformat()
    app.state.predictions_served = 0

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
app.include_router(metrics_router)
app.include_router(agent_router)
