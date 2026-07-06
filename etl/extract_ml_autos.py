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
RATE_DELAY  = 0.3        # segundos entre requests

MARCAS_TARGET = {
    "Volkswagen", "Toyota", "Chevrolet", "Ford",
    "Renault", "Peugeot", "Fiat", "Honda", "Nissan", "Citroen",
}


def get_brand_filter_ids(client: httpx.Client) -> dict[str, str]:
    """
    Hace una búsqueda mínima para obtener los filter IDs de cada marca.
    El search de ML es público — no requiere autenticación.
    Retorna {nombre_marca: filter_id} solo para las marcas que nos interesan.
    """
    resp = client.get(
        f"{ML_BASE_URL}/sites/MLA/search",
        params={"category": CATEGORY, "limit": 1},
        timeout=15,
    )
    resp.raise_for_status()

    for f in resp.json().get("available_filters", []):
        if f["id"] == "BRAND":
            return {
                v["name"]: v["id"]
                for v in f["values"]
                if v["name"] in MARCAS_TARGET
            }
    return {}


def fetch_brand_listings(brand_id: str, client: httpx.Client) -> list[dict]:
    """Pagina todos los listings de una marca hasta el límite de 1000 de la API."""
    results: list[dict] = []
    limit = 50

    for offset in range(0, 1000, limit):
        resp = client.get(
            f"{ML_BASE_URL}/sites/MLA/search",
            params={
                "category": CATEGORY,
                "BRAND":    brand_id,
                "limit":    limit,
                "offset":   offset,
            },
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

    brand_ids = get_brand_filter_ids(client)
    marcas_encontradas = list(brand_ids.keys())
    marcas_faltantes   = MARCAS_TARGET - set(marcas_encontradas)
    print(f"  → Marcas encontradas en ML: {marcas_encontradas}")
    if marcas_faltantes:
        print(f"  ⚠ Marcas sin listings en ML: {marcas_faltantes}")

    all_items: list[dict] = []

    for marca_nombre, brand_id in brand_ids.items():
        print(f"  → {marca_nombre}...", end=" ", flush=True)
        raw    = fetch_brand_listings(brand_id, client)
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
