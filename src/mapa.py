"""
mapa.py
───────
Mapas de Recife com Folium. Dois modos que NÃO dependem de GeoJSON:
  • Mapa de calor (densidade de casos por lat/lon)
  • Pontos agregados por bairro (centroide + raio proporcional)
Choropleth por bairro/DS entra quando o GeoJSON estiver disponível.

Coordenadas inválidas (fora da bounding box de Recife) são descartadas — são
ruído do geocode (regra: limpar geo inválida antes de plotar).
"""

import json
import unicodedata

import branca.colormap as cm
import folium
import pandas as pd
import streamlit as st
from folium.plugins import HeatMap

from src import banco
from src.constantes import RECIFE_BBOX as BB, RECIFE_CENTRO, GEOJSON_BAIRRO


def norm(s) -> str | None:
    """Normaliza nome de bairro: sem acento, maiúsculo, espaços colapsados."""
    if s is None:
        return None
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.upper().split())


def _filtro_bbox() -> str:
    return (
        f"latitude BETWEEN {BB['lat_min']} AND {BB['lat_max']} "
        f"AND longitude BETWEEN {BB['lon_min']} AND {BB['lon_max']}"
    )


@st.cache_data(show_spinner=False)
def pontos() -> pd.DataFrame:
    """Coordenadas válidas (uma linha por caso) para o mapa de calor."""
    return banco.query_geo(
        f"SELECT latitude, longitude FROM tb WHERE latitude IS NOT NULL AND {_filtro_bbox()}"
    )


@st.cache_data(show_spinner=False)
def por_bairro() -> pd.DataFrame:
    """Casos por bairro com centroide (média lat/lon) para o mapa de bolhas."""
    return banco.query_geo(f"""
        SELECT nm_bairro AS bairro, COUNT(*) AS casos,
               AVG(latitude) AS lat, AVG(longitude) AS lon
        FROM tb
        WHERE nm_bairro IS NOT NULL AND nm_bairro <> 'BAIRRO IGNORADO' AND {_filtro_bbox()}
        GROUP BY nm_bairro ORDER BY casos DESC
    """)


def _base() -> folium.Map:
    m = folium.Map(
        location=list(RECIFE_CENTRO), zoom_start=12, min_zoom=11, max_zoom=16,
        tiles="CartoDB dark_matter", control_scale=True,
        zoomControl=True, dragging=True, boxZoom=False,
    )
    return m


def mapa_calor() -> folium.Map:
    """Mapa de densidade (heatmap) dos casos geocodificados."""
    m = _base()
    dados = pontos()[["latitude", "longitude"]].values.tolist()
    HeatMap(dados, radius=11, blur=15, min_opacity=0.25,
            gradient={0.2: "#1f6feb", 0.45: "#2ea043", 0.7: "#d29922", 1.0: "#da3633"}).add_to(m)
    return m


def mapa_bolhas() -> folium.Map:
    """Bolhas por bairro: raio ∝ nº de casos, tooltip com o total."""
    m = _base()
    df = por_bairro()
    cmax = df["casos"].max()
    for _, r in df.iterrows():
        raio = 4 + (r["casos"] / cmax) * 22
        folium.CircleMarker(
            location=[r["lat"], r["lon"]], radius=raio,
            color="#f0883e", weight=1, fill=True, fill_color="#f0883e", fill_opacity=0.55,
            tooltip=f"<b>{r['bairro'].title()}</b><br>{int(r['casos']):,} casos".replace(",", "."),
        ).add_to(m)
    return m


@st.cache_resource(show_spinner=False)
def _geojson_bairros() -> dict:
    """Carrega o GeoJSON oficial dos 94 bairros e injeta o nome normalizado."""
    g = json.load(open(GEOJSON_BAIRRO, encoding="utf-8"))
    for f in g["features"]:
        f["properties"]["_nome"] = norm(f["properties"]["EBAIRRNOME"])
    return g


def choropleth_bairro() -> folium.Map:
    """Choropleth: cada bairro pintado pelo nº de casos (2010–2023)."""
    m = _base()
    g = _geojson_bairros()

    df = banco.query_geo("SELECT nm_bairro, COUNT(*) AS casos FROM tb WHERE nm_bairro IS NOT NULL GROUP BY nm_bairro")
    df["_nome"] = df["nm_bairro"].map(norm)
    casos = df.groupby("_nome")["casos"].sum().to_dict()

    vmax = max(casos.values())
    escala = cm.LinearColormap(
        ["#FFFFCC", "#FED976", "#FEB24C", "#FD8D3C", "#FC4E2A", "#E31A1C", "#B10026"],
        vmin=0, vmax=vmax, caption="Casos de TB (2010–2023)",
    )

    def style(feat):
        v = casos.get(feat["properties"]["_nome"], 0)
        return {"fillColor": escala(v), "color": "#30363d", "weight": 0.6,
                "fillOpacity": 0.78 if v else 0.15}

    for f in g["features"]:
        f["properties"]["_casos"] = int(casos.get(f["properties"]["_nome"], 0))

    folium.GeoJson(
        g, style_function=style,
        highlight_function=lambda _: {"weight": 2, "color": "#f0f6fc"},
        tooltip=folium.GeoJsonTooltip(
            fields=["EBAIRRNOMEOF", "_casos"], aliases=["Bairro:", "Casos:"],
            localize=True, sticky=False,
            style="background:#161b22;color:#f0f6fc;border:1px solid #30363d;border-radius:6px;padding:6px;",
        ),
    ).add_to(m)
    escala.add_to(m)
    return m
