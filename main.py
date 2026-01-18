import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import google.generativeai as genai
import json
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AEGIS REPAIR v4.1", layout="wide")

try:
    genai.configure(api_key=st.secrets["gemini_api_key"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    NEWS_API_KEY = st.secrets["news_api_key"]
except:
    st.error("🚨 KEYS NO ENCONTRADAS EN SECRETS")
    st.stop()

# --- FUNCIÓN DE IA CON DEBUG ---
def analizar_con_ia(titulo):
    # Prompt ultra-simplificado para evitar errores de formato
    prompt = f"""
    Analiza: "{titulo}"
    Responde SOLO un JSON:
    {{"is_mil": true, "threat": 5, "lat": 20.0, "lon": 0.0, "loc": "Unknown"}}
    Si NO es sobre guerra/ejército, is_mil: false.
    """
    try:
        response = model.generate_content(prompt)
        # Limpieza agresiva de la respuesta
        clean_json = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean_json)
    except Exception as e:
        # Si la IA falla, lo registramos internamente
        return {"is_mil": False, "error": str(e)}

@st.cache_data(ttl=300)
def get_intel():
    # Ampliamos los términos de búsqueda para asegurar que traiga algo
    query = "(military OR war OR 'border' OR 'missile' OR 'defense')"
    url = f'https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=10&apiKey={NEWS_API_KEY}'
    r = requests.get(url)
    if r.status_code != 200:
        st.sidebar.error(f"Error NewsAPI: {r.status_code}")
        return []
    return r.json().get('articles', [])

# --- UI ---
st.title("◤ AEGIS DEBUG_MODE")

articles = get_intel()
processed_intel = []

if not articles:
    st.warning("⚠️ No se recibieron noticias de NewsAPI. ¿Has llegado al límite diario?")
else:
    st.info(f"📡 {len(articles)} noticias crudas recibidas. Analizando con IA...")
    
    for art in articles:
        intel = analizar_con_ia(art['title'])
        if intel.get("is_mil"):
            processed_intel.append({**art, **intel})

# --- MOSTRAR RESULTADOS ---
col_map, col_feed = st.columns([3, 1])

with col_map:
    m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB dark_matter")
    for item in processed_intel:
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=item['title']
        ).add_to(m)
    st_folium(m, width="100%", height=600)

with col_feed:
    st.subheader("📥 LIVE STREAM")
    if not processed_intel:
        st.error("❌ La IA descartó todas las noticias o hubo un error de formato.")
    for item in processed_intel:
        st.markdown(f"**[{item['loc']}]** {item['title']}")
        st.divider()
