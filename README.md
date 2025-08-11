# Finance Dashboard - Streamlit Community Edition

Uma dashboard de finanças pessoais construída com Streamlit, agora pronta para ser publicada gratuitamente no [Streamlit Community Cloud](https://streamlit.io/cloud), usando dados do Google Sheets.

## 🚀 Início Rápido

1. **Configure seu Google Sheets** - Prepare sua planilha conforme instruções abaixo
2. **Configure as credenciais** - Adicione `credentials.json` e configure variáveis de ambiente se necessário
3. **Execute localmente** - Rode `streamlit run dashboard.py`
4. **Publique grátis** - Faça deploy no [Streamlit Community Cloud](https://streamlit.io/cloud)

## 📁 Estrutura do Projeto

```
├── dashboard.py              # Aplicação principal Streamlit
├── streamlit_service.py      # Serviços auxiliares para Streamlit
├── requirements.txt          # Dependências Python
├── Dockerfile                # (Opcional) Configuração Docker
├── config.yaml               # Configuração do app
├── credentials.json          # Credenciais Google Sheets
└── README.md                 # Este arquivo
```

## 🔧 Configuração

O app utiliza as seguintes configurações:
- `credentials.json`: Credenciais da API do Google Sheets
- `sheet_url`: URL da sua planilha Google Sheets
- Variáveis de ambiente opcionais para produção

## 🌟 Funcionalidades

- **Login Simples**: Autenticação opcional via senha
- **Dados em Tempo Real**: Atualização ao vivo do Google Sheets
- **Gráficos Interativos**: Análise financeira mensal com Plotly
- **Design Responsivo**: Funciona em desktop e mobile
- **Deploy Grátis**: Pronto para o Streamlit Community Cloud

## 📊 Seções do Dashboard

1. **KPIs**: Gastos, receitas, saldo, médias
2. **Destaques Mensais**: Melhores e piores meses
3. **Gráficos**: Várias abas de visualização
4. **Tabela de Dados**: Detalhamento mensal
5. **Filtro de Período**: Analise intervalos específicos

## 🔒 Segurança

- Autenticação opcional via streamlit_authenticator
- Credenciais protegidas por variáveis de ambiente
- Não armazene credenciais sensíveis no repositório

## 💰 Custo

O deploy no Streamlit Community Cloud é gratuito para projetos pessoais e de pequeno porte.

## 📝 Notas

- Requer Google Sheets com células específicas (M27 para despesas, B6 para receitas)
- As abas da planilha devem ser nomeadas como "Janeiro 2023", "Fevereiro 2024", etc.
- Os dados são cacheados por 1 hora para otimizar performance
