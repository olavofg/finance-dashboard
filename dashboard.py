import re
from datetime import datetime

import gspread
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit_authenticator as stauth
from dateutil.relativedelta import relativedelta

from streamlit_service import StreamlitCloudService


# Constants

MONTH_NAMES_PT = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}

MONTH_NAME_TO_NUMBER = {name.lower(): num for num, name in MONTH_NAMES_PT.items()}

SUMMARY_COLUMNS = [
    'Mês', 'Total de Gastos', 'Total de Receita',
    'Data do Mês', 'Economia', 'Taxa de Economia (%)'
]

EXPENSES_CELL = 'M27'
INCOME_CELL = 'B6'

# Page config

st.set_page_config(
    page_title="Dashboard Financeiro",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Pure helpers


def format_currency_br(value):
    """Format a numeric value to Brazilian currency format."""
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
    # Normalize 2-digit years to full 4-digit (e.g. 25 -> 2025).
    if len(year_str) == 2:
        current_century = (datetime.now().year // 100) * 100
        cutoff = datetime.now().year % 100 + 5
        year = (current_century - 100 + year) if year > cutoff else (current_century + year)

    try:
        return datetime(year, month, 1).date()
    except ValueError:
        return None


# UI helpers


def _show_config_error(message):
    """Display a configuration error and halt the app."""
    st.error(f"⚠️ Erro de configuração: {message}")
    st.info("Consulte o README para instruções de configuração.")
    st.stop()


def _validate_config(config):
    """Validate config structure. Returns error message or None if valid."""
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


# Cached resources


@st.cache_resource
def get_streamlit_service():
    """Return a singleton StreamlitCloudService instance."""
    return StreamlitCloudService()


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
    all_data = []

    try:
        spreadsheet = _gc.open_by_url(url)
        worksheets = spreadsheet.worksheets()
    except Exception as e:
        return pd.DataFrame(columns=SUMMARY_COLUMNS), [
            f"Erro ao abrir a planilha ou listar abas: {e}. Verifique a URL e permissões."
        ]

    sheet_info = [(ws.title, parse_sheet_name_to_date(ws.title)) for ws in worksheets]
    sheet_info = [(n, d) for n, d in sheet_info if d]

    if not sheet_info:
        warnings.append(
            "Nenhuma aba com nome de mês/ano válido foi encontrada na sua planilha. "
            "Verifique os nomes das suas abas (ex: 'Janeiro 2023')."
        )
        return pd.DataFrame(columns=SUMMARY_COLUMNS), warnings

    # Batch fetch all cells in a single API call
    ranges = []
    for sheet_name, _ in sheet_info:
        quoted = f"'{sheet_name}'"
        ranges.append(f"{quoted}!{EXPENSES_CELL}")
        ranges.append(f"{quoted}!{INCOME_CELL}")

    try:
        batch_result = spreadsheet.values_batch_get(ranges)
    except Exception as e:
        return pd.DataFrame(columns=SUMMARY_COLUMNS), [
            f"Erro ao buscar dados das abas em lote: {e}. Verifique a URL e permissões."
        ]

    value_ranges = batch_result.get('valueRanges', [])

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
            continue

    df = pd.DataFrame(all_data)
    df['Data do Mês'] = pd.to_datetime(df['Data do Mês'], errors='coerce')
    df.dropna(subset=['Data do Mês'], inplace=True)

    if df.empty:
        warnings.append("Nenhum dado válido foi carregado após o processamento das abas.")
        return pd.DataFrame(columns=SUMMARY_COLUMNS), warnings

    df.sort_values('Data do Mês', inplace=True)
    df['Economia'] = df['Total de Receita'] - df['Total de Gastos']
    df['Taxa de Economia (%)'] = df.apply(
        lambda row: (row['Economia'] / row['Total de Receita']) * 100
        if row['Total de Receita'] and row['Total de Receita'] != 0 else 0,
        axis=1
    )
    return df, warnings


# App flow

streamlit_service = get_streamlit_service()

st.markdown("## 📊 Dashboard Financeiro Pessoal")
top_bar = st.container()
description_area = st.container()
st.markdown("---")

# Validate secrets
secrets_error = streamlit_service.validate_secrets()
if secrets_error:
    _show_config_error(secrets_error)

# Load and validate config
try:
    config = streamlit_service.get_user_credentials()
    config_error = _validate_config(config)
    if config_error:
        _show_config_error(config_error)

    google_sheets_credentials = streamlit_service.get_google_sheets_credentials()
    if not google_sheets_credentials:
        _show_config_error("Credenciais do Google Sheets não encontradas. Verifique os secrets ou arquivo credentials.json.")
except Exception as e:
    _show_config_error(f"Erro crítico ao carregar configurações: {e}")

# Authentication
authenticator = stauth.Authenticate(
    config['credentials'],
    cookie_name=config['cookie']['name'],
    cookie_key=config['cookie']['key'],
    cookie_expiry_days=config['cookie']['expiry_days']
)

# Skip login form when already authenticated
if st.session_state.get('authentication_status'):
    name = st.session_state.get('name')
    username = st.session_state.get('username')
else:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        name, auth_status, username = authenticator.login(
            location='main',
            fields={'Form name': '🔐 Acessar Dashboard Financeiro',
                    'Username': 'Usuário', 'Password': 'Senha',
                    'Login': 'Entrar'}
        )

    if auth_status is False:
        with col2:
            st.error("Usuário ou senha incorretos.")
        st.stop()
    elif auth_status is None:
        st.stop()

# Dashboard top bar
with top_bar:
    col_welcome, col_update, col_logout = st.columns([9, 1, 1], gap="small")
    col_welcome.markdown(f"#### 👋 Bem-vindo(a), **{name}**")

    if col_update.button("🔄 Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    with col_logout:
        authenticator.logout(button_name="🔓 Sair", location='main')

# Google Sheets connection
try:
    gc = authenticate_gspread(google_sheets_credentials)
except Exception as e:
    _show_config_error(f"Erro ao autenticar com Google Sheets: {e}")

SHEET_URL = streamlit_service.get_sheet_url()
if not SHEET_URL:
    _show_config_error("URL da planilha não encontrada. Configure 'sheet_url' nos secrets ou no config.yaml.")

with description_area:
    st.markdown("Consolidação automática de receitas, gastos e economia mensal — com métricas, gráficos comparativos e filtros por período.")

# Load data
df_summary, data_warnings = load_monthly_financial_summary(gc, SHEET_URL)
for warning in data_warnings:
    st.warning(warning)

if df_summary.empty:
    st.error("Não foi possível carregar dados financeiros válidos. Verifique sua planilha e clique em 'Atualizar'.")
    st.stop()

# Date filter
month_year_options = [
    (f"{MONTH_NAMES_PT[d.month]} {d.year}", d)
    for d in sorted(df_summary['Data do Mês'].unique())
]
month_year_strings = [opt[0] for opt in month_year_options]

st.subheader("📅 Defina o intervalo de meses")

PERIOD_PRESETS = {
    'Tudo': None,
    'Últimos 12': 12,
    'Últimos 6': 6,
    'Ano atual': None,
}

with st.expander("📅 Filtro de Período", expanded=True):
    preset = st.segmented_control(
        "Período rápido:",
        options=list(PERIOD_PRESETS.keys()),
        default='Tudo',
        selection_mode='single',
    )

    # Compute start/end indices based on preset
    current_month_start = datetime.now().replace(day=1).date()
    default_end_index = len(month_year_strings) - 1
    for i, (_, d) in enumerate(month_year_options):
        if pd.Timestamp(d).date() < current_month_start:
            default_end_index = i

    if preset == 'Tudo':
        default_start_index = 0
    elif preset == 'Ano atual':
        year_start = datetime.now().replace(month=1, day=1).date()
        default_start_index = 0
        for i, (_, d) in enumerate(month_year_options):
            if pd.Timestamp(d).date() >= year_start:
                default_start_index = i
                break
    elif preset and PERIOD_PRESETS.get(preset):
        n_months = PERIOD_PRESETS[preset]
        cutoff = current_month_start - relativedelta(months=n_months)
        default_start_index = 0
        for i, (_, d) in enumerate(month_year_options):
            if pd.Timestamp(d).date() >= cutoff:
                default_start_index = i
                break
    else:
        default_start_index = 0

    col1, col2 = st.columns(2)
    if month_year_strings:
        start_month_str = col1.selectbox("Mês de Início:", options=month_year_strings, index=default_start_index)
        end_month_str = col2.selectbox("Mês de Fim:", options=month_year_strings, index=default_end_index)
    else:
        st.warning("Não há meses válidos para filtrar. Verifique os dados da sua planilha.")
        st.stop()

start_date = next((d for s, d in month_year_options if s == start_month_str), None)
end_date_raw = next((d for s, d in month_year_options if s == end_month_str), None)

if end_date_raw:
    end_date = end_date_raw.replace(day=pd.Timestamp(end_date_raw).days_in_month)
else:
    end_date = None

if start_date and end_date:
    if start_date > end_date:
        st.error("Erro: O mês de início não pode ser posterior ao mês de fim.")
        df_filtered = pd.DataFrame()
    else:
        df_filtered = df_summary[
            (df_summary['Data do Mês'] >= start_date) & (df_summary['Data do Mês'] <= end_date)
        ].copy()
else:
    st.warning("Não foi possível determinar o período de filtro. Verifique os dados da planilha e os nomes das abas.")
    df_filtered = pd.DataFrame()

if df_filtered.empty:
    st.info("Não há dados para o período selecionado ou os dados filtrados resultaram em um DataFrame vazio.")
    st.stop()

# KPIs
st.markdown("---")
st.subheader("📈 Métricas de Resumo do Período")
col1, col2, col3, col4 = st.columns(4)

total_income = df_filtered['Total de Receita'].sum()
total_expenses = df_filtered['Total de Gastos'].sum()
net_savings = df_filtered['Economia'].sum()
avg_expenses = df_filtered['Total de Gastos'].mean()

col1.metric("💵 Total de Receita", f"R$ {format_currency_br(total_income)}")
col2.metric("💰 Total de Gastos", f"R$ {format_currency_br(total_expenses)}")
col3.metric("📈 Economia Líquida", f"R$ {format_currency_br(net_savings)}")
col4.metric("📊 Média de Gastos Mensais", f"R$ {format_currency_br(avg_expenses)}")

# Monthly Highlights
st.markdown("---")
st.markdown("### 🌟 Destaques Mensais")
if not df_filtered.empty:
    highest_expense_month = df_filtered.loc[df_filtered['Total de Gastos'].idxmax()]
    lowest_expense_month = df_filtered.loc[df_filtered['Total de Gastos'].idxmin()]
    highest_savings_month = df_filtered.loc[df_filtered['Economia'].idxmax()]
    lowest_savings_month = df_filtered.loc[df_filtered['Economia'].idxmin()]

    col1, col2 = st.columns(2)
    col1.error(f"📈 Maior Gasto: **{highest_expense_month['Mês']}** — R$ {format_currency_br(highest_expense_month['Total de Gastos'])}")
    col1.info(f"📉 Menor Gasto: **{lowest_expense_month['Mês']}** — R$ {format_currency_br(lowest_expense_month['Total de Gastos'])}")
    col2.success(f"⬆️ Maior Economia: **{highest_savings_month['Mês']}** — R$ {format_currency_br(highest_savings_month['Economia'])}")
    col2.warning(f"⬇️ Menor Economia: **{lowest_savings_month['Mês']}** — R$ {format_currency_br(lowest_savings_month['Economia'])}")
else:
    st.info("Não há dados suficientes no período selecionado para exibir os destaques mensais.")

# Charts
st.markdown("---")
st.subheader("📊 Gráficos de Análise Financeira")
tabs = st.tabs(["💼 Receita vs Gastos", "💸 Economia", "📉 Taxa de Economia", "📊 Gastos Mensais", "📈 Tendência"])

if not df_filtered.empty:
    with tabs[0]:
        fig = px.bar(
            df_filtered.melt(id_vars='Mês', value_vars=['Total de Receita', 'Total de Gastos'],
                            var_name='Tipo', value_name='Valor'),
            x='Mês', y='Valor', color='Tipo', barmode='group', text='Valor',
            labels={'Valor': 'Total (R$)', 'Tipo': 'Tipo de Valor'}
        )
        fig.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
        fig.update_layout(yaxis_tickprefix="R$ ")
        st.plotly_chart(fig, width='stretch')

    with tabs[1]:
        fig = px.bar(df_filtered, x='Mês', y='Economia', text='Economia', color='Economia')
        fig.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
        fig.update_layout(yaxis_tickprefix="R$ ")
        st.plotly_chart(fig, width='stretch')

    with tabs[2]:
        fig = px.bar(df_filtered, x='Mês', y='Taxa de Economia (%)', text='Taxa de Economia (%)',
                    color='Taxa de Economia (%)', color_continuous_scale=px.colors.sequential.Blues)
        fig.update_traces(texttemplate='%{text:,.2f}%', textposition='outside')
        fig.update_layout(yaxis_ticksuffix="%")
        st.plotly_chart(fig, width='stretch')

    with tabs[3]:
        fig = px.bar(df_filtered, x='Mês', y='Total de Gastos', text='Total de Gastos',
                    color_discrete_sequence=px.colors.sequential.Blues_r)
        fig.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
        fig.update_layout(yaxis_tickprefix="R$ ")
        st.plotly_chart(fig, width='stretch')

    with tabs[4]:
        fig = px.line(df_filtered, x='Mês', y='Total de Gastos', markers=True)
        fig.update_traces(line_color='#607B8B', marker_color='#607B8B')
        fig.update_layout(yaxis_tickprefix="R$ ")
        st.plotly_chart(fig, width='stretch')
else:
    st.info("Não há dados no período selecionado para gerar os gráficos.")

# Summary Table
st.markdown("---")
st.subheader("📋 Tabela de Resumo Mensal")
if not df_filtered.empty:
    avg_savings = df_filtered['Economia'].mean()
    avg_savings_rate = df_filtered['Taxa de Economia (%)'].mean()
    col1, col2, _ = st.columns([1, 1, 3])
    col1.metric("📌 Média de Aportes Mensais", f"R$ {format_currency_br(avg_savings)}")
    col2.metric("📌 Média da Taxa de Economia", f"{format_currency_br(avg_savings_rate)}%")
    st.dataframe(
        df_filtered[['Mês', 'Total de Receita', 'Total de Gastos', 'Economia', 'Taxa de Economia (%)']].style.format({
            'Total de Gastos': lambda x: f"R$ {format_currency_br(x)}",
            'Total de Receita': lambda x: f"R$ {format_currency_br(x)}",
            'Economia': lambda x: f"R$ {format_currency_br(x)}",
            'Taxa de Economia (%)': lambda x: f"{format_currency_br(x).replace('R$ ', '')}%"
        }),
        width='stretch'
    )
else:
    st.info("Não há dados no período selecionado para exibir a tabela de resumo.")

st.markdown("---")
st.markdown("Dashboard Financeiro Pessoal.")
