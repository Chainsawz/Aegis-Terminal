import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA Y CSS DE VANGUARDIA ---
st.set_page_config(page_title="AEGIS OBSIDIAN v3.5", layout="wide")

st.markdown("""
    <style>
    /* Fondo principal y fuentes */
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
    
    .stApp {
        background: radial-gradient(circle, #1a1a1a 0%, #050505 100%);
        color: #e0e0e0;
        font-family: 'Share Tech Mono', monospace;
    }

    /* Tarjetas de noticias (Glassmorphism) */
    .intel-card {
        background: rgba(255, 255, 255, 0.03);
        border-left: 4px solid #ff0055;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
        transition: 0.3s;
    }
    .intel-card:hover {
        background: rgba(255, 255, 255, 0.08);
        border-left: 4px solid #00f2ff;
    }

    /* Header Estilizado */
    .header-box {
        border-bottom: 2px solid #333;
        padding-bottom: 20px;
        margin-bottom: 30px;
        display: flex;
        justify-content: space-between;
    }
    
    .status-glow {
        color: #00f2ff;
        text-shadow: 0 0 10px #00f2ff;
    }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER SISTEMA ---
st.markdown(f"""
    <div class="header-box">
        <h1 style="margin:0; color:#ff0055;">◢ AEGIS_TERMINAL_V3.5</h1>
        <div style="text-align:right;">
            <span class="status-glow">● SYSTEM_ONLINE</span><br>
            <small style="color:#666;">UTC: {datetime.now().strftime('%H:%M:%S')}</small>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- DASHBOARD METRICS ---
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.metric(label="WAR_ZONES_ACTIVE", value="12", delta="+2")
with col_m2:
    st.metric(label="THREAT_LEVEL", value="ORANGE", delta="HIGH")
with col_m3:
    st.metric(label="INTEL_FEED_LATENCY", value="45ms", delta="STABLE")
with col_m4:
    st.metric(label="AI_CONFIDENCE", value="94%", delta="OPTIMAL")

st.write("---")

# --- LÓGICA DE DATOS (Simplificada para el ejemplo visual) ---
# Aquí iría tu conexión a NewsAPI y Gemini
mock_news = [
    {"title": "Escalación en el Estrecho de Taiwán: Maniobras Navales detectadas", "source": "Reuters", "threat": "HIGH"},
    {"title": "Movimientos de blindados en la frontera Norte de Ucrania", "source": "OSINT_Daily", "threat": "CRITICAL"},
    {"title": "Nuevo ensayo de misiles hipersónicos en el Pacífico", "source": "AP News", "threat": "MEDIUM"}
]

# --- LAYOUT PRINCIPAL ---
main_col, side_col = st.columns([2, 1])

with main_col:
    st.subheader("🌐 GLOBAL_TACTICAL_MAP")
    # Mapa con estilo oscuro minimalista
    m = folium.Map(location=[20, 10], zoom_start=2, tiles="CartoDB dark_matter", zoom_control=False)
    # Ejemplo de marcador estético
    folium.CircleMarker(
        location=[23.69, 120.96], radius=15, color="#ff0055", fill=True, fill_opacity=0.2,
        popup="TAIWAN_STRAIT: HIGH_TENSION"
    ).add_to(m)
    
    st_folium(m, width="100%", height=550)

with side_col:
    st.subheader("📥 LIVE_INTEL_STREAM")
    for news in mock_news:
        color = "#ff0055" if news['threat'] == "CRITICAL" else "#00f2ff"
        st.markdown(f"""
            <div class="intel-card" style="border-left-color: {color};">
                <small style="color:{color}; font-weight:bold;">[{news['threat']}]</small><br>
                <span style="font-size:14px;">{news['title']}</span><br>
                <small style="color:#666;">Source: {news['source']}</small>
            </div>
            """, unsafe_allow_html=True)

st.markdown("<br><br><p style='text-align:center; color:#333;'>PROPERTY OF AEGIS CORP - UNIFIED DEFENSE INTERFACE</p>", unsafe_allow_html=True)
