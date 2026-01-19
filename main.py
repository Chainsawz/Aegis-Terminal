import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import requests
from google import genai
import json
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(
    page_title="AEGIS TACTICAL v7.3", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS: ESTÉTICA DE CIBER-BÚNKER TOTAL ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    
    /* ELIMINACIÓN DE RUIDO VISUAL: El iframe debe ser un pozo negro */
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
    st.error(f"🚨 FALLO DE ENLACE DE DATOS: {e}")
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
    cutoff = datetime.now() - timedelta(hours=24)
    st.session_state.memory = [i for i in st.session_state.memory if i['timestamp'] > cutoff]

# --- MOTOR IA ---
def analyze_batch(articles):
    if not articles: return []
    news_list = [{"id": i, "t": a['title']} for i, a in enumerate(articles)]
    prompt = f"Analyze military/geopolitical conflict. Return ONLY JSON: [{{'id':int, 'threat':1-10, 'lat':float, 'lon':float, 'loc':'Country', 'sum':'brief'}}]. Data: {json.dumps(news_list)}"
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
        return [{**articles[r['id']], **r} for r in data]
    except: return []

def fetch_news():
    query = "(military OR war OR missile OR conflict OR geopolitics)"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=15&apiKey={NEWS_API_KEY}'
    try:
        r = requests.get(url)
        return r.json().get('articles', []) if r.status_code == 200 else []
    except: return []

# --- INTERFAZ ---
st.markdown("<h1 style='color:#3b82f6; font-family:\"Share Tech Mono\";'>◢ AEGIS_TACTICAL_v7.3</h1>", unsafe_allow_html=True)

if st.sidebar.button("⚡ ESCANEO_TOTAL"):
    with st.spinner("Sincronizando satélites..."):
        raw = fetch_news()
        if raw:
            analyzed = analyze_batch(raw)
            update_memory(analyzed)
    st.rerun()

col_map, col_feed = st.columns([2.5, 1])

with col_map:
    # --- CALIBRACIÓN DE VISIÓN GRAN ANGULAR (v7.3) ---
    # Zoom 1.6 con centro en [10, 0] permite ver el mundo entero sin repetición
    m = folium.Map(
        location=[15, 0], 
        zoom_start=1.6, 
        tiles=None,               
        dragging=False,         # Anclaje estricto
        min_zoom=1.6,           # Bloqueo de zoom-out
        max_zoom=4,             # Permitimos un poco de zoom-in para detalle
        max_bounds=True,
        zoom_control=False,
        attributionControl=False
    )

    # Inyección de vacío negro
    m.get_root().header.add_child(folium.Element("<style>.folium-map { background: #000 !important; }</style>"))

    # Capa base oscura con No-Wrap real
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr='CartoDB',
        no_wrap=True,
        bounds=[[-90, -180], [90, 180]]
    ).add_to(m)

    # Fronteras Geopolíticas
    GEOJSON_URL = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json"
    try:
        folium.GeoJson(
            GEOJSON_URL,
            style_function=lambda x: {'fillColor': '#3b82f6', 'color': '#3b82f6', 'weight': 0.5, 'fillOpacity': 0.05},
            highlight_function=lambda x: {'fillColor': '#60a5fa', 'color': '#60a5fa', 'weight': 1.5, 'fillOpacity': 0.2},
            tooltip=folium.GeoJsonTooltip(fields=['name'], aliases=['Estado:'], localize=True)
        ).add_to(m)
    except: pass

    # Nodos de Inteligencia
    cluster = MarkerCluster().add_to(m)
    for item in st.session_state.memory:
        color = 'red' if item['threat'] > 7 else 'orange'
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=f"<b>{item['loc']}</b><br>{item['sum']}",
            icon=folium.Icon(color=color, icon='warning', prefix='fa')
        ).add_to(cluster)

    output = st_folium(m, width=1200, height=600, use_container_width=True, key="aegis_wide_v73")

with col_feed:
    st.subheader("📥 FEED_TACTICO_24H")
    selected_country = None
    if output and output.get("last_object_clicked_tooltip"):
        selected_country = output["last_object_clicked_tooltip"].replace("Estado: ", "").strip()
        st.info(f"📍 Zona: {selected_country}")

    if not st.session_state.memory:
        st.write("Radar en espera. Pulsa Escaneo.")
    else:
        intel = st.session_state.memory
        if selected_country:
            intel = [i for i in intel if selected_country.lower() in i['loc'].lower()]
        
        for item in sorted(intel, key=lambda x: x['threat'], reverse=True):
            t_style = "critical" if item['threat'] > 7 else ""
            st.markdown(f"<div class='intel-card {t_style}'><strong>{item['title']}</strong></div>", unsafe_allow_html=True)

st.markdown("<p style='text-align:center; color:#1e293b; font-size:10px;'>AEGIS CORP © 2026 - SECURE WIDE-EYE TERMINAL</p>", unsafe_allow_html=True)
