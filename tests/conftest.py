"""Fixtures y datos compartidos entre todos los tests."""

import io
from datetime import date

import polars as pl
import pytest

# Datos que simula devolver dolarapi.com
FAKE_RATES = [
    {"casa": "blue", "nombre": "Blue", "compra": 1505.0, "venta": 1525.0},
    {"casa": "oficial", "nombre": "Oficial", "compra": 1460.0, "venta": 1510.0},
]

# Payload completo tal como se guarda en bronze
FAKE_RAW = {
    "fetched_at": "2026-07-02T13:00:00+00:00",
    "source": "https://dolarapi.com/v1/dolares",
    "data": FAKE_RATES,
}

TEST_DAY = date(2026, 7, 2)


@pytest.fixture
def fake_silver_df() -> pl.DataFrame:
    """DataFrame con el schema de silver — usado en tests de load."""
    return pl.DataFrame({
        "fecha": [TEST_DAY, TEST_DAY],
        "casa": ["blue", "oficial"],
        "nombre": ["Blue", "Oficial"],
        "compra": [1505.0, 1460.0],
        "venta": [1525.0, 1510.0],
        "fetched_at": ["2026-07-02T13:00:00+00:00", "2026-07-02T13:00:00+00:00"],
    }).with_columns(pl.col("fecha").cast(pl.Date))


@pytest.fixture
def fake_parquet_bytes(fake_silver_df) -> bytes:
    """El DataFrame de silver serializado como Parquet — para mockear MinIO."""
    buf = io.BytesIO()
    fake_silver_df.write_parquet(buf)
    return buf.getvalue()
