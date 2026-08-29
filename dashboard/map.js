"use strict";

let fleetMap = null;
let colorMode = "soc";
let loadByKey = new Map();
let maxLoadKw = 1;
const markers = new Map();

function ensureMap() {
  if (fleetMap) return fleetMap;
  if (typeof L === "undefined") {
    showError("Leaflet failed to load — no map tiles.");
    return null;
  }
  fleetMap = L.map("fleet-map", {
    zoomControl: true,
    attributionControl: true,
  });
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: "&copy; OpenStreetMap &copy; CARTO",
    maxZoom: 19,
    subdomains: "abcd",
  }).addTo(fleetMap);
  return fleetMap;
}

function demandColor(ratio) {
  const t = Math.max(0, Math.min(1, ratio));
  return `rgb(${58 + t * 170 | 0},${40 + t * 100 | 0},${20 + t * 20 | 0})`;
}

function intervalOf(tNow) {
  return tNow - (tNow % 300);
}

function loadKw(locId, tNow) {
  const kw = loadByKey.get(`${locId}:${intervalOf(tNow)}`);
  return kw == null ? null : kw;
}

function indexLoads() {
  loadByKey = new Map();
  maxLoadKw = 0.001;
  for (const row of data?.loads || []) {
    loadByKey.set(`${row.location_id}:${row.t_s}`, row.kw);
    if (row.kw > maxLoadKw) maxLoadKw = row.kw;
  }
  paintLegend();
}

function paintLegend() {
  const bar = $("legend-bar");
  const lo = $("legend-lo");
  const hi = $("legend-hi");
  if (!bar || !lo || !hi) return;
  const demand = colorMode === "demand";
  bar.className = demand ? "demand" : "soc";
  if (demand) {
    lo.textContent = "0 kW";
    hi.textContent = `${maxLoadKw.toFixed(1)} kW`;
  } else {
    lo.textContent = "0%";
    hi.textContent = "100%";
  }
  $("color-soc")?.classList.toggle("on", !demand);
  $("color-demand")?.classList.toggle("on", demand);
}

function markerFill(tick, locId, tNow) {
  if (colorMode === "demand") {
    const kw = loadKw(locId, tNow);
    return kw == null ? "#6b7d8f" : demandColor(kw / maxLoadKw);
  }
  if (!tick) return "#6b7d8f";
  return socColor(tick.energy_kwh / tick.capacity_kwh);
}

function markerStyle(tick, locId, tNow) {
  if (!tick) {
    return {
      radius: 6,
      color: "#6b7d8f",
      weight: 1.5,
      fillColor: markerFill(null, locId, tNow),
      fillOpacity: colorMode === "demand" ? 0.92 : 0.12,
      dashArray: null,
    };
  }
  const silent = tick.link_up === false;
  return {
    radius: 7,
    color: tick.islanded ? "#e85d4a" : "#0c0f14",
    weight: tick.islanded ? 3 : 1.5,
    fillColor: markerFill(tick, locId, tNow),
    fillOpacity: silent ? 0.45 : 0.92,
    dashArray: silent ? "3,3" : null,
  };
}

function tipText(loc, tick, tNow) {
  const soc = tick ? `${((tick.energy_kwh / tick.capacity_kwh) * 100).toFixed(0)}%` : "—";
  const kw = loadKw(loc.id, tNow);
  const load = kw == null ? "—" : `${kw.toFixed(1)} kW`;
  return `${loc.id} · ${soc} · ${load}`;
}

function updateFleetMap(tNow) {
  const map = ensureMap();
  if (!map || !data) return;

  const inst = Object.fromEntries(data.installs.map((i) => [i.location_id, i.unit_id]));
  const tickOf = Object.fromEntries((ticksByTime.get(tNow) || []).map((t) => [t.unit_id, t]));
  const seen = new Set();

  for (const loc of data.locations) {
    seen.add(loc.id);
    const tick = tickOf[inst[loc.id]];
    const style = markerStyle(tick, loc.id, tNow);
    let m = markers.get(loc.id);
    if (!m) {
      m = L.circleMarker([loc.lat, loc.lon], style).addTo(map);
      m.bindTooltip(tipText(loc, tick, tNow), { direction: "top", offset: [0, -6] });
      markers.set(loc.id, m);
    } else {
      m.setStyle(style);
      m.setLatLng([loc.lat, loc.lon]);
      m.setTooltipContent(tipText(loc, tick, tNow));
    }
  }
  for (const [id, m] of markers) {
    if (!seen.has(id)) {
      map.removeLayer(m);
      markers.delete(id);
    }
  }

  $("map-caption").textContent = `${data.locations.length} locations · t=${fmtTime(tNow)}`;
}

function fitFleet() {
  const map = ensureMap();
  if (!map || !data?.locations?.length) return;
  const bounds = L.latLngBounds(data.locations.map((l) => [l.lat, l.lon]));
  map.invalidateSize();
  map.fitBounds(bounds.pad(0.55));
}

function setColorMode(mode) {
  colorMode = mode === "demand" ? "demand" : "soc";
  paintLegend();
  if (data) updateFleetMap(+$("time-slider").value);
}

function bindMapLegend() {
  $("color-soc")?.addEventListener("click", () => setColorMode("soc"));
  $("color-demand")?.addEventListener("click", () => setColorMode("demand"));
}
