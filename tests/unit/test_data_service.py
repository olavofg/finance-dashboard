"""Tests for data_service.py — Google Sheets data access layer.

All tests mock gspread; no network calls are made.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from constants import SUMMARY_COLUMNS
from data_service import (
    _batch_fetch_cells,
    _build_summary_dataframe,
    _filter_valid_sheets,
    _open_spreadsheet,
    _parse_sheet_values,
    load_monthly_financial_summary,
)
from tests.unit.conftest import make_batch_response, _make_worksheet


FAKE_URL = "https://docs.google.com/spreadsheets/d/fake/edit"


# ---------------------------------------------------------------------------
# _open_spreadsheet
# ---------------------------------------------------------------------------

class TestOpenSpreadsheet:
    def test_success(self, mock_gc_3):
        ss, ws, err = _open_spreadsheet(mock_gc_3, FAKE_URL)
        assert err is None
        assert len(ws) == 3

    def test_permission_denied(self, mock_gc_open_error):
        ss, ws, err = _open_spreadsheet(mock_gc_open_error, FAKE_URL)
        assert ss is None
        assert ws is None
        assert "Erro ao abrir" in err

    def test_bad_url(self):
        gc = MagicMock()
        gc.open_by_url.side_effect = Exception("Invalid URL")
        _, _, err = _open_spreadsheet(gc, "not-a-url")
        assert "Erro ao abrir" in err


# ---------------------------------------------------------------------------
# _filter_valid_sheets
# ---------------------------------------------------------------------------

class TestFilterValidSheets:
    def test_all_valid(self):
        worksheets = [_make_worksheet(n) for n in ["Janeiro 2024", "Fevereiro 2024"]]
        result = _filter_valid_sheets(worksheets)
        assert len(result) == 2

    def test_mixed_valid_and_invalid(self):
        worksheets = [
            _make_worksheet("Janeiro 2024"),
            _make_worksheet("Resumo"),
            _make_worksheet("Dashboard"),
            _make_worksheet("Fevereiro 2024"),
            _make_worksheet("Config"),
        ]
        result = _filter_valid_sheets(worksheets)
        assert len(result) == 2
        assert result[0][0] == "Janeiro 2024"
        assert result[1][0] == "Fevereiro 2024"

    def test_no_valid_sheets(self):
        worksheets = [_make_worksheet("Resumo"), _make_worksheet("Dashboard")]
        result = _filter_valid_sheets(worksheets)
        assert result == []

    def test_empty_list(self):
        assert _filter_valid_sheets([]) == []

    def test_duplicate_month_names(self):
        worksheets = [_make_worksheet("Janeiro 2024"), _make_worksheet("Janeiro 2024")]
        result = _filter_valid_sheets(worksheets)
        assert len(result) == 2  # both pass filter; dedup is not the filter's job


# ---------------------------------------------------------------------------
# _batch_fetch_cells
# ---------------------------------------------------------------------------

class TestBatchFetchCells:
    def test_success(self):
        spreadsheet = MagicMock()
        sheet_info = [("Janeiro 2024", None), ("Fevereiro 2024", None)]
        spreadsheet.values_batch_get.return_value = make_batch_response([
            ("R$ 3.000,00", "R$ 8.000,00"),
            ("R$ 4.000,00", "R$ 9.000,00"),
        ])
        ranges, err = _batch_fetch_cells(spreadsheet, sheet_info)
        assert err is None
        assert len(ranges) == 4  # 2 sheets × 2 cells

    def test_api_error(self):
        spreadsheet = MagicMock()
        spreadsheet.values_batch_get.side_effect = Exception("Quota exceeded")
        sheet_info = [("Janeiro 2024", None)]
        ranges, err = _batch_fetch_cells(spreadsheet, sheet_info)
        assert ranges is None
        assert "Erro ao buscar" in err

    def test_empty_sheet_list(self):
        spreadsheet = MagicMock()
        spreadsheet.values_batch_get.return_value = {"valueRanges": []}
        ranges, err = _batch_fetch_cells(spreadsheet, [])
        assert err is None
        assert ranges == []


# ---------------------------------------------------------------------------
# _parse_sheet_values
# ---------------------------------------------------------------------------

class TestParseSheetValues:
    def test_normal_values(self):
        sheet_info = [("Janeiro 2024", None)]
        value_ranges = [
            {"values": [["R$ 3.500,00"]]},
            {"values": [["R$ 8.000,00"]]},
        ]
        data, warnings = _parse_sheet_values(sheet_info, value_ranges)
        assert len(data) == 1
        assert data[0]["Total de Gastos"] == 3500.0
        assert data[0]["Total de Receita"] == 8000.0
        assert warnings == []

    def test_empty_cells_default_to_zero(self):
        sheet_info = [("Janeiro 2024", None)]
        value_ranges = [{}, {}]
        data, warnings = _parse_sheet_values(sheet_info, value_ranges)
        assert data[0]["Total de Gastos"] == 0.0
        assert data[0]["Total de Receita"] == 0.0

    def test_invalid_expense_warns(self):
        sheet_info = [("Janeiro 2024", None)]
        value_ranges = [
            {"values": [["abc"]]},
            {"values": [["R$ 8.000,00"]]},
        ]
        data, warnings = _parse_sheet_values(sheet_info, value_ranges)
        assert data[0]["Total de Gastos"] == 0.0
        assert len(warnings) == 1
        assert "Formato inválido" in warnings[0]
        assert "gastos" in warnings[0]

    def test_invalid_income_warns(self):
        sheet_info = [("Janeiro 2024", None)]
        value_ranges = [
            {"values": [["R$ 3.000,00"]]},
            {"values": [["not_a_number"]]},
        ]
        data, warnings = _parse_sheet_values(sheet_info, value_ranges)
        assert data[0]["Total de Receita"] == 0.0
        assert len(warnings) == 1
        assert "receita" in warnings[0]

    def test_both_invalid(self):
        sheet_info = [("Janeiro 2024", None)]
        value_ranges = [
            {"values": [["abc"]]},
            {"values": [["xyz"]]},
        ]
        data, warnings = _parse_sheet_values(sheet_info, value_ranges)
        assert data[0]["Total de Gastos"] == 0.0
        assert data[0]["Total de Receita"] == 0.0
        assert len(warnings) == 2

    def test_missing_value_ranges(self):
        """Fewer value_ranges than expected (truncated API response)."""
        sheet_info = [("Janeiro 2024", None), ("Fevereiro 2024", None)]
        value_ranges = [
            {"values": [["R$ 3.000,00"]]},
            {"values": [["R$ 8.000,00"]]},
            # Feb data missing entirely
        ]
        data, warnings = _parse_sheet_values(sheet_info, value_ranges)
        assert len(data) == 2
        # Feb should default to 0.0
        assert data[1]["Total de Gastos"] == 0.0
        assert data[1]["Total de Receita"] == 0.0

    def test_multiple_sheets(self):
        sheet_info = [("Janeiro 2024", None), ("Fevereiro 2024", None), ("Março 2024", None)]
        value_ranges = [
            {"values": [["R$ 3.500,00"]]}, {"values": [["R$ 8.000,00"]]},
            {"values": [["R$ 4.200,50"]]}, {"values": [["R$ 8.500,00"]]},
            {"values": [["R$ 3.000,00"]]}, {"values": [["R$ 9.000,00"]]},
        ]
        data, warnings = _parse_sheet_values(sheet_info, value_ranges)
        assert len(data) == 3
        assert warnings == []


# ---------------------------------------------------------------------------
# _build_summary_dataframe
# ---------------------------------------------------------------------------

class TestBuildSummaryDataframe:
    def test_normal_data(self):
        all_data = [
            {"Mês": "Janeiro 2024", "Total de Gastos": 3500, "Total de Receita": 8000,
             "Data do Mês": "2024-01-01"},
            {"Mês": "Fevereiro 2024", "Total de Gastos": 4000, "Total de Receita": 10000,
             "Data do Mês": "2024-02-01"},
        ]
        df, warnings = _build_summary_dataframe(all_data, [])
        assert len(df) == 2
        assert "Economia" in df.columns
        assert "Taxa de Economia (%)" in df.columns
        assert df.iloc[0]["Economia"] == 4500.0
        assert df.iloc[1]["Economia"] == 6000.0

    def test_savings_rate_calculation(self):
        all_data = [
            {"Mês": "Janeiro 2024", "Total de Gastos": 5000, "Total de Receita": 10000,
             "Data do Mês": "2024-01-01"},
        ]
        df, _ = _build_summary_dataframe(all_data, [])
        assert df.iloc[0]["Taxa de Economia (%)"] == pytest.approx(50.0)

    def test_zero_income_no_division_error(self):
        all_data = [
            {"Mês": "Janeiro 2024", "Total de Gastos": 3000, "Total de Receita": 0,
             "Data do Mês": "2024-01-01"},
        ]
        df, warnings = _build_summary_dataframe(all_data, [])
        assert df.iloc[0]["Taxa de Economia (%)"] == 0

    def test_negative_savings(self):
        all_data = [
            {"Mês": "Dezembro 2024", "Total de Gastos": 9000, "Total de Receita": 8500,
             "Data do Mês": "2024-12-01"},
        ]
        df, _ = _build_summary_dataframe(all_data, [])
        assert df.iloc[0]["Economia"] == -500.0
        assert df.iloc[0]["Taxa de Economia (%)"] < 0

    def test_sorted_by_date(self):
        all_data = [
            {"Mês": "Março 2024", "Total de Gastos": 3000, "Total de Receita": 9000,
             "Data do Mês": "2024-03-01"},
            {"Mês": "Janeiro 2024", "Total de Gastos": 3500, "Total de Receita": 8000,
             "Data do Mês": "2024-01-01"},
        ]
        df, _ = _build_summary_dataframe(all_data, [])
        assert df.iloc[0]["Mês"] == "Janeiro 2024"
        assert df.iloc[1]["Mês"] == "Março 2024"

    def test_empty_data_returns_warning(self):
        from constants import SUMMARY_COLUMNS
        empty = [{col: None for col in ['Mês', 'Total de Gastos', 'Total de Receita', 'Data do Mês']}]
        df = pd.DataFrame(empty)
        df['Data do Mês'] = pd.to_datetime(df['Data do Mês'], errors='coerce')
        # Simulates the real flow: dropna removes all rows
        df, warnings = _build_summary_dataframe(
            [{'Mês': 'Bad', 'Total de Gastos': 0, 'Total de Receita': 0, 'Data do Mês': 'not-a-date'}],
            [],
        )
        assert df.empty
        assert any("Nenhum dado válido" in w for w in warnings)

    def test_invalid_date_rows_dropped(self):
        all_data = [
            {"Mês": "Janeiro 2024", "Total de Gastos": 3500, "Total de Receita": 8000,
             "Data do Mês": "2024-01-01"},
            {"Mês": "Bad Month", "Total de Gastos": 1000, "Total de Receita": 5000,
             "Data do Mês": "not-a-date"},
        ]
        df, _ = _build_summary_dataframe(all_data, [])
        assert len(df) == 1


# ---------------------------------------------------------------------------
# load_monthly_financial_summary (integration with mocks)
# ---------------------------------------------------------------------------

class TestLoadMonthlyFinancialSummary:
    @patch("data_service.st")
    def test_24_months_full_pipeline(self, mock_st, mock_gc_24):
        df, warnings = load_monthly_financial_summary.__wrapped__(mock_gc_24, FAKE_URL)
        assert len(df) == 24
        expected_cols = {"Mês", "Total de Gastos", "Total de Receita", "Economia", "Taxa de Economia (%)"}
        assert expected_cols.issubset(set(df.columns))
        assert warnings == []

    @patch("data_service.st")
    def test_3_months(self, mock_st, mock_gc_3):
        df, warnings = load_monthly_financial_summary.__wrapped__(mock_gc_3, FAKE_URL)
        assert len(df) == 3
        assert df.iloc[0]["Total de Gastos"] == 3500.0
        assert df.iloc[0]["Total de Receita"] == 8000.0

    @patch("data_service.st")
    def test_open_error(self, mock_st, mock_gc_open_error):
        df, warnings = load_monthly_financial_summary.__wrapped__(mock_gc_open_error, FAKE_URL)
        assert df.empty
        assert len(warnings) == 1
        assert "Erro ao abrir" in warnings[0]

    @patch("data_service.st")
    def test_batch_error(self, mock_st, mock_gc_batch_error):
        df, warnings = load_monthly_financial_summary.__wrapped__(mock_gc_batch_error, FAKE_URL)
        assert df.empty
        assert any("Erro ao buscar" in w for w in warnings)

    @patch("data_service.st")
    def test_no_valid_tabs(self, mock_st, mock_gc_only_invalid_tabs):
        df, warnings = load_monthly_financial_summary.__wrapped__(mock_gc_only_invalid_tabs, FAKE_URL)
        assert df.empty
        assert any("Nenhuma aba" in w for w in warnings)

    @patch("data_service.st")
    def test_mixed_valid_invalid_tabs(self, mock_st, mock_gc_with_invalid_tabs):
        df, warnings = load_monthly_financial_summary.__wrapped__(mock_gc_with_invalid_tabs, FAKE_URL)
        assert len(df) == 2  # only Jan + Feb, invalid tabs ignored

    @patch("data_service.st")
    def test_empty_cells(self, mock_st, mock_gc_empty_cells):
        df, warnings = load_monthly_financial_summary.__wrapped__(mock_gc_empty_cells, FAKE_URL)
        assert len(df) == 2
        # Both empty → defaults to 0.0
        assert df.iloc[0]["Total de Gastos"] == 0.0
        assert df.iloc[0]["Total de Receita"] == 0.0

    @patch("data_service.st")
    def test_invalid_cell_values(self, mock_st, mock_gc_invalid_values):
        df, warnings = load_monthly_financial_summary.__wrapped__(mock_gc_invalid_values, FAKE_URL)
        assert len(df) == 2
        assert len(warnings) == 2  # one per invalid cell
        # Invalid values default to 0.0
        assert df.iloc[0]["Total de Gastos"] == 0.0
        assert df.iloc[1]["Total de Receita"] == 0.0

    @patch("data_service.st")
    def test_zero_income_savings_rate(self, mock_st, mock_gc_zero_income):
        df, warnings = load_monthly_financial_summary.__wrapped__(mock_gc_zero_income, FAKE_URL)
        zero_row = df[df["Total de Receita"] == 0.0].iloc[0]
        assert zero_row["Taxa de Economia (%)"] == 0

    @patch("data_service.st")
    def test_single_month(self, mock_st, mock_gc_single_month):
        df, warnings = load_monthly_financial_summary.__wrapped__(mock_gc_single_month, FAKE_URL)
        assert len(df) == 1
        assert df.iloc[0]["Mês"] == "Março 2025"

    @patch("data_service.st")
    def test_negative_savings(self, mock_st, mock_gc_negative_savings):
        df, warnings = load_monthly_financial_summary.__wrapped__(mock_gc_negative_savings, FAKE_URL)
        assert (df["Economia"] < 0).all()
        assert (df["Taxa de Economia (%)"] < 0).all()

    @patch("data_service.st")
    def test_24_months_sorted_chronologically(self, mock_st, mock_gc_24):
        df, _ = load_monthly_financial_summary.__wrapped__(mock_gc_24, FAKE_URL)
        dates = df["Data do Mês"].tolist()
        assert dates == sorted(dates)

    @patch("data_service.st")
    def test_24_months_economy_column(self, mock_st, mock_gc_24):
        df, _ = load_monthly_financial_summary.__wrapped__(mock_gc_24, FAKE_URL)
        for _, row in df.iterrows():
            assert row["Economia"] == pytest.approx(
                row["Total de Receita"] - row["Total de Gastos"]
            )

    @patch("data_service.st")
    def test_24_months_savings_rate(self, mock_st, mock_gc_24):
        df, _ = load_monthly_financial_summary.__wrapped__(mock_gc_24, FAKE_URL)
        for _, row in df.iterrows():
            if row["Total de Receita"] != 0:
                expected = (row["Economia"] / row["Total de Receita"]) * 100
                assert row["Taxa de Economia (%)"] == pytest.approx(expected)

    @patch("data_service.st")
    def test_december_2024_negative(self, mock_st, mock_gc_24):
        """Dec 2024 has expenses > income in our fixture."""
        df, _ = load_monthly_financial_summary.__wrapped__(mock_gc_24, FAKE_URL)
        dec = df[df["Mês"] == "Dezembro 2024"].iloc[0]
        assert dec["Economia"] < 0

    @patch("data_service.st")
    def test_december_2025_zero_savings(self, mock_st, mock_gc_24):
        """Dec 2025 has expenses == income (zero savings)."""
        df, _ = load_monthly_financial_summary.__wrapped__(mock_gc_24, FAKE_URL)
        dec = df[df["Mês"] == "Dezembro 2025"].iloc[0]
        assert dec["Economia"] == 0.0
        assert dec["Taxa de Economia (%)"] == 0.0
