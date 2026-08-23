"use strict";

function drawLineChart(canvasId, series, color, yFmt, stacked, prices, tNow) {
  const c = document.getElementById(canvasId);
  const ctx = c.getContext("2d");
  const w = c.width, h = c.height;
  ctx.fillStyle = "#141a22";
  ctx.fillRect(0, 0, w, h);
  if (!series.length) return;

  const pad = { l: 44, r: 12, t: 10, b: 22 };
  const tMin = series[0].t_s, tMax = series[series.length - 1].t_s;
  let yMax = Math.max(...series.map((p) => p.v), 0.001);
  if (stacked) {
    yMax = Math.max(...prices.map((p) => p.energy + p.scarcity + p.congestion + p.losses), 1);
  }
  const xOf = (t) => pad.l + ((t - tMin) / (tMax - tMin || 1)) * (w - pad.l - pad.r);
  const yOf = (v) => h - pad.b - (v / yMax) * (h - pad.t - pad.b);

  ctx.strokeStyle = "#243040";
  ctx.beginPath(); ctx.moveTo(pad.l, pad.t); ctx.lineTo(pad.l, h - pad.b); ctx.stroke();

  if (stacked) {
    const parts = [
      ["energy", "#3dd6c6"], ["scarcity", "#e8a44a"],
      ["congestion", "#6b8fd4"], ["losses", "#6b7d8f"],
    ];
    for (let pi = 0; pi < parts.length; pi++) {
      const [key, col] = parts[pi];
      ctx.beginPath();
      prices.forEach((p, i) => {
        const base = parts.slice(0, pi).reduce((s, [k]) => s + p[k], 0);
        const x = xOf(p.t_s);
        if (i === 0) ctx.moveTo(x, yOf(base));
        ctx.lineTo(x, yOf(base));
        ctx.lineTo(x, yOf(base + p[key]));
      });
      for (let i = prices.length - 1; i >= 0; i--) {
        const p = prices[i];
        const base = parts.slice(0, pi).reduce((s, [k]) => s + p[k], 0);
        ctx.lineTo(xOf(p.t_s), yOf(base));
      }
      ctx.closePath();
      ctx.fillStyle = col;
      ctx.globalAlpha = 0.75;
      ctx.fill();
      ctx.globalAlpha = 1;
    }
  } else {
    ctx.beginPath();
    series.forEach((p, i) => {
      const x = xOf(p.t_s), y = yOf(p.v);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  const cx = xOf(tNow);
  ctx.strokeStyle = "#3dd6c6";
  ctx.setLineDash([3, 3]);
  ctx.beginPath(); ctx.moveTo(cx, pad.t); ctx.lineTo(cx, h - pad.b); ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = "#6b7d8f";
  ctx.font = "10px IBM Plex Mono";
  ctx.fillText(yFmt(yMax), 4, pad.t + 10);
}
