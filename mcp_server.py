"""
TasaJusta MCP Server

Expone herramientas de inteligencia de precios de autos usados argentinos
a cualquier cliente MCP: Claude Desktop, Cursor, VS Code, n8n, etc.

Tools:
  - buscar_autos       → query a Supabase con filtros PostgREST
  - top_oportunidades  → autos más subvaluados según el modelo ML
  - predecir_precio    → proxy al endpoint /predict del Lambda (LightGBM)
  - cotizacion_dolar   → dólar blue en tiempo real (dolarapi.com)

Protocolo: stdio (estándar para clientes MCP locales)

─────────────────────────────────────────────────
Instalación en Claude Desktop:
~/.config/Claude/claude_desktop_config.json

{
  "mcpServers": {
    "tasajusta": {
      "command": "uv",
      "args": ["--directory", "/ruta/a/tasajusta", "run", "mcp_server.py"],
      "env": {
        "SUPABASE_URL": "...",
        "SUPABASE_SERVICE_KEY": "..."
      }
    }
  }
}
─────────────────────────────────────────────────
"""

import logging
import os

import httpx
from mcp.server import MCPServer

logger = logging.getLogger(__name__)

mcp = MCPServer("tasajusta")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
LAMBDA_URL   = os.getenv("LAMBDA_API_URL", "https://5yoo5ugs44.execute-api.us-east-1.amazonaws.com")
THRESHOLD    = 0.10


async def _supabase_get(table: str, params: dict) -> list[dict]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL y SUPABASE_SERVICE_KEY no están configuradas")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers={
                "apikey":        SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            },
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def buscar_autos(
    marca: str | None = None,
    modelo: str | None = None,
    provincia: str | None = None,
    anio_min: int | None = None,
    anio_max: int | None = None,
    km_max: int | None = None,
    precio_max: int | None = None,
    solo_oportunidades: bool = False,
) -> str:
    """Busca autos usados en la base de datos de TasaJusta.

    Args:
        marca: Marca del auto (ej: Toyota, Ford, Volkswagen)
        modelo: Modelo (ej: Corolla, Focus, Gol)
        provincia: Provincia argentina (ej: Córdoba, Buenos Aires)
        anio_min: Año mínimo del vehículo
        anio_max: Año máximo del vehículo
        km_max: Kilometraje máximo
        precio_max: Precio máximo en PESOS ARGENTINOS (convertir USD antes)
        solo_oportunidades: Si True, solo devuelve autos subvaluados >10% por el modelo ML
    """
    params: dict = {
        "select": "marca,modelo,anio,km,precio_ars,oportunidad_score,provincia,url",
        "order":  "oportunidad_score.desc.nullslast",
        "limit":  "10",
    }
    if marca:               params["marca"]            = f"ilike.*{marca}*"
    if modelo:              params["modelo"]           = f"ilike.*{modelo}*"
    if provincia:           params["provincia"]        = f"ilike.*{provincia}*"
    if anio_min:            params["anio"]             = f"gte.{anio_min}"
    if anio_max:            params["anio"]             = f"lte.{anio_max}"
    if km_max:              params["km"]               = f"lte.{km_max}"
    if precio_max:          params["precio_ars"]       = f"lte.{precio_max}"
    if solo_oportunidades:  params["oportunidad_score"] = f"gte.{THRESHOLD}"

    logger.info("buscar_autos: %s", params)
    rows = await _supabase_get("autos_usados", params)

    if not rows:
        return "No se encontraron autos con esos filtros."

    lines = []
    for r in rows:
        score = r.get("oportunidad_score")
        opp   = f" 🔥 {score*100:.0f}% subvaluado" if score and score >= THRESHOLD else ""
        lines.append(
            f"• {r['marca']} {r['modelo']} {r['anio']} | "
            f"{r['km']:,} km | ${r['precio_ars']:,}{opp} | "
            f"{r['provincia']} | {r['url']}"
        )
    return f"Encontré {len(rows)} autos:\n" + "\n".join(lines)


@mcp.tool()
async def top_oportunidades(
    marca: str | None = None,
    provincia: str | None = None,
    limite: int = 5,
) -> str:
    """Devuelve los autos más subvaluados según el modelo ML de TasaJusta.

    Los resultados están ordenados por brecha entre precio publicado y precio estimado.

    Args:
        marca: Filtrar por marca (opcional)
        provincia: Filtrar por provincia (opcional)
        limite: Cantidad de resultados (máx 10, default 5)
    """
    params: dict = {
        "select":            "marca,modelo,anio,km,precio_ars,precio_estimado,oportunidad_score,provincia,url",
        "oportunidad_score": f"gte.{THRESHOLD}",
        "order":             "oportunidad_score.desc",
        "limit":             str(min(limite, 10)),
    }
    if marca:     params["marca"]     = f"ilike.*{marca}*"
    if provincia: params["provincia"] = f"ilike.*{provincia}*"

    logger.info("top_oportunidades: %s", params)
    rows = await _supabase_get("autos_usados", params)

    if not rows:
        return "No hay oportunidades detectadas con esos filtros en este momento."

    lines = []
    for r in rows:
        ahorro = (r.get("precio_estimado") or 0) - r["precio_ars"]
        lines.append(
            f"• {r['marca']} {r['modelo']} {r['anio']} | "
            f"{r['km']:,} km | Publicado: ${r['precio_ars']:,} | "
            f"Estimado: ${r.get('precio_estimado', '?'):,} | "
            f"Ahorro: ${ahorro:,} ({r['oportunidad_score']*100:.0f}%) | "
            f"{r['provincia']} | {r['url']}"
        )
    return f"Top {len(rows)} oportunidades:\n" + "\n".join(lines)


@mcp.tool()
async def predecir_precio(
    marca: str,
    modelo: str,
    provincia: str,
    anio: int,
    km: int,
) -> str:
    """Estima el precio justo de mercado para un auto según el modelo LightGBM de TasaJusta.

    Args:
        marca: Marca del auto (ej: Toyota)
        modelo: Modelo (ej: Corolla)
        provincia: Provincia argentina (ej: Córdoba)
        anio: Año del vehículo
        km: Kilometraje actual
    """
    logger.info("predecir_precio: %s %s %d %d km", marca, modelo, anio, km)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{LAMBDA_URL}/predict",
            json={"marca": marca, "modelo": modelo, "provincia": provincia, "anio": anio, "km": km},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

    precio = data.get("precio_estimado_ars") or data.get("precio_estimado")
    if not precio:
        return "No se pudo estimar el precio para ese auto."
    return (
        f"Precio estimado de mercado: ${int(precio):,} ARS\n"
        f"({marca} {modelo} {anio}, {km:,} km, {provincia})"
    )


@mcp.tool()
async def cotizacion_dolar() -> str:
    """Devuelve la cotización actual del dólar blue en Argentina."""
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://dolarapi.com/v1/dolares/blue", timeout=5)
        resp.raise_for_status()
        data = resp.json()

    return (
        f"Dólar blue: compra ${data['compra']:,} / venta ${data['venta']:,}\n"
        f"Actualizado: {data.get('fechaActualizacion', 'N/A')}"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
    mcp.run(transport="stdio")
