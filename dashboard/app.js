"use strict";

let data = null;
let ticksByTime = new Map();
let socSeries = [];
let shortfallSeries = [];

const $ = (id) => document.getElementById(id);

function fmtTime(s) {
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}

function showError(msg) {
  $("error-banner").textContent = msg;
  $("error-banner").classList.remove("hidden");
}

function hideError() { $("error-banner").classList.add("hidden"); }

function socColor(ratio) {
  const t = Math.max(0, Math.min(1, ratio));
  return `rgb(${26 + t * 35 | 0},${74 + t * 140 | 0},${92 + t * 106 | 0})`;
}

function buildSeries() {
  ticksByTime = new Map();
  const socAt = new Map(), sfAt = new Map();
  for (const t of data.ticks) {
    if (!ticksByTime.has(t.t_s)) ticksByTime.set(t.t_s, []);
    ticksByTime.get(t.t_s).push(t);
    const s = socAt.get(t.t_s) || { sum: 0, n: 0 };
    s.sum += t.energy_kwh / t.capacity_kwh;
    s.n += 1;
    socAt.set(t.t_s, s);
    sfAt.set(t.t_s, (sfAt.get(t.t_s) || 0) + t.shortfall_kwh);
  }
  const times = [...ticksByTime.keys()].sort((a, b) => a - b);
  socSeries = times.map((t) => ({ t_s: t, v: socAt.get(t).sum / socAt.get(t).n }));
  shortfallSeries = times.map((t) => ({ t_s: t, v: sfAt.get(t) }));
}

function setMetrics(sb) {
  $("m-revenue").textContent = sb ? `$${sb.revenue_usd.toFixed(2)}` : "—";
  $("m-shortfall").textContent = sb ? `${sb.shortfall_kwh.toFixed(3)} kWh` : "—";
  $("m-coverage").textContent = sb ? `${(sb.coverage * 100).toFixed(1)}%` : "—";
  $("m-dark").textContent = sb?.locations_dark ?? "—";
  $("m-floor").textContent = sb ? fmtTime(sb.time_at_floor_s) : "—";
}

function drawMap(tNow) {
  const c = $("map-canvas");
  const ctx = c.getContext("2d");
  const w = c.width, h = c.height, pad = 40;
  ctx.fillStyle = "#141a22";
  ctx.fillRect(0, 0, w, h);

  const locs = data.locations;
  const inst = Object.fromEntries(data.installs.map((i) => [i.location_id, i.unit_id]));
  const tickOf = Object.fromEntries((ticksByTime.get(tNow) || []).map((t) => [t.unit_id, t]));
  const lats = locs.map((l) => l.lat), lons = locs.map((l) => l.lon);
  const latMin = Math.min(...lats) - 0.05, latMax = Math.max(...lats) + 0.05;
  const lonMin = Math.min(...lons) - 0.05, lonMax = Math.max(...lons) + 0.05;
  const px = (lon) => pad + ((lon - lonMin) / (lonMax - lonMin)) * (w - 2 * pad);
  const py = (lat) => h - pad - ((lat - latMin) / (latMax - latMin)) * (h - 2 * pad);

  ctx.strokeStyle = "#243040";
  for (let i = 0; i <= 4; i++) {
    const y = pad + (i / 4) * (h - 2 * pad);
    ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(w - pad, y); ctx.stroke();
  }

  for (const loc of locs) {
    const tick = tickOf[inst[loc.id]];
    const x = px(loc.lon), y = py(loc.lat), r = 10;
    if (tick?.islanded) {
      ctx.beginPath(); ctx.arc(x, y, r + 4, 0, Math.PI * 2);
      ctx.strokeStyle = "#e85d4a"; ctx.lineWidth = 2; ctx.stroke();
    }
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = socColor(tick ? tick.energy_kwh / tick.capacity_kwh : 0);
    ctx.fill();
    ctx.strokeStyle = "#0c0f14"; ctx.lineWidth = 1.5; ctx.stroke();
  }
  ctx.fillStyle = "#6b7d8f";
  ctx.font = "11px IBM Plex Mono";
  ctx.fillText(`${locs.length} locations · t=${fmtTime(tNow)}`, pad, 18);
}

function drawCharts(tNow) {
  const spp = data.prices.map((p) => ({
    t_s: p.t_s, v: p.energy + p.scarcity + p.congestion + p.losses,
  }));
  drawLineChart("chart-spp", spp, "#3dd6c6", (v) => `$${v.toFixed(0)}`, true, data.prices, tNow);
  drawLineChart("chart-soc", socSeries, "#6b8fd4", (v) => `${(v * 100).toFixed(0)}%`, false, [], tNow);
  drawLineChart("chart-shortfall", shortfallSeries, "#e85d4a", (v) => v.toFixed(3), false, [], tNow);
  $("spp-legend").textContent = "energy · scarcity · congestion · losses";
}

function onScrub() {
  const t = +$("time-slider").value;
  $("time-label").textContent = fmtTime(t);
  if (data) { drawMap(t); drawCharts(t); }
}

async function loadRun(id) {
  hideError();
  const res = await fetch(`/api/runs/${id}`);
  const body = await res.json();
  if (!res.ok) { showError(body.error || `Failed to load run ${id}`); data = null; return; }
  if (body.card?.status !== "success") {
    showError(body.card?.error || `Run ${id} did not succeed`);
    data = null;
    return;
  }
  data = body;
  buildSeries();
  setMetrics(body.scoreboard);
  const dur = body.card.finished_s || (body.prices.at(-1)?.t_s ?? 0) + 300 || 3600;
  const slider = $("time-slider");
  slider.max = dur;
  slider.value = 0;
  slider.step = (body.trace_stride || 1) * 15;
  onScrub();
}

async function init() {
  try {
    const runs = await (await fetch("/api/runs")).json();
    const sel = $("run-select");
    while (sel.firstChild) sel.removeChild(sel.firstChild);
    if (!runs.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "No successful runs";
      sel.appendChild(opt);
      showError("No successful runs found. Run a scenario first.");
      return;
    }
    for (const r of runs) {
      const opt = document.createElement("option");
      opt.value = r.id;
      opt.textContent = `${r.id}  (seed ${r.seed})`;
      sel.appendChild(opt);
    }
    sel.addEventListener("change", () => loadRun(sel.value));
    await loadRun(runs[0].id);
  } catch (e) {
    showError(String(e));
  }
}

$("time-slider").addEventListener("input", onScrub);
init();
