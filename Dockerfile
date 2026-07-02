FROM python:3.11-slim

# libgomp1: requerida por LightGBM para paralelismo (OpenMP)
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# uv — instalador de paquetes, más rápido que pip
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /workspace

# Solo copiamos las deps — el código llega como volumen en runtime
COPY pyproject.toml .

# Instalar todas las deps en el Python del sistema
# torch CPU-only: ~200MB en lugar de ~2GB con CUDA
RUN uv pip install --system \
    "httpx>=0.27" \
    "boto3>=1.34" \
    "polars>=0.20" \
    "psycopg2-binary>=2.9" \
    "python-dotenv>=1.0" \
    "pandas>=2.0" \
    "pyarrow>=15.0" \
    "lightgbm>=4.0" \
    "scikit-learn>=1.5" \
    "fastapi>=0.111" \
    "uvicorn>=0.30" \
    && uv pip install --system torch \
       --extra-index-url https://download.pytorch.org/whl/cpu
