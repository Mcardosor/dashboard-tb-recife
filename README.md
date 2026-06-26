# Dashboard TB · Recife

Painel interativo de vigilância epidemiológica da tuberculose no município de Recife (PE), com dados do SINAN vinculados ao SIM e geocodificados por bairro e Distrito Sanitário.

> **Acesso:** http://164.41.147.175:8503/cenarios/tbrecife

---

## O que você encontra no painel

- **KPIs principais** — incidência, taxa de cura, abandono, coinfecção HIV e óbitos por TB
- **Epidemiologia** — incidência anual por 100 mil hab., sazonalidade, casos novos vs. retratamento
- **Perfil & Clínico** — sexo, raça/cor, forma clínica, desfecho por HIV
- **Mapa** — distribuição geográfica por bairro e Distrito Sanitário de Recife
- **Análise Livre** — exploração interativa com PyGWalker + download CSV

---

## Destaques técnicos

- **27.871 casos notificados** — período 2010–2023
- **99% geocodificados** — vinculação espacial ao SIM por bairro
- **Cobertura do SIM** — desfechos de óbito enriquecidos com dados de mortalidade (SIM)
- Botão **🌙/☀️** para alternar entre tema claro e escuro

---

## Stack

| Tecnologia | Uso |
|---|---|
| Python 3.11 + Streamlit | Interface e servidor |
| DuckDB | Queries colunares sobre Parquet |
| Plotly | Gráficos interativos |
| Folium + streamlit-folium | Mapa de bairros |
| PyGWalker | Análise drag-and-drop |

---

## Como rodar

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Rodar o dashboard
streamlit run app.py
```

---

## Estrutura do projeto

```
dashboard-tb-recife/
├── app.py                        ← entrada principal
├── requirements.txt
├── src/
│   ├── styles.py                 ← CSS e toggle dark/light
│   ├── sidebar.py                ← filtros e navegação
│   ├── dados.py                  ← carregamento e cache (DuckDB)
│   ├── graficos.py               ← visualizações Plotly
│   └── mapa.py                   ← mapa Folium por bairro
└── dados_dashboard/
    └── tb_recife_tratado.parquet
```

---

**Fonte dos dados:** SINAN NET + SIM — Secretaria de Saúde do Recife / Ministério da Saúde
**Cobertura:** notificações de tuberculose, Recife (PE), 2010–2023
**Última atualização:** junho/2026
