"use strict";
// Display and messaging only. Every number is computed by the
// Python driver in the Pyodide worker. On load, the App shows
// the precomputed payload embedded at build time (every trace
// and table labelled precomputed); the first live run replaces
// that display in place, in the same chart elements, with the
// actual series names, and no precomputed label remains.
const $ = (id) => document.getElementById(id);
const LEGEND = { x: 1.02, y: 1.0, xanchor: "left", yanchor: "top" };

function resizeCharts() {
  document.querySelectorAll(".chart, .walkfig").forEach((el) => {
    if (el.offsetParent !== null && el.data) Plotly.Plots.resize(el);
  });
}
function plot(el, traces, layout) {
  el.data = true;
  const lay = Object.assign({ margin: { l: 55, r: 150, t: 30, b: 45 },
    legend: LEGEND, font: { size: 13 } }, layout || {});
  Plotly.react(el, traces, lay, { responsive: true });
}
function announce(msg) { $("live-announcer").textContent = msg; }

// ------------------------------------------------------------- worker
let worker = null, msgSeq = 0;
let runtimeReady = false, runtimeFailed = false;
const pending = new Map();
function callWorker(type, payload) {
  return new Promise((resolve, reject) => {
    const id = ++msgSeq;
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, type, payload });
  });
}
function initWorker() {
  try {
    const blob = new Blob([window.WORKER_SRC], { type: "text/javascript" });
    worker = new Worker(URL.createObjectURL(blob));
  } catch (e) {
    runtimeFailed = true;
    $("boot-status").textContent = "The Python runtime failed to load.";
    $("boot-progress").hidden = true;
    return;
  }
  worker.onmessage = (ev) => {
    const d = ev.data;
    if (d.type === "ready") {
      runtimeReady = true;
      $("boot-status").textContent = "Python runtime ready.";
      const bar = $("boot-progress");
      bar.max = 1; bar.value = 1;
      $("a-run").disabled = false;
      runLive();
    } else if (d.type === "fatal") {
      runtimeFailed = true;
      $("boot-status").textContent = "The Python runtime failed to load.";
      $("boot-progress").hidden = true;
    } else if (pending.has(d.id)) {
      const p = pending.get(d.id);
      pending.delete(d.id);
      if (d.ok) p.resolve(d.result); else p.reject(new Error(d.error));
    }
  };
  worker.onerror = () => {
    runtimeFailed = true;
    $("boot-status").textContent = "The Python runtime failed to load.";
    $("boot-progress").hidden = true;
  };
}

// ------------------------------------------------------- auto-run
function makeAutoRunner(fn, debounceMs) {
  let timer = null, running = false, again = false;
  async function kick() {
    if (running) { again = true; return; }
    running = true;
    try { await fn(); } catch (e) { /* fn reports its own errors */ }
    running = false;
    if (again) { again = false; schedule(); }
  }
  function schedule() {
    if (!runtimeReady || runtimeFailed || !worker) return;
    if (running) { again = true; return; }
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => { timer = null; kick(); }, debounceMs);
  }
  return { schedule };
}

// ------------------------------------------------------------- tabs
const PANELS = ["app", "theory", "code"];
function showPanel(name, push) {
  PANELS.forEach((p) => { $("panel-" + p).hidden = p !== name; });
  document.querySelectorAll(".tabbtn").forEach((b) =>
    b.classList.toggle("active", b.dataset.tab === name));
  if (push) history.replaceState(null, "", "#" + name);
  requestAnimationFrame(resizeCharts);
}
document.querySelectorAll(".tabbtn").forEach((b) =>
  b.addEventListener("click", () => showPanel(b.dataset.tab, true)));
document.querySelectorAll(".subbtn").forEach((b) =>
  b.addEventListener("click", () => {
    document.querySelectorAll(".subbtn").forEach((x) =>
      x.classList.toggle("active", x === b));
    $("sub-listings").hidden = b.dataset.subtab !== "listings";
    $("sub-walkthrough").hidden = b.dataset.subtab !== "walkthrough";
    if (b.dataset.subtab === "walkthrough") renderWalkFigs();
    requestAnimationFrame(resizeCharts);
  }));
function routeHash() {
  const h = location.hash.replace("#", "");
  if (!h) return;
  if (PANELS.includes(h)) { showPanel(h, false); return; }
  const el = document.getElementById(h);
  if (el) {
    const panel = el.closest(".panel");
    if (panel) showPanel(panel.id.replace("panel-", ""), false);
    const sub = el.closest(".subpanel");
    if (sub && sub.hidden)
      document.querySelector('[data-subtab="walkthrough"]').click();
    setTimeout(() => el.scrollIntoView(), 60);
  }
}
window.addEventListener("hashchange", routeHash);

// ------------------------------------------------------------- App
let liveShown = false;
function appPayload() {
  return {
    K: parseFloat($("i-K").value), tau: parseFloat($("i-tau").value),
    theta: parseFloat($("i-theta").value),
    lam: parseFloat($("i-lam").value), Ts: parseFloat($("i-Ts").value),
    u_min: parseFloat($("i-umin").value),
    u_max: parseFloat($("i-umax").value),
    anti_windup: $("i-aw").value === "on",
    dist_size: parseFloat($("i-dsize").value),
    dist_time: parseFloat($("i-dtime").value),
  };
}
function fmt(v, n) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return Math.abs(v) >= 100 ? v.toFixed(1) : v.toFixed(n);
}
function renderRun(res, precomputed) {
  const sfx = precomputed ? " (precomputed)" : "";
  const t = res.t, tEnd = t[t.length - 1];
  plot($("c-y"), [
    { x: t, y: res.y, mode: "lines", name: "output y" + sfx },
    { x: t, y: res.y_model, mode: "lines", name: "model output" + sfx },
    { x: [0, tEnd], y: [1, 1], mode: "lines",
      name: "set point" + sfx, line: { dash: "dash", color: "#888" } },
  ], { xaxis: { title: "t (s)" }, yaxis: { title: "y (dimensionless)" },
       title: "Output and model output" });
  plot($("c-u"), [
    { x: t, y: res.u_cmd, mode: "lines",
      name: "commanded u" + sfx, line: { dash: "dot" } },
    { x: t, y: res.u, mode: "lines", name: "delivered u" + sfx },
    { x: [0, tEnd], y: [res.u_max, res.u_max], mode: "lines",
      name: "maximum output limit" + sfx,
      line: { dash: "dash", color: "#c0392b" } },
    { x: [0, tEnd], y: [res.u_min, res.u_min], mode: "lines",
      name: "minimum output limit" + sfx,
      line: { dash: "dash", color: "#c0392b" } },
  ], { xaxis: { title: "t (s)" }, yaxis: { title: "u (dimensionless)" },
       title: "Manipulated variable" });
  plot($("c-d"), [
    { x: t, y: res.dhat, mode: "lines", name: "mismatch" + sfx },
  ], { xaxis: { title: "t (s)" },
       yaxis: { title: "d-hat (dimensionless)" },
       title: "Mismatch signal" });
  const m = res.metrics;
  $("a-table").innerHTML =
    '<table class="metrics"><tr><th>Measure</th><th>Value</th></tr>' +
    "<tr><td>IAE (s)</td><td>" + fmt(m.IAE, 3) + "</td></tr>" +
    "<tr><td>Overshoot (%)</td><td>" + fmt(m.overshoot_pct, 2) + "</td></tr>" +
    "<tr><td>Settled output y</td><td>" + fmt(m.final_y, 4) + "</td></tr>" +
    "<tr><td>Settled delivered u</td><td>" + fmt(m.final_u, 4) + "</td></tr>" +
    "<tr><td>Largest |commanded u|</td><td>" + fmt(m.max_abs_u_cmd, 3) + "</td></tr>" +
    "<tr><td>Samples at a limit (%)</td><td>" + fmt(m.sat_pct, 2) + "</td></tr></table>";
  const c = res.coeffs;
  $("a-coeffs").innerHTML =
    '<table class="metrics"><tr><th>Coefficient</th><th>Value</th></tr>' +
    ["a", "b1", "b2", "d", "f", "p0", "p1", "p2"].map((k) =>
      "<tr><td>" + k + "</td><td>" + fmt(c[k], 6) + "</td></tr>").join("") +
    "</table>";
  $("metrics-state").textContent = sfx;
  $("coeff-state").textContent = sfx;
  requestAnimationFrame(resizeCharts);
}
async function runLive() {
  if (!worker || !runtimeReady) return;
  try {
    const res = await callWorker("run", appPayload());
    renderRun(res, false);
    liveShown = true;
    $("a-stale").hidden = true;
    $("a-note").textContent = "";
    const pn = $("prestart-note");
    if (pn) pn.remove();
    announce("Run complete. Output settled at " +
      res.metrics.final_y.toFixed(3) + ".");
  } catch (e) {
    $("a-note").textContent = e.message;
    announce("Run failed: " + e.message);
  }
}
const appAuto = makeAutoRunner(runLive, 350);
document.querySelectorAll("#panel-app input, #panel-app select")
  .forEach((el) => el.addEventListener("change", () => {
    if (liveShown) $("a-stale").hidden = false;
    appAuto.schedule();
  }));
$("a-run").addEventListener("click", runLive);

// --------------------------------------------------- scrollspy
function initScrollspy(navId) {
  const nav = $(navId);
  if (!nav) return;
  const links = [...nav.querySelectorAll('a[href^="#"]')];
  const targets = links.map((a) =>
    document.getElementById(a.getAttribute("href").slice(1)))
    .filter(Boolean);
  if (!targets.length || !("IntersectionObserver" in window)) return;
  const obs = new IntersectionObserver((entries) => {
    for (const en of entries) {
      if (en.isIntersecting) {
        links.forEach((a) => a.removeAttribute("aria-current"));
        const link = links.find((a) =>
          a.getAttribute("href") === "#" + en.target.id);
        if (link) link.setAttribute("aria-current", "true");
      }
    }
  }, { rootMargin: "-20% 0px -70% 0px" });
  targets.forEach((t) => obs.observe(t));
}

// --------------------------------------------------- walkthrough figs
let walkDone = false;
function renderWalkFigs() {
  if (walkDone) return;
  walkDone = true;
  document.querySelectorAll("script[data-for]").forEach((s) => {
    const el = $(s.dataset.for);
    if (el) {
      const f = JSON.parse(s.textContent);
      plot(el, f.data, f.layout);
      Plotly.relayout(el, { "legend.x": 1.02, "legend.y": 1.0,
        "legend.xanchor": "left", "legend.yanchor": "top",
        "margin.r": 150 });
    }
  });
}

// ------------------------------------------------------------- init
try {
  const pre = JSON.parse($("prestart-data").textContent);
  renderRun(pre, true);
} catch (e) {
  $("a-note").textContent = "The precomputed display failed to load.";
}
initWorker();
routeHash();
initScrollspy("theory-toc");
initScrollspy("walk-toc");
window.addEventListener("resize", resizeCharts);
new MutationObserver(resizeCharts).observe(document.body,
  { attributes: true, subtree: true, attributeFilter: ["hidden"] });
