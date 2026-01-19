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
    page_title="AEGIS TACTICAL v7.4", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS: ESTÉTICA DE TERMINAL COMPRIMIDO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    
    /* ELIMINACIÓN DE LATERALES: Forzamos el contenedor del mapa a ser negro abisal */
    iframe { 
        background-color: #000 !important; 
        border: 1px solid #1e293b !important; 
        border-radius: 8px;
    }
    
    .intel-card {
        background: rgba(15, 23, 42, 0.95);
        border: 1px solid #1e293b;
        border-left: 4px solid #3b82f6;
        padding: 10px;
        border-radius: 6px;
        margin-bottom: 8px;
        font-size: 14px;
    }
    .critical { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.1); }
    [data-testid="stMetric"] { background: #0f172a; border: 1px solid #1e293b; padding: 10px; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN DE SISTEMAS ---
try:
    client = genai.Client(api_key=st.secrets["gemini_api_key"])
    NEWS_API_KEY = st.secrets["news_api_key"]
except:
    st.error("🚨 FALLO DE ENLACE.")
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

# --- MOTOR IA ---
def analyze_batch(articles):
    if not articles: return []
    news_list = [{"id": i, "t": a['title']} for i, a in enumerate(articles)]
    prompt = f"Analyze military conflict. Return ONLY JSON: [{{'id':int, 'threat':1-10, 'lat':float, 'lon':float, 'loc':'Country', 'sum':'brief text'}}]. Data: {json.dumps(news_list)}"
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
st.markdown("<h2 style='color:#3b82f6; font-family:\"Share Tech Mono\";'>◢ AEGIS_CONDENSED_v7.4</h2>", unsafe_allow_html=True)

if st.sidebar.button("⚡ ESCANEO_TOTAL"):
    with st.spinner("Sincronizando..."):
        raw = fetch_news()
        if raw:
            analyzed = analyze_batch(raw)
            update_memory(analyzed)
    st.rerun()

# --- LAYOUT AJUSTADO: Más sitio para noticias ---
col_map, col_feed = st.columns([1.6, 1])

with col_map:
    # Ajustamos altura y zoom para que el mapamundi llene el cuadro
    m = folium.Map(
        location=[15, 0], 
        zoom_start=1.6, 
        tiles=None,               
        dragging=False,
        min_zoom=1.6,
        max_bounds=True,
        zoom_control=False,
        attributionControl=False
    )

    # Forzamos fondo negro interno
    m.get_root().header.add_child(folium.Element("<style>.folium-map { background: #000 !important; }</style>"))

    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr='CartoDB',
        no_wrap=True,
        bounds=[[-90, -180], [90, 180]]
    ).add_to(m)

    # Capa GeoJSON de fronteras
    try:
        folium.GeoJson(
            "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json",
            style_function=lambda x: {'color': '#3b82f6', 'weight': 0.5, 'fillOpacity': 0.05}
        ).add_to(m)
    except: pass

    cluster = MarkerCluster().add_to(m)
    for item in st.session_state.memory:
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=item['sum'],
            icon=folium.Icon(color='red' if item['threat'] > 7 else 'orange', icon='warning', prefix='fa')
        ).add_to(cluster)

    # Altura reducida (500px) para que el mapamundi no deje tanto aire blanco
    output = st_folium(m, height=480, use_container_width=True, key="aegis_condensed")

with col_feed:
    st.subheader("📥 LIVE_INTEL_STREAM")
    
    # Métricas integradas en el feed para ahorrar espacio
    st.metric("NODOS_IA", len(st.session_state.memory), "24H")
    
    selected_country = None
    if output and output.get("last_object_clicked_tooltip"):
        # Extraer país si existe (depende de cómo esté el GeoJSON)
        pass

    if not st.session_state.memory:
        st.write("Radar en espera.")
    else:
        for item in sorted(st.session_state.memory, key=lambda x: x['threat'], reverse=True):
            t_style = "critical" if item['threat'] > 7 else ""
            st.markdown(f"""
                <div class="intel-card {t_style}">
                    <small style="color:#60a5fa;">[{item['loc'].upper()}] - LVL {item['threat']}</small><br>
                    <strong>{item['title']}</strong><br>
                    <a href="{item['url']}" target="_blank" style="color:#3b82f6; font-size:11px; text-decoration:none;">[ACCEDER]</a>
                </div>
            """, unsafe_allow_html=True)

st.markdown("<p style='text-align:center; color:#1e293b; font-size:10px;'>AEGIS CORP © 2026 - CONDENSED TERMINAL</p>", unsafe_allow_html=True)
