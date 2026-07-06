"""
Scraper de vehículos usados: Kavak Argentina → S3 bronze.

Pagina /ar/usados/{marca}?page=N por las 10 marcas target.
HTML renderizado server-side — no hay API interna.

Precio: toma el último monto ≥ $1.000.000 en el card.
  - Auto outlet → precio con descuento (el último, no el de contado)
  - Auto normal → único precio listado

Output: kavak_autos/YYYY-MM-DD.json en el bronze bucket.
"""

import json
import os
import re
import time
from datetime import date, datetime, timezone

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from etl.infra import get_s3_client

load_dotenv()

BRONZE_BUCKET = os.getenv("MINIO_BUCKET", "tasajusta-bronze")

BASE_URL    = "https://www.kavak.com"
RATE_DELAY  = 1.0  # segundos entre páginas

MARCAS_TARGET = [
    "volkswagen", "toyota", "chevrolet", "ford",
    "renault", "peugeot", "fiat", "honda", "nissan", "citroen",
    "hyundai", "jeep", "kia", "bmw", "audi", "mitsubishi",
    "chery", "ram", "ds", "alfa-romeo", "baic", "dodge", "smart",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def parse_card(card) -> dict | None:
    href = card.get("href", "")
    if not href or "/ar/venta/" not in href:
        return None

    slug = href.split("/ar/venta/")[-1].rstrip("/")

    h3 = card.find("h3")
    if not h3:
        return None

    title_parts = h3.get_text(strip=True).split(" • ")
    if len(title_parts) < 2:
        return None
    marca  = title_parts[0].strip()
    modelo = title_parts[1].strip()

    # "2012 • 154.267 km • 1.6 PACK II • Manual"
    subtitle = card.find("p")
    anio, km = None, 0
    if subtitle:
        sub_parts = subtitle.get_text(strip=True).split(" • ")
        if sub_parts[0].isdigit():
            anio = int(sub_parts[0])
        if len(sub_parts) > 1:
            km_clean = sub_parts[1].replace("km", "").replace(".", "").strip()
            km = int(km_clean) if km_clean.isdigit() else 0

    # Todos los montos en el card — filtramos los que sean ≥ 1.000.000 (ARS precios)
    text  = card.get_text(separator="|", strip=True)
    montos = [
        int(m.replace(".", ""))
        for m in re.findall(r"\d{1,3}(?:\.\d{3})+", text)
        if int(m.replace(".", "")) >= 1_000_000
    ]
    if not montos:
        return None
    precio_ars = montos[-1]  # el último es el precio real (outlet o único)

    # Provincia: span del footer
    footer = card.find("span", class_=re.compile(r"footerInfo"))
    provincia = footer.get_text(strip=True) if footer else ""

    return {
        "cod":        f"kavak-{slug}",
        "marca":      marca,
        "modelo":     modelo,
        "condicion":  "Usado",
        "provincia":  provincia,
        "precio_ars": precio_ars,
        "anio":       anio,
        "km":         km,
        "url":        href,
        "segmento":   0,
        "source":     "kavak",
    }


def scrape_marca(marca: str, client: httpx.Client) -> list[dict]:
    results: list[dict] = []
    page = 0

    while True:
        url  = f"{BASE_URL}/ar/usados/{marca}?page={page}"
        resp = client.get(url, headers=HEADERS, timeout=15)

        if resp.status_code == 404:
            break
        resp.raise_for_status()

        soup  = BeautifulSoup(resp.text, "lxml")
        cards = soup.find_all("a", href=lambda h: h and "/ar/venta/" in h)

        if not cards:
            break

        parsed = [p for c in cards if (p := parse_card(c)) is not None]
        results.extend(parsed)

        # Paginación: si la página devuelve menos cards que la anterior, llegamos al fin
        # Kavak no siempre expone el total de páginas directamente
        if len(cards) < 20:
            break

        page += 1
        time.sleep(RATE_DELAY)

    return results


def run(day: date | None = None) -> None:
    day = day or date.today()
    print(f"Scrapeando Kavak Argentina — {day}...")

    s3     = get_s3_client()
    client = httpx.Client(follow_redirects=True)

    all_items: list[dict] = []
    seen_cods: set[str]   = set()

    for marca in MARCAS_TARGET:
        print(f"  → {marca}...", end=" ", flush=True)
        items   = scrape_marca(marca, client)
        # Deduplicar por cod en caso de listings que aparecen en múltiples marcas
        nuevos  = [i for i in items if i["cod"] not in seen_cods]
        seen_cods.update(i["cod"] for i in nuevos)
        all_items.extend(nuevos)
        print(f"{len(nuevos)} listings")
        time.sleep(RATE_DELAY)

    payload = {
        "source":     "kavak",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "data":       all_items,
    }

    key = f"kavak_autos/{day.isoformat()}.json"
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
