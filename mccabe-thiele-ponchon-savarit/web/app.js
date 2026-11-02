"use strict";
/* App logic. All calculation is done by mtps_core.py in the Pyodide
   worker; this file only reads controls, draws figures from the
   returned arrays, and manages the page. */
const $ = (id) => document.getElementById(id);
const fmt = (v, d) => (v === null || v === undefined || !isFinite(v)) ? "–" : Number(v).toFixed(d);
const BLUE = "#0072B2", ORANGE = "#D55E00", GREEN = "#009E73", PINK = "#CC79A7", GREY = "#999999";
const LEGEND = { x: 1.02, y: 1.0, xanchor: "left", yanchor: "top" };
const PCTL = { responsive: true, displayModeBar: false };

let displayedSpec = null;   // spec of the run currently displayed
let current = null;         // current result object
let stepShown = Infinity;   // stages revealed by the step buttons
let workerReady = false;
let solveSeq = 0;

/* ---------- tabs and hash routing ---------- */
const PANELS = ["app", "theory", "code"];
function showPanel(name, push) {
  PANELS.forEach((p) => {
    $("panel-" + p).classList.toggle("active", p === name);
    $("tabbtn-" + p).setAttribute("aria-selected", p === name ? "true" : "false");
  });
  if (push) history.replaceState(null, "", "#" + name);
  if (name === "code") renderWalkFigs();
}
document.querySelectorAll("nav.tabs button").forEach((b) => {
  b.addEventListener("click", () => showPanel(b.dataset.panel, true));
});
document.querySelectorAll(".subtabs button").forEach((b) => {
  b.addEventListener("click", () => {
    document.querySelectorAll(".subtabs button").forEach((x) =>
      x.setAttribute("aria-selected", x === b ? "true" : "false"));
    $("sub-listings").classList.toggle("active", b.dataset.sub === "listings");
    $("sub-walkthrough").classList.toggle("active", b.dataset.sub === "walkthrough");
    if (b.dataset.sub === "walkthrough") renderWalkFigs();
  });
});
function routeHash() {
  const h = (location.hash || "#app").slice(1);
  if (PANELS.includes(h)) { showPanel(h, false); return; }
  const el = document.getElementById(h);
  if (!el) { showPanel("app", false); return; }
  if (el.closest("#panel-theory")) showPanel("theory", false);
  else if (el.closest("#panel-code")) {
    showPanel("code", false);
    if (el.closest("#sub-walkthrough")) {
      document.querySelectorAll(".subtabs button").forEach((x) =>
        x.setAttribute("aria-selected", x.dataset.sub === "walkthrough" ? "true" : "false"));
      $("sub-listings").classList.remove("active");
      $("sub-walkthrough").classList.add("active");
    }
  } else if (el.closest("#panel-app")) showPanel("app", false);
  setTimeout(() => el.scrollIntoView(), 60);
}
window.addEventListener("hashchange", routeHash);

/* scrollspy for the Theory and Code tables of contents */
function scrollspy(rootSel, tocSel) {
  const root = document.querySelector(rootSel);
  const toc = $(tocSel);
  if (!root || !toc) return;
  const links = new Map();
  toc.querySelectorAll("a[href^='#']").forEach((a) =>
    links.set(a.getAttribute("href").slice(1), a));
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        toc.querySelectorAll("a").forEach((a) => a.classList.remove("current"));
        const a = links.get(e.target.id);
        if (a) a.classList.add("current");
      }
    });
  }, { rootMargin: "-20% 0px -70% 0px" });
  root.querySelectorAll("[id]").forEach((el) => {
    if (links.has(el.id)) obs.observe(el);
  });
}

/* ---------- controls ---------- */
const SYS_DEFAULTS = {
  "alpha": { zF: 0.5, xD: 0.95 },
  "benzene-toluene": { zF: 0.4, xD: 0.95 },
  "methanol-water": { zF: 0.4, xD: 0.95 },
  "ethanol-water": { zF: 0.4, xD: 0.80 },
  "isopropanol-water": { zF: 0.4, xD: 0.60 },
};
function pressureFromSlider() {
  return 0.5 * Math.pow(20, Number($("P").value) / 1000);
}
function feedMode() {
  return document.querySelector("input[name='feedmode']:checked").value;
}
function readSpec() {
  const sys = $("sys").value;
  const spec = {
    system: sys,
    P_atm: pressureFromSlider(),
    alpha_value: Number($("alpha").value),
    latent_ratio: Number($("ratio").value),
    zF: Number($("zF").value),
    xD: Number($("xD").value),
    xB: Number($("xB").value),
    R_mult: Number($("Rmult").value),
    feed_mode: feedMode(),
    q: Number($("q").value),
    TF_C: Number($("TF").value),
    PF_atm: Math.max(Number($("PF").value), pressureFromSlider()),
  };
  return spec;
}
function refreshControlVisibility() {
  const sys = $("sys").value;
  const real = sys !== "alpha";
  $("ctl-pressure").style.display = real ? "" : "none";
  $("ctl-alpha").style.display = real ? "none" : "";
  $("ctl-ratio").style.display = real ? "none" : "";
  $("app-txy").style.display = real ? "" : "none";
  const tp = feedMode() === "TP";
  $("ctl-q").style.display = tp ? "none" : "";
  $("ctl-tp").style.display = tp ? "" : "none";
  if (!real && tp) {
    document.querySelector("input[name='feedmode'][value='q']").checked = true;
    $("ctl-q").style.display = "";
    $("ctl-tp").style.display = "none";
  }
  document.querySelector("input[name='feedmode'][value='TP']").disabled = !real;
}
function refreshLabels() {
  $("alpha-val").textContent = "= " + fmt(Number($("alpha").value), 2);
  $("ratio-val").textContent = "= " + fmt(Number($("ratio").value), 2);
  $("P-val").textContent = "= " + fmt(pressureFromSlider(), 2) + " atm";
  $("zF-val").textContent = "= " + fmt(Number($("zF").value), 2);
  $("xD-val").textContent = "= " + fmt(Number($("xD").value), 3);
  $("xB-val").textContent = "= " + fmt(Number($("xB").value), 3);
  $("Rmult-val").textContent = "= " + fmt(Number($("Rmult").value), 2) + " × R_min";
  $("q-val").textContent = "= " + fmt(Number($("q").value), 2);
}
function markStale() {
  refreshLabels();
  const stale = JSON.stringify(readSpec()) !== JSON.stringify(displayedSpec);
  $("stale-note").style.display = stale ? "block" : "none";
}
["sys", "alpha", "ratio", "P", "zF", "xD", "xB", "Rmult", "q", "TF", "PF"]
  .forEach((id) => $(id).addEventListener("input", () => {
    if (id === "sys") {
      const d = SYS_DEFAULTS[$("sys").value];
      $("zF").value = d.zF; $("xD").value = d.xD; $("xB").value = 0.05;
      refreshControlVisibility();
    }
    markStale();
  }));
document.querySelectorAll("input[name='feedmode']").forEach((r) =>
  r.addEventListener("change", () => { refreshControlVisibility(); markStale(); }));

/* ---------- rendering ---------- */
function interp(xs, ys, x) {
  if (x <= xs[0]) return ys[0];
  if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
  let lo = 0, hi = xs.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (xs[m] <= x) lo = m; else hi = m; }
  const t = (x - xs[lo]) / (xs[hi] - xs[lo]);
  return ys[lo] + t * (ys[hi] - ys[lo]);
}
function mtStageCount(r) { return Math.max(0, (r.mt.staircase.length - 1) / 2); }
function totalSteps() {
  if (!current) return 0;
  return Math.max(mtStageCount(current), current.ps.stages.length);
}
function renderMT(r, shown) {
  const eq = r.eq_curve;
  const pts = r.mt.staircase;
  const nShow = Math.min(shown, mtStageCount(r));
  const cut = pts.slice(0, 2 * nShow + 1);
  const traces = [
    { type: "scatter", x: eq.x, y: eq.y, mode: "lines", name: "Equilibrium curve",
      line: { color: BLUE, width: 2 } },
    { type: "scatter", x: [0, 1], y: [0, 1], mode: "lines", name: "Diagonal y = x",
      line: { color: GREY, width: 1, dash: "dash" } },
    { type: "scatter", x: [r.xB, r.mt.x_int, r.xD], y: [r.xB, r.mt.y_int, r.xD],
      mode: "lines", name: "Operating lines and q-line",
      line: { color: "#56B4E9", width: 1 } },
    { type: "scatter", x: cut.map((p) => p[0]), y: cut.map((p) => p[1]),
      mode: "lines", name: "Staircase", line: { color: ORANGE, width: 2 } },
  ];
  const lx = [], ly = [], lt = [];
  for (let k = 1; k <= nShow; k++) {
    const p = pts[2 * k - 1];
    if (p) { lx.push(p[0]); ly.push(p[1]); lt.push(String(k)); }
  }
  traces.push({ type: "scatter", x: lx, y: ly, mode: "markers+text", name: "Stage liquid points",
    text: lt, textposition: "bottom right", textfont: { size: 10 },
    marker: { color: ORANGE, size: 6 } });
  Plotly.react("fig-mt", traces, {
    margin: { l: 52, r: 150, t: 8, b: 44 }, legend: LEGEND,
    xaxis: { title: "x", range: [0, 1] }, yaxis: { title: "y", range: [0, 1] },
  }, PCTL);
}
function renderPS(r, shown) {
  const eq = r.eq_curve;
  const st = r.ps.stages;
  const nShow = Math.min(shown, st.length);
  const traces = [
    { type: "scatter", x: eq.x, y: eq.h_liq, mode: "lines", name: "Saturated liquid h(x)",
      line: { color: BLUE, width: 2 } },
    { type: "scatter", x: eq.y, y: eq.H_vap, mode: "lines", name: "Saturated vapour H(y)",
      line: { color: ORANGE, width: 2 } },
  ];
  const tieX = [], tieY = [], rayX = [], rayY = [], lx = [], ly = [], lt = [];
  for (let k = 1; k <= nShow; k++) {
    const s = st[k - 1];
    const hL = interp(eq.x, eq.h_liq, s.x), HV = interp(eq.y, eq.H_vap, s.y);
    tieX.push(s.x, s.y, null); tieY.push(hL, HV, null);
    lx.push(s.x); ly.push(hL); lt.push(String(k));
    if (k < st.length) {
      const yn = st[k].y, Hn = interp(eq.y, eq.H_vap, yn);
      const rect = s.x > r.ps.x_tie_feed;
      const px = rect ? r.xD : r.xB, pH = rect ? r.ps.H_DD : r.ps.H_DB;
      rayX.push(px, yn, null); rayY.push(pH, Hn, null);
    }
  }
  traces.push({ type: "scatter", x: rayX, y: rayY, mode: "lines", name: "Rays to difference points",
    line: { color: GREY, width: 1 }, hoverinfo: "skip" });
  traces.push({ type: "scatter", x: tieX, y: tieY, mode: "lines", name: "Tie lines",
    line: { color: GREEN, width: 1.4 } });
  traces.push({ type: "scatter", x: lx, y: ly, mode: "markers+text", name: "Stage liquid points",
    text: lt, textposition: "top right", textfont: { size: 10 },
    marker: { color: GREEN, size: 6 } });
  traces.push({ type: "scatter", x: [r.xD, r.xB], y: [r.ps.H_DD, r.ps.H_DB],
    mode: "markers", name: "Difference points (poles)",
    marker: { color: "#000000", size: 9, symbol: ["x", "square"] } });
  traces.push({ type: "scatter", x: [r.zF], y: [r.hF_kj_mol], mode: "markers",
    name: "Feed point", marker: { color: PINK, size: 10 } });
  const allH = eq.h_liq.concat(eq.H_vap, [r.ps.H_DD, r.ps.H_DB, r.hF_kj_mol]);
  const hmin = Math.min.apply(null, allH), hmax = Math.max.apply(null, allH);
  const pad = 0.06 * (hmax - hmin || 1);
  Plotly.react("fig-ps", traces, {
    margin: { l: 58, r: 150, t: 8, b: 44 }, legend: LEGEND,
    xaxis: { title: "mole fraction of light component", range: [0, 1] },
    yaxis: { title: "molar enthalpy (kJ/mol)", range: [hmin - pad, hmax + pad] },
  }, PCTL);
}
function renderTXY(r) {
  if (r.system === "alpha") return;
  const eq = r.eq_curve;
  Plotly.react("fig-txy", [
    { type: "scatter", x: eq.x, y: eq.T_C, mode: "lines", name: "Bubble point (liquid)",
      line: { color: BLUE, width: 2 } },
    { type: "scatter", x: eq.y, y: eq.T_C, mode: "lines", name: "Dew point (vapour)",
      line: { color: ORANGE, width: 2 } },
  ], {
    margin: { l: 52, r: 150, t: 8, b: 44 }, legend: LEGEND,
    xaxis: { title: "mole fraction of light component", range: [0, 1] },
    yaxis: { title: "T (°C)" },
  }, PCTL);
}
function metricCards(r) {
  const unb = r.infeasible_azeotrope;
  const nd = "not defined";
  const mtN = unb ? "unbounded"
    : (r.mt.pinched ? "unbounded (pinched)" : fmt(r.mt.N, 2));
  const psN = unb ? "unbounded"
    : (r.ps.pinched ? "unbounded (pinched)" : fmt(r.ps.N, 2));
  const fsMT = r.mt.pinched ? "—" : r.mt.feed_stage;
  const fsPS = r.ps.pinched ? "—" : r.ps.feed_stage;
  const cards = [
    ["McCabe–Thiele stages, N", mtN, ""],
    ["Ponchon–Savarit stages, N", psN, ""],
    ["Feed stage, MT / PS", fsMT + " / " + fsPS, ""],
    ["Reflux ratio, R", unb ? nd : fmt(r.R, 3), ""],
    ["Minimum reflux ratio, R_min", unb ? nd : fmt(r.R_min, 3), ""],
    ["Minimum stages, N_min", fmt(r.N_min, 2), ""],
    ["Condenser duty, Q_C", unb ? nd : fmt(r.ps.QC_MW, 2), "MW"],
    ["Reboiler duty, Q_B", unb ? nd : fmt(r.ps.QB_MW, 2), "MW"],
    ["Feed quality, q", fmt(r.q, 3), ""],
    ["D / B", fmt(r.D_kmol_s, 3) + " / " + fmt(r.B_kmol_s, 3), "kmol/s"],
  ];
  if (r.system === "alpha") {
    cards.push(["Relative volatility, α", fmt(r.alpha_at_zF, 2), "(prescribed)"]);
  } else {
    cards.push(["Relative volatility at z_F, α", fmt(r.alpha_at_zF, 3), ""]);
    cards.push(["Azeotrope, light mole fraction",
      r.azeotrope ? fmt(r.azeotrope.x, 3) + " at " + fmt(r.azeotrope.T_C, 1) + " °C" : "none", ""]);
    cards.push(["Condenser temperature", fmt(r.condenser_T_C, 1), "°C"]);
    cards.push(["Reboiler temperature", fmt(r.reboiler_T_C, 1), "°C"]);
  }
  $("metrics").innerHTML = cards.map((c) =>
    '<div class="metric"><div class="k">' + c[0] + '</div><div class="v">' +
    c[1] + ' <span class="u">' + c[2] + "</span></div></div>").join("");
}
function renderTable(r) {
  const rows = r.ps.stages;
  const cap = 80;
  let html = "";
  rows.slice(0, cap).forEach((s) => {
    const L = (s.L === null || s.L === undefined) ? r.B_kmol_s : s.L;
    html += "<tr><td>" + s.n + "</td><td>" + fmt(s.x, 4) + "</td><td>" +
      fmt(s.y, 4) + "</td><td>" +
      (s.T === null ? "–" : fmt(s.T - 273.15, 1)) + "</td><td>" +
      fmt(L, 4) + "</td><td>" + fmt(s.V, 4) + "</td></tr>";
  });
  if (rows.length > cap) {
    html += '<tr><td colspan="6">… ' + (rows.length - cap) +
      " further stages not tabulated" +
      (r.ps.pinched ? " (stepping pinched)" : "") + ".</td></tr>";
  }
  $("stage-rows").innerHTML = html;
}
function renderBanner(r) {
  const b = $("az-banner");
  if (r.infeasible_azeotrope && r.azeotrope) {
    b.textContent = "Specification infeasible: the distillate mole fraction " +
      fmt(r.xD, 3) + " exceeds the azeotrope composition " +
      fmt(r.azeotrope.x, 3) + " at this pressure. The azeotrope is the ceiling " +
      "for x_D; both constructions pinch there and the stage count is unbounded. " +
      "Minimum reflux and the condenser and reboiler duties are not defined " +
      "for such a specification.";
    b.style.display = "block";
  } else { b.style.display = "none"; }
}
function updateStepLabel() {
  const tot = totalSteps();
  const s = Math.min(stepShown, tot);
  $("stepct").textContent = tot ? ("Stages shown: " + s + " of " + tot) : "";
}
function renderAll() {
  if (!current) return;
  metricCards(current);
  renderBanner(current);
  renderMT(current, stepShown);
  renderPS(current, stepShown);
  renderTXY(current);
  renderTable(current);
  $("Rabs").textContent = fmt(current.R, 3);
  updateStepLabel();
}
function showSpecError(message) {
  /* A failed run renders no metric cards: clear the cards and show
     the failure as a specification-error banner. The next successful
     run re-renders both (renderBanner owns the banner then). */
  const b = $("az-banner");
  b.textContent = "Specification error: " + message;
  b.style.display = "block";
  $("metrics").innerHTML = "";
}
function displayResult(res, spec) {
  current = res;
  displayedSpec = spec;
  stepShown = totalSteps();
  renderAll();
  $("stale-note").style.display = "none";
}
$("step1").addEventListener("click", () => {
  if (!current) return;
  stepShown = (stepShown >= totalSteps()) ? 1
    : Math.min(stepShown + 1, totalSteps());
  renderMT(current, stepShown); renderPS(current, stepShown); updateStepLabel();
});
$("runall").addEventListener("click", () => {
  if (!current) return;
  stepShown = totalSteps();
  renderMT(current, stepShown); renderPS(current, stepShown); updateStepLabel();
});

/* ---------- worker (Pyodide, Python only) ---------- */
const worker = new Worker(URL.createObjectURL(new Blob(
  [$("worker-src").textContent], { type: "text/javascript" })));
worker.onmessage = (ev) => {
  const msg = ev.data;
  if (msg.type === "ready") {
    workerReady = true;
    $("run").disabled = false;
    $("run-status").textContent =
      "Python runtime ready. The displayed run is the precomputed default; press Run to recompute with the current inputs.";
    if (JSON.stringify(readSpec()) !== JSON.stringify(displayedSpec)) runSolve();
  } else if (msg.type === "fatal") {
    $("run-status").textContent = msg.message +
      " The precomputed default run remains displayed; no further calculation is possible in this session.";
  } else if (msg.type === "result") {
    $("prog").style.display = "none";
    $("run").disabled = false;
    $("run-status").textContent = "Run complete (computed live in Python).";
    displayResult(msg.result, msg.specEcho || pendingSpec);
  } else if (msg.type === "error") {
    $("prog").style.display = "none";
    $("run").disabled = false;
    $("run-status").textContent = msg.message;
    showSpecError(msg.message);
  }
};
worker.onerror = (err) => {
  console.error(err);
  $("run-status").textContent =
    "The Python runtime failed to load. The precomputed default run remains displayed.";
};
let pendingSpec = null;
function runSolve() {
  if (!workerReady) return;
  pendingSpec = readSpec();
  solveSeq += 1;
  $("prog").style.display = "block";
  $("run").disabled = true;
  $("run-status").textContent = "Computing in Python…";
  worker.postMessage({ type: "solve", id: solveSeq, spec: pendingSpec });
}
$("run").addEventListener("click", runSolve);

/* ---------- walkthrough figures (lazy) ---------- */
let walkRendered = false;
function renderWalkFigs() {
  if (walkRendered || !$("panel-code").classList.contains("active")) return;
  const sub = $("sub-walkthrough");
  if (!sub.classList.contains("active")) return;
  walkRendered = true;
  document.querySelectorAll(".walkfig").forEach((el) => {
    const tag = document.querySelector(
      'script[type="application/json"][data-for="' + el.id + '"]');
    if (!tag) return;
    const spec = JSON.parse(tag.textContent);
    Plotly.newPlot(el, spec.data, Object.assign(
      { margin: { l: 52, r: 150, t: 8, b: 44 }, legend: LEGEND }, spec.layout), PCTL);
  });
}

/* ---------- init ---------- */
(function init() {
  refreshControlVisibility();
  refreshLabels();
  const pre = JSON.parse($("prestart-data").textContent);
  displayResult(pre.result, pre.spec);
  routeHash();
  scrollspy("#theory-body", "theory-toc");
  scrollspy("#sub-listings", "code-toc");
  scrollspy("#sub-walkthrough", "walk-toc");
  worker.postMessage({ type: "init",
    dataB64: $("src-data").textContent, coreB64: $("src-core").textContent });
})();
