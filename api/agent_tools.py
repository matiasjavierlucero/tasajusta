"""
Definición de tools del agente y sus implementaciones.
Cada función ejecuta una query real a Supabase o al modelo local.
"""

import json
import os
from datetime import date

import httpx
import pandas as pd

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

OPORTUNIDAD_THRESHOLD = 0.10

# ── Definición de tools para Groq ─────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_autos",
            "description": (
                "Busca autos en la base de datos según los filtros del usuario. "
                "Devuelve publicaciones reales con precio, km y oportunidad detectada por el modelo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "marca":             {"type": "string",  "description": "Marca (ej: Toyota, Ford, Volkswagen)"},
                    "modelo":            {"type": "string",  "description": "Modelo (ej: Corolla, Focus, Gol)"},
                    "provincia":         {"type": "string",  "description": "Provincia argentina (ej: Córdoba, Buenos Aires)"},
                    "anio_min":          {"type": "integer", "description": "Año mínimo del vehículo"},
                    "anio_max":          {"type": "integer", "description": "Año máximo del vehículo"},
                    "km_max":            {"type": "integer", "description": "Kilometraje máximo"},
                    "precio_max":        {"type": "integer", "description": "Precio máximo en pesos ARS"},
                    "solo_oportunidades":{"type": "boolean", "description": "Si true, filtra solo autos subvaluados (score > 10%)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "top_oportunidades",
            "description": (
                "Devuelve los autos más subvaluados según el modelo ML: "
                "los que tienen mayor diferencia entre precio publicado y precio estimado."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "marca":    {"type": "string",  "description": "Filtrar por marca (opcional)"},
                    "provincia":{"type": "string",  "description": "Filtrar por provincia (opcional)"},
                    "limite":   {"type": "integer", "description": "Cantidad de resultados (default 5, máx 10)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "predecir_precio",
            "description": "Estima el precio justo de mercado para un auto con las características dadas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "marca":     {"type": "string",  "description": "Marca del auto"},
                    "modelo":    {"type": "string",  "description": "Modelo del auto"},
                    "provincia": {"type": "string",  "description": "Provincia argentina"},
                    "anio":      {"type": "integer", "description": "Año del vehículo"},
                    "km":        {"type": "integer", "description": "Kilometraje actual"},
                },
                "required": ["marca", "modelo", "provincia", "anio", "km"],
            },
        },
    },
]


# ── Implementaciones ───────────────────────────────────────────────────────────

def _supabase_get(path: str, params: dict) -> list[dict]:
    """Query GET a Supabase REST API con filtros PostgREST."""
    resp = httpx.get(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers={
            "apikey":        SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
        params=params,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def buscar_autos(
    marca: str | None = None,
    modelo: str | None = None,
    provincia: str | None = None,
    anio_min: int | None = None,
    anio_max: int | None = None,
    km_max: int | None = None,
    precio_max: int | None = None,
    solo_oportunidades: bool = False,
) -> str:
    params: dict = {
        "select": "cod,marca,modelo,anio,km,precio_ars,provincia,oportunidad_score,url",
        "order":  "oportunidad_score.desc.nullslast",
        "limit":  "10",
    }
    if marca:
        params["marca"] = f"ilike.*{marca}*"
    if modelo:
        params["modelo"] = f"ilike.*{modelo}*"
    if provincia:
        params["provincia"] = f"ilike.*{provincia}*"
    if anio_min:
        params["anio"] = f"gte.{anio_min}"
    if anio_max:
        params["anio"] = f"lte.{anio_max}"
    if km_max:
        params["km"] = f"lte.{km_max}"
    if precio_max:
        params["precio_ars"] = f"lte.{precio_max}"
    if solo_oportunidades:
        params["oportunidad_score"] = f"gte.{OPORTUNIDAD_THRESHOLD}"

    rows = _supabase_get("autos_usados", params)
    if not rows:
        return "No se encontraron autos con esos filtros."

    results = []
    for r in rows:
        score = r.get("oportunidad_score")
        etiqueta = f" 🔥 {score*100:.1f}% subvaluado" if score and score >= OPORTUNIDAD_THRESHOLD else ""
        results.append(
            f"- {r['marca']} {r['modelo']} {r['anio']} | "
            f"{r['km']:,} km | ${r['precio_ars']:,}{etiqueta} | "
            f"{r['provincia']} | {r['url']}"
        )
    return f"Encontré {len(rows)} autos:\n" + "\n".join(results)


def top_oportunidades(
    marca: str | None = None,
    provincia: str | None = None,
    limite: int = 5,
) -> str:
    params: dict = {
        "select":             "cod,marca,modelo,anio,km,precio_ars,precio_estimado,oportunidad_score,provincia,url",
        "oportunidad_score":  f"gte.{OPORTUNIDAD_THRESHOLD}",
        "order":              "oportunidad_score.desc",
        "limit":              str(min(limite, 10)),
    }
    if marca:
        params["marca"] = f"ilike.*{marca}*"
    if provincia:
        params["provincia"] = f"ilike.*{provincia}*"

    rows = _supabase_get("autos_usados", params)
    if not rows:
        return "No hay oportunidades detectadas con esos filtros en este momento."

    results = []
    for r in rows:
        ahorro = (r.get("precio_estimado") or 0) - (r.get("precio_ars") or 0)
        results.append(
            f"- {r['marca']} {r['modelo']} {r['anio']} | "
            f"{r['km']:,} km | Publicado: ${r['precio_ars']:,} | "
            f"Estimado: ${r.get('precio_estimado', '?'):,} | "
            f"Ahorro: ${ahorro:,} ({r['oportunidad_score']*100:.1f}%) | "
            f"{r['provincia']} | {r['url']}"
        )
    return f"Top {len(rows)} oportunidades:\n" + "\n".join(results)


def predecir_precio(marca: str, modelo: str, provincia: str, anio: int, km: int, app_state=None) -> str:
    if app_state is None or app_state.model is None:
        return "Modelo de predicción no disponible en este momento."

    from ml.train_lgbm import CAT_FEATURES

    anio_actual = date.today().year
    antiguedad  = anio_actual - anio
    km_valido   = km > 1
    km_por_anio = km / max(antiguedad, 1)
    dolar_blue  = float(app_state.dolar_blue) if app_state.dolar_blue else float("nan")

    X = pd.DataFrame([{
        "marca":            marca,
        "modelo":           modelo,
        "provincia":        provincia,
        "anio":             float(anio),
        "antiguedad":       float(antiguedad),
        "km":               float(km),
        "km_valido":        bool(km_valido),
        "km_por_anio":      float(km_por_anio),
        "dolar_blue_venta": dolar_blue,
    }])
    for col in CAT_FEATURES:
        X[col] = X[col].astype("category")

    precio = int(app_state.model.predict(X)[0])
    return f"El precio estimado de mercado para un {marca} {modelo} {anio} con {km:,} km en {provincia} es ${precio:,} ARS."


# ── Dispatcher ─────────────────────────────────────────────────────────────────

def execute_tool(name: str, arguments: str, app_state=None) -> str:
    args = json.loads(arguments)
    if name == "buscar_autos":
        return buscar_autos(**args)
    if name == "top_oportunidades":
        return top_oportunidades(**args)
    if name == "predecir_precio":
        return predecir_precio(**args, app_state=app_state)
    return f"Tool desconocida: {name}"
