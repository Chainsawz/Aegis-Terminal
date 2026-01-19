import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen
import requests
from google import genai
import json
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="AEGIS BLACKOUT v6.1", layout="wide", initial_sidebar_state="expanded")

# --- CSS: ESTÉTICA DE BÚNKER SUBTERRÁNEO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Inter:wght@400;700&display=swap');
    
    .stApp { background-color: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    
    /* ELIMINAR CUADROS BLANCOS DEFINITIVAMENTE */
    iframe { 
        background-color: #000000 !important; 
        border: 1px solid #1e293b !important;
        border-radius: 8px;
    }

    .intel-card {
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid #1e293b;
        border-left: 4px solid #3b82f6;
        padding: 10px;
        margin-bottom: 8px;
        border-radius: 4px;
    }
    .critical { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.05); }
    [data-testid="stMetric"] { background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN DE SISTEMAS ---
try:
    client = genai.Client(api_key=st.secrets["gemini_api_key"])
    NEWS_API_KEY = st.secrets["news_api_key"]
except Exception as e:
    st.error(f"🚨 FALLO DE ENLACE: {e}")
    st.stop()

# --- MEMORIA 24H ---
if 'memory' not in st.session_state: st.session_state.memory = []
if 'raw_count' not in st.session_state: st.session_state.raw_count = 0

def update_memory(new_intel):
    existing_urls = {item['url'] for item in st.session_state.memory}
    for item in new_intel:
        if item['url'] not in existing_urls:
            item['ts'] = datetime.now()
            st.session_state.memory.append(item)
    cutoff = datetime.now() - timedelta(hours=24)
    st.session_state.memory = [i for i in st.session_state.memory if i['ts'] > cutoff]

# --- MOTOR IA POR LOTES ---
def analyze_batch(articles):
    if not articles: return []
    news_list = [{"id": i, "t": a['title']} for i, a in enumerate(articles)]
    prompt = f"Extract military events. JSON list: [{{'id':int, 'threat':1-10, 'lat':float, 'lon':float, 'loc':'City', 'sum':'brief'}}]. Data: {json.dumps(news_list)}"
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
        return [{**articles[r['id']], **r} for r in data]
    except: return []

def fetch_news():
    url = f'https://newsapi.org/v2/everything?q=(military OR war OR missile)&language=en&pageSize=15&apiKey={NEWS_API_KEY}'
    r = requests.get(url)
    return r.json().get('articles', []) if r.status_code == 200 else []

# --- INTERFAZ ---
st.markdown("<h2 style='color:#3b82f6; font-family:\"Share Tech Mono\";'>◢ AEGIS_TERMINAL_v6.1_STABLE</h2>", unsafe_allow_html=True)

if st.sidebar.button("⚡ SINCRONIZACIÓN TOTAL"):
    with st.spinner("Interceptando señales..."):
        raw = fetch_news()
        st.session_state.raw_count = len(raw)
        if raw:
            analyzed = analyze_batch(raw)
            update_memory(analyzed)
    st.rerun()

# Diagnóstico Rápido
d1, d2, d3 = st.columns(3)
d1.metric("NODOS_MAPA", len(st.session_state.memory), "24H")
d2.metric("SEÑALES_RAW", st.session_state.raw_count)
d3.metric("MOTOR_MAPA", "FOLIUM_STABLE")

st.divider()

col_map, col_feed = st.columns([2.5, 1])

with col_map:
    # --- MOTOR DE MAPA ULTRA-ESTABLE ---
    # He eliminado todas las restricciones que causan "cuadros blancos"
    m = folium.Map(
        location=[20, 0], 
        zoom_start=2, 
        tiles="cartodb dark_matter",
        no_wrap=True,           # Evita duplicidad horizontal
        attr="AEGIS_CORP"
    )
    
    # Inyectar fondo negro al mapa por si tarda en cargar
    m.get_root().header.add_child(folium.Element("<style>.folium-map { background: #000 !important; }</style>"))
    
    cluster = MarkerCluster().add_to(m)
    for item in st.session_state.memory:
        folium.Marker(
            [item['lat'], item['lon']],
            popup=item['sum'],
            icon=folium.Icon(color='red' if item['threat'] > 7 else 'orange', icon='info-sign')
        ).add_to(cluster)
    
    # El mapa ahora es el centro absoluto
    st_folium(m, width=1200, height=700, use_container_width=True, key="aegis_final_fix")

with col_feed:
    st.subheader("📥 INTEL_24H")
    if not st.session_state.memory:
        st.write("Radar en espera de datos.")
    else:
        for item in sorted(st.session_state.memory, key=lambda x: x['threat'], reverse=True):
            st.markdown(f"""<div class="intel-card {'critical' if item['threat'] > 7 else ''}">
                <small>[{item['loc'].upper()}] - LVL {item['threat']}</small><br>
                <strong>{item['title']}</strong></div>""", unsafe_allow_html=True)

st.markdown("<p style='text-align:center; color:#1e293b; font-size:10px;'>PROPERTY OF AEGIS CORP - ENCRYPTED TERMINAL v6.1</p>", unsafe_allow_html=True)
