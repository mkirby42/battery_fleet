"use strict";

let data = null;
let ticksByTime = new Map();
let socSeries = [];
let shortfallSeries = [];

const $ = (id) => document.getElementById(id);

function fmtTime(s) {
  const t = Math.max(0, Math.round(+s || 0));
  const day = Math.floor(t / 86400);
  const tod = t % 86400;
  const h = Math.floor(tod / 3600);
  const m = Math.floor((tod % 3600) / 60);
  const sec = tod % 60;
  const hm = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
  const clock = sec ? `${hm}:${String(sec).padStart(2, "0")}` : hm;
  return day ? `d${day + 1} ${clock}` : clock;
}

function showError(msg) {
  hideLoading();
  $("error-banner").textContent = msg;
  $("error-banner").classList.remove("hidden");
}

function hideError() { $("error-banner").classList.add("hidden"); }

function showLoading() {
  hideError();
  $("loading-banner").classList.remove("hidden");
}

function hideLoading() { $("loading-banner").classList.add("hidden"); }

function socColor(ratio) {
  const t = Math.max(0, Math.min(1, ratio));
  return `rgb(${26 + t * 35 | 0},${74 + t * 140 | 0},${92 + t * 106 | 0})`;
}

function runLabel(r) {
  const kind = r.local_policy_kind || r.local_policy_id || "?";
  return `${r.id} · ${kind} · seed ${r.seed}`;
}

function lastTickS(body) {
  if (body.last_tick_s != null) return body.last_tick_s;
  let max = 0;
  for (const t of body.ticks || []) if (t.t_s > max) max = t.t_s;
  return max;
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

function drawCharts(tNow) {
  const spp = data.prices.map((p) => ({
    t_s: p.t_s, v: p.energy + p.scarcity + p.congestion + p.losses,
  }));
  drawLineChart("chart-spp", spp, "#3dd6c6", (v) => `$${v.toFixed(0)}`, true, data.prices, tNow, data.outages || []);
  drawLineChart("chart-soc", socSeries, "#6b8fd4", (v) => `${(v * 100).toFixed(0)}%`, false, [], tNow, []);
  drawLineChart("chart-shortfall", shortfallSeries, "#e85d4a", (v) => v.toFixed(3), false, [], tNow, []);
  $("spp-legend").textContent = "energy · scarcity · congestion · losses";
}

function onScrub() {
  const t = +$("time-slider").value;
  $("time-label").textContent = fmtTime(t);
  if (data) { updateFleetMap(t); drawCharts(t); }
}

async function loadRun(id) {
  showLoading();
  try {
    const res = await fetch(`/api/runs/${id}`);
    const body = await res.json();
    if (!res.ok) { data = null; showError(body.error || `Failed to load run ${id}`); return; }
    if (body.card?.status !== "success") {
      data = null;
      showError(body.card?.error || `Run ${id} did not succeed`);
      return;
    }
    data = body;
    indexLoads();
    const opt = [...$("run-select").options].find((o) => o.value === id);
    if (opt) opt.textContent = runLabel({ id, seed: body.card.seed, ...body.card });
    buildSeries();
    setMetrics(body.scoreboard);
    const slider = $("time-slider");
    slider.max = lastTickS(body);
    slider.value = 0;
    slider.step = (body.trace_stride || 1) * 15;
    setPlaying(false);
    fitFleet();
    onScrub();
    hideLoading();
  } catch (e) {
    data = null;
    showError(String(e));
  }
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
      opt.textContent = runLabel(r);
      sel.appendChild(opt);
    }
    sel.addEventListener("change", () => loadRun(sel.value));
    await loadRun(runs[0].id);
  } catch (e) {
    showError(String(e));
  }
}

$("time-slider").addEventListener("input", onScrub);
bindMapLegend();
bindPlayback();
window.addEventListener("resize", () => {
  if (fleetMap) fleetMap.invalidateSize();
  onScrub();
});
const ro = new ResizeObserver(() => { if (data) onScrub(); });
for (const id of ["chart-spp", "chart-soc", "chart-shortfall"]) {
  ro.observe($(id).parentElement);
}
init();
