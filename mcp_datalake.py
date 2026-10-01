"""
TasaJusta Datalake MCP Server

Expone visibilidad del pipeline de datos (S3) a clientes MCP.
Útil para saber si los datos están frescos y qué modelo está en producción.

Tools:
  - estado_datalake  → última ingesta por capa (bronze/silver/gold) con timestamps
  - estado_modelos   → artefactos de modelos disponibles en S3

Requiere credenciales AWS (mismo mecanismo que el ETL):
  - Dev: variables MINIO_ENDPOINT + MINIO_ROOT_USER/PASSWORD en .env
  - Prod: IAM role / AWS SSO (sin credenciales explícitas)

─────────────────────────────────────────────────
Instalación en Claude Desktop:
~/.config/Claude/claude_desktop_config.json

{
  "mcpServers": {
    "tasajusta-datalake": {
      "command": "uv",
      "args": ["--directory", "/ruta/a/tasajusta", "run", "mcp_datalake.py"],
      "env": {
        "MINIO_BUCKET": "tasajusta-datalake-966940665955",
        "MODELS_BUCKET": "tasajusta-models-966940665955"
      }
    }
  }
}
─────────────────────────────────────────────────
"""

import logging
import os
from datetime import timezone

from mcp.server import MCPServer

logger = logging.getLogger(__name__)

mcp = MCPServer("tasajusta-datalake")

DATALAKE_BUCKET = os.getenv("MINIO_BUCKET", "tasajusta-datalake-966940665955")
MODELS_BUCKET   = os.getenv("MODELS_BUCKET", "tasajusta-models-966940665955")

LAYERS = [
    ("Bronze — vehículos DeRuedas", "vehiculos_usados/"),
    ("Bronze — vehículos Kavak",    "kavak_autos/"),
    ("Bronze — dólar",             "bronze/cotizaciones_dolar/"),
    ("Silver — autos usados",       "silver/autos_usados/"),
    ("Silver — Kavak",              "silver/kavak_autos/"),
    ("Gold — autos usados",         "gold/autos_usados/"),
]


def _s3():
    from etl.infra import get_s3_client
    return get_s3_client()


def _fmt_size(n: int) -> str:
    if n >= 1_048_576:
        return f"{n/1_048_576:.1f} MB"
    if n >= 1024:
        return f"{n/1024:.1f} KB"
    return f"{n} B"


def _last_object(s3_client, bucket: str, prefix: str) -> dict | None:
    """Devuelve el objeto más reciente bajo un prefix, o None si no existe."""
    resp = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    objects = resp.get("Contents", [])
    if not objects:
        return None
    return max(objects, key=lambda o: o["LastModified"])


@mcp.tool()
async def estado_datalake() -> str:
    """Muestra la última ingesta por capa del datalake (bronze/silver/gold) con timestamps y tamaños."""
    try:
        s3 = _s3()
    except Exception as e:
        return f"No se pudo conectar a S3/MinIO: {e}"

    lines = [f"Datalake: s3://{DATALAKE_BUCKET}", ""]

    all_missing = True
    for label, prefix in LAYERS:
        try:
            obj = _last_object(s3, DATALAKE_BUCKET, prefix)
        except Exception as e:
            lines.append(f"  {label}: ERROR — {e}")
            continue

        if obj is None:
            lines.append(f"  {label}: sin datos")
            continue

        all_missing = False
        key       = obj["Key"].split("/")[-1]
        ts        = obj["LastModified"].astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        size      = _fmt_size(obj["Size"])
        lines.append(f"  {label}")
        lines.append(f"    Archivo: {key}")
        lines.append(f"    Fecha:   {ts}  ({size})")

    if all_missing:
        lines.append("⚠ No se encontraron archivos. ¿Está configurado el bucket correcto?")

    logger.info("estado_datalake: bucket=%s", DATALAKE_BUCKET)
    return "\n".join(lines)


@mcp.tool()
async def estado_modelos() -> str:
    """Lista los artefactos de modelos ML disponibles en S3, ordenados del más reciente al más antiguo."""
    try:
        s3 = _s3()
    except Exception as e:
        return f"No se pudo conectar a S3/MinIO: {e}"

    lines = [f"Modelos: s3://{MODELS_BUCKET}", ""]

    for prefix, label in [("lgbm/", "LightGBM"), ("mlp/", "MLP PyTorch")]:
        try:
            resp    = s3.list_objects_v2(Bucket=MODELS_BUCKET, Prefix=prefix)
            objects = resp.get("Contents", [])
        except Exception as e:
            lines.append(f"  {label}: ERROR — {e}")
            continue

        if not objects:
            lines.append(f"  {label}: sin artefactos")
            continue

        objects_sorted = sorted(objects, key=lambda o: o["LastModified"], reverse=True)
        lines.append(f"── {label} ({len(objects_sorted)} versiones) ──────────────")

        for i, obj in enumerate(objects_sorted[:5]):
            key  = obj["Key"].split("/")[-1]
            ts   = obj["LastModified"].astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            size = _fmt_size(obj["Size"])
            tag  = " ← producción" if i == 0 else ""
            lines.append(f"  {key}  ({size})  {ts}{tag}")

        if len(objects_sorted) > 5:
            lines.append(f"  … y {len(objects_sorted) - 5} versiones más antiguas")

        lines.append("")

    logger.info("estado_modelos: bucket=%s", MODELS_BUCKET)
    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
    mcp.run(transport="stdio")
