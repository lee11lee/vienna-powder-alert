import streamlit as st
import pandas as pd
import json
from urllib.request import urlopen
from datetime import datetime

# Seiteneinstellungen
st.set_page_config(page_title="Vienna Powder Alert", page_icon="❄️", layout="wide")

# Styling für die App
st.markdown("""
    <style>
    .main {
        background-color: #f0f2f6;
    }
    stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("❄️ Vienna Powder Alert")
st.subheader("Finde den Neuschnee (>30cm) um Wien")

# Datenbank der Gebiete
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
        # API Abfrage für 7 Tage (Schneefall-Summe pro Tag)
        url = f"https://api.open-meteo.com/v1/forecast?latitude={info['lat']}&longitude={info['lon']}&daily=snowfall_sum&timezone=Europe%2Berlin"
        try:
            with urlopen(url) as response:
                data = json.loads(response.read().decode())
            
            snow_days = data['daily']['snowfall_sum']
            dates = data['daily']['time']
            # Wir nehmen heute + morgen als relevanten Powder-Zeitraum
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
        except:
            continue
    return results

# Haupt-Interaktion
if st.button('🚀 Powder-Check jetzt ausführen'):
    with st.spinner('Frage Bergwetter-Daten ab...'):
        data = get_weather_data()
        
        if data:
            df = pd.DataFrame(data).sort_values(by="Neuschnee (cm)", ascending=False)
            
            # Karte anzeigen
            st.subheader("📍 Wo liegt der Schnee?")
            df['color'] = df['Neuschnee (cm)'].apply(lambda x: '#0000FF' if x >= 30 else '#A9A9A9')
            st.map(df, latitude='lat', longitude='lon', color='color', size=2500)

            # Top Gebiete als Metriken
            st.divider()
            cols = st.columns(3)
            for i, resort in enumerate(data[:3]):
                with cols[i % 3]:
                    st.metric(label=resort['Skigebiet'], value=f"{resort['Neuschnee (cm)']} cm", delta=f"🚗 {resort['Anfahrt']}")
                    st.link_button("📷 Webcam", resort['Webcam'])

            # 7-Tage-Check
            st.divider()
            st.subheader("📅 7-Tage-Prognose im Detail")
            for r in data:
                with st.expander(f"Details für {r['Skigebiet']} anzeigen"):
                    week_df = pd.DataFrame({
                        "Datum": [datetime.strptime(d, '%Y-%m-%d').strftime('%d.%m.') for d in r['Daten']],
                        "Schnee (cm)": r['Woche']
                    }).set_index("Datum")
                    st.bar_chart(week_df)
                    st.table(week_df.T)

            if df["Neuschnee (cm)"].max() >= 30:
                st.balloons()
                st.success("🔥 POWDER ALARM! Über 30cm Neuschnee in Sicht!")
        else:
            st.error("Konnte keine Daten von der Wetter-API empfangen.")

st.caption("Datenquelle: Open-Meteo API. Entfernungen ab Wien Zentrum (Durchschnitt).")
