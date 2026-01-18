import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from datetime import datetime

# --- CONFIGURACIÓN Y ESTÉTICA ---
st.set_page_config(page_title="AEGIS TERMINAL v2.0", layout="wide")
st.markdown("<style>.main { background-color: #0b0d17; color: #00ff41; }</style>", unsafe_allow_html=True)

st.title("🛰️ AEGIS TERMINAL: Live Intel Feed")

# --- GESTIÓN DE LA API KEY ---
# Nota: En Streamlit Cloud, pon esto en "Secrets" para que no te la roben.
# El código busca en el búnker 'Secrets' la etiqueta llamada "news_api_key"
API_KEY = st.secrets["news_api_key"]

def get_military_news(api_key):
    # Buscamos eventos de alto impacto bélico
    url = f'https://newsapi.org/v2/everything?q=(military OR army OR missile OR "border clash")&sortBy=publishedAt&apiKey={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('articles', [])
    return []

# --- BASE DE DATOS DE COORDENADAS (Simplificada para el Alpha) ---
# En una versión pro, usaríamos una IA para extraer la lat/lon de la noticia.
GEOMAP = {
    "Ukraine": [48.3794, 31.1656], "Russia": [61.524, 105.318], "Israel": [31.0461, 34.8516],
    "Taiwan": [23.6978, 120.9605], "Iran": [32.4279, 53.6880], "USA": [37.0902, -95.7129],
    "China": [35.8617, 104.1954], "Poland": [51.9194, 19.1451], "Yemen": [15.5527, 48.5164]
}

if API_KEY:
    articles = get_military_news(API_KEY)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB dark_matter")
        
        for art in articles[:15]: # Solo los últimos 15 eventos para no saturar
            # Buscamos si el país se menciona en el título
            for country, coords in GEOMAP.items():
                if country.lower() in art['title'].lower():
                    folium.Marker(
                        location=coords,
                        popup=f"<b>{art['source']['name']}</b>: {art['title']}",
                        icon=folium.Icon(color='red', icon='warning', prefix='fa')
                    ).add_to(m)
        
        st_folium(m, width=900, height=500)

    with col2:
        st.subheader("🔥 Últimos Despliegues")
        for art in articles[:10]:
            st.write(f"**{art['publishedAt'][:10]}**")
            st.write(f"[{art['title']}]({art['url']})")
            st.divider()
else:
    st.warning("Introduce tu API Key en la barra lateral para activar el radar.")
