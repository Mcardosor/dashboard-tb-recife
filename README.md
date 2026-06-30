# Dashboard TB · Recife

Painel de vigilância epidemiológica da tuberculose no município de Recife (PE). Dados do SINAN vinculados ao SIM, geocodificados por bairro e Distrito Sanitário.

Acesso: http://164.41.147.175:8503/cenarios/tbrecife

## Conteúdo

- KPIs: incidência, taxa de cura, abandono, coinfecção HIV, óbitos por TB
- Epidemiologia: incidência anual por 100 mil hab., sazonalidade, casos novos vs. retratamento
- Perfil & clínico: sexo, raça/cor, forma clínica, desfecho por HIV
- Mapa: distribuição por bairro e Distrito Sanitário
- Análise livre: exploração com PyGWalker e download em CSV

## Notas técnicas

- 27.871 casos notificados, período 2010–2023
- 99% dos casos geocodificados, vinculação espacial ao SIM por bairro
- Desfechos de óbito enriquecidos com dados de mortalidade do SIM
- Alternância de tema claro/escuro no canto superior

## Stack

| Tecnologia | Uso |
|---|---|
| Python 3.11 + Streamlit | Interface e servidor |
| DuckDB | Queries sobre Parquet |
| Plotly | Gráficos |
| Folium + streamlit-folium | Mapa por bairro |
| PyGWalker | Análise drag-and-drop |

## Como rodar

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Estrutura

```
dashboard-tb-recife/
├── app.py                        # entrada principal
├── requirements.txt
├── src/
│   ├── styles.py                 # CSS e toggle dark/light
│   ├── sidebar.py                # filtros e navegação
│   ├── dados.py                  # carregamento e cache (DuckDB)
│   ├── graficos.py               # visualizações Plotly
│   └── mapa.py                   # mapa Folium por bairro
└── dados_dashboard/
    └── tb_recife_tratado.parquet
```

Fonte: SINAN NET + SIM (Secretaria de Saúde do Recife / Ministério da Saúde). Cobertura: Recife (PE), 2010–2023. Última atualização: junho/2026.
