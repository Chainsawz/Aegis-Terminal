import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen
import requests
from google import genai
import json
from datetime import datetime, timedelta

# --- SETUP INICIAL ---
st.set_page_config(page_title="AEGIS HARD DEBUG v4.6", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    .debug-console { background: #000; border: 1px solid #3b82f6; padding: 10px; font-family: 'JetBrains Mono'; font-size: 11px; color: #00ff41; height: 150px; overflow-y: scroll; margin-bottom: 20px; }
    .intel-card { background: rgba(30, 41, 59, 0.7); border-left: 4px solid #3b82f6; padding: 12px; border-radius: 8px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- CREDENCIALES ---
try:
    client = genai.Client(api_key=st.secrets["gemini_api_key"])
    NEWS_API_KEY = st.secrets["news_api_key"]
except Exception as e:
    st.error(f"FATAL ERROR: Keys no configuradas. {e}")
    st.stop()

# --- MEMORIA DE SESIÓN ---
if 'intel_memory' not in st.session_state:
    st.session_state.intel_memory = []
if 'debug_logs' not in st.session_state:
    st.session_state.debug_logs = []

def add_log(msg):
    st.session_state.debug_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# --- MOTOR DE BÚSQUEDA SIMPLIFICADO ---
def fetch_raw_news():
    # Usamos una query súper simple para asegurar que NewsAPI devuelva ALGO
    query = "military OR war" 
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&pageSize=10&apiKey={NEWS_API_KEY}'
    add_log(f"Iniciando petición a NewsAPI...")
    try:
        r = requests.get(url)
        if r.status_code == 200:
            articles = r.json().get('articles', [])
            add_log(f"NewsAPI respondió con {len(articles)} artículos.")
            return articles
        else:
            add_log(f"ERROR NewsAPI: Código {r.status_code}")
            return []
    except Exception as e:
        add_log(f"EXCEPCIÓN en fetch: {str(e)}")
        return []

# --- ANALIZADOR IA ---
def analyze_with_gemini(article):
    text = f"Title: {article['title']}. Desc: {article['description']}"
    prompt = f"Extract military event data from this text: '{text}'. Return ONLY JSON: {{\"is_mil\":bool, \"threat\":1-10, \"lat\":float, \"lon\":float, \"loc\":\"City\", \"sum\":\"Summary\"}}. If not military, is_mil:false."
    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        res_text = response.text.strip().replace('```json', '').replace('```', '')
        data = json.loads(res_text)
        add_log(f"IA analizó: {article['title'][:30]}... -> MILITAR: {data['is_mil']}")
        return data
    except Exception as e:
        add_log(f"IA FALLÓ en: {article['title'][:30]}... Error: {str(e)}")
        return {"is_mil": False}

# --- UI ---
st.title("◤ AEGIS_HARD_DEBUG_v4.6")

# Consola de Debug en la parte superior
with st.expander("🖥️ CONSOLA DE SISTEMA (LOGS)", expanded=True):
    for log in reversed(st.session_state.debug_logs[-10:]):
        st.write(log)

# Botón de Escaneo Manual
if st.button("⚡ LANZAR ESCANEO FORZADO"):
    raw = fetch_raw_news()
    if raw:
        st.toast("Procesando inteligencia...")
        found_any = False
        for art in raw:
            intel = analyze_with_gemini(art)
            if intel.get("is_mil"):
                found_any = True
                # Evitar duplicados
                if art['url'] not in [x['url'] for x in st.session_state.intel_memory]:
                    st.session_state.intel_memory.append({**art, **intel})
        if not found_any:
            add_log("CRÍTICO: La IA descartó TODOS los artículos recibidos.")
    st.rerun()

# Layout
col_map, col_feed = st.columns([2.5, 1])

with col_map:
    m = folium.Map(location=[20, 0], zoom_start=2.2, tiles="CartoDB dark_matter", no_wrap=True)
    marker_cluster = MarkerCluster().add_to(m)
    
    for item in st.session_state.intel_memory:
        color = 'red' if item['threat'] >= 8 else 'orange'
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=f"<b>{item['loc']}</b><br>{item['sum']}",
            icon=folium.Icon(color=color, icon='warning', prefix='fa')
        ).add_to(marker_cluster)
    
    st_folium(m, width="100%", height=600)

with col_feed:
    st.markdown("### 📥 INTEL_MEMORY")
    if not st.session_state.intel_memory:
        st.write("No hay datos en memoria. Lanza un escaneo forzado.")
    for item in sorted(st.session_state.intel_memory, key=lambda x: x['threat'], reverse=True):
        st.markdown(f"""
            <div class="intel-card">
                <small>[{item['loc'].upper()}] - LVL {item['threat']}</small><br>
                <strong>{item['title']}</strong>
            </div>
            """, unsafe_allow_html=True)
