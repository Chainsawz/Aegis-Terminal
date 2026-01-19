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
    page_title="AEGIS TACTICAL v5.8", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS: ESTÉTICA DE BÚNKER APOCALÍPTICO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono&display=swap');
    
    .stApp { background: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    
    /* FIX DE RENDERIZADO: Fondo negro para eliminar cuadros blancos */
    iframe { 
        background-color: #020617 !important; 
        border-radius: 12px;
        border: 1px solid #1e293b;
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
    st.error(f"🚨 ERROR EN EL ENLACE DE DATOS: {e}")
    st.stop()

# --- BANCO DE MEMORIA (PERSISTENCIA 24H) ---
if 'memory' not in st.session_state:
    st.session_state.memory = []
if 'raw_feed' not in st.session_state:
    st.session_state.raw_feed = []

def update_memory(new_intel):
    # Filtrado de duplicados por URL para no llenar el radar de basura
    existing_urls = {item['url'] for item in st.session_state.memory}
    for item in new_intel:
        if item['url'] not in existing_urls:
            item['timestamp'] = datetime.now()
            st.session_state.memory.append(item)
    
    # Purgar transmisiones de más de 24 horas
    cutoff = datetime.now() - timedelta(hours=24)
    st.session_state.memory = [i for i in st.session_state.memory if i['timestamp'] > cutoff]

# --- MOTOR IA POR LOTES (ANTI-SATURACIÓN) ---
def analyze_batch_intel(articles):
    if not articles: return []
    # Comprimimos el feed para ahorrar tokens y cuota
    news_list = [{"id": i, "t": a['title']} for i, a in enumerate(articles)]
    
    prompt = f"Analyze these headlines for military events. Return ONLY JSON list: [{{'id':int, 'threat':1-10, 'lat':float, 'lon':float, 'loc':'City', 'sum':'brief'}}]. News: {json.dumps(news_list)}"
    
    try:
        # Usamos 1.5 Flash para maximizar la cuota de peticiones gratis
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        res_text = response.text.strip().replace('```json', '').replace('```', '')
        analyzed = json.loads(res_text)
        return [{**articles[r['id']], **r} for r in analyzed]
    except Exception:
        # Modo Fallback si la IA está en "cooldown"
        return []

def fetch_news():
    query = "(military OR war OR missile OR 'border conflict')"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=15&apiKey={NEWS_API_KEY}'
    try:
        r = requests.get(url)
        return r.json().get('articles', []) if r.status_code == 200 else []
    except: return []

# --- INTERFAZ DE COMANDO ---
st.markdown("<h1 style='color:#3b82f6;'>◤ AEGIS_VOID_BASTION_v5.8</h1>", unsafe_allow_html=True)

# Panel Lateral de Operaciones
st.sidebar.header("🕹️ OPERACIONES")
if st.sidebar.button("⚡ ESCANEO GLOBAL"):
    with st.spinner("Interceptando señales satelitales..."):
        raw = fetch_news()
        st.session_state.raw_feed = raw
        if raw:
            analyzed = analyze_batch_intel(raw)
            update_memory(analyzed)
    st.rerun()

# Métricas de Red
m1, m2, m3 = st.columns(3)
m1.metric("NODOS_24H", len(st.session_state.memory), "MEM_SYNC")
m2.metric("RAW_SIGNALS", len(st.session_state.raw_feed))
m3.metric("MAP_STATUS", "ANCHORED")

st.divider()

col_map, col_feed = st.columns([2.5, 1])

with col_map:
    # --- ANCLAJE TOTAL DEL MAPA (v5.8): PROHIBIDO MOVER ---
    # Implementamos el bloqueo absoluto de coordenadas y arrastre
    m = folium.Map(
        location=[20, 0], 
        zoom_start=2.3, 
        tiles="cartodbdark_matter", 
        no_wrap=True,               # Prohibida la repetición de continentes
        min_zoom=2.3,               # Prohibido el zoom-out para no ver el vacío
        max_bounds=True,            # Muros de realidad geográficos
        min_lat=-85, max_lat=85,
        min_lon=-180, max_lon=180,
        dragging=False,             # EL MAPA ESTÁ CLAVADO AL CHASIS
        scrollWheelZoom=True,       # Zoom con rueda permitido
        doubleClickZoom=False       # Desactivado para evitar errores de centrado
    )
    
    marker_cluster = MarkerCluster().add_to(m)
    Fullscreen().add_to(m)
    
    for item in st.session_state.memory:
        color = 'red' if item['threat'] > 7 else 'orange'
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=f"<b>{item['loc']}</b><br>{item['sum']}",
            icon=folium.Icon(color=color, icon='warning', prefix='fa')
        ).add_to(marker_cluster)
    
    # Sincronización de renderizado mediante Key única
    st_folium(m, width=1200, height=720, key="aegis_bastion_map")

with col_feed:
    st.subheader("📥 LIVE_INTEL_24H")
    if st.session_state.memory:
        # Prioridad por nivel de amenaza OSINT
        sorted_intel = sorted(st.session_state.memory, key=lambda x: x['threat'], reverse=True)
        for item in sorted_intel:
            t_style = "critical" if item['threat'] > 7 else ""
            st.markdown(f"""<div class="intel-card {t_style}">
                <small>[{item['loc'].upper()}] - AMENAZA: {item['threat']}</small><br>
                <strong>{item['title']}</strong><br>
                <a href="{item['url']}" target="_blank" style="color:#3b82f6; font-size:10px;">[SOURCE_LINK]</a>
                </div>""", unsafe_allow_html=True)
    elif st.session_state.raw_feed:
        st.info("📡 Feed Analógico: IA en recarga de cuota.")
        for item in st.session_state.raw_feed[:10]:
            st.markdown(f"<div class='intel-card'><strong>{item['title']}</strong></div>", unsafe_allow_html=True)
    else:
        st.write("Radar en espera de escaneo táctico.")

st.markdown("<p style='text-align:center; color:#1e293b; font-size:10px; margin-top:30px;'>PROPERTY OF AEGIS CORP - ENCRYPTED TERMINAL v5.8</p>", unsafe_allow_html=True)
