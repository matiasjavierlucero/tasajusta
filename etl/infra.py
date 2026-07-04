"""
Factories de clientes de infraestructura compartidos entre módulos ETL.

Por qué acá y no en cada módulo: get_s3_client() era idéntica en 4 archivos.
Centralizar evita que un cambio de credencial o endpoint se rompa en 4 lugares.
"""

import os
import socket
import urllib.parse

import boto3
import psycopg2
from dotenv import load_dotenv

load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")  # None = S3 real, valor = MinIO dev
MINIO_USER = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin123")

DATABASE_URL = os.getenv("DATABASE_URL")


def get_s3_client():
    """Cliente boto3 apuntando a MinIO (dev) o S3 real (prod) — solo cambia el .env."""
    if MINIO_ENDPOINT:
        return boto3.client(
            "s3",
            endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=MINIO_USER,
            aws_secret_access_key=MINIO_PASSWORD,
            config=boto3.session.Config(signature_version="s3v4"),
        )
    #  Sin endpoint_url, boto3 usa el credential chain de AWS:
    # variables de entorno → IAM role del Lambda → ~/.aws/credentials
    return boto3.client("s3")


def get_pg_connection():
    """Conexión psycopg2 a Postgres. Usar con context manager (with get_pg_connection())."""
    parsed = urllib.parse.urlparse(DATABASE_URL)
    host   = parsed.hostname

    # libpq prefiere IPv6 cuando DNS devuelve ambas (AAAA + A). En Docker y GitHub
    # Actions la dirección IPv6 de Supabase no es alcanzable → forzamos IPv4.
    _local = {"localhost", "127.0.0.1", "postgres"}
    if host and host not in _local:
        try:
            host = socket.getaddrinfo(host, None, socket.AF_INET)[0][4][0]
        except socket.gaierror:
            host = parsed.hostname  # fallback al hostname original

    return psycopg2.connect(
        host=host,
        port=parsed.port or 5432,
        dbname=parsed.path.lstrip("/"),
        user=parsed.username,
        password=parsed.password,
    )
