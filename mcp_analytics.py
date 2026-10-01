"""
TasaJusta Analytics MCP Server

Expone herramientas de inteligencia de mercado agregada a clientes MCP.
Complementa mcp_server.py (que opera sobre listings individuales).

Tools:
  - resumen_mercado      → estadísticas generales del dataset
  - distribucion_precios → distribución de precios para una marca/modelo
  - tendencia_dolar      → evolución del dólar blue en los últimos N días

─────────────────────────────────────────────────
Instalación en Claude Desktop:
~/.config/Claude/claude_desktop_config.json

{
  "mcpServers": {
    "tasajusta-analytics": {
      "command": "uv",
      "args": ["--directory", "/ruta/a/tasajusta", "run", "mcp_analytics.py"],
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
import statistics

import httpx
from mcp.server import MCPServer

logger = logging.getLogger(__name__)

mcp = MCPServer("tasajusta-analytics")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")


async def _get(table: str, params: dict) -> list[dict]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL y SUPABASE_SERVICE_KEY no están configuradas")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def resumen_mercado() -> str:
    """Estadísticas generales del mercado: cantidad de listings, fuentes, precios y oportunidades."""
    try:
        rows = await _get("autos_usados", {
            "select": "source,precio_ars,oportunidad_score,scraped_at",
            "precio_ars": "not.is.null",
            "limit": "2000",
        })
    except Exception as e:
        return f"Error al consultar Supabase: {e}"

    if not rows:
        return "No hay datos en el dataset todavía."

    precios = [r["precio_ars"] for r in rows if r.get("precio_ars")]
    oportunidades = [r for r in rows if (r.get("oportunidad_score") or 0) >= 0.10]

    by_source: dict[str, int] = {}
    for r in rows:
        src = r.get("source") or "desconocida"
        by_source[src] = by_source.get(src, 0) + 1

    fechas = sorted(r["scraped_at"] for r in rows if r.get("scraped_at"))

    lines = [
        f"Dataset: {len(rows)} listings (muestra hasta 2000)",
        "",
        "── Fuentes ─────────────────────────────",
    ]
    for src, count in sorted(by_source.items(), key=lambda x: -x[1]):
        lines.append(f"  {src}: {count} listings")

    if precios:
        avg = int(statistics.mean(precios))
        med = int(statistics.median(precios))
        lines += [
            "",
            "── Precios (ARS) ───────────────────────",
            f"  Mínimo:  ${min(precios):,}",
            f"  Mediana: ${med:,}",
            f"  Promedio:${avg:,}",
            f"  Máximo:  ${max(precios):,}",
        ]

    lines += [
        "",
        "── Oportunidades (score > 10%) ─────────",
        f"  {len(oportunidades)} de {len(rows)} listings ({len(oportunidades)/len(rows)*100:.1f}%)",
    ]

    if fechas:
        lines += [
            "",
            "── Datos ───────────────────────────────",
            f"  Más antiguo: {fechas[0][:10]}",
            f"  Más reciente:{fechas[-1][:10]}",
        ]

    logger.info("resumen_mercado: %d rows", len(rows))
    return "\n".join(lines)


@mcp.tool()
async def distribucion_precios(
    marca: str,
    modelo: str | None = None,
) -> str:
    """Distribución estadística de precios para una marca/modelo específico.

    Args:
        marca: Marca del auto (ej: Toyota, Ford, Volkswagen)
        modelo: Modelo opcional (ej: Corolla, Focus). Sin modelo = toda la marca.
    """
    params: dict = {
        "select": "precio_ars,anio,provincia",
        "marca":  f"ilike.*{marca}*",
        "precio_ars": "not.is.null",
        "limit":  "500",
    }
    if modelo:
        params["modelo"] = f"ilike.*{modelo}*"

    try:
        rows = await _get("autos_usados", params)
    except Exception as e:
        return f"Error al consultar Supabase: {e}"

    titulo = f"{marca.title()} {modelo.title()}" if modelo else marca.title()

    if not rows:
        return f"No se encontraron listings para {titulo}."

    precios = sorted(r["precio_ars"] for r in rows if r.get("precio_ars"))
    if len(precios) < 2:
        return f"Solo {len(precios)} listing encontrado — no hay suficientes datos para distribución."

    qs = statistics.quantiles(precios, n=4)  # [p25, p50, p75]

    # Conteo por provincia
    by_prov: dict[str, int] = {}
    for r in rows:
        p = r.get("provincia") or "N/D"
        by_prov[p] = by_prov.get(p, 0) + 1
    top_provs = sorted(by_prov.items(), key=lambda x: -x[1])[:5]

    # Conteo por año
    by_anio: dict[int, int] = {}
    for r in rows:
        a = r.get("anio")
        if a:
            by_anio[a] = by_anio.get(a, 0) + 1
    anio_range = f"{min(by_anio)} – {max(by_anio)}" if by_anio else "N/D"

    lines = [
        f"Distribución de precios — {titulo}",
        f"({len(precios)} listings encontrados)",
        "",
        "── Distribución ────────────────────────",
        f"  Mínimo (p0):  ${precios[0]:,}",
        f"  P25:          ${int(qs[0]):,}",
        f"  Mediana (p50):${int(qs[1]):,}",
        f"  Promedio:     ${int(statistics.mean(precios)):,}",
        f"  P75:          ${int(qs[2]):,}",
        f"  Máximo (p100):${precios[-1]:,}",
        f"  Desvío std:   ${int(statistics.stdev(precios)):,}",
        "",
        f"── Años disponibles: {anio_range} ─────────",
        "",
        "── Top provincias ──────────────────────",
    ]
    for prov, count in top_provs:
        lines.append(f"  {prov}: {count}")

    logger.info("distribucion_precios: %s %s → %d rows", marca, modelo, len(precios))
    return "\n".join(lines)


@mcp.tool()
async def tendencia_dolar(dias: int = 30) -> str:
    """Evolución del dólar blue en los últimos N días.

    Args:
        dias: Cantidad de días a mostrar (default 30, máx 90)
    """
    try:
        rows = await _get("cotizaciones_dolar", {
            "select": "fecha,compra,venta",
            "casa":   "eq.blue",
            "order":  "fecha.desc",
            "limit":  str(min(dias, 90)),
        })
    except Exception as e:
        return f"Error al consultar Supabase: {e}"

    if not rows:
        return "No hay datos de cotizaciones en la base de datos todavía."

    rows_asc = list(reversed(rows))
    ventas = [r["venta"] for r in rows_asc if r.get("venta")]

    lines = [f"Dólar blue — últimos {len(rows_asc)} días registrados", ""]

    if ventas:
        primer = rows_asc[0]
        ultimo = rows_asc[-1]
        var_abs = ultimo["venta"] - primer["venta"]
        var_pct = (var_abs / primer["venta"]) * 100 if primer["venta"] else 0
        signo   = "+" if var_abs >= 0 else ""
        lines += [
            f"  Inicio: ${primer['venta']:,} ({primer['fecha']})",
            f"  Cierre: ${ultimo['venta']:,} ({ultimo['fecha']})",
            f"  Variación: {signo}${var_abs:,} ({signo}{var_pct:.1f}%)",
            f"  Min: ${min(ventas):,}  |  Max: ${max(ventas):,}",
            "",
            "── Detalle (últimos 10) ────────────────",
        ]

    for r in rows[:10]:
        lines.append(f"  {r['fecha']}  compra ${r['compra']:,}  venta ${r['venta']:,}")

    logger.info("tendencia_dolar: %d días", len(rows_asc))
    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
    mcp.run(transport="stdio")
