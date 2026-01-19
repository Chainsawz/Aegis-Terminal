import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen
import requests
from google import genai
import json
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(
    page_title="AEGIS TACTICAL v5.4", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS: PROTOCOLO "STELLAR GHOST" (ELIMINACIÓN DE RUIDO VISUAL) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono&display=swap');
    
    .stApp { background: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    
    /* ELIMINAR CUADROS BLANCOS: Forzamos el contenedor a negro puro */
    iframe { 
        border-radius: 12px; 
        border: 1px solid #1e293b; 
        background-color: #000000 !important; 
    }
    
    .intel-card {
        background: rgba(15, 23, 42, 0.95);
        border: 1px solid #1e293b;
        border-left: 4px solid #3b82f6;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
        backdrop-filter: blur(10px);
    }
    .critical { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.1); }
    [data-testid="stMetric"] { background: #0f172a; border: 1px solid #1e293b; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN DE SISTEMAS ---
try:
    client = genai.Client(api_key=st.secrets["gemini_api_key"])
    NEWS_API_KEY = st.secrets["news_api_key"]
except Exception as e:
    st.error(f"🚨 FALLO DE ENLACE: {e}")
    st.stop()

# --- BÚFER DE MEMORIA (PERSISTENCIA 24H) ---
if 'memory' not in st.session_state:
    st.session_state.memory = []
if 'raw_feed' not in st.session_state:
    st.session_state.raw_feed = []

def update_memory(new_intel):
    existing_urls = {item['url'] for item in st.session_state.memory}
    for item in new_intel:
        if item['url'] not in existing_urls:
            item['timestamp'] = datetime.now()
            st.session_state.memory.append(item)
    # Purgar datos obsoletos (>24h)
    cutoff = datetime.now() - timedelta(hours=24)
    st.session_state.memory = [i for i in st.session_state.memory if i['timestamp'] > cutoff]

# --- INTELIGENCIA POR LOTES (PROTECCIÓN DE CUOTA) ---
def analyze_batch_intel(articles):
    if not articles: return []
    news_list = [{"id": i, "t": a['title']} for i, a in enumerate(articles)]
    prompt = f"Identify military events in this JSON: {json.dumps(news_list)}. Return ONLY a JSON list: [{{'id':int, 'threat':1-10, 'lat':float, 'lon':float, 'loc':'City', 'sum':'brief text'}}]"
    try:
        # Usamos 1.5 Flash para asegurar estabilidad de respuesta
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        res_text = response.text.strip().replace('```json', '').replace('```', '')
        analyzed = json.loads(res_text)
        return [{**articles[r['id']], **r} for r in analyzed]
    except Exception as e:
        st.sidebar.warning(f"⚠️ IA EN SOBRECARGA: {str(e)[:40]}")
        return []

def fetch_news():
    query = "(military OR war OR missile OR 'border conflict')"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=15&apiKey={NEWS_API_KEY}'
    try:
        r = requests.get(url)
        return r.json().get('articles', []) if r.status_code == 200 else []
    except: return []

# --- INTERFAZ DE COMANDO ---
st.markdown("<h1 style='color:#3b82f6;'>◤ AEGIS_STELLAR_GHOST_v5.4</h1>", unsafe_allow_html=True)

# Sidebar
st.sidebar.header("🕹️ OPERACIONES")
if st.sidebar.button("⚡ ESCANEO GLOBAL"):
    with st.spinner("Interceptando comunicaciones..."):
        raw = fetch_news()
        st.session_state.raw_feed = raw
        if raw:
            analyzed = analyze_batch_intel(raw)
