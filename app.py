import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Seiteneinstellungen für Mobile-Ansicht
st.set_page_config(
    page_title="Vienna Powder Alert",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Design-Optimierung
st.markdown("""
    <style>
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    [data-testid="stMetricValue"] {
        color: #0044ff;
    }
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
    base_url = "https://api.open-meteo.com/v1/forecast"
    
    for name, info in SKIGEBIETE.items():
        # Parameter als Dictionary übergeben (verhindert 400 Bad Request)
        params = {
            "latitude": info['lat'],
            "longitude": info['lon'],
            "daily": "snowfall_sum",
            "timezone": "Europe/Berlin"
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status() 
            data = response.json()
            
            snow_days = data['daily']['snowfall_sum']
            dates = data['daily']['time']
            
            # Neuschnee Vorhersage (Heute + Morgen Summe)
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
            st.sidebar.error(f"Fehler bei {name}: {e}")
            continue
    return results

# --- UI ---
st.title("❄️ Vienna Powder Alert")
st.write(f"Stand: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

if st.button('🚀 Jetzt Powder-Check starten'):
    with st.spinner('Wetter-Götter werden befragt...'):
        data = get_weather_data()
        
        if data:
            df = pd.DataFrame(data).sort_values(by="Neuschnee (cm)", ascending=False)
            
            # 1. Großer Alarm Check (30cm Regel)
            max_snow = df["Neuschnee (cm)"].max()
            if max_snow >= 30:
                st.balloons()
                st.success(f"🔥 FETTER POWDER ALARM! {max_snow}cm Neuschnee gemeldet!")
            elif max_snow >= 10:
                st.info(f"Gute Bedingungen: Bis zu {max_snow}cm Neuschnee.")
            else:
                st.warning("Aktuell kein massiver Neuschnee vorhergesagt.")

            # 2. Karte
            st.subheader("📍 Skigebiete Map")
            df['color'] = df['Neuschnee (cm)'].apply(lambda x: '#0044ff' if x >= 10 else '#a0a0a0')
            st.map(df, latitude='lat', longitude='lon', color='color', size=2500)

            # 3. Top 3 Gebiete
            st.divider()
            st.subheader("Beste Optionen (nächste 24h)")
            cols = st.columns(min(len(data), 3))
            for i, resort in enumerate(data[:3]):
                with cols[i]:
                    st.metric(label=resort['Skigebiet'], value=f"{resort['Neuschnee (cm)']} cm", delta=f"🚗 {resort['Anfahrt']}")
                    st.link_button("📷 Webcam", resort['Webcam'])

            # 4. 7-Tage-Check
            st.divider()
            st.subheader("📅 Die nächsten 7 Tage")
            for r in data:
                with st.expander(f"Details für {r['Skigebiet']} anzeigen"):
                    chart_data = pd.DataFrame({
                        "Datum": [datetime.strptime(d, '%Y-%m-%d').strftime('%d.%m.') for d in r['Daten']],
                        "Schnee (cm)": r['Woche']
                    }).set_index("Datum")
                    st.bar_chart(chart_data)
                    st.table(chart_data.T)
        else:
            st.error("Es konnten keine Daten geladen werden. Prüfe die Internetverbindung.")

st.divider()
st.caption("Daten von Open-Meteo. Neuschnee 24h berechnet aus der Summe von heute und morgen.")
