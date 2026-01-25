import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Seiteneinstellungen
st.set_page_config(page_title="Vienna Powder Alert", page_icon="❄️", layout="wide")

st.title("❄️ Vienna Powder Alert")
st.write("Echtzeit-Check der Schneevorhersage für Skigebiete nah bei Wien.")

# Datenbank
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
    for name, info in SKIGEBIETE.items():
        url = f"https://api.open-meteo.com/v1/forecast?latitude={info['lat']}&longitude={info['lon']}&daily=snowfall_sum&timezone=Europe%2Berlin"
        
        try:
            # Nutzung der 'requests' Library mit Timeout
            response = requests.get(url, timeout=10)
            response.raise_for_status() # Prüft auf HTTP Fehler
            data = response.json()
            
            snow_days = data['daily']['snowfall_sum']
            dates = data['daily']['time']
            # Heute + Morgen Summe
            snow_next_24h = round(snow_days[0] + snow_days[1], 1)
            
            results.append({
                "Skigebiet": name,
                "lat": info['lat'],
                "lon": info['lon'],
                "Neuschnee (cm)": snow_next_24h,
                "Anfahrt": info['zeit'],
                "Webcam": info['cam'],
                "Woche": snow_days,
                "Daten": dates
            })
        except Exception as e:
            st.error(f"Verbindungsfehler bei {name}: {e}")
            continue
    return results

if st.button('🚀 Powder-Check starten'):
    with st.spinner('Daten werden geladen...'):
        data = get_weather_data()
        
        if data:
            df = pd.DataFrame(data).sort_values(by="Neuschnee (cm)", ascending=False)
            
            # 1. Großer Alarm
            max_snow = df["Neuschnee (cm)"].max()
            if max_snow >= 30:
                st.balloons()
                st.success(f"🔥 POWDER ALARM! {max_snow}cm Neuschnee!")
            
            # 2. Karte
            st.subheader("📍 Übersichtskarte")
            df['color'] = df['Neuschnee (cm)'].apply(lambda x: '#0000ff' if x >= 10 else '#808080')
            st.map(df, latitude='lat', longitude='lon', color='color', size=2500)

            # 3. Details
            st.subheader("Ergebnisse")
            st.dataframe(df[["Skigebiet", "Neuschnee (cm)", "Anfahrt"]], use_container_width=True)
            
            for r in data:
                with st.expander(f"7-Tage Trend: {r['Skigebiet']}"):
                    chart_data = pd.DataFrame({"Datum": r['Daten'], "Schnee": r['Woche']}).set_index("Datum")
                    st.bar_chart(chart_data)
                    st.link_button(f"Live-Webcam {r['Skigebiet']}", r['Webcam'])
        else:
            st.error("Es konnten keine Daten geladen werden. Bitte kontrolliere die 'Logs' in Streamlit.")
