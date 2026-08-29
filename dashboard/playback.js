"use strict";

let playing = false;
let speed = 3600;
let lastFrame = 0;
let raf = 0;

function sliderStep() {
  return Math.max(15, +$("time-slider").step || 15);
}

function setPlaying(on) {
  playing = on && !!data;
  $("btn-play").textContent = playing ? "Pause" : "Play";
  $("btn-play").setAttribute("aria-pressed", playing ? "true" : "false");
  if (playing) {
    lastFrame = performance.now();
    if (!raf) raf = requestAnimationFrame(tickPlayback);
  }
}

function tickPlayback(now) {
  raf = 0;
  if (!playing) return;
  const slider = $("time-slider");
  const max = +slider.max;
  const dt = Math.min(0.08, (now - lastFrame) / 1000);
  lastFrame = now;
  let t = +slider.value + speed * dt;
  const step = sliderStep();
  t = Math.min(max, Math.round(t / step) * step);
  if (t >= max) {
    slider.value = max;
    onScrub();
    setPlaying(false);
    return;
  }
  slider.value = t;
  onScrub();
  raf = requestAnimationFrame(tickPlayback);
}

function restartPlayback() {
  $("time-slider").value = 0;
  onScrub();
}

function togglePlay() {
  if (!data) return;
  if (!playing && +$("time-slider").value >= +$("time-slider").max) {
    restartPlayback();
  }
  setPlaying(!playing);
}

function bindPlayback() {
  $("btn-play").addEventListener("click", togglePlay);
  $("btn-restart").addEventListener("click", () => {
    restartPlayback();
  });
  $("speed-select").addEventListener("change", (e) => {
    speed = +e.target.value;
  });
  $("time-slider").addEventListener("pointerdown", () => setPlaying(false));
  document.addEventListener("keydown", (e) => {
    if (e.code !== "Space") return;
    const tag = (e.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "select" || tag === "textarea") return;
    e.preventDefault();
    togglePlay();
  });
}
