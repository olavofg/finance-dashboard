EXPENSES_CELL = 'M27'
INCOME_CELL = 'B6'

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

PERIOD_PRESETS = {
    'Tudo': None,
    'Últimos 12': 12,
    'Últimos 6': 6,
    'Ano atual': None,
}
