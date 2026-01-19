import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen
import requests
from google import genai
import json
import time
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="AEGIS TACTICAL v4.7", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono&display=swap');
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
    [data-testid="stMetric"] { background: #0f172a; border: 1px solid #1e293b; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN DE SISTEMAS ---
try:
    client = genai.Client(api_key=st.secrets["gemini_api_key"])
    NEWS_API_KEY = st.secrets["news_api_key"]
except Exception as e:
    st.error(f"🚨 ERROR CRÍTICO EN CREDENCIALES: {e}")
    st.stop()

# --- BANCO DE MEMORIA PERSISTENTE (24H) ---
if 'memory' not in st.session_state:
    st.session_state.memory = []

def clean_old_memory():
    cutoff = datetime.now() - timedelta(hours=24)
    st.session_state.memory = [i for i in st.session_state.memory if i['timestamp'] > cutoff]

def update_memory(new_intel):
    existing_urls = {item['url'] for item in st.session_state.memory}
    for item in new_intel:
        if item['url'] not in existing_urls:
            item['timestamp'] = datetime.now()
            st.session_state.memory.append(item)
    clean_old_memory()

# --- MOTOR DE INTELIGENCIA POR LOTES (ANTI-429) ---
def analyze_batch_intel(articles):
    if not articles: return []
    
    # Preparamos una lista simplificada para la IA
    news_list = [{"id": i, "t": a['title'], "d": a.get('description', '')} for i, a in enumerate(articles)]
    
    prompt = f"""
    Analyze these news items for military conflict/OSINT value: {json.dumps(news_list)}
    Return ONLY a JSON list of objects for military news only:
    [
        {{"id": int, "threat": 1-10, "lat": float, "lon": float, "loc": "City/Region", "sum": "1-line brief"}}
    ]
    If an item is NOT military, exclude it from the list.
    """
    
    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        raw_res = response.text.strip().replace('```json', '').replace('```', '')
        analyzed_list = json.loads(raw_res)
        
        # Mapeamos los resultados de la IA con los artículos originales
        final_results = []
        for res in analyzed_list:
            original = articles[res['id']]
            final_results.append({**original, **res})
        return final_results
    except Exception as e:
        if "429" in str(e):
            st.sidebar.warning("⚠️ Límite de IA alcanzado. Esperando enfriamiento...")
        else:
            st.sidebar.error(f"IA Error: {e}")
        return []

def fetch_news():
    # Query agresiva
    query = "(military OR war OR 'border clash' OR 'missile strike' OR 'troop movement')"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=15&apiKey={NEWS_API_KEY}'
    r = requests.get(url)
    if r.status_code == 200:
        return r.json().get('articles', [])
    return []

# --- UI PRINCIPAL ---
st.markdown("<h1 style='color:#3b82f6;'>◤ AEGIS_TACTICAL_COMMAND_v4.7</h1>", unsafe_allow_html=True)

# Sidebar
st.sidebar.header("🕹️ CONTROL DE RADAR")
if st.sidebar.button("⚡ ESCANEO GLOBAL"):
    with st.status("🚀 Sincronizando satélites...", expanded=True) as status:
        raw = fetch_news()
        status.write(f"Detectadas {len(raw)} señales...")
        # Procesamos en un solo lote para ahorrar cuota
        analyzed = analyze_batch_intel(raw)
        update_memory(analyzed)
        status.update(label=f"✅ {len(analyzed)} eventos tácticos añadidos.", state="complete")
    st.rerun()

clean_old_memory() # Asegurar limpieza en cada carga

# Métricas
m1, m2, m3 = st.columns(3)
m1.metric("NODOS_ACTIVOS", len(st.session_state.memory), "24H")
m2.metric("SISTEMA", "ÓPTIMO" if st.session_state.memory else "VACÍO")
m3.metric("ANÁLISIS", "LOTE_ÚNICO")

col_map, col_feed = st.columns([2.5, 1])

with col_map:
    # Mapa estable
    m = folium.Map(location=[20, 0], zoom_start=2.2, tiles="CartoDB dark_matter", no_wrap=True)
    marker_cluster = MarkerCluster().add_to(m)
    Fullscreen().add_to(m)

    for item in st.session_state.memory:
        color = 'red' if item['threat'] >= 8 else 'orange'
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=f"<b>{item['loc']}</b><br>{item['sum']}",
            icon=folium.Icon(color=color, icon='warning', prefix='fa')
        ).add_to(marker_cluster)

    st_folium(m, width="100%", height=700)

with col_feed:
    st.markdown("### 📥 FEED_TÁCTICO_24H")
    sorted_intel = sorted(st.session_state.memory, key=lambda x: x['threat'], reverse=True)
    if not sorted_intel:
        st.write("Radar despejado. Lanza un escaneo.")
    for item in sorted_intel:
        threat_class = "critical" if item['threat'] >= 8 else ""
        st.markdown(f"""
            <div class="intel-card {threat_class}">
                <small style="color:#60a5fa;">[{item['loc'].upper()}] - AMENAZA: {item['threat']}</small><br>
                <strong>{item['title']}</strong><br>
                <a href="{item['url']}" target="_blank" style="color:#3b82f6; font-size:10px;">[VER_ALPHA]</a>
            </div>
            """, unsafe_allow_html=True)
