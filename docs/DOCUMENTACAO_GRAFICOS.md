# Documentação dos Gráficos — Dashboard TB Recife

> Painel de vigilância epidemiológica da tuberculose em Recife (PE) · 2010–2023  
> Fonte: SINAN-TB vinculado ao SIM, geocodificado por bairro e Distrito Sanitário.

---

## Sumário

- [Visão geral do projeto](#visão-geral-do-projeto)
- **KPIs (fixos no topo)**
  - [KPI — Incidência por 100 mil hab.](#kpi--incidência-por-100-mil-hab)
  - [KPI — Taxa de cura (casos novos e retratamento)](#kpi--taxa-de-cura-casos-novos-e-retratamento)
  - [KPI — Abandono](#kpi--abandono)
  - [KPI — Coinfecção HIV](#kpi--coinfecção-hiv)
  - [KPI — Óbitos por TB (SIM)](#kpi--óbitos-por-tb-sim)
- **Aba Epidemiologia**
  - [Incidência anual por 100 mil habitantes](#incidência-anual-por-100-mil-habitantes)
  - [Desfecho dos casos encerrados (coorte geral)](#desfecho-dos-casos-encerrados-coorte-geral)
  - [Casos novos vs. retratamento por ano](#casos-novos-vs-retratamento-por-ano)
  - [Sazonalidade — média de casos por mês](#sazonalidade--média-de-casos-por-mês)
  - [Evolução da taxa de abandono](#evolução-da-taxa-de-abandono)
  - [Casos por faixa etária ao longo dos anos](#casos-por-faixa-etária-ao-longo-dos-anos)
  - [KPIs de oportunidade terapêutica](#kpis-de-oportunidade-terapêutica)
- **Aba Perfil & Clínico**
  - [Distribuição por sexo e ano](#distribuição-por-sexo-e-ano)
  - [Distribuição por raça/cor](#distribuição-por-raçacor)
  - [Distribuição por faixa etária (perfil geral)](#distribuição-por-faixa-etária-perfil-geral)
  - [Populações vulneráveis](#populações-vulneráveis)
  - [Agravos associados](#agravos-associados)
  - [Forma clínica](#forma-clínica)
  - [Coinfecção HIV — cobertura e positividade por ano](#coinfecção-hiv--cobertura-e-positividade-por-ano)
  - [Taxa de cura por tipo de entrada (tendência)](#taxa-de-cura-por-tipo-de-entrada-tendência)
  - [Desfechos — casos novos (separado)](#desfechos--casos-novos-separado)
  - [Desfechos — retratamento (separado)](#desfechos--retratamento-separado)
- **Aba Mapa**
  - [Mapa choropleth por bairro](#mapa-choropleth-por-bairro)
  - [Mapa de calor (heatmap)](#mapa-de-calor-heatmap)
  - [Ranking: Top 15 bairros com mais casos](#ranking-top-15-bairros-com-mais-casos)
- **Aba Análise Livre**
  - [Exploração com PyGWalker](#exploração-com-pygwalker)

---

## Visão geral do projeto

### Fluxo de dados

```
SINAN-NET (Recife)          SIM (Recife)
      │                          │
      ▼                          ▼
recife_tb_sinan.parquet    obitos_sim_recife.parquet
(indicadores epidem.)      (óbitos CID A15–A19)
      │
      ├── recife_tb_geolink.parquet   (subconjunto geocodificado)
      │   (mapa: lat/lon, nm_bairro)
      │
      └── pop_recife.parquet           (IBGE — denominador da incidência)

Formato de armazenamento: Apache Parquet (colunar, comprimido)
Motor de consulta: DuckDB (SQL direto sobre os arquivos, sem banco persistente)
Interface: Streamlit (Python)
Gráficos interativos: Plotly
Mapas: Folium (renderizado como HTML estático com cache Streamlit)
Análise livre: PyGWalker (drag-and-drop sobre os microdados)
```

Os arquivos Parquet ficam em `dados_dashboard/`. O `banco.py` abre conexões DuckDB sob demanda (sem servidor), executa a query e retorna um `pandas.DataFrame`. O app carrega tudo uma vez em `carregar()` (decorado com `@st.cache_data`, TTL 1 hora) e distribui os DataFrames para cada função de gráfico.

### Stack e papel de cada peça

| Peça | Papel |
|---|---|
| `src/banco.py` | Abre DuckDB, expõe `query()` (tabela principal SINAN) e `query_geo()` (tabela geolink) |
| `src/indicadores.py` | Toda a matemática epidemiológica: incidência, coorte, HIV, abandono, sazonalidade, oportunidade |
| `src/graficos.py` | Transforma DataFrames em figuras Plotly; estilo único via `aplicar_layout()` |
| `src/mapa.py` | Constrói mapas Folium (choropleth e heatmap) a partir das coordenadas do geolink |
| `src/constantes.py` | Caminhos, paleta de cores, dicionários de decodificação dos códigos SINAN |
| `app.py` | Orquestra: chama indicadores, passa para graficos/mapa, renderiza com Streamlit |

### Por que essas escolhas técnicas

- **Parquet + DuckDB**: os microdados do SINAN chegam como tabela grande (≈ 28 mil linhas, dezenas de colunas). Parquet comprime bem e DuckDB lê só as colunas necessárias por query, sem precisar de um servidor de banco separado — ideal para deploy simples em servidor sem PostgreSQL.
- **Streamlit cache**: `@st.cache_data` guarda o resultado das queries durante 1 hora (TTL=3600 s). Isso evita re-leitura do Parquet a cada interação, mantendo o painel responsivo.
- **Folium renderizado como HTML**: mapas Folium são gerados uma vez e entregues como HTML estático ao `components.html()` do Streamlit, também cacheados com `@st.cache_data`.
- **Duas tabelas separadas (sinan × geolink)**: indicadores epidemiológicos usam o SINAN completo por residência (bate com o boletim oficial). Mapa usa o subconjunto geocodificado (geolink), que tem lat/lon e bairro mas pode ter menos casos que o total.

---

## KPI — Incidência por 100 mil hab.

**O que mostra:** coeficiente de incidência de tuberculose no último ano disponível (2023), acompanhado do número absoluto de casos novos.

**Por que existe:** a incidência por 100 mil habitantes é o indicador primário de controle da TB definido pela OMS e pelo Ministério da Saúde. Permite comparar anos e municípios independentemente do tamanho da população.

**Como é calculado:** numerador = casos novos do ano (tipo de entrada: Caso Novo + Não Sabe + Pós-óbito, códigos 1, 4 e 6 do campo `tratamento`); denominador = população total de Recife no ano (arquivo `pop_recife.parquet`, fonte IBGE). Fórmula: `(casos_novos / população) × 100.000`. O valor exibido no KPI refere-se ao último ano da série (`inc.iloc[-1]`).

<details>
<summary>▶ Ver código (src/indicadores.py → serie_incidencia / kpis_gerais)</summary>

~~~python
def serie_incidencia() -> pd.DataFrame:
    casos = banco.query(f"""
        SELECT CAST(nu_ano AS INTEGER) AS ano, COUNT(*) AS casos_novos
        FROM tb WHERE tratamento IN ({_in_list(CODIGOS_CASO_NOVO)})
        GROUP BY 1
    """)
    # CODIGOS_CASO_NOVO = ("1", "4", "6")
    pop = pop_por_ano()
    df = casos.merge(pop, on="ano", how="inner").sort_values("ano")
    df["incidencia"] = (df["casos_novos"] / df["pop"] * 100_000).round(1)
    return df

# Em kpis_gerais():
inc = serie_incidencia()
ult = inc.iloc[-1]   # último ano disponível (2023)
# → "incidencia_ult": float(ult["incidencia"])
# → "casos_novos_ult": int(ult["casos_novos"])
~~~
</details>

---

## KPI — Taxa de cura (casos novos e retratamento)

**O que mostra:** percentual de casos novos encerrados com desfecho "Cura" (valor principal) e, como subtítulo, o percentual equivalente entre os casos de retratamento.

**Por que existe:** a meta do Ministério da Saúde e da OMS é atingir ≥ 85% de cura. Separar casos novos de retratamentos é exigência metodológica: os dois grupos têm perfis distintos de resposta ao tratamento e são avaliados com denominadores diferentes.

**Como é calculado:** denominador = casos com situação de encerramento classificada como "encerrada" (códigos 1, 2, 3, 4, 7, 8, 9 e 10 do campo `situa_ence`); exclui casos em acompanhamento (nulo) e transferidos (desfecho desconhecido). Numerador = casos com `situa_ence = 1` (Cura). O percentual de cura é calculado separadamente para casos novos e para retratamentos via `_taxa_cura(tipo)`.

<details>
<summary>▶ Ver código (src/indicadores.py → coorte_desfecho / _taxa_cura)</summary>

~~~python
SITUACOES_ENCERRADAS = ("1", "2", "3", "4", "7", "8", "9", "10")

def coorte_desfecho(tipo: str | None = None):
    df = banco.query(f"""
        SELECT CAST(CAST(situa_ence AS INTEGER) AS VARCHAR) AS cod, COUNT(*) AS n
        FROM tb
        WHERE situa_ence IS NOT NULL
          AND CAST(CAST(situa_ence AS INTEGER) AS VARCHAR) IN ({_in_list(SITUACOES_ENCERRADAS)})
          {_filtro_tipo(tipo)}   -- filtra 'novo' ou 'retrat' se informado
        GROUP BY 1
    """)
    df["desfecho"] = df["cod"].map(SITUACAO_ENCERRAMENTO)
    total = df["n"].sum()
    df["pct"] = (df["n"] / total * 100).round(1) if total else 0
    return df.sort_values("n", ascending=False), int(total)

def _taxa_cura(tipo: str | None) -> float:
    df, _ = coorte_desfecho(tipo)
    return float(df.loc[df["desfecho"] == "Cura", "pct"].sum())
~~~
</details>

---

## KPI — Abandono

**O que mostra:** percentual de abandono entre os casos encerrados. Exibe alerta visual ("⚠ acima da meta (5%)") quando o valor ultrapassa a meta OMS.

**Por que existe:** abandonar o tratamento é a principal causa de TB resistente (TB-DR). A meta OMS é manter a taxa de abandono abaixo de 5%. Quando ultrapassada, indica necessidade de reforço no tratamento diretamente observado (TDO).

**Como é calculado:** soma dos percentuais de "Abandono" (código 2) e "Abandono Primário" (código 10) sobre o total de casos encerrados, calculada pela mesma função `coorte_desfecho()`. O campo `META_ABANDONO_OMS = 5.0` (definido em `constantes.py`) dispara o alerta.

<details>
<summary>▶ Ver código (src/indicadores.py → kpis_gerais / app.py)</summary>

~~~python
# Em kpis_gerais():
coorte, encerrados = coorte_desfecho()
pct = lambda nome: float(coorte.loc[coorte["desfecho"] == nome, "pct"].sum())
# ...
"taxa_abandono": pct("Abandono") + pct("Abandono Primário"),

# Em app.py:
META_ABANDONO_OMS = 5.0
abandono_alto = k["taxa_abandono"] > META_ABANDONO_OMS
~~~
</details>

---

## KPI — Coinfecção HIV

**O que mostra:** percentual de casos de TB com resultado HIV positivo entre os testados (positividade), e cobertura de testagem (proporção dos casos que realizaram o teste).

**Por que existe:** a coinfecção TB-HIV agrava o prognóstico e é monitorada separadamente. O denominador correto é o de testados (não o total de casos), pois comparar positivos sobre o total subestimaria a positividade real.

**Como é calculado:** numerador = casos com `hiv = '1'` (Positivo); denominador de positividade = testados (`hiv IN ('1','2')`, ou seja, Positivo + Negativo); denominador de cobertura = total de casos notificados. Fonte: campo `hiv` do SINAN-TB.

<details>
<summary>▶ Ver código (src/indicadores.py → coinfeccao_hiv)</summary>

~~~python
HIV_TESTADOS = ("1", "2")  # Positivo + Negativo

def coinfeccao_hiv() -> dict:
    r = banco.query(f"""
        SELECT
            COUNT(*)                                                   AS total,
            COUNT(*) FILTER (WHERE hiv IN ({_in_list(HIV_TESTADOS)}))  AS testados,
            COUNT(*) FILTER (WHERE hiv = '1')                          AS positivos
        FROM tb
    """).iloc[0]
    testados = int(r.testados)
    return {
        "positivos": int(r.positivos),
        "testados": testados,
        "pct_positivos": round(r.positivos / testados * 100, 1) if testados else 0.0,
        "cobertura": round(testados / r.total * 100, 1) if r.total else 0.0,
    }
~~~
</details>

---

## KPI — Óbitos por TB (SIM)

**O que mostra:** total de óbitos por tuberculose no período e coeficiente de mortalidade por 100 mil hab. no último ano.

**Por que existe:** o desfecho "Óbito por TB" do SINAN captura apenas os óbitos ocorridos durante o acompanhamento notificado. O SIM (Sistema de Informação sobre Mortalidade), com CID-10 A15–A19 como causa básica, é a fonte padrão para mortalidade por TB, pois inclui óbitos não notificados. Regra adotada no projeto: nunca usar o desfecho do SINAN como proxy de mortalidade.

**Como é calculado:** fonte = `obitos_sim_recife.parquet` (óbitos com CID A15, A16, A17, A18 ou A19). Coeficiente de mortalidade = `(óbitos / população) × 100.000`. O KPI soma todos os óbitos do período e exibe o coeficiente do último ano.

<details>
<summary>▶ Ver código (src/indicadores.py → obitos_sim_por_ano / kpis_gerais)</summary>

~~~python
CID_TB_OBITO_PREFIXOS = ("A15", "A16", "A17", "A18", "A19")
OBITOS_PARQUET = PASTA_DADOS / "obitos_sim_recife.parquet"

def obitos_sim_por_ano() -> pd.DataFrame:
    with duckdb.connect() as con:
        ob = con.execute(f"SELECT * FROM read_parquet('{OBITOS_PARQUET.as_posix()}')").df()
    pop = pop_por_ano()
    df = ob.merge(pop, on="ano", how="inner").sort_values("ano")
    df["mortalidade"] = (df["obitos"] / df["pop"] * 100_000).round(1)
    return df

# Em kpis_gerais():
mort = obitos_sim_por_ano()
mort_ult = mort.iloc[-1]
"obitos_tb": int(mort["obitos"].sum()),      # total do período
"mortalidade_ult": float(mort_ult["mortalidade"]),  # último ano
~~~
</details>

---

## Incidência anual por 100 mil habitantes

**O que mostra:** série temporal anual do coeficiente de incidência de TB em Recife, de 2010 a 2023, com valores anotados em cada ponto.

**Por que existe:** permite visualizar a tendência histórica — se o município está avançando no controle da TB ou se há piora. É o indicador de acompanhamento mais importante para vigilância epidemiológica.

**Como é calculado:** mesmo cálculo do KPI de incidência (ver acima), mas exibindo todos os anos da série, não apenas o último. Numerador: casos novos por ano (tipos de entrada 1, 4 e 6). Denominador: população IBGE de Recife no respectivo ano.

<details>
<summary>▶ Ver código (src/graficos.py → linha_incidencia)</summary>

~~~python
def linha_incidencia(df, x="ano", y="incidencia", titulo=None, altura=H_MEDIUM):
    fig = go.Figure(
        go.Scatter(
            x=df[x], y=df[y], mode="lines+markers+text",
            line=dict(color=COR_CURA, width=3, shape="spline"),
            fill="tozeroy", fillcolor="rgba(46,160,67,.10)",
            text=[f"{v:.0f}" for v in df[y]], textposition="top center",
            hovertemplate="<b>%{x}</b><br>%{y:.1f} / 100 mil hab<extra></extra>",
        )
    )
    fig.update_yaxes(title="por 100 mil hab", rangemode="tozero")
    return aplicar_layout(fig, altura=altura, titulo=titulo)
~~~
</details>

---

## Desfecho dos casos encerrados (coorte geral)

**O que mostra:** distribuição dos desfechos (Cura, Abandono, Óbito por TB, Óbito por outras causas, Falência, TB-DR etc.) entre todos os casos encerrados no período, em barras horizontais com o percentual sobre o total.

**Por que existe:** é o resultado final do tratamento — a "foto" de como a coorte de TB terminou. Permite avaliar se o município está próximo das metas de cura (≥ 85%) e abandono (< 5%), e quantificar os desfechos negativos.

**Como é calculado:** metodologia de coorte (MS/OMS). Denominador = casos com `situa_ence` classificada como encerrada (códigos 1, 2, 3, 4, 7, 8, 9 e 10). Excluem-se casos em acompanhamento (campo nulo) e transferidos (desfecho desconhecido no município). Cada desfecho recebe cor semântica: verde para cura, amarelo para abandono, vermelho para óbito etc.

<details>
<summary>▶ Ver código (src/graficos.py → barras_desfecho)</summary>

~~~python
def barras_desfecho(df, titulo=None, altura=H_MEDIUM):
    df = df.sort_values("n")
    cores = [tb_color_map([d])[d] for d in df["desfecho"]]
    fig = go.Figure(
        go.Bar(
            x=df["n"], y=df["desfecho"], orientation="h",
            marker=dict(color=cores, line=dict(width=0)),
            text=[f"{p:.1f}%" for p in df["pct"]],
            textposition="auto", insidetextanchor="end",
            customdata=df["n"],
            hovertemplate="<b>%{y}</b><br>%{customdata:,.0f} casos (%{text})<extra></extra>",
        )
    )
    return aplicar_layout(fig, altura=altura, titulo=titulo)
~~~
</details>

---

## Casos novos vs. retratamento por ano

**O que mostra:** barras agrupadas com, por ano, o total de casos novos (tipos 1, 4 e 6) ao lado do total de retratamentos (Recidiva + Reingresso após abandono, tipos 2 e 3).

**Por que existe:** casos novos e retratamentos têm dinâmicas distintas: o paciente em retratamento já falhou antes (por abandono ou recidiva) e tem menor taxa de cura, além de risco aumentado de TB resistente. Manter as séries separadas — e nunca somá-las para calcular incidência — é regra metodológica do MS e da OMS.

**Como é calculado:** query única com dois contadores condicionais por ano. Casos novos: `tratamento IN ('1','4','6')`; retratamento: `tratamento IN ('2','3')`.

<details>
<summary>▶ Ver código (src/indicadores.py → casos_por_tipo_entrada)</summary>

~~~python
def casos_por_tipo_entrada() -> pd.DataFrame:
    df = banco.query(f"""
        SELECT CAST(nu_ano AS INTEGER) AS ano,
               COUNT(*) FILTER (WHERE tratamento IN ({_in_list(CODIGOS_CASO_NOVO)}))   AS casos_novos,
               COUNT(*) FILTER (WHERE tratamento IN ('2', '3'))                        AS retratamento
        FROM tb GROUP BY 1 ORDER BY 1
    """)
    return df
~~~
</details>

---

## Sazonalidade — média de casos por mês

**O que mostra:** média de notificações de TB para cada mês do calendário (janeiro a dezembro), calculada sobre todos os anos disponíveis.

**Por que existe:** revela se há concentração de notificações em determinados meses — padrão relevante para planejar campanhas de busca ativa e alocar recursos.

**Como é calculado:** extrai o mês da data de notificação (`dt_notific`) via `month()` do DuckDB; conta o total histórico por mês; divide pelo número de anos distintos na base. Divisão: `casos_no_mês / n_anos`.

<details>
<summary>▶ Ver código (src/indicadores.py → sazonalidade)</summary>

~~~python
def sazonalidade() -> pd.DataFrame:
    df = banco.query(f"""
        SELECT mes, COUNT(*) AS casos
        FROM (SELECT month(TRY_CAST(dt_notific AS DATE)) AS mes FROM tb) AS s
        WHERE mes IS NOT NULL GROUP BY mes ORDER BY mes
    """)
    n_anos = banco.query("SELECT COUNT(DISTINCT nu_ano) n FROM tb").iloc[0]["n"]
    df["media"] = (df["casos"] / n_anos).round(1)
    return df
~~~
</details>

---

## Evolução da taxa de abandono

**O que mostra:** série temporal da taxa de abandono por ano (2010–2023), com linha horizontal de referência na meta OMS de 5%.

**Por que existe:** monitorar o abandono ano a ano permite identificar deterioração ou melhora da adesão ao tratamento. Taxas acima de 5% são alertas de risco de TB resistente.

**Como é calculado:** numerador = casos com `situa_ence IN ('2','10')` (Abandono + Abandono Primário); denominador = total de casos encerrados no ano. Taxa = `(abandonos / encerrados) × 100`.

<details>
<summary>▶ Ver código (src/indicadores.py → abandono_por_ano)</summary>

~~~python
SITUACOES_ENCERRADAS = ("1", "2", "3", "4", "7", "8", "9", "10")

def abandono_por_ano() -> pd.DataFrame:
    df = banco.query(f"""
        SELECT CAST(nu_ano AS INTEGER) AS ano,
               COUNT(*) FILTER (WHERE CAST(CAST(situa_ence AS INTEGER) AS VARCHAR)
                   IN ({_in_list(SITUACOES_ENCERRADAS)})) AS encerrados,
               COUNT(*) FILTER (WHERE CAST(CAST(situa_ence AS INTEGER) AS VARCHAR)
                   IN ('2', '10')) AS abandonos
        FROM tb GROUP BY 1 ORDER BY 1
    """)
    df["tx_abandono"] = (df["abandonos"] / df["encerrados"].replace(0, pd.NA) * 100).round(1)
    return df.dropna(subset=["tx_abandono"])
~~~
</details>

---

## Casos por faixa etária ao longo dos anos

**O que mostra:** barras empilhadas por ano, com cada faixa etária em uma cor diferente: < 15 anos, 15–34 anos, 35–54 anos, 55–64 anos e 65+ anos.

**Por que existe:** permite ver se a distribuição etária dos casos está mudando ao longo do tempo. O aumento na faixa 15–34 anos, por exemplo, reflete concentração da epidemia em adultos jovens.

**Como é calculado:** o campo `nu_idade_n` do SINAN usa um código numérico em que valores ≥ 4000 representam anos de vida (ex.: 4025 = 25 anos). Somente registros com `nu_idade_n >= 4000` são incluídos. As faixas são definidas por intervalos desse código. Não há denominador por faixa etária — trata-se de distribuição absoluta.

<details>
<summary>▶ Ver código (src/indicadores.py → casos_faixa_por_ano)</summary>

~~~python
def casos_faixa_por_ano() -> pd.DataFrame:
    df = banco.query("""
        SELECT CAST(nu_ano AS INTEGER) AS ano,
            CASE
                WHEN CAST(nu_idade_n AS INTEGER) < 4015 THEN '< 15 anos'
                WHEN CAST(nu_idade_n AS INTEGER) BETWEEN 4015 AND 4034 THEN '15–34 anos'
                WHEN CAST(nu_idade_n AS INTEGER) BETWEEN 4035 AND 4054 THEN '35–54 anos'
                WHEN CAST(nu_idade_n AS INTEGER) BETWEEN 4055 AND 4064 THEN '55–64 anos'
                WHEN CAST(nu_idade_n AS INTEGER) >= 4065 THEN '65+ anos'
            END AS faixa,
            COUNT(*) AS casos
        FROM tb
        WHERE nu_idade_n IS NOT NULL
          AND CAST(nu_idade_n AS INTEGER) >= 4000
        GROUP BY 1, 2 ORDER BY 1, 2
    """)
    return df.dropna(subset=["faixa"])
~~~
</details>

---

## KPIs de oportunidade terapêutica

Três indicadores exibidos como mini-KPIs na parte inferior da aba Epidemiologia:

### Diagnóstico → início do tratamento (mediana de dias)

**O que mostra:** mediana de dias entre a data do diagnóstico (`dt_diag`) e o início do tratamento (`dt_inic_tr`).

**Por que existe:** o ideal é iniciar o tratamento em até 7 dias após o diagnóstico. Atrasos prolongam o período de transmissão.

**Como é calculado:** `date_diff('day', dt_diag, dt_inic_tr)`. Filtro: somente intervalos entre 0 e 365 dias (remove datas invertidas e valores absurdos). Quando o SINAN registra início igual à data do diagnóstico, a mediana resulta em 0 dias — situação exibida com aviso específico no painel.

### Início em ≤ 7 dias (%)

**O que mostra:** percentual de casos com início do tratamento em até 7 dias do diagnóstico.

**Por que existe:** é a métrica de oportunidade de tratamento recomendada pelo MS. Quanto maior, melhor a agilidade da rede de atenção.

**Como é calculado:** `100 × COUNT(*) FILTER (WHERE d_inicio BETWEEN 0 AND 7) / COUNT(*) FILTER (WHERE d_inicio BETWEEN 0 AND 365)`.

### Notificação → encerramento (mediana de dias)

**O que mostra:** mediana de dias entre a data de notificação (`dt_notific`) e a data de encerramento (`dt_encerra`).

**Por que existe:** o esquema básico de TB dura aproximadamente 180 dias. Uma mediana muito abaixo pode indicar encerramento precoce (abandono ou óbito); muito acima pode sinalizar casos sem encerramento registrado.

**Como é calculado:** `date_diff('day', dt_notific, dt_encerra)`. Filtro: 0 a 730 dias (remove negativos e valores impossíveis).

<details>
<summary>▶ Ver código (src/indicadores.py → oportunidade)</summary>

~~~python
def oportunidade() -> dict:
    r = banco.query(f"""
        SELECT
            median(d_inicio) FILTER (WHERE d_inicio BETWEEN 0 AND 365)            AS med_inicio,
            median(d_enc)    FILTER (WHERE d_enc    BETWEEN 0 AND 730)            AS med_enc,
            100.0 * COUNT(*) FILTER (WHERE d_inicio BETWEEN 0 AND 7)
                  / NULLIF(COUNT(*) FILTER (WHERE d_inicio BETWEEN 0 AND 365), 0) AS pct_ate_7
        FROM (
            SELECT date_diff('day', TRY_CAST(dt_diag AS DATE),    TRY_CAST(dt_inic_tr AS DATE)) AS d_inicio,
                   date_diff('day', TRY_CAST(dt_notific AS DATE), TRY_CAST(dt_encerra AS DATE))  AS d_enc
            FROM tb
        ) base
    """).iloc[0]
    return {
        "med_inicio": float(r.med_inicio) if r.med_inicio is not None else None,
        "med_enc":    float(r.med_enc)    if r.med_enc    is not None else None,
        "pct_ate_7":  round(float(r.pct_ate_7), 1) if r.pct_ate_7 is not None else None,
    }
~~~
</details>

---

## Distribuição por sexo e ano

**O que mostra:** barras agrupadas (Masculino / Feminino) por ano, mostrando a contagem de casos de cada sexo.

**Por que existe:** a TB afeta desproporcionalmente o sexo masculino. Monitorar essa distribuição ao longo do tempo permite identificar mudanças no perfil epidemiológico e direcionar ações para grupos específicos.

**Como é calculado:** campo `cs_sexo` do SINAN, filtrado para 'M' e 'F' (exclui sexo ignorado para não distorcer a proporção).

<details>
<summary>▶ Ver código (src/indicadores.py → perfil_sexo)</summary>

~~~python
def perfil_sexo() -> pd.DataFrame:
    df = banco.query("""
        SELECT CAST(nu_ano AS INTEGER) AS ano,
               cs_sexo AS sexo,
               COUNT(*) AS casos
        FROM tb WHERE cs_sexo IN ('M', 'F')
        GROUP BY 1, 2 ORDER BY 1, 2
    """)
    return df
~~~
</details>

---

## Distribuição por raça/cor

**O que mostra:** barras horizontais com o percentual de casos por raça/cor (Parda, Preta, Branca, Amarela, Indígena).

**Por que existe:** desigualdades raciais na carga de TB são documentadas no Brasil. O monitoramento permite evidenciar grupos mais afetados e orientar políticas de equidade em saúde.

**Como é calculado:** campo `cs_raca` do SINAN, decodificado pelo dicionário `RACA_MAP`. Excluem-se registros com raça ignorada (`cs_raca IN ('9','')`) para que o percentual reflita apenas os casos com informação. Denominador = total de casos com raça informada.

<details>
<summary>▶ Ver código (src/indicadores.py → perfil_raca)</summary>

~~~python
RACA_MAP = {"1": "Branca", "2": "Preta", "3": "Amarela", "4": "Parda",
            "5": "Indígena", "9": "Ignorado"}

def perfil_raca() -> pd.DataFrame:
    df = banco.query("""
        SELECT cs_raca AS cod, COUNT(*) AS casos
        FROM tb WHERE cs_raca IS NOT NULL AND cs_raca NOT IN ('9', '')
        GROUP BY 1 ORDER BY 2 DESC
    """)
    df["raca"] = df["cod"].map(RACA_MAP).fillna("Ignorado")
    total = df["casos"].sum()
    df["pct"] = (df["casos"] / total * 100).round(1)
    return df
~~~
</details>

---

## Distribuição por faixa etária (perfil geral)

**O que mostra:** barras horizontais com o percentual de casos por faixa etária padrão MS/OMS: < 5, 5–14, 15–24, 25–34, 35–44, 45–54, 55–64 e 65+ anos.

**Por que existe:** a estrutura etária dos casos indica onde a doença está concentrada e orienta triagem em faixas prioritárias (ex.: envelhecimento da epidemia ou concentração em jovens).

**Como é calculado:** o campo `nu_idade_n` usa código SINAN: valores ≥ 4000 indicam idade em anos (4015 = 15 anos, 4065 = 65 anos). Registros com `nu_idade_n` nulo ou fora do padrão de anos são excluídos. Faixa "Ignorado" também é removida da exibição. Denominador = total de casos com faixa identificada.

<details>
<summary>▶ Ver código (src/indicadores.py → perfil_faixa_etaria)</summary>

~~~python
def perfil_faixa_etaria() -> pd.DataFrame:
    df = banco.query("""
        SELECT
            CASE
                WHEN CAST(nu_idade_n AS INTEGER) < 4005 THEN '< 5 anos'
                WHEN CAST(nu_idade_n AS INTEGER) BETWEEN 4005 AND 4014 THEN '5–14 anos'
                WHEN CAST(nu_idade_n AS INTEGER) BETWEEN 4015 AND 4024 THEN '15–24 anos'
                WHEN CAST(nu_idade_n AS INTEGER) BETWEEN 4025 AND 4034 THEN '25–34 anos'
                WHEN CAST(nu_idade_n AS INTEGER) BETWEEN 4035 AND 4044 THEN '35–44 anos'
                WHEN CAST(nu_idade_n AS INTEGER) BETWEEN 4045 AND 4054 THEN '45–54 anos'
                WHEN CAST(nu_idade_n AS INTEGER) BETWEEN 4055 AND 4064 THEN '55–64 anos'
                WHEN CAST(nu_idade_n AS INTEGER) >= 4065 THEN '65+ anos'
                ELSE 'Ignorado'
            END AS faixa,
            COUNT(*) AS casos
        FROM tb WHERE nu_idade_n IS NOT NULL
        GROUP BY 1
    """)
    # ...ordena por faixa etária e exclui "Ignorado"
    total = df["casos"].sum()
    df["pct"] = (df["casos"] / total * 100).round(1)
    return df
~~~
</details>

---

## Populações vulneráveis

**O que mostra:** barras horizontais com o percentual de casos pertencentes a cada população vulnerável: privados de liberdade, situação de rua, imigrantes, profissionais de saúde e beneficiários de programas de governo.

**Por que existe:** essas populações têm risco muito elevado de TB e acesso dificultado aos serviços de saúde. Quantificá-las é requisito da vigilância epidemiológica e orienta estratégias específicas (ex.: busca ativa em presídios).

**Como é calculado:** campos `pop_liber`, `pop_rua`, `pop_imig`, `pop_saude` e `benef_gov` do SINAN (código `'1'` = Sim). Denominador = total de casos notificados. Um mesmo caso pode pertencer a mais de uma categoria (contagens não são mutuamente exclusivas).

<details>
<summary>▶ Ver código (src/indicadores.py → pop_vulneravel)</summary>

~~~python
def pop_vulneravel() -> pd.DataFrame:
    df = banco.query("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE pop_liber = '1') AS privados_liberdade,
            COUNT(*) FILTER (WHERE pop_rua   = '1') AS situacao_rua,
            COUNT(*) FILTER (WHERE pop_imig  = '1') AS imigrantes,
            COUNT(*) FILTER (WHERE pop_saude = '1') AS profis_saude,
            COUNT(*) FILTER (WHERE benef_gov = '1') AS benef_governo
        FROM tb
    """).iloc[0]
    # ...converte para DataFrame com rótulos descritivos
    total = int(df["total"])
    for col, label in rotulos.items():
        n = int(df[col])
        rows.append({"populacao": label, "casos": n,
                     "pct": round(n / total * 100, 1) if total else 0})
~~~
</details>

---

## Agravos associados

**O que mostra:** barras horizontais com o percentual de casos que apresentam cada agravo associado: AIDS, Alcoolismo, Tabagismo, Uso de drogas e Diabetes.

**Por que existe:** agravos associados aumentam o risco de TB ativa e de desfecho negativo. A AIDS é o principal fator de risco individual. Esses dados orientam o manejo clínico e a busca ativa de contatos.

**Como é calculado:** campos `agravaids`, `agravalcoo`, `agravdiabe`, `agravdroga` e `agravtabac` do SINAN (código `'1'` = Sim). Denominador = total de casos notificados. Um caso pode ter mais de um agravo simultaneamente.

<details>
<summary>▶ Ver código (src/indicadores.py → agravos)</summary>

~~~python
def agravos() -> pd.DataFrame:
    df = banco.query("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE agravaids  = '1') AS aids,
            COUNT(*) FILTER (WHERE agravalcoo = '1') AS alcool,
            COUNT(*) FILTER (WHERE agravdiabe = '1') AS diabetes,
            COUNT(*) FILTER (WHERE agravdroga = '1') AS drogas,
            COUNT(*) FILTER (WHERE agravtabac = '1') AS tabaco
        FROM tb
    """).iloc[0]
    total = int(df["total"])
    for col, label in rotulos.items():
        n = int(df[col])
        rows.append({"agravo": label, "casos": n,
                     "pct": round(n / total * 100, 1) if total else 0})
~~~
</details>

---

## Forma clínica

**O que mostra:** barras horizontais com o percentual de casos por forma clínica: Pulmonar, Extrapulmonar e Pulmonar + Extrapulmonar.

**Por que existe:** a forma pulmonar é a mais frequente e a única que transmite a doença. A extrapulmonar indica disseminação, mais comum em imunossuprimidos (ex.: coinfectados HIV). A proporção entre formas auxilia na avaliação do perfil clínico da epidemia local.

**Como é calculado:** campo `forma` do SINAN, filtrado para os códigos válidos (`'1'`, `'2'`, `'3'`). Denominador = total de casos com forma informada (exclui nulos e ignorados).

<details>
<summary>▶ Ver código (src/indicadores.py → forma_clinica)</summary>

~~~python
FORMA_MAP = {"1": "Pulmonar", "2": "Extrapulmonar", "3": "Pulmonar + Extrapulmonar"}

def forma_clinica() -> pd.DataFrame:
    df = banco.query(f"""
        SELECT forma AS cod, COUNT(*) AS casos
        FROM tb WHERE forma IS NOT NULL AND forma IN ('1','2','3')
        GROUP BY 1 ORDER BY 2 DESC
    """)
    df["forma"] = df["cod"].map(FORMA_MAP)
    total = df["casos"].sum()
    df["pct"] = (df["casos"] / total * 100).round(1)
    return df
~~~
</details>

---

## Coinfecção HIV — cobertura e positividade por ano

**O que mostra:** duas linhas sobrepostas num eixo Y único de 0–100%: (1) cobertura de testagem (% de casos que fizeram o teste HIV) e (2) positividade (% de HIV+ entre os testados), por ano.

**Por que existe:** monitorar as duas séries juntas permite ver se a cobertura de testagem está crescendo (meta de testar todos os casos de TB) e se a positividade está caindo (impacto dos antirretrovirais). A decisão de usar eixo único — e não dois eixos — foi deliberada: escalas distintas distorceriam a comparação visual entre as duas métricas.

**Como é calculado:** por ano: `cobertura = testados / total × 100`; `positividade = positivos / testados × 100`. Casos com `hiv IN ('1','2')` são os testados; `hiv = '1'` são os positivos.

<details>
<summary>▶ Ver código (src/indicadores.py → hiv_por_ano)</summary>

~~~python
HIV_TESTADOS = ("1", "2")  # Positivo + Negativo

def hiv_por_ano() -> pd.DataFrame:
    df = banco.query(f"""
        SELECT CAST(nu_ano AS INTEGER) AS ano,
               COUNT(*) AS total,
               COUNT(*) FILTER (WHERE hiv IN ({_in_list(HIV_TESTADOS)})) AS testados,
               COUNT(*) FILTER (WHERE hiv = '1') AS positivos
        FROM tb GROUP BY 1 ORDER BY 1
    """)
    df["cobertura"]    = (df["testados"] / df["total"] * 100).round(1)
    df["positividade"] = (df["positivos"] / df["testados"].replace(0, pd.NA) * 100).round(1)
    return df
~~~
</details>

---

## Taxa de cura por tipo de entrada (tendência)

**O que mostra:** duas linhas — "Casos novos" e "Retratamento" — com a taxa anual de cura de cada grupo, acompanhadas de linha de referência pontilhada na meta OMS de 85%.

**Por que existe:** a taxa de cura de casos novos e de retratamentos precisa ser acompanhada separadamente porque os denominadores e os perfis de risco são distintos. Analisar a tendência ao longo dos anos revela se o tratamento está melhorando ou deteriorando.

**Como é calculado:** por ano e por tipo: `tx_cura = curas / encerrados × 100`. Curas = `situa_ence = '1'`; encerrados = `situa_ence IN (lista de situações encerradas)`. Anos sem encerrados suficientes são descartados (`dropna`).

<details>
<summary>▶ Ver código (src/indicadores.py → coorte_por_tipo_ano)</summary>

~~~python
def coorte_por_tipo_ano() -> pd.DataFrame:
    df = banco.query(f"""
        SELECT CAST(nu_ano AS INTEGER) AS ano,
               CASE
                   WHEN tratamento IN ({_in_list(CODIGOS_CASO_NOVO)}) THEN 'Casos novos'
                   WHEN tratamento IN ({_in_list(CODIGOS_RETRATAMENTO)}) THEN 'Retratamento'
               END AS tipo,
               COUNT(*) FILTER (WHERE CAST(CAST(situa_ence AS INTEGER) AS VARCHAR)
                   IN ({_in_list(SITUACOES_ENCERRADAS)})) AS encerrados,
               COUNT(*) FILTER (WHERE CAST(CAST(situa_ence AS INTEGER) AS VARCHAR) = '1') AS curas
        FROM tb
        WHERE tratamento IN ({_in_list(CODIGOS_CASO_NOVO + CODIGOS_RETRATAMENTO)})
        GROUP BY 1, 2 ORDER BY 1, 2
    """)
    df["tx_cura"] = (df["curas"] / df["encerrados"].replace(0, pd.NA) * 100).round(1)
    return df.dropna(subset=["tx_cura"])
~~~
</details>

---

## Desfechos — casos novos (separado)

**O que mostra:** o mesmo gráfico de barras horizontais de desfechos da coorte geral (função `barras_desfecho`), aplicado exclusivamente aos casos novos.

**Por que existe:** isolar os casos novos do retratamento é requisito metodológico. A taxa de cura oficial do MS é calculada sobre a coorte de casos novos; misturar os dois grupos distorce o indicador.

**Como é calculado:** `coorte_desfecho(tipo="novo")` — filtra `tratamento IN ('1','4','6')` antes de contar os desfechos.

<details>
<summary>▶ Ver código (src/indicadores.py → coorte_desfecho)</summary>

~~~python
def _filtro_tipo(tipo: str | None) -> str:
    if tipo == "novo":
        return f"AND tratamento IN ({_in_list(CODIGOS_CASO_NOVO)})"  # ('1','4','6')
    if tipo == "retrat":
        return f"AND tratamento IN ({_in_list(CODIGOS_RETRATAMENTO)})"  # ('2','3')
    return ""

# Chamada em app.py:
"coorte_novo": indicadores.coorte_desfecho(tipo="novo"),
~~~
</details>

---

## Desfechos — retratamento (separado)

**O que mostra:** o mesmo gráfico de barras horizontais de desfechos, aplicado exclusivamente aos casos de retratamento (Recidiva + Reingresso após abandono).

**Por que existe:** retratamentos têm taxa de cura estruturalmente menor e perfil de desfecho diferente (mais abandonos, mais falências). Exibir separadamente deixa evidente a diferença de resultado entre os dois grupos.

**Como é calculado:** `coorte_desfecho(tipo="retrat")` — filtra `tratamento IN ('2','3')`.

<details>
<summary>▶ Ver código (src/indicadores.py → coorte_desfecho)</summary>

~~~python
# Chamada em app.py:
"coorte_retrat": indicadores.coorte_desfecho(tipo="retrat"),
# Filtro interno: AND tratamento IN ('2', '3')
~~~
</details>

---

## Mapa choropleth por bairro

**O que mostra:** mapa de Recife com os 94 bairros coloridos por escala de calor proporcional ao número absoluto de casos de TB notificados no período 2010–2023. Ao passar o cursor sobre um bairro, exibe o nome e o total de casos.

**Por que existe:** permite identificar visualmente quais bairros concentram mais casos e orientar ações de busca ativa e vigilância geográfica.

**Como é calculado:** contagem de casos por bairro a partir da base geolink (`recife_tb_geolink.parquet`, campo `nm_bairro`). O nome do bairro é normalizado (sem acento, maiúsculo) para fazer a junção com o GeoJSON oficial dos bairros (`bairros_recife.geojson`). A escala de cor vai de amarelo claro (poucos casos) a vermelho escuro (muitos casos).

**Nota:** somente casos geocodificados com coordenadas dentro da bounding box de Recife são utilizados no mapa. O total exibido pode ser ligeiramente inferior ao total de notificações.

<details>
<summary>▶ Ver código (src/mapa.py → choropleth_bairro)</summary>

~~~python
def choropleth_bairro() -> folium.Map:
    m = _base()
    g = _geojson_bairros()  # carrega bairros_recife.geojson com nome normalizado

    df = banco.query_geo("SELECT nm_bairro, COUNT(*) AS casos FROM tb WHERE nm_bairro IS NOT NULL GROUP BY nm_bairro")
    df["_nome"] = df["nm_bairro"].map(norm)
    casos = df.groupby("_nome")["casos"].sum().to_dict()

    vmax = max(casos.values())
    escala = cm.LinearColormap(
        ["#FFFFCC", "#FED976", "#FEB24C", "#FD8D3C", "#FC4E2A", "#E31A1C", "#B10026"],
        vmin=0, vmax=vmax, caption="Casos de TB (2010–2023)",
    )
    # ...aplica estilo e tooltip por bairro
~~~
</details>

---

## Mapa de calor (heatmap)

**O que mostra:** camada de densidade sobre o mapa de Recife, onde manchas mais quentes (vermelho/laranja) indicam maior concentração geográfica de casos geocodificados.

**Por que existe:** o heatmap revela aglomerados de casos em nível sub-bairro, identificando áreas de concentração que o choropleth de bairro pode mascarar (ex.: rua ou quadra específica dentro de um bairro).

**Como é calculado:** usa as coordenadas individuais (`latitude`, `longitude`) de cada caso geocodificado, após filtrar coordenadas fora da bounding box de Recife. A camada `HeatMap` do Folium aplica um kernel gaussiano com `radius=11` e `blur=15`.

<details>
<summary>▶ Ver código (src/mapa.py → mapa_calor)</summary>

~~~python
RECIFE_BBOX = {"lat_min": -8.18, "lat_max": -7.93, "lon_min": -35.02, "lon_max": -34.82}

def pontos() -> pd.DataFrame:
    return banco.query_geo(
        f"SELECT latitude, longitude FROM tb WHERE latitude IS NOT NULL AND {_filtro_bbox()}"
    )

def mapa_calor() -> folium.Map:
    m = _base()
    dados = pontos()[["latitude", "longitude"]].values.tolist()
    HeatMap(dados, radius=11, blur=15, min_opacity=0.25,
            gradient={0.2: "#ffffb2", 0.45: "#fd8d3c", 0.7: "#e31a1c", 1.0: "#7f0000"}).add_to(m)
    return m
~~~
</details>

---

## Ranking: Top 15 bairros com mais casos

**O que mostra:** barras horizontais com os 15 bairros de Recife com maior número absoluto de casos notificados, ordenados do maior para o menor, com escala de cor proporcional ao número de casos.

**Por que existe:** complementa o mapa choropleth com uma lista explícita, útil em apresentações para identificar rapidamente os bairros prioritários para ações de vigilância.

**Como é calculado:** `por_bairro().head(15)` — agrega casos por bairro na base geolink, ordena decrescente e pega os 15 primeiros. A função gráfica ordena ascendente (menor embaixo, maior em cima) para leitura natural do gráfico horizontal.

<details>
<summary>▶ Ver código (src/mapa.py → por_bairro / src/graficos.py → barras_bairros)</summary>

~~~python
# src/mapa.py
def por_bairro() -> pd.DataFrame:
    return banco.query_geo(f"""
        SELECT nm_bairro AS bairro, COUNT(*) AS casos,
               AVG(latitude) AS lat, AVG(longitude) AS lon
        FROM tb
        WHERE nm_bairro IS NOT NULL AND nm_bairro <> 'BAIRRO IGNORADO' AND {_filtro_bbox()}
        GROUP BY nm_bairro ORDER BY casos DESC
    """)

# src/graficos.py
def barras_bairros(df, titulo="Top 15 Bairros — Casos de TB", altura=680):
    df = df.sort_values("casos", ascending=True)
    fig = go.Figure(
        go.Bar(
            x=df["casos"], y=df["bairro"].str.title(),
            orientation="h",
            marker=dict(
                color=df["casos"],
                colorscale=[[0, "#FED976"], [0.5, "#FC4E2A"], [1, "#B10026"]],
            ),
            text=df["casos"].astype(int), textposition="outside",
        )
    )
~~~
</details>

---

## Exploração com PyGWalker

**O que mostra:** interface de exploração visual drag-and-drop sobre os microdados do SINAN-TB de Recife (2010–2023), com colunas decodificadas para linguagem legível.

**Por que existe:** permite análises ad hoc sem programação — o usuário arrasta campos para os eixos X/Y, aplica filtros e muda o tipo de gráfico diretamente na interface. Serve para hipóteses não previstas nos gráficos fixos do painel.

**Colunas decodificadas disponíveis:** `tipo_entrada`, `desfecho`, `resultado_hiv`, `sexo`, `raca_cor`, `forma_clinica`, `ano`.

**Como é calculado:** a função `df_para_analise()` carrega todos os registros da tabela principal e substitui os códigos crus do SINAN por rótulos descritivos, usando os dicionários de `constantes.py`. O resultado é entregue ao `StreamlitRenderer` do PyGWalker.

<details>
<summary>▶ Ver código (src/indicadores.py → df_para_analise)</summary>

~~~python
def df_para_analise() -> pd.DataFrame:
    df = banco.query_all_cols("SELECT * FROM tb")
    df["tipo_entrada"]  = df["tratamento"].astype(str).map(TIPO_ENTRADA)
    df["desfecho"]      = df["situa_ence"].apply(
        lambda x: SITUACAO_ENCERRAMENTO.get(str(int(float(x))), None) if pd.notna(x) else None
    )
    df["resultado_hiv"] = df["hiv"].astype(str).map(HIV_MAP)
    df["sexo"]          = df["cs_sexo"].map(SEXO_MAP)
    df["raca_cor"]      = df["cs_raca"].astype(str).map(RACA_MAP)
    df["forma_clinica"] = df["forma"].astype(str).map(FORMA_MAP)
    df["ano"]           = pd.to_numeric(df["nu_ano"], errors="coerce").astype("Int64")
    return df
~~~
</details>

---

*Documento gerado a partir da leitura direta dos arquivos `app.py`, `src/graficos.py`, `src/indicadores.py`, `src/mapa.py` e `src/constantes.py`.*
