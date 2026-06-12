import streamlit as st
import pandas as pd
import geopandas as gpd
import folium

from streamlit_folium import st_folium

# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="CoopScore Granada",
    layout="wide"
)

# ============================================================
# CARGA DE DATOS
# ============================================================

@st.cache_data
def cargar_datos():

    df = pd.read_csv(
        "data/processed/dataset_scored_final.csv"
    )

    geo = gpd.read_file(
        "data/processed/municipios_granada_coopscore.geojson"
    )

    geo["codigo_ine"] = (
        geo["codigo_ine"]
        .astype(str)
        .str.zfill(5)
    )

    df["codigo_ine"] = (
        df["codigo_ine"]
        .astype(str)
        .str.zfill(5)
    )

    return df, geo


df, geo = cargar_datos()

# ============================================================
# CABECERA
# ============================================================

st.title("🏘️ CoopScore Granada")

st.markdown(
    """
    Herramienta de análisis territorial para la identificación
    de oportunidades urbanísticas, económicas y residenciales
    en los municipios de la provincia de Granada.
    """
)

# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ Mapa",
    "🏆 Ranking",
    "📊 Comparador",
    "📋 Metodología"
])

# ============================================================
# TAB 1 - MAPA
# ============================================================

with tab1:

    st.sidebar.header("Consulta municipal")

    municipio_sel = st.sidebar.selectbox(
        "Selecciona un municipio",
        sorted(df["municipio"].dropna().unique())
    )

    datos = df[
        df["municipio"] == municipio_sel
    ].iloc[0]

    st.subheader(
        f"Ficha municipal: {municipio_sel}"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "CoopScore",
        round(datos["CoopScore_4"], 2)
    )

    c2.metric(
        "IVU",
        round(datos["IVU"], 2)
    )

    c3.metric(
        "IPD",
        round(datos["IPD"], 2)
    )

    c4.metric(
        "IAL",
        round(datos["IAL"], 2)
    )

    st.write(
        f"**Categoría estratégica:** {datos['categoria_coopscore']}"
    )

    resumen = pd.DataFrame({
        "Indicador": [
            "Población 2025",
            "Precio venta €/m²",
            "Precio alquiler €/m²/mes",
            "Distancia capital (km)",
            "Distancia costa (km)"
        ],
        "Valor": [
            datos["poblacion_2025"],
            datos["precio_venta_eur_m2"],
            datos["precio_alquiler_eur_m2_mes"],
            round(datos["distancia_capital_km"], 1),
            round(datos["distancia_costa_km"], 1)
        ]
    })

    st.dataframe(
        resumen,
        use_container_width=True
    )

    st.subheader(
        "Mapa interactivo CoopScore"
    )

    mapa = folium.Map(
        location=[37.18, -3.60],
        zoom_start=9,
        tiles="CartoDB positron"
    )

    folium.Choropleth(
        geo_data=geo,
        data=geo,
        columns=[
            "codigo_ine",
            "CoopScore_4"
        ],
        key_on="feature.properties.codigo_ine",
        fill_color="YlOrRd",
        fill_opacity=0.8,
        line_opacity=0.2,
        legend_name="CoopScore"
    ).add_to(mapa)

    folium.GeoJson(
        geo,
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "nombre",
                "CoopScore_4",
                "categoria_coopscore"
            ],
            aliases=[
                "Municipio",
                "CoopScore",
                "Categoría"
            ]
        )
    ).add_to(mapa)

    st_folium(
        mapa,
        width=1200,
        height=700
    )

# ============================================================
# TAB 2 - RANKING
# ============================================================

with tab2:

    st.subheader("Ranking CoopScore")

    categoria = st.selectbox(
        "Filtrar categoría",
        ["Todas"] +
        sorted(df["categoria_coopscore"].unique())
    )

    if categoria == "Todas":

        df_filtrado = df.copy()

    else:

        df_filtrado = df[
            df["categoria_coopscore"] == categoria
        ]

    top_n = st.slider(
        "Número de municipios",
        5,
        50,
        20
    )

    ranking = (
        df_filtrado
        .sort_values(
            "CoopScore_4",
            ascending=False
        )
        .head(top_n)
    )

    st.dataframe(
        ranking[
            [
                "municipio",
                "CoopScore_4",
                "categoria_coopscore"
            ]
        ],
        use_container_width=True
    )

    col1, col2 = st.columns(2)

    with col1:

        st.download_button(
            label="📥 Descargar Ranking CSV",
            data=ranking.to_csv(index=False),
            file_name="ranking_coopscore.csv",
            mime="text/csv"
        )

    with col2:

        st.download_button(
            label="📥 Descargar Dataset Completo",
            data=df.to_csv(index=False),
            file_name="dataset_scored_final.csv",
            mime="text/csv"
        )

# ============================================================
# TAB 3 - COMPARADOR
# ============================================================

with tab3:

    st.subheader(
        "Comparador municipal"
    )

    col1, col2 = st.columns(2)

    with col1:
        mun1 = st.selectbox(
            "Municipio 1",
            sorted(df["municipio"]),
            key="mun1"
        )

    with col2:
        mun2 = st.selectbox(
            "Municipio 2",
            sorted(df["municipio"]),
            key="mun2"
        )

    comparacion = df[
        df["municipio"].isin(
            [mun1, mun2]
        )
    ][[
        "municipio",
        "CoopScore_4",
        "IVU",
        "IVEC",
        "IAL",
        "IPD"
    ]]

    st.dataframe(
        comparacion,
        use_container_width=True
    )

# ============================================================
# TAB 4 - METODOLOGÍA
# ============================================================

with tab4:

    st.markdown(
        """
# Metodología CoopScore

El CoopScore es un índice compuesto diseñado para evaluar
el potencial de desarrollo de los municipios de Granada.

## Componentes

### IVU
Índice de Viabilidad Urbanística.

### IVEC
Índice de Viabilidad Económica.

### IAL
Índice de Accesibilidad y Localización.

### IPD
Índice de Potencial de Demanda.

## Categorías Estratégicas

- Oportunidad Estratégica
- Potencial Urbanístico
- Potencial Económico
- Mercado Maduro

## Objetivo

Identificar municipios con potencial para el desarrollo
de proyectos residenciales, urbanísticos e inmobiliarios.
"""
    )