"""
Extractor: dolarapi.com → MinIO bronze

Patrón: Extract puro. No transforma nada — guarda el JSON tal cual llega.
Clave de idempotencia: dolar/YYYY-MM-DD.json (mismo día = mismo archivo = overwrite).
"""

import json
import os
from datetime import date, datetime, timezone

import boto3
import httpx
from dotenv import load_dotenv

load_dotenv()

DOLAR_API_URL = "https://dolarapi.com/v1/dolares"

# El mismo script funciona en dev (MinIO) y en prod (S3 real) — solo cambia el .env.
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_USER = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin123")
BRONZE_BUCKET = os.getenv("MINIO_BUCKET", "tasajusta-bronze")


def get_s3_client():
    """Crea el cliente S3 apuntando a MinIO (dev) o S3 real (prod)."""
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_USER,
        aws_secret_access_key=MINIO_PASSWORD,
        config=boto3.session.Config(signature_version="s3v4"),
    )


def ensure_bucket_exists(s3_client) -> None:
    """Crea el bucket si no existe. Idempotente: no falla si ya existe."""
    try:
        s3_client.head_bucket(Bucket=BRONZE_BUCKET)
    except s3_client.exceptions.ClientError:
        s3_client.create_bucket(Bucket=BRONZE_BUCKET)
        print(f"Bucket '{BRONZE_BUCKET}' creado.")


def fetch_dolar_rates() -> list[dict]:
    """Llama a la API y devuelve la lista de cotizaciones."""
    response = httpx.get(DOLAR_API_URL, timeout=10)
    # raise_for_status lanza una excepción si el status es 4xx o 5xx
    response.raise_for_status()
    return response.json()


def save_to_bronze(rates: list[dict], s3_client) -> str:
    """
    Guarda el JSON crudo en la capa bronze.

    Clave de idempotencia: la key incluye solo la fecha, no hora ni UUID.
    Correr dos veces el mismo día sobreescribe el mismo archivo — sin duplicados.
    """
    today = date.today().isoformat()  # "2026-07-02"
    key = f"dolar/{today}.json"

    # Envolvemos los datos con metadata de ingesta
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),  # cuándo fetcheamos
        "source": DOLAR_API_URL,
        "data": rates,
    }

    s3_client.put_object(
        Bucket=BRONZE_BUCKET,
        Key=key,
        Body=json.dumps(payload, ensure_ascii=False, indent=2),
        ContentType="application/json",
    )
    return key


def run() -> None:
    print("Iniciando extractor de dólar...")

    s3 = get_s3_client()
    ensure_bucket_exists(s3)

    rates = fetch_dolar_rates()
    print(f"  → {len(rates)} cotizaciones obtenidas de la API.")

    key = save_to_bronze(rates, s3)
    print(f"  → Guardado en s3://{BRONZE_BUCKET}/{key}")
    print("Listo.")


if __name__ == "__main__":
    run()
