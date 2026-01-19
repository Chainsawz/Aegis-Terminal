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
    page_title="AEGIS TACTICAL v6.4", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS: ESTÉTICA DE VACÍO ABSOLUTO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Inter:wght@400;700&display=swap');
    
    .stApp { background-color: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    
    /* ELIMINACIÓN DE RUIDO BLANCO: Fondo negro total para el iframe */
    iframe { 
        background-color: #000000 !important; 
        border: 1px solid #1e293b !important;
        border-radius: 12px;
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
    st.error(f"🚨 ERROR EN CREDENCIALES: {e}")
    st.stop()

# --- BÚFER DE MEMORIA (PERSISTENCIA 24H) ---
if 'memory' not in st.session_state:
    st.session_state.memory = []

def update_memory(new_intel):
    existing_urls = {item['url'] for item in st.session_state.memory}
    for item in new_intel:
        if item['url'] not in existing_urls:
            item['timestamp'] = datetime.now()
            st.session_state.memory.append(item)
    # Purgar datos obsoletos (>24h)
    cutoff = datetime.now() - timedelta(hours=24)
    st.session_state.memory = [i for i in st.session_state.memory if i['timestamp'] > cutoff]

# --- MOTOR IA POR LOTES ---
def analyze_batch(articles):
    if not articles: return []
    news_list = [{"id": i, "t": a['title']} for i, a in enumerate(articles)]
    prompt = f"Identify military conflict news. Return ONLY JSON: [{{'id':int, 'threat':1-10, 'lat':float, 'lon':float, 'loc':'City', 'sum':'brief'}}]. Data: {json.dumps(news_list)}"
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
        return [{**articles[r['id']], **r} for r in data]
    except Exception as e:
        st.sidebar.error(f"IA Offline: {str(e)[:50]}")
        return []

def fetch_news():
    # Saneamiento de búsqueda táctica
    query = "(military OR war OR conflict OR geopolitics OR NATO OR missile)"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=20&apiKey={NEWS_API_KEY}'
    try:
        r = requests.get(url)
        if r.status_code != 200:
            st.sidebar.error(f"NewsAPI Error: {r.status_code}")
            return []
        return r.json().get('articles', [])
    except:
        return []

# --- INTERFAZ DE COMANDO ---
st.markdown("<h1 style='color:#3b82f6; font-family:\"Share Tech Mono\";'>◢ AEGIS_TERMINAL_v6.4</h1>", unsafe_allow_html=True)

# Operaciones en Sidebar
st.sidebar.header("🕹️ CONTROL_CENTER")
if st.sidebar.button("⚡ ESCANEO_TÁCTICO"):
    with st.spinner("Interceptando señales..."):
        raw = fetch_news()
        if raw:
            analyzed = analyze_batch(raw)
            update_memory(analyzed)
    st.rerun()

# Métricas de Estado
m1, m2, m3 = st.columns(3)
m1.metric("NODOS_IA", len(st.session_state.memory), "24H")
m2.metric("ZOOM_LOCK", "MAX_STRICT")
m3.metric("VOID_ENGINE", "ACTIVE")

st.divider()

col_map, col_feed = st.columns([2.5, 1])

with col_map:
    # --- CONFIGURACIÓN DE MAPA BLINDADO (v6.4) ---
    # Centramos y bloqueamos el zoom mínimo para eliminar el espacio blanco
    m = folium.Map(
        location=[20, 0], 
        zoom_start=3,           # <--- Subimos zoom inicial para llenar el cuadro
        tiles=None,               
        dragging=False,         # Bloqueo de arrastre
        scrollWheelZoom=True,     
        doubleClickZoom=False,
        zoomControl=False,
        attributionControl=False,
        min_zoom=3,             # <--- NO PERMITE ALEJARSE MÁS ALLÁ DE LO NECESARIO
        max_bounds=True         # Muros de realidad
    )

    # Inyectamos negro puro en el alma del mapa
    m.get_root().header.add_child(folium.Element("<style>.folium-map { background: #000 !important; }</style>"))

    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr='CartoDB',
        no_wrap=True,           # No repetición de continentes
        bounds=[[-90, -180], [90, 180]]
    ).add_to(m)

    # Marcadores
    cluster = MarkerCluster().add_to(m)
    for item in st.session_state.memory:
        color = 'red' if item['threat'] > 7 else 'orange'
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=f"<b>{item['loc']}</b><br>{item['sum']}",
            icon=folium.Icon(color=color, icon='warning', prefix='fa')
        ).add_to(cluster)

    st_folium(m, width=1200, height=720, use_container_width=True, key="aegis_v64_map")

with col_feed:
    st.subheader("📥 LIVE_INTEL_24H")
    if not st.session_state.memory:
        st.write("Radar limpio. Verifica la cuota de las APIs si el escaneo no arroja resultados.")
