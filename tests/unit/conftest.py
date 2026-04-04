"""Shared fixtures for all test modules."""

from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest

from constants import MONTH_NAMES_PT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_worksheet(title):
    ws = MagicMock()
    ws.title = title
    return ws


def make_batch_response(pairs):
    """Build a fake values_batch_get response.

    pairs: list of (expenses_raw, income_raw) per sheet.
    Each raw value is a string like 'R$ 1.234,56' or None.
    """
    value_ranges = []
    for expenses_raw, income_raw in pairs:
        value_ranges.append(
            {"values": [[expenses_raw]]} if expenses_raw is not None else {}
        )
        value_ranges.append(
            {"values": [[income_raw]]} if income_raw is not None else {}
        )
    return {"valueRanges": value_ranges}


# ---------------------------------------------------------------------------
# 24-month dataset (Jan 2024 → Dec 2025) with realistic variation
# ---------------------------------------------------------------------------

MONTHLY_DATA_24 = [
    # (month_name, expenses_raw,   income_raw)
    ("Janeiro 2024",   "R$ 3.500,00", "R$ 8.000,00"),
    ("Fevereiro 2024", "R$ 4.200,50", "R$ 8.500,00"),
    ("Março 2024",     "R$ 3.000,00", "R$ 9.000,00"),
    ("Abril 2024",     "R$ 5.800,00", "R$ 8.200,00"),
    ("Maio 2024",      "R$ 3.100,00", "R$ 8.700,00"),
    ("Junho 2024",     "R$ 6.500,00", "R$ 8.000,00"),
    ("Julho 2024",     "R$ 3.800,00", "R$ 8.300,00"),
    ("Agosto 2024",    "R$ 4.000,00", "R$ 9.500,00"),
    ("Setembro 2024",  "R$ 3.200,00", "R$ 8.100,00"),
    ("Outubro 2024",   "R$ 7.500,00", "R$ 8.000,00"),  # near-breakeven
    ("Novembro 2024",  "R$ 4.500,00", "R$ 10.000,00"),
    ("Dezembro 2024",  "R$ 9.000,00", "R$ 8.500,00"),  # negative savings
    ("Janeiro 2025",   "R$ 3.600,00", "R$ 8.800,00"),
    ("Fevereiro 2025", "R$ 4.100,00", "R$ 8.400,00"),
    ("Março 2025",     "R$ 3.300,00", "R$ 9.200,00"),
    ("Abril 2025",     "R$ 5.000,00", "R$ 8.600,00"),
    ("Maio 2025",      "R$ 3.700,00", "R$ 8.900,00"),
    ("Junho 2025",     "R$ 4.800,00", "R$ 8.100,00"),
    ("Julho 2025",     "R$ 3.400,00", "R$ 8.500,00"),
    ("Agosto 2025",    "R$ 4.200,00", "R$ 9.300,00"),
    ("Setembro 2025",  "R$ 3.900,00", "R$ 8.200,00"),
    ("Outubro 2025",   "R$ 5.500,00", "R$ 8.000,00"),
    ("Novembro 2025",  "R$ 4.300,00", "R$ 10.500,00"),
    ("Dezembro 2025",  "R$ 8.000,00", "R$ 8.000,00"),  # zero savings
]

WORKSHEETS_24 = [_make_worksheet(name) for name, _, _ in MONTHLY_DATA_24]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_gc_24():
    """Mock gspread client wired to 24 months of data."""
    gc = MagicMock()
    spreadsheet = MagicMock()
    spreadsheet.worksheets.return_value = list(WORKSHEETS_24)
    spreadsheet.values_batch_get.return_value = make_batch_response(
        [(exp, inc) for _, exp, inc in MONTHLY_DATA_24]
    )
    gc.open_by_url.return_value = spreadsheet
    return gc


@pytest.fixture()
def mock_gc_3():
    """Mock gspread client wired to 3 months of data (quick tests)."""
    gc = MagicMock()
    spreadsheet = MagicMock()
    worksheets = [_make_worksheet(n) for n, _, _ in MONTHLY_DATA_24[:3]]
    spreadsheet.worksheets.return_value = worksheets
    spreadsheet.values_batch_get.return_value = make_batch_response(
        [(exp, inc) for _, exp, inc in MONTHLY_DATA_24[:3]]
    )
    gc.open_by_url.return_value = spreadsheet
    return gc


@pytest.fixture()
def mock_gc_with_invalid_tabs():
    """Mock with valid + non-month tabs mixed."""
    gc = MagicMock()
    spreadsheet = MagicMock()
    worksheets = [
        _make_worksheet("Janeiro 2024"),
        _make_worksheet("Resumo"),           # ignored
        _make_worksheet("Fevereiro 2024"),
        _make_worksheet("Dashboard"),        # ignored
        _make_worksheet("Config"),           # ignored
    ]
    spreadsheet.worksheets.return_value = worksheets
    spreadsheet.values_batch_get.return_value = make_batch_response([
        ("R$ 3.500,00", "R$ 8.000,00"),
        ("R$ 4.200,50", "R$ 8.500,00"),
    ])
    gc.open_by_url.return_value = spreadsheet
    return gc


@pytest.fixture()
def mock_gc_only_invalid_tabs():
    """Mock where all tabs are non-month (no valid data)."""
    gc = MagicMock()
    spreadsheet = MagicMock()
    spreadsheet.worksheets.return_value = [
        _make_worksheet("Resumo"),
        _make_worksheet("Dashboard"),
    ]
    gc.open_by_url.return_value = spreadsheet
    return gc


@pytest.fixture()
def mock_gc_open_error():
    """Mock where open_by_url raises (bad URL or permission)."""
    gc = MagicMock()
    gc.open_by_url.side_effect = Exception("Permission denied")
    return gc


@pytest.fixture()
def mock_gc_batch_error():
    """Mock where values_batch_get raises (API error)."""
    gc = MagicMock()
    spreadsheet = MagicMock()
    spreadsheet.worksheets.return_value = [_make_worksheet("Janeiro 2024")]
    spreadsheet.values_batch_get.side_effect = Exception("API quota exceeded")
    gc.open_by_url.return_value = spreadsheet
    return gc


@pytest.fixture()
def mock_gc_empty_cells():
    """Mock where expense/income cells are empty."""
    gc = MagicMock()
    spreadsheet = MagicMock()
    spreadsheet.worksheets.return_value = [
        _make_worksheet("Janeiro 2024"),
        _make_worksheet("Fevereiro 2024"),
    ]
    spreadsheet.values_batch_get.return_value = make_batch_response([
        (None, None),           # both empty
        ("R$ 3.000,00", None),  # income empty
    ])
    gc.open_by_url.return_value = spreadsheet
    return gc


@pytest.fixture()
def mock_gc_invalid_values():
    """Mock where cells contain non-parseable strings."""
    gc = MagicMock()
    spreadsheet = MagicMock()
    spreadsheet.worksheets.return_value = [
        _make_worksheet("Janeiro 2024"),
        _make_worksheet("Fevereiro 2024"),
    ]
    spreadsheet.values_batch_get.return_value = make_batch_response([
        ("abc", "R$ 8.000,00"),         # invalid expense
        ("R$ 3.000,00", "not_a_number"), # invalid income
    ])
    gc.open_by_url.return_value = spreadsheet
    return gc


@pytest.fixture()
def mock_gc_zero_income():
    """Mock where income is zero (division-by-zero edge case)."""
    gc = MagicMock()
    spreadsheet = MagicMock()
    spreadsheet.worksheets.return_value = [
        _make_worksheet("Janeiro 2024"),
        _make_worksheet("Fevereiro 2024"),
    ]
    spreadsheet.values_batch_get.return_value = make_batch_response([
        ("R$ 3.000,00", "0"),           # zero income
        ("R$ 4.000,00", "R$ 8.000,00"), # normal
    ])
    gc.open_by_url.return_value = spreadsheet
    return gc


@pytest.fixture()
def mock_gc_single_month():
    """Mock with exactly one month of data."""
    gc = MagicMock()
    spreadsheet = MagicMock()
    spreadsheet.worksheets.return_value = [_make_worksheet("Março 2025")]
    spreadsheet.values_batch_get.return_value = make_batch_response([
        ("R$ 5.000,00", "R$ 10.000,00"),
    ])
    gc.open_by_url.return_value = spreadsheet
    return gc


@pytest.fixture()
def mock_gc_negative_savings():
    """Mock where expenses exceed income in all months."""
    gc = MagicMock()
    spreadsheet = MagicMock()
    spreadsheet.worksheets.return_value = [
        _make_worksheet("Janeiro 2024"),
        _make_worksheet("Fevereiro 2024"),
    ]
    spreadsheet.values_batch_get.return_value = make_batch_response([
        ("R$ 10.000,00", "R$ 5.000,00"),
        ("R$ 12.000,00", "R$ 6.000,00"),
    ])
    gc.open_by_url.return_value = spreadsheet
    return gc


@pytest.fixture()
def valid_config():
    """Minimal valid user config dict."""
    return {
        "credentials": {
            "usernames": {
                "testuser": {
                    "name": "Test User",
                    "password": "$2b$12$fakehashvalue",
                }
            }
        },
        "cookie": {
            "name": "test_cookie",
            "key": "random_key",
            "expiry_days": 30,
        },
    }
