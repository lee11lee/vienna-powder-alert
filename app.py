import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Seiteneinstellungen
st.set_page_config(page_title="Vienna Powder Alert", page_icon="❄️", layout="wide")

# Datenbank der Skigebiete
SKIGEBIETE = {
    "Stuhleck": {"lat": 47.57, "lon": 15.79, "zeit": "75 Min.", "bergfex": "https://www.bergfex.at/semmering-stuhleck/schneebericht/"},
    "Mönichkirchen": {"lat": 47.51, "lon": 15.99, "zeit": "65 Min.", "bergfex": "https://www.bergfex.at/moenichkirchen-mariensee/schneebericht/"},
    "Annaberg": {"lat": 47.87, "lon": 15.37, "zeit": "100 Min.", "bergfex": "https://www.bergfex.at/annaberg/schneebericht/"},
    "Gemeindealpe": {"lat": 47.81, "lon": 15.28, "zeit": "120 Min.", "bergfex": "https://www.bergfex.at/mitterbach-gemeindealpe/schneebericht/"},
    "Ötscher": {"lat": 47.85, "lon": 15.15, "zeit": "130 Min.", "bergfex": "https://www.bergfex.at/lackenhof-oetscher/schneebericht/"},
    "Hochkar": {"lat": 47.73, "lon": 14.92, "zeit": "150 Min.", "bergfex": "https://www.bergfex.at/hochkar/schneebericht/"}
}

def get_weather_data():
    results = []
    base_url = "https://api.open-meteo.com/v1/forecast"
    
    for name, info in SKIGEBIETE.items():
        params = {
            "latitude": info['lat'],
            "longitude": info['lon'],
            "daily": ["snowfall_sum", "snow_depth_max"], # Neu: snow_depth_max hinzugefügt
            "timezone": "Europe/Berlin",
            "past_days": 1 
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status() 
            data = response.json()
            
            snowfall_days = data['daily']['snowfall_sum'] 
            snow_depth_days = data['daily']['snow_depth_max']
            dates = data['daily']['time']
            
            # Gestern (Index 0)
            snow_past_24h = round(snowfall_days[0], 1)
            # Heute + Morgen Summe (Index 1 + 2)
            snow_next_24h = round(snowfall_days[1] + snowfall_days[2], 1)
            # Aktuelle Gesamtschneehöhe (von heute)
            total_snow_depth = round(snow_depth_days[1] * 100, 0) # API liefert Meter, wir wollen cm
            
            results.append({
                "Skigebiet": name,
                "lat": info['lat'],
                "lon": info['lon'],
                "Neuschnee Morgen (cm)": snow_next_24h,
                "Neuschnee Gestern (cm)": snow_past_24h,
                "Gesamthöhe (cm)": total_snow_depth,
                "Anfahrt": info['zeit'],
                "Bergfex": info['bergfex'],
                "Woche_Schnee": snowfall_days[1:], 
                "Woche_Daten": dates[1:]
            })
        except Exception as e:
            st.sidebar.error(f"Fehler bei {name}: {e}")
            continue
    return results

st.title("❄️ Vienna Powder Alert Pro")
st.write(f"Update: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

if st.button('🚀 Schnee-Check starten'):
    with st.spinner('Wetterdaten werden geladen...'):
        data = get_weather_data()
        
        if data:
            df = pd.DataFrame(data).sort_values(by="Neuschnee Morgen (cm)", ascending=False)
            
            # Powder Alarm
            if df["Neuschnee Morgen (cm)"].max() >= 30:
                st.balloons()
                st.success(f"🔥 FETTER POWDER ALARM! {df['Neuschnee Morgen (cm)'].max()}cm Neuschnee erwartet!")

            # 1. Highlights
            st.subheader("Top-Spots (Nächste 24h)")
            cols = st.columns(min(len(data), 3))
            for i, resort in enumerate(data[:3]):
                with cols[i]:
                    st.metric(
                        label=resort['Skigebiet'], 
                        value=f"{resort['Neuschnee Morgen (cm)']} cm Neu", 
                        delta=f"Gesamt: {int(resort['Gesamthöhe (cm)'])} cm"
                    )
                    st.link_button(f"🔎 Bergfex {resort['Skigebiet']}", resort['Bergfex'])

            # 2. Übersichtstabelle (jetzt mit Gesamthöhe)
            st.divider()
            st.subheader("Alle Gebiete im Vergleich")
            st.table(df[["Skigebiet", "Neuschnee Gestern (cm)", "Neuschnee Morgen (cm)", "Gesamthöhe (cm)", "Anfahrt"]])

            # 3. 7-Tage-Details
            st.divider()
            st.subheader("📅 7-Tage Neuschnee-Trend")
            for r in data:
                with st.expander(f"Prognose für {r['Skigebiet']} (Gesamthöhe aktuell: {int(r['Gesamthöhe (cm)'])} cm)"):
                    chart_df = pd.DataFrame({
                        "Datum": [datetime.strptime(d, '%Y-%m-%d').strftime('%a, %d.%m.') for d in r['Woche_Daten']],
                        "Neuschnee (cm)": r['Woche_Schnee']
                    }).set_index("Datum")
                    st.bar_chart(chart_df)
                    st.link_button(f"Gegen-Check auf Bergfex", r['Bergfex'])

            # 4. Karte
            st.divider()
            st.subheader("📍 Karte")
            df['color'] = df['Neuschnee Morgen (cm)'].apply(lambda x: '#0044ff' if x >= 10 else '#a0a0a0')
            st.map(df, latitude='lat', longitude='lon', color='color', size=2500)
            
        else:
            st.error("Daten konnten nicht geladen werden.")

st.divider()
st.caption("Datenquelle: Open-Meteo API. Hinweis: Gesamthöhe ist ein modellierter Schätzwert.")
