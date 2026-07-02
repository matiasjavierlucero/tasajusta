"""Tests del load: silver → Postgres para autos usados."""

import io
from unittest.mock import MagicMock

import polars as pl

from etl.load_autos import load_to_postgres, read_silver
from tests.conftest import TEST_DAY


class TestReadSilver:
    def test_lee_key_correcta_de_minio(self, fake_autos_parquet_bytes):
        """Lee el archivo silver con la key correspondiente al día."""
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            "Body": io.BytesIO(fake_autos_parquet_bytes)
        }

        read_silver(mock_s3, TEST_DAY)

        mock_s3.get_object.assert_called_once_with(
            Bucket=mock_s3.get_object.call_args.kwargs["Bucket"],
            Key="silver/autos_usados/2026-07-02.parquet",
        )

    def test_devuelve_dataframe(self, fake_autos_parquet_bytes):
        """El resultado es un DataFrame de Polars."""
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            "Body": io.BytesIO(fake_autos_parquet_bytes)
        }

        df = read_silver(mock_s3, TEST_DAY)

        assert isinstance(df, pl.DataFrame)


class TestLoadToPostgres:
    def test_ejecuta_create_table_y_upsert(self, fake_autos_df):
        """Crea la tabla si no existe y hace upsert de todas las filas."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        load_to_postgres(fake_autos_df, mock_conn)

        first_call_sql = mock_cursor.execute.call_args_list[0][0][0]
        assert "CREATE TABLE IF NOT EXISTS" in first_call_sql
        mock_cursor.executemany.assert_called_once()
        rows_arg = mock_cursor.executemany.call_args[0][1]
        assert len(rows_arg) == len(fake_autos_df)

    def test_hace_commit(self, fake_autos_df):
        """Confirma la transacción al final."""
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = MagicMock()

        load_to_postgres(fake_autos_df, mock_conn)

        mock_conn.commit.assert_called_once()

    def test_devuelve_cantidad_de_filas(self, fake_autos_df):
        """Devuelve el número de filas procesadas."""
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = MagicMock()

        n = load_to_postgres(fake_autos_df, mock_conn)

        assert n == len(fake_autos_df)

    def test_upsert_incluye_cod_como_primera_columna(self, fake_autos_df):
        """El upsert envía cod como primer elemento de cada fila (es la PK)."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        load_to_postgres(fake_autos_df, mock_conn)

        rows_arg = mock_cursor.executemany.call_args[0][1]
        cods = {row[0] for row in rows_arg}
        assert cods == {"12345", "67890"}
