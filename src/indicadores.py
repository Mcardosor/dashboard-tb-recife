"""
indicadores.py
──────────────
Indicadores epidemiológicos de TB seguindo a metodologia oficial (MS/OMS).
Regras críticas aplicadas:
  • Incidência: SÓ casos novos (Caso Novo + Não Sabe + Pós-óbito), anualizada.
  • Coorte (cura/abandono/óbito): denominador = casos ENCERRADOS.
  • Coinfecção HIV: denominador = testados (Positivo + Negativo).
  • Óbito por TB: SIM, CID A15–A19 (nunca o desfecho do SINAN).
Todos os números carregam fonte e denominador explícitos na camada de UI.
"""

import duckdb
import pandas as pd

from src import banco
from src.constantes import (
    POP_PARQUET, OBITOS_PARQUET, CODIGOS_CASO_NOVO, CODIGOS_RETRATAMENTO,
    SITUACOES_ENCERRADAS, SITUACAO_ENCERRAMENTO, HIV_TESTADOS, CID_TB_OBITO_PREFIXOS,
)


def _in_list(valores) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def pop_por_ano() -> pd.DataFrame:
    """População total de Recife por ano (de pop_recife.parquet)."""
    with duckdb.connect() as con:
        return con.execute(
            f"SELECT ano, SUM(populacao) AS pop FROM read_parquet('{POP_PARQUET.as_posix()}') "
            "GROUP BY ano ORDER BY ano"
        ).df()


def serie_incidencia() -> pd.DataFrame:
    """Incidência anual por 100 mil hab (casos novos / população do ano × 100k)."""
    casos = banco.query(f"""
        SELECT CAST(nu_ano AS INTEGER) AS ano, COUNT(*) AS casos_novos
        FROM tb WHERE tratamento IN ({_in_list(CODIGOS_CASO_NOVO)})
        GROUP BY 1
    """)
    pop = pop_por_ano()
    df = casos.merge(pop, on="ano", how="inner").sort_values("ano")
    df["incidencia"] = (df["casos_novos"] / df["pop"] * 100_000).round(1)
    return df


def _filtro_tipo(tipo: str | None) -> str:
    """Cláusula extra de tratamento (tipo de entrada): 'novo', 'retrat' ou None."""
    if tipo == "novo":
        return f"AND tratamento IN ({_in_list(CODIGOS_CASO_NOVO)})"
    if tipo == "retrat":
        return f"AND tratamento IN ({_in_list(CODIGOS_RETRATAMENTO)})"
    return ""


def coorte_desfecho(tipo: str | None = None):
    """Desfechos entre casos ENCERRADOS (coorte). tipo: 'novo' | 'retrat' | None (todos)."""
    df = banco.query(f"""
        SELECT CAST(CAST(situa_ence AS INTEGER) AS VARCHAR) AS cod, COUNT(*) AS n
        FROM tb
        WHERE situa_ence IS NOT NULL
          AND CAST(CAST(situa_ence AS INTEGER) AS VARCHAR) IN ({_in_list(SITUACOES_ENCERRADAS)})
          {_filtro_tipo(tipo)}
        GROUP BY 1
    """)
    df["desfecho"] = df["cod"].map(SITUACAO_ENCERRAMENTO)
    total = df["n"].sum()
    df["pct"] = (df["n"] / total * 100).round(1) if total else 0
    return df.sort_values("n", ascending=False), int(total)


def _taxa_cura(tipo: str | None) -> float:
    df, _ = coorte_desfecho(tipo)
    return float(df.loc[df["desfecho"] == "Cura", "pct"].sum())


def obitos_sim_por_ano() -> pd.DataFrame:
    """Óbitos por TB (SIM, A15–A19) por ano + coeficiente de mortalidade por 100 mil."""
    with duckdb.connect() as con:
        ob = con.execute(f"SELECT * FROM read_parquet('{OBITOS_PARQUET.as_posix()}')").df()
    pop = pop_por_ano()
    df = ob.merge(pop, on="ano", how="inner").sort_values("ano")
    df["mortalidade"] = (df["obitos"] / df["pop"] * 100_000).round(1)
    return df


def coinfeccao_hiv() -> dict:
    """% HIV+ entre testados + cobertura de testagem."""
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



# ── Tendência / sazonalidade / oportunidade ───────────────────────────────────
# No SINAN completo (recife_tb_sinan.parquet) as datas já vêm como DATE (ISO).
# Na base geolink vinham como VARCHAR 'DD/MM/AAAA'. _dt() lida com ambos via TRY_CAST.
def _dt(col: str) -> str:
    return f"TRY_CAST({col} AS DATE)"


def casos_por_tipo_entrada() -> pd.DataFrame:
    """Casos novos vs retratamento por ano (regra: não juntar — têm dinâmicas distintas)."""
    df = banco.query(f"""
        SELECT CAST(nu_ano AS INTEGER) AS ano,
               COUNT(*) FILTER (WHERE tratamento IN ({_in_list(CODIGOS_CASO_NOVO)}))      AS casos_novos,
               COUNT(*) FILTER (WHERE tratamento IN ('2', '3'))                           AS retratamento
        FROM tb GROUP BY 1 ORDER BY 1
    """)
    return df


def sazonalidade() -> pd.DataFrame:
    """Média de notificações por mês do ano (padrão sazonal)."""
    df = banco.query(f"""
        SELECT mes, COUNT(*) AS casos
        FROM (SELECT month({_dt('dt_notific')}) AS mes FROM tb) AS s
        WHERE mes IS NOT NULL GROUP BY mes ORDER BY mes
    """)
    n_anos = banco.query("SELECT COUNT(DISTINCT nu_ano) n FROM tb").iloc[0]["n"]
    df["media"] = (df["casos"] / n_anos).round(1)
    return df


def oportunidade() -> dict:
    """Mediana de dias diagnóstico→início e notificação→encerramento + % início ≤7 dias.
    Remove intervalos negativos (datas invertidas) e absurdos (regra #9)."""
    r = banco.query(f"""
        SELECT
            median(d_inicio) FILTER (WHERE d_inicio BETWEEN 0 AND 365)            AS med_inicio,
            median(d_enc)    FILTER (WHERE d_enc    BETWEEN 0 AND 730)            AS med_enc,
            100.0 * COUNT(*) FILTER (WHERE d_inicio BETWEEN 0 AND 7)
                  / NULLIF(COUNT(*) FILTER (WHERE d_inicio BETWEEN 0 AND 365), 0) AS pct_ate_7
        FROM (
            SELECT date_diff('day', {_dt('dt_diag')},    {_dt('dt_inic_tr')}) AS d_inicio,
                   date_diff('day', {_dt('dt_notific')}, {_dt('dt_encerra')})  AS d_enc
            FROM tb
        ) base
    """).iloc[0]
    return {
        "med_inicio": float(r.med_inicio) if r.med_inicio is not None else None,
        "med_enc": float(r.med_enc) if r.med_enc is not None else None,
        "pct_ate_7": round(float(r.pct_ate_7), 1) if r.pct_ate_7 is not None else None,
    }


# ── Bloco 5: Perfil epidemiológico ───────────────────────────────────────────

_ESCOLARIDADE_MAP = {
    "0": "Analfabeto", "1": "Fund. I incompleto", "2": "Fund. I completo",
    "3": "Fund. II incompleto", "4": "Fund. II completo",
    "5": "Médio incompleto", "6": "Médio completo",
    "7": "Superior incompleto", "8": "Superior completo",
    "9": "Ignorado", "10": "Não se aplica",
}


def perfil_sexo() -> pd.DataFrame:
    """Casos por sexo e ano (M/F/I)."""
    df = banco.query("""
        SELECT CAST(nu_ano AS INTEGER) AS ano,
               cs_sexo AS sexo,
               COUNT(*) AS casos
        FROM tb WHERE cs_sexo IN ('M', 'F')
        GROUP BY 1, 2 ORDER BY 1, 2
    """)
    return df


def perfil_raca() -> pd.DataFrame:
    """Distribuição por raça/cor (total, % sobre informados)."""
    df = banco.query("""
        SELECT cs_raca AS cod, COUNT(*) AS casos
        FROM tb WHERE cs_raca IS NOT NULL AND cs_raca NOT IN ('9', '')
        GROUP BY 1 ORDER BY 2 DESC
    """)
    from src.constantes import RACA_MAP
    df["raca"] = df["cod"].map(RACA_MAP).fillna("Ignorado")
    total = df["casos"].sum()
    df["pct"] = (df["casos"] / total * 100).round(1)
    return df


def perfil_faixa_etaria() -> pd.DataFrame:
    """Distribuição por faixa etária padrão MS/OMS."""
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
    ordem = ['< 5 anos','5–14 anos','15–24 anos','25–34 anos','35–44 anos',
             '45–54 anos','55–64 anos','65+ anos','Ignorado']
    df["faixa"] = pd.Categorical(df["faixa"], categories=ordem, ordered=True)
    df = df[df["faixa"] != "Ignorado"].sort_values("faixa")
    total = df["casos"].sum()
    df["pct"] = (df["casos"] / total * 100).round(1)
    return df


def pop_vulneravel() -> pd.DataFrame:
    """% de casos em cada população vulnerável (código 1 = Sim no SINAN)."""
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
    rotulos = {
        "privados_liberdade": "Privados de liberdade",
        "situacao_rua": "Situação de rua",
        "imigrantes": "Imigrantes",
        "profis_saude": "Profissionais de saúde",
        "benef_governo": "Beneficiários gov.",
    }
    rows = []
    total = int(df["total"])
    for col, label in rotulos.items():
        n = int(df[col])
        rows.append({"populacao": label, "casos": n,
                     "pct": round(n / total * 100, 1) if total else 0})
    return pd.DataFrame(rows).sort_values("casos", ascending=False)


def agravos() -> pd.DataFrame:
    """% de casos com cada agravo associado (código 1 = Sim no SINAN)."""
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
    rotulos = {
        "aids": "AIDS", "alcool": "Alcoolismo", "diabetes": "Diabetes",
        "drogas": "Uso de drogas", "tabaco": "Tabagismo",
    }
    rows = []
    total = int(df["total"])
    for col, label in rotulos.items():
        n = int(df[col])
        rows.append({"agravo": label, "casos": n,
                     "pct": round(n / total * 100, 1) if total else 0})
    return pd.DataFrame(rows).sort_values("casos", ascending=False)


# ── Bloco 5: Perfil clínico ───────────────────────────────────────────────────

def forma_clinica() -> pd.DataFrame:
    """Distribuição por forma clínica (casos novos e todos)."""
    from src.constantes import FORMA_MAP
    df = banco.query(f"""
        SELECT forma AS cod, COUNT(*) AS casos
        FROM tb WHERE forma IS NOT NULL AND forma IN ('1','2','3')
        GROUP BY 1 ORDER BY 2 DESC
    """)
    df["forma"] = df["cod"].map(FORMA_MAP)
    total = df["casos"].sum()
    df["pct"] = (df["casos"] / total * 100).round(1)
    return df


def hiv_por_ano() -> pd.DataFrame:
    """Cobertura de testagem HIV e % positividade por ano."""
    df = banco.query(f"""
        SELECT CAST(nu_ano AS INTEGER) AS ano,
               COUNT(*) AS total,
               COUNT(*) FILTER (WHERE hiv IN ({_in_list(HIV_TESTADOS)})) AS testados,
               COUNT(*) FILTER (WHERE hiv = '1') AS positivos
        FROM tb GROUP BY 1 ORDER BY 1
    """)
    df["cobertura"] = (df["testados"] / df["total"] * 100).round(1)
    df["positividade"] = (df["positivos"] / df["testados"].replace(0, pd.NA) * 100).round(1)
    return df


def coorte_por_tipo_ano() -> pd.DataFrame:
    """Taxa de cura por tipo de entrada por ano (tendência da coorte)."""
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


def abandono_por_ano() -> pd.DataFrame:
    """Taxa de abandono (abandono + abandono primário) entre encerrados, por ano."""
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


def casos_faixa_por_ano() -> pd.DataFrame:
    """Casos por faixa etária agrupada e ano (para tendência de distribuição etária)."""
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


def df_para_analise() -> "pd.DataFrame":
    """DataFrame com colunas decodificadas para uso no PyGWalker."""
    from src.constantes import TIPO_ENTRADA, SITUACAO_ENCERRAMENTO, HIV_MAP, SEXO_MAP, RACA_MAP, FORMA_MAP
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


def kpis_gerais() -> dict:
    """KPIs consolidados para a página de Visão Geral (período completo 2010–2023)."""
    inc = serie_incidencia()
    ult = inc.iloc[-1]   # último ano disponível (2023)

    coorte, encerrados = coorte_desfecho()
    pct = lambda nome: float(coorte.loc[coorte["desfecho"] == nome, "pct"].sum())

    mort = obitos_sim_por_ano()
    mort_ult = mort.iloc[-1]

    hiv = coinfeccao_hiv()
    return {
        "ano_ref": int(ult["ano"]),
        "incidencia_ult": float(ult["incidencia"]),
        "casos_novos_ult": int(ult["casos_novos"]),
        "taxa_cura_novo": _taxa_cura("novo"),
        "taxa_cura_retrat": _taxa_cura("retrat"),
        "taxa_abandono": pct("Abandono") + pct("Abandono Primário"),
        "encerrados": encerrados,
        "obitos_tb": int(mort["obitos"].sum()),
        "obitos_ult": int(mort_ult["obitos"]),
        "mortalidade_ult": float(mort_ult["mortalidade"]),
        "hiv_pct": hiv["pct_positivos"],
        "hiv_cobertura": hiv["cobertura"],
    }
