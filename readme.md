# 🏘️ CoopScore Granada

## Inteligencia territorial para la identificación de oportunidades de vivienda cooperativa

CoopScore Granada es una plataforma de análisis territorial basada en Data Science, GIS e Inteligencia Artificial que permite identificar municipios con potencial para el desarrollo de vivienda cooperativa en la provincia de Granada.

### Principales funcionalidades

✅ Mapa interactivo de los 174 municipios de Granada

✅ Índice territorial propio (CoopScore)

✅ Clasificación estratégica municipal

✅ Comparador de municipios

✅ Explainable AI (SHAP)

✅ Asesor urbanístico basado en IA y PGOU de Granada

---

## Capturas

### Mapa interactivo

![Mapa CoopScore](docs/mapa.png)

### Comparador municipal

![Comparador](docs/comparador.png)

### Asesor urbanístico

![Asesor PGOU](docs/pgou.png)

---

## Arquitectura

ETL → Dataset Maestro → CoopScore → Explainability → Streamlit → Asesor PGOU

---

## Tecnologías

- Python
- Pandas
- GeoPandas
- Scikit-Learn
- SHAP
- Plotly
- Folium
- Streamlit
- Claude API
- RAG

---

## Instalación

```bash
git clone ...
cd coopscore-granada

pip install -r requirements.txt