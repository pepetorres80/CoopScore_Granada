"""
normativa_pgou.py
─────────────────────────────────────────────────────────────────────────────
Módulo de consulta de la Normativa Urbanística del PGOU de Granada.
Extrae fragmentos relevantes por búsqueda de palabras clave y genera
respuestas mediante la API de Claude (Anthropic).

Uso en Streamlit:
    from normativa_pgou import buscar_normativa, consultar_pgou, analizar_parcela

Archivos necesarios en el mismo directorio (o indicar ruta):
    - normativa_chunks.json   → 854 artículos del PGOU de Granada
    - parcelas_granada.json   → 20.841 parcelas catastrales de Granada

Dependencias:
    pip install anthropic streamlit
─────────────────────────────────────────────────────────────────────────────
"""

import json
import os
import re
from pathlib import Path
from typing import Optional

try:
    import anthropic
except ImportError:
    raise ImportError("Instala anthropic: pip install anthropic")


# ─── Configuración ────────────────────────────────────────────────────────────

# Por defecto los JSON se buscan junto a este archivo.
# Puedes sobreescribir con variables de entorno:
#   PGOU_CHUNKS_PATH=/ruta/normativa_chunks.json
#   PGOU_PARCELAS_PATH=/ruta/parcelas_granada.json
_BASE_DIR = Path(__file__).parent
CHUNKS_PATH   = Path(os.getenv("PGOU_CHUNKS_PATH",   str(_BASE_DIR / "normativa_chunks.json")))
PARCELAS_PATH = Path(os.getenv("PGOU_PARCELAS_PATH", str(_BASE_DIR / "parcelas_granada.json")))

# La API key se lee de la variable de entorno ANTHROPIC_API_KEY
# (Streamlit Secrets también funciona si la defines ahí)
MODELO     = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024
N_CHUNKS   = 5   # Número de artículos a recuperar por consulta


# ─── Carga de datos (cacheada en módulo) ──────────────────────────────────────

_chunks: Optional[list] = None
_parcelas: Optional[dict] = None


def _cargar_chunks() -> list:
    global _chunks
    if _chunks is None:
        if not CHUNKS_PATH.exists():
            raise FileNotFoundError(
                f"No se encuentra normativa_chunks.json en {CHUNKS_PATH}\n"
                "Ajusta PGOU_CHUNKS_PATH o coloca el archivo junto a normativa_pgou.py"
            )
        with open(CHUNKS_PATH, encoding="utf-8") as f:
            _chunks = json.load(f)
    return _chunks


def _cargar_parcelas() -> dict:
    global _parcelas
    if _parcelas is None:
        if not PARCELAS_PATH.exists():
            raise FileNotFoundError(
                f"No se encuentra parcelas_granada.json en {PARCELAS_PATH}\n"
                "Ajusta PGOU_PARCELAS_PATH o coloca el archivo junto a normativa_pgou.py"
            )
        with open(PARCELAS_PATH, encoding="utf-8") as f:
            _parcelas = json.load(f)
    return _parcelas


# ─── Búsqueda de artículos relevantes ─────────────────────────────────────────

def buscar_normativa(consulta: str, n: int = N_CHUNKS) -> list:
    """
    Busca los artículos más relevantes para una consulta dada.

    Estrategia: puntuación por frecuencia de palabras clave (≥4 chars)
    en título + contenido, con bonus por términos urbanísticos clave.

    Parámetros
    ----------
    consulta : str
        Pregunta o texto libre del usuario.
    n : int
        Número máximo de chunks a devolver.

    Devuelve
    --------
    list[dict] con campos: id, titulo, contenido, score
    """
    chunks = _cargar_chunks()
    palabras = [p for p in consulta.lower().split() if len(p) >= 4]

    terminos_clave = {
        "altura", "planta", "edificabilidad", "ocupacion", "retranqueo",
        "residencial", "industrial", "terciario", "comercial", "vivienda",
        "unifamiliar", "plurifamiliar", "cooperativa", "parcela", "suelo",
        "urbanizable", "urbanizado", "equipamiento", "zona", "uso", "permitido",
        "prohibido", "licencia", "obras", "reforma", "ampliacion", "segregacion",
    }

    scored = []
    for chunk in chunks:
        texto = (chunk["titulo"] + " " + chunk["contenido"]).lower()
        score = 0
        for p in palabras:
            ocurrencias = len(re.findall(re.escape(p), texto))
            bonus = 2 if p in chunk["titulo"].lower() else 1
            score += ocurrencias * bonus
        for t in terminos_clave:
            if t in texto:
                score += 0.5
        scored.append({**chunk, "score": score})

    resultado = sorted(scored, key=lambda x: x["score"], reverse=True)
    return [c for c in resultado[:n] if c["score"] > 0]


# ─── Cliente Anthropic ────────────────────────────────────────────────────────

def _get_client() -> "anthropic.Anthropic":
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("ANTHROPIC_API_KEY")
        except Exception:
            pass
    if not api_key:
        raise EnvironmentError(
            "No se encontró ANTHROPIC_API_KEY.\n"
            "Defínela como variable de entorno o en .streamlit/secrets.toml:\n"
            "  ANTHROPIC_API_KEY = 'sk-ant-...'"
        )
    return anthropic.Anthropic(api_key=api_key)


# ─── Consulta principal al PGOU ───────────────────────────────────────────────

def consultar_pgou(
    pregunta: str,
    municipio: str = "Granada",
    historial: Optional[list] = None,
) -> dict:
    """
    Responde una pregunta sobre la normativa urbanística del PGOU.

    Parámetros
    ----------
    pregunta : str
        Pregunta del usuario en lenguaje natural.
    municipio : str
        Municipio de referencia (por defecto Granada).
    historial : list[dict], opcional
        Mensajes previos [{"role": "user"|"assistant", "content": "..."}]
        para mantener el contexto de la conversación.

    Devuelve
    --------
    dict con:
        - respuesta (str): texto generado
        - articulos (list[str]): títulos de los artículos usados
        - chunks (list[dict]): chunks completos recuperados
    """
    chunks = buscar_normativa(pregunta)

    if chunks:
        contexto = "\n\n---\n\n".join(
            f"## {c['titulo']}\n{c['contenido']}" for c in chunks
        )
    else:
        contexto = "No se encontraron artículos específicos para esta consulta."

    system_prompt = (
        f"Eres un asesor experto en urbanismo especializado en el Plan General de "
        f"Ordenación Urbanística (PGOU) de {municipio} "
        f"(aprobado 2001, adaptado a LOUA 2009, comentado por COAATGR junio 2023).\n\n"
        "Respondes consultas urbanísticas de forma clara y precisa, citando artículos "
        "cuando los tengas disponibles. Cuando des parámetros concretos (alturas, "
        "edificabilidades, retranqueos) indícalos explícitamente. Si la consulta requiere "
        "información de zonificación no disponible en la normativa textual, indícalo.\n"
        "Responde siempre en español.\n\n"
        f"NORMATIVA RECUPERADA:\n{contexto}"
    )

    mensajes = list(historial) if historial else []
    mensajes.append({"role": "user", "content": pregunta})

    cliente = _get_client()
    respuesta = cliente.messages.create(
        model=MODELO,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=mensajes,
    )

    return {
        "respuesta": respuesta.content[0].text,
        "articulos": [c["titulo"] for c in chunks],
        "chunks": chunks,
    }


# ─── Análisis de parcela catastral ────────────────────────────────────────────

def analizar_parcela(refcat: str) -> dict:
    """
    Dado una referencia catastral, devuelve datos y análisis urbanístico.

    Parámetros
    ----------
    refcat : str
        Referencia catastral (ej: '7661708VG4176B').

    Devuelve
    --------
    dict con:
        - encontrada (bool)
        - parcela (dict | None): datos catastrales
        - analisis (str): análisis generado
        - articulos (list[str]): artículos consultados
        - error (str | None)
    """
    parcelas = _cargar_parcelas()
    ref = refcat.strip().upper()
    parcela = parcelas.get(ref)

    if not parcela:
        return {
            "encontrada": False,
            "parcela": None,
            "analisis": "",
            "articulos": [],
            "error": f"Referencia catastral '{ref}' no encontrada en la base de datos.",
        }

    prompt = (
        f"Analiza urbanísticamente la siguiente parcela del municipio de Granada "
        f"según el PGOU vigente:\n\n"
        f"- Referencia catastral: {parcela['refcat']}\n"
        f"- Tipo de suelo (catastral): {parcela['tipo']}\n"
        f"- Superficie: {parcela['area_m2']} m²\n"
        f"- Municipio: {parcela['municipio']}\n"
        f"- Masa catastral: {parcela['masa']}\n\n"
        "Por favor:\n"
        "1. Explica qué significa cada dato catastral.\n"
        "2. Indica la clasificación urbanística probable según el PGOU.\n"
        "3. Explica qué información adicional sería necesaria para saber exactamente "
        "qué se puede construir.\n"
        "4. Orienta sobre usos y parámetros edificatorios habituales para este tipo "
        "de suelo en Granada.\n"
        "5. Comenta brevemente su idoneidad para vivienda cooperativa."
    )

    resultado = consultar_pgou(prompt)

    return {
        "encontrada": True,
        "parcela": parcela,
        "analisis": resultado["respuesta"],
        "articulos": resultado["articulos"],
        "error": None,
    }


# ─── Análisis de viabilidad cooperativa (integración CoopScore) ──────────────

def analizar_viabilidad_cooperativa(
    municipio: str,
    coopscore: float,
    ivu: float,
    ivec: float,
    perfil: str,
    poblacion: int,
    precio_m2: float,
    superficie_residencial_m2: float,
    suelo_por_habitante: float,
    distancia_capital_km: float,
) -> str:
    """
    Genera un análisis narrativo de viabilidad para vivienda cooperativa
    combinando los datos del CoopScore con el conocimiento del PGOU.

    Diseñado para integrarse directamente en el Streamlit del TFM.

    Devuelve
    --------
    str con el análisis generado.
    """
    sup_ha = superficie_residencial_m2 / 10_000

    prompt = (
        f"Analiza la viabilidad para el desarrollo de vivienda cooperativa "
        f"en el municipio de {municipio} (provincia de Granada) con estos indicadores:\n\n"
        f"**Indicadores CoopScore:**\n"
        f"- CoopScore v6: {coopscore:.2f} / 100\n"
        f"- IVU (Índice de Viabilidad Urbanística): {ivu:.2f}\n"
        f"- IVEC (Índice de Viabilidad Económica Cooperativa): {ivec:.2f}\n"
        f"- Perfil municipal: {perfil}\n\n"
        f"**Datos municipales:**\n"
        f"- Población (2025): {poblacion:,} habitantes\n"
        f"- Precio de venta estimado: {precio_m2:.0f} €/m²\n"
        f"- Superficie residencial disponible: {sup_ha:.1f} ha ({superficie_residencial_m2:,.0f} m²)\n"
        f"- Suelo disponible por habitante: {suelo_por_habitante:.1f} m²/hab\n"
        f"- Distancia a Granada capital: {distancia_capital_km:.1f} km\n\n"
        "Por favor proporciona:\n"
        "1. Valoración global de la oportunidad cooperativa (2-3 frases).\n"
        "2. Fortalezas principales del municipio para este tipo de promoción.\n"
        "3. Riesgos o limitaciones a considerar.\n"
        "4. Recomendación sobre el siguiente paso urbanístico (qué información del "
        "PGOU local habría que consultar para avanzar).\n\n"
        "Sé concreto y práctico. Extensión: 200-300 palabras."
    )

    resultado = consultar_pgou(prompt, municipio=municipio)
    return resultado["respuesta"]


# ─── Test desde línea de comandos ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("TEST normativa_pgou.py")
    print("=" * 60)

    print("\n[1] Búsqueda: 'altura máxima vivienda unifamiliar'")
    resultados = buscar_normativa("altura máxima vivienda unifamiliar", n=3)
    for r in resultados:
        print(f"  • {r['titulo']} (score: {r['score']:.1f})")

    print("\n[2] Consulta PGOU (requiere ANTHROPIC_API_KEY)")
    try:
        resp = consultar_pgou("¿Cuál es la edificabilidad en zona residencial?")
        print(f"  Artículos: {resp['articulos'][:2]}")
        print(f"  Respuesta: {resp['respuesta'][:300]}...")
    except EnvironmentError as e:
        print(f"  [Sin API key configurada] {e}")

    print("\nOK — módulo listo.")
