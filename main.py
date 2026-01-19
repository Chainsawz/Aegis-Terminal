import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen
import requests
from google import genai
import json
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="AEGIS TACTICAL v4.5", layout="wide", initial_sidebar_state="expanded")

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

# --- BANCO DE MEMORIA ---
if 'memory' not in st.session_state:
    st.session_state.memory = []

def update_memory(new_intel):
    existing_urls = {item['url'] for item in st.session_state.memory}
    for item in new_intel:
        if item['url'] not in existing_urls:
            item['timestamp'] = datetime.now()
            st.session_state.memory.append(item)
    # Limpieza: solo mantener últimas 24h
    cutoff = datetime.now() - timedelta(hours=24)
    st.session_state.memory = [i for i in st.session_state.memory if i['timestamp'] > cutoff]

# --- MOTOR DE INTELIGENCIA ---
def analyze_intel(title, desc):
    prompt = f"OSINT analysis: {title}. {desc}. Return ONLY JSON: {{\"is_mil\":bool, \"threat\":1-10, \"lat\":float, \"lon\":float, \"loc\":\"City\", \"sum\":\"Quick brief\"}}"
    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return json.loads(response.text.strip().replace('```json', '').replace('```', ''))
    except: return {"is_mil": False}

def fetch_news():
    # Query agresiva para maximizar resultados
    query = "(military OR war OR 'border clash' OR 'missile strike' OR 'troop movement')"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=30&apiKey={NEWS_API_KEY}'
    r = requests.get(url)
    if r.status_code == 200:
        return r.json().get('articles', [])
    else:
        st.sidebar.error(f"📡 Error de Enlace: {r.status_code}")
        return []

# --- AUTO-BOOT SEQUENCE ---
if not st.session_state.memory:
    with st.status("🚀 Iniciando secuencia de escaneo global...", expanded=True) as status:
        raw = fetch_news()
        status.write(f"Encontradas {len(raw)} señales de noticias...")
        analyzed = []
        for n in raw[:12]: # Analizamos 12 para no saturar la API gratuita
            intel = analyze_intel(n['title'], n['description'])
            if intel.get("is_mil"):
                analyzed.append({**n, **intel})
        update_memory(analyzed)
        status.update(label="✅ Escaneo completo.", state="complete")

# --- UI PRINCIPAL ---
st.markdown("<h1 style='color:#3b82f6;'>◤ AEGIS_SIGNAL_BOOSTER_v4.5</h1>", unsafe_allow_html=True)

# Sidebar
st.sidebar.header("🕹️ CONTROL DE RADAR")
if st.sidebar.button("⚡ RESCANEAR AHORA"):
    st.session_state.memory = [] # Limpiar para forzar refresco
    st.rerun()

# Métricas
col_met1, col_met2, col_met3 = st.columns(3)
col_met1.metric("INTEL_NODES", len(st.session_state.memory))
col_met2.metric("SIGNAL_STRENGTH", "OPTIMAL" if st.session_state.memory else "LOW")
col_met3.metric("TIME_WINDOW", "24H")

col_map, col_feed = st.columns([2.5, 1])

with col_map:
    # Mapa optimizado
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
    st.markdown("### 📥 LIVE_FEED_24H")
    sorted_intel = sorted(st.session_state.memory, key=lambda x: x['threat'], reverse=True)
    for item in sorted_intel:
        threat_class = "critical" if item['threat'] >= 8 else ""
        st.markdown(f"""
            <div class="intel-card {threat_class}">
                <small style="color:#60a5fa;">[{item['loc'].upper()}] - LVL {item['threat']}</small><br>
                <strong>{item['title']}</strong><br>
                <a href="{item['url']}" target="_blank" style="color:#3b82f6; font-size:10px;">[LINK]</a>
            </div>
            """, unsafe_allow_html=True)
