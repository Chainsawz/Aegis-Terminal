import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen
import requests
from google import genai
import json
from datetime import datetime

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(
    page_title="AEGIS TACTICAL v4.2", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS: ESTÉTICA DE CONTRATISTA MILITAR PRIVADO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono&display=swap');
    
    .stApp {
        background: radial-gradient(circle, #0f172a 0%, #020617 100%);
        color: #f1f5f9;
        font-family: 'Inter', sans-serif;
    }
    
    /* Tarjetas de Inteligencia */
    .intel-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid #334155;
        border-left: 4px solid #3b82f6;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        backdrop-filter: blur(10px);
    }
    .critical { border-left-color: #ef4444; box-shadow: 0 0 15px rgba(239, 68, 68, 0.2); }
    .high { border-left-color: #f97316; }

    /* Estilo para métricas */
    [data-testid="stMetric"] {
        background: #1e293b;
        border: 1px solid #334155;
        padding: 20px;
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN CON EL BÚNKER (API KEYS) ---
try:
    # Nuevo cliente de Google Gen AI (Estándar 2026)
    client = genai.Client(api_key=st.secrets["gemini_api_key"])
    NEWS_API_KEY = st.secrets["news_api_key"]
except Exception as e:
    st.error("🚨 FALLO DE AUTENTICACIÓN: Verifica los Secrets en Streamlit.")
    st.stop()

# --- CEREBRO: ANÁLISIS TÁCTICO POR IA ---
def analizar_con_ia(titulo, descripcion):
    prompt = f"""
    Actúa como analista OSINT militar. Analiza: "{titulo}. {descripcion}"
    Responde estrictamente en JSON:
    {{
        "is_mil": boolean,
        "threat": int(1-10),
        "lat": float,
        "lon": float,
        "location": "Nombre del lugar",
        "summary": "Resumen técnico de 1 frase"
    }}
    Si no es un evento militar o de conflicto, pon "is_mil": false.
    """
    try:
        # Usando Gemini 2.0 Flash para máxima velocidad
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt
        )
        # Limpieza de markdown en la respuesta
        res_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(res_text)
    except:
        return {"is_mil": False}

# --- SUMINISTRO: OBTENCIÓN DE NOTICIAS ---
@st.cache_data(ttl=600)
def fetch_global_intel():
    # Buscamos términos bélicos clave
    query = "(war OR military OR missile OR 'border clash' OR invasion OR 'air strike')"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=15&apiKey={NEWS_API_KEY}'
    try:
        r = requests.get(url)
        return r.json().get('articles', [])
    except:
        return []

# --- PANEL DE CONTROL ---
st.markdown("<h1 style='color:#3b82f6;'>◤ AEGIS_TACTICAL_COMMAND_v4.2</h1>", unsafe_allow_html=True)
st.sidebar.image("
