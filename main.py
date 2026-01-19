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
    page_title="AEGIS TACTICAL v7.0", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS: ESTÉTICA DE MAPA TÁCTICO AVANZADO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    iframe { background-color: #000 !important; border: 1px solid #1e293b !important; border-radius: 12px; }
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
    [data-testid="stMetric"] { background: #0f172a; border: 1px solid #1e293b; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN DE SISTEMAS ---
try:
    client = genai.Client(api_key=st.secrets["gemini_api_key"])
    NEWS_API_KEY = st.secrets["news_api_key"]
except Exception as e:
    st.error(f"🚨 FALLO DE COMUNICACIÓN: {e}")
    st.stop()

# --- BANCO DE MEMORIA (24H) ---
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

# --- MOTOR IA ---
def analyze_batch(articles):
    if not articles: return []
    news_list = [{"id": i, "t": a['title']} for i, a in enumerate(articles)]
    prompt = f"Analyze military conflict. Return ONLY JSON: [{{'id':int, 'threat':1-10, 'lat':float, 'lon':float, 'loc':'Country', 'sum':'brief'}}]. Data: {json.dumps(news_list)}"
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
        return [{**articles[r['id']], **r} for r in data]
    except: return []

def fetch_news():
    query = "(military OR war OR missile OR conflict)"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=15&apiKey={NEWS_API_KEY}'
    try:
        r = requests.get(url)
        return r.json().get('articles', []) if r.status_code == 200 else []
    except: return []

# --- INTERFAZ ---
st.markdown("<h1 style='color:#3b82f6; font-family:\"Share Tech Mono\";'>◢ AEGIS_TACTICAL_v7.0</h1>", unsafe_allow_html=True)

if st.sidebar.button("⚡ ESCANEO_FRONTERAS"):
    with st.spinner("Cargando inteligencia de campo..."):
        raw = fetch_news()
        if raw:
            analyzed = analyze_batch(raw)
            update_memory(analyzed)
    st.rerun()

col_map, col_feed = st.columns([2.5, 1])

with col_map:
    # --- CONFIGURACIÓN DE MAPA CON FRONTERAS (v7.0) ---
    m = folium.Map(
        location=[20, 0], 
        zoom_start=3, 
        tiles=None,               
        dragging=False,         # Anclaje estricto
        min_zoom=3,             # Bloqueo de zoom out
        max_bounds=True,
        zoom_control=False,
        attributionControl=False
    )

    # Inyección de vacío negro
    m.get_root().header.add_child(folium.Element("<style>.folium-map { background: #000 !important; }</style>"))

    # Capa de mapa base
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr='CartoDB',
        no_wrap=True,           # No repetición
        bounds=[[-90, -180], [90, 180]]
    ).add_to(m)

    # --- CARGA DE FRONTERAS (GEOJSON) ---
    # URL de fronteras mundiales estándar
    GEOJSON_URL = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json"
    
    folium.GeoJson(
        GEOJSON_URL,
        name="fronteras",
        style_function=lambda x: {
            'fillColor': '#3b82f6',
            'color': '#3b82f6',
            'weight': 0.5,
            'fillOpacity': 0.05,
        },
        highlight_function=lambda x: {
            'fillColor': '#60a5fa',
            'color': '#60a5fa',
            'weight': 2,
            'fillOpacity': 0.2,
        },
        tooltip=folium.GeoJsonTooltip(fields=['name'], aliases=['País:'], localize=True)
    ).add_to(m)

    # Marc
