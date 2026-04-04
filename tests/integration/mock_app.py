"""Test entrypoint that patches external services with mock data,
then runs the real dashboard.py code via exec().

Started via AppTest.from_file("tests/integration/mock_app.py") in integration tests.
Produces a fully functional Streamlit app with deterministic 24-month
data and no dependency on Google Sheets or real credentials.
"""

import sys
import os
import pathlib
from unittest.mock import MagicMock

import pandas as pd

# Ensure project root is on the path
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from helpers import parse_brl_value, parse_sheet_name_to_date

# ---------------------------------------------------------------------------
# 24-month mock dataset (Jan 2024 → Dec 2025)
# ---------------------------------------------------------------------------

MONTHLY_DATA = [
    ("Janeiro 2024",   "R$ 3.500,00", "R$ 8.000,00"),
    ("Fevereiro 2024", "R$ 4.200,50", "R$ 8.500,00"),
    ("Março 2024",     "R$ 3.000,00", "R$ 9.000,00"),
    ("Abril 2024",     "R$ 5.800,00", "R$ 8.200,00"),
    ("Maio 2024",      "R$ 3.100,00", "R$ 8.700,00"),
    ("Junho 2024",     "R$ 6.500,00", "R$ 8.000,00"),
    ("Julho 2024",     "R$ 3.800,00", "R$ 8.300,00"),
    ("Agosto 2024",    "R$ 4.000,00", "R$ 9.500,00"),
    ("Setembro 2024",  "R$ 3.200,00", "R$ 8.100,00"),
    ("Outubro 2024",   "R$ 7.500,00", "R$ 8.000,00"),
    ("Novembro 2024",  "R$ 4.500,00", "R$ 10.000,00"),
    ("Dezembro 2024",  "R$ 9.000,00", "R$ 8.500,00"),   # negative savings
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
    ("Dezembro 2025",  "R$ 8.000,00", "R$ 8.000,00"),   # zero savings
]


def _build_mock_df():
    rows = []
    for name, exp_raw, inc_raw in MONTHLY_DATA:
        exp = parse_brl_value(exp_raw)
        inc = parse_brl_value(inc_raw)
        rows.append({
            "Mês": name,
            "Total de Gastos": exp,
            "Total de Receita": inc,
            "Data do Mês": pd.Timestamp(parse_sheet_name_to_date(name)),
            "Economia": inc - exp,
            "Taxa de Economia (%)": ((inc - exp) / inc * 100) if inc else 0,
        })
    return pd.DataFrame(rows)


MOCK_DF = _build_mock_df()

# ---------------------------------------------------------------------------
# Patch external services BEFORE running dashboard code
# ---------------------------------------------------------------------------

import data_service
import streamlit_service

# Replace Google Sheets functions with mocks
data_service.authenticate_gspread = MagicMock(return_value=MagicMock())
data_service.load_monthly_financial_summary = lambda _gc, _url: (MOCK_DF.copy(), [])


# Replace StreamlitCloudService with mock that returns test credentials
# bcrypt hash of "testpass123":
_TEST_CONFIG = {
    "credentials": {
        "usernames": {
            "testuser": {
                "name": "Test User",
                "password": "$2b$12$LZkVYiGGHYsLQHLJSqWZ5.6G.TEBasu0SS6GFkqPAxVE3dlq.3pPy",
            }
        }
    },
    "cookie": {
        "name": "e2e_test_cookie",
        "key": "e2e_test_secret_key_abc123",
        "expiry_days": 1,
    },
}

_OrigService = streamlit_service.StreamlitCloudService


class _MockService(_OrigService):
    def get_user_credentials(self):
        return _TEST_CONFIG

    def get_google_sheets_credentials(self):
        return {"type": "service_account", "project_id": "mock"}

    def get_sheet_url(self):
        return "https://docs.google.com/spreadsheets/d/mock/edit"

    def validate_secrets(self):
        return None


streamlit_service.StreamlitCloudService = _MockService

# ---------------------------------------------------------------------------
# Execute the real dashboard.py code in this context
# ---------------------------------------------------------------------------

_dashboard_path = PROJECT_ROOT / "dashboard.py"
exec(compile(_dashboard_path.read_text(encoding="utf-8"), str(_dashboard_path), "exec"))
