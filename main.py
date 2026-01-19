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
    page_title="AEGIS TACTICAL v4.2.1", 
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
    client = genai.Client(api_key=st.secrets["gemini_api_key"])
    NEWS_API_KEY = st.secrets["news_api_key"]
except Exception as e:
    st.error("🚨 FALLO DE AUTENTICACIÓN: Verifica los Secrets en Streamlit.")
    st.stop()

# --- CEREBRO: ANÁLISIS TÁCTICO POR IA ---
def analizar_con_ia(titulo, descripcion):
    prompt = f"Analiza: {titulo}. {descripcion}. Responde SOLO JSON: {{\"is_mil\":bool, \"threat\":int, \"lat\":float, \"lon\":float, \"location\":\"City\", \"summary\":\"short text\"}}"
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt
        )
        res_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(res_text)
    except:
        return {"is_mil": False}

# --- SUMINISTRO: OBTENCIÓN DE NOTICIAS ---
@st.cache_data(ttl=600)
def fetch_global_intel():
    query = "(war OR military OR missile OR 'air strike')"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=15&apiKey={NEWS_API_KEY}'
    try:
        r = requests.get(url)
        return r.json().get('articles', [])
    except:
        return []

# --- PANEL DE CONTROL ---
st.markdown("<h1 style='color:#3b82f6;'>◤ AEGIS_TACTICAL_COMMAND_v4.2.1</h1>", unsafe_allow_html=True)

# Sidebar corregida para evitar el SyntaxError
st.sidebar.markdown("### 🛰️ RADAR_SYSTEM")
st.sidebar.success("STATUS: ONLINE")
st.sidebar.info(f"SYNC: {datetime.now().strftime('%H:%M:%S')}")

if st.sidebar.button("🔄 REFRESH_SCAN"):
    st.cache_data.clear()
    st.rerun()

# Métricas
m1, m2, m3 = st.columns(3)
m1.metric("THREAT_LEVEL", "ELEVATED", "LVL 7")
m2.metric("SENSORS", "GEMINI_2.0", "ACTIVE")
m3.metric("OSINT_FEED", "SYNCED")

st.divider()

# --- CORE: MAPA Y FEED ---
articles = fetch_global_intel()
processed_data = []

col_map, col_feed = st.columns([2.5, 1])

with col_map:
    m = folium.Map(
        location=[20, 0], zoom_start=2.5, 
        tiles="CartoDB dark_matter",
        no_wrap=True, max_bounds=True
    )
    marker_cluster = MarkerCluster().add_to(m)
    Fullscreen().add_to(m)

    if articles:
        with st.spinner("Escaneando zonas de conflicto..."):
            for art in articles:
                intel = analizar_con_ia(art['title'], art['description'])
                if intel.get("is_mil"):
                    processed_data.append({**art, **intel})
                    color = 'red' if intel['threat'] >= 8 else 'orange'
                    folium.Marker(
                        location=[intel['lat'], intel['lon']],
                        popup=f"<b>{intel['location']}</b><br>{intel['summary']}",
                        icon=folium.Icon(color=color, icon='warning', prefix='fa')
                    ).add_to(marker_cluster)

    st_folium(m, width="100%", height=700, use_container_width=True)

with col_feed:
    st.markdown("### 📥 LIVE_STREAM")
    if not processed_data:
        st.write("Radar limpio.")
    for item in processed_data:
        threat_class = "critical" if item['threat'] >= 8 else "high"
        st.markdown(f"""
            <div class="intel-card {threat_class}">
                <strong style="color:#f1f5f9;">[{item['location'].upper()}]</strong><br>
                <span style="font-size:12px;">{item['title']}</span><br>
                <a href="{item['url']}" target="_blank" style="color:#3b82f6; font-size:10px;">[VER_FUENTE]</a>
            </div>
            """, unsafe_allow_html=True)

st.markdown("<p style='text-align:center; color:#334155; font-size:10px; margin-top:30px;'>AEGIS CORP © 2026</p>", unsafe_allow_html=True)
