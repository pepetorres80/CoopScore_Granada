import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata

# =====================================================
# CONFIGURACIÓN
# =====================================================

st.set_page_config(
    page_title="CoopScore Granada",
    page_icon="🏘️",
    layout="wide"
)

# =====================================================
# FUNCIONES
# =====================================================

def limpiar_texto(texto):

    texto = str(texto).strip().lower()

    texto = ''.join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )

    return texto


# =====================================================
# TÍTULO
# =====================================================

st.title("🏘️ CoopScore Granada")

st.markdown(
    """
    Plataforma de apoyo a la decisión para la identificación
    de oportunidades de desarrollo de vivienda cooperativa
    en la provincia de Granada.
    """
)

# =====================================================
# CARGA DE DATOS
# =====================================================

df = pd.read_csv(
    "data/processed/dataset_final_tfm_v7.csv"
)

coords = pd.read_csv(
    "data/external/coordenadas_pueblos_v2.csv"
)

# =====================================================
# NORMALIZACIÓN MUNICIPIOS
# =====================================================

df["municipio_merge"] = (
    df["municipio"]
    .apply(limpiar_texto)
)

coords["municipio_merge"] = (
    coords["municipio"]
    .apply(limpiar_texto)
)

correcciones = {
    "gabias, las": "las gabias",
    "valle, el": "el valle",
    "malaha, la": "la malaha",
    "calahorra, la": "la calahorra",
    "peza, la": "la peza"
}

df["municipio_merge"] = (
    df["municipio_merge"]
    .replace(correcciones)
)

# =====================================================
# MERGE COORDENADAS
# =====================================================

mapa_df = df.merge(
    coords[
        [
            "municipio_merge",
            "latitud",
            "longitud"
        ]
    ],
    on="municipio_merge",
    how="left"
)

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.title("Filtros")

perfil_sel = st.sidebar.multiselect(
    "Perfil municipal",
    sorted(df["perfil_municipio"].unique()),
    default=sorted(df["perfil_municipio"].unique())
)

df_filtrado = df[
    df["perfil_municipio"].isin(perfil_sel)
]

mapa_df_filtrado = mapa_df[
    mapa_df["perfil_municipio"].isin(perfil_sel)
]

# =====================================================
# KPIs
# =====================================================

st.subheader("Indicadores Provinciales")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Municipios",
    len(df)
)

col2.metric(
    "CoopScore Máximo",
    round(df["coopscore_v6"].max(), 2)
)

col3.metric(
    "Alta Prioridad",
    (df["perfil_municipio"] == "Alta Prioridad").sum()
)

col4.metric(
    "Precio Medio €/m²",
    round(df["precio_venta_eur_m2"].mean(), 0)
)

# =====================================================
# TOP MUNICIPIOS
# =====================================================

st.subheader("🏆 Top 20 Municipios")

st.dataframe(
    df_filtrado[
        [
            "municipio",
            "coopscore_v6",
            "IVU",
            "IVEC",
            "perfil_municipio"
        ]
    ]
    .sort_values(
        "coopscore_v6",
        ascending=False
    )
    .head(20),
    width="stretch"
)

# =====================================================
# MAPA
# =====================================================

st.subheader("🗺️ Mapa de Oportunidad Cooperativa")

fig = px.scatter_mapbox(
    mapa_df_filtrado,
    lat="latitud",
    lon="longitud",
    size="coopscore_v6",
    color="perfil_municipio",
    hover_name="municipio",
    hover_data={
        "coopscore_v6": True,
        "IVU": True,
        "IVEC": True,
        "poblacion_2025": True,
        "latitud": False,
        "longitud": False
    },
    zoom=8,
    height=700
)

fig.update_layout(
    mapbox_style="open-street-map",
    margin=dict(
        l=0,
        r=0,
        t=0,
        b=0
    )
)

st.plotly_chart(
    fig,
    width="stretch"
)

# =====================================================
# ANÁLISIS MUNICIPAL
# =====================================================

st.subheader("🔍 Análisis Municipal")

municipio_sel = st.selectbox(
    "Selecciona un municipio",
    sorted(df_filtrado["municipio"].unique())
)

fila = df_filtrado[
    df_filtrado["municipio"] == municipio_sel
].iloc[0]

# =====================================================
# KPIs MUNICIPALES
# =====================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "CoopScore",
    round(fila["coopscore_v6"], 2)
)

c2.metric(
    "IVU",
    round(fila["IVU"], 2)
)

c3.metric(
    "IVEC",
    round(fila["IVEC"], 2)
)

c4.metric(
    "Perfil",
    fila["perfil_municipio"]
)

# =====================================================
# INTERPRETACIÓN AUTOMÁTICA
# =====================================================

if fila["perfil_municipio"] == "Alta Prioridad":

    st.success(
        f"{municipio_sel} presenta una combinación especialmente favorable "
        "de potencial urbanístico y atractivo económico para el desarrollo "
        "de promociones cooperativas."
    )

elif fila["perfil_municipio"] == "Potencial Económico":

    st.info(
        f"{municipio_sel} destaca principalmente por sus indicadores "
        "económicos y de mercado."
    )

elif fila["perfil_municipio"] == "Potencial Urbanístico":

    st.info(
        f"{municipio_sel} destaca por la disponibilidad de suelo "
        "y capacidad de desarrollo urbanístico."
    )

else:

    st.info(
        f"{municipio_sel} presenta un perfil equilibrado entre "
        "variables urbanísticas y económicas."
    )

# =====================================================
# DETALLE MUNICIPAL
# =====================================================

st.dataframe(

    pd.DataFrame(

        {
            "Indicador": [
                "Población",
                "Precio €/m²",
                "Distancia capital (km)",
                "Suelo por habitante"
            ],

            "Valor": [
                fila["poblacion_2025"],
                fila["precio_venta_eur_m2"],
                fila["distancia_capital_km"],
                round(fila["suelo_por_habitante"], 2)
            ]
        }

    ),

    width="stretch"
)

# =====================================================
# COMPARATIVA VISUAL
# =====================================================

st.subheader("📊 Comparativa de Indicadores")

grafico = pd.DataFrame(
    {
        "Valor": [
            fila["coopscore_v6"],
            fila["IVU"],
            fila["IVEC"]
        ]
    },
    index=[
        "CoopScore",
        "IVU",
        "IVEC"
    ]
)

st.bar_chart(grafico)

# =====================================================
# FOOTER
# =====================================================

st.divider()

st.caption(
    "TFM Data Science e Inteligencia Artificial · CoopScore Granada · 2026"
)