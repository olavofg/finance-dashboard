import gspread
import pandas as pd
import streamlit as st

from constants import EXPENSES_CELL, INCOME_CELL, SUMMARY_COLUMNS
from helpers import parse_brl_value, parse_sheet_name_to_date


@st.cache_resource
def authenticate_gspread(creds_dict):
    """Authenticate with Google Sheets API."""
    return gspread.service_account_from_dict(creds_dict)


@st.cache_data(ttl=3600)
def load_monthly_financial_summary(_gc, url):
    """Load and summarize monthly financial data from Google Sheets.

    Returns (DataFrame, list[str]) — the summary data and any warnings.
    """
    warnings = []

    spreadsheet, worksheets, err = _open_spreadsheet(_gc, url)
    if err:
        return pd.DataFrame(columns=SUMMARY_COLUMNS), [err]

    sheet_info = _filter_valid_sheets(worksheets)
    if not sheet_info:
        warnings.append(
            "Nenhuma aba com nome de mês/ano válido foi encontrada na sua planilha. "
            "Verifique os nomes das suas abas (ex: 'Janeiro 2023')."
        )
        return pd.DataFrame(columns=SUMMARY_COLUMNS), warnings

    value_ranges, err = _batch_fetch_cells(spreadsheet, sheet_info)
    if err:
        return pd.DataFrame(columns=SUMMARY_COLUMNS), [err]

    all_data, parse_warnings = _parse_sheet_values(sheet_info, value_ranges)
    warnings.extend(parse_warnings)

    return _build_summary_dataframe(all_data, warnings)


def _open_spreadsheet(_gc, url):
    """Open a spreadsheet by URL. Returns (spreadsheet, worksheets, error_msg)."""
    try:
        spreadsheet = _gc.open_by_url(url)
        return spreadsheet, spreadsheet.worksheets(), None
    except Exception as e:
        return None, None, f"Erro ao abrir a planilha ou listar abas: {e}. Verifique a URL e permissões."


def _filter_valid_sheets(worksheets):
    """Filter worksheets to only those with valid month/year names."""
    sheet_info = [(ws.title, parse_sheet_name_to_date(ws.title)) for ws in worksheets]
    return [(name, date) for name, date in sheet_info if date]


def _batch_fetch_cells(spreadsheet, sheet_info):
    """Fetch expense and income cells for all sheets in a single API call."""
    ranges = []
    for sheet_name, _ in sheet_info:
        quoted = f"'{sheet_name}'"
        ranges.append(f"{quoted}!{EXPENSES_CELL}")
        ranges.append(f"{quoted}!{INCOME_CELL}")

    try:
        batch_result = spreadsheet.values_batch_get(ranges)
        return batch_result.get('valueRanges', []), None
    except Exception as e:
        return None, f"Erro ao buscar dados das abas em lote: {e}. Verifique a URL e permissões."


def _parse_sheet_values(sheet_info, value_ranges):
    """Parse raw cell values into structured data dicts."""
    all_data = []
    warnings = []

    for i, (sheet_name, _) in enumerate(sheet_info):
        try:
            expenses_data = value_ranges[i * 2] if i * 2 < len(value_ranges) else {}
            income_data = value_ranges[i * 2 + 1] if i * 2 + 1 < len(value_ranges) else {}

            expenses_values = expenses_data.get('values', [[]])
            income_values = income_data.get('values', [[]])

            expenses_raw = expenses_values[0][0] if expenses_values and expenses_values[0] else None
            income_raw = income_values[0][0] if income_values and income_values[0] else None

            expenses = parse_brl_value(expenses_raw)
            if expenses is None:
                warnings.append(f"Formato inválido na célula {EXPENSES_CELL} da aba '{sheet_name}'. Usando 0.0 para gastos.")
                expenses = 0.0

            income = parse_brl_value(income_raw)
            if income is None:
                warnings.append(f"Formato inválido na célula {INCOME_CELL} da aba '{sheet_name}'. Usando 0.0 para receita.")
                income = 0.0

            all_data.append({
                'Mês': sheet_name,
                'Total de Gastos': expenses,
                'Total de Receita': income,
                'Data do Mês': parse_sheet_name_to_date(sheet_name)
            })
        except Exception as e:
            warnings.append(f"Erro ao processar a aba '{sheet_name}': {e}. Verifique as células {EXPENSES_CELL} e {INCOME_CELL}.")

    return all_data, warnings


def _build_summary_dataframe(all_data, warnings):
    """Build the final summary DataFrame with computed columns."""
    df = pd.DataFrame(all_data)
    df['Data do Mês'] = pd.to_datetime(df['Data do Mês'], errors='coerce')
    df.dropna(subset=['Data do Mês'], inplace=True)

    if df.empty:
        warnings.append("Nenhum dado válido foi carregado após o processamento das abas.")
        return pd.DataFrame(columns=SUMMARY_COLUMNS), warnings

    df.sort_values('Data do Mês', inplace=True)
    df['Economia'] = df['Total de Receita'] - df['Total de Gastos']
    receita = df['Total de Receita']
    df['Taxa de Economia (%)'] = df['Economia'].div(receita).where(receita != 0, 0) * 100
    return df, warnings
