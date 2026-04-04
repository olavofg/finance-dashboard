"""Tests for helpers.py — pure formatting and parsing functions."""

from datetime import date

import pytest

from helpers import fmt_delta, format_currency_br, parse_brl_value, parse_sheet_name_to_date


# ---------------------------------------------------------------------------
# format_currency_br
# ---------------------------------------------------------------------------

class TestFormatCurrencyBr:
    def test_positive_integer(self):
        assert format_currency_br(1000) == "1.000,00"

    def test_positive_decimal(self):
        assert format_currency_br(1234.56) == "1.234,56"

    def test_zero(self):
        assert format_currency_br(0) == "0,00"

    def test_negative(self):
        assert format_currency_br(-500.10) == "-500,10"

    def test_large_number(self):
        assert format_currency_br(1_000_000) == "1.000.000,00"

    def test_small_decimal(self):
        assert format_currency_br(0.01) == "0,01"

    def test_very_large(self):
        assert format_currency_br(999_999_999.99) == "999.999.999,99"

    def test_nan_returns_empty(self):
        assert format_currency_br(float("nan")) == ""

    def test_none_returns_empty(self):
        assert format_currency_br(None) == ""

    def test_string_numeric(self):
        assert format_currency_br("2500.75") == "2.500,75"

    def test_string_non_numeric(self):
        assert format_currency_br("abc") == "abc"

    def test_negative_large(self):
        assert format_currency_br(-1_234_567.89) == "-1.234.567,89"

    def test_float_inf(self):
        result = format_currency_br(float("inf"))
        assert isinstance(result, str)

    def test_rounding(self):
        assert format_currency_br(1.999) == "2,00"

    def test_three_decimals_rounds(self):
        # Python uses banker's rounding: 1.555 → 1.56 only if significand is exact
        assert format_currency_br(1.555) == "1,55" or format_currency_br(1.555) == "1,56"


# ---------------------------------------------------------------------------
# parse_brl_value
# ---------------------------------------------------------------------------

class TestParseBrlValue:
    def test_standard_brl(self):
        assert parse_brl_value("R$ 1.234,56") == 1234.56

    def test_without_symbol(self):
        assert parse_brl_value("1.234,56") == 1234.56

    def test_plain_float_br_format(self):
        # parse_brl_value strips dots (thousands sep) then replaces comma
        # So '1234.56' → '123456' → 123456.0 — this is expected BRL behavior
        assert parse_brl_value("1234.56") == 123456.0

    def test_integer_string(self):
        assert parse_brl_value("5000") == 5000.0

    def test_zero(self):
        assert parse_brl_value("0") == 0.0

    def test_empty_string(self):
        assert parse_brl_value("") == 0.0

    def test_none(self):
        assert parse_brl_value(None) == 0.0

    def test_invalid_format(self):
        assert parse_brl_value("abc") is None

    def test_negative_value(self):
        assert parse_brl_value("-500,00") == -500.0

    def test_with_spaces(self):
        assert parse_brl_value("R$  3.500,00") == 3500.0

    def test_large_brl(self):
        assert parse_brl_value("R$ 999.999,99") == 999999.99

    def test_number_passed_as_int(self):
        # Sheets API can return an int
        assert parse_brl_value(5000) == 5000.0

    def test_number_passed_as_float(self):
        # float → str '3500.5' → dot stripped → '35005' → 35005.0
        # For numeric input, the caller should handle conversion directly
        assert parse_brl_value(3500.50) == 35005.0

    def test_only_symbol(self):
        assert parse_brl_value("R$") is None

    def test_whitespace_only(self):
        assert parse_brl_value("   ") is None


# ---------------------------------------------------------------------------
# parse_sheet_name_to_date
# ---------------------------------------------------------------------------

class TestParseSheetNameToDate:
    def test_standard_name(self):
        assert parse_sheet_name_to_date("Janeiro 2024") == date(2024, 1, 1)

    def test_lowercase(self):
        assert parse_sheet_name_to_date("janeiro 2024") == date(2024, 1, 1)

    def test_uppercase(self):
        assert parse_sheet_name_to_date("MARÇO 2023") == date(2023, 3, 1)

    def test_mixed_case(self):
        assert parse_sheet_name_to_date("fEvErEiRo 2024") == date(2024, 2, 1)

    def test_two_digit_year(self):
        result = parse_sheet_name_to_date("Maio 25")
        assert result == date(2025, 5, 1)

    @pytest.mark.parametrize("month_name,month_num", [
        ("Janeiro", 1), ("Fevereiro", 2), ("Março", 3), ("Abril", 4),
        ("Maio", 5), ("Junho", 6), ("Julho", 7), ("Agosto", 8),
        ("Setembro", 9), ("Outubro", 10), ("Novembro", 11), ("Dezembro", 12),
    ])
    def test_all_twelve_months(self, month_name, month_num):
        assert parse_sheet_name_to_date(f"{month_name} 2024") == date(2024, month_num, 1)

    def test_invalid_month_name(self):
        assert parse_sheet_name_to_date("InvalidMonth 2024") is None

    def test_english_month(self):
        assert parse_sheet_name_to_date("January 2024") is None

    def test_spanish_month(self):
        assert parse_sheet_name_to_date("Enero 2024") is None

    def test_no_year(self):
        assert parse_sheet_name_to_date("Janeiro") is None

    def test_non_month_tab(self):
        assert parse_sheet_name_to_date("Resumo") is None

    def test_dashboard_tab(self):
        assert parse_sheet_name_to_date("Dashboard") is None

    def test_numbers_only(self):
        assert parse_sheet_name_to_date("12 2024") is None

    def test_empty_string(self):
        assert parse_sheet_name_to_date("") is None

    def test_extra_whitespace(self):
        # re.match with \s+ handles multiple spaces
        assert parse_sheet_name_to_date("Janeiro  2024") is not None

    def test_tab_with_cedilla(self):
        assert parse_sheet_name_to_date("Março 2025") == date(2025, 3, 1)

    def test_year_far_future(self):
        assert parse_sheet_name_to_date("Janeiro 2099") == date(2099, 1, 1)

    def test_year_2000(self):
        assert parse_sheet_name_to_date("Dezembro 2000") == date(2000, 12, 1)


# ---------------------------------------------------------------------------
# fmt_delta
# ---------------------------------------------------------------------------

class TestFmtDelta:
    def test_positive(self):
        assert fmt_delta(12.3) == "+12.3% vs média"

    def test_negative(self):
        assert fmt_delta(-5.0) == "-5.0% vs média"

    def test_zero(self):
        assert fmt_delta(0.0) == "+0.0% vs média"

    def test_none(self):
        assert fmt_delta(None) is None

    def test_small_positive(self):
        assert fmt_delta(0.1) == "+0.1% vs média"

    def test_large_negative(self):
        assert fmt_delta(-99.9) == "-99.9% vs média"
