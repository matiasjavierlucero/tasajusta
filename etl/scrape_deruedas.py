"""
Scraper de vehículos usados: DeRuedas → MinIO bronze.

Cubre los 3 segmentos (Autos, Utilitarios/Camionetas, Motos) y toda Argentina.
La URL base `bus.asp?segmento=X` sin provincia devuelve listings de todo el país.

Dos fases:
  1. Recolección: bus.asp?segmento=X → URLs únicas de listings (con paginación)
  2. Detalle: por cada URL extrae precio/año/km de los inputs ocultos

Respeta el Crawl-delay: 5s del robots.txt.
Idempotente: vehículos_usados/YYYY-MM-DD.json — reejecutar sobreescribe el mismo archivo.
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
CRAWL_DELAY = 5   # segundos — respeta robots.txt Crawl-delay
BASE_URL    = "https://www.deruedas.com.ar"
PAGE_SIZE   = 15  # resultados por página

# 0=Autos, 1=Utilitarios/Camionetas, 2=Motos
SEGMENTOS = {
    0: "Autos",
    1: "Utilitarios/Camionetas",
    2: "Motos",
}

BRONZE_BUCKET = os.getenv("MINIO_BUCKET", "tasajusta-bronze")

# IDs de provincia en DeRuedas (confirmados: van de 2 a 24)
PROVINCIA_IDS = range(2, 25)


def collect_listing_urls(segmento: int, provincia_id: int, client: httpx.Client) -> set[str]:
    """
    Pagina bus.asp?segmento=X&provincia=Y incrementando `desde`
    hasta que no aparezcan URLs nuevas.
    Sin filtro de provincia, DeRuedas devuelve solo los 30 destacados
    de la home y la paginación no avanza — por eso iteramos por provincia.
    """
    all_urls: set[str] = set()
    desde = 0

    while True:
        r = client.get(
            f"{BASE_URL}/bus.asp",
            params={"segmento": segmento, "provincia": provincia_id, "desde": desde},
            timeout=15,
        )
        r.raise_for_status()

        page_urls = set(re.findall(r"/vendo/[^\s\"<']+", r.text))
        nuevas    = page_urls - all_urls

        if not nuevas:
            break

        all_urls |= nuevas
        desde    += PAGE_SIZE
        time.sleep(CRAWL_DELAY)

    return all_urls


def parse_listing_url(path: str) -> dict | None:
    """
    Extrae marca, modelo, condicion y provincia del path de la URL.
    Ejemplo: /vendo/Volkswagen/Gol/Usado/Buenos-Aires?cod=12345
    """
    m = re.match(r"/vendo/([^/]+)/([^/]+)/([^/]+)/([^?]+)\?cod=(\d+)", path)
    if not m:
        return None
    return {
        "marca":     m.group(1).replace("-", " "),
        "modelo":    m.group(2).replace("-", " "),
        "condicion": m.group(3),
        "provincia": m.group(4).replace("-", " "),
        "cod":       m.group(5),
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
        m = re.search(rf'name="{name}"[^>]+value="([^"]*)"', r.text)
        return m.group(1) if m else None

    precio = extract_input("precio")
    anio   = extract_input("anio")
    km     = extract_input("kilometraje")

    if not all([precio, anio, km]):
        return None

    try:
        return {
            "precio_ars": int(precio),
            "anio":       int(anio),
            "km":         int(km),
        }
    except ValueError:
        return None


def run() -> None:
    today = date.today().isoformat()
    print(f"=== Scraper DeRuedas — {today} ===")
    print(f"Segmentos: {', '.join(f'{k}={v}' for k, v in SEGMENTOS.items())}")
    print(f"Cobertura: Toda Argentina | Crawl-delay: {CRAWL_DELAY}s\n")

    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=BRONZE_BUCKET)
    except Exception:
        s3.create_bucket(Bucket=BRONZE_BUCKET)

    records = []

    with httpx.Client(headers=HEADERS, follow_redirects=True) as client:

        for segmento, nombre in SEGMENTOS.items():

            # ── Fase 1: recolectar URLs — loop por provincia ──────────────
            print(f"[ Segmento {segmento} — {nombre} ]")
            print(f"  Recolectando URLs por provincia (IDs 2-24)...")
            urls: set[str] = set()
            for prov_id in PROVINCIA_IDS:
                prov_urls = collect_listing_urls(segmento, prov_id, client)
                nuevas    = prov_urls - urls
                if nuevas:
                    urls |= nuevas
                    print(f"    Provincia {prov_id:2d}: {len(nuevas):4d} nuevas | acumulado: {len(urls)}")
                time.sleep(CRAWL_DELAY)
            print(f"  URLs únicas totales: {len(urls)}")
            time.sleep(CRAWL_DELAY)

            # ── Fase 2: scraping de detalle ───────────────────────────────
            total = len(urls)
            ok = 0
            for i, path in enumerate(sorted(urls), 1):
                meta = parse_listing_url(path)
                if not meta:
                    continue

                detail = scrape_detail(path, client)
                if not detail:
                    print(f"  [{i:4d}/{total}] SKIP  {meta['marca']} {meta['modelo']}")
                    time.sleep(CRAWL_DELAY)
                    continue

                record = {
                    **meta,
                    **detail,
                    "segmento":  segmento,
                    "url":       f"{BASE_URL}{path}",
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                }
                records.append(record)
                ok += 1
                print(
                    f"  [{i:4d}/{total}] OK  "
                    f"{meta['marca']:12} {meta['modelo']:15} "
                    f"{detail['anio']} | "
                    f"${detail['precio_ars']:>12,} | {detail['km']:>7,} km | "
                    f"{meta['provincia']}"
                )
                time.sleep(CRAWL_DELAY)

            print(f"  → {ok}/{total} registros OK para {nombre}\n")

    # ── Guardar en bronze ─────────────────────────────────────────────────
    print(f"Total registros: {len(records)}")
    payload = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "source":     BASE_URL,
        "segmentos":  SEGMENTOS,
        "total":      len(records),
        "data":       records,
    }
    key = f"vehiculos_usados/{today}.json"
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
