import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime

# Configuración estética Cyberpunk
st.set_page_config(page_title="AEGIS TERMINAL v1.0", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0b0d17; color: #00ff41; }
    h1 { color: #ff0055; text-shadow: 2px 2px #5d001e; font-family: 'Courier New'; }
    .stAlert { background-color: #1a1a1a; border: 1px solid #ff0055; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛰️ AEGIS TERMINAL: Global Military Watch (2026)")
st.write(f"Sincronizado con la Red: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")

# --- SIMULACIÓN DE DATOS (Lo que extraeremos con IA después) ---
data = [
    {"lat": 50.0755, "lon": 14.4378, "pueblo": "Europa Central", "status": "Alerta Roja", "info": "Maniobras de la OTAN - Despliegue de blindados."},
    {"lat": 23.6978, "lon": 120.9605, "pueblo": "Estrecho de Taiwán", "status": "Crítico", "info": "Incursión naval detectada. 12 destructores en zona."},
    {"lat": 34.0522, "lon": -118.2437, "pueblo": "Costa Oeste USA", "status": "Normal", "info": "Ejercicios de defensa costera rutinarios."},
    {"lat": 12.0000, "lon": 43.0000, "pueblo": "Bab el-Mandeb", "status": "Ataque en curso", "info": "Drones interceptados sobre buque comercial."}
]

# --- SIDEBAR: EL FEED DE NOTICIAS (THE ALPHA) ---
st.sidebar.header("⚠️ FEED DE INTELIGENCIA")
for d in data:
    with st.sidebar.expander(f"{d['pueblo']} - {d['status']}"):
        st.write(d['info'])

# --- EL MAPA DE GUERRA ---
col1, col2 = st.columns([3, 1])

with col1:
    m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB dark_matter")
    
    for d in data:
        color = "red" if d["status"] in ["Crítico", "Ataque en curso"] else "orange"
        folium.CircleMarker(
            location=[d["lat"], d["lon"]],
            radius=10,
            color=color,
            fill=True,
            fill_color=color,
            popup=f"{d['pueblo']}: {d['info']}"
        ).add_to(m)

    st_folium(m, width=900, height=500)

with col2:
    st.subheader("📊 Riesgo Global")
    st.metric(label="DEFCON LEVEL", value="3", delta="-1", delta_color="inverse")
    st.progress(75, text="Inestabilidad Geopolítica")
    st.info("Nota: Los datos mostrados son de fuentes OSINT públicas filtradas por IA.")

st.warning("DISCLAIMER: El uso de esta información para trading de futuros de petróleo es bajo tu propio riesgo, bro. No seas exit liquidity.")
