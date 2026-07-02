"""Tests del pipeline: orquestación y fail-fast."""

from unittest.mock import patch, MagicMock
from datetime import date

import pytest

from etl.pipeline import run


class TestPipelineHappyPath:
    @patch("etl.pipeline.load_run")
    @patch("etl.pipeline.transform_run")
    @patch("etl.pipeline.extract_run")
    def test_ejecuta_los_tres_pasos_en_orden(
        self, mock_extract, mock_transform, mock_load
    ):
        """El pipeline llama a extract, transform y load, en ese orden."""
        run(date(2026, 7, 2))

        mock_extract.assert_called_once()
        mock_transform.assert_called_once_with(date(2026, 7, 2))
        mock_load.assert_called_once_with(date(2026, 7, 2))


class TestPipelineFailFast:
    @patch("etl.pipeline.load_run")
    @patch("etl.pipeline.transform_run")
    @patch("etl.pipeline.extract_run")
    def test_si_extract_falla_no_corre_transform_ni_load(
        self, mock_extract, mock_transform, mock_load
    ):
        """Si extract falla, transform y load no corren."""
        mock_extract.side_effect = Exception("API caída")

        with pytest.raises(SystemExit):
            run(date(2026, 7, 2))

        mock_transform.assert_not_called()
        mock_load.assert_not_called()

    @patch("etl.pipeline.load_run")
    @patch("etl.pipeline.transform_run")
    @patch("etl.pipeline.extract_run")
    def test_si_transform_falla_no_corre_load(
        self, mock_extract, mock_transform, mock_load
    ):
        """Si transform falla, load no corre."""
        mock_transform.side_effect = Exception("Parquet corrupto")

        with pytest.raises(SystemExit):
            run(date(2026, 7, 2))

        mock_load.assert_not_called()
