import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata
import anthropic

from normativa_pgou import CHUNKS, buscar_chunks


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


def get_client():
    """Devuelve el cliente Anthropic usando la API key de Streamlit secrets."""
    return anthropic.Anthropic(
        api_key=st.secrets["ANTHROPIC_API_KEY"]
    )


def analizar_municipio_ia(fila: pd.Series) -> str:
    """Genera un análisis de viabilidad cooperativa para un municipio."""

    chunks_relevantes = buscar_chunks(
        "vivienda cooperativa suelo urbanizable edificabilidad residencial"
    )

    normativa_ctx = "\n\n".join(
        f"### {c['titulo']}\n{c['contenido']}"
        for c in chunks_relevantes
    )

    prompt = f"""Analiza la viabilidad para una promoción de **vivienda cooperativa** en
**{fila['municipio']}** con los siguientes datos del CoopScore:

- **CoopScore:** {round(fila['coopscore_v6'], 2)}/100
- **IVU (Urbanístico):** {round(fila['IVU'], 2)}/100
- **IVEC (Económico):** {round(fila['IVEC'], 2)}/100
- **Perfil:** {fila['perfil_municipio']}
- **Población:** {int(fila['poblacion_2025']):,} hab.
- **Precio suelo:** {fila['precio_venta_eur_m2']} €/m²
- **Suelo residencial disponible:** {fila['superficie_residencial_m2']/10000:.1f} ha ({int(fila['n_poligonos'])} polígonos)
- **Suelo por habitante:** {round(fila['suelo_por_habitante'], 1)} m²/hab.
- **Distancia a Granada capital:** {fila['distancia_capital_km']} km

Proporciona un análisis estructurado con:
1. **Diagnóstico rápido**: idoneidad del municipio para una cooperativa
2. **Potencial edificatorio**: si IVU > 40, estima viviendas posibles
   (usa edificabilidad bruta 0,35 m²/m² en SUP, 100 m² útiles/vivienda)
3. **Condiciones urbanísticas clave** del PGOU aplicables
4. **Recomendación**: pasos concretos para una cooperativa interesada

NORMATIVA PGOU DE GRANADA APLICABLE:
{normativa_ctx}"""

    client = get_client()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        system=(
            "Eres un experto en vivienda cooperativa y urbanismo en Andalucía. "
            "Analiza la viabilidad de promociones cooperativas usando datos del CoopScore "
            "y la normativa del PGOU de Granada. Sé concreto, útil y directo. "
            "Responde en español."
        ),
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


def chat_pgou(historial: list[dict], pregunta: str, municipio_fila=None) -> str:
    """Responde una pregunta del asistente PGOU con contexto de normativa."""

    chunks_relevantes = buscar_chunks(pregunta, n=3)

    normativa_ctx = (
        "\n\n".join(
            f"### {c['titulo']}\n{c['contenido']}"
            for c in chunks_relevantes
        )
        if chunks_relevantes
        else ""
    )

    municipio_ctx = ""
    if municipio_fila is not None:
        municipio_ctx = (
            f"\n\nMUNICIPIO ACTIVO EN LA SESIÓN: {municipio_fila['municipio']}\n"
            f"CoopScore: {round(municipio_fila['coopscore_v6'],2)} | "
            f"IVU: {round(municipio_fila['IVU'],2)} | "
            f"IVEC: {round(municipio_fila['IVEC'],2)} | "
            f"Perfil: {municipio_fila['perfil_municipio']} | "
            f"Precio: {municipio_fila['precio_venta_eur_m2']} €/m²"
        )

    system = (
        "Eres un experto en vivienda cooperativa, urbanismo y el PGOU de Granada. "
        "Combinas análisis del CoopScore con normativa urbanística para asesorar "
        "sobre viabilidad de cooperativas en la provincia de Granada. "
        "Responde en español de forma clara y útil."
        + (f"\n\nNORMATIVA PGOU RELEVANTE:\n{normativa_ctx}" if normativa_ctx else "")
        + municipio_ctx
    )

    mensajes = historial + [{"role": "user", "content": pregunta}]

    client = get_client()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=system,
        messages=mensajes,
    )

    return response.content[0].text


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
# INTERPRETACIÓN AUTOMÁTICA (original)
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
# ANÁLISIS IA + PGOU  ← NUEVO
# =====================================================

st.divider()

st.subheader("🤖 Análisis IA + Normativa PGOU")

st.markdown(
    "Análisis de viabilidad cooperativa generado por IA, "
    "combinando el CoopScore con la normativa urbanística del "
    "**PGOU de Granada**."
)

if st.button(
    f"Generar análisis para {municipio_sel}",
    type="primary"
):

    with st.spinner("Analizando viabilidad urbanística y económica..."):

        try:

            analisis = analizar_municipio_ia(fila)
            st.markdown(analisis)

        except Exception as e:

            st.error(
                f"Error al generar el análisis: {e}. "
                "Comprueba que la API key está configurada en .streamlit/secrets.toml"
            )

# =====================================================
# ASISTENTE PGOU  ← NUEVO
# =====================================================

st.divider()

st.subheader("💬 Asistente PGOU Granada")

st.markdown(
    "Pregunta sobre normativa urbanística, condiciones de edificación "
    "o viabilidad cooperativa en la provincia de Granada."
)

# Inicializar historial en session_state
if "historial_chat" not in st.session_state:
    st.session_state.historial_chat = []

# Mostrar historial
for msg in st.session_state.historial_chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input del usuario
pregunta = st.chat_input(
    "Pregunta sobre normativa PGOU, cooperativas o municipios..."
)

if pregunta:

    # Mostrar pregunta
    with st.chat_message("user"):
        st.markdown(pregunta)

    # Generar respuesta
    with st.chat_message("assistant"):

        with st.spinner("Consultando normativa PGOU..."):

            try:

                # Pasar solo los últimos 6 mensajes para no sobrecargar
                historial_reciente = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.historial_chat[-6:]
                ]

                respuesta = chat_pgou(
                    historial=historial_reciente,
                    pregunta=pregunta,
                    municipio_fila=fila
                )

                st.markdown(respuesta)

            except Exception as e:

                respuesta = (
                    f"Error al conectar con la IA: {e}. "
                    "Comprueba la API key en .streamlit/secrets.toml"
                )

                st.error(respuesta)

    # Guardar en historial
    st.session_state.historial_chat.append(
        {"role": "user", "content": pregunta}
    )

    st.session_state.historial_chat.append(
        {"role": "assistant", "content": respuesta}
    )

# Botón para limpiar chat
if st.session_state.historial_chat:

    if st.button("🗑️ Limpiar conversación"):

        st.session_state.historial_chat = []
        st.rerun()

# =====================================================
# FOOTER
# =====================================================

st.divider()

st.caption(
    "TFM Data Science e Inteligencia Artificial · CoopScore Granada · 2026"
)
