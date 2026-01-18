import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen
import requests
import google.generativeai as genai
import json
from datetime import datetime

# --- CONFIGURACIÓN DE ALTO NIVEL ---
st.set_page_config(page_title="AEGIS TACTICAL v4.0", layout="wide", initial_sidebar_state="collapsed")

# --- CSS PROFESIONAL (UX/UI REFINADO) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    .stApp {
        background-color: #080a0c;
        color: #e6e8eb;
        font-family: 'Inter', sans-serif;
    }
    
    /* Contenedor del Mapa */
    iframe {
        border-radius: 10px;
        border: 1px solid #1f2937;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }

    /* Tarjetas de Intel Stream */
    .intel-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-left: 3px solid #3b82f6;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 12px;
        font-size: 0.85rem;
    }
    .threat-critical { border-left-color: #ef4444; }
    .threat-high { border-left-color: #f97316; }

    /* Métricas Pulidas */
    [data-testid="stMetric"] {
        background: #111827;
        border: 1px solid #1f2937;
        padding: 15px;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE INTELIGENCIA ---
try:
    genai.configure(api_key=st.secrets["gemini_api_key"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    NEWS_API_KEY = st.secrets["news_api_key"]
except Exception as e:
    st.error("🚨 Error de conexión con el búnker de datos.")
    st.stop()

# --- FUNCIONES DE NÚCLEO ---
def analizar_con_ia(titulo, desc):
    prompt = f"Analyze military impact of: {titulo}. Respond ONLY JSON: {{\"is_mil\":bool, \"threat\":1-10, \"lat\":float, \"lon\":float, \"loc\":\"Name\"}}"
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text.replace('```json', '').replace('```', ''))
    except: return {"is_mil": False}

@st.cache_data(ttl=600)
def get_intel():
    url = f'https://newsapi.org/v2/everything?q=(military OR war OR missile)&sortBy=publishedAt&pageSize=12&apiKey={NEWS_API_KEY}'
    return requests.get(url).json().get('articles', [])

# --- INTERFAZ DE COMANDO ---
st.markdown("<h2 style='color:#3b82f6; margin-bottom:5px;'>◤ AEGIS TACTICAL COMMAND</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='color:#6b7280; font-family:\"JetBrains Mono\"; font-size:12px;'>SYSTEM_READY // STREAM_SYNC: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>", unsafe_allow_html=True)

# Dash de métricas rápido
m1, m2, m3, m4 = st.columns(4)
m1.metric("SENSORS_ACTIVE", "GLOBAL")
m2.metric("THREAT_INDEX", "ELEVATED", delta="MODERATE")
m3.metric("NODES", "ONLINE")
m4.metric("AI_ANALYST", "GEMINI_PRO")

col_map, col_feed = st.columns([3, 1])

with col_map:
    # --- CONFIGURACIÓN DEL MAPA PRO ---
    # world_copy_jump=False y no_wrap=True evitan la repetición
    m = folium.Map(
        location=[20, 0], 
        zoom_start=2.5, 
        tiles="CartoDB dark_matter",
        no_wrap=True,
        max_bounds=True,
        min_zoom=2,
        zoom_control=True
    )
    
    Fullscreen().add_to(m)
    marker_cluster = MarkerCluster().add_to(m)
    
    articles = get_intel()
    processed_intel = []

    for art in articles:
        intel = analizar_con_ia(art['title'], art['description'])
        if intel.get("is_mil"):
            processed_intel.append({**art, **intel})
            
            # Color basado en amenaza
            color = 'red' if intel['threat'] > 7 else 'orange'
            
            folium.Marker(
                location=[intel['lat'], intel['lon']],
                popup=f"<b>{intel['loc']}</b><br>{art['title']}",
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(marker_cluster)

    st_folium(m, width="100%", height=700, use_container_width=True)

with col_feed:
    st.markdown("### 📥 LIVE_INTEL_STREAM")
    if not processed_intel:
        st.write("Esperando datos del satélite...")
    for item in processed_intel:
        threat_class = "threat-critical" if item['threat'] > 7 else "threat-high"
        st.markdown(f"""
            <div class="intel-card {threat_class}">
                <strong style="color:#60a5fa;">{item['loc'].upper()} [LVL {item['threat']}]</strong><br>
                {item['title']}<br>
                <a href="{item['url']}" style="color:#3b82f6; text-decoration:none; font-size:11px;">→ VER FUENTE</a>
            </div>
            """, unsafe_allow_html=True)

st.markdown("<hr style='border:0.5px solid #1f2937'><p style='text-align:center; color:#4b5563; font-size:10px;'>CLASSIFIED INFORMATION - AEGIS CORP PROPRIETARY</p>", unsafe_allow_html=True)
