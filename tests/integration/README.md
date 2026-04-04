# Integration Tests

**42 scenarios** that run the **real** dashboard with mock data using Streamlit's `AppTest` framework.

> The app is loaded in-memory via `mock_app.py`, which injects mocks into `data_service` and `streamlit_service` before executing `dashboard.py`. No HTTP server or browser is required.

---

## Architecture

| File | Role |
|------|------|
| `mock_app.py` | Patches data/service modules + `exec()` of the real dashboard.py |
| `conftest.py` | `app_authenticated` and `app_unauthenticated` fixtures via `AppTest.from_file` |
| `test_integration.py` | 42 tests organized in 8 classes |

### Mock Data

- **24 months** of financial data (Jan 2024 → Dec 2025)
- Test user: `testuser` / bcrypt hash of `"testpass123"`
- Built-in edge cases: negative savings (Dec 2024), zero savings (Dec 2025)

---

## `TestLoginFlow` — Authentication Flow (3 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Unauthenticated app | Shows login form (text inputs visible), metrics **not** visible |
| 2 | Wrong password (`"wrongpassword"`) | Error message containing `"incorretos"` |
| 3 | Authenticated user | Dashboard rendered without exceptions, metrics visible |

---

## `TestPageStructure` — Page Structure (6 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Main title | Markdown contains `"Dashboard Financeiro"` |
| 2 | Welcome message | Markdown contains `"Test User"` |
| 3 | Subheaders present | `"Métricas"`, `"Destaques"`, `"Gráficos"`, `"Tabela"` rendered |
| 4 | No errors on load | No exceptions, no `st.error` calls |
| 5 | No warnings with valid data | No `st.warning` rendered |
| 6 | Footer caption | Caption contains `"Dashboard Financeiro"` |

---

## `TestKpiMetrics` — KPI Metrics (9 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Metric count | At least 8 metrics rendered |
| 2 | "Total de Receita" metric | Label present |
| 3 | "Total de Gastos" metric | Label present |
| 4 | "Economia" metric | Label present |
| 5 | "Média de Gastos" metric | Label present |
| 6 | "Mediana" metric | Label present |
| 7 | "Projeção" (annual) metric | Label present |
| 8 | Currency values | The 4 primary metrics contain `"R$"` |
| 9 | Non-zero values | None of the 4 primary metrics is `"R$ 0,00"` |

---

## `TestHighlights` — Monthly Highlights (9 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Highlight count | 6 metrics with `"Maior"` or `"Menor"` in label |
| 2 | Highest Income | Label present |
| 3 | Lowest Income | Label present |
| 4 | Highest Expense | Label present |
| 5 | Lowest Expense | Label present |
| 6 | Highest Savings | Label present |
| 7 | Lowest Savings | Label present |
| 8 | Currency values | All highlights contain `"R$"` |
| 9 | Savings deltas | Savings metrics have delta with `"da receita"` |

---

## `TestCharts` — Charts (2 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Chart tabs rendered | At least 1 tab present |
| 2 | No crash on render | No exceptions when rendering all charts |

---

## `TestSummaryTable` — Summary Table (2 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | DataFrame rendered | At least 1 `st.dataframe` present |
| 2 | "Média de Economia" metric above table | Label present in metrics |

---

## `TestPeriodFilter` — Period Filter (8 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Default filter (All) | All 8+ metrics rendered |
| 2 | Single month (Jan 2024 → Jan 2024) | No exceptions, 8+ metrics |
| 3 | Last month (Dec 2025 → Dec 2025) | No exceptions, 8+ metrics |
| 4 | First half 2024 (Jan → Jun) | No exceptions, 8+ metrics |
| 5 | Year 2025 (Jan → Dec) | No exceptions, 8+ metrics |
| 6 | Selectboxes with 24 options | Both selectboxes have exactly 24 items |
| 7 | First option = `"Janeiro 2024"` | Start selectbox begins at Jan 2024 |
| 8 | Last option = `"Dezembro 2025"` | End selectbox ends at Dec 2025 |

---

## `TestEdgeCases` — Edge Cases (3 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Negative savings in dataset (Dec 2024) | App renders without exceptions |
| 2 | Zero savings in dataset (Dec 2025) | App renders without exceptions |
| 3 | Multiple consecutive runs | Metrics identical on 1st and 2nd run (stability) |
