import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import requests
from google import genai
import json
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="AEGIS OMNI v7.7", layout="wide", initial_sidebar_state="expanded")

# --- CSS: ESTÉTICA DE TERMINAL DE OPERACIONES ---
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
    .lang-label { font-size: 10px; color: #64748b; font-weight: bold; margin-top: 5px; text-transform: uppercase; }
    .link-btn { color: #3b82f6; text-decoration: none; font-size: 11px; font-weight: bold; border: 1px solid #3b82f6; padding: 2px 5px; border-radius: 4px; }
    .link-btn:hover { background: #3b82f6; color: #fff; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN DE SISTEMAS ---
try:
    client = genai.Client(api_key=st.secrets["gemini_api_key"])
    NEWS_API_KEY = st.secrets["news_api_key"]
except Exception as e:
    st.error(f"🚨 FALLO DE ENLACE API: {e}")
    st.stop()

# --- BÚFER DE MEMORIA (24H PERSISTENCIA) ---
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
        res_text = response.text.strip().replace('```json', '').replace('```', '')
        data = json.loads(res_text)
        return [{**articles[r['id']], **r} for r in data]
    except Exception: return []

def fetch_news():
    query = "(military OR war OR conflict OR NATO OR missile OR 'border clash')"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=15&apiKey={NEWS_API_KEY}'
    try:
        r = requests.get(url)
        return r.json().get('articles', []) if r.status_code == 200 else []
    except: return []

# --- INTERFAZ ---
st.markdown("<h2 style='color:#3b82f6; font-family:\"Share Tech Mono\";'>◢ AEGIS_OMNI_v7.7</h2>", unsafe_allow_html=True)

if st.sidebar.button("⚡ SINCRONIZACIÓN TÁCTICA"):
    with st.spinner("Interceptando comunicaciones bilingües..."):
        raw = fetch_news()
        st.session_state.raw_feed = raw
        if raw:
            analyzed = analyze_batch(raw)
            update_memory(analyzed)
    st.rerun()

col_map, col_feed = st.columns([1.6, 1])

with col_map:
    # --- MAPA ANCLADO (v7.7) ---
    m = folium.Map(location=[15, 0], zoom_start=2.1, tiles=None, dragging=False, min_zoom=2.1, max_bounds=True, zoom_control=False, attributionControl=False)
    m.get_root().header.add_child(folium.Element("<style>.folium-map { background: #000 !important; }</style>"))
    folium.TileLayer(tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr='CartoDB', no_wrap=True, bounds=[[-90, -180], [90, 180]]).add_to(m)

    cluster = MarkerCluster().add_to(m)
    for item in st.session_state.memory:
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=f"<b>{item.get('loc_es', item.get('loc_en'))}</b><br>{item.get('sum_es', item.get('sum_en'))}",
            icon=folium.Icon(color='red' if item.get('threat', 0) > 7 else 'orange', icon='warning', prefix='fa')
        ).add_to(cluster)

    st_folium(m, height=520, use_container_width=True, key="aegis_omni_map")

with col_feed:
    st.subheader("📥 LIVE_INTEL_STREAM")
    st.metric("NODOS_IA", len(st.session_state.memory), "24H")
    
    if not st.session_state.memory and not st.session_state.raw_feed:
        st.write("Radar en espera de datos tácticos.")
    elif not st.session_state.memory:
        st.warning("⚠️ IA SATURADA. Mostrando señales crudas.")
        for item in st.session_state.raw_feed[:10]:
            st.markdown(f"""<div class="intel-card"><a href="{item['url']}" target="_blank" style="color:inherit; text-decoration:none;"><strong>{item['title']}</strong></a><br><div class="lang-label">RAW_ENG</div></div>""", unsafe_allow_html=True)
    else:
        for item in sorted(st.session_state.memory, key=lambda x: x.get('threat', 0), reverse=True):
            t_style = "critical" if item.get('threat', 0) > 7 else ""
            st.markdown(f"""
                <div class="intel-card {t_style}">
                    <a href="{item['url']}" target="_blank" style="color:inherit; text-decoration:none;">
                        <strong>{item['title']}</strong>
                    </a><br>
                    <div class="lang-label">ESP</div>
                    <span style="font-size:13px;">{item.get('sum_es', 'No disponible')}</span>
                    <div class="lang-label">ENG</div>
                    <span style="font-size:12px; opacity:0.8;">{item.get('sum_en', 'No disponible')}</span>
                    <div style="margin-top:12px;">
                        <a href="{item['url']}" target="_blank" class="link-btn">📂 [ACCEDER_AL_ALPHA]</a>
                    </div>
                </div>
            """, unsafe_allow_html=True)

st.markdown("<p style='text-align:center; color:#1e293b; font-size:10px; margin-top:20px;'>PROPERTY OF AEGIS CORP - OMNI TERMINAL v7.7</p>", unsafe_allow_html=True)
