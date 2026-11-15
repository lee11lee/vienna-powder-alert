/* ===================== Vienna Powder Alert — vanilla JS PWA =====================
   Rewrite of the Streamlit app as a home-screen web app for iPhone, built the same way as
   Portafilter: static files, no build step, no server, hosted on GitHub Pages. Snowfall
   forecasts come straight from Open-Meteo in the browser (free, no key, CORS-enabled), and
   the last result is kept on the device so the app still opens offline.
   ============================================================================== */

/* Bump with every change that gets shipped; Setup shows it, so it's easy to tell whether an
   update actually reached the phone. Bump the ?v= in index.html at the same time. */
const APP_VERSION = 'v1 · 2026-11-15';

/* ---------- Ski areas (same list as the Streamlit app) ----------
   drive: minutes by car from Vienna. label: which side of its marker the map writes the
   name on, so the Annaberg / Gemeindealpe / Ötscher cluster doesn't overlap. */
const RESORTS = [
  {id:'stuhleck',       name:'Stuhleck',      lat:47.57, lon:15.79, drive:75,  label:'w',  bergfex:'https://www.bergfex.at/semmering-stuhleck/schneebericht/'},
  {id:'moenichkirchen', name:'Mönichkirchen', lat:47.51, lon:15.99, drive:65,  label:'e',  bergfex:'https://www.bergfex.at/moenichkirchen-mariensee/schneebericht/'},
  {id:'annaberg',       name:'Annaberg',      lat:47.87, lon:15.37, drive:100, label:'e',  bergfex:'https://www.bergfex.at/annaberg/schneebericht/'},
  {id:'gemeindealpe',   name:'Gemeindealpe',  lat:47.81, lon:15.28, drive:120, label:'se', bergfex:'https://www.bergfex.at/mitterbach-gemeindealpe/schneebericht/'},
  {id:'oetscher',       name:'Ötscher',       lat:47.85, lon:15.15, drive:130, label:'n',  bergfex:'https://www.bergfex.at/lackenhof-oetscher/schneebericht/'},
  {id:'hochkar',        name:'Hochkar',       lat:47.73, lon:14.92, drive:150, label:'s',  bergfex:'https://www.bergfex.at/hochkar/schneebericht/'},
];
const VIENNA = {lat:48.2082, lon:16.3738};
function findResort(id){ return RESORTS.find(r=>r.id===id); }

/* ---------- Storage ---------- */
const SETTINGS_KEY = 'powder_settings_v1';
const FORECAST_KEY = 'powder_forecast_v1';
const DEFAULT_SETTINGS = { alarmCm:30, markCm:10 };   // the Streamlit app's fixed 30 cm alarm / 10 cm map colour
const LIMITS = { alarmCm:[5,100], markCm:[1,50] };
function readJSON(key){ try{ const raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : null; }catch(e){ return null; } }
function writeJSON(key, val){
  try{ localStorage.setItem(key, JSON.stringify(val)); return true; }
  catch(err){ console.error('Saving '+key+' failed:', err); return false; }
}
let Settings = Object.assign({}, DEFAULT_SETTINGS, readJSON(SETTINGS_KEY) || {});

/* Last forecast that loaded: {fetchedAt, areas:{[id]:{dates, snow, elevation}}}. */
let Forecast = readJSON(FORECAST_KEY);
if(!Forecast || !Forecast.fetchedAt || !Forecast.areas) Forecast = null;
let Load = { busy:false, error:null };

/* ---------- Fetching ----------
   One request for all areas: Open-Meteo takes comma-separated coordinates and answers with
   an array in the same order. past_days=1 puts yesterday first, then today and 6 more days. */
const API = 'https://api.open-meteo.com/v1/forecast';
const FETCH_TIMEOUT_MS = 15000;
const STALE_AFTER_MS = 15 * 60 * 1000;

async function refresh(){
  if(Load.busy) return;
  Load.busy = true; Load.error = null; render();
  const ctrl = new AbortController();
  const timer = setTimeout(()=>ctrl.abort(), FETCH_TIMEOUT_MS);
  try{
    const params = new URLSearchParams({
      latitude: RESORTS.map(r=>r.lat).join(','),
      longitude: RESORTS.map(r=>r.lon).join(','),
      daily: 'snowfall_sum',
      timezone: 'Europe/Vienna',
      past_days: '1',
    });
    const res = await fetch(API + '?' + params, {signal:ctrl.signal, cache:'no-store'});
    if(!res.ok) throw new Error('HTTP ' + res.status);
    let body = await res.json();
    if(!Array.isArray(body)) body = [body];   // a single location comes back as a plain object
    if(body.length !== RESORTS.length) throw new Error('Expected '+RESORTS.length+' locations, got '+body.length);
    const areas = {};
    RESORTS.forEach((r,i)=>{
      const d = body[i] && body[i].daily;
      if(!d || !Array.isArray(d.time) || !Array.isArray(d.snowfall_sum)) throw new Error('No daily data for '+r.name);
      areas[r.id] = { dates:d.time, snow:d.snowfall_sum, elevation:body[i].elevation };
    });
    Forecast = { fetchedAt:new Date().toISOString(), areas };
    writeJSON(FORECAST_KEY, Forecast);
  }catch(err){
    console.error('Loading the forecast failed:', err);
    Load.error = navigator.onLine === false ? 'Offline'
      : err.name === 'AbortError' ? 'Zeitüberschreitung'
      : 'Laden fehlgeschlagen';
  }finally{
    clearTimeout(timer);
    Load.busy = false;
    render();
  }
}
/* Reload when there's nothing yet, the data is over 15 minutes old, or the day has rolled
   over since it was fetched (then "today" is no longer the date it was fetched for). */
function refreshIfStale(){
  const first = Forecast && Forecast.areas[RESORTS[0].id];
  const old = !Forecast || Date.now() - new Date(Forecast.fetchedAt).getTime() > STALE_AFTER_MS;
  if(old || !first || !first.dates.includes(todayISO())) refresh();
  else render();
}

/* ---------- Derived numbers ----------
   Days are looked up by date rather than by position, so a forecast cached yesterday still
   lines up correctly ("today" is then its third day, not its second). */
function round1(v){ return Math.round(v*10)/10; }
function statsFor(r){
  const a = Forecast && Forecast.areas[r.id];
  if(!a) return null;
  const ti = a.dates.indexOf(todayISO());
  if(ti < 0) return null;   // the stored forecast no longer covers today
  const at = i => (i>=0 && i<a.snow.length && typeof a.snow[i]==='number') ? a.snow[i] : 0;
  const week = [], weekDates = [];
  for(let i=ti; i<Math.min(ti+7, a.dates.length); i++){ week.push(at(i)); weekDates.push(a.dates[i]); }
  return {
    resort: r,
    yday: ti>0 ? round1(at(ti-1)) : null,
    next: round1(at(ti) + at(ti+1)),   // "Neuschnee Morgen" in the Streamlit app: today + tomorrow
    week, weekDates,
    weekTotal: round1(week.reduce((s,v)=>s+v, 0)),
    elevation: a.elevation,
  };
}
function allStats(){ return RESORTS.map(statsFor).filter(Boolean); }
function bySnow(a,b){ return (b.next - a.next) || (a.resort.drive - b.resort.drive); }
function byDrive(a,b){ return a.resort.drive - b.resort.drive; }

/* ---------- Formatting ---------- */
const WD = ['So','Mo','Di','Mi','Do','Fr','Sa'];
const NUM = new Intl.NumberFormat('de-AT', {maximumFractionDigits:1});
function escapeHtml(s){ if(s===undefined||s===null) return ''; return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function pad2(n){ return String(n).padStart(2,'0'); }
function todayISO(){ const d=new Date(); return d.getFullYear()+'-'+pad2(d.getMonth()+1)+'-'+pad2(d.getDate()); }
function parseISODate(s){ const [y,m,d] = s.split('-').map(Number); return new Date(y, m-1, d); }
function fmtCm(v){ return v===null || v===undefined ? '–' : NUM.format(v); }
function fmtStand(iso){
  const d = new Date(iso), hm = pad2(d.getHours())+':'+pad2(d.getMinutes());
  return d.toDateString()===new Date().toDateString() ? hm : d.getDate()+'.'+(d.getMonth()+1)+'. '+hm;
}
function isStandalone(){ return window.navigator.standalone===true || (window.matchMedia && matchMedia('(display-mode: standalone)').matches); }

/* ===================== Navigation / state ===================== */
const TABS = ['Powder','Gebiete','Karte','Setup'];
let Nav = { tab:0, stacks:[[],[],[],[]], confirm:null };
let UIState = { areaSort:'snow' };
function currentTop(){ const st = Nav.stacks[Nav.tab]; return st.length ? st[st.length-1] : {screen:'tab', params:{}}; }
function confirmDialog(title, message, confirmLabel, onConfirm){ Nav.confirm = {title, message, confirmLabel, onConfirm}; render(); }

/* ===================== Render engine ===================== */
function render(){
  try{ renderInner(); }
  catch(err){
    // A broken confirm left in Nav would throw on every render and lock the app up.
    console.error('render() failed, resetting dialog state:', err);
    Nav.confirm = null;
    try{ renderInner(); }catch(err2){ console.error('render() failed again:', err2); }
  }
}
function renderInner(){
  const app = document.getElementById('app');
  const top = currentTop();
  const key = Nav.tab + ':' + top.screen + ':' + (top.params.id || '');
  // Background reloads re-render the screen you're looking at; keep its scroll position.
  const prev = app.querySelector(':scope > .screen');
  const keepScroll = prev && prev.dataset.key === key ? prev.scrollTop : 0;
  const isBase = Nav.stacks[Nav.tab].length === 0;
  const body = top.screen === 'resort' ? ResortScreen(top.params) : TabScreen(Nav.tab);
  app.innerHTML = `<div class="screen" data-key="${escapeHtml(key)}">${body}</div>` + (isBase ? TabBar() : '');
  if(keepScroll) app.querySelector(':scope > .screen').scrollTop = keepScroll;
  if(Nav.confirm) app.insertAdjacentHTML('beforeend', renderConfirm());
}
function TabScreen(tab){
  switch(tab){
    case 0: return PowderScreen();
    case 1: return AreasScreen();
    case 2: return MapScreen();
    default: return SetupScreen();
  }
}
function TabBar(){
  return `<nav class="tab-bar"><div class="tab-row">
    ${TABS.map((t,i)=>`<button class="tab-btn ${i===Nav.tab?'active':''}" onclick="A.switchTab(${i})">${t}</button>`).join('')}
  </div></nav>`;
}
function renderConfirm(){
  const c = Nav.confirm;
  return `<div class="confirm-overlay"><div class="confirm-box">
    <div class="body"><div class="t">${escapeHtml(c.title)}</div><div class="m">${escapeHtml(c.message)}</div></div>
    <div class="btnrow"><button onclick="A.confirmNo()">Abbrechen</button><button onclick="A.confirmYes()">${escapeHtml(c.confirmLabel)}</button></div>
  </div></div>`;
}

/* ---------- Shared pieces ---------- */
function standMeta(){
  if(!Forecast) return `<span class="meta">${Load.busy ? 'Lädt…' : '—'}</span>`;
  return `<span class="meta${Load.error?' warn':''}">${Load.busy ? 'Lädt… · ' : ''}Stand ${fmtStand(Forecast.fetchedAt)}</span>`;
}
function screenHeader(title){ return `<div class="screen-header"><h1>${escapeHtml(title)}</h1>${standMeta()}</div>`; }
function detailHeader(title, meta){
  return `<div class="header-row">
    <button class="link-back" onclick="A.pop()" aria-label="Zurück">‹</button>
    <span class="htitle">${escapeHtml(title)}</span>
    ${meta ? `<span class="hmeta">${escapeHtml(meta)}</span>` : ''}
  </div>`;
}
/* Shown instead of a screen's content while there's no usable forecast at all. */
function noDataBlock(){
  if(Load.busy) return `<div class="empty-msg">Wetterdaten werden geladen…</div>`;
  const why = Load.error ? `Wetterdaten konnten nicht geladen werden (${escapeHtml(Load.error)}).` : 'Noch keine Wetterdaten auf diesem Gerät.';
  return `<div class="empty-msg">${why}</div><button class="btn-primary" onclick="A.refresh()">Neuschnee-Check starten</button>`;
}
/* Shown above the content when a reload failed but older data is still on screen. */
function errorLine(){
  return (Load.error && Forecast) ? `<div class="status-line">${escapeHtml(Load.error)} · zeigt Stand ${fmtStand(Forecast.fetchedAt)}</div>` : '';
}
function refreshButton(){
  return `<button class="btn-ghost" ${Load.busy?'disabled':''} onclick="A.refresh()">${Load.busy ? 'Lädt…' : '↻ Aktualisieren'}</button>`;
}
function chartMax(week){ return Math.max(10, ...week); }   // ≥10 cm so a dusting doesn't fill the chart
function Spark(week){
  const m = chartMax(week);
  return `<div class="spark" aria-hidden="true">${week.map(v=>
    `<span class="${v>0?'':'nil'}" style="height:${v>0 ? Math.max(10, Math.round(v/m*100)) : 4}%"></span>`).join('')}</div>`;
}

/* ===================== Screen: Powder (home) ===================== */
function PowderScreen(){
  const st = allStats().sort(bySnow);
  let html = screenHeader('Powder');
  if(!st.length) return html + noDataBlock();
  html += errorLine();
  html += AlarmPlate(st[0]);
  html += `<div class="subhead">Top-Spots · Heute + Morgen</div>`;
  html += st.slice(0,3).map(SpotCard).join('');
  html += refreshButton();
  html += `<div class="caption">Neuschnee laut Prognose von <a href="https://open-meteo.com/" target="_blank" rel="noopener">Open-Meteo</a>. Heute + Morgen = Summe der Tageswerte von heute und morgen.</div>`;
  return html;
}
function AlarmPlate(best){
  const max = best.next;
  if(max >= Settings.alarmCm){
    return `<div class="alarm on">${Flakes()}
      <div class="a-kicker">Heute + Morgen · Alarm ab ${Settings.alarmCm} cm</div>
      <div class="a-title">Powder-Alarm!</div>
      <div class="a-sub">${fmtCm(max)} cm Neuschnee · ${escapeHtml(best.resort.name)}</div>
    </div>`;
  }
  return `<div class="alarm">
    <div class="a-kicker">Heute + Morgen · Alarm ab ${Settings.alarmCm} cm</div>
    <div class="a-title">${max>0 ? 'Kein Powder-Alarm' : 'Kein Neuschnee'}</div>
    <div class="a-sub">${max>0 ? `Am meisten: ${fmtCm(max)} cm · ${escapeHtml(best.resort.name)}` : 'In keinem Gebiet ist Schnee angesagt.'}</div>
  </div>`;
}
/* The Streamlit app's st.balloons(), as snow. Positions are fixed per flake (not random) so
   a re-render doesn't reshuffle them. */
function Flakes(){
  let s = '';
  for(let i=0; i<16; i++){
    s += `<i style="left:${(i*37)%100}%;animation-delay:-${((i*53)%36)/10}s;animation-duration:${2.8+((i*29)%20)/10}s"></i>`;
  }
  return `<div class="flakes" aria-hidden="true">${s}</div>`;
}
function SpotCard(s, i){
  const r = s.resort;
  return `<div class="spot-card" role="button" onclick="A.openResort('${r.id}')">
    <div class="top">
      <span class="rank">${i+1}</span>
      <div class="who"><div class="name">${escapeHtml(r.name)}</div><div class="meta">${r.drive} Min. ab Wien</div></div>
      <div class="big-num"><div class="num${s.next>0?'':' zero'}">${fmtCm(s.next)}<span class="unit"> cm</span></div><div class="label">Heute + Morgen</div></div>
    </div>
    <div class="foot">
      <span class="yday">Gestern ${s.yday===null ? '–' : fmtCm(s.yday)+' cm'}</span>
      ${Spark(s.week)}
      <a class="bergfex-link" href="${r.bergfex}" target="_blank" rel="noopener" onclick="event.stopPropagation()">Bergfex ↗</a>
    </div>
  </div>`;
}

/* ===================== Screen: Gebiete (all areas) ===================== */
function AreasScreen(){
  const st = allStats();
  let html = screenHeader('Gebiete');
  if(!st.length) return html + noDataBlock();
  st.sort(UIState.areaSort==='drive' ? byDrive : bySnow);
  html += errorLine();
  html += `<div class="seg-row">${[['snow','Neuschnee'],['drive','Anfahrt']].map(([k,l])=>
    `<button class="seg-btn${UIState.areaSort===k?' on':''}" onclick="A.setAreaSort('${k}')">${l}</button>`).join('')}</div>`;
  html += `<div class="area-head"><span class="c-name">Gebiet</span><span class="c-y">Gestern</span><span class="c-n">Heute+Morgen</span><span class="chev"></span></div>`;
  html += st.map(s=>`<button class="area-row" onclick="A.openResort('${s.resort.id}')">
      <div class="c-name"><div class="name">${escapeHtml(s.resort.name)}</div><div class="sub">${s.resort.drive} Min. Anfahrt</div></div>
      <span class="c-y">${fmtCm(s.yday)}</span>
      <span class="c-n${s.next>0?'':' zero'}">${fmtCm(s.next)}</span>
      <span class="chev">›</span>
    </button>`).join('');
  html += `<div class="caption">Neuschnee in cm. Antippen für die 7-Tage-Prognose und den Bergfex-Schneebericht.</div>`;
  return html;
}

/* ===================== Screen: Karte (schematic map) =====================
   No map tiles: the areas and Vienna are plotted to scale on a plain grid, which works
   offline and keeps the look. Marker size grows with today + tomorrow's snowfall. */
const MAP = (()=>{
  const W = 360, padX = 34, padTop = 34, padBottom = 40;
  const lats = RESORTS.map(r=>r.lat).concat(VIENNA.lat), lons = RESORTS.map(r=>r.lon).concat(VIENNA.lon);
  const lat0 = Math.min(...lats), lat1 = Math.max(...lats), lon0 = Math.min(...lons), lon1 = Math.max(...lons);
  const k = Math.cos((lat0+lat1)/2 * Math.PI/180);      // shrink longitude to keep distances true
  const s = (W - 2*padX) / ((lon1-lon0) * k);           // px per degree of latitude
  const H = Math.round((lat1-lat0)*s + padTop + padBottom);
  const xy = (lat, lon)=>[padX + (lon-lon0)*k*s, padTop + (lat1-lat)*s];
  return { W, H, xy, pxPerKm: s/111.2 };
})();
// Capped so the biggest peaks in the Annaberg / Gemeindealpe / Ötscher cluster don't merge.
function markerSize(cm){ return 5 + Math.min(7, Math.sqrt(Math.max(0, cm)) * 1.6); }
function legendPeak(on){ return `<svg class="lg-peak" viewBox="0 0 12 10" aria-hidden="true"><polygon class="m-peak${on?' on':''}" points="6,1 11,9 1,9"/></svg>`; }
function labelPos(dir, x, y, r){
  switch(dir){
    case 'e':  return {x:x+r+5, y:y-1, anchor:'start'};
    case 'w':  return {x:x-r-5, y:y-1, anchor:'end'};
    case 'n':  return {x, y:y-r-17, anchor:'middle'};
    case 'se': return {x:x+r*0.6+5, y:y+r*0.6+9, anchor:'start'};
    default:   return {x, y:y+r*0.6+14, anchor:'middle'};
  }
}
function MapSVG(st){
  const f = n => n.toFixed(1);
  const [vx, vy] = MAP.xy(VIENNA.lat, VIENNA.lon);
  const lines = st.map(s=>{ const [x,y] = MAP.xy(s.resort.lat, s.resort.lon);
    return `<line class="m-line" x1="${f(vx)}" y1="${f(vy)}" x2="${f(x)}" y2="${f(y)}"/>`; }).join('');
  const marks = st.map(s=>{
    const r = s.resort, [x,y] = MAP.xy(r.lat, r.lon), m = markerSize(s.next), on = s.next >= Settings.markCm;
    const lp = labelPos(r.label, x, y, m);
    return `<g class="m-hit" onclick="A.openResort('${r.id}')">
      <circle cx="${f(x)}" cy="${f(y)}" r="20" fill="transparent"/>
      <polygon class="m-peak${on?' on':''}" points="${f(x)},${f(y-m)} ${f(x+m)},${f(y+m*0.6)} ${f(x-m)},${f(y+m*0.6)}"/>
      <text class="m-name" x="${f(lp.x)}" y="${f(lp.y)}" text-anchor="${lp.anchor}">${escapeHtml(r.name.toUpperCase())}</text>
      <text class="m-val${on?' on':''}" x="${f(lp.x)}" y="${f(lp.y+12)}" text-anchor="${lp.anchor}">${fmtCm(s.next)} cm</text>
    </g>`;
  }).join('');
  const km = 25, bar = km * MAP.pxPerKm, by = MAP.H - 14;
  return `<svg viewBox="0 0 ${MAP.W} ${MAP.H}" role="img" aria-label="Karte der Skigebiete rund um Wien">
    ${lines}
    <rect class="m-city" x="${f(vx-4)}" y="${f(vy-4)}" width="8" height="8"/>
    <text class="m-name" x="${f(vx-10)}" y="${f(vy+4)}" text-anchor="end">WIEN</text>
    ${marks}
    <line class="m-scale" x1="34" y1="${by}" x2="${f(34+bar)}" y2="${by}"/>
    <line class="m-scale" x1="34" y1="${by-3}" x2="34" y2="${by+3}"/>
    <line class="m-scale" x1="${f(34+bar)}" y1="${by-3}" x2="${f(34+bar)}" y2="${by+3}"/>
    <text class="m-small" x="${f(34+bar+6)}" y="${by+3.5}">${km} KM</text>
  </svg>`;
}
function MapScreen(){
  const st = allStats();
  let html = screenHeader('Karte');
  if(!st.length) return html + noDataBlock();
  html += errorLine();
  html += `<div class="map-wrap">${MapSVG(st)}</div>`;
  html += `<div class="map-legend"><span>${legendPeak(true)}ab ${Settings.markCm} cm</span><span>${legendPeak(false)}darunter</span><span><b></b>Wien</span></div>`;
  html += `<div class="caption">Größe = Neuschnee heute + morgen. Ein Gebiet antippen für die 7-Tage-Prognose.</div>`;
  return html;
}

/* ===================== Screen: one area (pushed) ===================== */
function ResortScreen(p){
  const r = findResort(p.id);
  if(!r) return detailHeader('Gebiet') + `<div class="empty-msg">Dieses Gebiet gibt es nicht mehr.</div>`;
  const s = statsFor(r);
  let html = detailHeader(r.name, `${r.drive} Min. ab Wien`);
  if(!s) return html + noDataBlock();
  html += errorLine();
  const mark = s.next >= Settings.markCm;
  html += `<div class="plate-row" style="margin-top:14px">
    <div class="plate-cell"><div class="pl">Gestern</div><div class="pv">${fmtCm(s.yday)}<span class="unit"> cm</span></div></div>
    <div class="plate-cell${mark?' fill':''}"><div class="pl">Heute + Morgen</div><div class="pv">${fmtCm(s.next)}<span class="unit"> cm</span></div></div>
    <div class="plate-cell"><div class="pl">${s.week.length} Tage</div><div class="pv">${fmtCm(s.weekTotal)}<span class="unit"> cm</span></div></div>
  </div>`;
  html += `<span class="section-label">${s.week.length}-Tage Neuschnee-Trend</span>`;
  html += WeekChart(s);
  html += `<div class="note">Das ist Neuschnee laut Prognose. Für die Gesamtschneehöhe auf der Piste bitte den Bergfex-Check nutzen.</div>`;
  html += `<a class="btn-primary" href="${r.bergfex}" target="_blank" rel="noopener">Gegen-Check auf Bergfex ↗</a>`;
  if(typeof s.elevation === 'number'){
    html += `<div class="caption">Prognose für ${Math.round(s.elevation)} m Seehöhe (Gitterpunkt des Wettermodells). Stand ${fmtStand(Forecast.fetchedAt)}.</div>`;
  }
  return html;
}
function WeekChart(s){
  const m = chartMax(s.week), BAR = 150;
  const cols = s.week.map((v,i)=>{
    const h = v>0 ? Math.max(3, Math.round(v/m*BAR)) : 1;
    return `<div class="col"><div class="val${v>0?'':' nil'}">${fmtCm(round1(v))}</div><div class="bar${v>0?'':' nil'}" style="height:${h}px"></div></div>`;
  }).join('');
  const days = s.weekDates.map((d,i)=>{
    const dt = parseISODate(d);
    return `<span class="${i===0?'today':''}">${i===0 ? 'Heute' : WD[dt.getDay()]}<small>${dt.getDate()}.${dt.getMonth()+1}.</small></span>`;
  }).join('');
  return `<div class="week-chart">${cols}</div><div class="week-days">${days}</div>`;
}

/* ===================== Screen: Setup ===================== */
function SetupScreen(){
  let html = `<div class="screen-header"><h1>Setup</h1><span class="meta">${APP_VERSION}</span></div>`;
  html += `<span class="section-label">Alarm</span><div class="row-list">
    ${stepperRow('Powder-Alarm ab', 'Heute + Morgen im besten Gebiet', 'alarmCm', 5)}
    ${stepperRow('Markieren ab', 'Farbe auf Karte und Detailseite', 'markCm', 1)}
  </div>`;
  html += `<span class="section-label">Daten</span><div class="row-list">
    <button class="settings-row" ${Load.busy?'disabled':''} onclick="A.refresh()">
      <div><div class="stitle">Jetzt aktualisieren</div><div class="ssub">${Load.busy ? 'Lädt…' : Forecast ? 'Stand '+fmtStand(Forecast.fetchedAt) : 'Noch keine Daten'}</div></div>
      <span class="schev">↻</span></button>
    <button class="settings-row" onclick="A.forceRefreshApp()">
      <div><div class="stitle">App neu laden</div><div class="ssub">Holt die neueste Version von GitHub</div></div>
      <span class="schev">›</span></button>
  </div>`;
  if(!isStandalone()){
    html += `<span class="section-label">Auf den Home-Bildschirm</span>
      <div class="note" style="margin-top:0">In Safari auf Teilen tippen, dann „Zum Home-Bildschirm“. Danach startet Powder Alert wie eine App: eigenes Icon, Vollbild, und offline mit dem letzten Stand.</div>`;
  }
  html += `<div class="caption">Wetterdaten: <a href="https://open-meteo.com/" target="_blank" rel="noopener">Open-Meteo.com</a> (CC BY 4.0). Schneeberichte: Bergfex. Alles bleibt auf diesem Gerät: kein Konto, kein Server.</div>`;
  return html;
}
function stepperRow(label, sub, key, step){
  return `<div class="row-item">
    <span class="rlabel">${escapeHtml(label)}<span class="rsub">${escapeHtml(sub)}</span></span>
    <div class="stepper">
      <button onclick="A.step('${key}',${-step})" aria-label="weniger">−</button>
      <span class="sval">${Settings[key]} cm</span>
      <button onclick="A.step('${key}',${step})" aria-label="mehr">+</button>
    </div>
  </div>`;
}

/* ===================== Actions (called from inline onclick) ===================== */
const A = {
  switchTab(i){
    if(i === Nav.tab) Nav.stacks[i] = [];   // tapping the current tab again goes back to its top
    Nav.tab = i; render();
  },
  pop(){ Nav.stacks[Nav.tab].pop(); render(); },
  openResort(id){ Nav.stacks[Nav.tab].push({screen:'resort', params:{id}}); render(); },
  refresh(){ refresh(); },
  setAreaSort(k){ UIState.areaSort = k; render(); },
  step(key, d){
    const [lo, hi] = LIMITS[key];
    Settings[key] = Math.min(hi, Math.max(lo, Settings[key] + d));
    writeJSON(SETTINGS_KEY, Settings); render();
  },
  confirmNo(){ Nav.confirm = null; render(); },
  confirmYes(){ const c = Nav.confirm; Nav.confirm = null; render(); if(c && c.onConfirm) c.onConfirm(); },
  forceRefreshApp(){
    confirmDialog('App neu laden?', 'Löscht nur den gespeicherten App-Code (nicht deine Einstellungen) und lädt die neueste Version.', 'Neu laden', async ()=>{
      try{
        if('serviceWorker' in navigator){
          const regs = await navigator.serviceWorker.getRegistrations();
          await Promise.all(regs.map(r=>r.unregister()));
        }
        if('caches' in window){
          const keys = await caches.keys();
          await Promise.all(keys.map(k=>caches.delete(k)));
        }
      }catch(err){ console.error('Clearing the app cache failed:', err); }
      location.href = location.pathname + '?refreshed=' + Date.now();
    });
  },
};
window.A = A;

/* ---------- Swipe back from the left edge (as in Portafilter) ----------
   Home-screen web apps don't get the system back gesture, since screens here aren't browser
   history. Drag from the left edge on any screen with a back button: past a third of the
   width, or with a quick flick, the screen slides off and back is tapped; otherwise it
   springs back. */
const SWIPE_EDGE_PX = 20;
function initSwipeBack(){
  let s = null;
  document.addEventListener('touchstart', e=>{
    s = null;
    if(e.touches.length!==1 || Nav.confirm) return;
    const t = e.touches[0];
    if(t.clientX > SWIPE_EDGE_PX) return;
    const screen = document.querySelector('#app > .screen');
    const back = screen && screen.querySelector('.link-back');
    if(!back) return;
    s = {x0:t.clientX, y0:t.clientY, t0:Date.now(), dx:0, screen, back, active:false};
  }, {passive:true});
  document.addEventListener('touchmove', e=>{
    if(!s) return;
    const t = e.touches[0];
    const dx = t.clientX - s.x0, dy = t.clientY - s.y0;
    if(!s.active){
      if(Math.abs(dy) > 10 && Math.abs(dy) > dx){ s = null; return; }   // vertical scroll, not a swipe
      if(dx < 8) return;
      s.active = true;
      s.screen.style.transition = 'none';
      s.screen.style.willChange = 'transform';
    }
    e.preventDefault();
    s.dx = Math.max(0, dx);
    s.screen.style.transform = 'translateX(' + s.dx + 'px)';
  }, {passive:false});
  const end = ()=>{
    const st = s; s = null;
    if(!st || !st.active) return;
    const w = window.innerWidth;
    const speed = st.dx / Math.max(1, Date.now() - st.t0);   // px per ms
    const goBack = st.dx > w*0.33 || (speed > 0.5 && st.dx > 40);
    st.screen.style.transition = 'transform .2s ease-out';
    st.screen.style.transform = 'translateX(' + (goBack ? w : 0) + 'px)';
    setTimeout(()=>{
      if(goBack) st.back.click();
      if(st.screen.isConnected){ st.screen.style.transition = ''; st.screen.style.transform = ''; st.screen.style.willChange = ''; }
    }, 200);
  };
  document.addEventListener('touchend', end);
  document.addEventListener('touchcancel', end);
}

/* ---------- Init ---------- */
function initApp(){
  initSwipeBack();
  render();
  refreshIfStale();
  // Coming back to the app (it stays suspended in the background on iOS) or back online.
  document.addEventListener('visibilitychange', ()=>{ if(document.visibilityState === 'visible') refreshIfStale(); });
  window.addEventListener('online', ()=>{ if(Load.error) refresh(); });
  if('serviceWorker' in navigator){ navigator.serviceWorker.register('sw.js').catch(()=>{}); }
}
document.addEventListener('DOMContentLoaded', initApp);
