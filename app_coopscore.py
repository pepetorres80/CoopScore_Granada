import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
import plotly.express as px
import plotly.graph_objects as go
import anthropic
import re
import json
import os
from pathlib import Path
from streamlit_folium import st_folium

# ════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="CoopScore Granada",
    page_icon="🏘️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS personalizado — identidad visual limpia y técnica
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main { background: #0e1117; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #1a1f2e;
        padding: 6px;
        border-radius: 10px;
        border: 1px solid #2a2f3e;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 7px;
        color: #7a8099;
        font-weight: 500;
        font-size: 13px;
        padding: 6px 16px;
    }
    .stTabs [aria-selected="true"] {
        background: #e85d26 !important;
        color: white !important;
    }

    /* Métricas */
    [data-testid="metric-container"] {
        background: #1a1f2e;
        border: 1px solid #2a2f3e;
        border-radius: 10px;
        padding: 14px 18px;
    }
    [data-testid="metric-container"] label {
        color: #7a8099 !important;
        font-size: 11px !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    [data-testid="stMetricValue"] {
        color: #e8e9ed !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 1.8rem !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0f1420;
        border-right: 1px solid #1e2535;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

    /* Botones */
    .stButton button {
        background: #e85d26;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        font-size: 13px;
        padding: 8px 20px;
    }
    .stButton button:hover { background: #c44d1e; }

    /* Header badge */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
    }
    .badge-oe  { background: #1a3a2a; color: #4ade80; border: 1px solid #2a5a3a; }
    .badge-pu  { background: #1a2a3a; color: #60a5fa; border: 1px solid #2a4a6a; }
    .badge-pe  { background: #3a2a1a; color: #fb923c; border: 1px solid #6a4a2a; }
    .badge-mm  { background: #2a1a3a; color: #c084fc; border: 1px solid #4a2a6a; }

    /* Chat bubble */
    .chat-user {
        background: #e85d26; color: white;
        border-radius: 12px 12px 2px 12px;
        padding: 10px 14px; margin: 6px 0;
        max-width: 75%; margin-left: auto;
        font-size: 13px; line-height: 1.5;
    }
    .chat-bot {
        background: #1a1f2e; color: #e8e9ed;
        border: 1px solid #2a2f3e;
        border-radius: 12px 12px 12px 2px;
        padding: 10px 14px; margin: 6px 0;
        max-width: 85%;
        font-size: 13px; line-height: 1.6;
    }
    .chat-sources {
        font-size: 10px; color: #4a5070;
        margin-top: 4px; font-style: italic;
    }
    .beta-badge {
        background: #e85d26; color: white;
        border-radius: 4px; padding: 2px 7px;
        font-size: 10px; font-weight: 700;
        letter-spacing: 1px; vertical-align: middle;
    }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ════════════════════════════════════════════════════════════

BASE = Path(__file__).parent

@st.cache_data
def cargar_datos():
    df  = pd.read_csv(BASE / "data/processed/dataset_scored_final.csv")
    geo = gpd.read_file(BASE / "data/processed/municipios_granada_coopscore.geojson")
    df["codigo_ine"]  = df["codigo_ine"].astype(str).str.zfill(5)
    geo["codigo_ine"] = geo["codigo_ine"].astype(str).str.zfill(5)
    return df, geo

@st.cache_data
def cargar_chunks():
    path = BASE / "normativa_chunks.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)

df, geo = cargar_datos()
chunks  = cargar_chunks()

# Paleta de categorías
CAT_COLOR = {
    "Oportunidad Estratégica": "#4ade80",
    "Potencial Urbanístico":   "#60a5fa",
    "Potencial Económico":     "#fb923c",
    "Mercado Maduro":          "#c084fc",
}
CAT_BADGE = {
    "Oportunidad Estratégica": "badge-oe",
    "Potencial Urbanístico":   "badge-pu",
    "Potencial Económico":     "badge-pe",
    "Mercado Maduro":          "badge-mm",
}

# ════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════

col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("""
    <div style="padding: 8px 0 4px">
        <span style="font-family:'Space Grotesk',sans-serif;font-size:28px;
                     font-weight:700;color:#e8e9ed;letter-spacing:-0.5px">
            🏘️ CoopScore Granada
        </span>
        <span style="margin-left:10px;font-size:12px;color:#7a8099">
            Análisis territorial · Vivienda cooperativa · Provincia de Granada
        </span>
    </div>
    """, unsafe_allow_html=True)
with col_h2:
    st.markdown(f"""
    <div style="text-align:right;padding-top:10px">
        <span style="background:#1a1f2e;border:1px solid #2a2f3e;border-radius:20px;
                     padding:5px 14px;font-size:11px;color:#4ade80">
            ● {len(df)} municipios analizados
        </span>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### 🔍 Filtros globales")
    categorias = st.multiselect(
        "Categoría estratégica",
        options=sorted(df["categoria_coopscore"].unique()),
        default=sorted(df["categoria_coopscore"].unique()),
    )
    comarcas_disponibles = sorted(df["comarca"].dropna().unique())
    comarcas_disponibles = [c for c in comarcas_disponibles if c.strip()]
    comarca_sel = st.multiselect("Comarca", comarcas_disponibles, default=comarcas_disponibles)

    st.divider()
    st.markdown("### 📌 Municipio de análisis")
    municipio_sel = st.selectbox(
        "Selecciona municipio",
        sorted(df["municipio"].dropna().unique()),
    )

df_fil = df[df["categoria_coopscore"].isin(categorias)]
if comarca_sel:
    df_fil = df_fil[df_fil["comarca"].isin(comarca_sel) | df_fil["comarca"].isna() | (df_fil["comarca"] == "")]

geo_fil = geo[geo["codigo_ine"].isin(df_fil["codigo_ine"].astype(str).str.zfill(5))]

# ════════════════════════════════════════════════════════════
# KPIs GLOBALES
# ════════════════════════════════════════════════════════════

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Municipios", len(df_fil))
k2.metric("CoopScore máx.", f"{df_fil['CoopScore_4'].max():.1f}")
k3.metric("Oportunidad Estratégica", (df_fil["categoria_coopscore"] == "Oportunidad Estratégica").sum())
k4.metric("Precio medio €/m²",
          f"{df_fil[df_fil['precio_venta_eur_m2']>0]['precio_venta_eur_m2'].mean():.0f}" if (df_fil["precio_venta_eur_m2"]>0).any() else "N/D")
k5.metric("Suelo urb. medio (ha)",
          f"{(df_fil['area_m2_Urbanizable'].fillna(0)/10000).mean():.1f}")

st.divider()

# ════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺️ Mapa",
    "🏆 Ranking",
    "📊 Comparador",
    "📋 Metodología",
    "🤖 Asesor PGOU  BETA",
])

# ────────────────────────────────────────────────────────────
# TAB 1 — MAPA
# ────────────────────────────────────────────────────────────

with tab1:
    datos_mun = df[df["municipio"] == municipio_sel].iloc[0]
    cat = datos_mun["categoria_coopscore"]

    st.markdown(f"""
    <div style="background:#1a1f2e;border:1px solid #2a2f3e;border-radius:10px;
                padding:14px 20px;margin-bottom:16px;display:flex;align-items:center;gap:12px">
        <span style="font-size:20px">📍</span>
        <span style="font-family:'Space Grotesk',sans-serif;font-size:16px;font-weight:700;color:#e8e9ed">
            {municipio_sel}
        </span>
        <span class="badge {CAT_BADGE.get(cat,'badge-mm')}">{cat}</span>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("CoopScore", f"{datos_mun['CoopScore_4']:.1f}")
    c2.metric("IVU", f"{datos_mun['IVU']:.1f}")
    c3.metric("IVEC", f"{datos_mun['IVEC']:.1f}")
    c4.metric("IPD", f"{datos_mun['IPD']:.1f}")
    c5.metric("IAL", f"{datos_mun['IAL']:.1f}")

    col_mapa, col_ficha = st.columns([3, 1])

    with col_mapa:
        mapa = folium.Map(location=[37.18, -3.60], zoom_start=9, tiles="CartoDB dark_matter")
        folium.Choropleth(
            geo_data=geo,
            data=geo,
            columns=["codigo_ine", "CoopScore_4"],
            key_on="feature.properties.codigo_ine",
            fill_color="YlOrRd",
            fill_opacity=0.75,
            line_opacity=0.3,
            line_color="#333",
            legend_name="CoopScore",
            nan_fill_color="#1a1f2e",
        ).add_to(mapa)
        folium.GeoJson(
            geo,
            style_function=lambda f: {"fillOpacity": 0, "color": "transparent", "weight": 0},
            tooltip=folium.GeoJsonTooltip(
                fields=["nombre", "CoopScore_4", "categoria_coopscore", "poblacion_2025"],
                aliases=["Municipio", "CoopScore", "Categoría", "Población"],
                style="background:#1a1f2e;color:#e8e9ed;border:1px solid #2a2f3e;border-radius:6px;font-size:12px",
            ),
        ).add_to(mapa)
        st_folium(mapa, width="100%", height=600)

    with col_ficha:
        st.markdown("##### 📋 Ficha municipal")
        ficha = {
            "Población 2025": f"{int(datos_mun['poblacion_2025']):,}",
            "Precio venta €/m²": f"{datos_mun['precio_venta_eur_m2']:.0f}" if datos_mun['precio_venta_eur_m2'] > 0 else "N/D",
            "Precio alquiler €/m²/mes": f"{datos_mun['precio_alquiler_eur_m2_mes']:.1f}" if datos_mun['precio_alquiler_eur_m2_mes'] > 0 else "N/D",
            "Dist. capital (km)": f"{datos_mun['distancia_capital_km']:.1f}",
            "Dist. costa (km)": f"{datos_mun['distancia_costa_km']:.1f}",
            "Suelo SUNC (ha)": f"{datos_mun['area_m2_SUNC']/10000:.1f}" if datos_mun['area_m2_SUNC'] > 0 else "N/D",
            "Suelo urbanizable (ha)": f"{datos_mun['area_m2_Urbanizable']/10000:.1f}" if datos_mun['area_m2_Urbanizable'] > 0 else "N/D",
            "Suelo por habitante (m²)": f"{datos_mun['suelo_residencial_m2_por_hab']:.1f}" if datos_mun['suelo_residencial_m2_por_hab'] > 0 else "N/D",
        }
        for k, v in ficha.items():
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;padding:7px 0;
                        border-bottom:1px solid #1e2535;font-size:12px">
                <span style="color:#7a8099">{k}</span>
                <span style="color:#e8e9ed;font-weight:500">{v}</span>
            </div>
            """, unsafe_allow_html=True)

        # Radar chart
        st.markdown("<br>", unsafe_allow_html=True)
        fig_radar = go.Figure(go.Scatterpolar(
            r=[datos_mun["IVU"], datos_mun["IVEC"], datos_mun["IPD"], datos_mun["IAL"], datos_mun["IVU"]],
            theta=["IVU", "IVEC", "IPD", "IAL", "IVU"],
            fill="toself",
            fillcolor="rgba(232,93,38,0.25)",
            line=dict(color="#e85d26", width=2),
        ))
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], gridcolor="#2a2f3e", color="#4a5070"),
                angularaxis=dict(gridcolor="#2a2f3e", color="#7a8099"),
                bgcolor="#1a1f2e",
            ),
            paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
            margin=dict(l=30, r=30, t=30, b=30),
            height=250,
            showlegend=False,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

# ────────────────────────────────────────────────────────────
# TAB 2 — RANKING
# ────────────────────────────────────────────────────────────

with tab2:
    col_r1, col_r2 = st.columns([2, 1])
    with col_r1:
        st.markdown("#### 🏆 Ranking CoopScore")
    with col_r2:
        top_n = st.slider("Número de municipios", 10, 50, 20, key="top_n")

    ranking = (
        df_fil[["municipio", "comarca", "CoopScore_4", "IVU", "IVEC", "IPD", "IAL",
                "categoria_coopscore", "poblacion_2025", "precio_venta_eur_m2"]]
        .sort_values("CoopScore_4", ascending=False)
        .head(top_n)
        .rename(columns={
            "CoopScore_4": "CoopScore", "categoria_coopscore": "Categoría",
            "poblacion_2025": "Población", "precio_venta_eur_m2": "€/m²",
        })
    )

    st.dataframe(
        ranking.style.background_gradient(subset=["CoopScore"], cmap="YlOrRd")
                     .format({"CoopScore": "{:.1f}", "IVU": "{:.1f}", "IVEC": "{:.1f}",
                               "IPD": "{:.1f}", "IAL": "{:.1f}", "Población": "{:,.0f}"}),
        use_container_width=True, height=480,
    )

    # Scatter plot IVU vs IVEC
    st.markdown("#### IVU vs IVEC por categoría")
    fig_scatter = px.scatter(
        df_fil,
        x="IVU", y="IVEC",
        size="CoopScore_4", color="categoria_coopscore",
        color_discrete_map=CAT_COLOR,
        hover_name="municipio",
        hover_data={"CoopScore_4": ":.1f", "poblacion_2025": ":,.0f"},
        labels={"IVU": "Índice Viabilidad Urbanística", "IVEC": "Índice Viabilidad Económica",
                "categoria_coopscore": "Categoría"},
        template="plotly_dark",
    )
    fig_scatter.update_layout(
        paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
        legend=dict(bgcolor="#1a1f2e", bordercolor="#2a2f3e"),
        margin=dict(t=20),
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    # Downloads
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.download_button(
            "📥 Descargar ranking CSV",
            ranking.to_csv(index=False),
            "ranking_coopscore.csv", "text/csv",
        )
    with col_d2:
        st.download_button(
            "📥 Descargar dataset completo",
            df.to_csv(index=False),
            "dataset_scored_final.csv", "text/csv",
        )

# ────────────────────────────────────────────────────────────
# TAB 3 — COMPARADOR
# ────────────────────────────────────────────────────────────

with tab3:
    st.markdown("#### 📊 Comparador municipal")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        mun1 = st.selectbox("Municipio A", sorted(df["municipio"]), key="mun1")
    with col_c2:
        opciones2 = [m for m in sorted(df["municipio"]) if m != mun1]
        mun2 = st.selectbox("Municipio B", opciones2, key="mun2")

    d1 = df[df["municipio"] == mun1].iloc[0]
    d2 = df[df["municipio"] == mun2].iloc[0]

    INDICADORES = ["CoopScore_4", "IVU", "IVEC", "IPD", "IAL"]
    LABELS       = ["CoopScore",   "IVU", "IVEC", "IPD", "IAL"]

    # Métricas lado a lado
    cols = st.columns(len(INDICADORES) + 1)
    cols[0].markdown(f"<div style='padding:30px 0;font-weight:600;color:#7a8099;font-size:12px'>INDICADOR</div>", unsafe_allow_html=True)
    for i, (ind, lbl) in enumerate(zip(INDICADORES, LABELS)):
        delta = d1[ind] - d2[ind]
        cols[i+1].metric(lbl, f"{d1[ind]:.1f}", f"{delta:+.1f} vs {mun2[:8]}")

    # Bar chart comparativo
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        name=mun1, x=LABELS, y=[d1[i] for i in INDICADORES],
        marker_color="#e85d26", text=[f"{d1[i]:.1f}" for i in INDICADORES],
        textposition="outside",
    ))
    fig_bar.add_trace(go.Bar(
        name=mun2, x=LABELS, y=[d2[i] for i in INDICADORES],
        marker_color="#60a5fa", text=[f"{d2[i]:.1f}" for i in INDICADORES],
        textposition="outside",
    ))
    fig_bar.update_layout(
        barmode="group", template="plotly_dark",
        paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
        legend=dict(bgcolor="#1a1f2e", bordercolor="#2a2f3e"),
        yaxis_range=[0, 110], margin=dict(t=20),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # Tabla detalle
    detalle_cols = [
        "municipio", "categoria_coopscore", "poblacion_2025",
        "precio_venta_eur_m2", "precio_alquiler_eur_m2_mes",
        "distancia_capital_km", "distancia_costa_km",
        "area_m2_SUNC", "area_m2_Urbanizable",
    ]
    detalle = df[df["municipio"].isin([mun1, mun2])][detalle_cols].copy()
    detalle["area_m2_SUNC"] = (detalle["area_m2_SUNC"] / 10000).round(1)
    detalle["area_m2_Urbanizable"] = (detalle["area_m2_Urbanizable"] / 10000).round(1)
    detalle.columns = [
        "Municipio", "Categoría", "Población",
        "€/m² venta", "€/m² alquiler",
        "Dist. capital km", "Dist. costa km",
        "SUNC ha", "Urbanizable ha",
    ]
    st.dataframe(detalle.set_index("Municipio").T, use_container_width=True)

# ────────────────────────────────────────────────────────────
# TAB 4 — METODOLOGÍA
# ────────────────────────────────────────────────────────────

with tab4:
    col_m1, col_m2 = st.columns([3, 2])
    with col_m1:
        st.markdown("""
## Metodología CoopScore

El **CoopScore** es un índice compuesto que evalúa el potencial de desarrollo de
vivienda cooperativa en los 174 municipios de la provincia de Granada.

### Índices componentes

| Índice | Descripción | Peso |
|--------|-------------|------|
| **IVU** | Índice de Viabilidad Urbanística | Disponibilidad y capacidad de suelo residencial |
| **IVEC** | Índice de Viabilidad Económica Cooperativa | Condiciones de mercado inmobiliario |
| **IPD** | Índice de Potencial de Demanda | Tamaño poblacional y presión demográfica |
| **IAL** | Índice de Accesibilidad y Localización | Proximidad a Granada capital y costa |

### Categorías estratégicas

- 🟢 **Oportunidad Estratégica** — Combinación favorable de urbanismo y economía
- 🔵 **Potencial Urbanístico** — Suelo disponible, condiciones económicas moderadas
- 🟠 **Potencial Económico** — Mercado activo, suelo más limitado
- 🟣 **Mercado Maduro** — Mercado consolidado, menor margen de crecimiento

### Fuentes de datos

- Catastro Inmobiliario (Ministerio de Hacienda)
- Sistema de Información Urbana (MITMA)
- INE — Padrón Municipal 2025
- Idealista / Fotocasa (precios de mercado)
- IGN — Cartografía de municipios

### Limitaciones

El CoopScore es un indicador orientativo de priorización territorial.
No sustituye al análisis jurídico, técnico o financiero de una promoción cooperativa concreta.
La disponibilidad de datos de precio es parcial (93/174 municipios con dato de venta).
        """)
    with col_m2:
        # Distribución de categorías
        cat_counts = df["categoria_coopscore"].value_counts().reset_index()
        cat_counts.columns = ["Categoría", "Municipios"]
        fig_pie = px.pie(
            cat_counts, names="Categoría", values="Municipios",
            color="Categoría", color_discrete_map=CAT_COLOR,
            hole=0.5, template="plotly_dark",
        )
        fig_pie.update_layout(
            paper_bgcolor="#0e1117",
            legend=dict(bgcolor="#1a1f2e", bordercolor="#2a2f3e"),
            margin=dict(t=20),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

        # Histograma CoopScore
        fig_hist = px.histogram(
            df, x="CoopScore_4", nbins=30,
            color="categoria_coopscore", color_discrete_map=CAT_COLOR,
            labels={"CoopScore_4": "CoopScore", "categoria_coopscore": "Categoría"},
            template="plotly_dark",
        )
        fig_hist.update_layout(
            paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
            legend=dict(bgcolor="#1a1f2e", bordercolor="#2a2f3e"),
            barmode="stack", margin=dict(t=20),
        )
        st.plotly_chart(fig_hist, use_container_width=True)

# ────────────────────────────────────────────────────────────
# TAB 5 — ASESOR PGOU (RAG + Claude + Catastro)
# ────────────────────────────────────────────────────────────

@st.cache_data
def cargar_parcelas():
    path = BASE / "parcelas_granada.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

parcelas_db = cargar_parcelas()

REFCAT_RE = re.compile(r'\b([0-9]{7}[A-Z]{2}[0-9]{4}[A-Z])\b', re.IGNORECASE)

def detectar_refcat(texto: str) -> str | None:
    """Extrae una referencia catastral del texto si existe."""
    m = REFCAT_RE.search(texto.upper())
    return m.group(1) if m else None

def buscar_parcela(refcat: str) -> dict | None:
    """Busca una parcela en la base de datos catastral."""
    return parcelas_db.get(refcat.upper().strip())

def buscar_chunks(consulta: str, n: int = 5) -> list:
    if not chunks:
        return []
    palabras = [p for p in consulta.lower().split() if len(p) >= 4]
    terminos_clave = {
        "altura", "planta", "edificabilidad", "ocupacion", "retranqueo",
        "residencial", "industrial", "terciario", "comercial", "vivienda",
        "unifamiliar", "plurifamiliar", "cooperativa", "parcela", "suelo",
        "urbanizable", "permitido", "prohibido", "licencia", "zona",
    }
    scored = []
    for chunk in chunks:
        texto = (chunk["titulo"] + " " + chunk["contenido"]).lower()
        score = sum(
            len(re.findall(re.escape(p), texto)) * (2 if p in chunk["titulo"].lower() else 1)
            for p in palabras
        ) + sum(0.5 for t in terminos_clave if t in texto)
        scored.append({**chunk, "score": score})
    return sorted(scored, key=lambda x: x["score"], reverse=True)[:n]

def get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            pass
    return key

def responder(pregunta: str, historial: list, parcela_ctx: dict | None = None) -> tuple[str, list]:
    """Genera respuesta con RAG. Si hay contexto de parcela, lo incorpora."""
    found = buscar_chunks(pregunta)
    contexto_norm = (
        "\n\n---\n\n".join(f"## {c['titulo']}\n{c['contenido']}" for c in found)
        if found else "No se encontraron artículos específicos."
    )

    # Contexto de parcela catastral si existe
    ctx_parcela = ""
    if parcela_ctx:
        ctx_parcela = (
            f"\n\nCONTEXTO DE PARCELA (Catastro Inmobiliario):\n"
            f"- Referencia catastral: {parcela_ctx['refcat']}\n"
            f"- Tipo de suelo: {parcela_ctx['tipo']}\n"
            f"- Superficie: {parcela_ctx['area_m2']} m²\n"
            f"- Uso catastral: {parcela_ctx.get('uso', 'No determinado')}\n"
            f"- Masa catastral: {parcela_ctx['masa']}\n"
            f"- Número de parcela: {parcela_ctx['parcela']}\n"
            f"Usa estos datos para contextualizar la respuesta urbanística.\n"
        )

    system = (
        "Eres un asesor experto en urbanismo especializado en el Plan General de "
        "Ordenación Urbanística (PGOU) de Granada (aprobado 2001, adaptado a LOUA 2009, "
        "comentado por COAATGR junio 2023). Tienes acceso a 20.841 referencias catastrales "
        "del municipio de Granada.\n"
        "Cuando tengas datos de una parcela concreta, úsalos para dar una respuesta más "
        "precisa sobre esa parcela específica. Cita artículos relevantes. "
        "Cuando des parámetros concretos (alturas, edificabilidades, retranqueos) "
        "indícalos explícitamente. Si necesitas la zonificación PGOU (zona R-1, R-2, etc.) "
        "para ser más preciso, indícalo. Responde en español de forma clara y estructurada."
        f"{ctx_parcela}\n\n"
        f"NORMATIVA RECUPERADA:\n{contexto_norm}"
    )

    api_key = get_api_key()
    if not api_key:
        return "⚠️ Configura `ANTHROPIC_API_KEY` en `.streamlit/secrets.toml` para activar el asesor.", []

    try:
        client = anthropic.Anthropic(api_key=api_key)
        msgs = historial + [{"role": "user", "content": pregunta}]
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=900,
            system=system,
            messages=msgs,
        )
        return resp.content[0].text, [c["titulo"] for c in found]
    except Exception as e:
        return f"Error al conectar con Claude: {e}", []

# ── Estado del chat ───────────────────────────────────────────
if "chat_history"   not in st.session_state: st.session_state.chat_history   = []
if "api_history"    not in st.session_state: st.session_state.api_history    = []
if "parcela_activa" not in st.session_state: st.session_state.parcela_activa = None
if "esperando_ref"  not in st.session_state: st.session_state.esperando_ref  = False

with tab5:

    # ── Header ────────────────────────────────────────────────
    st.markdown("""
    <div style="background:#1a1f2e;border:1px solid #2a3350;border-radius:10px;
                padding:16px 20px;margin-bottom:16px">
        <span style="font-family:'Space Grotesk',sans-serif;font-size:18px;
                     font-weight:700;color:#e8e9ed">
            🤖 Asesor de Normativa Urbanística
        </span>
        <span class="beta-badge" style="margin-left:10px">BETA</span>
        <p style="color:#7a8099;font-size:13px;margin:8px 0 0">
            Consulta sobre el <strong style="color:#e8e9ed">PGOU de Granada</strong>
            (Normativa 2001 · LOUA 2009 · COAATGR 2023) con acceso a
            <strong style="color:#e85d26">20.841 parcelas catastrales</strong>.
            Si conoces la referencia catastral, la respuesta será mucho más precisa.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Panel parcela activa ──────────────────────────────────
    col_chat, col_parcela = st.columns([3, 1])

    with col_parcela:
        st.markdown("##### 📍 Parcela activa")

        # Buscador manual de referencia catastral
        refcat_input = st.text_input(
            "Referencia catastral",
            placeholder="Ej: 7661708VG4176B",
            key="refcat_manual",
            help="14 caracteres: 7 dígitos + 2 letras + 4 dígitos + 1 letra",
        )
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("🔍 Buscar", key="btn_buscar_ref"):
                ref = refcat_input.strip().upper()
                p = buscar_parcela(ref)
                if p:
                    st.session_state.parcela_activa = p
                    st.session_state.esperando_ref  = False
                    # Añadir mensaje automático al chat
                    msg_auto = f"He localizado la referencia catastral **{ref}**. ¿Qué quieres saber sobre esta parcela?"
                    st.session_state.chat_history.append({"role": "assistant", "content": msg_auto, "sources": []})
                    st.session_state.api_history.append({"role": "assistant", "content": msg_auto})
                    st.rerun()
                else:
                    st.error(f"Ref. `{ref}` no encontrada")
        with col_b2:
            if st.button("✖ Quitar", key="btn_quitar_ref"):
                st.session_state.parcela_activa = None
                st.rerun()

        # Mostrar datos de parcela activa
        if st.session_state.parcela_activa:
            p = st.session_state.parcela_activa
            st.markdown(f"""
            <div style="background:#0f1420;border:1px solid #2a3350;border-radius:8px;
                        padding:12px;margin-top:8px">
                <div style="color:#e85d26;font-size:11px;font-weight:700;
                            letter-spacing:1px;margin-bottom:8px">PARCELA CARGADA</div>
            """, unsafe_allow_html=True)
            ficha_p = {
                "Ref.": p["refcat"],
                "Tipo": p["tipo"],
                "Área": f"{p['area_m2']} m²",
                "Uso catastral": p.get("uso", "—"),
                "Masa": p["masa"],
                "Parcela nº": p["parcela"],
            }
            for k, v in ficha_p.items():
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;padding:4px 0;
                            border-bottom:1px solid #1e2535;font-size:11px">
                    <span style="color:#7a8099">{k}</span>
                    <span style="color:#e8e9ed;font-weight:500;font-family:monospace;
                                 font-size:10px">{v}</span>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            st.caption("💡 El asesor usará estos datos en todas las respuestas")
        else:
            st.markdown("""
            <div style="background:#0f1420;border:1px dashed #2a3350;border-radius:8px;
                        padding:16px;text-align:center;color:#4a5070;font-size:12px;margin-top:8px">
                Sin parcela cargada.<br>Las consultas serán sobre normativa general.
            </div>
            """, unsafe_allow_html=True)

    # ── Chat principal ────────────────────────────────────────
    with col_chat:

        # Mensaje de bienvenida + pregunta inicial si no hay historial
        if not st.session_state.chat_history:
            bienvenida = (
                "Hola, soy tu asesor de normativa urbanística del **PGOU de Granada**. "
                "Puedo ayudarte con usos del suelo, alturas, edificabilidades, retranqueos y más.\n\n"
                "Para darte una respuesta más precisa sobre una parcela concreta: "
                "**¿conoces la referencia catastral?** Puedes introducirla en el panel de la derecha "
                "o escribirla directamente aquí. Si no la tienes, puedo responder sobre normativa general."
            )
            st.session_state.chat_history.append({"role": "assistant", "content": bienvenida, "sources": []})
            st.session_state.api_history.append({"role": "assistant", "content": bienvenida})

        # Sugerencias rápidas (solo al inicio con bienvenida)
        if len(st.session_state.chat_history) == 1:
            st.markdown("**Consultas frecuentes:**")
            sugerencias = [
                "¿Cuál es la altura máxima para vivienda unifamiliar?",
                "¿Qué usos están permitidos en suelo no urbanizable?",
                "¿Cuál es la edificabilidad en zona residencial R-3?",
                "¿Puedo instalar un local comercial en planta baja?",
                "¿Qué retranqueos exige el PGOU en zona industrial?",
                "¿Qué es el suelo urbanizable programado?",
            ]
            cols_s = st.columns(3)
            for i, s in enumerate(sugerencias):
                with cols_s[i % 3]:
                    if st.button(s, key=f"sug_{i}"):
                        st.session_state._pregunta_rapida = s
                        st.rerun()

        # Procesar pregunta rápida
        if hasattr(st.session_state, "_pregunta_rapida"):
            preg = st.session_state._pregunta_rapida
            del st.session_state._pregunta_rapida
            # Comprobar si contiene refcat
            ref_detectada = detectar_refcat(preg)
            if ref_detectada:
                p = buscar_parcela(ref_detectada)
                if p:
                    st.session_state.parcela_activa = p
            respuesta, fuentes = responder(preg, st.session_state.api_history, st.session_state.parcela_activa)
            st.session_state.chat_history.append({"role": "user",      "content": preg,      "sources": []})
            st.session_state.chat_history.append({"role": "assistant", "content": respuesta, "sources": fuentes})
            st.session_state.api_history.append({"role": "user",      "content": preg})
            st.session_state.api_history.append({"role": "assistant", "content": respuesta})

        # Render mensajes
        chat_box = st.container(height=420)
        with chat_box:
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f'<div class="chat-user">{msg["content"]}</div>', unsafe_allow_html=True)
                else:
                    fuentes_html = ""
                    if msg.get("sources"):
                        arts = " · ".join(
                            s.replace("Artículo ", "Art. ").split(".")[0] + "."
                            for s in msg["sources"][:3]
                        )
                        fuentes_html = f'<div class="chat-sources">📄 {arts}</div>'
                    st.markdown(
                        f'<div class="chat-bot">{msg["content"]}{fuentes_html}</div>',
                        unsafe_allow_html=True,
                    )

        # Input
        col_inp, col_btn, col_clear = st.columns([6, 1, 1])
        with col_inp:
            placeholder = (
                f"Pregunta sobre la parcela {st.session_state.parcela_activa['refcat']}..."
                if st.session_state.parcela_activa
                else "Escribe tu consulta o una referencia catastral (ej: 7661708VG4176B)..."
            )
            pregunta = st.text_input(
                "Consulta",
                placeholder=placeholder,
                label_visibility="collapsed",
                key="input_pgou",
            )
        with col_btn:
            enviar = st.button("Enviar", key="btn_enviar")
        with col_clear:
            if st.button("🗑️", key="btn_clear", help="Limpiar conversación"):
                st.session_state.chat_history   = []
                st.session_state.api_history    = []
                st.session_state.parcela_activa = None
                st.session_state.esperando_ref  = False
                st.rerun()

        if enviar and pregunta.strip():
            preg = pregunta.strip()
            # Detectar refcat en el mensaje escrito
            ref_detectada = detectar_refcat(preg)
            if ref_detectada:
                p = buscar_parcela(ref_detectada)
                if p and not st.session_state.parcela_activa:
                    st.session_state.parcela_activa = p
                    st.toast(f"✅ Parcela {ref_detectada} cargada automáticamente", icon="📍")
                elif not p:
                    st.toast(f"⚠️ Ref. {ref_detectada} no encontrada en la base de datos", icon="❌")

            respuesta, fuentes = responder(preg, st.session_state.api_history, st.session_state.parcela_activa)
            st.session_state.chat_history.append({"role": "user",      "content": preg,      "sources": []})
            st.session_state.chat_history.append({"role": "assistant", "content": respuesta, "sources": fuentes})
            st.session_state.api_history.append({"role": "user",      "content": preg})
            st.session_state.api_history.append({"role": "assistant", "content": respuesta})
            st.rerun()

    # ── API key info ──────────────────────────────────────────
    if not get_api_key():
        st.info(
            "💡 Para activar el asesor añade tu API key en `.streamlit/secrets.toml`:\n\n"
            "```toml\nANTHROPIC_API_KEY = 'sk-ant-...'\n```",
            icon="🔑",
        )
