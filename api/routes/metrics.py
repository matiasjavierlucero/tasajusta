import os

import httpx
from fastapi import APIRouter, Request

router = APIRouter()

SUPABASE_URL  = os.getenv("SUPABASE_URL")
SUPABASE_KEY  = os.getenv("SUPABASE_SERVICE_KEY")
OPP_THRESHOLD = 0.10


def _count(params: dict | None = None) -> int | None:
    """Cuenta filas en autos_usados vía HEAD + Prefer: count=exact."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        resp = httpx.head(
            f"{SUPABASE_URL}/rest/v1/autos_usados",
            headers={
                "apikey":        SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Prefer":        "count=exact",
            },
            params=params or {},
            timeout=5,
        )
        # Content-Range: */156  (cuando no hay filas devueltas)
        return int(resp.headers.get("content-range", "*/0").split("/")[-1])
    except Exception:
        return None


def _latest_scrape_date() -> str | None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/autos_usados",
            headers={
                "apikey":        SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            },
            params={"select": "fecha", "order": "fecha.desc", "limit": "1"},
            timeout=5,
        )
        data = resp.json()
        return data[0]["fecha"] if data else None
    except Exception:
        return None


@router.get("/metrics")
def metrics(request: Request):
    state = request.app.state
    return {
        "predictions_served":    getattr(state, "predictions_served", 0),
        "threshold_oportunidad": OPP_THRESHOLD,
        "total_autos":           _count(),
        "total_oportunidades":   _count({"oportunidad_score": f"gt.{OPP_THRESHOLD}"}),
        "ultima_fecha_scraping": _latest_scrape_date(),
        "started_at":            getattr(state, "started_at", None),
    }
