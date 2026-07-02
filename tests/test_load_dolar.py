"""Tests del load: silver → Postgres."""

import io
from unittest.mock import MagicMock, call, patch

import polars as pl

from etl.load_dolar import load_to_postgres, read_silver
from tests.conftest import TEST_DAY


class TestReadSilver:
    @patch("etl.load_dolar.boto3.client")
    def test_lee_key_correcta_de_minio(self, mock_boto3_client, fake_parquet_bytes):
        """Lee el archivo silver con la key correspondiente al día."""
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.get_object.return_value = {
            "Body": io.BytesIO(fake_parquet_bytes)
        }

        read_silver(mock_s3, TEST_DAY)

        mock_s3.get_object.assert_called_once_with(
            Bucket=mock_s3.get_object.call_args.kwargs["Bucket"],
            Key="silver/dolar/2026-07-02.parquet",
        )

    @patch("etl.load_dolar.boto3.client")
    def test_devuelve_dataframe(self, mock_boto3_client, fake_parquet_bytes):
        """El resultado es un DataFrame de Polars."""
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.get_object.return_value = {
            "Body": io.BytesIO(fake_parquet_bytes)
        }

        df = read_silver(mock_s3, TEST_DAY)

        assert isinstance(df, pl.DataFrame)


class TestLoadToPostgres:
    def test_ejecuta_create_table_y_upsert(self, fake_silver_df):
        """Crea la tabla si no existe y hace upsert de todas las filas."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        load_to_postgres(fake_silver_df, mock_conn)

        # CREATE TABLE IF NOT EXISTS debe correr siempre
        first_call_sql = mock_cursor.execute.call_args_list[0][0][0]
        assert "CREATE TABLE IF NOT EXISTS" in first_call_sql

        # executemany debe correr con todas las filas
        mock_cursor.executemany.assert_called_once()
        rows_arg = mock_cursor.executemany.call_args[0][1]
        assert len(rows_arg) == len(fake_silver_df)

    def test_hace_commit(self, fake_silver_df):
        """Confirma la transacción al final."""
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = MagicMock()

        load_to_postgres(fake_silver_df, mock_conn)

        mock_conn.commit.assert_called_once()

    def test_devuelve_cantidad_de_filas(self, fake_silver_df):
        """Devuelve el número de filas procesadas."""
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = MagicMock()

        n = load_to_postgres(fake_silver_df, mock_conn)

        assert n == len(fake_silver_df)
