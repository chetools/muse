"use strict";
// Display and messaging only. Every number on this page is computed
// by the Python driver in the Pyodide worker (or precomputed at
// build time by the same driver).
const $ = (id) => document.getElementById(id);
const PRE = JSON.parse($("prestart-data").textContent);
const LEGEND = { x: 1.02, y: 1.0, xanchor: "left", yanchor: "top" };

function resizeCharts() {
  document.querySelectorAll(".chart, .walkfig").forEach((el) => {
    if (el.offsetParent !== null && el.data) {
      Plotly.Plots.resize(el);
    }
  });
}
function plot(el, traces, layout) {
  el.data = true;
  const lay = Object.assign({ margin: { l: 55, r: 130, t: 30, b: 45 },
    legend: LEGEND, font: { size: 13 } }, layout || {});
  Plotly.react(el, traces, lay, { responsive: true });
}

// ------------------------------------------------------------- worker
let worker = null, msgSeq = 0;
let runtimeReady = false, runtimeFailed = false;
const pending = new Map();
let progressCb = null;
function callWorker(type, payload, onProgress) {
  return new Promise((resolve, reject) => {
    const id = ++msgSeq;
    pending.set(id, { resolve, reject });
    progressCb = onProgress || null;
    worker.postMessage({ id, type, payload });
  });
}
function initWorker() {
  try {
    const blob = new Blob([window.WORKER_SRC], { type: "text/javascript" });
    worker = new Worker(URL.createObjectURL(blob));
  } catch (e) {
    $("boot-status").textContent =
      "The Python runtime could not start. The precomputed default " +
      "run remains displayed.";
    return;
  }
  worker.onmessage = (ev) => {
    const d = ev.data;
    if (d.type === "ready") {
      runtimeReady = true;
      $("boot-status").textContent = "Python runtime ready.";
      document.querySelectorAll("button.run, #m-dual-manual, " +
        "#m-dual-half, #m-dual-ls, #s-load-opt, #s-load-click")
        .forEach((b) => { if (b.id !== "s-load-opt" &&
                            b.id !== "s-load-click") b.disabled = false; });
      // A sweep marked stale while its panel was on screen runs now.
      if (sweepStale && !$("panel-sweep").hidden) sweepAuto.schedule();
    } else if (d.type === "progress") {
      if (progressCb) progressCb(d.frac);
    } else if (d.type === "fatal") {
      runtimeFailed = true;
      $("boot-status").textContent =
        "The Python runtime failed to load. The precomputed default " +
        "run remains displayed.";
    } else if (pending.has(d.id)) {
      const p = pending.get(d.id);
      pending.delete(d.id);
      if (d.ok) p.resolve(d.result); else p.reject(new Error(d.error));
    }
  };
  worker.onerror = () => {
    runtimeFailed = true;
    $("boot-status").textContent =
      "The Python runtime failed to load. The precomputed default " +
      "run remains displayed.";
  };
}

// ------------------------------------------------------- auto-run
// Fast calculations run automatically when inputs change: a change
// schedules one run after a debounce; changes inside the window
// coalesce, and a change arriving while a run is in flight schedules
// exactly one follow-up run, which reads the latest inputs when it
// starts. Scheduling is gated on the runtime being ready — before
// boot (or after a failed boot) a change only marks the display
// stale, exactly as it did before auto-run existed.
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
const PANELS = ["model", "app", "sweep", "theory", "code"];
function showPanel(name, push) {
  PANELS.forEach((p) => { $("panel-" + p).hidden = p !== name; });
  document.querySelectorAll(".tabbtn").forEach((b) =>
    b.classList.toggle("active", b.dataset.tab === name));
  if (push) history.replaceState(null, "", "#" + name);
  // A sweep left stale by App edits runs once when its panel is
  // next shown and the runtime is ready.
  if (name === "sweep" && sweepStale && runtimeReady && !runtimeFailed)
    sweepAuto.schedule();
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
  if (PANELS.includes(h)) { showPanel(h, false); return; }
  const el = document.getElementById(h);
  if (el) {
    const panel = el.closest(".panel");
    if (panel) showPanel(panel.id.replace("panel-", ""), false);
    const sub = el.closest(".subpanel");
    if (sub && sub.hidden) {
      document.querySelector('[data-subtab="walkthrough"]').click();
    }
    setTimeout(() => el.scrollIntoView(), 60);
  }
}
window.addEventListener("hashchange", routeHash);

// ------------------------------------------------------------- metrics table
function metricsTable(rows) {
  // rows: [{name, metrics}] — metrics keys per driver._metrics_plain
  const cols = [["IAE", "IAE (% s)"], ["ITAE", "ITAE (% s²)"],
    ["overshoot_pct", "Overshoot (%)"], ["settling_s", "Settling (s)"],
    ["MV_travel_pct", "MV travel (%)"], ["Ms", "Ms (–)"],
    ["saturated", "Limited?"]];
  let h = '<table class="metrics"><tr><th>Run</th>' +
    cols.map((c) => "<th>" + c[1] + "</th>").join("") + "</tr>";
  for (const r of rows) {
    const m = r.metrics;
    h += "<tr><td>" + r.name + "</td>" + cols.map((c) => {
      let v = m[c[0]];
      if (c[0] === "saturated") return "<td>" + (v ? "yes" : "no") + "</td>";
      if (v === null || v === undefined || Number.isNaN(v))
        return "<td>—</td>";
      let s = (Math.abs(v) >= 100 ? v.toFixed(1) : v.toFixed(3));
      if (c[0] === "Ms" && v > 2.0) s += " (infeasible)";
      return "<td>" + s + "</td>";
    }).join("") + "</tr>";
  }
  return h + "</table>";
}

// ------------------------------------------------------------- App tab
let overlays = [];   // {name, res, metrics}
let lastSpans = [];
function appPayload(extra) {
  const tfOff = $("a-tf-off").checked;
  const p = {
    Kp: parseFloat($("a-Kp").value), tau: parseFloat($("a-tau").value),
    theta: parseFloat($("a-theta").value),
    mode: $("a-mode").value, input_type: $("a-input-type").value,
    form: $("a-form").value,
    Kc: parseFloat($("a-Kc").value), Ti: parseFloat($("a-Ti").value),
    Td: parseFloat($("a-Td").value),
    b_weight: parseFloat($("a-b").value),
    Tf_ratio: tfOff ? null : parseFloat($("a-tf-ratio").value),
    noise_on: $("a-noise-on").checked,
    noise_level: parseFloat($("a-noise-level").value),
    sp_step: parseFloat($("a-sp-step").value),
    load_step: parseFloat($("a-load-step").value),
    u_min: parseFloat($("a-u-min").value),
    u_max: parseFloat($("a-u-max").value),
    bias: parseFloat($("a-bias").value),
    slew: $("a-slew-off").checked ? null : parseFloat($("a-slew").value),
    anti_windup: $("a-aw").value,
    Tt: $("a-Tt").value === "" ? null : parseFloat($("a-Tt").value),
  };
  return Object.assign(p, extra || {});
}
function renderApp() {
  const sp = parseFloat($("a-sp-step").value);
  const pvT = [], mvT = [];
  if ($("a-show-pv").checked) {
    overlays.forEach((o) => pvT.push({ x: o.res.t, y: o.res.y,
      mode: "lines", name: o.name }));
    if (overlays.length) pvT.push({ x: [0, overlays[0].res.horizon],
      y: [sp, sp], mode: "lines", name: "set point (%)",
      line: { dash: "dash", color: "#888" } });
  }
  if ($("a-show-e").checked) overlays.forEach((o) =>
    pvT.push({ x: o.res.t, y: o.res.e, mode: "lines",
      name: o.name + " error (%)", line: { dash: "dot" } }));
  if ($("a-show-mv").checked) overlays.forEach((o) =>
    mvT.push({ x: o.res.t, y: o.res.u, mode: "lines", name: o.name }));
  if ($("a-show-pid").checked && overlays.length) {
    const o = overlays[overlays.length - 1];
    [["P", "P (%)"], ["I", "I (%)"], ["D", "D (%)"]].forEach((k) =>
      mvT.push({ x: o.res.t, y: o.res[k[0]], mode: "lines",
        name: o.name + " " + k[1], line: { dash: "dot" } }));
  }
  plot($("a-chart-pv"), pvT, { xaxis: { title: "t (s)" },
    yaxis: { title: "y (%)" }, title: "Controlled variable" });
  const shapes = lastSpans.map((s) => ({ type: "rect", xref: "x",
    yref: "paper", x0: s[0], x1: s[1], y0: 0, y1: 1,
    fillcolor: "rgba(200,60,40,0.12)", line: { width: 0 } }));
  plot($("a-chart-mv"), mvT, { xaxis: { title: "t (s)" },
    yaxis: { title: "u (%)" }, title: "Controller output " +
    "(shaded: output limited)", shapes: shapes });
  $("a-table").innerHTML = overlays.length
    ? metricsTable(overlays.map((o) => ({ name: o.name, metrics: o.metrics })))
    : "";
  $("a-stale").hidden = true;
}
async function runAppAs(name) {
  if (!worker) return;
  try {
    const res = await callWorker("app_run", appPayload());
    overlays = overlays.filter((o) => o.name !== name);
    overlays.push({ name, res, metrics: res.metrics });
    if (overlays.length > 4) overlays.shift();
    lastSpans = res.limited_spans || [];
    renderApp();
  } catch (e) { $("a-note").textContent = e.message; }
}
const appAuto = makeAutoRunner(() => runAppAs("Manual tuning"), 350);
// One path for every App input change, typed or programmatic:
// mark the display stale, register the sweep impact, and schedule
// the automatic re-run (a no-op until the runtime is ready).
function appInputsChanged() {
  markStale();
  noteSweepImpact();
  appAuto.schedule();
}
async function refreshTuning(which) {
  if (!worker) return;
  const res = await callWorker("tuning", appPayload());
  const src = which === "ZN" ? res.ZN : res;
  $("a-Kc").value = src.Kc.toFixed(4);
  $("a-Ti").value = src.Ti.toFixed(4);
  $("a-Td").value = src.Td.toFixed(4);
  $("a-note").textContent = res.note || "";
  noteSweepImpact();
  runAppAs(which === "ZN" ? "Ziegler–Nichols" : "Smith and Corripio");
}
$("a-run").addEventListener("click", () => runAppAs("Manual tuning"));
$("a-use-sc").addEventListener("click", () => refreshTuning("SC"));
$("a-use-zn").addEventListener("click", () => refreshTuning("ZN"));
$("a-clear").addEventListener("click", () => { overlays = []; renderApp(); });
$("a-windup-preset").addEventListener("click", () => {
  $("a-sp-step").value = 25; $("a-load-step").value = 0;
  $("a-u-min").value = 0; $("a-u-max").value = 80;
  $("a-aw").value = "none";
  $("a-note").textContent = "Windup preset set: set-point step 25 %, " +
    "output limited to 80 %. Run with anti-windup None, then with " +
    "Clamping or Back-calculation, and compare the overshoot.";
  appInputsChanged();
});
$("a-preset").addEventListener("change", () => {
  const r = parseFloat($("a-preset").value);
  if (!Number.isNaN(r)) {
    $("a-theta").value = (r * parseFloat($("a-tau").value)).toFixed(2);
    appInputsChanged();
  }
});
function markStale() { $("a-stale").hidden = false; }
// Every computational input and select auto-runs on change; the
// display toggles are excluded — they only re-render the last run.
const DISPLAY_ONLY = ["a-show-pv", "a-show-mv", "a-show-e", "a-show-pid"];
document.querySelectorAll("#panel-app input, #panel-app select")
  .forEach((el) => { if (!DISPLAY_ONLY.includes(el.id))
    el.addEventListener("change", appInputsChanged); });
["a-show-pv", "a-show-mv", "a-show-e", "a-show-pid"].forEach((id) =>
  $(id).addEventListener("change", renderApp));

// ------------------------------------------------------------- Model tab
let modelRes = null;
function modelPayload() {
  return { family: $("m-family").value, Kp: parseFloat($("m-Kp").value),
    n_lags: parseInt($("m-n").value), tau_each: parseFloat($("m-tau-each").value),
    tau1: parseFloat($("m-tau1").value), tau2: parseFloat($("m-tau2").value),
    tau_n: parseFloat($("m-tau-n").value), zeta: parseFloat($("m-zeta").value),
    theta0: parseFloat($("m-theta0").value),
    man_tau: parseFloat($("m-man-tau").value),
    man_theta: parseFloat($("m-man-theta").value),
    noise_on: $("m-noise-on").checked,
    noise_level: parseFloat($("m-noise-level").value),
    sample_dt: parseFloat($("m-sample-dt").value) };
}
const METHOD_NAMES = { manual: "Manual", half: "Half rule", ls: "Least squares" };
const METHOD_COLORS = { manual: "#2563eb", half: "#dd7700", ls: "#1a9850" };
function renderModel() {
  if (!modelRes) return;
  const traces = [{ x: modelRes.t, y: modelRes.y_true, mode: "lines",
    name: "true plant (%)", line: { color: "#222", width: 2.5 } }];
  const resid = [];
  for (const k of Object.keys(modelRes.methods)) {
    traces.push({ x: modelRes.t, y: modelRes.methods[k].y, mode: "lines",
      name: METHOD_NAMES[k] + " (%)", line: { color: METHOD_COLORS[k] } });
    resid.push({ x: modelRes.t, y: modelRes.methods[k].resid,
      mode: "lines", name: METHOD_NAMES[k] + " residual (%)",
      line: { color: METHOD_COLORS[k] } });
  }
  if (modelRes.sampled) traces.push({ x: modelRes.sampled.t,
    y: modelRes.sampled.y, mode: "markers", name: "sampled data (%)",
    marker: { size: 4 } });
  plot($("m-chart-fit"), traces, { xaxis: { title: "t (s)" },
    yaxis: { title: "y (%)" }, title: "Step responses, input step 10 %" });
  plot($("m-chart-resid"), resid, { xaxis: { title: "t (s)" },
    yaxis: { title: "residual (%)" }, title: "Residuals" });
  let h = '<table class="metrics"><tr><th>Method</th><th>Kp (–)</th>' +
    "<th>τ (s)</th><th>θ (s)</th><th>θ/τ (–)</th>" +
    "<th>Mismatch IAE (% s)</th></tr>";
  for (const k of Object.keys(modelRes.methods)) {
    const m = modelRes.methods[k];
    h += "<tr><td>" + METHOD_NAMES[k] + "</td><td>" + m.Kp.toFixed(3) +
      "</td><td>" + m.tau.toFixed(3) + "</td><td>" + m.theta.toFixed(3) +
      "</td><td>" + m.ratio.toFixed(3) + "</td><td>" +
      m.IAE_mismatch.toFixed(2) + "</td></tr>";
  }
  $("m-table").innerHTML = h + "</table>";
  $("m-note").textContent = modelRes.methods.half ? "" :
    "The half rule does not apply to the underdamped family; the " +
    "Manual and Least-squares approximations show why: no FOPTD " +
    "model reproduces an overshooting step response.";
}
async function runModel() {
  if (!worker) return;
  try {
    modelRes = await callWorker("model", modelPayload());
    renderModel();
  } catch (e) { $("m-note").textContent = e.message; }
}
$("m-run").addEventListener("click", runModel);
const modelAuto = makeAutoRunner(runModel, 350);
document.querySelectorAll("#panel-model input, #panel-model select")
  .forEach((el) => el.addEventListener("change",
    () => modelAuto.schedule()));
$("m-family").addEventListener("change", () => {
  const f = $("m-family").value;
  $("m-fam-equal").hidden = f !== "lags_equal";
  $("m-fam-two").hidden = f !== "lags_two";
  $("m-fam-under").hidden = f !== "underdamped";
});
document.querySelectorAll("[data-preset]").forEach((b) =>
  b.addEventListener("click", () => {
    const p = b.dataset.preset;
    if (p === "mild") { $("m-family").value = "lags_two";
      $("m-tau1").value = 8; $("m-tau2").value = 6; $("m-theta0").value = 0; }
    if (p === "severe") { $("m-family").value = "lags_equal";
      $("m-n").value = 5; $("m-tau-each").value = 4; $("m-theta0").value = 0; }
    if (p === "deadtime") { $("m-family").value = "lags_equal";
      $("m-n").value = 2; $("m-tau-each").value = 5; $("m-theta0").value = 6; }
    $("m-family").dispatchEvent(new Event("change"));
  }));
async function runDual(method) {
  if (!worker || !modelRes || !modelRes.methods[method]) return;
  const m = modelRes.methods[method];
  const p = Object.assign(modelPayload(),
    appPayload({ fitted: { Kp: m.Kp, tau: m.tau, theta: m.theta } }));
  try {
    const res = await callWorker("dual", p);
    const traces = [];
    for (const k of ["fitted", "true"]) {
      traces.push({ x: res.runs[k].t, y: res.runs[k].y, mode: "lines",
        name: (k === "fitted" ? "fitted FOPTD" : "true plant") + " (%)" });
    }
    plot($("m-chart-dual"), traces, { xaxis: { title: "t (s)" },
      yaxis: { title: "y (%)" },
      title: "Tuning from the " + METHOD_NAMES[method] +
        " fit: Kc = " + res.Kc.toFixed(3) + ", Ti = " +
        res.Ti.toFixed(2) + " s, Td = " + res.Td.toFixed(3) + " s" });
    $("m-dual-table").innerHTML = metricsTable([
      { name: "On fitted FOPTD", metrics: res.runs.fitted.metrics },
      { name: "On true plant", metrics: res.runs.true.metrics }]);
  } catch (e) { $("m-note").textContent = e.message; }
}
$("m-dual-manual").addEventListener("click", () => runDual("manual"));
$("m-dual-half").addEventListener("click", () => runDual("half"));
$("m-dual-ls").addEventListener("click", () => runDual("ls"));
async function useForTuning(method) {
  if (!modelRes || !modelRes.methods[method]) return;
  const m = modelRes.methods[method];
  $("a-Kp").value = m.Kp; $("a-tau").value = m.tau.toFixed(3);
  $("a-theta").value = m.theta.toFixed(3);
  showPanel("app", true);
  if (worker) refreshTuning("SC");
}

$("m-use-manual").addEventListener("click", () => useForTuning("manual"));
$("m-use-half").addEventListener("click", () => useForTuning("half"));
$("m-use-ls").addEventListener("click", () => useForTuning("ls"));

// ------------------------------------------------------------- Sweep tab
let sweepRes = null, clickedPoint = null;
let sweepStale = false;
// An App input change reaches the sweep in one of two ways: while
// the Sweep panel is visible it schedules an automatic re-sweep;
// while hidden it only marks the results stale (the note says so),
// and showing the panel again runs the sweep once — see showPanel.
function noteSweepImpact() {
  if (!$("panel-sweep").hidden) { sweepAuto.schedule(); return; }
  sweepStale = true;
  $("s-note").textContent = "App inputs have changed since these " +
    "sweeps were computed. The sweep runs again when this panel " +
    "is shown.";
}
const sweepAuto = makeAutoRunner(runSweep, 800);
function renderSweep() {
  if (!sweepRes) return;
  for (const param of ["Kc", "Ti", "Td"]) {
    const rows = sweepRes.slices[param];
    plot($("s-chart-" + param),
      [{ x: sweepRes.factors, y: rows.map((r) => r.IAE),
         mode: "lines+markers", name: "IAE (% s)" },
       { x: [1], y: [rows[12].IAE], mode: "markers",
         name: "Smith and Corripio point", marker: { size: 11, symbol: "x" } }],
      { xaxis: { title: param + " factor (dimensionless)", type: "log",
          tickvals: [0.25, 0.5, 1, 2, 4],
          ticktext: ["0.25", "0.5", "1", "2", "4"] },
        yaxis: { title: "IAE (% s)" }, title: "Slice over " + param });
  }
  const heat = sweepRes.heat;
  plot($("s-chart-heat"),
    [{ type: "heatmap", x: heat.kc_factors, y: heat.ti_factors,
       z: heat.IAE, colorscale: "Viridis",
       colorbar: { title: "IAE (% s)" }, name: "IAE (% s)" },
     { x: [1], y: [1], mode: "markers", name: "Smith and Corripio point",
       marker: { size: 13, symbol: "x", color: "white" } }],
    { xaxis: { title: "Kc factor (dimensionless)", type: "log",
        tickvals: [0.25, 0.5, 1, 2, 4], ticktext: ["0.25", "0.5", "1", "2", "4"] },
      yaxis: { title: "Ti factor (dimensionless)", type: "log",
        tickvals: [0.25, 0.5, 1, 2, 4], ticktext: ["0.25", "0.5", "1", "2", "4"] },
      title: "IAE over Kc and Ti factors (click a cell to inspect)" });
  const o = heat.opt, m = o.metrics;
  $("s-opt").innerHTML = "<p>Kc = " + o.Kc.toFixed(3) + ", Ti = " +
    o.Ti.toFixed(2) + " s, Td = " + o.Td.toFixed(3) + " s<br>IAE = " +
    m.IAE.toFixed(2) + " % s, overshoot = " + m.overshoot_pct.toFixed(2) +
    " %, Ms = " + (m.Ms === null ? "—" : m.Ms.toFixed(2)) +
    (m.Ms > 2.0 ? " — flagged infeasible (Ms above 2.0)" : "") +
    (m.saturated ? "<br>This optimum run reaches an output limit." : "") +
    "</p>";
  $("s-load-opt").disabled = !worker;
  $("s-chart-heat").on("plotly_click", (ev) => {
    const pt = ev.points[0];
    if (pt.curveNumber !== 0) return;
    const base = appPayload();
    clickedPoint = { Kc: base.Kc * pt.x, Ti: base.Ti * pt.y, Td: base.Td,
                     IAE: pt.z };
    $("s-click").innerHTML = "<p>Kc = " + clickedPoint.Kc.toFixed(3) +
      ", Ti = " + clickedPoint.Ti.toFixed(2) + " s, IAE = " +
      pt.z.toFixed(2) + " % s</p>";
    $("s-load-click").disabled = !worker;
  });
}
async function runSweep() {
  if (!worker) return;
  sweepStale = false;
  const bar = $("s-progress");
  bar.hidden = false; bar.value = 0;
  try {
    sweepRes = await callWorker("sweep", appPayload(),
      (f) => { bar.value = f; });
    renderSweep();
    $("s-note").textContent = "Sweeps computed with the App limits, " +
      "slew and anti-windup settings active.";
  } catch (e) { $("s-note").textContent = e.message; }
  bar.hidden = true;
}
$("s-run").addEventListener("click", runSweep);
function loadIntoApp(pt) {
  $("a-Kc").value = pt.Kc.toFixed(4);
  $("a-Ti").value = pt.Ti.toFixed(4);
  $("a-Td").value = pt.Td.toFixed(4);
  showPanel("app", true);
  // The loaded point changes the App tuning the sweep is based on.
  noteSweepImpact();
  runAppAs("Sweep point");
}
$("s-load-opt").addEventListener("click", () => {
  if (sweepRes) loadIntoApp(sweepRes.heat.opt);
});
$("s-load-click").addEventListener("click", () => {
  if (clickedPoint) loadIntoApp(clickedPoint);
});

// ------------------------------------------------------------- walkthrough figs
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

// ------------------------------------------------------------- prestart
function initFromPrestart() {
  const t = PRE.tuning;
  $("a-Kc").value = t.Kc.toFixed(4);
  $("a-Ti").value = t.Ti.toFixed(4);
  $("a-Td").value = t.Td.toFixed(4);
  overlays = [{ name: "Smith and Corripio (precomputed)",
                res: PRE.app, metrics: PRE.app.metrics }];
  lastSpans = PRE.app.limited_spans || [];
  renderApp();
  modelRes = PRE.model;
  renderModel();
  sweepRes = PRE.sweep;
  renderSweep();
}
initFromPrestart();
initWorker();
routeHash();
window.addEventListener("resize", resizeCharts);
new MutationObserver(resizeCharts).observe(document.body,
  { attributes: true, subtree: true, attributeFilter: ["hidden"] });
