import streamlit as st
import folium
from streamlit_folium import st_folium
import requests

# --- ESTILO CYBERPUNK RADICAL ---
st.set_page_config(page_title="AEGIS TERMINAL | OSINT", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00ff41; }
    .css-1d391kg { background-color: #0a0a0a; } /* Sidebar */
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN CON EL BÚNKER (SECRETS) ---
try:
    API_KEY = st.secrets["news_api_key"]
except:
    st.error("⚠️ Error: No encuentro la API Key en los Secrets de Streamlit.")
    st.stop()

# --- DICCIONARIO DE GUERRA EXPANDIDO ---
# Añadimos ciudades y regiones calientes para que el mapa no esté desierto
WAR_ZONES = {
    "Ucrania": {"coords": [48.37, 31.16], "keywords": ["ukraine", "kyiv", "donbas", "kharkiv", "zelensky", "bakhmut"]},
    "Taiwán": {"coords": [23.69, 120.96], "keywords": ["taiwan", "taipei", "strait", "tsmc", "pla navy"]},
    "Medio Oriente": {"coords": [31.04, 34.85], "keywords": ["israel", "gaza", "lebanon", "iran", "tehran", "tel aviv", "hezbollah"]},
    "Mar Rojo": {"coords": [15.55, 48.51], "keywords": ["yemen", "houthis", "red sea", "bab el-mandeb"]},
    "Coreas": {"coords": [38.33, 127.23], "keywords": ["pyongyang", "seoul", "kim jong un", "dmz", "missile test"]},
    "África Sahel": {"coords": [12.23, -1.52], "keywords": ["mali", "niger", "burkina faso", "coup", "wagner group"]}
}

def get_live_intel(api_key):
    # Ampliamos la búsqueda: ahora rastreamos TODO lo relacionado con conflicto
    query = "(war OR military OR explosion OR missile OR attack OR invasion OR 'state of emergency')"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=40&apiKey={api_key}'
    r = requests.get(url)
    return r.json().get('articles', []) if r.status_code == 200 else []

st.title("🔴 AEGIS TERMINAL: LIVE TACTICAL FEED")

articles = get_live_intel(API_KEY)

col1, col2 = st.columns([3, 1])

with col1:
    # Mapa estilo "Satélite Nocturno"
    m = folium.Map(location=[20, 10], zoom_start=2, tiles="CartoDB dark_matter")
    
    intel_count = 0
    for art in articles:
        text = (art['title'] + " " + (art['description'] or "")).lower()
        
        for zone, data in WAR_ZONES.items():
            if any(key in text for key in data["keywords"]):
                intel_count += 1
                # Marcadores personalizados: Círculos de "pulsación" roja
                folium.CircleMarker(
                    location=data["coords"],
                    radius=12,
                    color="#ff0000",
                    fill=True,
                    fill_color="#ff0000",
                    fill_opacity=0.4,
                    popup=f"<b>{zone}</b><br>{art['title']}"
                ).add_to(m)
                break # Para no repetir el mismo evento en el mismo sitio

    st_folium(m, width=1000, height=600)
    st.write(f"📡 {intel_count} eventos tácticos detectados en las últimas 24h.")

with col2:
    st.subheader("⚠️ INTEL STREAM")
    for art in articles[:15]:
        with st.expander(f"NEWS: {art['source']['name']}"):
            st.write(f"**{art['title']}**")
            st.caption(art['publishedAt'])
            st.write(f"[Ver satélite/fuente]({art['url']})")
