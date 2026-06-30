"""
constantes.py
─────────────
Caminhos, paletas e config global do dashboard TB Recife.
SEM imports de streamlit/pandas — módulo leve, importável sem efeitos pesados.

Fonte de dados: dados_geolink.Recife_PE_geolink_TB (SINAN+SIM linkado, geocodificado),
exportada por scripts/exportar_recife.py. Colunas em minúsculas (ver export).
"""

from pathlib import Path

# ── Caminhos ────────────────────────────────────────────────────────────────
PASTA_DADOS    = Path("dados_dashboard")
# Indicadores (incidência, casos, coorte, HIV) → SINAN completo por residência
# (bate com o boletim epidemiológico). Mapa/geografia → subconjunto geocodificado.
PARQUET        = PASTA_DADOS / "recife_tb_sinan.parquet"
GEOLINK_PARQUET = PASTA_DADOS / "recife_tb_geolink.parquet"
POP_PARQUET    = PASTA_DADOS / "pop_recife.parquet"
OBITOS_PARQUET = PASTA_DADOS / "obitos_sim_recife.parquet"
GEOJSON_BAIRRO = PASTA_DADOS / "bairros_recife.geojson"          # Bloco 5 (a buscar)
GEOJSON_DS     = PASTA_DADOS / "distritos_sanitarios.geojson"    # Bloco 5 (a buscar)

# ── Recorte temporal (a base vai de 2010 a 2023) ──────────────────────────────
ANO_INICIO = 2010
ANO_FIM    = 2023

# ── Recife ────────────────────────────────────────────────────────────────────
COD_MUNICIPIO_RECIFE = "261160"   # IBGE 6 díg. (no SIM aparece tb como 2611606)
# Bounding box aproximada do município (p/ filtrar coords outliers do geocode).
RECIFE_BBOX = {"lat_min": -8.18, "lat_max": -7.93, "lon_min": -35.02, "lon_max": -34.82}
RECIFE_CENTRO = (-8.05, -34.90)

# ── Óbito por TB: CID-10 A15–A19 (regra: usar SIM, nunca desfecho do SINAN) ────
CID_TB_OBITO_PREFIXOS = ("A15", "A16", "A17", "A18", "A19")

# ══════════════════════════════════════════════════════════════════════════════
# Decodificação dos códigos CRUS do SINAN-TB (a base geolink é bronze, não tratada).
# Valores conferidos direto na tabela antes de mapear (regra: nunca filtrar às cegas).
# ══════════════════════════════════════════════════════════════════════════════

# tratamento = TIPO DE ENTRADA
TIPO_ENTRADA = {
    "1": "Caso Novo", "2": "Recidiva", "3": "Reingresso após Abandono",
    "4": "Não Sabe", "5": "Transferência", "6": "Pós-óbito",
}
# Incidência usa SÓ casos novos: Caso Novo + Não Sabe + Pós-óbito (exclui retratamento).
CODIGOS_CASO_NOVO = ("1", "4", "6")
CODIGOS_RETRATAMENTO = ("2", "3")   # Recidiva + Reingresso após abandono

# situa_ence = SITUAÇÃO DE ENCERRAMENTO (vem como float: '1.0', '2.0'...)
SITUACAO_ENCERRAMENTO = {
    "1": "Cura", "2": "Abandono", "3": "Óbito por TB", "4": "Óbito por outras causas",
    "5": "Transferência", "6": "Mudança de Diagnóstico", "7": "TB-DR",
    "8": "Mudança de Esquema", "9": "Falência", "10": "Abandono Primário",
}
# Coorte (taxa de cura/abandono/óbito): denominador = ENCERRADOS.
# Exclui não-encerrados (em acompanhamento = nulo) e transferidos (desfecho desconhecido).
SITUACOES_ENCERRADAS = ("1", "2", "3", "4", "7", "8", "9", "10")

# hiv = RESULTADO SOROLOGIA HIV
HIV_MAP = {"1": "Positivo", "2": "Negativo", "3": "Em andamento", "4": "Não realizado"}
HIV_TESTADOS = ("1", "2")   # denominador da coinfecção = testados

# forma clínica
FORMA_MAP = {"1": "Pulmonar", "2": "Extrapulmonar", "3": "Pulmonar + Extrapulmonar"}

# sexo / raça
SEXO_MAP = {"M": "Masculino", "F": "Feminino", "I": "Ignorado"}
RACA_MAP = {"1": "Branca", "2": "Preta", "3": "Amarela", "4": "Parda",
            "5": "Indígena", "9": "Ignorado"}
POP_SEXO_MAP = {"1": "Masculino", "2": "Feminino"}  # pop_ibge

META_ABANDONO_OMS = 5.0  # % — acima disso é alerta (risco de TB resistente)

# ── Paleta semântica (estilo GitHub dark) ─────────────────────────────────────
COR_CURA      = "#2ea043"
COR_OBITO     = "#da3633"
COR_ABANDONO  = "#d29922"
COR_NEUTRO    = "#8b949e"
COR_HIV       = "#da3633"
COR_MASC      = "#58a6ff"
COR_FEM       = "#f778ba"

TB_COLORS = {
    "Cura": COR_CURA, "Óbito por TB": COR_OBITO, "Obito por TB": COR_OBITO,
    "Abandono": COR_ABANDONO, "Abandono Primário": "#bb8009", "Abandono Primario": "#bb8009",
    "Falência": "#f85149", "Falencia": "#f85149", "Transferência": "#1f6feb",
    "Transferencia": "#1f6feb", "Mudança de Esquema": "#ffa657", "Em acompanhamento": "#388bfd",
    "Masculino": COR_MASC, "Feminino": COR_FEM,
    "Positivo": COR_OBITO, "Negativo": COR_CURA, "Ignorado": COR_ABANDONO,
    "Pulmonar": "#58a6ff", "Extrapulmonar": "#a371f7", "Pulmonar + Extrapulmonar": "#d2a8ff",
    "Caso Novo": "#3fb950", "Recidiva": "#d29922", "Reingresso Abandono": "#f0883e",
}
CORES = ["#58a6ff", "#a371f7", "#3fb950", "#d29922", "#f778ba", "#79c0ff", "#d2a8ff"]


def tb_color_map(labels: list[str]) -> dict:
    """Mapeia labels → cores TB, com fallback determinístico."""
    mapping, i = {}, 0
    for lbl in labels:
        if lbl in TB_COLORS:
            mapping[lbl] = TB_COLORS[lbl]
        else:
            mapping[lbl] = CORES[i % len(CORES)]
            i += 1
    return mapping


# ── Template Plotly único e centralizado ──────────────────────────────────────
PLOTLY_TEMPLATE = {
    "layout": {
        "font": {"family": "Inter, -apple-system, system-ui, sans-serif",
                 "color": "#444d56", "size": 12},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "title": {"font": {"size": 15, "color": "#1a3a5c"},
                  "x": 0.02, "xanchor": "left"},
        "xaxis": {"gridcolor": "#e1e4e8", "linecolor": "#d0d7de",
                  "tickfont": {"color": "#57606a", "size": 11}},
        "yaxis": {"gridcolor": "#e1e4e8", "linecolor": "#d0d7de",
                  "tickfont": {"color": "#57606a", "size": 11}},
        "legend": {"bgcolor": "rgba(255,255,255,0.85)", "bordercolor": "#d0d7de",
                   "borderwidth": 1, "font": {"color": "#444d56", "size": 11}},
        "hoverlabel": {"bgcolor": "#ffffff", "bordercolor": "#d0d7de",
                       "font": {"color": "#24292f"}},
        "margin": {"l": 50, "r": 30, "t": 50, "b": 50},
    }
}
PLOTLY_CFG = {"displayModeBar": False, "scrollZoom": False}

H_SMALL, H_MEDIUM, H_LARGE = 300, 380, 480


# ── Colunas do SINAN cru usadas nos indicadores (performance: SELECT só estas) ─
# Base recife_tb_sinan.parquet (98 cols). NÃO tem geografia intra-municipal nem SIM.
COLUNAS_DASHBOARD = (
    # identificação / tempo
    "nu_ano", "tp_not", "dt_notific", "dt_diag", "dt_inic_tr", "dt_encerra",
    "id_mn_resi",
    # demografia
    "cs_sexo", "cs_raca", "cs_escol_n", "nu_idade_n", "cs_gestant",
    # tipo de entrada / forma clínica
    "tratamento", "forma", "extrapu1_n",
    # desfecho (coorte)
    "situa_ence",
    # HIV / coinfecção
    "hiv", "ant_retro",
    # exames
    "bacilosc_e", "cultura_es", "test_molec", "test_sensi",
    "raiox_tora", "teste_tube", "histopatol",
    # tratamento supervisionado
    "trat_super",
    # populações vulneráveis
    "pop_liber", "pop_rua", "pop_imig", "pop_saude", "benef_gov",
    # agravos
    "agravaids", "agravalcoo", "agravdiabe", "agravdroga", "agravtabac",
)

# ── Colunas da base geolink usadas SÓ no mapa (geografia + coordenadas) ────────
COLUNAS_GEO = (
    "nu_ano", "nm_bairro", "id_distrit", "latitude", "longitude", "georreferenciado",
)
