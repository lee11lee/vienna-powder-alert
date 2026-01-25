import streamlit as st
import pandas as pd
import json
import urllib.request
from datetime import datetime

# Seiteneinstellungen für Mobile-Optimierung
st.set_page_config(
    page_title="Vienna Powder Alert",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS für schöneres Design
st.markdown("""
    <style>
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

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
    # Header, um API-Blockaden zu vermeiden
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for name, info in SKIGEBIETE.items():
        url = f"https://api.open-meteo.com/v1/forecast?latitude={info['lat']}&longitude={info['lon']}&daily=snowfall_sum&timezone=Europe%2Berlin"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
            
            snow_days = data['daily']['snowfall_sum']
            dates = data['daily']['time']
            # Heute + Morgen Summe für den Powder-Check
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
            st.sidebar.warning(f"Fehler bei {name}: {str(e)}")
            continue
    return results

# --- UI START ---
st.title("❄️ Vienna Powder Alert")
st.write("Checkt den Neuschnee der nächsten 24h in der Umgebung von Wien.")

if st.button('🚀 Jetzt Powder-Check starten'):
    with st.spinner('Frage Wetterdaten ab...'):
        data = get_weather_data()
        
        if data:
            df = pd.DataFrame(data).sort_values(by="Neuschnee (cm)", ascending=False)
            
            # 1. Powder Alarm Banner
            max_snow = df["Neuschnee (cm)"].max()
            if max_snow >= 30:
                st.balloons()
                st.success(f"🔥 MASSIVER POWDER ALARM! Bis zu {max_snow} cm Neuschnee erwartet!")
            elif max_snow >= 15:
                st.info(f"Gute Bedingungen: Bis zu {max_snow} cm Neuschnee.")
            else:
                st.warning("Kein großer Powder in Sicht. Check die 7-Tage-Prognose unten.")

            # 2. Karte
            st.subheader("📍 Skigebiete Map")
            # Marker-Farbe: Blau wenn Schnee, Grau wenn wenig
            df['color'] = df['Neuschnee (cm)'].apply(lambda x: '#0044ff' if x >= 10 else '#a0a0a0')
            st.map(df, latitude='lat', longitude='lon', color='color', size=2000)

            # 3. Top Gebiete Kacheln
            st.divider()
            st.subheader("Beste Optionen für morgen")
            cols = st.columns(min(len(data), 3))
            for i, resort in enumerate(data[:3]):
                with cols[i]:
                    st.metric(label=resort['Skigebiet'], value=f"{resort['Neuschnee (cm)']} cm", delta=f"🚗 {resort['Anfahrt']}")
                    st.link_button("📷 Webcam", resort['Webcam'])

            # 4. 7-Tage Details
            st.divider()
            st.subheader("📅 7-Tage Neuschnee-Vorschau")
            for r in data:
                with st.expander(f"Details & Woche für {r['Skigebiet']}"):
                    week_df = pd.DataFrame({
                        "Datum": [datetime.strptime(d, '%Y-%m-%d').strftime('%a, %d.%m.') for d in r['Daten']],
                        "Neuschnee (cm)": r['Woche']
                    }).set_index("Datum")
                    st.bar_chart(week_df)
                    st.table(week_df.T)
        else:
            st.error("Keine Daten empfangen. Eventuell ist die API temporär nicht erreichbar.")

st.divider()
st.caption("Datenquelle: Open-Meteo API | Entfernungen ab Wien Zentrum | 24h = Heute + Morgen Summe")
