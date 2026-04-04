import re
from datetime import datetime

import pandas as pd

from constants import MONTH_NAME_TO_NUMBER


def format_currency_br(value):
    """Format a number in Brazilian notation (e.g. 1.234,56)."""
    if pd.isna(value):
        return ""
    try:
        return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except ValueError:
        return str(value)


def parse_brl_value(raw):
    """Parse a BRL currency string (e.g. 'R$ 1.234,56') into a float."""
    if not raw:
        return 0.0
    try:
        return float(str(raw).replace('R$', '').replace('.', '').replace(',', '.'))
    except ValueError:
        return None


def parse_sheet_name_to_date(sheet_name):
    """Parse a sheet tab name (e.g. 'Janeiro 2023') into a date."""
    match = re.match(r'([a-zA-ZçÇ]+)\s+(\d{2,4})', sheet_name, re.IGNORECASE)
    if not match:
        return None

    month = MONTH_NAME_TO_NUMBER.get(match.group(1).lower())
    if not month:
        return None

    year_str = match.group(2)
    year = int(year_str)
    if len(year_str) == 2:
        current_century = (datetime.now().year // 100) * 100
        cutoff = datetime.now().year % 100 + 5
        year = (current_century - 100 + year) if year > cutoff else (current_century + year)

    try:
        return datetime(year, month, 1).date()
    except ValueError:
        return None


def fmt_delta(val):
    """Format a delta percentage value for display in KPI metrics."""
    return f"{val:+.1f}% vs média" if val is not None else None
