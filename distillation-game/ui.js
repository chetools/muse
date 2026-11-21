"use strict";
// ---------- Formatting ----------
const f1 = (v) => v.toFixed(1);
const f2 = (v) => v.toFixed(2);
const pct = (v) => (v * 100).toFixed(1) + "%";
const kW = (v) => (v / 1000).toFixed(0) + " kW";

// ---------- Sound (synthesised, no audio files) ----------
let audio = null, masterGain = null;
function ensureAudio() {
  if (audio) return;
  try {
    audio = new (window.AudioContext || window.webkitAudioContext)();
    masterGain = audio.createGain();
    masterGain.gain.value = 0.5;
    masterGain.connect(audio.destination);
  } catch (e) { audio = null; }
}
function click(delay, freq) {
  if (!audio || !$("chkSound").checked) return;
  const t = audio.currentTime + delay;
  const o = audio.createOscillator(), g = audio.createGain();
  o.type = "square"; o.frequency.value = freq || 1800;
  g.gain.setValueAtTime(0.06, t);
  g.gain.exponentialRampToValueAtTime(0.001, t + 0.03);
  o.connect(g); g.connect(masterGain);
  o.start(t); o.stop(t + 0.04);
}
let lastOpeningVal = {};
function soundValve(idx, value) {
  ensureAudio();
  if (!audio || !$("chkSound").checked) return;
  const prev = lastOpeningVal[idx];
  lastOpeningVal[idx] = value;
  if (prev === undefined || Math.abs(value - prev) < 0.01) return;
  // Soft clicks, density rising with the size of the move.
  const n = Math.min(6, Math.max(1, Math.round(Math.abs(value - prev) / 4)));
  for (let i = 0; i < n; i++) click(i * 0.05, 1400 + Math.random() * 500);
}
let alarmSoundAt = 0;
function soundAlarm(kind) {
  ensureAudio();
  if (!audio || !$("chkSound").checked) return;
  const now = performance.now();
  if (now - alarmSoundAt < 1600) return;
  alarmSoundAt = now;
  const freq = kind === "relief" ? 620 : 880;
  for (let i = 0; i < 2; i++) {
    const t = audio.currentTime + i * 0.22;
    const o = audio.createOscillator(), g = audio.createGain();
    o.type = "sine"; o.frequency.value = freq;
    g.gain.setValueAtTime(0.12, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + 0.18);
    o.connect(g); g.connect(masterGain);
    o.start(t); o.stop(t + 0.2);
  }
}

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
function syncValvePanel() {
  if (!selected) return;
  const v = VALVES[selected];
  const disp = valveDisplay(selected);
  $("vSlider").value = disp;
  $("vOpenVal").textContent = v.kind === "kpa" ? `${disp.toFixed(0)} kPa` : `${disp.toFixed(1)}%`;
}
function applyValve(dispValue) {
  if (!selected) return;
  const v = VALVES[selected];
  const raw = v.kind === "frac" ? dispValue / 100 : dispValue;
  setOpening(v.idx, raw);
  syncValvePanel();
}
$("vSlider").addEventListener("input", (e) => applyValve(parseFloat(e.target.value)));
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
function tempColor(t) {
  const u = Math.min(1, Math.max(0, (t - 315) / 95));
  return `hsl(${Math.round(215 - 215 * u)}, 70%, ${Math.round(72 - 22 * u)}%)`;
}
let prevAlarm = { hp: false, relief: false, flash: false, ruptured: false };
let riserPhase = 0;

function refreshOutputs() {
  const o = outputs();
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
    dyn.trayTemp[j].setAttribute("fill", tempColor(o[91 + j]));
  }
  dyn.topT.textContent = `top ${f1(o[9])} K`;
  dyn.rebT.textContent = `${f1(o[10])} K, level ${pct(o[33])}`;
  const rebY = 84 + 32 * 12 + 14;
  dyn.rebLiq.setAttribute("y", rebY + 58 - 2 - o[33] * 54);
  dyn.rebLiq.setAttribute("height", o[33] * 54);
  dyn.feedLbl.textContent = `F = ${f2(o[37])} mol/s`;
  // Drum and condenser levels.
  dyn.drumLiq.setAttribute("y", 108 + 82 - 2 - o[32] * 78);
  dyn.drumLiq.setAttribute("height", o[32] * 78);
  dyn.drumLbl.textContent = `P ${f1(P.drum)} kPa`;
  dyn.drumLbl2.textContent = `level ${pct(o[32])}, ${f1(o[4])} K`;
  dyn.condFlood.setAttribute("y", 286 + 92 - 2 - o[23] * 88);
  dyn.condFlood.setAttribute("height", o[23] * 88);
  dyn.condLbl.textContent = `flooded ${pct(o[23])}, condensing at ${f1(o[7])} K`;
  dyn.riserLbl.textContent = `${f2(o[20])} mol/s, margin ${f2(o[21])} K`;
  dyn.riser.setAttribute("stroke", o[21] < 0 ? "#b3541e" : "#56b4e9");
  dyn.reliefLbl.textContent = o[27] > 0 ? `LIFTING ${f2(o[27])} mol/s` : "";
  dyn.distLbl.textContent = `${f2(o[15])} mol/s`;
  dyn.botLbl.textContent = `${f2(o[16])} mol/s`;
  dyn.chestLbl.textContent = `${f1(P.chest)} kPa`;
  dyn.tankLbl.textContent = `${f1(o[5])} K`;
  dyn.qCondArrow.textContent = `condenser duty ${kW(o[25])}`;
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
    <span class="sect">Products</span>
    <span>Distillate pentane</span><span class="v ${specD ? "spec-ok" : "spec-bad"}">${pct(xd[0])}</span>
    <span>Bottoms pentane</span><span class="v ${specB ? "spec-ok" : "spec-bad"}">${pct(xb[0])}</span>`;
  segSet(segDist, xd);
  segSet(segBot, xb);
  // Alarms.
  const alarm = { hp: o[36] > 0, relief: o[35] > 0, flash: o[21] < 0, ruptured: o[34] > 0 };
  const bar = $("alarmBar");
  bar.className = "";
  bar.style.display = "none";
  if (alarm.relief) {
    bar.className = "relief"; bar.style.display = "block";
    bar.textContent = "RELIEF VALVE LIFTING — vapour is being lost to the flare and the score penalty is heavy.";
    soundAlarm("relief");
  } else if (alarm.hp) {
    bar.className = "hp"; bar.style.display = "block";
    bar.textContent = "HIGH PRESSURE ALARM — column pressure is above 360 kPa. The relief valve lifts at 400 kPa.";
    soundAlarm("hp");
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
  if (selected) syncValvePanel();
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
const NOMINAL_FEED = { F: 10, z: [0.4, 0.3, 0.3] };
let nominalFeedState = null;
document.querySelectorAll(".dist").forEach((b) => {
  b.addEventListener("click", () => {
    const fi = feedInfo();
    if (!nominalFeedState) nominalFeedState = fi;
    const d = b.dataset.d;
    if (d === "feedUp") { setFeed(fi.F * 1.2, fi.z, fi.T, fi.P); logMsg("Disturbance: feed flow +20%."); }
    if (d === "feedDown") { setFeed(fi.F / 1.2, fi.z, fi.T, fi.P); logMsg("Disturbance: feed flow −20%."); }
    if (d === "feedLight") { setFeed(fi.F, [0.55, 0.25, 0.20], fi.T, fi.P); logMsg("Disturbance: feed richer in pentane."); }
    if (d === "feedHeavy") { setFeed(fi.F, [0.25, 0.35, 0.40], fi.T, fi.P); logMsg("Disturbance: feed leaner in pentane."); }
    if (d === "warmWater") { W.dg_set_supply(sim, 308.15); logMsg("Disturbance: cooling supply warmed to 35 °C."); }
    if (d === "restore") {
      const n = nominalFeedState || { ...NOMINAL_FEED, T: fi.T, P: fi.P };
      setFeed(n.F, n.z, n.T, n.P);
      W.dg_set_supply(sim, 298.0);
      logMsg("Feed and cooling supply restored to nominal.");
    }
    refreshOutputs();
  });
});

// ---------- Run controls and the main loop ----------
let playing = true;
$("btnPlay").addEventListener("click", () => {
  playing = !playing;
  $("btnPlay").textContent = playing ? "Pause" : "Play";
});
function doReset() {
  W.dg_reset(sim);
  W.dg_set_supply(sim, 298.0);
  simClock = 0;
  nominalFeedState = null;
  $("overBar").style.display = "none";
  prevAlarm = { hp: false, relief: false, flash: false, ruptured: false };
  playing = true;
  $("btnPlay").textContent = "Pause";
  logMsg("Reset to the nominal point.");
  refreshOutputs();
}
$("btnReset").addEventListener("click", doReset);
$("btnOverReset").addEventListener("click", doReset);
$("chkSound").addEventListener("change", ensureAudio);

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
