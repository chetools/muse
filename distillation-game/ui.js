"use strict";
// ---------- Formatting ----------
const f1 = (v) => v.toFixed(1);
const f2 = (v) => v.toFixed(2);
const pct = (v) => (v * 100).toFixed(1) + "%";
const kW = (v) => (v / 1000).toFixed(0) + " kW";

// ---------- Event log ----------
let simClock = 0;
function logMsg(msg) {
  const d = document.createElement("div");
  d.textContent = `[${Math.round(simClock)} s] ${msg}`;
  const log = $("log");
  log.prepend(d);
  while (log.children.length > 60) log.lastChild.remove();
}
function logEvent(idx, value) {
  const key = Object.keys(VALVES).find((k) => VALVES[k].idx === idx);
  if (!key) return;
  const v = VALVES[key];
  const shown = v.kind === "kpa" ? `${value.toFixed(0)} kPa`
    : v.kind === "frac" ? pct(value) : `${value.toFixed(1)}%`;
  logMsg(`${v.name} set to ${shown} (You)`);
}

// ---------- Valve panel ----------
function valveDisplay(key) {
  const o = getOpenings();
  const v = VALVES[key];
  const raw = o[v.idx];
  return v.kind === "kpa" ? raw : v.kind === "frac" ? raw * 100 : raw;
}
function selectValve(key) {
  selected = key;
  document.querySelectorAll(".valve").forEach((g) =>
    g.classList.toggle("selected", g.dataset.valve === key));
  const v = VALVES[key];
  $("vName").textContent = v.name;
  $("vDesc").textContent = v.desc;
  const s = $("vSlider");
  if (v.kind === "kpa") { s.min = 150; s.max = 900; s.step = 5; }
  else { s.min = 0; s.max = 100; s.step = 0.5; }
  s.disabled = false;
  for (const b of ["vMinus", "vPlus", "vFull", "vShut"]) $(b).disabled = false;
  syncValvePanel();
}
let apStatus = null;   // Float64Array(12) from dg_ap_status
let prevHelp = 0;
const HELP_NAMES = ["drum level", "reboiler level", "column pressure",
  "distillate composition", "bottoms composition"];
function pollApStatus() {
  const p = W.dg_alloc(12);
  W.dg_ap_status(sim, p);
  apStatus = Array.from(new Float64Array(W.memory.buffer, p, 12));
  W.dg_free(p, 12);
  for (const [key, v] of Object.entries(VALVES)) {
    const g = document.querySelector(`.valve[data-valve="${key}"]`);
    if (!g) continue;
    const mode = apStatus[2 + v.idx];
    g.classList.toggle("auto", mode === 2);
    g.classList.toggle("claimed", mode === 1);
  }
  const help = apStatus[1];
  if (help > 0 && prevHelp === 0) {
    logMsg(`Autopilot is calling for help: ${HELP_NAMES[help - 1]} out of band with its valve saturated.`);
  }
  prevHelp = help;
}
function syncValvePanel() {
  if (!selected) return;
  const v = VALVES[selected];
  const disp = valveDisplay(selected);
  $("vSlider").value = disp;
  lastSliderVal = disp;
  $("vOpenVal").textContent = v.kind === "kpa" ? `${disp.toFixed(0)} kPa` : `${disp.toFixed(1)}%`;
  const mode = apStatus ? apStatus[2 + v.idx] : 0;
  $("vSeat").textContent =
    mode === 2 ? "This seat is on autopilot (teal outline). Moving the valve claims the seat." :
    mode === 1 ? "You claimed this seat from the autopilot." : "";
  $("vHandBack").style.display = mode === 1 ? "" : "none";
}
$("vHandBack").addEventListener("click", () => {
  if (!selected) return;
  W.dg_release_seat(sim, VALVES[selected].idx);
  logMsg(`${VALVES[selected].name} handed back to the autopilot.`);
  pollApStatus();
  syncValvePanel();
});
function applyValve(dispValue) {
  if (!selected) return;
  const v = VALVES[selected];
  const raw = v.kind === "frac" ? dispValue / 100 : dispValue;
  setOpening(v.idx, raw);
  syncValvePanel();
}
let lastSliderVal = null;
let shiftDown = false;
window.addEventListener("keydown", (e) => { if (e.key === "Shift") shiftDown = true; });
window.addEventListener("keyup", (e) => { if (e.key === "Shift") shiftDown = false; });
window.addEventListener("blur", () => { shiftDown = false; });
let dragV = null;
document.addEventListener("pointerdown", (e) => {
  if (e.button !== 0) return;
  const g = e.target.closest ? e.target.closest("[data-valve]") : null;
  if (!g || !VALVES[g.dataset.valve]) return;
  const key = g.dataset.valve;
  selectValve(key);
  const s = $("vSlider");
  dragV = { key, x0: e.clientX, y0: e.clientY, v0: valveDisplay(key),
            min: parseFloat(s.min), max: parseFloat(s.max), moved: false };
  window.__dragQuiet = true;
});
document.addEventListener("pointermove", (e) => {
  if (!dragV) return;
  const dx = e.clientX - dragV.x0, dy = e.clientY - dragV.y0;
  if (Math.abs(dx) + Math.abs(dy) > 2) dragV.moved = true;
  if (!dragV.moved) return;
  const range = dragV.max - dragV.min;
  const sens = range / ((shiftDown || e.shiftKey) ? 2000 : 400);
  const val = Math.min(dragV.max, Math.max(dragV.min,
    dragV.v0 + (dx - dy) * sens));
  applyValve(val);
});
document.addEventListener("pointerup", () => {
  if (!dragV) return;
  if (dragV.moved) {
    const v = VALVES[dragV.key];
    logEvent(v.idx, getOpenings()[v.idx]);
  }
  dragV = null;
  window.__dragQuiet = false;
});
$("vSlider").addEventListener("input", (e) => {
  let val = parseFloat(e.target.value);
  if (shiftDown && lastSliderVal !== null && selected) {
    val = lastSliderVal + (val - lastSliderVal) * 0.2;
    e.target.value = val;
  }
  lastSliderVal = val;
  applyValve(val);
});
$("vMinus").addEventListener("click", () => { if (selected) applyValve(Math.max(parseFloat($("vSlider").min), valveDisplay(selected) - 5)); });
$("vPlus").addEventListener("click", () => { if (selected) applyValve(Math.min(parseFloat($("vSlider").max), valveDisplay(selected) + 5)); });
$("vFull").addEventListener("click", () => { if (selected) applyValve(parseFloat($("vSlider").max)); });
$("vShut").addEventListener("click", () => { if (selected) applyValve(parseFloat($("vSlider").min)); });

// ---------- Readings ----------
function segInit(id) {
  const bar = $(id);
  bar.innerHTML = "";
  return COMP_COLORS.map((c) => {
    const d = document.createElement("div");
    d.style.background = c;
    bar.appendChild(d);
    return d;
  });
}
const segDist = segInit("segDist"), segBot = segInit("segBot");
function segSet(segs, x) {
  segs.forEach((d, i) => { d.style.width = pct(x[i]); });
  segs.forEach((d, i) => { d.title = `${["pentane", "hexane", "heptane"][i]} ${pct(x[i])}`; });
}
let prevAlarm = { hp: false, relief: false, flash: false, ruptured: false };
let riserPhase = 0;

let bubV = { R: 9, S: 9 };
function refreshOutputs() {
  if (!nominalOpenings) nominalOpenings = getOpenings();
  if (!feedInputsSynced) { feedInputsSynced = true; syncFeedInputs(); }
  const o = outputs();
  bubV = { R: o[12], S: o[11] };
  sampleHistory(o);
  const P = { col: o[0], cond: o[1], drum: o[2], chest: o[3] };
  // Pressure bar.
  dyn.pBar.setAttribute("width", Math.max(0, (P.col - 20) / 620 * 350));
  dyn.pBar.setAttribute("fill", P.col >= 360 ? "#b00020" : P.col >= 300 ? "#b3541e" : "#16697a");
  dyn.pVal.textContent = `${f1(P.col)} kPa`;
  // Trays: composition segments and temperature strip.
  for (let j = 1; j <= 12; j++) {
    const x = [o[52 + j * 3], o[52 + j * 3 + 1], o[52 + j * 3 + 2]];
    let sx = 98;
    dyn.traySegs[j].forEach((r, c) => {
      r.setAttribute("x", sx);
      r.setAttribute("width", Math.max(0, x[c] * 104));
      sx += x[c] * 104;
    });
    const Lj = j > 6 ? o[13] : o[14];
    const target = Math.min(20, 6 + 7 * Math.pow(Math.max(0, Lj) / (j > 6 ? 5 : 15), 2 / 3));
    if (trayDepthVis[j] === undefined) trayDepthVis[j] = target;
    const dtTray = Math.max(0, simClock - lastTrayClock);
    trayDepthVis[j] += (target - trayDepthVis[j]) * (1 - Math.exp(-dtTray / 20));
    const depth = trayDepthVis[j];
    const plateY = 84 + (13 - j) * 32;
    dyn.traySegs[j].forEach((r) => {
      r.setAttribute("y", plateY - depth);
      r.setAttribute("height", depth);
    });
    dyn.traySurf[j].setAttribute("y1", plateY - depth);
    dyn.traySurf[j].setAttribute("y2", plateY - depth);
    const ratej = Math.max(0, (j > 6 ? o[12] : o[11])) / 9;
    const foamH = Math.min(9, Math.max(0, (ratej - 1.25) * 22));
    dyn.trayFoam[j].setAttribute("y", plateY - depth - foamH);
    dyn.trayFoam[j].setAttribute("height", foamH);
    trayVis[j] = { depth, foamH, rate: ratej, plateY };
    dyn.trayTempTxt[j].textContent = `${Math.round(o[91 + j])} K`;
  }
  dyn.topT.textContent = `top ${f1(o[9])} K`;
  dyn.rebT.textContent = `${f1(o[10])} K, level ${pct(o[33])}`;
  const rebY = 84 + 32 * 12 + 14;
  dyn.rebLiq.setAttribute("y", rebY + 46 - o[33] * 44);
  dyn.rebLiq.setAttribute("height", o[33] * 44);
  dyn.feedLbl.textContent = `F = ${f2(o[37])} mol/s`;
  // Drum and condenser levels.
  dyn.drumLiq.setAttribute("y", 88 + 50 - o[32] * 48);
  dyn.drumLiq.setAttribute("height", o[32] * 48);
  dyn.drumLbl.textContent = `P ${f1(o[2])} kPa`;
  dyn.drumLbl2.textContent = `level ${(o[32] * 100).toFixed(1)}%`;
  dyn.drumLbl3.textContent = `${f1(o[4])} K`;
  dyn.condFlood.setAttribute("y", 300 + 54 - o[23] * 52);
  dyn.condFlood.setAttribute("height", o[23] * 52);
  dyn.condLbl.textContent = `flooded ${pct(o[23])}`;
  dyn.riserLbl.textContent = `riser ${f2(o[20])} mol/s`;
  dyn.marginLbl.textContent = `margin ${f2(o[21])} K`;
  dyn.riser.setAttribute("stroke", o[21] < 0 ? "#b3541e" : "#56b4e9");
  dyn.reliefLbl.textContent = o[27] > 0 ? `LIFTING ${f2(o[27])} mol/s` : "";
  dyn.distLbl.textContent = `${f2(o[15])} mol/s`;
  dyn.botLbl.textContent = `${f2(o[16])} mol/s`;
  dyn.chestLbl.textContent = `${f1(P.chest)} kPa`;
  dyn.tankLbl.textContent = `${f1(o[5])} K`;
  dyn.qCondArrow.textContent = "condensing at";
  dyn.condLbl2.textContent = `${f1(o[7])} K`;
  dyn.qRebArrow.textContent = `reboiler duty ${kW(o[24])}`;
  // Valve labels.
  const ops = getOpenings();
  for (const [key, v] of Object.entries(VALVES)) {
    if (!dyn["v_" + key]) continue;
    dyn["v_" + key].textContent = v.kind === "kpa" ? `${ops[v.idx].toFixed(0)} kPa`
      : v.kind === "frac" ? pct(ops[v.idx]) : `${ops[v.idx].toFixed(0)}%`;
  }
  // Readout table.
  const xd = [o[40], o[41], o[42]], xb = [o[49], o[50], o[51]];
  const specD = xd[0] >= 0.95, specB = xb[0] <= 0.05;
  const fiR = feedInfo();
  $("readouts").innerHTML = `
    <span class="sect">Pressures</span>
    <span>Column</span><span class="v">${f1(P.col)} kPa</span>
    <span>Condenser</span><span class="v">${f1(P.cond)} kPa</span>
    <span>Drum</span><span class="v">${f1(P.drum)} kPa</span>
    <span>Condenser minus drum</span><span class="v">${f1(P.cond - P.drum)} kPa</span>
    <span>Steam chest</span><span class="v">${f1(P.chest)} kPa</span>
    <span class="sect">Levels and flooding</span>
    <span>Drum level</span><span class="v">${pct(o[32])}</span>
    <span>Reboiler level</span><span class="v">${pct(o[33])}</span>
    <span>Condenser flooded</span><span class="v">${pct(o[23])}</span>
    <span>Subcooling margin</span><span class="v">${f2(o[21])} K</span>
    <span class="sect">Flows, mol/s</span>
    <span>Vapour into condenser</span><span class="v">${f2(o[17])}</span>
    <span>Bypass vapour</span><span class="v">${f2(o[18])}</span>
    <span>Condensation rate</span><span class="v">${f2(o[19])}</span>
    <span>Condensate to drum</span><span class="v">${f2(o[20])}</span>
    <span>Reflux</span><span class="v">${f2(o[13])}</span>
    <span>Distillate</span><span class="v">${f2(o[15])}</span>
    <span>Bottoms</span><span class="v">${f2(o[16])}</span>
    <span>Boilup</span><span class="v">${f2(o[11])}</span>
    <span class="sect">Duties and temperatures</span>
    <span>Condenser duty</span><span class="v">${kW(o[25])}</span>
    <span>Reboiler duty</span><span class="v">${kW(o[24])}</span>
    <span>Cooling tank</span><span class="v">${f1(o[5])} K</span>
    <span>Water leaving condenser</span><span class="v">${f1(o[6])} K</span>
    <span class="sect">Feed</span>
    <span>Flow</span><span class="v">${f2(fiR.F)} mol/s</span>
    <span>Pentane</span><span class="v">${pct(fiR.z[0])}</span>
    <span>Hexane</span><span class="v">${pct(fiR.z[1])}</span>
    <span>Heptane</span><span class="v">${pct(fiR.z[2])}</span>
    <span>Temperature</span><span class="v">${f1(fiR.T)} K</span>
    <span>Pressure</span><span class="v">${f1(fiR.P)} kPa</span>
    <span class="sect">Products</span>
    <span>Distillate pentane</span><span class="v ${specD ? "spec-ok" : "spec-bad"}">${pct(xd[0])}</span>
    <span>Bottoms pentane</span><span class="v ${specB ? "spec-ok" : "spec-bad"}">${pct(xb[0])}</span>`;
  segSet(segDist, xd);
  segSet(segBot, xb);
  const fiNow = fiR;
  for (let c = 0; c < 3; c++) dyn.feedZ[c].textContent = `${COMP_NAMES[c]} ${Math.round(fiNow.z[c] * 100)}%`;
  dyn.feedTP.textContent = `${fiNow.T.toFixed(0)} K · ${fiNow.P.toFixed(0)} kPa`;
  lastTrayClock = simClock;
  // Alarms.
  const alarm = { hp: o[36] > 0, relief: o[35] > 0, flash: o[21] < 0, ruptured: o[34] > 0 };
  const bar = $("alarmBar");
  bar.className = "";
  bar.style.display = "none";
  if (alarm.relief) {
    bar.className = "relief"; bar.style.display = "block";
    bar.textContent = "RELIEF VALVE LIFTING — vapour is being lost to the flare and the score penalty is heavy.";
  } else if (alarm.hp) {
    bar.className = "hp"; bar.style.display = "block";
    bar.textContent = "HIGH PRESSURE ALARM — column pressure is above 360 kPa. The relief valve lifts at 400 kPa.";
  } else if (alarm.flash) {
    bar.className = "flash"; bar.style.display = "block";
    bar.textContent = "RISER FLASHING — the condensate is not subcooled enough for the lift to the drum; drainage is degraded.";
  }
  if (alarm.relief && !prevAlarm.relief) logMsg("Relief valve lifted.");
  if (alarm.hp && !prevAlarm.hp) logMsg("High pressure alarm (360 kPa).");
  if (alarm.flash && !prevAlarm.flash) logMsg("Riser flashing began (subcooling margin below zero).");
  if (alarm.ruptured && !prevAlarm.ruptured) {
    logMsg("VESSEL RUPTURE.");
    $("overBar").style.display = "block";
    playing = false;
    $("btnPlay").textContent = "Play";
  }
  prevAlarm = alarm;
  pollApStatus();
  if (selected) syncValvePanel();
  drawAllTiles();
}

// ---------- Disturbances ----------
function feedInfo() {
  const p = W.dg_alloc(6);
  W.dg_feed_info(sim, p);
  const a = Array.from(new Float64Array(W.memory.buffer, p, 6));
  W.dg_free(p, 6);
  return { F: a[0], T: a[1], P: a[2], z: [a[3], a[4], a[5]] };
}
function setFeed(F, z, T, P) {
  new Float64Array(W.memory.buffer, zPtr, 3).set(z);
  W.dg_set_feed(sim, F, zPtr, T, P);
}
function feedBubbleT(z, P) {
  new Float64Array(W.memory.buffer, zPtr, 3).set(z);
  return W.dg_feed_bubble(sim, zPtr, P);
}
const NOMINAL_FEED = { F: 10, z: [0.4, 0.3, 0.3] };
let nominalFeedState = null;
let nominalOpenings = null;
let feedInputsSynced = false;
document.querySelectorAll(".dist").forEach((b) => {
  b.addEventListener("click", () => {
    const fi = feedInfo();
    if (!nominalFeedState) nominalFeedState = fi;
    if (!nominalOpenings) nominalOpenings = getOpenings();
    const d = b.dataset.d;
    if (d === "feedUp") { setFeed(fi.F * 1.2, fi.z, fi.T, fi.P); logMsg("Disturbance: feed flow +20%."); }
    if (d === "feedDown") { setFeed(fi.F / 1.2, fi.z, fi.T, fi.P); logMsg("Disturbance: feed flow −20%."); }
    if (d === "feedLight") { const z = [0.55, 0.25, 0.20]; setFeed(fi.F, z, feedBubbleT(z, fi.P), fi.P); logMsg("Disturbance: feed richer in pentane (arrives as a saturated liquid)."); }
    if (d === "feedHeavy") { const z = [0.25, 0.35, 0.40]; setFeed(fi.F, z, feedBubbleT(z, fi.P), fi.P); logMsg("Disturbance: feed leaner in pentane (arrives as a saturated liquid)."); }
    if (d === "warmWater") { W.dg_set_supply(sim, 308.15); logMsg("Disturbance: cooling supply warmed to 35 °C."); }
    if (d === "restore") {
      const n = nominalFeedState || { ...NOMINAL_FEED, T: fi.T, P: fi.P };
      setFeed(n.F, n.z, n.T, n.P);
      W.dg_set_supply(sim, 298.0);
      if (nominalOpenings) {
        nominalOpenings.forEach((v, i) => setOpening(i, v));
        if (selected) syncValvePanel();
      }
      logMsg("Feed, cooling supply and valve openings restored to nominal; flow rates return to the nominal point.");
    }
    syncFeedInputs(d === "restore");
    refreshOutputs();
  });
});

function syncFeedInputs(force) {
  if (!W || !sim) return;
  const fi = feedInfo();
  const vals = {
    inFeedF: fi.F.toFixed(2),
    inFeedZ0: Math.round(fi.z[0] * 100),
    inFeedZ1: Math.round(fi.z[1] * 100),
    inFeedZ2: Math.round(fi.z[2] * 100),
    inFeedT: fi.T.toFixed(1),
    inFeedP: fi.P.toFixed(0),
    inFeedQ: Math.round((1 - outputs()[31]) * 100),
  };
  for (const [id, v] of Object.entries(vals)) {
    const el = $(id);
    if (el && (force || document.activeElement !== el)) el.value = v;
  }
}
$("btnFeedApply").addEventListener("click", () => {
  const F = parseFloat($("inFeedF").value);
  const zIn = [0, 1, 2].map((i) => parseFloat($("inFeedZ" + i).value));
  const T = parseFloat($("inFeedT").value);
  const P = parseFloat($("inFeedP").value);
  const mode = $("selFeedMode").value;
  if ([F, P, ...zIn].some((v) => !isFinite(v)) || ((mode === "T" || mode === "qT") && !isFinite(T))) {
    logMsg("Feed entry incomplete; nothing applied.");
    return;
  }
  const zc = zIn.map((v) => Math.max(0, v));
  const sum = zc[0] + zc[1] + zc[2];
  if (sum <= 0) { logMsg("Feed composition is all zeros; nothing applied."); return; }
  const zn = zc.map((v) => v / sum);
  let Pin = P;
  let pNote = "";
  const pColNow = outputs()[0];
  if (Pin < pColNow) {
    Pin = pColNow;
    pNote = ` Feed pressure raised to the column pressure, ${pColNow.toFixed(0)} kPa: a feed cannot enter against a higher pressure.`;
  }
  const Tb = feedBubbleT(zn, Pin);
  let appliedT = T, appliedP = Pin, note = "";
  if (mode === "T") {
    setFeed(F, zn, T, Pin);
    note = ` Flash vapour fraction at the tray: ${(outputs()[31] * 100).toFixed(0)}%.`;
  } else if (mode === "qT") {
    const qPct = parseFloat($("inFeedQ").value);
    if (!isFinite(qPct)) { logMsg("No liquid fraction entered; nothing applied."); return; }
    const psiTarget = 1 - Math.min(100, Math.max(0, qPct)) / 100;
    const psiAtP = (Pp) => { setFeed(F, zn, T, Pp); return outputs()[31]; };
    let lo = Math.ceil(pColNow), hi = 500;
    const psiLo = psiAtP(lo), psiHi = psiAtP(hi);
    if (psiLo - psiHi < 1e-6) {
      note = " The flash fraction does not respond to the feed pressure at this temperature (the feed stays a liquid at its own conditions throughout); the pressure is left as entered.";
      setFeed(F, zn, T, Pin);
    } else if (psiTarget >= psiLo) {
      appliedP = lo;
      note = ` Liquid fraction ${qPct}% is below the flash range at this temperature; pressure set to ${lo} kPa (liquid fraction ${((1 - psiLo) * 100).toFixed(0)}%).`;
      setFeed(F, zn, T, appliedP);
    } else if (psiTarget <= psiHi) {
      appliedP = hi;
      note = ` Liquid fraction ${qPct}% is above the flash range at this temperature; pressure set to ${hi} kPa (liquid fraction ${((1 - psiHi) * 100).toFixed(0)}%).`;
      setFeed(F, zn, T, appliedP);
    } else {
      for (let i = 0; i < 24; i++) {
        const mid = (lo + hi) / 2;
        if (psiAtP(mid) > psiTarget) lo = mid; else hi = mid;
      }
      appliedP = (lo + hi) / 2;
      setFeed(F, zn, T, appliedP);
      note = ` Pressure from the adiabatic flash: ${appliedP.toFixed(0)} kPa (liquid fraction ${((1 - outputs()[31]) * 100).toFixed(0)}%).`;
    }
  } else {
    const qPct = parseFloat($("inFeedQ").value);
    if (!isFinite(qPct)) { logMsg("No liquid fraction entered; nothing applied."); return; }
    const psiTarget = 1 - Math.min(100, Math.max(0, qPct)) / 100;
    const psiAt = (Tt) => { setFeed(F, zn, Tt, Pin); return outputs()[31]; };
    let lo = Tb, hi = Tb + 150;
    const psiLo = psiAt(lo), psiHi = psiAt(hi);
    if (psiTarget <= psiLo) {
      appliedT = lo;
      note = ` Liquid fraction ${qPct}% is above the flash range at this pressure; the feed is set at its bubble point (liquid fraction ${((1 - psiLo) * 100).toFixed(0)}%).`;
    } else if (psiTarget >= psiHi) {
      appliedT = hi;
      note = ` Liquid fraction ${qPct}% is below the flash range reached in the search; temperature set to ${hi.toFixed(1)} K.`;
    } else {
      for (let i = 0; i < 24; i++) {
        const mid = (lo + hi) / 2;
        if (psiAt(mid) < psiTarget) lo = mid; else hi = mid;
      }
      appliedT = (lo + hi) / 2;
    }
    setFeed(F, zn, appliedT, Pin);
    note += ` Temperature from the adiabatic flash: ${appliedT.toFixed(1)} K (liquid fraction ${((1 - outputs()[31]) * 100).toFixed(0)}%).`;
  }
  logMsg(`Feed set directly: ${F.toFixed(2)} mol/s, pentane ${(zn[0] * 100).toFixed(0)}%, hexane ${(zn[1] * 100).toFixed(0)}%, heptane ${(zn[2] * 100).toFixed(0)}%, ${appliedT.toFixed(1)} K, ${appliedP.toFixed(0)} kPa.${note}${pNote}`);
  const btn = $("btnFeedApply");
  btn.textContent = "Applied \u2713";
  setTimeout(() => { btn.textContent = "Apply feed"; }, 1200);
  syncFeedInputs();
  refreshOutputs();
});

// ---------- Run controls and the main loop ----------
let playing = true;
$("btnPlay").addEventListener("click", () => {
  playing = !playing;
  $("btnPlay").textContent = playing ? "Pause" : "Play";
});
$("selAp").addEventListener("change", (e) => {
  const level = parseInt(e.target.value, 10);
  W.dg_set_autopilot(sim, level);
  pollApStatus();
  if (selected) syncValvePanel();
  logMsg(level === 0 ? "Autopilot off." :
    `Autopilot level ${level} engaged${level >= 1 ? "; the inlet valve is parked fully open" : ""}. Teal-outlined valves are on autopilot; moving one claims its seat.`);
});
function doReset() {
  HISTORY.length = 0;
  trayDepthVis = {};
  lastSampleT = -1;
  W.dg_reset(sim);
  $("selAp").value = "0";
  apStatus = null;
  W.dg_set_supply(sim, 298.0);
  simClock = 0;
  nominalFeedState = null;
  nominalOpenings = null;
  $("overBar").style.display = "none";
  prevAlarm = { hp: false, relief: false, flash: false, ruptured: false };
  playing = true;
  $("btnPlay").textContent = "Pause";
  logMsg("Reset to the nominal point.");
  refreshOutputs();
  syncFeedInputs(true);
}
$("btnReset").addEventListener("click", doReset);
$("btnOverReset").addEventListener("click", doReset);

let lastFrame = null, uiAccum = 0;
function tick(now) {
  requestAnimationFrame(tick);
  if (!W || !sim) return;
  if (lastFrame === null) { lastFrame = now; return; }
  const realDt = Math.min(0.1, (now - lastFrame) / 1000);
  lastFrame = now;
  if (playing) {
    const speed = parseFloat($("selSpeed").value);
    let simDt = realDt * speed;
    while (simDt > 0) {
      const h = Math.min(0.25, simDt);
      W.dg_step(sim, h);
      simClock += h;
      simDt -= h;
    }
    // Animate the riser flow.
    riserPhase = (riserPhase + realDt * 30) % 16;
    dyn.riser.setAttribute("stroke-dasharray", "7 9");
    dyn.riser.setAttribute("stroke-dashoffset", -riserPhase);
    uiAccum += realDt;
    if (uiAccum > 0.2) {
      uiAccum = 0;
      refreshOutputs();
      $("clock").textContent = `${Math.round(simClock)} s`;
    }
  }
}
loadEngine().catch((e) => {
  $("status").textContent = "Engine failed to load: " + e.message;
});

// ---------- Tray bubbling (vapour-rate driven) ----------
const trayVis = {};
let trayDepthVis = {};
let lastTrayClock = 0;
let bubLast = performance.now();
function animateBubbles(now) {
  requestAnimationFrame(animateBubbles);
  const dt = Math.min(0.05, (now - bubLast) / 1000);
  bubLast = now;
  if (!dyn.trayBubbles || !playing) return;
  for (let j = 1; j <= 12; j++) {
    const bubs = dyn.trayBubbles[j];
    if (!bubs) continue;
    const vis = trayVis[j] || { depth: 13, foamH: 0, rate: 1, plateY: 84 + (13 - j) * 32 };
    const rise = Math.max(2, vis.depth + vis.foamH - 3);
    for (let i = 0; i < bubs.length; i++) {
      const b = bubs[i];
      const active = vis.rate > 0.12 + i * 0.16;
      b.phase += dt * (0.15 + 1.15 * vis.rate) * b.speed;
      if (b.phase > 1) { b.phase -= 1; b.x = b.x0 + (Math.random() * 6 - 3); }
      b.el.setAttribute("cy", (vis.plateY - 2 - b.phase * rise).toFixed(1));
      b.el.setAttribute("cx", (b.x + Math.sin(b.phase * 6 + b.x0) * 1).toFixed(1));
      const op = active ? Math.sin(Math.PI * Math.min(1, b.phase)) * 0.8 : 0;
      b.el.setAttribute("opacity", op.toFixed(2));
      b.el.setAttribute("r", (0.7 + b.size * 0.6).toFixed(2));
    }
  }
}
requestAnimationFrame(animateBubbles);
// ---------- Plots: history, parameter catalogue, palette ----------
const HISTORY = [];
let lastSampleT = -1;
function sampleHistory(o) {
  if (simClock - lastSampleT < 1.0) return;
  lastSampleT = simClock;
  const fi = feedInfo();
  HISTORY.push({ t: simClock, v: Array.from(o), f: [fi.F, fi.T, fi.P, fi.z[0], fi.z[1], fi.z[2]] });
  if (HISTORY.length > 7200) HISTORY.shift();
}
const COMP_NAMES = ["pentane", "hexane", "heptane"];
const KEY_TAG = [" (light key)", " (heavy key)", ""];
const SERIES_COLORS = ["#16697a", "#b3541e", "#7d3c98", "#1e7a34",
  "#8a6d00", "#005f8f", "#a83232", "#4d4d4d"];
const PLOT_PARAMS = {};
const PLOT_GROUPS = [];
function defParam(id, name, short, group, unit, color, frac, get) {
  if (!PLOT_GROUPS.includes(group)) PLOT_GROUPS.push(group);
  PLOT_PARAMS[id] = { id, name, short, group, unit, color, frac, get };
}
(function buildCatalogue() {
  let ci = 0;
  const col = () => SERIES_COLORS[(ci++) % SERIES_COLORS.length];
  const P = (id, name, idx) => defParam(id, name, name, "Pressures", "kPa", col(), false, (s) => s.v[idx]);
  P("pcol", "Column pressure", 0); P("pcond", "Condenser pressure", 1);
  P("pdrum", "Drum pressure", 2); P("pchest", "Steam chest pressure", 3);
  defParam("lvl_drum", "Drum level", "drum level", "Levels and margin", "", col(), true, (s) => s.v[32]);
  defParam("lvl_reb", "Reboiler level", "reboiler level", "Levels and margin", "", col(), true, (s) => s.v[33]);
  defParam("flooded", "Condenser flooded fraction", "flooded", "Levels and margin", "", col(), true, (s) => s.v[23]);
  defParam("margin", "Subcooling margin", "margin", "Levels and margin", "K", col(), false, (s) => s.v[21]);
  const F = (id, name, idx) => defParam(id, name, name, "Flows", "mol/s", col(), false, (s) => s.v[idx]);
  F("feed", "Feed flow", 37); F("vrec", "Vapour, rectifying", 12);
  F("vstrip", "Vapour, stripping", 11); F("refluxf", "Reflux flow", 13);
  F("distf", "Distillate flow", 15); F("botf", "Bottoms flow", 16);
  F("vin", "Vapour into condenser", 17); F("bypassf", "Bypass vapour", 18);
  F("condrate", "Condensation rate", 19); F("drain", "Condensate to drum", 20);
  F("steamf", "Steam flow", 26); F("relieff", "Relief flow", 27);
  defParam("feedz0", "Feed pentane (light key)", "pentane", "Feed", "", COMP_COLORS[0], true, (s) => s.f[3]);
  defParam("feedz1", "Feed hexane (heavy key)", "hexane", "Feed", "", COMP_COLORS[1], true, (s) => s.f[4]);
  defParam("feedz2", "Feed heptane", "heptane", "Feed", "", COMP_COLORS[2], true, (s) => s.f[5]);
  defParam("feedT", "Feed temperature", "temperature", "Feed", "K", col(), false, (s) => s.f[1]);
  defParam("feedP", "Feed pressure", "pressure", "Feed", "kPa", col(), false, (s) => s.f[2]);
  const T = (id, name, idx) => defParam(id, name, name, "Temperatures", "K", col(), false, (s) => s.v[idx]);
  T("ttop", "Top temperature", 9); T("tdrum", "Drum temperature", 4);
  T("tcond", "Condensing temperature", 7); T("tpool", "Reboiler liquid temperature", 8);
  T("treb", "Reboiler temperature", 10); T("twout", "Water leaving condenser", 6);
  T("ttank", "Cooling tank temperature", 5);
  defParam("qcond", "Condenser duty", "condenser", "Duties", "kW", col(), false, (s) => s.v[25] / 1000);
  defParam("qreb", "Reboiler duty", "reboiler", "Duties", "kW", col(), false, (s) => s.v[24] / 1000);
  const compGroup = (prefix, label, base) => {
    for (let c = 0; c < 3; c++) {
      defParam(`${prefix}${c}`, `${label} ${COMP_NAMES[c]}${KEY_TAG[c]}`,
        COMP_NAMES[c], `${label} composition`, "", COMP_COLORS[c], true,
        (s) => s.v[base + c]);
    }
  };
  compGroup("xd", "Distillate", 40);
  compGroup("xb", "Bottoms", 49);
  compGroup("xt", "Top vapour", 46);
  compGroup("xp", "Condenser pool", 43);
  for (let j = 0; j <= 12; j++) {
    const stage = j === 0 ? "Reboiler" : `Tray ${j}`;
    for (let c = 0; c < 3; c++) {
      defParam(`xs${j}_${c}`, `${stage} ${COMP_NAMES[c]}`, `${stage} ${COMP_NAMES[c]}`,
        "Tray compositions", "", COMP_COLORS[c], true, (s) => s.v[52 + j * 3 + c]);
    }
    defParam(`ts${j}`, `${stage} temperature`, `${stage}`, "Tray temperatures", "K",
      col(), false, (s) => s.v[91 + j]);
  }
})();
function buildPalette() {
  const pal = $("palette");
  pal.innerHTML = "";
  for (const g of PLOT_GROUPS) {
    const det = document.createElement("details");
    if (g === "Distillate composition" || g === "Bottoms composition") det.open = true;
    const sum = document.createElement("summary");
    sum.textContent = g;
    det.appendChild(sum);
    const row = document.createElement("div");
    row.className = "chipRow";
    for (const p of Object.values(PLOT_PARAMS)) {
      if (p.group !== g) continue;
      const chip = document.createElement("span");
      chip.className = "pChip";
      chip.textContent = p.name;
      chip.dataset.pid = p.id;
      chip.draggable = true;
      chip.addEventListener("dragstart", (e) => {
        e.dataTransfer.setData("text/plain", "param:" + p.id);
        e.dataTransfer.effectAllowed = "copy";
      });
      chip.addEventListener("click", () => toggleParam(p.id));
      chip.addEventListener("mouseenter", () => {
        clearTimeout(window.__pvTimer);
        window.__pvTimer = setTimeout(() => showPlotPreview(p, chip), 250);
      });
      chip.addEventListener("mouseleave", () => {
        clearTimeout(window.__pvTimer);
        $("plotPreview").style.display = "none";
      });
      row.appendChild(chip);
    }
    det.appendChild(row);
    pal.appendChild(det);
  }
}

function showPlotPreview(p, chip) {
  const pv = $("plotPreview");
  const last = HISTORY.length ? HISTORY[HISTORY.length - 1] : null;
  pv.querySelector(".pvTitle").textContent =
    `${p.name} — ${last ? fmtVal(p, p.get(last)) : "no data yet"}`;
  const cv = pv.querySelector("canvas");
  const ctx = cv.getContext("2d");
  const W = cv.width, H = cv.height;
  ctx.clearRect(0, 0, W, H);
  if (HISTORY.length > 1) {
    const { tStart, tEnd } = plotWindow();
    const vis = HISTORY.filter((sm) => sm.t >= tStart - 1e-9);
    let lo = Infinity, hi = -Infinity;
    if (p.frac) { lo = 0; hi = 1; } else {
      for (const sm of vis) { const v = p.get(sm); if (v < lo) lo = v; if (v > hi) hi = v; }
      if (lo === Infinity) { lo = 0; hi = 1; }
      const pad = (hi - lo) * 0.1 || 1; lo -= pad; hi += pad;
    }
    ctx.strokeStyle = "#e3ddcb";
    ctx.beginPath(); ctx.moveTo(0, H - 1); ctx.lineTo(W, H - 1); ctx.stroke();
    ctx.strokeStyle = p.color; ctx.lineWidth = 1.6;
    ctx.beginPath();
    vis.forEach((sm, i) => {
      const x = (sm.t - tStart) / Math.max(1e-9, tEnd - tStart) * (W - 2) + 1;
      const y = H - 3 - (p.get(sm) - lo) / (hi - lo) * (H - 8);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke(); ctx.lineWidth = 1;
  }
  const r = chip.getBoundingClientRect();
  pv.style.display = "block";
  pv.style.left = (r.right + 10 + 280 > window.innerWidth
    ? Math.max(4, r.left - 290) : r.right + 10) + "px";
  pv.style.top = Math.max(4, Math.min(r.top, window.innerHeight - 140)) + "px";
}
function refreshChipStates() {
  const plotted = new Set();
  for (const t of tiles) for (const id of t.series) plotted.add(id);
  document.querySelectorAll(".pChip").forEach((chip) => {
    chip.classList.toggle("on", plotted.has(chip.dataset.pid));
  });
}
function toggleParam(pid) {
  const tile = tiles.find((t) => t.series.includes(pid));
  if (tile) removeSeries(tile, pid);
  else addTile([pid]);
}

// ---------- Plots: tiles and drawing ----------
let tiles = [];
let tileSeq = 0;
function fmtVal(p, v) {
  if (p.frac) return v.toFixed(3);
  return `${fmtY(v)}${p.unit ? " " + p.unit : ""}`;
}
function fmtClock(t) {
  return `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;
}
function fmtY(v) {
  const a = Math.abs(v);
  if (a >= 100) return v.toFixed(0);
  if (a >= 10) return v.toFixed(1);
  if (a >= 1) return v.toFixed(2);
  return v.toFixed(3);
}
function tileTitle(tile) {
  if (tile.fixedTitle) return tile.fixedTitle;
  const names = tile.series.map((id) => PLOT_PARAMS[id].short);
  return names.length === 1 ? PLOT_PARAMS[tile.series[0]].name : names.join(" · ");
}
function renderTileHead(tile) {
  tile.titleEl.textContent = tileTitle(tile);
  tile.legendEl.innerHTML = "";
  for (const id of tile.series) {
    const p = PLOT_PARAMS[id];
    const chip = document.createElement("span");
    chip.className = "sChip";
    const dot = document.createElement("span");
    dot.className = "dot";
    dot.style.background = p.color;
    chip.appendChild(dot);
    chip.appendChild(document.createTextNode(p.short));
    chip.draggable = true;
    chip.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("text/plain", `series:${tile.n}:${id}`);
      e.dataTransfer.effectAllowed = "move";
    });
    const x = document.createElement("button");
    x.textContent = "×";
    x.title = `Remove ${p.name}`;
    x.addEventListener("click", () => removeSeries(tile, id));
    chip.appendChild(x);
    tile.legendEl.appendChild(chip);
  }
}
function addTile(seriesIds, guides, fixedTitle) {
  const tile = { n: ++tileSeq, series: [...seriesIds], guides: guides || [], fixedTitle: fixedTitle || null };
  const el = document.createElement("div");
  el.className = "tile";
  const head = document.createElement("div");
  head.className = "tileHead";
  tile.titleEl = document.createElement("span");
  tile.titleEl.className = "tileTitle";
  const x = document.createElement("button");
  x.className = "tileX";
  x.textContent = "×";
  x.title = "Remove this plot";
  x.addEventListener("click", () => { el.remove(); tiles = tiles.filter((t) => t !== tile); refreshChipStates(); });
  head.appendChild(tile.titleEl);
  head.appendChild(x);
  head.draggable = true;
  head.addEventListener("dragstart", (e) => {
    e.dataTransfer.setData("text/plain", "tile:" + tile.n);
    e.dataTransfer.effectAllowed = "move";
  });
  tile.legendEl = document.createElement("div");
  tile.legendEl.className = "tileLegend";
  tile.canvas = document.createElement("canvas");
  tile.tipEl = document.createElement("div");
  tile.tipEl.className = "tileTip";
  tile.canvas.addEventListener("mousemove", (e) => {
    if (!HISTORY.length) return;
    const rect = tile.canvas.getBoundingClientRect();
    const mL = 36, pw = rect.width - 44;
    const { tStart, tEnd } = plotWindow();
    const t = tStart + (e.clientX - rect.left - mL) / Math.max(1, pw) * (tEnd - tStart);
    let best = null, bd = Infinity;
    for (const smp of HISTORY) {
      const d = Math.abs(smp.t - t);
      if (d < bd) { bd = d; best = smp; }
    }
    if (!best) return;
    tile.hover = best;
    tile.tipEl.innerHTML = `<b>${fmtClock(best.t)}</b>` + tile.series.map((id) => {
      const p = PLOT_PARAMS[id];
      return `<div><span style="color:${p.color}">\u25cf</span> ${p.name}: ${fmtVal(p, p.get(best))}</div>`;
    }).join("");
    tile.tipEl.style.display = "block";
    const tx = e.clientX - rect.left, ty = e.clientY - rect.top;
    tile.tipEl.style.left = (tx > rect.width - 170 ? tx - 165 : tx + 14) + "px";
    tile.tipEl.style.top = Math.max(0, ty - 10) + "px";
    drawTile(tile);
  });
  tile.canvas.addEventListener("mouseleave", () => {
    tile.hover = null;
    tile.tipEl.style.display = "none";
    drawTile(tile);
  });
  el.appendChild(head);
  el.appendChild(tile.legendEl);
  el.appendChild(tile.canvas);
  el.appendChild(tile.tipEl);
  el.addEventListener("dragover", (e) => { e.preventDefault(); el.classList.add("dragover"); });
  el.addEventListener("dragleave", () => el.classList.remove("dragover"));
  el.addEventListener("drop", (e) => {
    e.preventDefault();
    e.stopPropagation();
    el.classList.remove("dragover");
    const data = e.dataTransfer.getData("text/plain");
    if (data.startsWith("series:")) {
      const [, fromN, pid] = data.split(":");
      const src = tiles.find((t) => t.n === parseInt(fromN, 10));
      if (src && src !== tile && src.series.includes(pid)) moveSeries(src, pid, tile);
    } else if (data.startsWith("tile:")) {
      const dragged = tiles.find((t) => t.n === parseInt(data.slice(5), 10));
      if (dragged && dragged !== tile) moveTileBefore(dragged, tile);
    } else if (data.startsWith("param:")) {
      const pid = data.slice(6);
      if (PLOT_PARAMS[pid]) addSeries(tile, pid);
    }
  });
  tile.el = el;
  $("plotGrid").appendChild(el);
  tiles.push(tile);
  renderTileHead(tile);
  drawTile(tile);
  refreshChipStates();
  return tile;
}
function moveTileBefore(dragged, target) {
  $("plotGrid").insertBefore(dragged.el, target.el);
  tiles = tiles.filter((t) => t !== dragged);
  tiles.splice(tiles.indexOf(target), 0, dragged);
}
function moveTileToEnd(dragged) {
  $("plotGrid").appendChild(dragged.el);
  tiles = tiles.filter((t) => t !== dragged);
  tiles.push(dragged);
}
function moveSeries(src, pid, dst) {
  if (dst.series.includes(pid) || dst.series.length >= 6) return;
  dst.series.push(pid);
  dst.fixedTitle = null;
  renderTileHead(dst);
  drawTile(dst);
  removeSeries(src, pid);
}
function addSeries(tile, pid) {
  if (tile.series.includes(pid) || tile.series.length >= 6) return;
  tile.series.push(pid);
  tile.fixedTitle = null;
  renderTileHead(tile);
  drawTile(tile);
  refreshChipStates();
}
function removeSeries(tile, pid) {
  tile.series = tile.series.filter((s) => s !== pid);
  if (tile.series.length === 0) {
    tile.el.remove();
    tiles = tiles.filter((t) => t !== tile);
    refreshChipStates();
    return;
  }
  tile.fixedTitle = null;
  renderTileHead(tile);
  drawTile(tile);
  refreshChipStates();
}
function buildDefaultTiles() {
  $("plotGrid").innerHTML = "";
  tiles = [];
  addTile(["pcol"], [{ y: 360, label: "alarm 360" }, { y: 400, label: "relief 400" }], "Column pressure");
  addTile(["lvl_drum", "lvl_reb", "flooded"], [], "Levels and flooding");
  addTile(["feed", "distf", "botf", "refluxf"], [], "Flows");
  addTile(["xd0", "xd1", "xd2"], [{ y: 0.95, label: "spec 0.95" }], "Distillate composition");
  addTile(["xb0", "xb1", "xb2"], [{ y: 0.05, label: "spec 0.05" }], "Bottoms composition");
  addTile(["qcond", "qreb"], [], "Duties");
}
function plotWindow() {
  const winSel = $("selPlotWin").value;
  const win = winSel === "inf" ? Infinity : parseFloat(winSel);
  const tEnd = HISTORY.length ? HISTORY[HISTORY.length - 1].t : Math.max(simClock, 1);
  const tStart = Math.max(0, tEnd - win);
  return { tStart, tEnd };
}
function drawTile(tile) {
  const cv = tile.canvas;
  if (!cv || !cv.clientWidth) return;
  const dpr = window.devicePixelRatio || 1;
  const W = cv.clientWidth, H = cv.clientHeight;
  if (cv.width !== Math.round(W * dpr) || cv.height !== Math.round(H * dpr)) {
    cv.width = Math.round(W * dpr);
    cv.height = Math.round(H * dpr);
  }
  const ctx = cv.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);
  const mL = 36, mR = 8, mT = 5, mB = 15;
  const pw = W - mL - mR, ph = H - mT - mB;
  const { tStart, tEnd } = plotWindow();
  const vis = HISTORY.filter((s) => s.t >= tStart - 1e-9);
  const allFrac = tile.series.every((id) => PLOT_PARAMS[id].frac);
  let yLo = Infinity, yHi = -Infinity;
  if (allFrac && tile.series.length) { yLo = 0; yHi = 1; }
  if (yLo === Infinity) {
    for (const s of vis) for (const id of tile.series) {
      const v = PLOT_PARAMS[id].get(s);
      if (v < yLo) yLo = v;
      if (v > yHi) yHi = v;
    }
    for (const g of tile.guides) { if (g.y < yLo) yLo = g.y; if (g.y > yHi) yHi = g.y; }
    if (yLo === Infinity) { yLo = 0; yHi = 1; }
    const pad = (yHi - yLo) * 0.1 || 1;
    yLo -= pad; yHi += pad;
  }
  const X = (t) => mL + (t - tStart) / Math.max(1e-9, tEnd - tStart) * pw;
  const Y = (v) => mT + (yHi - v) / (yHi - yLo) * ph;
  ctx.font = "10px sans-serif";
  ctx.strokeStyle = "#e3ddcb";
  ctx.fillStyle = "#55503f";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const v = yLo + (yHi - yLo) * i / 4;
    const y = Y(v);
    ctx.beginPath(); ctx.moveTo(mL, y); ctx.lineTo(mL + pw, y); ctx.stroke();
    ctx.textAlign = "right";
    ctx.fillText(fmtY(v), mL - 3, y + 3);
  }
  ctx.textAlign = "left";
  ctx.fillText(fmtClock(tStart), mL, H - 3);
  ctx.textAlign = "right";
  ctx.fillText(fmtClock(tEnd), mL + pw, H - 3);
  for (const g of tile.guides) {
    if (g.y < yLo || g.y > yHi) continue;
    ctx.strokeStyle = "rgba(176,0,32,0.55)";
    ctx.setLineDash([5, 4]);
    ctx.beginPath(); ctx.moveTo(mL, Y(g.y)); ctx.lineTo(mL + pw, Y(g.y)); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "rgba(176,0,32,0.8)";
    ctx.textAlign = "right";
    ctx.fillText(g.label, mL + pw - 2, Y(g.y) - 3);
    ctx.fillStyle = "#55503f";
  }
  for (const id of tile.series) {
    const p = PLOT_PARAMS[id];
    ctx.strokeStyle = p.color;
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    let started = false;
    for (const s of vis) {
      const x = X(s.t), y = Y(p.get(s));
      if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  if (tile.hover && tile.hover.t >= tStart && tile.hover.t <= tEnd) {
    const hx = X(tile.hover.t);
    ctx.strokeStyle = "rgba(85,80,63,0.6)";
    ctx.setLineDash([3, 3]);
    ctx.beginPath(); ctx.moveTo(hx, mT); ctx.lineTo(hx, mT + ph); ctx.stroke();
    ctx.setLineDash([]);
    for (const id of tile.series) {
      const p = PLOT_PARAMS[id];
      ctx.fillStyle = p.color;
      ctx.strokeStyle = "#fff";
      ctx.beginPath(); ctx.arc(hx, Y(p.get(tile.hover)), 3.2, 0, 7); ctx.fill(); ctx.stroke();
    }
  }
  ctx.lineWidth = 1;
}
function drawAllTiles() {
  for (const t of tiles) drawTile(t);
}
(function initPlots() {
  const pv = document.createElement("div");
  pv.id = "plotPreview";
  pv.innerHTML = `<div class="pvTitle"></div><canvas width="262" height="84"></canvas>`;
  document.body.appendChild(pv);
  buildPalette();
  buildDefaultTiles();
  const panel = $("plotPanel");
  panel.addEventListener("dragover", (e) => { e.preventDefault(); panel.classList.add("dragover"); });
  panel.addEventListener("dragleave", () => panel.classList.remove("dragover"));
  panel.addEventListener("drop", (e) => {
    e.preventDefault();
    panel.classList.remove("dragover");
    const data = e.dataTransfer.getData("text/plain");
    if (data.startsWith("series:")) {
      const [, fromN, pid] = data.split(":");
      const src = tiles.find((t) => t.n === parseInt(fromN, 10));
      if (src && src.series.includes(pid)) {
        const t = addTile([pid]);
        removeSeries(src, pid);
      }
    } else if (data.startsWith("tile:")) {
      const dragged = tiles.find((t) => t.n === parseInt(data.slice(5), 10));
      if (dragged) moveTileToEnd(dragged);
    } else if (data.startsWith("param:")) {
      const pid = data.slice(6);
      if (PLOT_PARAMS[pid]) addTile([pid]);
    }
  });
  $("btnPlotsReset").addEventListener("click", buildDefaultTiles);
  $("selPlotWin").addEventListener("change", drawAllTiles);
})();
