import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Seiteneinstellungen
st.set_page_config(page_title="Vienna Powder Alert", page_icon="❄️", layout="wide")

# Datenbank der Skigebiete
SKIGEBIETE = {
    "Stuhleck": {"lat": 47.57, "lon": 15.79, "zeit": "75 Min.", "cam": "https://www.stuhleck.at/service/webcams/"},
    "Mönichkirchen": {"lat": 47.51, "lon": 15.99, "zeit": "65 Min.", "cam": "https://www.schischaukel.at/webcams"},
    "Annaberg": {"lat": 47.87, "lon": 15.37, "zeit": "100 Min.", "cam": "https://www.annaberg.info/webcams"},
    "Gemeindealpe": {"lat": 47.81, "lon": 15.28, "zeit": "120 Min.", "cam": "https://www.gemeindealpe.at/webcams"},
    "Ötscher": {"lat": 47.85, "lon": 15.15, "zeit": "130 Min.", "cam": "https://www.oetscher.at/webcams"},
    "Hochkar": {"lat": 47.73, "lon": 14.92, "zeit": "150 Min.", "cam": "https://www.hochkar.com/webcams"}
}

def get_weather_data():
    results = []
    base_url = "https://api.open-meteo.com/v1/forecast"
    
    for name, info in SKIGEBIETE.items():
        params = {
            "latitude": info['lat'],
            "longitude": info['lon'],
            "daily": "snowfall_sum",
            "timezone": "Europe/Berlin",
            "past_days": 1  # Holt die Daten von gestern dazu
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status() 
            data = response.json()
            
            snow_days = data['daily']['snowfall_sum']
            dates = data['daily']['time']
            
            # Index 0 ist Gestern, Index 1 ist Heute, Index 2 ist Morgen
            snow_past_24h = round(snow_days[0], 1)
            snow_next_24h = round(snow_days[1] + snow_days[2], 1)
            
            results.append({
                "Skigebiet": name,
                "lat": info['lat'],
                "lon": info['lon'],
                "Schnee Gestern (cm)": snow_past_24h,
                "Schnee Morgen (cm)": snow_next_24h,
                "Anfahrt": info['zeit'],
                "Webcam": info['cam'],
                "Woche": snow_days,
                "Daten": dates
            })
        except Exception as e:
            st.sidebar.error(f"Fehler bei {name}: {e}")
            continue
    return results

st.title("❄️ Vienna Powder Alert")

if st.button('🚀 Neuschnee-Check (Vergangenheit & Zukunft)'):
    with st.spinner('Daten werden analysiert...'):
        data = get_weather_data()
        
        if data:
            df = pd.DataFrame(data).sort_values(by="Schnee Morgen (cm)", ascending=False)
            
            # Powder Alarm Check
            if df["Schnee Morgen (cm)"].max() >= 30:
                st.balloons()
                st.success("🔥 POWDER ALARM für Morgen!")

            # 1. Metriken für die Top-Gebiete
            st.subheader("Top-Spots in der Nähe")
            cols = st.columns(3)
            for i, resort in enumerate(data[:3]):
                with cols[i]:
                    st.metric(
                        label=resort['Skigebiet'], 
                        value=f"{resort['Schnee Morgen (cm)']} cm Morgen", 
                        delta=f"{resort['Schnee Gestern (cm)']} cm Gestern"
                    )
                    st.link_button("📷 Webcam", resort['Webcam'])

            # 2. Komplette Tabelle
            st.divider()
            st.subheader("Alle Gebiete im Überblick")
            st.dataframe(df[["Skigebiet", "Schnee Gestern (cm)", "Schnee Morgen (cm)", "Anfahrt"]], use_container_width=True)

            # 3. Karte
            st.map(df, latitude='lat', longitude='lon', size=2000)
            
        else:
            st.error("Daten konnten nicht geladen werden.")

st.caption("Hinweis: 'Schnee Gestern' zeigt den tatsächlichen Schneefall der letzten 24h laut Wettermodell.")
