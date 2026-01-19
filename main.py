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
    page_title="AEGIS TACTICAL v5.3", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS: ESTÉTICA "VOID" (ELIMINA CUADROS BLANCOS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono&display=swap');
    
    /* Fondo total de la app */
    .stApp { background: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    
    /* FIX DEFINITIVO PARA PARTES BLANCAS: Forzamos el fondo del mapa a NEGRO */
    iframe { 
        border-radius: 12px; 
        border: 1px solid #1e293b; 
        background-color: #060606 !important; /* Si el tile no carga, se ve negro, no blanco */
    }
    
    .intel-card {
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid #1e293b;
        border-left: 4px solid #3b82f6;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
        backdrop-filter: blur(5px);
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
    st.error(f"🚨 ERROR EN SECRETS: {e}")
    st.stop()

# --- BANCO DE MEMORIA (24H PERSISTENCIA) ---
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
    cutoff = datetime.now() - timedelta(hours=24)
    st.session_state.memory = [i for i in st.session_state.memory if i['timestamp'] > cutoff]

# --- MOTOR IA POR LOTES ---
def analyze_batch_intel(articles):
    if not articles: return []
    news_list = [{"id": i, "t": a['title']} for i, a in enumerate(articles)]
    prompt = f"Analyze military news: {json.dumps(news_list)}. Return ONLY JSON list: [{{'id':int, 'threat':1-10, 'lat':float, 'lon':float, 'loc':'City', 'sum':'brief'}}]"
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        res_text = response.text.strip().replace('```json', '').replace('```', '')
        analyzed = json.loads(res_text)
        return [{**articles[r['id']], **r} for r in analyzed]
    except:
        return []

def fetch_news():
    query = "(military OR war OR missile OR 'border clash')"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=15&apiKey={NEWS_API_KEY}'
    try:
        r = requests.get(url)
        return r.json().get('articles', []) if r.status_code == 200 else []
    except: return []

# --- UI PRINCIPAL ---
st.markdown("<h1 style='color:#3b82f6;'>◤ AEGIS_VOID_PHANTOM_v5.3</h1>", unsafe_allow_html=True)

# Barra Lateral
st.sidebar.header("🕹️ CENTRO DE MANDO")
if st.sidebar.button("⚡ ESCANEO TÁCTICO"):
    with st.spinner("Sincronizando satélites..."):
        raw = fetch_news()
        st.session_state.raw_feed = raw
        if raw:
            analyzed = analyze_batch_intel(raw)
            update_memory(analyzed)
    st.rerun()

# Métricas
m1, m2, m3 = st.columns(3)
m1.metric("NODOS_INTEL", len(st.session_state.memory), "24H")
m2.metric("SEÑALES_RAW", len(st.session_state.raw_feed))
m3.metric("STATUS", "ONLINE")

st.divider()

col_map, col_feed = st.columns([2.5, 1])

with col_map:
    # --- MAPA REFORZADO (ANTI-PARTES BLANCAS) ---
    m = folium.Map(
        location=[20, 0], 
        zoom_start=2.3, 
        # Usamos la URL directa para mayor estabilidad
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr='&copy; CartoDB',
        no_wrap=True,           # Evita repetición
        min_zoom=2.3,           # Evita alejar demasiado
        max_bounds=True,        # Límites activos
        min_lat=-85, max_lat=85,
        min_lon=-180, max_lon=180
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
    
    # use_container_width asegura que el mapa ocupe su lugar correctamente
    st_folium(m, width=1200, height=720, use_container_width=True)

with col_feed:
    st.subheader("📥 LIVE_INTEL_24H")
    if st.session_state.memory:
        sorted_intel = sorted(st.session_state.memory, key=lambda x: x['threat'], reverse=True)
        for item in sorted_intel:
            t_style = "critical" if item['threat'] > 7 else ""
            st.markdown(f"""<div class="intel-card {t_style}">
                <small>[{item['loc'].upper()}] - AMENAZA: {item['threat']}</small><br>
                <strong>{item['title']}</strong><br>
                <a href="{item['url']}" target="_blank" style="color:#3b82f6; font-size:10px;">[ALPHA_LINK]</a>
                </div>""", unsafe_allow_html=True)
    elif st.session_state.raw_feed:
        st.info("📡 Feed Crudo (IA Saturada)")
        for item in st.session_state.raw_feed[:10]:
            st.markdown(f"<div class='intel-card'><strong>{item['title']}</strong></div>", unsafe_allow_html=True)
    else:
        st.write("Radar en espera.")

st.markdown("<p style='text-align:center; color:#1e293b; font-size:10px; margin-top:30px;'>PROPERTY OF AEGIS CORP - ENCRYPTED TERMINAL v5.3</p>", unsafe_allow_html=True)
