// Linde ASU page application logic. All calculations are performed in
// Python (Pyodide worker); this script only presents results.
const BOOT_LINES = @@BOOT_LINES@@;
const MODEL_B64 = @@MODEL_B64@@;
const TABS = ["app", "process", "theory", "economics", "safety", "code", "references"];

function activateFromHash() {
  let h = (location.hash || "#app").slice(1);
  let tab = TABS.includes(h) ? h : (TABS.find(t => h.startsWith(t + "-")) || "app");
  document.querySelectorAll("section.tab").forEach(s => s.classList.toggle("active", s.id === "tab-" + tab));
  document.querySelectorAll("#tabnav a").forEach(a => a.classList.toggle("active", a.dataset.tab === tab));
  const el = document.getElementById(h);
  if (el && !TABS.includes(h)) { setTimeout(() => el.scrollIntoView(), 30); }
  if (tab === "code") { renderWalkthroughFigures(); }
}
window.addEventListener("hashchange", activateFromHash);

const prestart = JSON.parse(document.getElementById("prestart-data").textContent);
let displayedInputs = JSON.stringify(prestart.inputs);
let worker = null;
let workerReady = false;

function fmt(x, d) { return (x === null || x === undefined || Number.isNaN(x)) ? "—" : Number(x).toFixed(d); }

function renderResult(r, label) {
  document.getElementById("run-label").textContent = label;
  const cards = [
    ["Oxygen product (t/d)", fmt(r.gox_tpd, 1)],
    ["Contained oxygen (t/d)", fmt(r.o2_in_gox_tpd, 1)],
    ["Nitrogen product (t/d)", fmt(r.gan_tpd, 1)],
    ["Crude argon product (t/d)", fmt(r.crude_tpd, 2)],
    ["Total power (kW)", fmt(r.p_total_kw, 0)],
    ["Specific power (kWh/t)", fmt(r.spec_kwh_per_t, 1)],
    ["Capital cost (million USD)", fmt(r.capex_usd / 1e6, 1)],
    ["Unit oxygen cost (USD/t)", fmt(r.unit_cost_usd_t, 1)]
  ];
  document.getElementById("metric-cards").innerHTML = cards.map(c =>
    '<div class="card"><div class="k">' + c[0] + '</div><div class="v">' + c[1] + "</div></div>").join("");
  const names = [["feed", "Feed air"], ["gox", "Oxygen product"], ["gan", "Nitrogen product"], ["crude", "Crude argon"], ["waste", "Waste nitrogen"]];
  let html = '<table class="data"><tr><th>Stream</th><th>Nitrogen (kmol/h)</th><th>Oxygen (kmol/h)</th><th>Argon (kmol/h)</th><th>Total (kmol/h)</th></tr>';
  for (const [k, nm] of names) {
    const c = r.components[k];
    html += "<tr><td>" + nm + "</td><td>" + fmt(c[0], 1) + "</td><td>" + fmt(c[1], 1) + "</td><td>" + fmt(c[2], 1) + "</td><td>" + fmt(r.totals[k], 1) + "</td></tr>";
  }
  document.getElementById("component-table").innerHTML = html + "</table>";
  const xs = ["Feed", "Oxygen product", "Nitrogen product", "Crude argon", "Waste"];
  const keys = ["feed", "gox", "gan", "crude", "waste"];
  const traces = ["Nitrogen", "Oxygen", "Argon"].map((nm, i) => ({
    type: "bar", name: nm, x: xs, y: keys.map(k => r.components[k][i])
  }));
  Plotly.react("chart-balance", traces, prestart.figs.balance.layout, { responsive: true });
  if (r.sweep) {
    Plotly.react("chart-sweep", [{ type: "scatter", mode: "lines+markers", name: "Unit cost", x: r.sweep.caps, y: r.sweep.units }],
      prestart.figs.sweep.layout, { responsive: true });
  }
  const err = document.getElementById("app-error");
  if (r.feasible === false) {
    err.style.display = "block";
    err.textContent = "The specified recoveries and purities are jointly infeasible: a waste component flow rate is negative. The values are shown unclamped.";
  } else { err.style.display = "none"; }
}

function collectInputs() {
  const o = {};
  document.querySelectorAll("[data-input]").forEach(inp => { o[inp.dataset.input] = parseFloat(inp.value); });
  return o;
}

function checkStale() {
  document.getElementById("stale-note").style.display =
    (JSON.stringify(collectInputs()) !== displayedInputs) ? "block" : "none";
}

function bootWorker() {
  const status = document.getElementById("boot-status");
  const prog = document.getElementById("boot-progress");
  const workerLines = [
    "importScripts('https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js');",
    "let handleFn = null;",
    "async function boot(){",
    "  const pyodide = await loadPyodide();",
    "  postMessage({type:'stage', stage:'numpy'});",
    "  await pyodide.loadPackage(['numpy']);",
    "  pyodide.globals.set('MODEL_B64', MODEL_B64);",
    "  pyodide.runPython(BOOT_PY);",
    "  handleFn = pyodide.globals.get('handle');",
    "  postMessage({type:'ready'});",
    "}",
    "boot().catch(e => postMessage({type:'booterror', message: String(e)}));",
    "onmessage = (ev) => {",
    "  if (!handleFn) { postMessage({type:'result', payload: JSON.stringify({error:'No live session yet - the Python runtime is still loading. Wait for the ready message, then run again.'})}); return; }",
    "  postMessage({type:'result', payload: handleFn(JSON.stringify(ev.data.inputs))});",
    "};"
  ];
  const src = "const MODEL_B64 = " + JSON.stringify(MODEL_B64) + ";\n" +
    "const BOOT_PY = " + JSON.stringify(BOOT_LINES.join("\n")) + ";\n" + workerLines.join("\n");
  worker = new Worker(URL.createObjectURL(new Blob([src], { type: "text/javascript" })));
  worker.onmessage = (ev) => {
    const m = ev.data;
    if (m.type === "stage") { prog.value = 55; status.textContent = "Python runtime: loading packages."; }
    if (m.type === "ready") {
      workerReady = true; prog.value = 100;
      status.textContent = "Python runtime: ready. Live runs compute in the browser (Pyodide).";
      document.getElementById("run-btn").disabled = false;
    }
    if (m.type === "booterror") {
      prog.value = 0;
      status.textContent = "Python runtime failed to load (" + m.message + "). The precomputed run remains displayed; live runs are unavailable.";
    }
    if (m.type === "result") {
      prog.value = 100;
      const btn = document.getElementById("run-btn");
      btn.disabled = false;
      let r = null;
      try { r = JSON.parse(m.payload); } catch (e) { r = { error: "The calculation returned an unreadable result." }; }
      if (r.error) {
        const err = document.getElementById("app-error");
        err.style.display = "block"; err.textContent = r.error;
      } else {
        displayedInputs = JSON.stringify(collectInputs());
        checkStale();
        renderResult(r, "Live run, computed in the browser (Pyodide).");
      }
    }
  };
  worker.onerror = () => {
    status.textContent = "Python runtime failed to load. The precomputed run remains displayed; live runs are unavailable.";
  };
}

let walkthroughRendered = false;
function renderWalkthroughFigures() {
  if (walkthroughRendered) return;
  walkthroughRendered = true;
  document.querySelectorAll("[data-fig]").forEach(div => {
    const fig = walkthroughFigs[div.dataset.fig];
    if (fig) { Plotly.newPlot(div, fig.data, fig.layout, { responsive: true }); }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  renderResult(prestart.result, "Precomputed run, computed when this page was built (default inputs).");
  Plotly.newPlot("chart-balance", prestart.figs.balance.data, prestart.figs.balance.layout, { responsive: true });
  Plotly.newPlot("chart-sweep", prestart.figs.sweep.data, prestart.figs.sweep.layout, { responsive: true });
  document.querySelectorAll("[data-input]").forEach(inp => inp.addEventListener("input", checkStale));
  document.getElementById("run-btn").addEventListener("click", () => {
    if (!workerReady) return;
    const prog = document.getElementById("boot-progress");
    prog.value = 35;
    document.getElementById("run-btn").disabled = true;
    document.getElementById("app-error").style.display = "none";
    worker.postMessage({ inputs: collectInputs() });
  });
  // Scroll-spy for tables of contents within the active tab.
  const spy = new IntersectionObserver(entries => {
    entries.forEach(en => {
      if (en.isIntersecting) {
        document.querySelectorAll('.toc a').forEach(a =>
          a.classList.toggle("current", a.getAttribute("href") === "#" + en.target.id));
      }
    });
  }, { rootMargin: "-10% 0px -70% 0px" });
  document.querySelectorAll("section.tab h2[id], section.tab h3[id]").forEach(h => spy.observe(h));
  activateFromHash();
  bootWorker();
});
