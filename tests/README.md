# Tests

**223 total scenarios** — 181 unit tests + 42 integration tests.

---

## Unit Tests (`tests/unit/`)

Unit tests validate **individual functions and modules in isolation**. Each function is tested with a variety of inputs — valid, invalid, edge cases — and all external dependencies (Google Sheets API, Streamlit secrets) are mocked. These tests are fast, deterministic, and catch regressions in formatting, parsing, data transformation, and configuration logic.

Covered modules: `helpers.py`, `data_service.py`, `streamlit_service.py`, `dashboard.py`.

See [unit/README.md](unit/README.md) for detailed scenario descriptions.

## Integration Tests (`tests/integration/`)

Integration tests run the **real dashboard application end-to-end** with mock data injected at the service boundary. Using Streamlit's built-in `AppTest` framework, the full rendering pipeline is exercised in-memory — authentication flow, KPI metrics, highlights, charts, filters, and summary table — without needing a browser or HTTP server. These tests catch issues that unit tests miss: component wiring, rendering errors, and interaction between modules.

See [integration/README.md](integration/README.md) for detailed scenario descriptions.

---

## How to Run

```bash
# All tests (unit + integration)
python -m pytest tests/ -v

# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests only
python -m pytest tests/integration/ -v

# With short traceback on failure
python -m pytest tests/ -v --tb=short

# Run inside Docker (validates dependencies + Python version)
docker build -t finance-dashboard . && docker run --rm finance-dashboard python -m pytest tests/ -v --tb=short
```
