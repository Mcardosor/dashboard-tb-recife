"""
app.py — Dashboard TB Recife
════════════════════════════
Hero + KPIs epidemiológicos fixos no topo; abas para os recortes.
Blocos 3-5: Visão Geral, Geográfico, Tendência, Perfil, Clínico, Análise Livre.

Rodar local:  python -m streamlit run app.py   ->  http://localhost:8501
"""

import streamlit as st
import streamlit.components.v1 as components

from src import banco, styles, graficos, indicadores, mapa
from src.constantes import (
    ANO_INICIO, ANO_FIM, PLOTLY_CFG, META_ABANDONO_OMS,
    COR_CURA, COR_OBITO, COR_ABANDONO, COR_HIV, COR_MASC, COR_NEUTRO,
)

st.set_page_config(page_title="Dashboard TB | Recife", page_icon="🩺", layout="wide")
styles.inject_css()
styles.navbar()

fmt = lambda n: f"{int(n):,}".replace(",", ".")

with st.sidebar:
    st.caption("**Dashboard TB · Recife**")
    if st.button("🔄 Limpar cache", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()


@st.cache_data(show_spinner="Calculando indicadores…", ttl=3600)
def carregar():
    resumo = banco.query("SELECT COUNT(*) AS total FROM tb").iloc[0]
    geo = banco.query_geo(
        "SELECT ROUND(100.0 * AVG((georreferenciado = 1)::INT), 1) AS pct_geo FROM tb"
    ).iloc[0]
    return {
        "total": int(resumo.total), "pct_geo": float(geo.pct_geo),
        "kpis": indicadores.kpis_gerais(),
        "inc": indicadores.serie_incidencia(),
        "coorte": indicadores.coorte_desfecho(),
        "tipo_entrada": indicadores.casos_por_tipo_entrada(),
        "sazonalidade": indicadores.sazonalidade(),
        "oportunidade": indicadores.oportunidade(),
        "abandono_ano": indicadores.abandono_por_ano(),
        "sexo": indicadores.perfil_sexo(),
        "raca": indicadores.perfil_raca(),
        "faixa": indicadores.perfil_faixa_etaria(),
        "faixa_ano": indicadores.casos_faixa_por_ano(),
        "vulneravel": indicadores.pop_vulneravel(),
        "agravos": indicadores.agravos(),
        "forma": indicadores.forma_clinica(),
        "hiv_ano": indicadores.hiv_por_ano(),
        "coorte_tipo_ano": indicadores.coorte_por_tipo_ano(),
        "coorte_novo": indicadores.coorte_desfecho(tipo="novo"),
        "coorte_retrat": indicadores.coorte_desfecho(tipo="retrat"),
    }


@st.cache_data(show_spinner="Renderizando mapa…")
def mapa_html(modo: str) -> str:
    """HTML do mapa Folium (cacheado — renderiza uma vez por modo)."""
    builder = {
        "Choropleth": mapa.choropleth_bairro,
        "Mapa de calor": mapa.mapa_calor,
    }[modo]
    return builder()._repr_html_()



# ── Warmup: pré-aquece cache na inicialização ──────────────────────────────
@st.cache_resource(show_spinner=False)
def _iniciar_warmup():
    """Roda uma vez por processo — pré-carrega indicadores e mapa em background."""
    import threading
    def _bg():
        try:
            carregar()
            mapa_html('Choropleth')
        except Exception:
            pass
    threading.Thread(target=_bg, daemon=True).start()
    return True
_iniciar_warmup()
# ───────────────────────────────────────────────────────────────────────────

try:
    d = carregar()
    k = d["kpis"]
except Exception as _e:
    st.error(f"Erro ao carregar dados: {_e}")
    st.info("Verifique se os arquivos Parquet estão em `dados_dashboard/` e reinicie.")
    st.stop()

# ── Hero ──────────────────────────────────────────────────────────────────────
styles.hero(
    titulo="Tuberculose · Recife",
    subtitulo=(
        "Tuberculose no município de Recife (PE) por bairro e Distrito Sanitário · "
        "SINAN vinculado ao SIM e geocodificado."
    ),
    badges=[
        (f"{ANO_INICIO}–{ANO_FIM}", "accent"),
        (f"{fmt(d['total'])} casos notificados", ""),
        ("Fonte: SINAN + SIM", ""),
        (f"{d['pct_geo']}% georreferenciado", "success"),
    ],
)

# ── KPIs epidemiológicos (fixos) ──────────────────────────────────────────────
abandono_alto = k["taxa_abandono"] > META_ABANDONO_OMS
styles.kpi_row([
    {"label": f"Incidência {k['ano_ref']}", "value": f"{k['incidencia_ult']:.0f}",
     "sub": f"/100 mil · {fmt(k['casos_novos_ult'])} novos", "icon": "📈", "accent": COR_MASC},
    {"label": "Cura (casos novos)", "value": f"{k['taxa_cura_novo']:.1f}%",
     "sub": f"retrat. {k['taxa_cura_retrat']:.0f}%", "icon": "✅", "accent": COR_CURA},
    {"label": "Abandono", "value": f"{k['taxa_abandono']:.1f}%",
     "sub": ("⚠ acima da meta (5%)" if abandono_alto else "dentro da meta"),
     "icon": "⚠️", "accent": COR_ABANDONO, "alert": abandono_alto},
    {"label": "Coinfecção HIV", "value": f"{k['hiv_pct']:.1f}%",
     "sub": f"testados · cob. {k['hiv_cobertura']:.0f}%", "icon": "🧬", "accent": COR_HIV},
    {"label": "Óbitos por TB (SIM)", "value": fmt(k["obitos_tb"]),
     "sub": f"{k['mortalidade_ult']:.1f}/100 mil em {k['ano_ref']}", "icon": "⚰️", "accent": COR_OBITO},
])

st.divider()


# ── Abas ──────────────────────────────────────────────────────────────────────
tab_geo, tab_epi, tab_perfil, tab_livre = st.tabs([
    "🗺️  Mapa", "📊  Epidemiologia", "👤  Perfil & Clínico", "🔬  Análise Livre",
])


# ── Epidemiologia ─────────────────────────────────────────────────────────────
with tab_epi:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Incidência por 100 mil habitantes", help=(
            "**Fonte:** SINAN-TB  \n"
            "**Numerador:** casos novos (Caso Novo + Não Sabe + Pós-óbito)  \n"
            "**Denominador:** população IBGE de Recife no ano  \n"
            "**Cálculo:** coeficiente anual por 100 mil hab."))
        st.plotly_chart(graficos.linha_incidencia(d["inc"]),
                        width="stretch", config=PLOTLY_CFG)
    with c2:
        coorte_df, encerrados = d["coorte"]
        st.subheader("Desfecho dos casos encerrados", help=(
            "**Fonte:** SINAN-TB (situação de encerramento)  \n"
            f"**Denominador:** {fmt(encerrados)} casos encerrados  \n"
            "**Exclui:** em acompanhamento e transferidos  \n"
            "**Metodologia:** coorte (MS/OMS)."))
        st.plotly_chart(graficos.barras_desfecho(coorte_df),
                        width="stretch", config=PLOTLY_CFG)

    st.divider()
    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Casos novos vs. retratamento por ano", help=(
            "**Fonte:** SINAN-TB (tipo de entrada)  \n"
            "**Casos novos:** Caso Novo + Não Sabe + Pós-óbito  \n"
            "**Retratamento:** Recidiva + Reingresso após abandono  \n"
            "*Mantidos separados: têm dinâmicas e taxas de cura distintas.*"))
        st.plotly_chart(graficos.barras_novos_retratamento(d["tipo_entrada"]),
                        width="stretch", config=PLOTLY_CFG)
    with c4:
        st.subheader("Sazonalidade — média de casos por mês", help=(
            "**Fonte:** SINAN-TB (data de notificação)  \n"
            "**Cálculo:** total de cada mês ÷ nº de anos (2010–2023)."))
        st.plotly_chart(graficos.barras_sazonalidade(d["sazonalidade"]),
                        width="stretch", config=PLOTLY_CFG)

    st.divider()
    c5, c6 = st.columns(2)
    with c5:
        st.subheader("Evolução da taxa de abandono", help=(
            "**Fonte:** SINAN-TB (situação de encerramento)  \n"
            "**Numerador:** Abandono (cód 2) + Abandono Primário (cód 10)  \n"
            "**Denominador:** casos encerrados no ano  \n"
            "**Meta OMS:** < 5% — acima disso indica risco de TB resistente."))
        st.plotly_chart(graficos.linha_abandono(d["abandono_ano"]),
                        width="stretch", config=PLOTLY_CFG)
    with c6:
        st.subheader("Casos por faixa etária ao longo dos anos", help=(
            "**Fonte:** SINAN-TB (nu_idade_n)  \n"
            "**Nota:** mostra distribuição absoluta — sem denominador por faixa etária.  \n"
            "O aumento recente em 15–34 anos reflete a epidemia concentrada em adultos jovens."))
        st.plotly_chart(graficos.barras_faixa_por_ano(d["faixa_ano"]),
                        width="stretch", config=PLOTLY_CFG)

    st.divider()
    op = d["oportunidade"]
    med_inicio = op["med_inicio"]
    inicio_valor = f"{med_inicio:.0f} dias" if med_inicio and med_inicio > 0 else "0 dias"
    inicio_sub = (
        "SINAN registra início = data do diagnóstico"
        if not med_inicio or med_inicio == 0
        else "mediana · ideal ≤ 7 dias"
    )
    styles.kpi_row([
        {"label": "Diagnóstico → início trat.", "value": inicio_valor,
         "sub": inicio_sub, "icon": "⏱️", "accent": COR_CURA},
        {"label": "Início em ≤ 7 dias", "value": f"{op['pct_ate_7']:.0f}%",
         "sub": "oportunidade do tratamento", "icon": "🎯", "accent": COR_MASC},
        {"label": "Notificação → encerramento", "value": f"{op['med_enc']:.0f} dias",
         "sub": "mediana · esquema básico ≈ 180", "icon": "📅", "accent": "#a371f7"},
    ])


# ── Perfil & Clínico ──────────────────────────────────────────────────────────
with tab_perfil:
    # — Perfil sociodemográfico —
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Distribuição por sexo e ano", help=(
            "**Fonte:** SINAN-TB (cs_sexo)  \n"
            "**Exclui:** sexo ignorado para não distorcer a proporção."))
        st.plotly_chart(graficos.barras_sexo_ano(d["sexo"]),
                        width="stretch", config=PLOTLY_CFG)
    with c2:
        st.subheader("Distribuição por raça/cor", help=(
            "**Fonte:** SINAN-TB (cs_raca)  \n"
            "**Denominador:** casos com raça informada (exclui ignorado)."))
        st.plotly_chart(
            graficos.barras_h_pct(d["raca"], col_label="raca", col_pct="pct", col_n="casos",
                                  cor_unica=COR_MASC),
            width="stretch", config=PLOTLY_CFG,
        )

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Distribuição por faixa etária", help=(
            "**Fonte:** SINAN-TB (nu_idade_n · código SINAN 4XXX = anos)  \n"
            "**Grupos:** padrão MS/OMS para TB."))
        st.plotly_chart(graficos.barras_faixa_etaria(d["faixa"]),
                        width="stretch", config=PLOTLY_CFG)
    with c4:
        st.subheader("Populações vulneráveis", help=(
            "**Fonte:** SINAN-TB (pop_liber, pop_rua, pop_imig, pop_saude, benef_gov)  \n"
            "**Denominador:** total de casos notificados (2010–2023).  \n"
            "**Nota:** um caso pode pertencer a mais de uma categoria."))
        st.plotly_chart(
            graficos.barras_h_pct(d["vulneravel"], col_label="populacao",
                                  col_pct="pct", col_n="casos", cor_unica=COR_ABANDONO),
            width="stretch", config=PLOTLY_CFG,
        )

    _mapa_cores_agravos = {
        "AIDS": COR_OBITO, "Alcoolismo": COR_ABANDONO, "Tabagismo": "#8b949e",
        "Uso de drogas": "#a371f7", "Diabetes": COR_MASC,
    }
    _cores_agravos_lista = [_mapa_cores_agravos.get(r, COR_NEUTRO)
                             for r in d["agravos"]["agravo"]]
    st.subheader("Agravos associados", help=(
        "**Fonte:** SINAN-TB (agravaids, agravalcoo, agravdiabe, agravdroga, agravtabac)  \n"
        "**Denominador:** total de casos.  \n"
        "**Nota:** um caso pode ter mais de um agravo."))
    st.plotly_chart(
        graficos.barras_h_pct(
            d["agravos"], col_label="agravo", col_pct="pct", col_n="casos",
            altura=260, cores=_cores_agravos_lista,
        ),
        width="stretch", config=PLOTLY_CFG,
    )

    st.divider()

    # — Perfil clínico —
    c5, c6 = st.columns([1, 2])
    with c5:
        st.subheader("Forma clínica", help=(
            "**Fonte:** SINAN-TB (forma)  \n"
            "**Denominador:** casos com forma informada."))
        st.plotly_chart(graficos.pizza_forma(d["forma"]),
                        width="stretch", config=PLOTLY_CFG)
    with c6:
        st.subheader("Coinfecção HIV — cobertura e positividade por ano", help=(
            "**Fonte:** SINAN-TB (hiv)  \n"
            "**Positividade:** HIV+ ÷ testados (Positivo + Negativo).  \n"
            "**Cobertura:** testados ÷ total de casos notificados."))
        st.plotly_chart(graficos.linhas_hiv(d["hiv_ano"]),
                        width="stretch", config=PLOTLY_CFG)

    c7, c8 = st.columns(2)
    with c7:
        st.subheader("Taxa de cura por tipo de entrada (tendência)", help=(
            "**Fonte:** SINAN-TB (coorte fechada)  \n"
            "**Denominador:** casos encerrados (exclui transferidos e em acompanhamento).  \n"
            "**Meta OMS:** ≥ 85% de cura."))
        st.plotly_chart(graficos.linhas_cura_tipo(d["coorte_tipo_ano"]),
                        width="stretch", config=PLOTLY_CFG)
    with c8:
        coorte_novo_df, total_novo = d["coorte_novo"]
        coorte_retrat_df, total_retrat = d["coorte_retrat"]
        subtab_novo, subtab_retrat = st.tabs([
            f"Casos novos ({fmt(total_novo)})",
            f"Retratamento ({fmt(total_retrat)})",
        ])
        with subtab_novo:
            st.subheader("Desfechos — casos novos", help=(
                "**Fonte:** SINAN-TB · **Denominador:** casos novos encerrados."))
            st.plotly_chart(graficos.barras_desfecho(coorte_novo_df),
                            width="stretch", config=PLOTLY_CFG)
        with subtab_retrat:
            st.subheader("Desfechos — retratamento", help=(
                "**Fonte:** SINAN-TB · **Denominador:** retratamentos encerrados."))
            st.plotly_chart(graficos.barras_desfecho(coorte_retrat_df),
                            width="stretch", config=PLOTLY_CFG)


# ── Mapa ──────────────────────────────────────────────────────────────────────
with tab_geo:
    # ── Controles compactos
    _b1, _b2, _spacer = st.columns([1, 1, 6])
    with _b1:
        if st.button("🗺️ Choropleth", use_container_width=True,
                     type="primary" if st.session_state.get("_modo_mapa", "Choropleth") == "Choropleth" else "secondary"):
            st.session_state["_modo_mapa"] = "Choropleth"
    with _b2:
        if st.button("🔥 Mapa de calor", use_container_width=True,
                     type="primary" if st.session_state.get("_modo_mapa") == "Mapa de calor" else "secondary"):
            st.session_state["_modo_mapa"] = "Mapa de calor"
    _modo_ativo = st.session_state.get("_modo_mapa", "Choropleth")

    # ── Layout 2 colunas: mapa | ranking
    col_map, col_rank = st.columns([3, 2])
    with col_map:
        components.html(mapa_html(_modo_ativo), height=680)
        st.caption("Fonte: SINAN-TB geocodificado · 2010–2023 · contornos: Prefeitura do Recife.")
    with col_rank:
        df_rank = mapa.por_bairro().head(15)
        fig_rank = graficos.barras_bairros(df_rank)
        st.plotly_chart(fig_rank, width="stretch", config=PLOTLY_CFG)


# ── Análise Livre (PyGWalker) ─────────────────────────────────────────────────
with tab_livre:
    st.markdown(
        "Exploração livre dos microdados SINAN-TB de Recife · 2010–2023.  \n"
        "Arraste campos para o eixo X/Y, use **Cor** e **Filtro** para segmentar.  \n"
        "Colunas decodificadas disponíveis: `tipo_entrada`, `desfecho`, `resultado_hiv`, "
        "`sexo`, `raca_cor`, `forma_clinica`, `ano`."
    )
    try:
        from pygwalker.api.streamlit import StreamlitRenderer

        @st.cache_resource
        def _pygwalker():
            df_dec = indicadores.df_para_analise()
            return StreamlitRenderer(df_dec, appearance="light")

        _pygwalker().explorer()
    except Exception as e:
        st.error(f"PyGWalker indisponível: {e}")

styles.footer()
