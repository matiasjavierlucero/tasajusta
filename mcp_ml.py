"""
TasaJusta ML MCP Server

Expone herramientas de introspección del ciclo ML a clientes MCP:
Claude Desktop, Cursor, VS Code, n8n, etc.

Tools:
  - experimentos_recientes  → últimos N runs con métricas de test
  - mejor_modelo            → run con mejor R² en test set
  - detalle_run             → params + métricas completas de un run

Requiere el grupo de dependencias `tracking`:
  uv sync --group tracking

─────────────────────────────────────────────────
Instalación en Claude Desktop:
~/.config/Claude/claude_desktop_config.json

{
  "mcpServers": {
    "tasajusta-ml": {
      "command": "uv",
      "args": ["--directory", "/ruta/a/tasajusta", "run", "--group", "tracking", "mcp_ml.py"]
    }
  }
}
─────────────────────────────────────────────────
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from mcp.server import MCPServer

logger = logging.getLogger(__name__)

mcp = MCPServer("tasajusta-ml")

MLFLOW_DB   = Path(__file__).parent / "mlflow.db"
EXPERIMENT  = "tasajusta-lgbm"


def _client():
    try:
        import mlflow
    except ImportError:
        raise RuntimeError(
            "mlflow no está instalado. Instalá con: uv sync --group tracking"
        )
    mlflow.set_tracking_uri(f"sqlite:///{MLFLOW_DB.resolve()}")
    return mlflow.MlflowClient()


def _ts(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _fmt_run(run) -> str:
    m = run.data.metrics
    p = run.data.params
    r2   = m.get("test_r2",   float("nan"))
    mae  = m.get("test_mae",  float("nan"))
    rmse = m.get("test_rmse", float("nan"))
    mape = m.get("test_mape", float("nan"))
    gap  = m.get("overfitting_gap_mae", float("nan"))
    return (
        f"  ID:          {run.info.run_id[:8]}…\n"
        f"  Gold date:   {p.get('gold_date', '?')}\n"
        f"  Filas train: {p.get('train_size', '?')}\n"
        f"  R² test:     {r2:.3f}\n"
        f"  MAE test:    ${mae:,.0f}\n"
        f"  RMSE test:   ${rmse:,.0f}\n"
        f"  MAPE test:   {mape:.1f}%\n"
        f"  Gap MAE:     ${gap:,.0f}  (test − train; mayor = más overfitting)\n"
        f"  Fecha:       {_ts(run.info.start_time)}"
    )


def _get_experiment(client):
    exp = client.get_experiment_by_name(EXPERIMENT)
    if not exp:
        raise LookupError(
            f"Experimento '{EXPERIMENT}' no encontrado. "
            "¿Ya entrenaste algún modelo con uv run -m ml.train_lgbm?"
        )
    return exp


@mcp.tool()
async def experimentos_recientes(limite: int = 5) -> str:
    """Lista los últimos entrenamientos LightGBM con sus métricas de test.

    Args:
        limite: Cantidad de runs a mostrar (default 5, máx 20)
    """
    try:
        client = _client()
        exp    = _get_experiment(client)
    except (RuntimeError, LookupError) as e:
        return str(e)

    runs = client.search_runs(
        experiment_ids=[exp.experiment_id],
        order_by=["start_time DESC"],
        max_results=min(limite, 20),
    )

    if not runs:
        return "No hay runs registrados todavía."

    logger.info("experimentos_recientes: %d runs", len(runs))
    lines = [f"Últimos {len(runs)} entrenamientos (experimento: {EXPERIMENT}):\n"]
    for i, run in enumerate(runs, 1):
        lines.append(f"── #{i} ────────────────────────────────")
        lines.append(_fmt_run(run))
    return "\n".join(lines)


@mcp.tool()
async def mejor_modelo() -> str:
    """Devuelve el run con mejor R² en test set — el candidato a producción."""
    try:
        client = _client()
        exp    = _get_experiment(client)
    except (RuntimeError, LookupError) as e:
        return str(e)

    runs = client.search_runs(
        experiment_ids=[exp.experiment_id],
        order_by=["metrics.test_r2 DESC"],
        max_results=1,
    )

    if not runs:
        return "No hay runs registrados todavía."

    run = runs[0]
    r2  = run.data.metrics.get("test_r2", float("nan"))
    logger.info("mejor_modelo: run %s R²=%.3f", run.info.run_id[:8], r2)
    return f"Mejor modelo por R² test ({r2:.3f}):\n\n{_fmt_run(run)}"


@mcp.tool()
async def detalle_run(run_id: str) -> str:
    """Muestra todos los parámetros y métricas de un run específico.

    Args:
        run_id: ID del run — alcanza con los primeros 8 caracteres
    """
    try:
        client = _client()
        exp    = _get_experiment(client)
    except (RuntimeError, LookupError) as e:
        return str(e)

    if len(run_id) < 32:
        all_runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            max_results=50,
        )
        matches = [r for r in all_runs if r.info.run_id.startswith(run_id)]
        if not matches:
            return f"No se encontró ningún run que empiece con '{run_id}'."
        run = matches[0]
    else:
        run = client.get_run(run_id)

    m = run.data.metrics
    p = run.data.params

    lines = [
        f"Run:    {run.info.run_id}",
        f"Estado: {run.info.status}",
        f"Fecha:  {_ts(run.info.start_time)}",
        "",
        "── Parámetros ──────────────────────────",
    ]
    for k, v in sorted(p.items()):
        lines.append(f"  {k}: {v}")

    lines += ["", "── Métricas train ──────────────────────"]
    for k, label in [("train_r2", "R²"), ("train_mae", "MAE"), ("train_rmse", "RMSE"), ("train_mape", "MAPE")]:
        v = m.get(k)
        if v is not None:
            if "mae" in k or "rmse" in k:
                lines.append(f"  {label}: ${v:,.0f}")
            elif "mape" in k:
                lines.append(f"  {label}: {v:.1f}%")
            else:
                lines.append(f"  {label}: {v:.3f}")

    lines += ["", "── Métricas test ───────────────────────"]
    for k, label in [("test_r2", "R²"), ("test_mae", "MAE"), ("test_rmse", "RMSE"), ("test_mape", "MAPE")]:
        v = m.get(k)
        if v is not None:
            if "mae" in k or "rmse" in k:
                lines.append(f"  {label}: ${v:,.0f}")
            elif "mape" in k:
                lines.append(f"  {label}: {v:.1f}%")
            else:
                lines.append(f"  {label}: {v:.3f}")

    gap = m.get("overfitting_gap_mae")
    if gap is not None:
        lines += ["", f"── Overfitting gap (MAE test − train): ${gap:,.0f}"]

    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
    mcp.run(transport="stdio")
