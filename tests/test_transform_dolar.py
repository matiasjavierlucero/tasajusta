"""Tests del transform: bronze → silver.

transform() es una función pura — mismo input, mismo output, sin efectos externos.
No necesita mocks: es el tipo de función más fácil de testear.
"""

from datetime import date

import polars as pl
import pytest

from etl.transform_dolar import transform
from tests.conftest import FAKE_RAW, TEST_DAY


def test_returns_polars_dataframe():
    """El resultado es siempre un DataFrame de Polars."""
    df = transform(FAKE_RAW, TEST_DAY)
    assert isinstance(df, pl.DataFrame)


def test_schema_tiene_tipos_correctos():
    """Cada columna tiene el tipo exacto que definimos — no inferencia."""
    df = transform(FAKE_RAW, TEST_DAY)
    assert df.schema == {
        "fecha": pl.Date,
        "casa": pl.String,
        "nombre": pl.String,
        "compra": pl.Float64,
        "venta": pl.Float64,
        "fetched_at": pl.String,
    }


def test_cantidad_de_filas_coincide_con_input():
    """Una fila por cotización — no se pierden ni duplican registros."""
    df = transform(FAKE_RAW, TEST_DAY)
    assert len(df) == len(FAKE_RAW["data"])


def test_fecha_es_el_dia_recibido():
    """La columna fecha usa el day que se le pasa, no la fecha del sistema."""
    otro_dia = date(2025, 1, 15)
    df = transform(FAKE_RAW, otro_dia)
    assert all(f == otro_dia for f in df["fecha"].to_list())


def test_valores_se_preservan_correctamente():
    """Los valores de compra y venta coinciden con los del input."""
    df = transform(FAKE_RAW, TEST_DAY)
    row_blue = df.filter(pl.col("casa") == "blue").row(0, named=True)
    assert row_blue["compra"] == 1505.0
    assert row_blue["venta"] == 1525.0
