"""Integration tests — runs the REAL dashboard app with mock data via AppTest.

These tests verify the full Streamlit rendering pipeline:
login flow, KPI metrics, highlights, charts, filters, and summary table.
"""

import pytest
from streamlit.testing.v1 import AppTest


MOCK_APP_PATH = "tests/integration/mock_app.py"


# ---------------------------------------------------------------------------
# Authentication flow
# ---------------------------------------------------------------------------

class TestLoginFlow:
    def test_unauthenticated_shows_login_form(self, app_unauthenticated):
        at = app_unauthenticated
        # Login form should render — look for text inputs (username + password)
        assert len(at.text_input) >= 1
        # Dashboard content should NOT be visible (st.stop() after login)
        assert len(at.metric) == 0

    def test_wrong_password_shows_error(self):
        at = AppTest.from_file(MOCK_APP_PATH, default_timeout=30)
        at.run()
        # Fill in credentials — wrong password
        for ti in at.text_input:
            if "usu" in ti.label.lower():
                ti.set_value("testuser")
            elif "senha" in ti.label.lower():
                ti.set_value("wrongpassword")
        # Click login button
        for btn in at.button:
            if "entrar" in btn.label.lower():
                btn.click()
        at.run()
        # Should show error
        errors = [e.value for e in at.error]
        assert any("incorretos" in e.lower() for e in errors)

    def test_authenticated_shows_dashboard(self, app_authenticated):
        at = app_authenticated
        assert not at.exception
        # Should see welcome message and metrics
        assert len(at.metric) > 0


# ---------------------------------------------------------------------------
# Page structure
# ---------------------------------------------------------------------------

class TestPageStructure:
    def test_title_rendered(self, app_authenticated):
        at = app_authenticated
        markdowns = [m.value for m in at.markdown]
        assert any("Dashboard Financeiro" in m for m in markdowns)

    def test_welcome_message(self, app_authenticated):
        at = app_authenticated
        markdowns = [m.value for m in at.markdown]
        assert any("Test User" in m for m in markdowns)

    def test_subheaders_present(self, app_authenticated):
        at = app_authenticated
        subheaders = [s.value for s in at.subheader]
        labels = " ".join(subheaders)
        assert "Métricas" in labels
        assert "Destaques" in labels
        assert "Gráficos" in labels
        assert "Tabela" in labels

    def test_no_errors_on_load(self, app_authenticated):
        at = app_authenticated
        assert not at.exception
        errors = [e.value for e in at.error]
        assert len(errors) == 0

    def test_no_warnings_with_valid_data(self, app_authenticated):
        at = app_authenticated
        warnings = [w.value for w in at.warning]
        assert len(warnings) == 0

    def test_caption_footer(self, app_authenticated):
        at = app_authenticated
        captions = [c.value for c in at.caption]
        assert any("Dashboard Financeiro" in c for c in captions)


# ---------------------------------------------------------------------------
# KPI Metrics (8 total: 4 primary + 4 complementary)
# ---------------------------------------------------------------------------

class TestKpiMetrics:
    def test_eight_metrics_rendered(self, app_authenticated):
        at = app_authenticated
        # 8 KPIs + 1 "Média de Economia" above table + 6 highlights = 15 total
        # But let's just check we have at least 8
        assert len(at.metric) >= 8

    def test_total_receita_metric(self, app_authenticated):
        at = app_authenticated
        labels = [m.label for m in at.metric]
        assert any("Total de Receita" in l for l in labels)

    def test_total_gastos_metric(self, app_authenticated):
        at = app_authenticated
        labels = [m.label for m in at.metric]
        assert any("Total de Gastos" in l for l in labels)

    def test_economia_liquida_metric(self, app_authenticated):
        at = app_authenticated
        labels = [m.label for m in at.metric]
        assert any("Economia" in l for l in labels)

    def test_media_gastos_metric(self, app_authenticated):
        at = app_authenticated
        labels = [m.label for m in at.metric]
        assert any("Média de Gastos" in l for l in labels)

    def test_mediana_gastos_metric(self, app_authenticated):
        at = app_authenticated
        labels = [m.label for m in at.metric]
        assert any("Mediana" in l for l in labels)

    def test_projecao_anual_metric(self, app_authenticated):
        at = app_authenticated
        labels = [m.label for m in at.metric]
        assert any("Projeção" in l for l in labels)

    def test_metric_values_are_currency(self, app_authenticated):
        at = app_authenticated
        # All primary metrics should contain "R$"
        primary_metrics = at.metric[:4]
        for m in primary_metrics:
            assert "R$" in m.value, f"Metric '{m.label}' missing R$: {m.value}"

    def test_metric_values_are_nonzero(self, app_authenticated):
        at = app_authenticated
        # With 24 months of data, primary totals should not be "R$ 0,00"
        for m in at.metric[:4]:
            assert m.value != "R$ 0,00", f"Metric '{m.label}' is zero"


# ---------------------------------------------------------------------------
# Highlights (Destaques Mensais)
# ---------------------------------------------------------------------------

class TestHighlights:
    def _highlight_labels(self, at):
        return [m.label for m in at.metric if "Maior" in m.label or "Menor" in m.label]

    def test_six_highlight_metrics(self, app_authenticated):
        labels = self._highlight_labels(app_authenticated)
        assert len(labels) == 6

    def test_maior_receita(self, app_authenticated):
        labels = self._highlight_labels(app_authenticated)
        assert any("Maior Receita" in l for l in labels)

    def test_menor_receita(self, app_authenticated):
        labels = self._highlight_labels(app_authenticated)
        assert any("Menor Receita" in l for l in labels)

    def test_maior_gasto(self, app_authenticated):
        labels = self._highlight_labels(app_authenticated)
        assert any("Maior Gasto" in l for l in labels)

    def test_menor_gasto(self, app_authenticated):
        labels = self._highlight_labels(app_authenticated)
        assert any("Menor Gasto" in l for l in labels)

    def test_maior_economia(self, app_authenticated):
        labels = self._highlight_labels(app_authenticated)
        assert any("Maior Economia" in l for l in labels)

    def test_menor_economia(self, app_authenticated):
        labels = self._highlight_labels(app_authenticated)
        assert any("Menor Economia" in l for l in labels)

    def test_highlight_values_are_currency(self, app_authenticated):
        at = app_authenticated
        highlights = [m for m in at.metric if "Maior" in m.label or "Menor" in m.label]
        for h in highlights:
            assert "R$" in h.value, f"Highlight '{h.label}' missing R$"

    def test_economia_highlights_have_delta(self, app_authenticated):
        at = app_authenticated
        eco = [m for m in at.metric if "Economia" in m.label and ("Maior" in m.label or "Menor" in m.label)]
        for m in eco:
            assert m.delta is not None
            assert "da receita" in m.delta


# ---------------------------------------------------------------------------
# Charts (5 tabs)
# ---------------------------------------------------------------------------

class TestCharts:
    def test_tabs_rendered(self, app_authenticated):
        at = app_authenticated
        assert len(at.tabs) > 0

    def test_no_crash_on_chart_render(self, app_authenticated):
        """The app should render all chart tabs without exceptions."""
        at = app_authenticated
        assert not at.exception


# ---------------------------------------------------------------------------
# Summary Table
# ---------------------------------------------------------------------------

class TestSummaryTable:
    def test_dataframe_rendered(self, app_authenticated):
        at = app_authenticated
        assert len(at.dataframe) >= 1

    def test_media_economia_above_table(self, app_authenticated):
        at = app_authenticated
        labels = [m.label for m in at.metric]
        assert any("Média de Economia" in l for l in labels)


# ---------------------------------------------------------------------------
# Period filter interaction
# ---------------------------------------------------------------------------

class TestPeriodFilter:
    def _run_with_filter(self, start_idx, end_idx):
        """Run app with specific start/end selectbox indices."""
        at = AppTest.from_file(MOCK_APP_PATH, default_timeout=30)
        at.session_state["authentication_status"] = True
        at.session_state["name"] = "Test User"
        at.session_state["username"] = "testuser"
        at.run()

        if len(at.selectbox) >= 2:
            options_start = at.selectbox[0].options
            options_end = at.selectbox[1].options

            at.selectbox[0].set_value(options_start[start_idx])
            at.selectbox[1].set_value(options_end[end_idx])
            at.run()

        return at

    def test_default_filter_shows_all(self, app_authenticated):
        at = app_authenticated
        # Default is "Tudo" — all 24 months
        assert len(at.metric) >= 8

    def test_filter_single_month(self):
        """Select Jan 2024 as both start and end."""
        at = self._run_with_filter(0, 0)
        assert not at.exception
        assert len(at.metric) >= 8

    def test_filter_last_month(self):
        """Select only the last month (Dec 2025)."""
        at = self._run_with_filter(23, 23)
        assert not at.exception
        assert len(at.metric) >= 8

    def test_filter_first_half_2024(self):
        """Jan 2024 → Jun 2024."""
        at = self._run_with_filter(0, 5)
        assert not at.exception
        assert len(at.metric) >= 8

    def test_filter_year_2025(self):
        """Jan 2025 → Dec 2025 (indices 12-23)."""
        at = self._run_with_filter(12, 23)
        assert not at.exception
        assert len(at.metric) >= 8

    def test_selectboxes_have_24_options(self, app_authenticated):
        at = app_authenticated
        if len(at.selectbox) >= 2:
            assert len(at.selectbox[0].options) == 24
            assert len(at.selectbox[1].options) == 24

    def test_selectbox_first_is_janeiro_2024(self, app_authenticated):
        at = app_authenticated
        if len(at.selectbox) >= 1:
            assert at.selectbox[0].options[0] == "Janeiro 2024"

    def test_selectbox_last_is_dezembro_2025(self, app_authenticated):
        at = app_authenticated
        if len(at.selectbox) >= 2:
            assert at.selectbox[1].options[-1] == "Dezembro 2025"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_december_2024_negative_savings_in_data(self, app_authenticated):
        """App should handle months with negative savings without crashing."""
        at = app_authenticated
        assert not at.exception

    def test_december_2025_zero_savings_in_data(self, app_authenticated):
        """App should handle months with zero savings without crashing."""
        at = app_authenticated
        assert not at.exception

    def test_multiple_reruns_stable(self):
        """Running the app twice should produce same results."""
        at = AppTest.from_file(MOCK_APP_PATH, default_timeout=30)
        at.session_state["authentication_status"] = True
        at.session_state["name"] = "Test User"
        at.session_state["username"] = "testuser"
        at.run()
        metrics_1 = [(m.label, m.value) for m in at.metric]
        at.run()
        metrics_2 = [(m.label, m.value) for m in at.metric]
        assert metrics_1 == metrics_2
