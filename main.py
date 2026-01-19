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
    page_title="AEGIS TACTICAL v4.4", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS: ESTÉTICA REFINADA ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono&display=swap');
    .stApp { background: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    iframe { border-radius: 12px; border: 1px solid #1e293b; background: #020617; }
    .intel-card {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid #1e293b;
        border-left: 4px solid #3b82f6;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        backdrop-filter: blur(8px);
    }
    .critical { border-left-color: #ef4444; box-shadow: 0 0 15px rgba(239, 68, 68, 0.2); }
    .high { border-left-color: #f97316; }
    [data-testid="stMetric"] { background: #0f172a; border: 1px solid #1e293b; padding: 15px; border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN CON EL BÚNKER ---
try:
    client = genai.Client(api_key=st.secrets["gemini_api_key"])
    NEWS_API_KEY = st.secrets["news_api_key"]
except:
    st.error("🚨 ERROR: Revisa las claves en Secrets.")
    st.stop()

# --- LÓGICA DE MEMORIA (24 HORAS) ---
# Usamos cache_resource para que los datos persistan entre sesiones de usuario
@st.cache_resource
def get_memory_bank():
    return [] # Aquí guardaremos las noticias: {data, timestamp}

def update_memory(new_items):
    bank = get_memory_bank()
    current_time = datetime.now()
    # 1. Añadir nuevos (si no existen ya por URL)
    existing_urls = [item['url'] for item in bank]
    for ni in new_items:
        if ni['url'] not in existing_urls:
            ni['saved_at'] = current_time
            bank.append(ni)
    # 2. Limpiar antiguos (más de 24h)
    # Nota: En un producto real esto se filtraría dinámicamente
    return bank

# --- CEREBRO IA ---
def analizar_con_ia(titulo, desc):
    prompt = f"Analyze military conflict: {titulo}. {desc}. Return ONLY JSON: {{\"is_mil\":bool, \"threat\":int(1-10), \"lat\":float, \"lon\":float, \"loc\":\"Name\", \"sum\":\"1 line\"}}"
    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return json.loads(response.text.strip().replace('```json', '').replace('```', ''))
    except: return {"is_mil": False}

# --- SUMINISTRO ---
def fetch_news():
    query = "(military OR war OR missile OR 'border clash' OR 'airstrike' OR 'attack')"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=20&apiKey={NEWS_API_KEY}'
    try:
        r = requests.get(url)
        return r.json().get('articles', [])
    except: return []

# --- PANEL DE CONTROL ---
st.markdown("<h1 style='color:#3b82f6;'>◤ AEGIS_TACTICAL_COMMAND_v4.4</h1>", unsafe_allow_html=True)

st.sidebar.markdown("### 🛰️ RADAR_STATUS")
if st.sidebar.button("🔄 FORCE_RESCAN & SYNC"):
    with st.spinner("Escaneando..."):
        raw_news = fetch_news()
        analyzed = []
        for n in raw_news:
            intel = analizar_con_ia(n['title'], n['description'])
            if intel.get("is_mil"):
                analyzed.append({**n, **intel})
        update_memory(analyzed)
    st.rerun()

# Filtrar memoria por 24h
memory = get_memory_bank()
cutoff = datetime.now() - timedelta(hours=24)
live_intel = [n for n in memory if n['saved_at'] > cutoff]

# Métricas
m1, m2, m3 = st.columns(3)
m1.metric("INTEL_IN_MEMORY", len(live_intel), "24H WINDOW")
m2.metric("THREAT_LEVEL", "ELEVATED" if live_intel else "STABLE")
m3.metric("SENSORS", "GEMINI_2.0", "LIVE")

col_map, col_feed = st.columns([2.5, 1])

with col_map:
    # --- FIX MAPA: Eliminamos restricciones agresivas que causan carga lenta ---
    m = folium.Map(
        location=[20, 0], 
        zoom_start=2, 
        tiles="CartoDB dark_matter",
        no_wrap=True,
        min_zoom=2,
        max_bounds=False # Desactivado temporalmente para asegurar carga total
    )
    
    marker_cluster = MarkerCluster().add_to(m)
    Fullscreen().add_to(m)

    for item in live_intel:
        color = 'red' if item['threat'] >= 8 else 'orange'
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=f"<b>{item['loc']}</b><br>{item['sum']}",
            icon=folium.Icon(color=color, icon='warning', prefix='fa')
        ).add_to(marker_cluster)

    st_folium(m, width="100%", height=700, use_container_width=True)

with col_feed:
    st.markdown("### 📥 24H_TACTICAL_FEED")
    # Ordenar por importancia y luego por tiempo
    sorted_intel = sorted(live_intel, key=lambda x: (x['threat'], x['publishedAt']), reverse=True)
    
    if not sorted_intel:
        st.write("Sin datos en memoria. Pulsa REFRESH_SCAN.")
    
    for item in sorted_intel:
        t_style = "critical" if item['threat'] >= 8 else "high"
        st.markdown(f"""
            <div class="intel-card {t_style}">
                <strong style="color:#60a5fa;">[{item['loc'].upper()}] - LVL {item['threat']}</strong><br>
                <span style="font-size:12px;">{item['title']}</span><br>
                <a href="{item['url']}" target="_blank" style="color:#3b82f6; font-size:10px;">[VER_FUENTE]</a>
            </div>
            """, unsafe_allow_html=True)

st.markdown("<p style='text-align:center; color:#1e293b; font-size:10px; margin-top:50px;'>AEGIS CORP © 2026 - PERSISTENT TERMINAL</p>", unsafe_allow_html=True)
