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
            "past_days": 1 
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status() 
            data = response.json()
            
            snow_days = data['daily']['snowfall_sum'] # [Gestern, Heute, Morgen, Tag3, Tag4, Tag5, Tag6, Tag7]
            dates = data['daily']['time']
            
            # Gestern (Index 0)
            snow_past_24h = round(snow_days[0], 1)
            # Morgen-Check (Heute + Morgen Summe, Index 1 + 2)
            snow_next_24h = round(snow_days[1] + snow_days[2], 1)
            
            results.append({
                "Skigebiet": name,
                "lat": info['lat'],
                "lon": info['lon'],
                "Schnee Gestern (cm)": snow_past_24h,
                "Schnee Morgen (cm)": snow_next_24h,
                "Anfahrt": info['zeit'],
                "Webcam": info['cam'],
                "Woche_Schnee": snow_days[1:], # Ab heute für 7 Tage
                "Woche_Daten": dates[1:]
            })
        except Exception as e:
            st.sidebar.error(f"Fehler bei {name}: {e}")
            continue
    return results

st.title("❄️ Vienna Powder Alert Pro")
st.write(f"Update: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

if st.button('🚀 Daten für Wien & Umgebung abrufen'):
    with st.spinner('Wetterdaten werden geladen...'):
        data = get_weather_data()
        
        if data:
            df = pd.DataFrame(data).sort_values(by="Schnee Morgen (cm)", ascending=False)
            
            # 1. Powder Alarm
            max_snow = df["Schnee Morgen (cm)"].max()
            if max_snow >= 30:
                st.balloons()
                st.success(f"🔥 FETTER POWDER ALARM! {max_snow}cm Neuschnee erwartet!")

            # 2. Highlights (Kacheln)
            st.subheader("Quick-Check")
            cols = st.columns(min(len(data), 3))
            for i, resort in enumerate(data[:3]):
                with cols[i]:
                    st.metric(
                        label=resort['Skigebiet'], 
                        value=f"{resort['Schnee Morgen (cm)']} cm Morgen", 
                        delta=f"{resort['Schnee Gestern (cm)']} cm Gestern"
                    )
                    # Webcam Link als Button direkt unter der Metrik
                    st.link_button(f"🔗 Live-Webcam {resort['Skigebiet']}", resort['Webcam'])

            # 3. Übersichtstabelle
            st.divider()
            st.subheader("Alle Skigebiete im Vergleich")
            st.table(df[["Skigebiet", "Schnee Gestern (cm)", "Schnee Morgen (cm)", "Anfahrt"]])

            # 4. 7-Tage Vorhersage
            st.divider()
            st.subheader("📅 7-Tage Neuschnee-Trend")
            
            # Wir zeigen für jedes Skigebiet einen Expander mit dem Chart
            for r in data:
                with st.expander(f"Detail-Prognose für {r['Skigebiet']}"):
                    chart_df = pd.DataFrame({
                        "Datum": [datetime.strptime(d, '%Y-%m-%d').strftime('%a, %d.%m.') for d in r['Woche_Daten']],
                        "Neuschnee (cm)": r['Woche_Schnee']
                    }).set_index("Datum")
                    
                    st.bar_chart(chart_df)
                    st.write(f"**Anfahrt von Wien:** {r['Anfahrt']}")
                    st.link_button("Zur offiziellen Webcam-Seite", r['Webcam'])

            # 5. Karte
            st.divider()
            st.subheader("📍 Geografische Übersicht")
            df['color'] = df['Schnee Morgen (cm)'].apply(lambda x: '#0044ff' if x >= 10 else '#a0a0a0')
            st.map(df, latitude='lat', longitude='lon', color='color', size=2500)
            
        else:
            st.error("Es konnten keine Daten geladen werden.")

st.divider()
st.caption("Datenquelle: Open-Meteo API | Entfernungen ab Wien Zentrum | Gestern = Letzte 24h | Morgen = Vorhersage für die nächsten 24h")
