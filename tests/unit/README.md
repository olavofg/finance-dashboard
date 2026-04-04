# Unit Tests

**181 scenarios** covering formatting, parsing, data access, Streamlit configuration, and dashboard logic.

---

## `test_helpers.py` — Formatting & Parsing Functions

### `TestFormatCurrencyBr` (15 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Positive integer (`1000`) | `"1.000,00"` |
| 2 | Positive decimal (`1234.56`) | `"1.234,56"` |
| 3 | Zero (`0`) | `"0,00"` |
| 4 | Negative number (`-500.10`) | `"-500,10"` |
| 5 | Large number (`1_000_000`) | `"1.000.000,00"` |
| 6 | Small decimal (`0.01`) | `"0,01"` |
| 7 | Very large number (`999_999_999.99`) | `"999.999.999,99"` |
| 8 | `NaN` | `""` (empty string) |
| 9 | `None` | `""` (empty string) |
| 10 | Numeric string (`"2500.75"`) | `"2.500,75"` |
| 11 | Non-numeric string (`"abc"`) | `"abc"` (returned as-is) |
| 12 | Large negative (`-1_234_567.89`) | `"-1.234.567,89"` |
| 13 | Infinity (`float("inf")`) | Returns a string without error |
| 14 | Rounding (`1.999`) | `"2,00"` |
| 15 | Banker's rounding (`1.555`) | `"1,55"` or `"1,56"` (Python behavior) |

### `TestParseBrlValue` (15 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Standard BRL (`"R$ 1.234,56"`) | `1234.56` |
| 2 | Without symbol (`"1.234,56"`) | `1234.56` |
| 3 | Float with dot (`"1234.56"`) | `123456.0` (dot treated as thousands separator) |
| 4 | Integer string (`"5000"`) | `5000.0` |
| 5 | Zero (`"0"`) | `0.0` |
| 6 | Empty string (`""`) | `0.0` |
| 7 | `None` | `0.0` |
| 8 | Invalid format (`"abc"`) | `None` |
| 9 | Negative value (`"-500,00"`) | `-500.0` |
| 10 | Extra spaces (`"R$  3.500,00"`) | `3500.0` |
| 11 | Large value (`"R$ 999.999,99"`) | `999999.99` |
| 12 | Integer input (`5000`) | `5000.0` |
| 13 | Float input (`3500.50`) | `35005.0` (float→str produces dot which gets stripped) |
| 14 | Symbol only (`"R$"`) | `None` |
| 15 | Whitespace only (`"   "`) | `None` |

### `TestParseSheetNameToDate` (20 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Standard name (`"Janeiro 2024"`) | `date(2024, 1, 1)` |
| 2 | Lowercase (`"janeiro 2024"`) | `date(2024, 1, 1)` |
| 3 | Uppercase (`"MARÇO 2023"`) | `date(2023, 3, 1)` |
| 4 | Mixed case (`"fEvErEiRo 2024"`) | `date(2024, 2, 1)` |
| 5 | Two-digit year (`"Maio 25"`) | `date(2025, 5, 1)` |
| 6–17 | All 12 months (parametrized) | `date(2024, N, 1)` for each month N=1..12 |
| 18 | Invalid month name (`"InvalidMonth 2024"`) | `None` |
| 19 | English month (`"January 2024"`) | `None` |
| 20 | Spanish month (`"Enero 2024"`) | `None` |
| 21 | No year (`"Janeiro"`) | `None` |
| 22 | Summary tab (`"Resumo"`) | `None` |
| 23 | Dashboard tab (`"Dashboard"`) | `None` |
| 24 | Numbers only (`"12 2024"`) | `None` |
| 25 | Empty string (`""`) | `None` |
| 26 | Extra spaces (`"Janeiro  2024"`) | `not None` (regex uses `\s+`) |
| 27 | With cedilla (`"Março 2025"`) | `date(2025, 3, 1)` |
| 28 | Far future year (`"Janeiro 2099"`) | `date(2099, 1, 1)` |
| 29 | Year 2000 (`"Dezembro 2000"`) | `date(2000, 12, 1)` |

### `TestFmtDelta` (6 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Positive (`12.3`) | `"+12.3% vs média"` |
| 2 | Negative (`-5.0`) | `"-5.0% vs média"` |
| 3 | Zero (`0.0`) | `"+0.0% vs média"` |
| 4 | `None` | `None` |
| 5 | Small positive (`0.1`) | `"+0.1% vs média"` |
| 6 | Large negative (`-99.9`) | `"-99.9% vs média"` |

---

## `test_data_service.py` — Data Access Layer (Google Sheets)

> All tests use gspread mocks — no network calls are made.

### `TestOpenSpreadsheet` (3 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Successful open | `err=None`, returns 3 worksheets |
| 2 | Permission denied | `ss=None`, `ws=None`, error contains `"Erro ao abrir"` |
| 3 | Invalid URL | Error contains `"Erro ao abrir"` |

### `TestFilterValidSheets` (5 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | All valid (`"Janeiro"`, `"Fevereiro"`) | Returns 2 sheets |
| 2 | Mix valid/invalid (`"Resumo"`, `"Dashboard"`, `"Config"` + 2 months) | Returns only the 2 month sheets |
| 3 | None valid (`"Resumo"`, `"Dashboard"`) | Empty list |
| 4 | Empty input list | Empty list |
| 5 | Duplicate names (`"Janeiro 2024"` × 2) | Returns both (dedup is not the filter's responsibility) |

### `TestBatchFetchCells` (3 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Successful fetch (2 sheets) | `err=None`, returns 4 ranges (2 sheets × 2 cells) |
| 2 | API error (`"Quota exceeded"`) | `ranges=None`, error contains `"Erro ao buscar"` |
| 3 | Empty sheet list | `err=None`, empty ranges |

### `TestParseSheetValues` (7 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Normal values (`"R$ 3.500,00"` / `"R$ 8.000,00"`) | Expenses=3500.0, Income=8000.0, no warnings |
| 2 | Empty cells | Expenses=0.0, Income=0.0 (defaults) |
| 3 | Invalid expense format (`"abc"`) | Expenses=0.0, 1 warning with `"Formato inválido"` and `"gastos"` |
| 4 | Invalid income format | Income=0.0, 1 warning with `"receita"` |
| 5 | Both invalid | Both=0.0, 2 warnings |
| 6 | Truncated API response (2 sheets, data for 1 only) | 2 rows; February defaults to 0.0 |
| 7 | Multiple sheets (3 months) | 3 data rows, no warnings |

### `TestBuildSummaryDataframe` (7 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Normal data (2 months) | DataFrame with correct `Economia` and `Taxa de Economia (%)` columns |
| 2 | Savings rate calculation (50%) | Expenses=5000, Income=10000 → Rate=50.0% |
| 3 | Zero income (division by zero) | Savings Rate=0, no crash |
| 4 | Negative savings (expenses > income) | Savings=-500.0, negative rate |
| 5 | Date sorting | March before January in input → January first in output |
| 6 | Empty/invalid data | Empty DataFrame, warning `"Nenhum dado válido"` |
| 7 | Invalid date rows dropped | `"not-a-date"` removed, only 1 valid row remains |

### `TestLoadMonthlyFinancialSummary` (17 tests)

> Uses `__wrapped__` to bypass `@st.cache_data`.

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Full 24-month pipeline | 24 rows, all columns present, no warnings |
| 2 | 3 months | 3 rows, correct values (Expenses=3500.0, Income=8000.0) |
| 3 | Spreadsheet open error | Empty DataFrame, 1 warning `"Erro ao abrir"` |
| 4 | Batch fetch error | Empty DataFrame, warning `"Erro ao buscar"` |
| 5 | No valid tabs | Empty DataFrame, warning `"Nenhuma aba"` |
| 6 | Mix of valid and invalid tabs | Only 2 rows (invalid tabs ignored) |
| 7 | Empty cells | 2 rows with Expenses=0.0 and Income=0.0 |
| 8 | Invalid cell values | 2 rows defaults=0.0, 2 warnings |
| 9 | Zero income → savings rate | Savings Rate=0 (no division by zero) |
| 10 | Single month | 1 row, month `"Março 2025"` |
| 11 | Negative savings in all months | All Savings<0, all rates<0 |
| 12 | 24 months sorted chronologically | Dates in ascending order |
| 13 | Savings column = Income − Expenses | Verified for each row |
| 14 | Savings Rate = (Savings/Income)×100 | Verified for each row with income>0 |
| 15 | December 2024 with negative savings | Fixture: expenses R$9,000 > income R$8,500 |
| 16 | December 2025 with zero savings | Fixture: expenses = income = R$8,000 |

---

## `test_streamlit_service.py` — Configuration & Secrets

### `TestConvertSecretsToDict` (7 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Plain dict | Returns the same dict |
| 2 | Nested dict | Returns preserving nesting |
| 3 | List | Returns the same list |
| 4 | Primitives (`"hello"`, `42`, `True`) | Returns the value as-is |
| 5 | `None` | Returns `None` |
| 6 | Object with `_data` attribute | Extracts and returns `_data` |
| 7 | Object with `to_dict()` method | Calls `to_dict()` and returns result |

### `TestGetUserCredentials` (4 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Credentials from `st.secrets` | Returns credentials from secrets |
| 2 | Credentials from local YAML file | Reads and returns config from file |
| 3 | No secrets, no local file | Returns `None` |
| 4 | Corrupted YAML file | Returns `None` (no crash) |

### `TestGetGoogleSheetsCredentials` (3 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Credentials from local JSON file | Returns dict with `type`, `project_id` |
| 2 | No file, no secrets | Returns `None` |
| 3 | Corrupted JSON file | Returns `None` (no crash) |

### `TestGetSheetUrl` (3 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | URL from local config | Returns the spreadsheet URL |
| 2 | No source available | Returns `None` |
| 3 | Config without `sheet_url` key | Returns `None` |

### `TestValidateSecrets` (5 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Local files present | `None` (validation skipped) |
| 2 | No `secrets` attribute | Error message containing `"secrets"` |
| 3 | Secrets missing required keys | Error mentioning `"user_credentials"` |
| 4 | All secrets present | `None` (valid) |
| 5 | Partial secrets (missing `google_sheets_credentials` and `sheet_url`) | Error message |

---

## `test_dashboard.py` — Dashboard Logic

### `TestValidateConfig` (18 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Fully valid config | `None` (no error) |
| 2 | `None` as config | Error: `"não encontradas"` |
| 3 | Empty dict | Error: `"não encontradas"` |
| 4 | Missing `credentials` | Error mentioning `"credentials"` |
| 5 | Missing `cookie` | Error mentioning `"cookie"` |
| 6 | Missing both (`credentials` and `cookie`) | Error mentioning both |
| 7 | Empty cookie (`{}`) | Error mentioning `"cookie"` |
| 8 | Cookie `None` | Error mentioning `"cookie"` |
| 9 | Missing `cookie.name` | Error mentioning `"name"` |
| 10 | Missing `cookie.key` | Error mentioning `"key"` |
| 11 | Missing `cookie.expiry_days` | Error mentioning `"expiry_days"` |
| 12 | All cookie fields missing | Error mentioning `"name"` |
| 13 | Empty `usernames` | Error: `"Nenhum usuário"` |
| 14 | No `usernames` key | Error: `"Nenhum usuário"` |
| 15 | User without password (empty string) | Error mentioning `"testuser"` and `"senha"` |
| 16 | User with password `None` | Error mentioning `"testuser"` |
| 17 | Multiple users, one without password | Error mentioning `"user2"` |
| 18 | Multiple valid users | `None` (no error) |

### `TestPeriodPresets` (4 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Expected keys | `{"Tudo", "Últimos 12", "Últimos 6", "Ano atual"}` |
| 2 | `"Tudo"` is `None` | No period filter applied |
| 3 | `"Ano atual"` is `None` | Special handling in dashboard |
| 4 | Numeric presets | `"Últimos 12"=12`, `"Últimos 6"=6` |

### `TestKpiMetrics` (7 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Total income | Value > 0 |
| 2 | Total expenses | Value > 0 |
| 3 | Net savings = Income − Expenses | Exact match (pytest.approx) |
| 4 | Average expenses = sum / month count | Exact match |
| 5 | Median expenses | Between min and max |
| 6 | Annual projection = avg savings × 12 | Value > 0 (fixture is net positive overall) |
| 7 | Average savings rate | Between -100% and 100% |

### `TestDeltaComputation` (3 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Full range (filter = baseline) | `None` (no delta to compare) |
| 2 | Partial range (2025 onward) | Float with % variation |
| 3 | Single-month filter (Nov 2024) | Float with % variation |

### `TestHighlights` (8 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Highest expense | Value = max of `Total de Gastos` column |
| 2 | Lowest expense | Value = min of `Total de Gastos` column |
| 3 | Highest income | `R$ 10.500,00` (Nov 2025 in fixture) |
| 4 | Lowest income | `R$ 8.000,00` (multiple months in fixture) |
| 5 | Highest savings | Value = max of `Economia` column |
| 6 | Lowest savings | Value = min of `Economia` column |
| 7 | Negative savings exists (Dec 2024) | Expenses R$9,000 > Income R$8,500 |
| 8 | Zero savings exists (Dec 2025) | Expenses = Income = R$8,000 |

### `TestCompositionChart` (3 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Normal composition | expenses% + savings% = 100% for each month |
| 2 | Zero total (expenses + savings = 0) | Both = 0% (fillna(0) prevents NaN) |
| 3 | Negative savings | expenses% > 100%, savings% < 0% |

### `TestDateFilter` (7 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Full range (min→max) | 24 months |
| 2 | Single month (Jun 2024) | 1 month |
| 3 | Last 6 months (Jul–Dec 2025) | 6 months |
| 4 | Last 12 months (Jan–Dec 2025) | 12 months |
| 5 | Year 2024 | 12 months |
| 6 | Future filter (2030) | Empty DataFrame |
| 7 | Start date after end date | Empty DataFrame |

### `TestCumulativeSavings` (3 tests)

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | All positive (3 months) | Cumsum monotonically increasing |
| 2 | Month with negative savings (Dec 2024) | Cumsum decreases at that point |
| 3 | Month with zero savings (Dec 2025) | Cumsum stays equal to previous month |

---

## Shared Fixtures (`conftest.py`)

| Fixture | Description |
|---------|-------------|
| `MONTHLY_DATA_24` | 24-month dataset (Jan 2024 → Dec 2025) with built-in edge cases |
| `mock_gc_24` | gspread mock with 24 valid sheets |
| `mock_gc_3` | gspread mock with 3 sheets (Jan–Mar 2024) |
| `mock_gc_with_invalid_tabs` | 2 valid sheets + 3 invalid (Resumo, Dashboard, Config) |
| `mock_gc_only_invalid_tabs` | Only invalid sheets |
| `mock_gc_open_error` | Simulates spreadsheet open failure |
| `mock_gc_batch_error` | Simulates batch API failure |
| `mock_gc_empty_cells` | Empty expense and income cells |
| `mock_gc_invalid_values` | Non-numeric cell values |
| `mock_gc_zero_income` | Income = 0 (division by zero test) |
| `mock_gc_single_month` | Only 1 sheet (Março 2025) |
| `mock_gc_negative_savings` | All months with expenses > income |
| `valid_config` | Fully valid config for `_validate_config` |

### Edge Cases in Dataset (24 months)

| Month | Expenses | Income | Scenario |
|-------|----------|--------|----------|
| Dec 2024 | R$ 9,000 | R$ 8,500 | **Negative** savings (−R$ 500) |
| Dec 2025 | R$ 8,000 | R$ 8,000 | **Zero** savings |
| Oct 2024 | R$ 4,500 | R$ 8,200 | Near-breakeven (relatively low savings) |
