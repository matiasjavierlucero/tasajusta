"""Tests del extractor: dolarapi.com → MinIO bronze."""

from unittest.mock import MagicMock, patch

import pytest

from etl.extract_dolar import ensure_bucket_exists, fetch_dolar_rates, save_to_bronze
from tests.conftest import FAKE_RATES, TEST_DAY


class TestFetchDolarRates:
    @patch("etl.extract_dolar.httpx.get")
    def test_returns_list_from_api(self, mock_get):
        """Devuelve la lista de cotizaciones que retorna la API."""
        mock_get.return_value.json.return_value = FAKE_RATES

        result = fetch_dolar_rates()

        assert result == FAKE_RATES

    @patch("etl.extract_dolar.httpx.get")
    def test_raises_on_http_error(self, mock_get):
        """Si la API devuelve 4xx/5xx, raise_for_status propaga la excepción."""
        mock_get.return_value.raise_for_status.side_effect = Exception("503")

        with pytest.raises(Exception, match="503"):
            fetch_dolar_rates()


class TestSaveToBronze:
    @patch("etl.extract_dolar.date")
    def test_key_uses_date_for_idempotence(self, mock_date):
        """La key siempre es dolar/YYYY-MM-DD.json — garantía de idempotencia."""
        mock_date.today.return_value = TEST_DAY
        mock_s3 = MagicMock()

        save_to_bronze(FAKE_RATES, mock_s3)

        # Verificamos la key exacta que se usó en put_object
        call_kwargs = mock_s3.put_object.call_args.kwargs
        assert call_kwargs["Key"] == "dolar/2026-07-02.json"

    @patch("etl.extract_dolar.date")
    def test_payload_includes_fetched_at(self, mock_date):
        """El JSON guardado envuelve los datos con metadata de ingesta."""
        import json

        mock_date.today.return_value = TEST_DAY
        mock_s3 = MagicMock()

        save_to_bronze(FAKE_RATES, mock_s3)

        body = mock_s3.put_object.call_args.kwargs["Body"]
        payload = json.loads(body)
        assert "fetched_at" in payload
        assert "data" in payload
        assert payload["data"] == FAKE_RATES


class TestEnsureBucketExists:
    def test_creates_bucket_if_missing(self):
        """Si el bucket no existe (ClientError), lo crea."""
        from botocore.exceptions import ClientError

        mock_s3 = MagicMock()
        mock_s3.exceptions.ClientError = ClientError
        mock_s3.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket"
        )

        ensure_bucket_exists(mock_s3)

        mock_s3.create_bucket.assert_called_once()

    def test_does_not_recreate_existing_bucket(self):
        """Si el bucket ya existe, no llama a create_bucket."""
        mock_s3 = MagicMock()
        mock_s3.head_bucket.return_value = {}  # éxito — bucket existe

        ensure_bucket_exists(mock_s3)

        mock_s3.create_bucket.assert_not_called()
