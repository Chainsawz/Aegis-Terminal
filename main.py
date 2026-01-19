import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import requests
from google import genai
import json
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="AEGIS BABEL v7.6", layout="wide", initial_sidebar_state="expanded")

# --- CSS: ESTÉTICA CYBERPUNK BILINGÜE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    iframe { background-color: #000 !important; border: 1px solid #1e293b !important; border-radius: 8px; }
    .intel-card {
        background: rgba(15, 23, 42, 0.95);
        border: 1px solid #1e293b;
        border-left: 4px solid #3b82f6;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .critical { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.1); }
    .lang-label { font-size: 10px; color: #64748b; font-weight: bold; margin-top: 5px; }
    .link-btn { color: #3b82f6; text-decoration: none; font-size: 11px; font-weight: bold; }
    .link-btn:hover { color: #60a5fa; text-decoration: underline; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN DE SISTEMAS ---
try:
    client = genai.Client(api_key=st.secrets["gemini_api_key"])
    NEWS_API_KEY = st.secrets["news_api_key"]
except:
    st.error("🚨 ENLACE ROTO: Revisa tus API Keys.")
    st.stop()

# --- BÚFER DE MEMORIA (24H) ---
if 'memory' not in st.session_state: st.session_state.memory = []
if 'raw_feed' not in st.session_state: st.session_state.raw_feed = []

def update_memory(new_intel):
    existing_urls = {item['url'] for item in st.session_state.memory}
    for item in new_intel:
        if item['url'] not in existing_urls:
            item['timestamp'] = datetime.now()
            st.session_state.memory.append(item)
    cutoff = datetime.now() - timedelta(hours=24)
    st.session_state.memory = [i for i in st.session_state.memory if i['timestamp'] > cutoff]

# --- MOTOR IA BILINGÜE ---
def analyze_batch(articles):
    if not articles: return []
    news_list = [{"id": i, "t": a['title']} for i, a in enumerate(articles)]
    
    prompt = """Analyze military/geopolitics. Return ONLY JSON list:
    [{"id":int, "threat":1-10, "lat":float, "lon":float, "loc_en":"Country", "loc_es":"País", "sum_en":"Brief English", "sum_es":"Breve Español"}]
    Data: """ + json.dumps(news_list)
    
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
        return [{**articles[r['id']], **r} for r in data]
    except Exception as e:
        st.sidebar.warning(f"⚠️ IA en 'cooldown': {str(e)[:40]}")
        return []

def fetch_news():
    query = "(military OR war OR conflict OR NATO OR missile OR 'cyber attack')"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=15&apiKey={NEWS_API_KEY}'
    try:
        r = requests.get(url)
        return r.json().get('articles', []) if r.status_code == 200 else []
    except: return []

# --- INTERFAZ ---
st.markdown("<h2 style='color:#3b82f6; font-family:\"Share Tech Mono\";'>◢ AEGIS_BABEL_v7.6</h2>", unsafe_allow_html=True)

if st.sidebar.button("⚡ ESCANEO_TOTAL"):
    with st.spinner("Interceptando comunicaciones bilingües..."):
        raw = fetch_news()
        st.session_state.raw_feed = raw
        if raw:
            analyzed = analyze_batch(raw)
            update_memory(analyzed)
    st.rerun()

col_map, col_feed = st.columns([1.6, 1])

with col_map:
    # --- MAPA ANCLADO (v7.6) ---
    m = folium.Map(location=[15, 0], zoom_start=2.1, tiles=None, dragging=False, min_zoom=2.1, max_bounds=True, zoom_control=False, attributionControl=False)
    m.get_root().header.add_child(folium.Element("<style>.folium-map { background: #000 !important; }</style>"))
    folium.TileLayer(tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr='CartoDB', no_wrap=True, bounds=[[-90, -180], [90, 180]]).add_to(m)

    cluster = MarkerCluster().add_to(m)
    for item in st.session_state.memory:
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=f"<b>{item.get('loc_es', item.get('loc_en'))}</b><br>{item.get('sum_es', item.get('sum_en'))}",
            icon=folium.Icon(color='red' if item['threat'] > 7 else 'orange', icon='warning', prefix='fa')
        ).add_to(cluster)

    st_folium(m, height=520, use_container_width=True, key="aegis_babel_map")

with col_feed:
    st.subheader("📥 LIVE_BILINGUAL_STREAM")
    
    if not st.session_state.memory and not st.session_state.raw_feed:
        st.write("Radar en espera de datos tácticos.")
    elif not st.session_state.memory:
        st.warning("⚠️ IA SATURADA. Mostrando señales crudas.")
        for item in st.session_state.raw_feed[:10]:
            st.markdown(f"""<div class="intel-card"><a href="{item['url']}" target="_blank" class="link-btn">🔗 {item['title']}</a><br><div class="lang-label">ENG</div></div>""", unsafe_allow_html=True)
    else:
        # Mostrar noticias procesadas por la IA
        for item in sorted(st.session_state.memory, key=lambda x: x['threat'], reverse=True):
            t_style = "critical" if item['threat'] >
