"use strict";

// Top-down silhouettes, nose up, 100×100 viewBox.
const ART = {
  jet: "M50 4c3 0 5 5 5 12v20l38 20v8l-38-9v22l12 9v6l-17-4-17 4v-6l12-9V55L7 64v-8l38-20V16c0-7 2-12 5-12z" +
       "M27 40h6v9h-6zM67 40h6v9h-6z",
  quad: "M50 3c3 0 5 5 5 13v19l40 21v7l-40-9v22l12 9v6l-17-4-17 4v-6l12-9V54L5 63v-7l40-21V16c0-8 2-13 5-13z" +
        "M20 38h5v10h-5zM33 32h5v10h-5zM62 32h5v10h-5zM75 38h5v10h-5z",
  prop: "M50 8c3 0 4 4 4 9v17h40v8l-40 4v28l12 4v6H34v-6l12-4V46l-40-4v-8h40V17c0-5 1-9 4-9z" +
        "M22 27h2v14h-2zM76 27h2v14h-2zM16 33h14v2H16zM70 33h14v2H70z",
  heli: "M50 22c7 0 11 6 11 14s-4 15-11 15-11-7-11-15 4-14 11-14zM48 50h4v38h-4zM40 84h20v4H40z" +
        "M12 33l76 6-1 3-76-6zM48 4l3-1 4 70-3 1z",
  glider: "M50 20c2 0 3 3 3 6v12l44 4v5l-44 1v30l9 4v4H38v-4l9-4V48L3 47v-5l44-4V26c0-3 1-6 3-6z",
  balloon: "M50 6c17 0 28 13 28 29 0 17-15 29-23 41h-10C37 64 22 52 22 35 22 19 33 6 50 6zM42 82h16v12H42z",
  drone: "M42 42h16v16H42zM20 20l24 24-3 3-24-24zM80 20 56 44l3 3 24-24zM20 80l24-24-3-3-24 24zM80 80 56 56l3-3 24 24z" +
         "M10 10h20v4H10zM70 10h20v4H70zM10 86h20v4H10zM70 86h20v4H70z",
};
const svg = (k) => `<svg viewBox="0 0 100 100" aria-hidden="true"><path d="${ART[k] || ART.jet}"/></svg>`;

const TIER_ORDER = ["common", "uncommon", "rare", "epic", "legendary"];
const GEMS = { common: "◆", uncommon: "◆◆", rare: "◆◆◆", epic: "◆◆◆◆", legendary: "★★★★★" };

const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const api = (p) => fetch(p).then((r) => r.json());

const hue = (s) => { let h = 0; for (const c of String(s || "?")) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
const fmtKm = (v) => (v == null ? "—" : v < 10 ? v.toFixed(1) : Math.round(v));
const fmtAlt = (v) => (v == null ? "—" : v === 0 ? "GND" : v >= 10000 ? "FL" + Math.round(v / 100) : v.toLocaleString());
const fmtDate = (t) => new Date(t * 1000).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
const fmtTime = (t) => new Date(t * 1000).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
const fmtDur = (s) => (s < 60 ? `${Math.round(s)} s` : `${Math.round(s / 60)} min`);

const BADGE_CLASS = (b) =>
  b === "new" ? "new" : b === "1st edition" ? "b1st" : b === "low pass" ? "low" :
  b.startsWith("squawk") ? "sq" : b === "military" ? "mil" : b === "regular" ? "reg" : "";

const logoImg = (icao, variant, cls) =>
  `<img class="${cls}" src="/logo/${encodeURIComponent(icao)}/${variant}.svg" alt="" loading="lazy" onerror="this.remove()">`;

function cardHTML(c) {
  const title = c.reg || c.last_callsign || c.hex.toUpperCase();
  const model = c.type_name || c.model || (c.type ? c.type : "Unidentified airframe");
  const al = c.airline;
  const brand = al && al.color ? `;--brand:${esc(al.color)}` : "";
  const chip = al && al.icon ? `<span class="chip">${logoImg(c.operator, "icon", "")}</span>` : "";
  const op = (al && al.name) || c.operator_name || (c.operator ? c.operator : c.last_callsign && c.last_callsign !== c.reg ? c.last_callsign : "Private / unknown operator");
  return `
  <article class="card ${c.rarity}" style="--hue:${hue(c.operator || c.type)}${brand}" data-hex="${esc(c.hex)}" tabindex="0">
    <div class="card-inner">
      <div class="card-head"><span>#${String(c.card_no).padStart(3, "0")} · ${esc(c.series)} SERIES</span><span class="pts">${c.points} PTS</span></div>
      <div class="art${brand ? " branded" : ""}">${chip}${svg(c.art)}<span class="tail">${esc(c.type || "????")}</span></div>
      <div class="plate">
        <div class="reg">${esc(title)}</div>
        <div class="model">${esc(model)}</div>
        <div class="op">${esc(op)}</div>
      </div>
      <div class="statline">
        <div><b>${fmtKm(c.closest_km)}</b><span>KM MIN</span></div>
        <div><b>${fmtAlt(c.max_alt_ft)}</b><span>PEAK ALT</span></div>
        <div><b>${c.max_gs_kt == null ? "—" : Math.round(c.max_gs_kt)}</b><span>KT</span></div>
        <div><b>${c.sightings}</b><span>SEEN</span></div>
      </div>
      <div class="rarity-tag"><span>${c.rarity}</span><span class="gems">${GEMS[c.rarity]}</span></div>
    </div>
    <div class="badges">${c.badges.map((b) => `<span class="badge ${BADGE_CLASS(b)}">${esc(b)}</span>`).join("")}</div>
  </article>`;
}

let CARDS = [];
let SUMMARY = null;
let MAP = null;

function renderBinder() {
  const q = $("#search").value.trim().toLowerCase();
  const rf = $("#rarity-filter").value;
  const sort = $("#sort").value;
  let list = CARDS.filter((c) => {
    if (rf && c.rarity !== rf) return false;
    if (!q) return true;
    return [c.hex, c.reg, c.type, c.type_name, c.model, c.operator, c.operator_name, c.last_callsign]
      .some((v) => v && String(v).toLowerCase().includes(q));
  });
  const by = {
    newest: (a, b) => b.first_seen - a.first_seen,
    number: (a, b) => a.card_no - b.card_no,
    rarity: (a, b) => TIER_ORDER.indexOf(b.rarity) - TIER_ORDER.indexOf(a.rarity) || b.first_seen - a.first_seen,
    closest: (a, b) => (a.closest_km ?? 1e9) - (b.closest_km ?? 1e9),
    sightings: (a, b) => b.sightings - a.sightings,
  }[sort];
  list = list.slice().sort(by);
  $("#cards").innerHTML = list.map(cardHTML).join("");
  $("#empty").hidden = CARDS.length > 0;
}

function renderSummary(s) {
  $("#radius-line").textContent =
    `Catches count within ${s.zones.map((z) => z.text).join(" or ")} of ${s.receiver.lat.toFixed(3)}, ${s.receiver.lon.toFixed(3)}`;
  $("#level").textContent = s.level;
  $("#score").textContent = `${s.score.toLocaleString()} pts`;
  $("#level-bar").style.width = `${Math.round(s.level_progress * 100)}%`;
  const tiers = TIER_ORDER.slice().reverse()
    .map((t) => `<span style="color:var(--${t})">${s.by_tier[t]} ${t}</span>`).join("");
  $("#stats").innerHTML = `
    <div class="stat"><div class="v">${s.cards}</div><div class="k">Cards</div></div>
    <div class="stat"><div class="v">${s.types}</div><div class="k">Types</div></div>
    <div class="stat"><div class="v">${s.operators}</div><div class="k">Airlines</div></div>
    <div class="stat"><div class="v">${s.new_24h}</div><div class="k">New today</div></div>
    <div class="stat"><div class="v">${s.sightings_24h}</div><div class="k">Passes 24 h</div></div>
    <div class="stat" style="grid-column: span 2"><div class="k">By rarity</div><div class="tiers">${tiers}</div></div>`;
}

function stars(n) { return n >= 25 ? "★★★" : n >= 10 ? "★★" : n >= 3 ? "★" : ""; }

async function renderDex() {
  const types = await api("/api/types");
  $("#dex-grid").innerHTML = types.map((t) => `
    <div class="dex-entry" style="--tier:var(--${t.rarity})">
      ${svg(t.art)}
      <div>
        <div class="code">${esc(t.type)} <span class="stars">${stars(t.count)}</span></div>
        <div class="nm" title="${esc(t.name)}">${esc(t.name || "Unknown type")}</div>
        <div class="ct">${t.count} airframe${t.count === 1 ? "" : "s"} · since ${fmtDate(t.first_seen)}</div>
      </div>
    </div>`).join("") || `<p class="empty">No types yet.</p>`;
}

async function renderAirlines() {
  const ops = await api("/api/operators");
  $("#airline-list").innerHTML = ops.map((o) => `
    <div class="airline">
      ${o.airline && o.airline.icon
        ? `<div class="crest logo" style="--brand:${esc(o.airline.color || "#fff")}">${logoImg(o.icao, "icon", "")}<span>${esc(o.icao)}</span></div>`
        : `<div class="crest" style="background:hsl(${hue(o.icao)} 55% 40%)">${esc(o.icao)}</div>`}
      <div>
        <div class="nm">${esc((o.airline && o.airline.name) || o.name || o.icao)}</div>
        <div class="meta">${o.airline && o.airline.parent ? `${esc(o.airline.parent)} group · ` : ""}${esc(o.country || "")}${o.callsign ? ` · “${esc(o.callsign)}”` : ""}${o.airline && o.airline.alliance ? ` · ${esc(o.airline.alliance)}` : ""}</div>
        <div class="meta">${o.count} airframe${o.count === 1 ? "" : "s"} · ${o.types.map(esc).join(", ")}</div>
      </div>
    </div>`).join("") || `<p class="empty">No airline flights caught yet.</p>`;
}

async function renderLive() {
  const d = await api("/api/live");
  $("#live-count").textContent = d.aircraft.length;
  $("#live-hint").textContent = d.error ||
    `${d.aircraft.length} aircraft inside your catch zones right now · ${d.outside_radius} more tracked outside them (not counted).`;
  $("#live-body").innerHTML = d.aircraft.map((a) => `
    <tr>
      <td>${esc(a.callsign || "—")}</td><td><code>${esc(a.hex)}</code></td>
      <td class="num">${a.dist_km} km</td><td class="num">${fmtAlt(a.alt_ft)}</td>
      <td class="num">${a.gs_kt == null ? "—" : Math.round(a.gs_kt) + " kt"}</td>
      <td>${a.collected ? `<span class="yes">in binder</span>` : `<span class="catch">new catch!</span>`}</td>
    </tr>`).join("");
}

async function openCard(hex) {
  const c = await api(`/api/card/${hex}`);
  if (c.error) return;
  const rows = c.history.map((s) => `
    <tr data-sid="${s.id}" class="${s.track_points ? "has-track" : ""}"><td>${fmtTime(s.start)}</td><td>${esc(s.callsign || "—")}</td>
    <td class="num">${fmtKm(s.min_dist_km)} km</td>
    <td class="num">${fmtAlt(s.min_alt_ft)}–${fmtAlt(s.max_alt_ft)}</td>
    <td class="num">${fmtDur(s.end - s.start)}</td>
    <td>${s.track_points ? `<span class="maplink">map</span>` : `<span class="muted">—</span>`}</td></tr>`).join("");
  $("#modal-body").innerHTML = `
    <div class="detail">
      <div>${cardHTML(c)}</div>
      <div class="back">
        ${c.airline && c.airline.logo ? `<div class="logo-plate">${logoImg(c.operator, "logo", "logo-full")}</div>` : ""}
        <h2>${esc(c.reg || c.hex.toUpperCase())}</h2>
        <div class="muted">${esc(c.model || c.type_name || "Unidentified airframe")}</div>
        <dl class="facts">
          <dt>ICAO hex</dt><dd><code>${esc(c.hex)}</code></dd>
          <dt>Type</dt><dd>${esc(c.type || "—")}${c.desc ? ` (${esc(c.desc)}, wake ${esc(c.wtc || "?")})` : ""}</dd>
          <dt>Operator</dt><dd>${esc((c.airline && c.airline.name) || c.operator_name || c.operator || "—")}${c.operator_country ? `, ${esc(c.operator_country)}` : ""}${c.airline && c.airline.alliance ? ` · ${esc(c.airline.alliance)}` : ""}</dd>
          <dt>First caught</dt><dd>${fmtTime(c.first_seen)}</dd>
          <dt>Last seen</dt><dd>${fmtTime(c.last_seen)}</dd>
          <dt>Closest pass</dt><dd>${fmtKm(c.closest_km)} km at ${fmtAlt(c.closest_alt_ft)} ft</dd>
          <dt>Type in binder</dt><dd>${c.type_count} airframe${c.type_count === 1 ? "" : "s"}</dd>
          <dt>Value</dt><dd>${c.points} pts · ${c.rarity}</dd>
        </dl>
        <h3>Flight path</h3>
        <div id="track-map" class="track-map"></div>
        <div id="track-info" class="track-info"></div>
        <h3>Sightings</h3>
        <table class="sightings"><thead><tr><th>When</th><th>Callsign</th><th class="num">Closest</th><th class="num">Altitude</th><th class="num">In zone</th><th>Track</th></tr></thead>
        <tbody>${rows}</tbody></table>
      </div>
    </div>`;
  $("#modal").hidden = false;
  setupMap();
  $("#modal-body .sightings").addEventListener("click", (e) => {
    const tr = e.target.closest("tr.has-track");
    if (tr) showTrack(+tr.dataset.sid);
  });
  const first = c.history.find((s) => s.track_points);
  if (first) showTrack(first.id);
  else $("#track-info").textContent = "No flight path recorded yet: paths are logged for sightings from the moment track logging was switched on.";
}

// ---------- flight-path map ----------
const R_EARTH = 6371.0088;
function dest(lat, lon, brg, km) {
  const p1 = (lat * Math.PI) / 180, l1 = (lon * Math.PI) / 180, b = (brg * Math.PI) / 180, d = km / R_EARTH;
  const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(b));
  const l2 = l1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(p1), Math.cos(d) - Math.sin(p1) * Math.sin(p2));
  return [(p2 * 180) / Math.PI, (l2 * 180) / Math.PI];
}

function zoneLayer(z, rx) {
  const style = { color: "#ffb547", weight: 1, fillColor: "#ffb547", fillOpacity: 0.07, dashArray: "3 4" };
  if (z.bearing_from == null) return L.circle([rx.lat, rx.lon], { ...style, radius: z.max_distance_km * 1000 });
  const span = ((z.bearing_to - z.bearing_from) % 360 + 360) % 360 || 360;
  const pts = [[rx.lat, rx.lon]];
  for (let i = 0; i <= 48; i++) pts.push(dest(rx.lat, rx.lon, z.bearing_from + (span * i) / 48, z.max_distance_km));
  return L.polygon(pts, style);
}

function setupMap() {
  if (MAP) { MAP.remove(); MAP = null; }
  const el = $("#track-map");
  if (!el || !window.L || !SUMMARY) return;
  const rx = SUMMARY.receiver;
  MAP = L.map(el, { zoomControl: true, attributionControl: true }).setView([rx.lat, rx.lon], 10);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18, className: "dark-tiles",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(MAP);
  SUMMARY.zones.forEach((z) => zoneLayer(z, rx).addTo(MAP));
  L.circleMarker([rx.lat, rx.lon], { radius: 4, color: "#fff", weight: 2, fillColor: "#ffb547", fillOpacity: 1 })
    .bindTooltip("Receiver").addTo(MAP);
  MAP.trackLayer = L.layerGroup().addTo(MAP);
}

const fmtClock = (t) => new Date(t * 1000).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });

async function showTrack(sid) {
  if (!MAP) return;
  document.querySelectorAll("#modal-body .sightings tr").forEach((r) => r.classList.toggle("sel", +r.dataset.sid === sid));
  const d = await api(`/api/sighting/${sid}/track`);
  const pts = d.points || [];
  MAP.trackLayer.clearLayers();
  if (!pts.length) { $("#track-info").textContent = "No flight path stored for this sighting."; return; }
  // split into runs of in-zone / outside-zone points (sharing the boundary vertex)
  let run = [pts[0]];
  const flush = () => {
    if (run.length < 2) return;
    const inZone = run[run.length - 1][4] && run[0][4];
    L.polyline(run.map((p) => [p[1], p[2]]), inZone
      ? { color: "#ffb547", weight: 4 }
      : { color: "#8fb3ff", weight: 2, opacity: 0.8, dashArray: "5 5" }).addTo(MAP.trackLayer);
  };
  for (let i = 1; i < pts.length; i++) {
    run.push(pts[i]);
    if (pts[i][4] !== pts[i - 1][4]) { flush(); run = [pts[i]]; }
  }
  flush();
  pts.forEach((p) => L.circleMarker([p[1], p[2]], {
    radius: p[4] ? 2.5 : 1.5, weight: 0, fillColor: p[4] ? "#ffb547" : "#8fb3ff", fillOpacity: 0.9,
  }).bindTooltip(`${fmtClock(p[0])} · ${p[3] == null ? "alt ?" : fmtAlt(p[3]) + (p[3] && p[3] < 10000 ? " ft" : "")}`).addTo(MAP.trackLayer));
  const a = pts[0], b = pts[pts.length - 1];
  L.circleMarker([a[1], a[2]], { radius: 5, color: "#8fb3ff", weight: 2, fillOpacity: 0 }).bindTooltip(`First seen ${fmtClock(a[0])}`).addTo(MAP.trackLayer);
  L.circleMarker([b[1], b[2]], { radius: 5, color: "#8fb3ff", weight: 2, fillColor: "#8fb3ff", fillOpacity: 1 }).bindTooltip(`Last seen ${fmtClock(b[0])}`).addTo(MAP.trackLayer);
  MAP.fitBounds(L.latLngBounds(pts.map((p) => [p[1], p[2]])).pad(0.1));
  const s = d.sighting;
  $("#track-info").innerHTML =
    `<span class="key zone"></span> in zone ${fmtClock(s.start)}–${fmtClock(s.end)} ` +
    `<span class="key out"></span> tracked ${fmtClock(a[0])}–${fmtClock(b[0])} · ${pts.length} points · ` +
    `<a href="/api/sighting/${sid}/track.geojson" download>GeoJSON</a> · <a href="/api/sighting/${sid}/track" target="_blank">JSON</a>`;
}

async function refresh() {
  const [s, cards] = await Promise.all([api("/api/summary"), api("/api/cards")]);
  CARDS = cards;
  SUMMARY = s;
  renderSummary(s);
  renderBinder();
  const active = $(".tabs .active").dataset.tab;
  if (active === "dex") renderDex();
  if (active === "airlines") renderAirlines();
  renderLive();
}

document.querySelectorAll(".tabs button").forEach((b) =>
  b.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((x) => x.classList.toggle("active", x === b));
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === b.dataset.tab));
    if (b.dataset.tab === "dex") renderDex();
    if (b.dataset.tab === "airlines") renderAirlines();
    if (b.dataset.tab === "live") renderLive();
  })
);
["#search", "#rarity-filter", "#sort"].forEach((s) => $(s).addEventListener("input", renderBinder));
$("#cards").addEventListener("click", (e) => { const c = e.target.closest(".card"); if (c) openCard(c.dataset.hex); });
$("#cards").addEventListener("keydown", (e) => { if (e.key === "Enter") { const c = e.target.closest(".card"); if (c) openCard(c.dataset.hex); } });
function closeModal() { $("#modal").hidden = true; if (MAP) { MAP.remove(); MAP = null; } }
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal" || e.target.classList.contains("close")) closeModal(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

refresh();
setInterval(refresh, 30000);
setInterval(() => { if ($(".tabs .active").dataset.tab === "live") renderLive(); }, 5000);
