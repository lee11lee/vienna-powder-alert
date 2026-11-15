# Vienna Powder Alert — Neuschnee-Check (PWA)

Wie viel Neuschnee kommt heute und morgen in den Skigebieten rund um Wien? A home-screen web
app for iPhone, built the same way as [Portafilter](https://github.com/lee11lee/portafilter):
plain HTML/CSS/JS, no build step, no server, no account, $0 to run. It replaces the earlier
Streamlit version (`app.py`), which needed a Python server.

## What it shows
- **Powder**: the alarm (default: 30 cm or more today + tomorrow in the best area) and the
  top 3 spots, each with yesterday's snow, a 7-day sparkline and a Bergfex link.
- **Gebiete**: all six areas, sorted by new snow or by drive time from Vienna.
- **Karte**: the areas and Vienna to scale; marker size = snow today + tomorrow, blue from
  10 cm. No map tiles, so it works offline too.
- **Detail** (tap any area): yesterday / today + tomorrow / 7-day total, the 7-day bar chart,
  and "Gegen-Check auf Bergfex". Swipe from the left edge to go back.
- **Setup**: alarm and highlight thresholds, reload data, reload the app itself.

Areas: Stuhleck, Mönichkirchen, Annaberg, Gemeindealpe, Ötscher, Hochkar (edit `RESORTS` at
the top of `app.js` to change them).

## Data
Daily `snowfall_sum` from [Open-Meteo](https://open-meteo.com/) (free, no API key), fetched
straight from the phone in one request for all areas. "Heute + Morgen" is today's plus
tomorrow's daily total, the same number the Streamlit app called "Neuschnee Morgen". The last
result is kept on the device, so the app opens offline and shows when that data is from.
It reloads on launch and whenever you come back to it after 15 minutes.

## Host it (GitHub Pages)
1. Repo → Settings → Pages → Deploy from branch → `main` / root.
2. The app is then at `https://lee11lee.github.io/vienna-powder-alert/`.

Netlify, Vercel or Cloudflare Pages work too: it's just static files.

## Install on your iPhone
1. Open the URL in **Safari**.
2. Share → **Add to Home Screen**.
3. It now opens like an app: own icon, full screen, works offline with the last data.

## Releasing a change
Bump `APP_VERSION` in `app.js` and the `?v=` on `style.css` / `app.js` in `index.html`
together. Setup shows the version, so you can tell whether the phone has the update.

## Differences from the Streamlit version
- Loads by itself on launch instead of behind a "Neuschnee-Check starten" button.
- The top 3 spots are now really the three snowiest areas. The old page sorted the table but
  took the top spots from the unsorted list, so it showed the first three in the list
  (Stuhleck, Mönichkirchen, Annaberg) whatever the snow.
- Alarm and map-highlight thresholds can be changed in Setup (defaults 30 cm / 10 cm as before).
- Timezone is Europe/Vienna (was Europe/Berlin; same offset, clearer intent).
- No push notifications: the alarm shows when you open the app. Real push alerts would need a
  small server or scheduled job to send them.

Run it locally: `python3 -m http.server` in this folder, then open http://localhost:8000.
