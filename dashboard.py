from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit_authenticator as stauth
from dateutil.relativedelta import relativedelta

from constants import MONTH_NAMES_PT, PERIOD_PRESETS
from data_service import authenticate_gspread, load_monthly_financial_summary
from helpers import fmt_delta, format_currency_br
from streamlit_service import StreamlitCloudService


st.set_page_config(
    page_title="Dashboard Financeiro",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="collapsed",
)


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


@st.cache_resource
def _get_streamlit_service():
    return StreamlitCloudService()


streamlit_service = _get_streamlit_service()

st.markdown("## 📊 Dashboard Financeiro Pessoal")
st.markdown("Visualizando receitas, gastos e indicadores financeiros.")
top_bar = st.container()
st.markdown("---")

secrets_error = streamlit_service.validate_secrets()
if secrets_error:
    _show_config_error(secrets_error)

try:
    config = streamlit_service.get_user_credentials()
    config_error = _validate_config(config)
    if config_error:
        _show_config_error(config_error)

    google_sheets_credentials = streamlit_service.get_google_sheets_credentials()
    if not google_sheets_credentials:
        _show_config_error("Credenciais do Google Sheets não encontradas.")
except Exception as e:
    _show_config_error(f"Erro crítico ao carregar configurações: {e}")

authenticator = stauth.Authenticate(
    config['credentials'],
    cookie_name=config['cookie']['name'],
    cookie_key=config['cookie']['key'],
    cookie_expiry_days=config['cookie']['expiry_days'],
)

if st.session_state.get('authentication_status'):
    name = st.session_state.get('name')
else:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        name, auth_status, _ = authenticator.login(
            location='main',
            fields={
                'Form name': '🔐 Acessar Dashboard Financeiro',
                'Username': 'Usuário',
                'Password': 'Senha',
                'Login': 'Entrar',
            },
        )

    if auth_status is False:
        with col2:
            st.error("Usuário ou senha incorretos.")
        st.stop()
    elif auth_status is None:
        st.stop()

with top_bar:
    col_welcome, col_update, col_logout = st.columns([9, 1, 1], gap="small")
    col_welcome.markdown(f"#### 👋 Bem-vindo(a), **{name}**")

    if col_update.button("🔄 Atualizar"):
        st.cache_data.clear()
        st.rerun()

    with col_logout:
        authenticator.logout(button_name="🔓 Sair", location='main')

try:
    gc = authenticate_gspread(google_sheets_credentials)
except Exception as e:
    _show_config_error(f"Erro ao autenticar com Google Sheets: {e}")

sheet_url = streamlit_service.get_sheet_url()
if not sheet_url:
    _show_config_error("URL da planilha não encontrada.")

df_summary, data_warnings = load_monthly_financial_summary(gc, sheet_url)
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
current_month_start = datetime.now().replace(day=1).date()

with st.expander("📅 Filtro de Período", expanded=True):
    preset = st.segmented_control(
        "Período rápido:",
        options=list(PERIOD_PRESETS.keys()),
        default='Tudo',
        selection_mode='single',
    )

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
        cutoff = current_month_start - relativedelta(months=PERIOD_PRESETS[preset])
        default_start_index = 0
        for i, (_, d) in enumerate(month_year_options):
            if pd.Timestamp(d).date() >= cutoff:
                default_start_index = i
                break
    else:
        default_start_index = 0

    col1, col2 = st.columns(2)
    start_month_str = col1.selectbox("Mês de Início:", options=month_year_strings, index=default_start_index)
    end_month_str = col2.selectbox("Mês de Fim:", options=month_year_strings, index=default_end_index)

start_date = next((d for s, d in month_year_options if s == start_month_str), None)
end_date_raw = next((d for s, d in month_year_options if s == end_month_str), None)
end_date = end_date_raw.replace(day=pd.Timestamp(end_date_raw).days_in_month) if end_date_raw else None

if not start_date or not end_date:
    st.warning("Não foi possível determinar o período de filtro.")
    st.stop()

if start_date > end_date:
    st.error("O mês de início não pode ser posterior ao mês de fim.")
    st.stop()

df_filtered = df_summary[
    (df_summary['Data do Mês'] >= start_date) & (df_summary['Data do Mês'] <= end_date)
].copy()

if df_filtered.empty:
    st.info("Não há dados para o período selecionado.")
    st.stop()

# KPIs
st.subheader("📈 Métricas de Resumo do Período")
col1, col2, col3, col4 = st.columns(4)

total_income = df_filtered['Total de Receita'].sum()
total_expenses = df_filtered['Total de Gastos'].sum()
net_savings = df_filtered['Economia'].sum()
avg_expenses = df_filtered['Total de Gastos'].mean()

# Delta: filtered period avg vs overall avg (excluding current/future months)
df_baseline = df_summary[df_summary['Data do Mês'] < pd.Timestamp(current_month_start)]
if len(df_baseline) > len(df_filtered):
    avg_income_all = df_baseline['Total de Receita'].mean()
    avg_expenses_all = df_baseline['Total de Gastos'].mean()
    avg_savings_all = df_baseline['Economia'].mean()

    avg_income_filt = df_filtered['Total de Receita'].mean()
    avg_expenses_filt = df_filtered['Total de Gastos'].mean()
    avg_savings_filt = df_filtered['Economia'].mean()

    delta_income = ((avg_income_filt - avg_income_all) / avg_income_all * 100) if avg_income_all else None
    delta_expenses = ((avg_expenses_filt - avg_expenses_all) / avg_expenses_all * 100) if avg_expenses_all else None
    delta_savings = ((avg_savings_filt - avg_savings_all) / abs(avg_savings_all) * 100) if avg_savings_all else None
else:
    delta_income = delta_expenses = delta_savings = None

col1.metric("💵 Total de Receita", f"R$ {format_currency_br(total_income)}", delta=fmt_delta(delta_income))
col2.metric("💰 Total de Gastos", f"R$ {format_currency_br(total_expenses)}", delta=fmt_delta(delta_expenses), delta_color="inverse")
col3.metric("📈 Economia Líquida", f"R$ {format_currency_br(net_savings)}", delta=fmt_delta(delta_savings))
col4.metric("📊 Média de Gastos Mensais", f"R$ {format_currency_br(avg_expenses)}")

col5, col6, col7, col8 = st.columns(4)

median_expenses = df_filtered['Total de Gastos'].median()
avg_income = df_filtered['Total de Receita'].mean()
annual_projection = df_filtered['Economia'].mean() * 12
avg_savings_rate = df_filtered['Taxa de Economia (%)'].mean()

col5.metric("📊 Mediana de Gastos", f"R$ {format_currency_br(median_expenses)}")
col6.metric("📌 Taxa Média de Economia", f"{format_currency_br(avg_savings_rate)}%")
col7.metric("📅 Projeção Anual", f"R$ {format_currency_br(annual_projection)}")
col8.metric("💵 Média de Receita", f"R$ {format_currency_br(avg_income)}")

with st.expander("ℹ️ Como interpretar as métricas"):
    st.markdown(
        "- **Vs média**: compara a média mensal do período selecionado com a média de todo o histórico.\n"
        "- **Mediana de Gastos**: valor central dos gastos mensais — menos sensível a meses atípicos que a média.\n"
        "- **Projeção Anual**: economia média mensal do período × 12."
    )

st.subheader("🌟 Destaques Mensais")
if not df_filtered.empty:
    highest_expense_month = df_filtered.loc[df_filtered['Total de Gastos'].idxmax()]
    lowest_expense_month = df_filtered.loc[df_filtered['Total de Gastos'].idxmin()]
    highest_savings_month = df_filtered.loc[df_filtered['Economia'].idxmax()]
    lowest_savings_month = df_filtered.loc[df_filtered['Economia'].idxmin()]
    highest_income_month = df_filtered.loc[df_filtered['Total de Receita'].idxmax()]
    lowest_income_month = df_filtered.loc[df_filtered['Total de Receita'].idxmin()]

    col1, col2, col3 = st.columns(3)
    with col1.container(border=True):
        st.metric(f"🟢 Maior Receita — {highest_income_month['Mês']}", f"R$ {format_currency_br(highest_income_month['Total de Receita'])}")
        st.metric(f"🔴 Menor Receita — {lowest_income_month['Mês']}", f"R$ {format_currency_br(lowest_income_month['Total de Receita'])}")
    with col2.container(border=True):
        st.metric(f"🔴 Maior Gasto — {highest_expense_month['Mês']}", f"R$ {format_currency_br(highest_expense_month['Total de Gastos'])}")
        st.metric(f"🟢 Menor Gasto — {lowest_expense_month['Mês']}", f"R$ {format_currency_br(lowest_expense_month['Total de Gastos'])}")
    with col3.container(border=True):
        highest_sav_pct = highest_savings_month['Taxa de Economia (%)']
        lowest_sav_pct = lowest_savings_month['Taxa de Economia (%)']
        st.metric(f"🟢 Maior Economia — {highest_savings_month['Mês']}", f"R$ {format_currency_br(highest_savings_month['Economia'])}", delta=f"{highest_sav_pct:.1f}% da receita", delta_color="off")
        st.metric(f"🔴 Menor Economia — {lowest_savings_month['Mês']}", f"R$ {format_currency_br(lowest_savings_month['Economia'])}", delta=f"{lowest_sav_pct:.1f}% da receita", delta_color="off")
else:
    st.info("Não há dados suficientes no período selecionado para exibir os destaques mensais.")

# Charts
st.subheader("📊 Gráficos de Análise Financeira")
tabs = st.tabs([
    "💼 Receita vs Gastos",
    "📊 Distribuição de Gastos e Economia",
    "💰 Taxa de Economia",
    "📉 Evolução de Gastos e Economia",
    "📈 Economia Acumulada"
])

if not df_filtered.empty:
    with tabs[0]:
        df_chart = df_filtered[['Mês', 'Total de Receita', 'Total de Gastos']].rename(
            columns={'Total de Receita': 'Receita', 'Total de Gastos': 'Gastos'})
        fig = px.bar(
            df_chart.melt(id_vars='Mês', value_vars=['Receita', 'Gastos'],
                         var_name='Tipo', value_name='Valor'),
            x='Mês', y='Valor', color='Tipo', barmode='group', text='Valor',
            labels={'Valor': 'Total (R$)', 'Tipo': 'Tipo de Valor'}
        )
        fig.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
        fig.update_layout(yaxis_tickprefix="R$ ")
        st.plotly_chart(fig, width='stretch')

    with tabs[1]:
        df_comp = df_filtered[['Mês', 'Total de Gastos', 'Economia']].copy()
        total = df_comp['Total de Gastos'] + df_comp['Economia']
        df_comp['Gastos (%)'] = df_comp['Total de Gastos'].div(total).fillna(0) * 100
        df_comp['Economia (%)'] = df_comp['Economia'].div(total).fillna(0) * 100
        fig = px.bar(
            df_comp.melt(id_vars='Mês', value_vars=['Economia (%)', 'Gastos (%)'],
                        var_name='Tipo', value_name='Percentual'),
            x='Mês', y='Percentual', color='Tipo', barmode='stack', text='Percentual',
            labels={'Percentual': '%', 'Tipo': 'Tipo'},
            color_discrete_map={'Gastos (%)': '#EF553B', 'Economia (%)': '#00CC96'}
        )
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='inside')
        fig.update_layout(yaxis_ticksuffix="%", yaxis_range=[0, 100])
        st.plotly_chart(fig, width='stretch')

    with tabs[2]:
        fig = px.line(df_filtered, x='Mês', y='Taxa de Economia (%)',
                      markers=True, text='Taxa de Economia (%)',
                      labels={'Taxa de Economia (%)': 'Taxa (%)'})
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='top center',
                          line=dict(color='#4A90D9', width=2))
        avg_rate = df_filtered['Taxa de Economia (%)'].mean()
        fig.add_hline(y=avg_rate, line_dash="dash", line_color="rgba(239, 85, 59, 0.6)",
                      annotation_text=f"Média: {avg_rate:.1f}%", annotation_position="top left")
        fig.update_layout(yaxis_ticksuffix="%")
        st.plotly_chart(fig, width='stretch')

    with tabs[3]:
        df_chart = df_filtered[['Mês', 'Total de Gastos', 'Economia']].rename(
            columns={'Total de Gastos': 'Gastos'})
        fig = px.line(
            df_chart.melt(id_vars='Mês', value_vars=['Gastos', 'Economia'],
                         var_name='Tipo', value_name='Valor'),
            x='Mês', y='Valor', color='Tipo', markers=True,
            labels={'Valor': 'Total (R$)', 'Tipo': 'Tipo'},
            color_discrete_map={'Gastos': '#EF553B', 'Economia': '#00CC96'}
        )
        avg_gastos = df_filtered['Total de Gastos'].mean()
        avg_economia = df_filtered['Economia'].mean()
        fig.add_hline(y=avg_gastos, line_dash="dash", line_color="rgba(239, 85, 59, 0.5)",
                      annotation_text=f"Média Gastos: R$ {format_currency_br(avg_gastos)}", annotation_position="top left")
        fig.add_hline(y=avg_economia, line_dash="dash", line_color="rgba(0, 204, 150, 0.5)",
                      annotation_text=f"Média Economia: R$ {format_currency_br(avg_economia)}", annotation_position="bottom left")
        fig.update_layout(yaxis_tickprefix="R$ ")
        st.plotly_chart(fig, width='stretch')

    with tabs[4]:
        cumulative = df_filtered[['Mês', 'Economia']].copy()
        cumulative['Economia Acumulada'] = cumulative['Economia'].cumsum()
        fig = px.area(cumulative, x='Mês', y='Economia Acumulada',
                      text='Economia Acumulada', markers=True,
                      labels={'Economia Acumulada': 'Total Acumulado (R$)'})
        fig.update_traces(texttemplate='R$ %{text:,.2f}', textposition='top center',
                          line=dict(color='#4A90D9'), fillcolor='rgba(74, 144, 217, 0.15)')
        y_max = cumulative['Economia Acumulada'].max()
        y_min = cumulative['Economia Acumulada'].min()
        y_margin = (y_max - y_min) * 0.15 if y_max != y_min else abs(y_max) * 0.15 or 1
        fig.update_layout(
            yaxis_tickprefix="R$ ",
            yaxis_range=[y_min - y_margin * 0.3, y_max + y_margin],
            xaxis=dict(range=[-0.5, len(cumulative) - 0.5]),
        )
        st.plotly_chart(fig, width='stretch')
else:
    st.info("Não há dados no período selecionado para gerar os gráficos.")

# Summary Table
st.subheader("📋 Tabela de Resumo Mensal")
if not df_filtered.empty:
    avg_savings = df_filtered['Economia'].mean()
    col1, _, _ = st.columns([1, 1, 3])
    col1.metric("📌 Média de Economia", f"R$ {format_currency_br(avg_savings)}")
    st.dataframe(
        df_filtered[['Mês', 'Total de Receita', 'Total de Gastos', 'Economia', 'Taxa de Economia (%)']].style.format({
            'Total de Gastos': lambda x: f"R$ {format_currency_br(x)}",
            'Total de Receita': lambda x: f"R$ {format_currency_br(x)}",
            'Economia': lambda x: f"R$ {format_currency_br(x)}",
            'Taxa de Economia (%)': lambda x: f"{format_currency_br(x)}%"
        }),
        width='stretch'
    )
else:
    st.info("Não há dados no período selecionado para exibir a tabela de resumo.")

st.caption("Dashboard Financeiro Pessoal.")
