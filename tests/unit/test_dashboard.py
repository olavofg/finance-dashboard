"""Tests for dashboard validation logic and computed metrics.

_validate_config is tested via direct import from the helpers-like function.
Since dashboard.py executes Streamlit on import, we copy the function here.
Metric/delta/highlight computations are tested against the same DataFrame
logic used in dashboard.py but without importing the module.
"""

import copy
from datetime import date, datetime
from unittest.mock import patch

import pandas as pd
import pytest

from constants import PERIOD_PRESETS


def _validate_config(config):
    """Copy of dashboard._validate_config for testability."""
    if not config:
        return "Configurações de usuário não encontradas. Verifique os secrets ou arquivos de configuração."

    required_keys = ['credentials', 'cookie']
    missing_keys = [k for k in required_keys if k not in config]
    if missing_keys:
        return f"config.yaml incompleto — chaves obrigatórias ausentes: {', '.join(missing_keys)}"

    if not config.get('cookie'):
        return "config.yaml incompleto — seção 'cookie' está vazia ou ausente."

    cookie_keys = ['name', 'key', 'expiry_days']
    missing_cookie = [k for k in cookie_keys if k not in config['cookie']]
    if missing_cookie:
        return f"config.yaml incompleto — campos ausentes em 'cookie': {', '.join(missing_cookie)}"

    usernames = config.get('credentials', {}).get('usernames', {})
    if not usernames:
        return "Nenhum usuário configurado em 'credentials.usernames'. Adicione pelo menos um usuário com senha."

    for uname, udata in usernames.items():
        if not udata.get('password'):
            return f"Usuário '{uname}' não possui senha configurada. Gere um hash bcrypt e adicione ao config."

    return None


# ---------------------------------------------------------------------------
# _validate_config — every error branch
# ---------------------------------------------------------------------------

class TestValidateConfig:
    def test_valid_config(self, valid_config):
        assert _validate_config(valid_config) is None

    def test_none(self):
        result = _validate_config(None)
        assert result is not None
        assert "não encontradas" in result

    def test_empty_dict(self):
        result = _validate_config({})
        assert "não encontradas" in result

    def test_missing_credentials(self, valid_config):
        del valid_config["credentials"]
        result = _validate_config(valid_config)
        assert "credentials" in result

    def test_missing_cookie(self, valid_config):
        del valid_config["cookie"]
        result = _validate_config(valid_config)
        assert "cookie" in result

    def test_missing_both_keys(self):
        result = _validate_config({"other": "stuff"})
        assert "credentials" in result and "cookie" in result

    def test_empty_cookie(self, valid_config):
        valid_config["cookie"] = {}
        result = _validate_config(valid_config)
        assert "cookie" in result.lower()

    def test_cookie_none(self, valid_config):
        valid_config["cookie"] = None
        result = _validate_config(valid_config)
        assert "cookie" in result.lower()

    def test_missing_cookie_name(self, valid_config):
        del valid_config["cookie"]["name"]
        result = _validate_config(valid_config)
        assert "name" in result

    def test_missing_cookie_key(self, valid_config):
        del valid_config["cookie"]["key"]
        result = _validate_config(valid_config)
        assert "key" in result

    def test_missing_cookie_expiry(self, valid_config):
        del valid_config["cookie"]["expiry_days"]
        result = _validate_config(valid_config)
        assert "expiry_days" in result

    def test_missing_all_cookie_fields(self, valid_config):
        valid_config["cookie"] = {"extra": "field"}
        result = _validate_config(valid_config)
        assert "name" in result

    def test_empty_usernames(self, valid_config):
        valid_config["credentials"]["usernames"] = {}
        result = _validate_config(valid_config)
        assert "Nenhum usuário" in result

    def test_no_usernames_key(self, valid_config):
        valid_config["credentials"] = {}
        result = _validate_config(valid_config)
        assert "Nenhum usuário" in result

    def test_user_without_password(self, valid_config):
        valid_config["credentials"]["usernames"]["testuser"]["password"] = ""
        result = _validate_config(valid_config)
        assert "testuser" in result
        assert "senha" in result.lower()

    def test_user_password_none(self, valid_config):
        valid_config["credentials"]["usernames"]["testuser"]["password"] = None
        result = _validate_config(valid_config)
        assert "testuser" in result

    def test_multiple_users_one_without_password(self, valid_config):
        valid_config["credentials"]["usernames"]["user2"] = {
            "name": "User 2",
            "password": "",
        }
        result = _validate_config(valid_config)
        assert "user2" in result

    def test_multiple_valid_users(self, valid_config):
        valid_config["credentials"]["usernames"]["user2"] = {
            "name": "User 2",
            "password": "$2b$12$anotherhash",
        }
        assert _validate_config(valid_config) is None


# ---------------------------------------------------------------------------
# PERIOD_PRESETS structure
# ---------------------------------------------------------------------------

class TestPeriodPresets:
    def test_has_all_expected_keys(self):
        expected = {"Tudo", "Últimos 12", "Últimos 6", "Ano atual"}
        assert set(PERIOD_PRESETS.keys()) == expected

    def test_tudo_is_none(self):
        assert PERIOD_PRESETS["Tudo"] is None

    def test_ano_atual_is_none(self):
        assert PERIOD_PRESETS["Ano atual"] is None

    def test_numeric_presets(self):
        assert PERIOD_PRESETS["Últimos 12"] == 12
        assert PERIOD_PRESETS["Últimos 6"] == 6


# ---------------------------------------------------------------------------
# Metric computation logic (extracted from dashboard flow)
# ---------------------------------------------------------------------------

def _build_test_df(n_months=24):
    """Build a DataFrame mimicking load_monthly_financial_summary output."""
    from tests.unit.conftest import MONTHLY_DATA_24
    from helpers import parse_brl_value, parse_sheet_name_to_date

    rows = []
    for name, exp_raw, inc_raw in MONTHLY_DATA_24[:n_months]:
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


class TestKpiMetrics:
    def test_total_income(self):
        df = _build_test_df()
        total = df["Total de Receita"].sum()
        assert total > 0

    def test_total_expenses(self):
        df = _build_test_df()
        total = df["Total de Gastos"].sum()
        assert total > 0

    def test_net_savings_equals_income_minus_expenses(self):
        df = _build_test_df()
        assert df["Economia"].sum() == pytest.approx(
            df["Total de Receita"].sum() - df["Total de Gastos"].sum()
        )

    def test_avg_expenses(self):
        df = _build_test_df()
        assert df["Total de Gastos"].mean() == pytest.approx(
            df["Total de Gastos"].sum() / len(df)
        )

    def test_median_expenses(self):
        df = _build_test_df()
        median = df["Total de Gastos"].median()
        # median should be between min and max
        assert df["Total de Gastos"].min() <= median <= df["Total de Gastos"].max()

    def test_annual_projection(self):
        df = _build_test_df()
        projection = df["Economia"].mean() * 12
        assert projection > 0  # overall our fixture is net positive

    def test_avg_savings_rate(self):
        df = _build_test_df()
        rate = df["Taxa de Economia (%)"].mean()
        assert -100 < rate < 100


class TestDeltaComputation:
    """Test the delta % comparison logic: filtered avg vs baseline avg."""

    def _compute_deltas(self, df_full, df_filtered, current_month_start):
        df_baseline = df_full[df_full["Data do Mês"] < pd.Timestamp(current_month_start)]
        if len(df_baseline) > len(df_filtered):
            avg_all = df_baseline["Total de Receita"].mean()
            avg_filt = df_filtered["Total de Receita"].mean()
            return ((avg_filt - avg_all) / avg_all * 100) if avg_all else None
        return None

    def test_full_range_returns_none(self):
        df = _build_test_df()
        current = date(2026, 4, 1)  # future — all data is baseline
        delta = self._compute_deltas(df, df, current)
        assert delta is None

    def test_partial_range_returns_value(self):
        df = _build_test_df()
        current = date(2026, 4, 1)
        df_filtered = df[df["Data do Mês"] >= "2025-01-01"]
        delta = self._compute_deltas(df, df_filtered, current)
        assert delta is not None
        assert isinstance(delta, float)

    def test_single_month_filter(self):
        df = _build_test_df()
        current = date(2026, 4, 1)
        df_filtered = df[df["Mês"] == "Novembro 2024"]
        delta = self._compute_deltas(df, df_filtered, current)
        assert delta is not None


class TestHighlights:
    """Test that idxmax/idxmin pick correct months from 24-month fixture."""

    def test_highest_expense(self):
        df = _build_test_df()
        row = df.loc[df["Total de Gastos"].idxmax()]
        assert row["Total de Gastos"] == df["Total de Gastos"].max()

    def test_lowest_expense(self):
        df = _build_test_df()
        row = df.loc[df["Total de Gastos"].idxmin()]
        assert row["Total de Gastos"] == df["Total de Gastos"].min()

    def test_highest_income(self):
        df = _build_test_df()
        row = df.loc[df["Total de Receita"].idxmax()]
        # Our fixture: Nov 2025 has R$ 10.500,00
        assert row["Total de Receita"] == 10500.0

    def test_lowest_income(self):
        df = _build_test_df()
        row = df.loc[df["Total de Receita"].idxmin()]
        # Multiple months at R$ 8.000,00 — just verify it's the min
        assert row["Total de Receita"] == 8000.0

    def test_highest_savings(self):
        df = _build_test_df()
        row = df.loc[df["Economia"].idxmax()]
        assert row["Economia"] == df["Economia"].max()

    def test_lowest_savings(self):
        df = _build_test_df()
        row = df.loc[df["Economia"].idxmin()]
        assert row["Economia"] == df["Economia"].min()

    def test_negative_savings_exists(self):
        df = _build_test_df()
        # Dec 2024: expenses R$ 9.000 > income R$ 8.500
        dec = df[df["Mês"] == "Dezembro 2024"].iloc[0]
        assert dec["Economia"] < 0

    def test_zero_savings_exists(self):
        df = _build_test_df()
        # Dec 2025: expenses == income
        dec = df[df["Mês"] == "Dezembro 2025"].iloc[0]
        assert dec["Economia"] == 0.0


class TestCompositionChart:
    """Test the composition % calculation (division-by-zero guard)."""

    def test_normal_composition(self):
        df = _build_test_df(3)
        total = df["Total de Gastos"] + df["Economia"]
        gastos_pct = df["Total de Gastos"].div(total).fillna(0) * 100
        eco_pct = df["Economia"].div(total).fillna(0) * 100
        for g, e in zip(gastos_pct, eco_pct):
            assert g + e == pytest.approx(100.0)

    def test_zero_total_no_crash(self):
        """If gastos + economia = 0, fillna(0) prevents NaN."""
        df = pd.DataFrame([{
            "Mês": "Test",
            "Total de Gastos": 0.0,
            "Economia": 0.0,
        }])
        total = df["Total de Gastos"] + df["Economia"]
        gastos_pct = df["Total de Gastos"].div(total).fillna(0) * 100
        eco_pct = df["Economia"].div(total).fillna(0) * 100
        assert gastos_pct.iloc[0] == 0.0
        assert eco_pct.iloc[0] == 0.0

    def test_negative_savings_composition(self):
        """When savings is negative, gastos% > 100 and economia% < 0."""
        df = pd.DataFrame([{
            "Mês": "Test",
            "Total de Gastos": 10000.0,
            "Economia": -2000.0,
        }])
        total = df["Total de Gastos"] + df["Economia"]
        gastos_pct = df["Total de Gastos"].div(total).fillna(0) * 100
        assert gastos_pct.iloc[0] > 100


class TestDateFilter:
    """Test the date filtering logic extracted from the dashboard flow."""

    def test_full_range(self):
        df = _build_test_df()
        start = df["Data do Mês"].min()
        end = df["Data do Mês"].max()
        filtered = df[(df["Data do Mês"] >= start) & (df["Data do Mês"] <= end)]
        assert len(filtered) == 24

    def test_single_month(self):
        df = _build_test_df()
        target = pd.Timestamp("2024-06-01")
        end = target.replace(day=30)
        filtered = df[(df["Data do Mês"] >= target) & (df["Data do Mês"] <= end)]
        assert len(filtered) == 1

    def test_last_6_months(self):
        df = _build_test_df()
        cutoff = pd.Timestamp("2025-07-01")
        filtered = df[df["Data do Mês"] >= cutoff]
        assert len(filtered) == 6  # Jul-Dec 2025

    def test_last_12_months(self):
        df = _build_test_df()
        cutoff = pd.Timestamp("2025-01-01")
        filtered = df[df["Data do Mês"] >= cutoff]
        assert len(filtered) == 12  # Jan-Dec 2025

    def test_year_2024(self):
        df = _build_test_df()
        year_start = pd.Timestamp("2024-01-01")
        year_end = pd.Timestamp("2024-12-31")
        filtered = df[(df["Data do Mês"] >= year_start) & (df["Data do Mês"] <= year_end)]
        assert len(filtered) == 12

    def test_empty_filter(self):
        df = _build_test_df()
        filtered = df[df["Data do Mês"] >= "2030-01-01"]
        assert filtered.empty

    def test_start_after_end_produces_empty(self):
        df = _build_test_df()
        start = pd.Timestamp("2025-06-01")
        end = pd.Timestamp("2024-01-31")
        filtered = df[(df["Data do Mês"] >= start) & (df["Data do Mês"] <= end)]
        assert filtered.empty


class TestCumulativeSavings:
    """Test the cumulative savings (Economia Acumulada) chart data."""

    def test_cumsum_monotonic_when_all_positive(self):
        df = _build_test_df(3)
        cumsum = df["Economia"].cumsum()
        # All 3 months have positive savings
        assert (cumsum.diff().dropna() > 0).all()

    def test_cumsum_decreases_on_negative(self):
        df = _build_test_df()
        cumsum = df["Economia"].cumsum()
        # Dec 2024 is negative — cumsum should decrease
        dec_idx = df[df["Mês"] == "Dezembro 2024"].index[0]
        if dec_idx > 0:
            assert cumsum.iloc[dec_idx] < cumsum.iloc[dec_idx - 1]

    def test_cumsum_flat_on_zero(self):
        df = _build_test_df()
        cumsum = df["Economia"].cumsum()
        dec_idx = df[df["Mês"] == "Dezembro 2025"].index[0]
        if dec_idx > 0:
            # Dec 2025 has 0 savings, cumsum unchanged
            assert cumsum.iloc[dec_idx] == cumsum.iloc[dec_idx - 1]
