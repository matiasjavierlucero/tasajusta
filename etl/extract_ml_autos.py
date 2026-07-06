"""
Extract: MercadoLibre API → MinIO bronze.

Obtiene listings de autos usados de Argentina via la API oficial de ML.
Filtra por las 10 marcas del proyecto y skippea listings en USD.
Pagina hasta 1000 resultados por marca (límite de la API sin quota extendida).

Output: ml_autos_usados/YYYY-MM-DD.json en el bronze bucket.
"""

import json
import os
import time
from datetime import date, datetime, timezone

import httpx
from dotenv import load_dotenv

from etl.infra import get_s3_client

load_dotenv()

BRONZE_BUCKET = os.getenv("MINIO_BUCKET", "tasajusta-bronze")

ML_BASE_URL = "https://api.mercadolibre.com"
CATEGORY    = "MLA1743"  # Autos y Camionetas — Argentina
RATE_DELAY  = 0.5        # segundos entre requests

MARCAS_TARGET = [
    "Volkswagen", "Toyota", "Chevrolet", "Ford",
    "Renault", "Peugeot", "Fiat", "Honda", "Nissan", "Citroen",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json",
    "Accept-Language": "es-AR,es;q=0.9",
}


def fetch_marca_listings(marca: str, client: httpx.Client) -> list[dict]:
    """
    Busca listings por nombre de marca usando el parámetro q.
    Pagina hasta 1000 resultados (límite de la API).
    """
    results: list[dict] = []
    limit = 50

    for offset in range(0, 1000, limit):
        resp = client.get(
            f"{ML_BASE_URL}/sites/MLA/search",
            params={
                "q":        marca,
                "category": CATEGORY,
                "limit":    limit,
                "offset":   offset,
            },
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data  = resp.json()
        batch = data["results"]

        if not batch:
            break

        results.extend(batch)

        if offset + len(batch) >= data["paging"]["total"]:
            break

        time.sleep(RATE_DELAY)

    return results


def parse_item(item: dict) -> dict | None:
    """
    Normaliza un item de la API de ML al schema compartido con DeRuedas.
    Retorna None para listings en USD (los skipeamos).
    """
    if item.get("currency_id") != "ARS":
        return None

    attrs = {a["id"]: a.get("value_name") for a in item.get("attributes", [])}

    try:
        anio = int(attrs["VEHICLE_YEAR"]) if attrs.get("VEHICLE_YEAR") else None
    except (ValueError, TypeError):
        anio = None

    try:
        km = int(attrs["KILOMETERS"]) if attrs.get("KILOMETERS") else 0
    except (ValueError, TypeError):
        km = 0

    marca  = attrs.get("BRAND", "").strip()
    modelo = (attrs.get("MODEL") or item.get("title", "")).strip()

    provincia = (
        item.get("seller_address", {})
            .get("state", {})
            .get("name", "")
    )

    return {
        "cod":        item["id"],
        "marca":      marca,
        "modelo":     modelo,
        "condicion":  "Nuevo" if item.get("condition") == "new" else "Usado",
        "provincia":  provincia,
        "precio_ars": int(item["price"]),
        "anio":       anio,
        "km":         km,
        "url":        item.get("permalink", ""),
        "segmento":   0,
    }


def run(day: date | None = None) -> None:
    day = day or date.today()
    print(f"Extrayendo autos de MercadoLibre — {day}...")

    s3     = get_s3_client()
    client = httpx.Client()

    all_items: list[dict] = []

    for marca in MARCAS_TARGET:
        print(f"  → {marca}...", end=" ", flush=True)
        raw    = fetch_marca_listings(marca, client)
        parsed = [p for item in raw if (p := parse_item(item)) is not None]
        print(f"{len(parsed)} listings ARS (de {len(raw)} totales)")
        all_items.extend(parsed)
        time.sleep(RATE_DELAY)

    payload = {
        "source":     "mercadolibre",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "data":       all_items,
    }

    key = f"ml_autos_usados/{day.isoformat()}.json"
    s3.put_object(
        Bucket=BRONZE_BUCKET,
        Key=key,
        Body=json.dumps(payload, ensure_ascii=False),
        ContentType="application/json",
    )
    print(f"  → {len(all_items)} items guardados en s3://{BRONZE_BUCKET}/{key}")
    print("Listo.")


if __name__ == "__main__":
    run()
