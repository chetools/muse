// Skogestad Column A page logic. All computation happens in the
// Pyodide worker (Python); this file only collects inputs,
// renders results with Plotly, and routes tabs and fragments.
"use strict";

const $ = (id) => document.getElementById(id);
const LEGEND = { x: 1.02, y: 1.0, xanchor: "left", yanchor: "top" };
const MARGIN = { l: 60, r: 190, t: 36, b: 52 };

function fmt(x, d) {
  if (x === null || x === undefined) return "—";
  return Number(x).toFixed(d === undefined ? 4 : d);
}
function fmtE(x) {
  if (x === null || x === undefined) return "—";
  return Number(x).toExponential(2);
}
function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");
}

// ---------- worker RPC ----------
let _wid = 0;
const _pending = new Map();
const worker = new Worker(URL.createObjectURL(
  new Blob([window.WORKER_SRC], { type: "text/javascript" })));
let booted = false;
let bootResolve;
const bootPromise = new Promise((res) => { bootResolve = res; });
worker.onmessage = (ev) => {
  const m = ev.data;
  if (m.type === "ready") {
    booted = true;
    bootResolve(true);
    return;
  }
  if (m.type === "fatal") {
    $("boot-status").textContent =
      "The Python runtime failed to load: " + m.error;
    bootResolve(false);
    return;
  }
  if (m.id !== undefined && _pending.has(m.id)) {
    const { resolve, reject } = _pending.get(m.id);
    _pending.delete(m.id);
    if (m.ok) resolve(m.result); else reject(new Error(m.error));
  }
};
function rpc(type, payload) {
  return new Promise((resolve, reject) => {
    const id = ++_wid;
    _pending.set(id, { resolve, reject });
    worker.postMessage({ id, type, payload });
  });
}
window.columnA = { rpc };

// ---------- progress / status ----------
function busy(on) {
  const p = $("run-progress");
  if (on) { p.hidden = false; $("ready-line").hidden = true; }
  else {
    p.hidden = true;
    const r = $("ready-line");
    r.textContent = "Ready.";
    r.hidden = false;
  }
}
function announce(msg) { $("live-region").textContent = msg; }

// ---------- inputs ----------
const INPUT_IDS = ["in-n", "in-alpha", "in-feed-flow", "in-feed-comp",
  "in-feed-q", "in-reflux", "in-boilup", "in-config", "in-mode",
  "in-kc-drum", "in-kc-reb", "in-step-col", "in-step-size"];
function collect() {
  return {
    n_trays: parseInt($("in-n").value, 10),
    alpha: parseFloat($("in-alpha").value),
    feed_flow: parseFloat($("in-feed-flow").value),
    feed_comp: parseFloat($("in-feed-comp").value),
    feed_q: parseFloat($("in-feed-q").value),
    reflux: parseFloat($("in-reflux").value),
    boilup: parseFloat($("in-boilup").value),
    config: $("in-config").value,
    mode: $("in-mode").value,
    kc_drum: parseFloat($("in-kc-drum").value),
    kc_reb: parseFloat($("in-kc-reb").value),
    step_col: parseInt($("in-step-col").value, 10),
    step_size: parseFloat($("in-step-size").value),
    with_step: true,
  };
}
let displayedParams = null;
let liveShown = false;
function paramsKey(p) {
  return JSON.stringify([p.n_trays, p.alpha, p.feed_flow, p.feed_comp,
    p.feed_q, p.reflux, p.boilup, p.config, p.mode, p.kc_drum,
    p.kc_reb, p.step_col, p.step_size]);
}
function markStale() {
  if (!liveShown) return;
  const now = paramsKey(collect());
  const stale = displayedParams !== null && now !== displayedParams;
  $("app-stale").hidden = !stale;
  $("an-stale").hidden = !stale;
  if (stale) {
    showChannelPlaceholder();
    $("an-channel-note").innerHTML = "";
  }
}

// ---------- tabs and fragments ----------
const TABS = ["theory", "app", "analysis", "code"];
function showTab(name, pushHash) {
  for (const t of TABS) {
    $("panel-" + t).hidden = t !== name;
    document.querySelector(`[data-tab="${t}"]`)
      .classList.toggle("active", t === name);
  }
  if (pushHash) {
    history.replaceState(null, "", "#panel-" + name);
  }
  refitCharts();
}
document.querySelectorAll(".tabbtn").forEach((b) => {
  b.addEventListener("click", () => showTab(b.dataset.tab, true));
});
document.querySelectorAll(".subbtn").forEach((b) => {
  b.addEventListener("click", () => {
    document.querySelectorAll(".subbtn").forEach((x) =>
      x.classList.toggle("active", x === b));
    $("sub-listings").hidden = b.dataset.subtab !== "listings";
    $("sub-walkthrough").hidden = b.dataset.subtab !== "walkthrough";
    if (b.dataset.subtab === "walkthrough") renderWalkFigs();
    refitCharts();
  });
});
function routeFragment() {
  const h = location.hash.replace("#", "");
  if (!h) return;
  const el = document.getElementById(h);
  if (!el) return;
  for (const t of TABS) {
    if ($("panel-" + t).contains(el) || h === "panel-" + t) {
      showTab(t, false);
      if (el.closest("#sub-walkthrough")) {
        document.querySelector('[data-subtab="walkthrough"]').click();
      }
      setTimeout(() => el.scrollIntoView(), 60);
      return;
    }
  }
}
window.addEventListener("hashchange", routeFragment);

// ---------- guidance pop-ups (native popover, with fallback) ----------
if (!("showPopover" in HTMLElement.prototype)) {
  document.querySelectorAll(".guidepop").forEach((pop) => {
    pop.removeAttribute("popover");
    pop.hidden = true;
    pop.classList.remove("open");
  });
  document.querySelectorAll("[popovertarget]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const pop = document.getElementById(btn.getAttribute("popovertarget"));
      if (!pop) return;
      const hideOnly = btn.getAttribute("popovertargetaction") === "hide";
      const willShow = !hideOnly && pop.hidden;
      document.querySelectorAll(".guidepop").forEach((other) => {
        other.hidden = true;
        other.classList.remove("open");
      });
      if (willShow) {
        pop.hidden = false;
        pop.classList.add("open");
      }
    });
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.key !== "Escape") return;
    document.querySelectorAll(".guidepop").forEach((pop) => {
      pop.hidden = true;
      pop.classList.remove("open");
    });
  });
}

// ---------- chart sizing (reveal-triggered) ----------
function refitCharts() {
  requestAnimationFrame(() => {
    document.querySelectorAll(".chart, .walkfig").forEach((d) => {
      if (d.offsetParent !== null && d.data && window.Plotly) {
        Plotly.Plots.resize(d);
      }
    });
  });
}
window.addEventListener("resize", refitCharts);
new MutationObserver(refitCharts).observe(document.body,
  { attributes: true, attributeFilter: ["hidden"], subtree: true });

// ---------- rendering ----------
function colNames(res) {
  return [res.mv_names[0], res.mv_names[1], "F", "xF"];
}
function colUnit(config, j) {
  if (j === 3) return "dimensionless";
  if (config === "RR" && j < 2) return "mole fraction per unit ratio";
  return "mole fraction per (mol/s)";
}
function plot(id, traces, layout) {
  const el = $(id);
  el.data = true;
  Plotly.react(el, traces, Object.assign(
    { margin: MARGIN, legend: LEGEND, showlegend: true }, layout));
}

const CHANNEL_PLACEHOLDER = "No channel overlay yet — it appears " +
  "here when the FOPTD matrix is fitted.";
function showChannelPlaceholder() {
  showChannelText('<p class="note chart-placeholder">' +
    CHANNEL_PLACEHOLDER + "</p>");
}
function showChannelText(html) {
  const el = $("chart-channel");
  if (window.Plotly && el.data) Plotly.purge(el);
  el.data = false;
  el.innerHTML = html;
}

function renderSummary(res, pre) {
  const tag = pre ? " (precomputed)" : "";
  const rows = [
    ["Configuration / level mode", res.config + " / " +
      (res.mode === "perfect" ? "perfect" : "proportional-only")],
    ["Stages NT (feed stage from bottom)",
      res.nt + " (" + res.feed_stage_bottom + ")"],
    ["Distillate composition xD" + tag, fmt(res.xD)],
    ["Bottoms composition xB" + tag, fmt(res.xB)],
    ["Distillate flow D0 (mol/s)", fmt(res.D0, 3)],
    ["Bottoms flow B0 (mol/s)", fmt(res.B0, 3)],
    ["Dominant time constant (s)", fmt(res.poles.tau_dom, 1)],
    ["Steady-state residual (largest |right-hand side|)",
      fmtE(res.residual)],
  ];
  $("app-summary").innerHTML = '<table class="metrics">' +
    rows.map((r) => "<tr><th>" + esc(r[0]) + "</th><td>" +
      esc(r[1]) + "</td></tr>").join("") + "</table>";
  const stages = res.profile_x.map((_, i) => i + 1);
  plot("chart-profile", [{
    x: stages, y: res.profile_x, mode: "lines+markers",
    name: "liquid mole fraction x" + tag,
  }], {
    title: "Steady composition profile" + tag,
    xaxis: { title: "stage (1 = reboiler, NT = condenser)" },
    yaxis: { title: "x (mole fraction)" },
  });
}

function renderStep(res, pre) {
  const tag = pre ? " (precomputed)" : "";
  const s = res.step;
  if (!s) { $("app-step-note").innerHTML = ""; return; }
  const names = colNames(res);
  const traces = [];
  const outs = ["xD", "xB"];
  for (let i = 0; i < 2; i++) {
    traces.push({ x: s.t, y: s.y_lin[i], mode: "lines",
      name: outs[i] + " deviation, linear" + tag });
    traces.push({ x: s.t, y: s.y_nonlin[i], mode: "lines",
      name: outs[i] + " deviation, nonlinear" + tag,
      line: { dash: "dot" } });
  }
  plot("chart-step", traces, {
    title: "Step in " + names[s.col] + " of " + s.size +
      " (input units)" + tag,
    xaxis: { title: "t (s)" },
    yaxis: { title: "composition deviation (mole fraction)" },
  });
  $("app-step-note").innerHTML = '<p class="note">Linear final ' +
    "values: xD " + fmt(s.y_lin[0][s.y_lin[0].length - 1]) +
    ", xB " + fmt(s.y_lin[1][s.y_lin[1].length - 1]) +
    " (mole fraction deviation). Nonlinear final values: xD " +
    fmt(s.y_nonlin[0][s.y_nonlin[0].length - 1]) + ", xB " +
    fmt(s.y_nonlin[1][s.y_nonlin[1].length - 1]) + "." +
    (s.truncated ? " The nonlinear integration stops early: " +
      "the step drives a stage holdup toward zero, where the " +
      "model leaves its valid region (an integrating " +
      "configuration drains or fills the column)." : "") + "</p>";
}

function gainsTable(res) {
  const names = colNames(res);
  let h = '<table class="metrics"><tr><th>Output</th>' +
    names.map((n, j) => "<th>" + esc(n) + "<br>(" +
      esc(colUnit(res.config, j)) + ")</th>").join("") + "</tr>";
  const outs = ["xD", "xB"];
  for (let i = 0; i < 2; i++) {
    h += "<tr><th>" + outs[i] + "</th>" + res.gains[i].map((v) =>
      "<td>" + fmt(v, 5) + "</td>").join("") + "</tr>";
  }
  return h + "</table>";
}

function renderAnalysis(res, pre) {
  const tag = pre ? " (precomputed)" : "";
  const preNote = pre ? '<p class="note">Precomputed results ' +
    "for the default inputs; the first live run replaces " +
    "them.</p>" : "";
  if (res.db) {
    const db = res.db;
    $("an-gains").innerHTML = preNote +
      '<p class="note">The DB configuration has a pole at the ' +
      "origin (Theory, §9): the unbalanced manipulated-variable " +
      "directions and the feed-flow column are integrating and " +
      "have no steady-state gain. The finite gains are:</p>" +
      '<table class="metrics"><tr><th>Output</th>' +
      "<th>Balanced split, D up and B down (mole fraction per " +
      "(mol/s))</th><th>xF (dimensionless)</th></tr>" +
      ["xD", "xB"].map((o, i) => "<tr><th>" + o + "</th><td>" +
        fmt(db.balanced_gains[i], 5) + "</td><td>" +
        fmt(db.xf_gains[i], 5) + "</td></tr>").join("") + "</table>" +
      (db.residuals ? '<p class="note">Residuals of the ' +
        "deflated steady-state system: balanced split " +
        fmtE(db.residuals.balanced) + ", feed composition " +
        fmtE(db.residuals.xf) + " (Theory, §9).</p>" : "") +
      '<h3>Integrating channels: long-time ramp rates' + tag +
      '</h3><table class="metrics"><tr><th>Input</th>' +
      "<th>xD ramp (mole fraction/s per unit input)</th>" +
      "<th>xB ramp (mole fraction/s per unit input)</th></tr>" +
      [0, 1, 2].map((j) => "<tr><th>" +
        esc(colNames(res)[j]) + '</th><td class="integ">' +
        fmtE(db.ramp[String(j)][0]) + "</td><td class=\"integ\">" +
        fmtE(db.ramp[String(j)][1]) + "</td></tr>").join("") +
      "</table>";
    $("an-rga").innerHTML = '<p class="note">No relative gain ' +
      "array exists for DB: the gain matrix does not exist at " +
      "steady state, and the published relative gain is " +
      "infinite (Theory, §8 and §9).</p>";
  } else {
    $("an-gains").innerHTML = preNote + gainsTable(res);
    const lam = res.rga;
    $("an-rga").innerHTML = '<table class="metrics">' +
      "<tr><th></th><th>" + esc(res.mv_names[0]) + "</th><th>" +
      esc(res.mv_names[1]) + "</th></tr>" +
      ["xD", "xB"].map((o, i) => "<tr><th>" + o + "</th>" +
        lam[i].map((v) => "<td>" + fmt(v, 4) + "</td>").join("") +
        "</tr>").join("") + "</table>" +
      '<p class="note">λ11 from the matrix formula: ' +
      fmt(res.rga11, 4) + "; from the shortcut " +
      "1 / (1 − g12 g21 / (g11 g22)): " + fmt(res.shortcut, 4) +
      ". Every row and column sums to 1 (Theory, §8).</p>";
  }
  const p = res.poles;
  $("an-poles").innerHTML = '<p class="note">Number of poles: ' +
    p.count + ". Dominant (slowest) time constant: " +
    fmt(p.tau_dom, 1) + " s. Largest imaginary part over all " +
    "poles: " + fmtE(p.max_imag) + " 1/s." +
    (p.has_origin_pole
      ? " A pole sits at the origin (integrating)."
      : "") + "</p>" +
    '<table class="metrics"><tr><th>Slowest poles (1/s), ' +
    "real parts</th></tr>" + p.slowest.map((v) =>
      "<tr><td>" + fmtE(v) + "</td></tr>").join("") + "</table>";
}

// ---------- FOPTD rendering ----------
let lastRun = null;
function inName(res, j) {
  if (j === 4) return "balanced split";
  return colNames(res)[j];
}
function renderFoptd(fit, res, pre) {
  const outs = ["xD", "xB"];
  let h = '<p class="note">' + (pre
    ? "Precomputed fit for the default inputs; a live fit " +
      "replaces it. " : "") + "Fit horizon: " + fmt(fit.horizon, 0) +
    " s (five times the dominant time constant, " +
    fmt(fit.tau_dom, 1) + " s), 200 samples. Gain K is the exact " +
    "steady-state gain; tau and theta are fitted. Fit errors " +
    "above 10 % are flagged.</p>";
  h += '<table class="metrics"><tr><th>Channel</th><th>K</th>' +
    "<th>tau (s)</th><th>theta (s)</th><th>Fit error (%)</th></tr>";
  for (const r of fit.rows) {
    const label = outs[r.i] + " ← " + inName(res, r.j);
    if (r.integrating) {
      h += "<tr><th>" + esc(label) + '</th><td class="integ" ' +
        'colspan="4">integrating — ramp rate ' +
        fmtE(r.ramp) + " mole fraction/s per unit input</td></tr>";
    } else if (r.negligible) {
      h += "<tr><th>" + esc(label) + "</th><td>" + fmt(r.K, 5) +
        '</td><td colspan="3">negligible (gain only)</td></tr>';
    } else {
      const flag = r.err > 10;
      h += "<tr><th>" + esc(label) + "</th><td>" + fmt(r.K, 5) +
        "</td><td>" + fmt(r.tau, 1) + "</td><td>" +
        fmt(r.theta, 1) + "</td>" +
        (flag ? '<td class="flag">' + fmt(r.err, 2) +
          " (above 10 %)</td>"
              : "<td>" + fmt(r.err, 2) + "</td>") + "</tr>";
    }
  }
  $("an-foptd").innerHTML = h + "</table>";
}

function renderChannel(ch, res) {
  const outs = ["xD", "xB"];
  const c = ch.channel;
  const label = outs[c.i] + " ← " + inName(res, c.j);
  if (c.integrating) {
    const html = '<p class="note">Channel ' +
      esc(label) + " is integrating: no FOPTD fit. Long-time " +
      "ramp rate " + fmtE(c.ramp) +
      " mole fraction/s per unit input.</p>";
    $("an-channel-note").innerHTML = html;
    showChannelText(html);
    return;
  }
  if (c.negligible) {
    const html = '<p class="note">Channel ' +
      esc(label) + " is negligible (K = " + fmt(c.K, 5) +
      "); no fit is identifiable.</p>";
    $("an-channel-note").innerHTML = html;
    showChannelText(html);
    return;
  }
  const el = $("chart-channel");
  if (window.Plotly && el.data) Plotly.purge(el);
  el.data = false;
  el.innerHTML = "";
  plot("chart-channel", [
    { x: c.t, y: c.y_high, mode: "lines",
      name: "high-order step response" },
    { x: c.t, y: c.y_model, mode: "lines",
      name: "FOPTD step response", line: { dash: "dot" } },
  ], {
    title: "Channel " + label + " (unit step)",
    xaxis: { title: "t (s)" },
    yaxis: { title: "output deviation (mole fraction)" },
  });
  $("an-channel-note").innerHTML = '<p class="note">K = ' +
    fmt(c.K, 5) + ", tau = " + fmt(c.tau, 1) + " s, theta = " +
    fmt(c.theta, 1) + " s, fit error = " + fmt(c.err, 2) + " %." +
    (c.err > 10 ? " The fit error is above 10 %: the channel " +
      "shape is not FOPTD-like (Theory, §10)." : "") + "</p>";
}

// ---------- actions ----------
async function doRun() {
  const payload = collect();
  busy(true);
  $("run-err").hidden = true;
  try {
    const res = await rpc("run", payload);
    lastRun = res;
    displayedParams = paramsKey(payload);
    liveShown = true;
    renderSummary(res, false);
    renderStep(res, false);
    renderAnalysis(res, false);
    $("an-foptd").innerHTML = '<p class="note">Not fitted for ' +
      "the current inputs. Use the Fit FOPTD matrix button.</p>";
    showChannelPlaceholder();
    $("an-channel-note").innerHTML = "";
    $("run-note").textContent = "Run complete.";
    announce("Run complete. xD " + fmt(res.xD) + ", xB " +
      fmt(res.xB) + ".");
    markStale();
  } catch (e) {
    $("run-err").textContent = e.message;
    $("run-err").hidden = false;
    announce("Run failed: " + e.message);
  } finally {
    busy(false);
  }
}

async function doFit() {
  const payload = collect();
  busy(true);
  $("fit-err").hidden = true;
  try {
    const fit = await rpc("foptd",
      Object.assign(payload, { fit_mode: "matrix" }));
    renderFoptd(fit, lastRun || { config: payload.config,
      mv_names: ["MV1", "MV2"] });
    $("fit-note").textContent = "FOPTD matrix fitted.";
    announce("FOPTD matrix fitted.");
    await doChannel();
  } catch (e) {
    $("fit-err").textContent = e.message;
    $("fit-err").hidden = false;
  } finally {
    busy(false);
  }
}

async function doChannel() {
  const payload = collect();
  busy(true);
  $("ch-err").hidden = true;
  try {
    const ch = await rpc("foptd", Object.assign(payload, {
      fit_mode: "channel",
      channel: [parseInt($("ch-out").value, 10),
                parseInt($("ch-in").value, 10)],
    }));
    renderChannel(ch, lastRun || { config: payload.config,
      mv_names: ["MV1", "MV2"] });
    announce("Channel overlay updated.");
  } catch (e) {
    if (String(e.message).includes("channel")) {
      $("ch-err").textContent =
        "The balanced-split channel exists only for DB.";
      showChannelText('<p class="note chart-placeholder">' +
        "The balanced-split channel exists only for DB.</p>");
    } else {
      $("ch-err").textContent = e.message;
    }
    $("ch-err").hidden = false;
  } finally {
    busy(false);
  }
}

// ---------- walkthrough figures (lazy) ----------
let walkRendered = false;
function renderWalkFigs() {
  if (walkRendered) return;
  walkRendered = true;
  document.querySelectorAll("script[data-for]").forEach((s) => {
    const fig = JSON.parse(s.textContent);
    const el = $(s.dataset.for);
    el.data = true;
    Plotly.newPlot(el, fig.data, Object.assign(
      { margin: MARGIN, legend: LEGEND, showlegend: true },
      fig.layout));
  });
}

// ---------- scrollspy ----------
function scrollspy() {
  const obs = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      const id = e.target.id;
      document.querySelectorAll("aside.toc nav a").forEach((a) => {
        if (a.getAttribute("href") === "#" + id) {
          a.setAttribute("aria-current", "true");
        } else if (a.getAttribute("aria-current")) {
          a.removeAttribute("aria-current");
        }
      });
    }
  }, { rootMargin: "-20% 0px -70% 0px" });
  document.querySelectorAll(
    "#theory-body h2, #theory-body h3, .walkcell, " +
    "#sub-listings h2").forEach((el) => { if (el.id) obs.observe(el); });
}

// ---------- wiring, prestart, boot ----------
let debounce = null;
function scheduleRun() {
  markStale();
  if (!booted) return;
  clearTimeout(debounce);
  debounce = setTimeout(doRun, 350);
}
INPUT_IDS.forEach((id) => {
  $(id).addEventListener("input", scheduleRun);
  $(id).addEventListener("change", scheduleRun);
});
$("in-config").addEventListener("change", () => {
  // keep step-column labels generic; names appear in results
});
$("run-btn").addEventListener("click", doRun);
$("fit-btn").addEventListener("click", doFit);
$("ch-btn").addEventListener("click", doChannel);

(function prestart() {
  try {
    const pre = JSON.parse($("prestart-data").textContent);
    if (pre && pre.run) {
      lastRun = pre.run;
      renderSummary(pre.run, true);
      renderStep(pre.run, true);
      renderAnalysis(pre.run, true);
      $("run-note").textContent =
        "Precomputed results for the default inputs are shown; " +
        "the first live run replaces them.";
    }
    if (pre && pre.foptd) {
      renderFoptd(pre.foptd, pre.run, true);
    }
  } catch (e) { /* prestart is an enhancement */ }
})();

bootPromise.then((ok) => {
  if (!ok) return;
  $("boot-status").textContent = "Python runtime ready.";
  $("run-btn").disabled = false;
  $("fit-btn").disabled = false;
  $("ch-btn").disabled = false;
  doRun();
});
routeFragment();
scrollspy();
