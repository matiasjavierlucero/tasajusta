"""
Scraper de autos usados: DeRuedas → MinIO bronze.

Dos fases:
  1. Recolección: bus.asp?marca=X → URLs únicas de listings
  2. Detalle: por cada URL, extrae precio/año/km de los inputs ocultos

Respeta el Crawl-delay: 5s del robots.txt.
Idempotente: autos_usados/YYYY-MM-DD.json — reejecutar sobreescribe el mismo archivo.
"""

import json
import os
import re
import time
from datetime import date, datetime, timezone

import httpx
from dotenv import load_dotenv

from etl.infra import get_s3_client

load_dotenv()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
CRAWL_DELAY = 5  # segundos — respeta robots.txt Crawl-delay
BASE_URL = "https://www.deruedas.com.ar"

# 10 marcas = ~600 autos únicos, ~50 minutos de scraping
MARCAS = [
    "Volkswagen", "Toyota", "Chevrolet", "Ford", "Renault",
    "Peugeot", "Fiat", "Honda", "Nissan", "Citroen",
]

BRONZE_BUCKET = os.getenv("MINIO_BUCKET", "tasajusta-bronze")


def collect_listing_urls(marca: str, client: httpx.Client) -> set[str]:
    """Obtiene hasta 60 URLs únicas de listings para una marca vía bus.asp."""
    r = client.get(
        f"{BASE_URL}/bus.asp",
        params={
            "segmento": 0,
            "condicion": "Usados",
            "tipo": "Autos",
            "desde": 0,
            "marca": marca,
        },
        timeout=15,
    )
    r.raise_for_status()
    return set(re.findall(r"/vendo/[^\s\"<']+", r.text))


def parse_listing_url(path: str) -> dict | None:
    """
    Extrae marca, modelo, condicion y provincia del path de la URL.
    Ejemplo: /vendo/Volkswagen/Gol/Usado/Buenos-Aires?cod=12345
    """
    m = re.match(
        r"/vendo/([^/]+)/([^/]+)/([^/]+)/([^?]+)\?cod=(\d+)", path
    )
    if not m:
        return None
    return {
        "marca": m.group(1).replace("-", " "),
        "modelo": m.group(2).replace("-", " "),
        "condicion": m.group(3),
        "provincia": m.group(4).replace("-", " "),
        "cod": m.group(5),
    }


def scrape_detail(path: str, client: httpx.Client) -> dict | None:
    """
    Extrae precio, año y km de los inputs ocultos de la página de detalle.
    Devuelve None si la página no existe o faltan campos.
    """
    r = client.get(f"{BASE_URL}{path}", timeout=15)
    if r.status_code != 200:
        return None

    def extract_input(name: str) -> str | None:
        # Busca <input ... name="campo" ... value="valor">
        m = re.search(rf'name="{name}"[^>]+value="([^"]*)"', r.text)
        return m.group(1) if m else None

    precio = extract_input("precio")
    anio = extract_input("anio")
    km = extract_input("kilometraje")

    if not all([precio, anio, km]):
        return None

    return {
        "precio_ars": int(precio),
        "anio": int(anio),
        "km": int(km),
    }


def run() -> None:
    today = date.today().isoformat()
    print(f"=== Scraper DeRuedas — {today} ===")
    print(f"Marcas: {', '.join(MARCAS)}")
    print(f"Crawl-delay: {CRAWL_DELAY}s\n")

    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=BRONZE_BUCKET)
    except Exception:
        s3.create_bucket(Bucket=BRONZE_BUCKET)

    records = []

    with httpx.Client(headers=HEADERS, follow_redirects=True) as client:

        # ── Fase 1: recolectar URLs de listings ──────────────────────────
        print("[ Fase 1 ] Recolectando URLs de listings...")
        all_urls: set[str] = set()
        for marca in MARCAS:
            urls = collect_listing_urls(marca, client)
            nuevas = urls - all_urls
            all_urls |= urls
            print(f"  {marca}: {len(nuevas)} nuevas | acumulado: {len(all_urls)}")
            time.sleep(CRAWL_DELAY)

        total = len(all_urls)
        print(f"\n  Total URLs únicas: {total}\n")

        # ── Fase 2: scraping de detalle ───────────────────────────────────
        print("[ Fase 2 ] Scrapeando páginas de detalle...")
        for i, path in enumerate(sorted(all_urls), 1):
            meta = parse_listing_url(path)
            if not meta:
                continue

            detail = scrape_detail(path, client)
            if not detail:
                print(f"  [{i:3d}/{total}] SKIP  {meta['marca']} {meta['modelo']}")
                time.sleep(CRAWL_DELAY)
                continue

            record = {
                **meta,
                **detail,
                "url": f"{BASE_URL}{path}",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
            records.append(record)
            print(
                f"  [{i:3d}/{total}] OK  "
                f"{meta['marca']:12} {meta['modelo']:15} "
                f"{detail['anio']} — "
                f"${detail['precio_ars']:>12,} | {detail['km']:>7,} km"
            )
            time.sleep(CRAWL_DELAY)

    # ── Guardar en bronze ─────────────────────────────────────────────────
    print(f"\nRegistros obtenidos: {len(records)}")
    payload = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "source": BASE_URL,
        "marcas": MARCAS,
        "total": len(records),
        "data": records,
    }
    key = f"autos_usados/{today}.json"
    s3.put_object(
        Bucket=BRONZE_BUCKET,
        Key=key,
        Body=json.dumps(payload, ensure_ascii=False, indent=2),
        ContentType="application/json",
    )
    print(f"Guardado en s3://{BRONZE_BUCKET}/{key}")
    print("=== Listo ===")


if __name__ == "__main__":
    run()
