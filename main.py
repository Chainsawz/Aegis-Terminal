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
    page_title="AEGIS TACTICAL v5.2", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS: ESTÉTICA DE BÚNKERS MILITARES ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono&display=swap');
    .stApp { background: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    iframe { border-radius: 12px; border: 1px solid #1e293b; background: #0b0f1a; }
    .intel-card {
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid #1e293b;
        border-left: 4px solid #3b82f6;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .critical { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.1); }
    .emergency { border-left-color: #64748b; opacity: 0.8; }
    [data-testid="stMetric"] { background: #0f172a; border: 1px solid #1e293b; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN DE SISTEMAS ---
try:
    client = genai.Client(api_key=st.secrets["gemini_api_key"])
    NEWS_API_KEY = st.secrets["news_api_key"]
except Exception as e:
    st.error(f"🚨 ERROR EN SECRETS: {e}")
    st.stop()

# --- BANCO DE MEMORIA (24H PERSISTENCIA) ---
if 'memory' not in st.session_state:
    st.session_state.memory = [] # Almacén de inteligencia analizada
if 'raw_feed' not in st.session_state:
    st.session_state.raw_feed = [] # Feed de emergencia sin filtrar

def update_memory(new_intel):
    # Evitar duplicados por URL
    existing_urls = {item['url'] for item in st.session_state.memory}
    for item in new_intel:
        if item['url'] not in existing_urls:
            item['timestamp'] = datetime.now()
            st.session_state.memory.append(item)
    # Limpieza: borrar datos de más de 24 horas
    cutoff = datetime.now() - timedelta(hours=24)
    st.session_state.memory = [i for i in st.session_state.memory if i['timestamp'] > cutoff]

# --- MOTOR IA POR LOTES (ANTI-QUOTA LIMIT) ---
def analyze_batch_intel(articles):
    if not articles: return []
    # Comprimimos los datos para la IA
    news_list = [{"id": i, "t": a['title']} for i, a in enumerate(articles)]
    
    prompt = f"Analyze these headlines for military events. Return ONLY JSON list: [{{'id': int, 'threat': 1-10, 'lat': float, 'lon': float, 'loc': 'City', 'sum': 'brief text'}}] News: {json.dumps(news_list)}"
    
    try:
        # Usamos 1.5 Flash para asegurar cuota gratuita en 2026
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        res_text = response.text.strip().replace('```json', '').replace('```', '')
        analyzed = json.loads(res_text) #
        return [{**articles[r['id']], **r} for r in analyzed]
    except Exception as e:
        st.sidebar.warning("⚠️ CEREBRO IA SATURADO: Usando datos RAW.") #
        return []

def fetch_news():
    query = "(military OR war OR missile OR 'border clash' OR airstrike)" #
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=15&apiKey={NEWS_API_KEY}'
    try:
        r = requests.get(url)
        return r.json().get('articles', []) if r.status_code == 200 else []
    except:
        return []

# --- UI PRINCIPAL ---
st.markdown("<h1 style='color:#3b82f6;'>◤ AEGIS_VOID_SHIELD_v5.2</h1>", unsafe_allow_html=True)

# Barra Lateral de Control
st.sidebar.header("🕹️ CENTRO DE MANDO")
if st.sidebar.button("⚡ ESCANEO TÁCTICO GLOBAL"):
    with st.spinner("Sincronizando con satélites..."):
        raw = fetch_news()
        st.session_state.raw_feed = raw
        if raw:
            analyzed = analyze_batch_intel(raw) # Procesamiento por lotes
            update_memory(analyzed)
    st.rerun()

# Métricas de Estado
m1, m2, m3 = st.columns(3)
m1.metric("INTEL_NODES", len(st.session_state.memory), "24H WINDOW")
m2.metric("RAW_SIGNALS", len(st.session_state.raw_feed))
m3.metric("SYSTEM", "READY" if st.session_state.memory else "SCAN_IDLE")

col_map, col_feed = st.columns([2.5, 1])

with col_map:
    # --- BLINDAJE DE MAPA (v5.2): Bloqueo de Zoom y Repetición ---
    # Limita la vista a un solo mapa sin bucles
    m = folium.Map(
        location=[20, 0], 
        zoom_start=2.3, 
        tiles="CartoDB dark_matter",
        no_wrap=True,           # Evita que el mapa se repita horizontalmente
        min_zoom=2.3,           # Bloqueo para evitar ver cuadros blancos al alejar
        max_bounds=True,        # Activa las barreras geográficas
        min_lat=-85, max_lat=85,
        min_lon=-180, max_lon=180
    )
    
    # Agrupación de marcadores
    marker_cluster = MarkerCluster().add_to(m)
    Fullscreen().add_to(m)
    
    for item in st.session_state.memory:
        color = 'red' if item['threat'] > 7 else 'orange'
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=f"<b>{item['loc']}</b><br>{item['sum']}",
            icon=folium.Icon(color=color, icon='warning', prefix='fa')
        ).add_to(marker_cluster)
    
    st_folium(m, width="100%", height=700, use_container_width=True)

with col_feed:
    st.subheader("📥 LIVE_STREAM_24H")
    if st.session_state.memory:
        # Priorizar noticias por nivel de amenaza
        sorted_intel = sorted(st.session_state.memory, key=lambda x: x['threat'], reverse=True)
        for item in sorted_intel:
            t_style = "critical" if item['threat'] > 7 else ""
            st.markdown(f"""<div class="intel-card {t_style}">
                <small>[{item['loc'].upper()}] - AMENAZA: {item['threat']}</small><br>
                <strong>{item['title']}</strong><br>
                <a href="{item['url']}" target="_blank" style="color:#3b82f6; font-size:10px;">[VER_ALPHA]</a>
                </div>""", unsafe_allow_html=True)
    elif st.session_state.raw_feed:
        st.info("📡 Feed Crudo: IA sin cuota por hoy.") #
        for item in st.session_state.raw_feed[:10]:
            st.markdown(f"""<div class="intel-card emergency">
                <small>[RAW_SIGNAL]</small><br>{item['title']}</div>""", unsafe_allow_html=True)
    else:
        st.write("Radar en espera de escaneo.")

st.markdown("<p style='text-align:center; color:#1e293b; font-size:10px; margin-top:50px;'>PROPERTY OF AEGIS CORP - ENCRYPTED TERMINAL v5.2</p>", unsafe_allow_html=True)
