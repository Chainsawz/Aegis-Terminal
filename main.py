import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen
import requests
from google import genai
import json
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AEGIS OMEGA v4.8", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono&display=swap');
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
    .emergency { border-left-color: #64748b; opacity: 0.8; }
    .critical { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.1); }
    [data-testid="stMetric"] { background: #0f172a; border: 1px solid #1e293b; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN ---
try:
    client = genai.Client(api_key=st.secrets["gemini_api_key"])
    NEWS_API_KEY = st.secrets["news_api_key"]
except Exception as e:
    st.error(f"🚨 CREDENCIALES COMPROMETIDAS: {e}")
    st.stop()

# --- BANCO DE MEMORIA ---
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

# --- MOTOR IA (LOTE ÚNICO) ---
def analyze_batch(articles):
    if not articles: return []
    news_list = [{"id": i, "t": a['title']} for i, a in enumerate(articles)]
    
    prompt = f"""Analyze these headlines for military events. Return ONLY JSON list:
    [{{"id": int, "threat": 1-10, "lat": float, "lon": float, "loc": "City", "sum": "brief"}}]
    News: {json.dumps(news_list)}"""
    
    try:
        # CAMBIO A 1.5 FLASH PARA MAYOR CUOTA
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        res_text = response.text.strip().replace('```json', '').replace('```', '')
        analyzed = json.loads(res_text)
        return [{**articles[r['id']], **r} for r in analyzed]
    except Exception as e:
        st.sidebar.error(f"IA FUERA DE SERVICIO: {str(e)[:50]}...")
        return []

def fetch_news():
    url = f'https://newsapi.org/v2/everything?q=(military OR war OR missile)&language=en&sortBy=publishedAt&pageSize=15&apiKey={NEWS_API_KEY}'
    r = requests.get(url)
    return r.json().get('articles', []) if r.status_code == 200 else []

# --- UI ---
st.markdown("<h1 style='color:#3b82f6;'>◤ AEGIS_OMEGA_v4.8</h1>", unsafe_allow_html=True)

# Sidebar
st.sidebar.header("🕹️ CENTRO DE MANDO")
if st.sidebar.button("⚡ ESCANEO DE EMERGENCIA"):
    raw = fetch_news()
    st.session_state.raw_feed = raw # Guardamos el feed crudo siempre
    if raw:
        analyzed = analyze_batch(raw)
        update_memory(analyzed)
    st.rerun()

# Métricas
m1, m2, m3 = st.columns(3)
m1.metric("MAP_NODES", len(st.session_state.memory), "IA FILTERED")
m2.metric("RAW_SIGNALS", len(st.session_state.raw_feed), "UNFILTERED")
m3.metric("STATUS", "EMERGENCY" if not st.session_state.memory and st.session_state.raw_feed else "ACTIVE")

col_map, col_feed = st.columns([2.5, 1])

with col_map:
    # Mapa Robusto
    m = folium.Map(location=[20, 0], zoom_start=2.2, tiles="CartoDB dark_matter", no_wrap=True)
    marker_cluster = MarkerCluster().add_to(m)
    
    for item in st.session_state.memory:
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=item['sum'],
            icon=folium.Icon(color='red' if item['threat'] > 7 else 'orange')
        ).add_to(marker_cluster)
    
    st_folium(m, width="100%", height=650)

with col_feed:
    st.subheader("📥 INTEL_STREAM")
    # PRIORIDAD 1: Noticias analizadas por IA
    if st.session_state.memory:
        for item in sorted(st.session_state.memory, key=lambda x: x['threat'], reverse=True):
            st.markdown(f"""<div class="intel-card {'critical' if item['threat'] > 7 else ''}">
                <small>[{item['loc'].upper()}]</small><br><strong>{item['title']}</strong></div>""", unsafe_allow_html=True)
    
    # PRIORIDAD 2: Si la IA falla, mostrar feed crudo para que no esté vacío
    elif st.session_state.raw_feed:
        st.warning("⚠️ MODO ANALÓGICO: IA sin cuota. Mostrando feed crudo.")
        for item in st.session_state.raw_feed[:10]:
            st.markdown(f"""<div class="intel-card emergency">
                <small>[RAW_SIGNAL]</small><br>{item['title']}</div>""", unsafe_allow_html=True)
    else:
        st.write("Radar ciego. Pulsa Escaneo de Emergencia.")

st.markdown("<p style='text-align:center; color:#1e293b; font-size:10px;'>AEGIS OMEGA - FALLBACK MODE ACTIVE</p>", unsafe_allow_html=True)
