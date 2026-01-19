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
    page_title="AEGIS TACTICAL v6.2", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS: ESTÉTICA DE PANTALLA DE MANDO ESTÁTICA ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono&display=swap');
    
    .stApp { background: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    
    /* El contenedor del mapa debe ser un pozo negro para evitar cuadros blancos */
    iframe { 
        background-color: #000000 !important; 
        border: 1px solid #1e293b;
        border-radius: 12px;
    }

    .intel-card {
        background: rgba(15, 23, 42, 0.95);
        border: 1px solid #1e293b;
        border-left: 4px solid #3b82f6;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
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
    st.error(f"🚨 ERROR EN EL ENLACE DE DATOS: {e}")
    st.stop()

# --- BÚFER DE MEMORIA (24H) ---
if 'memory' not in st.session_state:
    st.session_state.memory = []

def update_memory(new_intel):
    existing_urls = {item['url'] for item in st.session_state.memory}
    for item in new_intel:
        if item['url'] not in existing_urls:
            item['timestamp'] = datetime.now()
            st.session_state.memory.append(item)
    cutoff = datetime.now() - timedelta(hours=24)
    st.session_state.memory = [i for i in st.session_state.memory if i['timestamp'] > cutoff]

# --- MOTOR IA POR LOTES ---
def analyze_batch_intel(articles):
    if not articles: return []
    news_list = [{"id": i, "t": a['title']} for i, a in enumerate(articles)]
    prompt = f"Identify military events. Return ONLY JSON: [{{'id':int, 'threat':1-10, 'lat':float, 'lon':float, 'loc':'City', 'sum':'brief'}}]. Data: {json.dumps(news_list)}"
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
        return [{**articles[r['id']], **r} for r in data]
    except: return []

def fetch_news():
    query = "(military OR war OR missile OR 'border conflict')"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=15&apiKey={NEWS_API_KEY}'
    try:
        r = requests.get(url)
        return r.json().get('articles', []) if r.status_code == 200 else []
    except: return []

# --- INTERFAZ DE COMANDO ---
st.markdown("<h1 style='color:#3b82f6;'>◤ AEGIS_FLAT_HORIZON_v6.2</h1>", unsafe_allow_html=True)

if st.sidebar.button("⚡ ESCANEO TÁCTICO"):
    with st.spinner("Sincronizando satélites..."):
        raw = fetch_news()
        if raw:
            analyzed = analyze_batch_intel(raw)
            update_memory(analyzed)
    st.rerun()

# Métricas
m1, m2, m3 = st.columns(3)
m1.metric("NODOS_24H", len(st.session_state.memory))
m2.metric("PROYECCIÓN", "FLAT_WORLD")
m3.metric("INTERFAZ", "LOCKED")

st.divider()

col_map, col_feed = st.columns([2.5, 1])

with col_map:
    # --- CONFIGURACIÓN DE MAPA PLANO (v6.2) ---
    # Centramos el mundo y bloqueamos cualquier movimiento
    m = folium.Map(
        location=[20, 0], 
        zoom_start=2.2, 
        tiles=None,               # Quitamos el tile por defecto para configurarlo a mano
        dragging=False,           # PROHIBIDO ARRASTRAR
        scrollWheelZoom=True,     # Permitimos zoom pero en el sitio
        doubleClickZoom=False,
        attributionControl=False,
        zoomControl=False         # Quitamos los botones +/- para limpiar la UI
    )

    # Añadimos la capa de mapa con NO_WRAP estricto
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr='CartoDB',
        name='Aegis Dark Matter',
        no_wrap=True,             # PROHIBIDA LA REPETICIÓN LATERAL
        bounds=[[-90, -180], [90, 180]] # Límites físicos de la imagen
    ).add_to(m)

    # Fijamos los límites del mapa para que no se pueda mover ni "rebotar"
    m.fit_bounds([[-60, -160], [80, 160]])
    
    cluster = MarkerCluster().add_to(m)
    for item in st.session_state.memory:
        color = 'red' if item['threat'] > 7 else 'orange'
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=f"<b>{item['loc']}</b><br>{item['sum']}",
            icon=folium.Icon(color=color, icon='warning', prefix='fa')
        ).add_to(cluster)

    st_folium(m, width=1200, height=720, use_container_width=True, key="aegis_flat_map")

with col_feed:
    st.subheader("📥 INTEL_STREAM_24H")
    if not st.session_state.memory:
        st.write("Radar en espera.")
    else:
        for item in sorted(st.session_state.memory, key=lambda x: x['threat'], reverse=True):
            t_style = "critical" if item['threat'] > 7 else ""
            st.markdown(f"""<div class="intel-card {t_style}">
                <small>[{item['loc'].upper()}] - LVL {item['threat']}</small><br>
                <strong>{item['title']}</strong></div>""", unsafe_allow_html=True)

st.markdown("<p style='text-align:center; color:#1e293b; font-size:10px; margin-top:30px;'>PROPERTY OF AEGIS CORP - FLAT HORIZON TERMINAL v6.2</p>", unsafe_allow_html=True)
