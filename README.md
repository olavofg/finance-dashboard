# 💸 Dashboard Financeiro

Dashboard interativo para controle de finanças pessoais, desenvolvido com Streamlit e integrado ao Google Sheets.

## 🚀 Como usar

1. **Clone o repositório**
   ```bash
   git clone <url-do-repositorio>
   cd dashboard
   ```

2. **Instale as dependências**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure as credenciais do Google Sheets**
   - Crie um arquivo `credentials.json` com as credenciais da API do Google Sheets
   - Configure a URL da planilha no arquivo `config.yaml`

4. **Execute o dashboard**
   ```bash
   streamlit run dashboard.py
   ```

## ⚙️ Configuração

### Google Sheets
- As abas devem ser nomeadas no formato: "Janeiro 2023", "Fevereiro 2024", etc.
- Célula **M27**: Total de gastos do mês
- Célula **B6**: Total de salário/receita do mês

### Autenticação (opcional)
Configure usuários e senhas no arquivo `config.yaml`

## 🌟 Funcionalidades

- 📊 **Métricas financeiras**: Total de gastos, receitas, economia e médias
- 📈 **Gráficos interativos**: Análise visual dos dados mensais
- 🎯 **Destaques**: Identifica melhores e piores períodos
- 📅 **Filtros de período**: Analise intervalos específicos
- � **Atualização em tempo real**: Dados sempre sincronizados com a planilha

## 📦 Estrutura do Projeto

```
├── dashboard.py              # Aplicação principal
├── streamlit_service.py      # Serviços auxiliares
├── config.yaml              # Configurações e credenciais
├── credentials.json         # Credenciais Google Sheets
└── requirements.txt         # Dependências Python
```

## 🔒 Segurança

- Credenciais protegidas em arquivos de configuração
- Autenticação opcional via senha
- Não armazene credenciais sensíveis no repositório público
