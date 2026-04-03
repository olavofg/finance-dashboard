import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from datetime import datetime
import re
import streamlit_authenticator as stauth
from streamlit_service import StreamlitCloudService

st.set_page_config(
    page_title="Dashboard Financeiro",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializa o serviço do Streamlit Cloud
@st.cache_resource
def get_streamlit_service():
    return StreamlitCloudService()

streamlit_service = get_streamlit_service()

# Valida se todos os secrets obrigatórios estão configurados
if not streamlit_service.validate_secrets():
    st.stop()

# --- CARREGAR CONFIG E CREDENCIAIS ---
try:
    # Obtém configuração de credenciais de usuário dos secrets do Streamlit ou arquivos locais
    config = streamlit_service.get_user_credentials()
    if not config:
        st.error("Configurações de usuário não encontradas. Verifique os secrets ou arquivos de configuração.")
        st.stop()

    # Obtém credenciais do Google Sheets dos secrets do Streamlit ou arquivos locais
    google_sheets_credentials = streamlit_service.get_google_sheets_credentials()
    if not google_sheets_credentials:
        st.error("Credenciais do Google Sheets não encontradas. Verifique os secrets ou arquivo credentials.json.")
        st.stop()

except Exception as e:
    st.error(f"Erro crítico ao carregar configurações: {e}")
    st.stop()

# --- AUTENTICAÇÃO ---
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# A tela de login é a primeira coisa a ser renderizada
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    name, auth_status, username = authenticator.login("🔐 Acessar Dashboard Financeiro", "main")

if auth_status is False:
    with col2:
        st.error("Usuário ou senha incorretos.")
    st.stop()
elif auth_status is None:
    with col2:
        st.info("Por favor, insira suas credenciais.")
    st.stop()

# Impede re-renderização desnecessária após o primeiro login
if 'logged_in_just_now' not in st.session_state:
    st.session_state.logged_in_just_now = True
    st.rerun()
elif st.session_state.logged_in_just_now:
    st.session_state.logged_in_just_now = False

# --- INTERFACE PÓS LOGIN ---
# Este bloco é executado apenas após a autenticação bem-sucedida
with st.container():
    col_welcome_text, col_logout_button = st.columns([10, 1])
    with col_welcome_text:
        st.markdown(f"#### 👋 Bem-vindo(a), **{name}**")
    with col_logout_button:
        authenticator.logout("🔓 Sair", "main")

st.markdown("### 🛠️ Atualização dos Dados")
col_update_button, _ = st.columns([0.15, 0.85])
with col_update_button:
    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear() # Limpa o cache de dados
        st.rerun() # Força uma nova execução do script

st.markdown("## 📊 Dashboard de Controle Financeiro Pessoal")
st.info("Resumo dos seus **gastos** e **rendimentos** mensais, com base nos dados da planilha.")

@st.cache_resource
def authenticate_gspread(creds_dict):
    try:
        return gspread.service_account_from_dict(creds_dict)
    except Exception as e:
        st.error(f"Erro ao autenticar com Google Sheets: {e}")
        st.stop()

gc = authenticate_gspread(google_sheets_credentials)
SHEET_URL = streamlit_service.get_sheet_url()

# Valida se temos a URL da planilha
if not SHEET_URL:
    st.stop()

def format_currency_br(value):
    """Formata um valor numérico para o formato de moeda brasileira."""
    if pd.isna(value): return ""
    # Evita quebra se o valor for None ou não numérico antes da formatação
    try:
        formatted = f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except ValueError:
        return str(value) # Retorna o valor original se a formatação falhar

def parse_sheet_name_to_date(sheet_name):
    """
    Tenta parsear o nome de uma aba para uma data.
    Suporta formatos como 'Janeiro 2023' ou 'Fevereiro 25'.
    """
    months = {'janeiro':1, 'fevereiro':2, 'março':3, 'abril':4, 'maio':5, 'junho':6,
              'julho':7, 'agosto':8, 'setembro':9, 'outubro':10, 'novembro':11, 'dezembro':12}
    # Expressão regular para capturar o nome do mês e o ano (2 ou 4 dígitos)
    match = re.match(r'([a-zA-ZçÇ]+)\s+(\d{2,4})', sheet_name, re.IGNORECASE)
    if match:
        month_name = match.group(1).lower()
        year_str = match.group(2)
        month = months.get(month_name)

        if month:
            year = int(year_str)
            # Ajuste para anos de 2 dígitos: assume o século 21 para anos próximos ao atual
            current_year_last_two_digits = datetime.now().year % 100
            if len(year_str) == 2:
                if year > current_year_last_two_digits + 5:
                    year = (datetime.now().year // 100 - 1) * 100 + year
                else:
                    year = (datetime.now().year // 100) * 100 + year

            try:
                return datetime(year, month, 1).date()
            except ValueError:
                return None
    return None

@st.cache_data(ttl=3600)
def load_monthly_financial_summary(_gc, url):
    """Carrega e sumariza os dados financeiros mensais da planilha do Google Sheets."""
    all_data = []
    try:
        spreadsheet = _gc.open_by_url(url)
        worksheets = spreadsheet.worksheets()
    except Exception as e:
        st.error(f"Erro ao abrir a planilha ou listar abas: {e}. Verifique a URL e permissões.")
        return pd.DataFrame(columns=['Mês', 'Total de Gastos', 'Total de Salário', 'Data do Mês', 'Economia', 'Taxa de Economia (%)'])

    sheet_info = [(ws.title, parse_sheet_name_to_date(ws.title)) for ws in worksheets]
    sheet_info = [(n, d) for n, d in sheet_info if d]

    if not sheet_info:
        st.warning("Nenhuma aba com nome de mês/ano válido foi encontrada na sua planilha. Verifique os nomes das suas abas (ex: 'Janeiro 2023').")
        return pd.DataFrame(columns=['Mês', 'Total de Gastos', 'Total de Salário', 'Data do Mês', 'Economia', 'Taxa de Economia (%)'])

    for name, _ in sheet_info:
        try:
            ws = spreadsheet.worksheet(name)
            gastos_raw = ws.cell(27,13).value
            salario_raw = ws.cell(6,2).value

            gastos = 0.0
            if gastos_raw:
                try:
                    gastos = float(str(gastos_raw).replace('R$', '').replace('.', '').replace(',', '.'))
                except ValueError:
                    st.warning(f"Formato inválido na célula M27 da aba '{name}'. Usando 0.0 para gastos.")

            salario = 0.0
            if salario_raw:
                try:
                    salario = float(str(salario_raw).replace('R$', '').replace('.', '').replace(',', '.'))
                except ValueError:
                    st.warning(f"Formato inválido na célula B6 da aba '{name}'. Usando 0.0 para salário.")

            all_data.append({
                'Mês': name,
                'Total de Gastos': gastos,
                'Total de Salário': salario,
                'Data do Mês': parse_sheet_name_to_date(name)
            })
        except Exception as e:
            st.warning(f"Erro ao processar a aba '{name}': {e}. Verifique as células M27 e B6 e seus formatos.")
            continue

    df = pd.DataFrame(all_data)

    df['Data do Mês'] = pd.to_datetime(df['Data do Mês'], errors='coerce')
    df.dropna(subset=['Data do Mês'], inplace=True)

    if df.empty:
        st.warning("Nenhum dado válido foi carregado após o processamento das abas e filtragem de datas inválidas.")
        return pd.DataFrame(columns=['Mês', 'Total de Gastos', 'Total de Salário', 'Data do Mês', 'Economia', 'Taxa de Economia (%)'])

    df.sort_values('Data do Mês', inplace=True)
    df['Economia'] = df['Total de Salário'] - df['Total de Gastos']
    df['Taxa de Economia (%)'] = df.apply(
        lambda row: (row['Economia'] / row['Total de Salário']) * 100 if row['Total de Salário'] and row['Total de Salário'] != 0 else 0,
        axis=1
    )
    return df

df_summary = load_monthly_financial_summary(gc, SHEET_URL)

if df_summary.empty:
    st.error("Não foi possível carregar dados financeiros válidos para exibição do dashboard. Por favor, verifique sua planilha e clique em 'Atualizar Dados'.")
    st.stop()

month_names_pt = {1:'Janeiro',2:'Fevereiro',3:'Março',4:'Abril',5:'Maio',6:'Junho',
                  7:'Julho',8:'Agosto',9:'Setembro',10:'Outubro',11:'Novembro',12:'Dezembro'}

month_year_options = [(f"{month_names_pt[d.month]} {d.year}", d) for d in sorted(df_summary['Data do Mês'].unique())]
month_year_strings = [opt[0] for opt in month_year_options]

st.markdown("---")
st.subheader("📅 Defina o intervalo de meses")

with st.expander("📅 Filtro de Período"):
    col1, col2 = st.columns(2)
    default_start_index = 0
    default_end_index = len(month_year_strings) - 1 if month_year_strings else 0

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
        df_filtered = df_summary[(df_summary['Data do Mês'] >= start_date) & (df_summary['Data do Mês'] <= end_date)].copy()
else:
    st.warning("Não foi possível determinar o período de filtro. Verifique os dados da planilha e os nomes das abas.")
    df_filtered = pd.DataFrame()

if df_filtered.empty:
    st.info("Não há dados para o período selecionado ou os dados filtrados resultaram em um DataFrame vazio.")
    st.stop()

# --- KPIs ---
st.markdown("---")
st.subheader("📈 Métricas de Resumo do Período")
col1, col2, col3, col4 = st.columns(4)

total_gastos = df_filtered['Total de Gastos'].sum()
total_salarios = df_filtered['Total de Salário'].sum()
economia_liquida = df_filtered['Economia'].sum()
media_gastos = df_filtered['Total de Gastos'].mean()

col1.metric("💰 Total de Gastos", f"R$ {format_currency_br(total_gastos)}")
col2.metric("💵 Total de Salário", f"R$ {format_currency_br(total_salarios)}")
col3.metric("📈 Economia Líquida", f"R$ {format_currency_br(economia_liquida)}")
col4.metric("📊 Média de Gastos Mensais", f"R$ {format_currency_br(media_gastos)}")

# --- Destaques ---
st.markdown("---")
st.markdown("### 🌟 Destaques Mensais")
if not df_filtered.empty:
    mes_maior_gasto = df_filtered.loc[df_filtered['Total de Gastos'].idxmax()]
    mes_menor_gasto = df_filtered.loc[df_filtered['Total de Gastos'].idxmin()]
    mes_maior_economia = df_filtered.loc[df_filtered['Economia'].idxmax()]
    mes_menor_economia = df_filtered.loc[df_filtered['Economia'].idxmin()]

    col1, col2 = st.columns(2)
    col1.error(f"📈 Maior Gasto: **{mes_maior_gasto['Mês']}** — R$ {format_currency_br(mes_maior_gasto['Total de Gastos'])}")
    col1.info(f"📉 Menor Gasto: **{mes_menor_gasto['Mês']}** — R$ {format_currency_br(mes_menor_gasto['Total de Gastos'])}")
    col2.success(f"⬆️ Maior Economia: **{mes_maior_economia['Mês']}** — R$ {format_currency_br(mes_maior_economia['Economia'])}")
    col2.warning(f"⬇️ Menor Economia: **{mes_menor_economia['Mês']}** — R$ {format_currency_br(mes_menor_economia['Economia'])}")
else:
    st.info("Não há dados suficientes no período selecionado para exibir os destaques mensais.")

# --- Gráficos ---
st.markdown("---")
st.subheader("📊 Gráficos de Análise Financeira")
tabs = st.tabs(["💼 Salário vs Gastos", "💸 Economia", "📉 Taxa de Economia", "📊 Gastos Mensais", "📈 Tendência"])

if not df_filtered.empty:
    with tabs[0]:
        fig = px.bar(
            df_filtered.melt(id_vars='Mês', value_vars=['Total de Salário', 'Total de Gastos'],
                            var_name='Tipo', value_name='Valor'),
            x='Mês', y='Valor', color='Tipo', barmode='group', text='Valor',
            labels={'Valor': 'Total (R$)', 'Tipo': 'Tipo de Valor'}
        )
        fig.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
        fig.update_layout(yaxis_tickprefix="R$ ")
        st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        fig = px.bar(df_filtered, x='Mês', y='Economia', text='Economia', color='Economia')
        fig.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
        fig.update_layout(yaxis_tickprefix="R$ ")
        st.plotly_chart(fig, use_container_width=True)

    with tabs[2]:
        fig = px.bar(df_filtered, x='Mês', y='Taxa de Economia (%)', text='Taxa de Economia (%)',
                    color='Taxa de Economia (%)', color_continuous_scale=px.colors.sequential.Blues)
        fig.update_traces(texttemplate='%{text:,.2f}%', textposition='outside')
        fig.update_layout(yaxis_ticksuffix="%")
        st.plotly_chart(fig, use_container_width=True)

    with tabs[3]:
        fig = px.bar(df_filtered, x='Mês', y='Total de Gastos', text='Total de Gastos',
                    color_discrete_sequence=px.colors.sequential.Blues_r)
        fig.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
        fig.update_layout(yaxis_tickprefix="R$ ")
        st.plotly_chart(fig, use_container_width=True)

    with tabs[4]:
        fig = px.line(df_filtered, x='Mês', y='Total de Gastos', markers=True)
        fig.update_traces(line_color='#607B8B', marker_color='#607B8B')
        fig.update_layout(yaxis_tickprefix="R$ ")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Não há dados no período selecionado para gerar os gráficos.")

# --- TABELA FINAL ---
st.markdown("---")
st.subheader("📋 Tabela de Resumo Mensal")
if not df_filtered.empty:
    st.dataframe(
        df_filtered[['Mês', 'Total de Salário', 'Total de Gastos', 'Economia', 'Taxa de Economia (%)']].style.format({
            'Total de Gastos': lambda x: f"R$ {format_currency_br(x)}",
            'Total de Salário': lambda x: f"R$ {format_currency_br(x)}",
            'Economia': lambda x: f"R$ {format_currency_br(x)}",
            'Taxa de Economia (%)': lambda x: f"{format_currency_br(x).replace('R$ ', '')}%"
        }),
        use_container_width=True
    )
else:
    st.info("Não há dados no período selecionado para exibir a tabela de resumo.")

st.markdown("---")
st.markdown("Dashboard financeiro.")
