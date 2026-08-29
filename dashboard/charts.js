"use strict";

function sizeCanvas(c) {
  const dpr = window.devicePixelRatio || 1;
  const cssW = Math.max(c.clientWidth, 1);
  const cssH = Math.max(c.clientHeight, 1);
  const bw = Math.round(cssW * dpr);
  const bh = Math.round(cssH * dpr);
  if (c.width !== bw || c.height !== bh) {
    c.width = bw;
    c.height = bh;
  }
  const ctx = c.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w: cssW, h: cssH };
}

function drawLineChart(canvasId, series, color, yFmt, stacked, prices, tNow, bands) {
  const c = document.getElementById(canvasId);
  const { ctx, w, h } = sizeCanvas(c);
  ctx.fillStyle = "#141a22";
  ctx.fillRect(0, 0, w, h);
  if (!series.length) return;

  const pad = { l: 44, r: 16, t: 10, b: 26 };
  const tMin = series[0].t_s, tMax = series[series.length - 1].t_s;
  let yMax = 0;
  if (stacked) {
    for (const p of prices) {
      const s = p.energy + p.scarcity + p.congestion + p.losses;
      if (s > yMax) yMax = s;
    }
    if (yMax < 1) yMax = 1;
  } else {
    for (const p of series) if (p.v > yMax) yMax = p.v;
    if (yMax <= 0) yMax = 1;
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

  if (bands && bands.length) {
    ctx.fillStyle = "rgba(232, 93, 74, 0.22)";
    for (const o of bands) {
      const x0 = xOf(o.start_s), x1 = xOf(o.end_s);
      ctx.fillRect(x0, pad.t, Math.max(x1 - x0, 1), h - pad.t - pad.b);
    }
  }

  const cx = xOf(tNow);
  ctx.strokeStyle = "#3dd6c6";
  ctx.setLineDash([3, 3]);
  ctx.beginPath(); ctx.moveTo(cx, pad.t); ctx.lineTo(cx, h - pad.b); ctx.stroke();
  ctx.setLineDash([]);

  ctx.fillStyle = "#6b7d8f";
  ctx.font = "10px IBM Plex Mono";
  ctx.fillText(yFmt(yMax), 4, pad.t + 10);
  ctx.fillText(fmtTime(tMin), pad.l, h - 6);
  const span = tMax - tMin || 1;
  if (Math.abs(tNow - tMin) / span > 0.08 && Math.abs(tNow - tMax) / span > 0.08) {
    const mid = fmtTime(tNow);
    ctx.fillText(mid, cx - ctx.measureText(mid).width / 2, h - 6);
  }
  const end = fmtTime(tMax);
  ctx.fillText(end, w - pad.r - ctx.measureText(end).width, h - 6);
}
