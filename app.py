import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Seiteneinstellungen
st.set_page_config(page_title="Vienna Powder Alert", page_icon="❄️", layout="wide")

# Datenbank der Skigebiete mit Bergfex-Hardlinks
SKIGEBIETE = {
    "Stuhleck": {
        "lat": 47.57, "lon": 15.79, "zeit": "75 Min.", 
        "bergfex": "https://www.bergfex.at/semmering-stuhleck/schneebericht/"
    },
    "Mönichkirchen": {
        "lat": 47.51, "lon": 15.99, "zeit": "65 Min.", 
        "bergfex": "https://www.bergfex.at/moenichkirchen-mariensee/schneebericht/"
    },
    "Annaberg": {
        "lat": 47.87, "lon": 15.37, "zeit": "100 Min.", 
        "bergfex": "https://www.bergfex.at/annaberg/schneebericht/"
    },
    "Gemeindealpe": {
        "lat": 47.81, "lon": 15.28, "zeit": "120 Min.", 
        "bergfex": "https://www.bergfex.at/mitterbach-gemeindealpe/schneebericht/"
    },
    "Ötscher": {
        "lat": 47.85, "lon": 15.15, "zeit": "130 Min.", 
        "bergfex": "https://www.bergfex.at/lackenhof-oetscher/schneebericht/"
    },
    "Hochkar": {
        "lat": 47.73, "lon": 14.92, "zeit": "150 Min.", 
        "bergfex": "https://www.bergfex.at/hochkar/schneebericht/"
    }
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
            
            snow_days = data['daily']['snowfall_sum'] 
            dates = data['daily']['time']
            
            snow_past_24h = round(snow_days[0], 1)
            snow_next_24h = round(snow_days[1] + snow_days[2], 1)
            
            results.append({
                "Skigebiet": name,
                "lat": info['lat'],
                "lon": info['lon'],
                "Schnee Gestern (cm)": snow_past_24h,
                "Schnee Morgen (cm)": snow_next_24h,
                "Anfahrt": info['zeit'],
                "Bergfex": info['bergfex'],
                "Woche_Schnee": snow_days[1:], 
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
            
            if df["Schnee Morgen (cm)"].max() >= 30:
                st.balloons()
                st.success(f"🔥 FETTER POWDER ALARM! {df['Schnee Morgen (cm)'].max()}cm Neuschnee erwartet!")

            st.subheader("Quick-Check")
            cols = st.columns(min(len(data), 3))
            for i, resort in enumerate(data[:3]):
                with cols[i]:
                    st.metric(
                        label=resort['Skigebiet'], 
                        value=f"{resort['Schnee Morgen (cm)']} cm Morgen", 
                        delta=f"{resort['Schnee Gestern (cm)']} cm Gestern"
                    )
                    st.link_button(f"🔎 Bergfex {resort['Skigebiet']}", resort['Bergfex'])

            st.divider()
            st.subheader("Alle Skigebiete im Vergleich")
            st.table(df[["Skigebiet", "Schnee Gestern (cm)", "Schnee Morgen (cm)", "Anfahrt"]])

            st.divider()
            st.subheader("📅 7-Tage Neuschnee-Trend")
            
            for r in data:
                with st.expander(f"Detail-Prognose für {r['Skigebiet']}"):
                    chart_df = pd.DataFrame({
                        "Datum": [datetime.strptime(d, '%Y-%m-%d').strftime('%a, %d.%m.') for d in r['Woche_Daten']],
                        "Neuschnee (cm)": r['Woche_Schnee']
                    }).set_index("Datum")
                    
                    st.bar_chart(chart_df)
                    st.info(f"💡 **Bergfex-Check:** Suche auf der Bergfex-Seite nach dem Feld 'Neu' oder 'letzter Schneefall'. Die offizielle Messung erfolgt oft nur 1x morgens.")
                    st.link_button(f"Gegen-Check auf Bergfex", r['Bergfex'])

            st.divider()
            st.subheader("📍 Geografische Übersicht")
            df['color'] = df['Schnee Morgen (cm)'].apply(lambda x: '#0044ff' if x >= 10 else '#a0a0a0')
            st.map(df, latitude='lat', longitude='lon', color='color', size=2500)
            
        else:
            st.error("Es konnten keine Daten geladen werden.")

st.divider()
st.caption("Datenquelle: Open-Meteo API | Bergfex Hardlinks für manuellen Check.")
