import streamlit as st
import pydeck as pdk
import pandas as pd
import requests
from google import genai
import json
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="AEGIS SPECTRE v6.0", layout="wide", initial_sidebar_state="expanded")

# --- CSS: ESTÉTICA DE TERMINAL DE OPERACIONES ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono&display=swap');
    .stApp { background: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    .intel-card {
        background: rgba(15, 23, 42, 0.95);
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
    st.error(f"🚨 FALLO DE ENLACE: {e}")
    st.stop()

# --- BÚFER DE MEMORIA (PERSISTENCIA 24H) ---
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

# --- MOTOR IA POR LOTES ---
def analyze_batch_intel(articles):
    if not articles: return []
    news_list = [{"id": i, "t": a['title']} for i, a in enumerate(articles)]
    prompt = f"Analyze military news. Return ONLY JSON list: [{{'id':int, 'threat':1-10, 'lat':float, 'lon':float, 'loc':'City', 'sum':'brief'}}]. Data: {json.dumps(news_list)}"
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        res_text = response.text.strip().replace('```json', '').replace('```', '')
        analyzed = json.loads(res_text)
        return [{**articles[r['id']], **r} for r in analyzed]
    except: return []

def fetch_news():
    query = "(military OR war OR missile OR 'border conflict')"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=15&apiKey={NEWS_API_KEY}'
    try:
        r = requests.get(url)
        return r.json().get('articles', []) if r.status_code == 200 else []
    except: return []

# --- INTERFAZ ---
st.markdown("<h1 style='color:#3b82f6;'>◤ AEGIS_SPECTRE_v6.0</h1>", unsafe_allow_html=True)

if st.sidebar.button("⚡ ESCANEO GLOBAL"):
    with st.spinner("Sincronizando satélites..."):
        raw = fetch_news()
        st.session_state.raw_feed = raw
        if raw:
            analyzed = analyze_batch_intel(raw)
            update_memory(analyzed)
    st.rerun()

m1, m2, m3 = st.columns(3)
m1.metric("NODOS_IA", len(st.session_state.memory), "24H")
m2.metric("MOTOR_GRÁFICO", "PYDECK_WEBGL")
m3.metric("STATUS", "LOCKED")

st.divider()

col_map, col_feed = st.columns([2.5, 1])

with col_map:
    # --- MOTOR DE MAPA PYDECK (v6.0) ---
    # Creamos un DataFrame con los puntos de inteligencia
    if st.session_state.memory:
        df = pd.DataFrame(st.session_state.memory)
        # Definimos colores según amenaza: Rojo (Critical) u Naranja (High)
        df['color_r'] = df['threat'].apply(lambda x: 239 if x > 7 else 249)
        df['color_g'] = df['threat'].apply(lambda x: 68 if x > 7 else 115)
        df['color_b'] = df['threat'].apply(lambda x: 68 if x > 7 else 22)
    else:
        df = pd.DataFrame(columns=['lat', 'lon', 'color_r', 'color_g', 'color_b', 'loc'])

    # Capa de puntos tácticos
    layer = pdk.Layer(
        "ScatterplotLayer",
        df,
        get_position='[lon, lat]',
        get_color='[color_r, color_g, color_b, 160]',
        get_radius=200000,
        pickable=True,
    )

    # Vista del mapa BLOQUEADA
    view_state = pdk.ViewState(
        latitude=20,
        longitude=0,
        zoom=1.2,
        pitch=0,
        bearing=0
    )

    # Renderizado final con estilo Dark nativo de Mapbox/Pydeck
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v11", # Estilo ultra-oscuro profesional
        tooltip={"text": "{loc}\n{sum}"}
    ))
    

with col_feed:
    st.subheader("📥 LIVE_STREAM_24H")
    if st.session_state.memory:
        sorted_intel = sorted(st.session_state.memory, key=lambda x: x['threat'], reverse=True)
        for item in sorted_intel:
            t_style = "critical" if item['threat'] > 7 else ""
            st.markdown(f"""<div class="intel-card {t_style}">
                <small>[{item['loc'].upper()}] - AMENAZA: {item['threat']}</small><br>
                <strong>{item['title']}</strong><br>
                </div>""", unsafe_allow_html=True)
    elif st.session_state.raw_feed:
        st.info("📡 Señales crudas detectadas.")
        for item in st.session_state.raw_feed[:10]:
            st.markdown(f"<div class='intel-card'><strong>{item['title']}</strong></div>", unsafe_allow_html=True)
    else:
        st.write("Radar en espera.")

st.markdown("<p style='text-align:center; color:#1e293b; font-size:10px; margin-top:30px;'>PROPERTY OF AEGIS CORP - SPECTRE TERMINAL v6.0</p>", unsafe_allow_html=True)
