# Dashboard TB · Recife

Painel de vigilância epidemiológica da tuberculose no município de Recife (PE). Dados do SINAN vinculados ao SIM, geocodificados por bairro e Distrito Sanitário.

Acesso: https://painel.cenarios.unb.br/cenarios/tbrecife

## Documentação

| Documento | Descrição |
|---|---|
| [Arquitetura](docs/ARQUITETURA.md) | Fluxo de dados ponta a ponta, módulos, deploy e limitações — comece por aqui |
| [Documentação dos Gráficos](docs/DOCUMENTACAO_GRAFICOS.md) | Por que cada gráfico existe, como é calculado e o código |

## Conteúdo

- KPIs: incidência, taxa de cura, abandono, coinfecção HIV, óbitos por TB
- Epidemiologia: incidência anual por 100 mil hab., sazonalidade, casos novos vs. retratamento
- Perfil & clínico: sexo, raça/cor, forma clínica, desfecho por HIV
- Mapa: distribuição por bairro e Distrito Sanitário
- Análise livre: Apache Superset embutido via iframe e download em CSV

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
| Apache Superset | Análise drag-and-drop (embutido via iframe) |

## Como rodar

```bash
pip install -r requirements.lock.txt
streamlit run app.py
```

## Dependências

| Arquivo | Papel |
|---|---|
| `requirements.txt` | **Intenção** — faixas de versão que o código suporta |
| `requirements.lock.txt` | **Realidade** — as 48 versões exatas; é daqui que o Dockerfile instala |

As faixas antigas eram largas demais (`pyarrow>=14.0`, `plotly>=5.20`,
`duckdb>=0.10`) e a produção já tinha atravessado **plotly 5 → 6** e
**pyarrow 14 → 25** sem que isso fosse decidido nem registrado.

> **Este lock não descreve a VM — descreve o código.**
>
> Nos outros painéis da família o lock é uma fotografia do container em
> execução, e travar as versões é um no-op no deploy. Aqui não: a VM ainda
> roda a versão com PyGWalker e o código já é a versão Superset.
>
> O lock foi montado em duas etapas para minimizar a diferença: resolveu-se o
> `requirements.txt` novo para obter a **lista** (48 pacotes, contra 89), e
> para cada sobrevivente usou-se a **versão que a VM já roda**. O próximo
> deploy então remove os 41 pacotes da árvore do PyGWalker (ipython,
> jupyter-widgets, wasmtime, sqlglot, pydantic…) e não mexe em mais nada.
> Resolver do zero teria trazido GitPython, pytz, streamlit-folium e tornado
> mais novos de brinde — subida de versão que ninguém pediu.

Uma curiosidade que sobrevive à migração: este painel roda **numpy 1.26.4**
enquanto os outros da família estão em 2.x. Era de se esperar que o teto viesse
do `pygwalker`, mas mesmo sem ele a resolução continua em 1.26.4 — quem segura
é o `streamlit==1.35.0`, que é bem anterior aos demais painéis.

Para regenerar, depois de mexer no `requirements.txt`:

```bash
docker run --rm -v "$PWD:/w" -w /w python:3.11-slim \
  sh -c "pip install -q -r requirements.txt && pip freeze" > requirements.lock.txt
```

Resolva **dentro do `python:3.11-slim`**, não no Python da sua máquina: a
resolução muda conforme a versão do interpretador, e o que vale é a da imagem.

## O que o CI cobre

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) roda a cada push e PR:
`ruff check .`, o build da imagem, e um diff entre o `pip freeze` da imagem e o
lock.

**Este painel não tem testes.** O CI pega import quebrado, erro de sintaxe e
lock que parou de instalar — não pega taxa de incidência calculada errada.
Conferir número continua sendo trabalho de abrir o painel.

## Estrutura

```
dashboard-tb-recife/
├── app.py                        # entrada principal
├── requirements.txt
├── src/
│   ├── styles.py                 # CSS e toggle dark/light
│   ├── banco.py                  # engine DuckDB sobre o Parquet local
│   ├── indicadores.py            # cálculos epidemiológicos
│   ├── constantes.py             # caminhos, colunas usadas, paletas
│   ├── graficos.py               # visualizações Plotly
│   └── mapa.py                   # mapa Folium por bairro
└── dados_dashboard/
    ├── recife_tb_geolink.parquet     # base principal (SINAN x SIM, geocodificada)
    ├── recife_tb_sinan.parquet
    ├── obitos_sim_recife.parquet
    ├── pop_recife.parquet
    └── bairros_recife.geojson
```

Fonte: SINAN NET + SIM (Secretaria de Saúde do Recife / Ministério da Saúde). Cobertura: Recife (PE), 2010–2023. Última atualização: junho/2026.
