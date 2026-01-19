import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import requests
from google import genai
import json
import os
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="AEGIS OPTIMIZER v7.8", layout="wide", initial_sidebar_state="expanded")

# --- CSS: ESTÉTICA DE BÚNKER DE BAJO CONSUMO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    iframe { background-color: #000 !important; border: 1px solid #1e293b !important; border-radius: 8px; }
    .intel-card {
        background: rgba(15, 23, 42, 0.95);
        border: 1px solid #1e293b;
        border-left: 4px solid #3b82f6;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .cache-alert { color: #facc15; font-size: 10px; font-weight: bold; margin-bottom: 5px; }
    .critical { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.1); }
    .link-btn { color: #3b82f6; text-decoration: none; font-size: 11px; font-weight: bold; border: 1px solid #3b82f6; padding: 2px 5px; border-radius: 4px; }
    </style>
    """, unsafe_allow_html=True)

# --- SISTEMA DE COLD STORAGE (ARCHIVO LOCAL) ---
CACHE_FILE = "aegis_cache.json"

def save_to_cold_storage(data):
    try:
        with open(CACHE_FILE, "w") as f:
            # Convertimos timestamps a string para JSON
            serializable_data = []
            for item in data:
                temp_item = item.copy()
                if isinstance(temp_item['timestamp'], datetime):
                    temp_item['timestamp'] = temp_item['timestamp'].isoformat()
                serializable_data.append(temp_item)
            json.dump(serializable_data, f)
    except: pass

def load_from_cold_storage():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                for item in data:
                    item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                return data
        except: return []
    return []

# --- CONEXIÓN DE SISTEMAS ---
try:
    client = genai.Client(api_key=st.secrets["gemini_api_key"])
    NEWS_API_KEY = st.secrets["news_api_key"]
except:
    st.error("🚨 FALLO DE ENLACE.")
    st.stop()

# --- BÚFER DE MEMORIA (PERSISTENCIA 24H) ---
if 'memory' not in st.session_state:
    # Intentamos cargar desde el archivo local al iniciar
    st.session_state.memory = load_from_cold_storage()
if 'raw_feed' not in st.session_state: 
    st.session_state.raw_feed = []

def update_memory(new_intel):
    existing_urls = {item['url'] for item in st.session_state.memory}
    added = False
    for item in new_intel:
        if item['url'] not in existing_urls:
            item['timestamp'] = datetime.now()
            st.session_state.memory.append(item)
            added = True
    
    # Purgar datos de más de 24h
    cutoff = datetime.now() - timedelta(hours=24)
    st.session_state.memory = [i for i in st.session_state.memory if i['timestamp'] > cutoff]
    
    if added:
        save_to_cold_storage(st.session_state.memory)

# --- MOTOR IA OPTIMIZADO ---
def analyze_batch(articles):
    if not articles: return []
    news_list = [{"id": i, "t": a['title']} for i, a in enumerate(articles)]
    prompt = """Analyze military/geopolitics. Return ONLY JSON list:
    [{"id":int, "threat":1-10, "lat":float, "lon":float, "loc_en":"Country", "loc_es":"País", "sum_en":"Short", "sum_es":"Corto"}]
    Data: """ + json.dumps(news_list)
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        res_text = response.text.strip().replace('```json', '').replace('```', '')
        data = json.loads(res_text)
        return [{**articles[r['id']], **r} for r in data]
    except: return [] # Fallback automático

def fetch_news():
    # Optimizamos query para no gastar peticiones en basura
    query = "(military OR war OR conflict OR NATO OR missile)"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=10&apiKey={NEWS_API_KEY}'
    try:
        r = requests.get(url)
        # NewsAPI suele dar 100 req/día
        return r.json().get('articles', []) if r.status_code == 200 else []
    except: return []

# --- INTERFAZ ---
st.markdown("<h2 style='color:#3b82f6; font-family:\"Share Tech Mono\";'>◢ AEGIS_OPTIMIZER_v7.8</h2>", unsafe_allow_html=True)

# Sidebar con temporizador de seguridad
st.sidebar.header("🕹️ OPERACIONES")
if st.sidebar.button("⚡ ESCANEO_TÁCTICO"):
    with st.spinner("Consumiendo cuota mínima..."):
        raw = fetch_news()
        st.session_state.raw_feed = raw
        if raw:
            analyzed = analyze_batch(raw)
            update_memory(analyzed)
    st.rerun()

col_map, col_feed = st.columns([1.6, 1])

with col_map:
    # --- MAPA ANCLADO (v7.8) ---
    m = folium.Map(location=[15, 0], zoom_start=2.1, tiles=None, dragging=False, min_zoom=2.1, max_bounds=True, zoom_control=False, attributionControl=False)
    m.get_root().header.add_child(folium.Element("<style>.folium-map { background: #000 !important; }</style>"))
    folium.TileLayer(tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr='CartoDB', no_wrap=True).add_to(m)

    cluster = MarkerCluster().add_to(m)
    for item in st.session_state.memory:
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=f"<b>{item.get('loc_es')}</b><br>{item.get('sum_es')}",
            icon=folium.Icon(color='red' if item.get('threat', 0) > 7 else 'orange', icon='warning', prefix='fa')
        ).add_to(cluster)
    st_folium(m, height=520, use_container_width=True, key="aegis_opt_map")

with col_feed:
    st.subheader("📥 FEED_OPTIMIZADO")
    # Indicador de estado de la cuota
    is_cached = len(st.session_state.memory) > 0
    st.caption(f"MODO: {'FALLBACK_PERSISTENTE' if is_cached else 'ESPERANDO_DATOS'}")
    
    if not st.session_state.memory:
        st.write("Radar en espera de gas (cuota).")
    else:
        for item in sorted(st.session_state.memory, key=lambda x: x.get('threat', 0), reverse=True):
            t_style = "critical" if item.get('threat', 0) > 7 else ""
            st.markdown(f"""
                <div class="intel-card {t_style}">
                    <div class="cache-alert">✓ PERSISTENCIA LOCAL ACTIVA</div>
                    <strong>{item['title']}</strong><br>
                    <span style="font-size:12px; color:#60a5fa;">{item.get('sum_es')}</span><br>
                    <div style="margin-top:8px;">
                        <a href="{item['url']}" target="_blank" class="link-btn">📂 FUENTE</a>
                    </div>
                </div>
            """, unsafe_allow_html=True)

st.markdown("<p style='text-align:center; color:#1e293b; font-size:10px;'>AEGIS CORP © 2026 - OPTIMIZED COLD STORAGE</p>", unsafe_allow_html=True)
