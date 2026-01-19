import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen
import requests
from google import genai
import json
from datetime import datetime

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(
    page_title="AEGIS TACTICAL v4.3", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS: ESTÉTICA DE ALTO NIVEL (GLASSMORPHISM & STEALTH) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono&display=swap');
    
    .stApp {
        background: #020617; /* Fondo ultra oscuro */
        color: #f1f5f9;
        font-family: 'Inter', sans-serif;
    }

    /* Contenedor del Mapa con bordes de neón sutil */
    iframe {
        border-radius: 12px;
        border: 1px solid #1e293b;
        box-shadow: 0 4px 20px rgba(0,0,0,0.8);
    }

    /* Tarjetas de Intel Stream */
    .intel-card {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid #1e293b;
        border-left: 4px solid #3b82f6;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        backdrop-filter: blur(8px);
    }
    .critical { border-left-color: #ef4444; }
    .high { border-left-color: #f97316; }

    /* Métricas */
    [data-testid="stMetric"] {
        background: #0f172a;
        border: 1px solid #1e293b;
        padding: 15px;
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN CON EL BÚNKER (API KEYS) ---
try:
    client = genai.Client(api_key=st.secrets["gemini_api_key"])
    NEWS_API_KEY = st.secrets["news_api_key"]
except Exception as e:
    st.error("🚨 FALLO EN CREDENCIALES: Verifica tus Secrets.")
    st.stop()

# --- CEREBRO: ANALISTA IA GEMINI 2.0 ---
def analizar_con_ia(titulo, descripcion):
    # Prompt optimizado para evitar alucinaciones y asegurar JSON puro
    prompt = f"""
    Analyze: "{titulo}. {descripcion}"
    Return ONLY JSON:
    {{
        "is_mil": bool,
        "threat": int(1-10),
        "lat": float,
        "lon": float,
        "location": "City/Region",
        "summary": "Short technical briefing"
    }}
    If not military/conflict related, is_mil: false.
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt
        )
        res_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(res_text)
    except:
        return {"is_mil": False}

# --- SUMINISTRO: NEWS API ---
@st.cache_data(ttl=600)
def fetch_global_intel():
    query = "(military OR war OR missile OR 'border clash' OR 'airstrike')"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=12&apiKey={NEWS_API_KEY}'
    try:
        r = requests.get(url)
        return r.json().get('articles', [])
    except:
        return []

# --- DASHBOARD PRINCIPAL ---
st.markdown("<h1 style='color:#3b82f6;'>◤ AEGIS_TACTICAL_COMMAND_v4.3</h1>", unsafe_allow_html=True)

# Sidebar de Control
st.sidebar.markdown("### 🛰️ RADAR_STATUS")
st.sidebar.success("SENSORS: ACTIVE")
st.sidebar.info(f"SYNC_UTC: {datetime.now().strftime('%H:%M:%S')}")

if st.sidebar.button("🔄 FORCE_RESCAN"):
    st.cache_data.clear()
    st.rerun()

# Métricas de la Red
m1, m2, m3 = st.columns(3)
m1.metric("GLOBAL_THREAT", "ELEVATED", "DEFCON 3")
m2.metric("AI_ANALYST", "GEMINI_2.0", "OPTIMAL")
m3.metric("OSINT_FEED", "SYNCED", "LIVE")

st.divider()

# --- CORE: MAPA Y FEED DE INTELIGENCIA ---
articles = fetch_global_intel()
processed_data = []

col_map, col_feed = st.columns([2.5, 1])

with col_map:
    # --- AJUSTE DE MAPA: SIN REPETICIÓN Y ZOOM BLOQUEADO ---
    # Definimos el área visible del mundo para evitar el vacío
    m = folium.Map(
        location=[20, 0], 
        zoom_start=2.3, 
        tiles="CartoDB dark_matter",
        no_wrap=True,           # Mata la repetición horizontal
        min_zoom=2.3,           # No deja que el usuario se aleje más de la cuenta
        max_bounds=True,        # Activa el límite de scroll
        min_lat=-85, max_lat=85,
        min_lon=-180, max_lon=180
    )
    
    # Marcadores con clustering para evitar líos visuales
    marker_cluster = MarkerCluster().add_to(m)
    Fullscreen().add_to(m)

    if articles:
        with st.spinner("Decodificando transmisiones satelitales..."):
            for art in articles:
                intel = analizar_con_ia(art['title'], art['description'])
                if intel.get("is_mil"):
                    processed_data.append({**art, **intel})
                    # Color del marcador según nivel de amenaza
                    color = 'red' if intel['threat'] >= 8 else 'orange'
                    folium.Marker(
                        location=[intel['lat'], intel['lon']],
                        popup=f"<b>{intel['location']}</b><br>{intel['summary']}",
                        icon=folium.Icon(color=color, icon='warning', prefix='fa')
                    ).add_to(marker_cluster)

    st_folium(m, width="100%", height=720, use_container_width=True)

with col_feed:
    st.markdown("### 📥 LIVE_INTEL_STREAM")
    if not processed_data:
        st.write("Esperando señal... Radar despejado.")
    
    for item in processed_data:
        t_style = "critical" if item['threat'] >= 8 else "high"
        st.markdown(f"""
            <div class="intel-card {t_style}">
                <strong style="color:#60a5fa;">[{item['location'].upper()}] - AMENAZA: {item['threat']}</strong><br>
                <span style="font-size:13px;">{item['title']}</span><br>
                <div style="margin-top:10px;">
                    <a href="{item['url']}" target="_blank" style="color:#3b82f6; text-decoration:none; font-size:11px;">[ACCEDER_AL_ALPHA]</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("<p style='text-align:center; color:#1e293b; font-size:10px; margin-top:50px;'>PROPERTY OF AEGIS CORP - ENCRYPTED TERMINAL v4.3</
