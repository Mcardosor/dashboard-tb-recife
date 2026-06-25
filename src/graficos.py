"""
graficos.py
───────────
Template Plotly ÚNICO e centralizado — toda figura passa por aplicar_layout()
para garantir consistência visual (regra de estética do projeto).
"""

import plotly.graph_objects as go
import plotly.express as px

from src.constantes import (
    PLOTLY_TEMPLATE, H_MEDIUM, H_LARGE, COR_MASC, COR_FEM, COR_CURA,
    COR_ABANDONO, COR_OBITO, COR_HIV, COR_NEUTRO, CORES, tb_color_map,
)

_MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def aplicar_layout(fig: go.Figure, altura: int = H_MEDIUM, titulo: str | None = None) -> go.Figure:
    """Aplica o template dark padrão a qualquer figura Plotly."""
    fig.update_layout(**PLOTLY_TEMPLATE["layout"])
    # title text explícito ("" quando sem título) — evita o Plotly renderizar "undefined".
    fig.update_layout(height=altura, title_text=(titulo or ""))
    return fig


def barras_por_ano(df, x="nu_ano", y="casos", titulo=None, cor=COR_MASC,
                    altura=H_MEDIUM, texto=True):
    """Gráfico de barras anual padronizado (números fora das barras, dark)."""
    fig = go.Figure(
        go.Bar(
            x=df[x], y=df[y],
            marker=dict(color=cor, line=dict(width=0)),
            text=df[y] if texto else None,
            textposition="outside",
            texttemplate="%{text:,.0f}" if texto else None,
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>%{y:,.0f} casos<extra></extra>",
        )
    )
    fig.update_xaxes(type="category", title=None)
    fig.update_yaxes(title=None)
    return aplicar_layout(fig, altura=altura, titulo=titulo)


def linha_incidencia(df, x="ano", y="incidencia", titulo=None, altura=H_MEDIUM):
    """Série anual de incidência por 100 mil hab (linha com área e marcadores)."""
    fig = go.Figure(
        go.Scatter(
            x=df[x], y=df[y], mode="lines+markers+text",
            line=dict(color=COR_CURA, width=3, shape="spline"),
            marker=dict(size=7, color=COR_CURA, line=dict(width=1, color="#0d1117")),
            fill="tozeroy", fillcolor="rgba(46,160,67,.10)",
            text=[f"{v:.0f}" for v in df[y]], textposition="top center",
            textfont=dict(size=10, color="#8b949e"),
            hovertemplate="<b>%{x}</b><br>%{y:.1f} / 100 mil hab<extra></extra>",
        )
    )
    fig.update_xaxes(type="category", title=None)
    fig.update_yaxes(title="por 100 mil hab", rangemode="tozero")
    return aplicar_layout(fig, altura=altura, titulo=titulo)


def barras_desfecho(df, titulo=None, altura=H_MEDIUM):
    """Barras horizontais dos desfechos de coorte, cor semântica + % no rótulo."""
    df = df.sort_values("n")
    cores = [tb_color_map([d])[d] for d in df["desfecho"]]
    fig = go.Figure(
        go.Bar(
            x=df["n"], y=df["desfecho"], orientation="h",
            marker=dict(color=cores, line=dict(width=0)),
            text=[f"{p:.1f}%" for p in df["pct"]],
            textposition="auto", insidetextanchor="end",
            textfont=dict(color="#0d1117", size=11),
            customdata=df["n"],
            hovertemplate="<b>%{y}</b><br>%{customdata:,.0f} casos (%{text})<extra></extra>",
        )
    )
    fig.update_xaxes(title=None, showticklabels=False)
    fig.update_yaxes(title=None)
    return aplicar_layout(fig, altura=altura, titulo=titulo)


def barras_novos_retratamento(df, titulo=None, altura=H_MEDIUM):
    """Casos novos vs retratamento por ano (barras agrupadas — não somar os dois)."""
    fig = go.Figure()
    fig.add_bar(x=df["ano"], y=df["casos_novos"], name="Casos novos",
                marker_color=COR_CURA,
                hovertemplate="<b>%{x}</b><br>%{y:,.0f} casos novos<extra></extra>")
    fig.add_bar(x=df["ano"], y=df["retratamento"], name="Retratamento",
                marker_color=COR_ABANDONO,
                hovertemplate="<b>%{x}</b><br>%{y:,.0f} retratamentos<extra></extra>")
    fig.update_layout(barmode="group", legend=dict(orientation="h", y=1.12, x=0))
    fig.update_xaxes(type="category", title=None)
    fig.update_yaxes(title=None)
    return aplicar_layout(fig, altura=altura, titulo=titulo)


def barras_sexo_ano(df, titulo=None, altura=H_MEDIUM):
    """Casos por sexo e ano (barras agrupadas M/F)."""
    fig = go.Figure()
    cores_sexo = {"M": COR_MASC, "F": COR_FEM}
    nomes = {"M": "Masculino", "F": "Feminino"}
    for sexo in ["M", "F"]:
        sub = df[df["sexo"] == sexo]
        fig.add_bar(
            x=sub["ano"], y=sub["casos"],
            name=nomes[sexo], marker_color=cores_sexo[sexo],
            hovertemplate=f"<b>%{{x}}</b><br>{nomes[sexo]}: %{{y:,.0f}}<extra></extra>",
        )
    fig.update_layout(barmode="group", legend=dict(orientation="h", y=1.12, x=0))
    fig.update_xaxes(type="category", title=None)
    fig.update_yaxes(title=None)
    return aplicar_layout(fig, altura=altura, titulo=titulo)


def barras_h_pct(df, col_label, col_pct, col_n, titulo=None, altura=H_MEDIUM, cores=None,
                  cor_unica=None):
    """Barras horizontais com % e N no tooltip. Genérico para raça, faixa, pop vulnerável."""
    df = df.sort_values(col_pct)
    if cores:
        bar_cores = cores
    elif cor_unica:
        bar_cores = [cor_unica] * len(df)
    else:
        bar_cores = [COR_NEUTRO] * len(df)
    fig = go.Figure(
        go.Bar(
            x=df[col_pct], y=df[col_label], orientation="h",
            marker=dict(color=bar_cores, line=dict(width=0)),
            text=[f"{p:.1f}%" for p in df[col_pct]],
            textposition="outside", cliponaxis=False,
            customdata=df[col_n],
            hovertemplate="<b>%{y}</b><br>%{customdata:,.0f} casos (%{text})<extra></extra>",
        )
    )
    fig.update_xaxes(title="%", range=[0, df[col_pct].max() * 1.18])
    fig.update_yaxes(title=None)
    return aplicar_layout(fig, altura=altura, titulo=titulo)


def barras_faixa_etaria(df, titulo=None, altura=H_MEDIUM):
    """Pirâmide simplificada — barras horizontais por faixa etária."""
    return barras_h_pct(
        df, col_label="faixa", col_pct="pct", col_n="casos",
        titulo=titulo, altura=altura,
        cores=[COR_MASC] * len(df),
    )


def pizza_forma(df, titulo=None, altura=H_MEDIUM):
    """Gráfico de rosca para forma clínica."""
    cores_forma = tb_color_map(df["forma"].tolist())
    fig = go.Figure(
        go.Pie(
            labels=df["forma"], values=df["casos"],
            hole=0.45,
            marker=dict(colors=[cores_forma[f] for f in df["forma"]],
                        line=dict(color="#0d1117", width=2)),
            textinfo="percent+label",
            textfont=dict(size=11, color="#c9d1d9"),
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} casos (%{percent})<extra></extra>",
        )
    )
    return aplicar_layout(fig, altura=altura, titulo=titulo)


def linhas_hiv(df, titulo=None, altura=H_MEDIUM):
    """Cobertura de testagem e positividade HIV por ano (dois eixos)."""
    fig = go.Figure()
    fig.add_scatter(
        x=df["ano"], y=df["cobertura"], name="Cobertura testagem (%)",
        mode="lines+markers", line=dict(color=COR_NEUTRO, width=2),
        marker=dict(size=6), yaxis="y2",
        hovertemplate="<b>%{x}</b><br>Cobertura: %{y:.1f}%<extra></extra>",
    )
    fig.add_scatter(
        x=df["ano"], y=df["positividade"], name="HIV+ entre testados (%)",
        mode="lines+markers+text", line=dict(color=COR_HIV, width=3),
        marker=dict(size=7, color=COR_HIV),
        text=[f"{v:.0f}%" for v in df["positividade"]],
        textposition="top center", textfont=dict(size=9, color="#8b949e"),
        hovertemplate="<b>%{x}</b><br>Positividade: %{y:.1f}%<extra></extra>",
    )
    fig.update_layout(
        yaxis=dict(title="HIV+ (%)", range=[0, df["positividade"].max() * 1.3]),
        yaxis2=dict(title="Cobertura (%)", overlaying="y", side="right",
                    range=[0, 110], showgrid=False),
        legend=dict(orientation="h", y=1.15, x=0),
    )
    fig.update_xaxes(type="category", title=None)
    return aplicar_layout(fig, altura=altura, titulo=titulo)


def linhas_cura_tipo(df, titulo=None, altura=H_MEDIUM):
    """Taxa de cura por tipo de entrada ao longo dos anos."""
    fig = go.Figure()
    cores_tipo = {"Casos novos": COR_CURA, "Retratamento": COR_ABANDONO}
    for tipo, grp in df.groupby("tipo"):
        fig.add_scatter(
            x=grp["ano"], y=grp["tx_cura"], name=tipo,
            mode="lines+markers",
            line=dict(color=cores_tipo.get(tipo, COR_MASC), width=2),
            marker=dict(size=6),
            hovertemplate=f"<b>%{{x}}</b><br>{tipo}: %{{y:.1f}}% cura<extra></extra>",
        )
    fig.add_hline(y=85, line_dash="dot", line_color="#30363d",
                  annotation_text="Meta OMS 85%", annotation_font_color="#8b949e",
                  annotation_position="bottom right")
    fig.update_xaxes(type="category", title=None)
    fig.update_yaxes(title="% cura", range=[0, 100])
    fig.update_layout(legend=dict(orientation="h", y=1.12, x=0))
    return aplicar_layout(fig, altura=altura, titulo=titulo)


def linha_abandono(df, titulo=None, altura=H_MEDIUM):
    """Evolução da taxa de abandono por ano com linha de meta OMS."""
    fig = go.Figure(
        go.Scatter(
            x=df["ano"], y=df["tx_abandono"],
            mode="lines+markers+text",
            line=dict(color=COR_ABANDONO, width=3),
            marker=dict(size=7, color=COR_ABANDONO, line=dict(width=1, color="#0d1117")),
            text=[f"{v:.1f}%" for v in df["tx_abandono"]],
            textposition="top center", textfont=dict(size=9, color="#8b949e"),
            hovertemplate="<b>%{x}</b><br>Abandono: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_hline(y=5, line_dash="dot", line_color="#30363d",
                  annotation_text="Meta OMS 5%", annotation_font_color="#8b949e",
                  annotation_position="bottom right")
    fig.update_xaxes(type="category", title=None)
    fig.update_yaxes(title="% abandono", range=[0, max(df["tx_abandono"].max() * 1.25, 8)])
    return aplicar_layout(fig, altura=altura, titulo=titulo)


def barras_faixa_por_ano(df, titulo=None, altura=H_MEDIUM):
    """Casos por faixa etária ao longo dos anos (barras empilhadas)."""
    faixas  = ["< 15 anos", "15–34 anos", "35–54 anos", "55–64 anos", "65+ anos"]
    cores_f = ["#cae8ff", "#79c0ff", "#58a6ff", "#1f6feb", "#0d419d"]
    fig = go.Figure()
    for faixa, cor in zip(faixas, cores_f):
        sub = df[df["faixa"] == faixa]
        if sub.empty:
            continue
        fig.add_bar(
            x=sub["ano"], y=sub["casos"], name=faixa, marker_color=cor,
            hovertemplate=f"<b>%{{x}}</b><br>{faixa}: %{{y:,.0f}} casos<extra></extra>",
        )
    fig.update_layout(barmode="stack", legend=dict(orientation="h", y=1.15, x=0))
    fig.update_xaxes(type="category", title=None)
    fig.update_yaxes(title=None)
    return aplicar_layout(fig, altura=altura, titulo=titulo)


def barras_sazonalidade(df, titulo=None, altura=H_MEDIUM):
    """Média de notificações por mês do ano."""
    fig = go.Figure(
        go.Bar(
            x=[_MESES[m - 1] for m in df["mes"]], y=df["media"],
            marker=dict(color=COR_MASC),
            text=[f"{v:.0f}" for v in df["media"]], textposition="outside", cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>%{y:.1f} casos/mês (média)<extra></extra>",
        )
    )
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="média/mês", rangemode="tozero")
    return aplicar_layout(fig, altura=altura, titulo=titulo)
