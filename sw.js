const CACHE = 'powder-v1';
// app.js and style.css are left out: index.html loads them with a ?v= cache-buster that
// changes every release, so they're cached under their real, versioned URL as they're used.
const ASSETS = ['./', './index.html', './manifest.json', './icon-192.png', './icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Network-first for the app's own files, so an update pushed to GitHub Pages shows up on the
// next launch; the cache is only the offline fallback. Other origins (the Open-Meteo API,
// Google Fonts) aren't touched: the forecast is kept in localStorage by app.js instead.
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  if (!e.request.url.startsWith(self.location.origin)) return;
  e.respondWith(
    fetch(e.request, { cache: 'reload' }).then(resp => {
      if (resp && resp.status === 200) {
        const copy = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
      }
      return resp;
    }).catch(() => caches.match(e.request).then(hit =>
      // Offline launch through a URL that was never cached (e.g. ?refreshed=…): open the app shell.
      hit || (e.request.mode === 'navigate' ? caches.match('./index.html') : undefined)))
  );
});
