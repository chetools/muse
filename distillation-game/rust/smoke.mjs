// Headless smoke test of the WASM API (node smoke.mjs).
import { readFileSync } from "node:fs";

const bytes = readFileSync(
  new URL("./target/wasm32-unknown-unknown/release/distgame_engine.wasm", import.meta.url));
const { instance } = await WebAssembly.instantiate(bytes, {});
const ex = instance.exports;
const mem = ex.memory;

const sim = ex.dg_sim_new();
console.log("state len:", ex.dg_state_len(sim));
const outPtr = ex.dg_alloc(104);
const out = () => {
  ex.dg_outputs(sim, outPtr);
  return new Float64Array(mem.buffer, outPtr, 104);
};
let o = out();
console.log("t=0  P_col", o[0].toFixed(1), "P_drum", o[2].toFixed(1),
  "D", o[15].toFixed(2), "L_R", o[13].toFixed(2), "margin", o[21].toFixed(2),
  "x_drum", Array.from(o.slice(40, 43)).map((v) => v.toFixed(3)).join("/"));
const t0 = performance.now();
for (let k = 0; k < 60; k++) ex.dg_step(sim, 1.0);
const ms = performance.now() - t0;
o = out();
console.log("t=60 P_col", o[0].toFixed(1), "P_drum", o[2].toFixed(1),
  "D", o[15].toFixed(2), "drum level", o[32].toFixed(3),
  "x_drum", Array.from(o.slice(40, 43)).map((v) => v.toFixed(3)).join("/"));
console.log(`stepping: ${ms.toFixed(1)} ms for 60 s of plant time`);
// Disturbance: feed +20 percent through the feed setter.
const zPtr = ex.dg_alloc(3);
new Float64Array(mem.buffer, zPtr, 3).set([0.4, 0.3, 0.3]);
ex.dg_set_feed(sim, zPtr, 352.0, 300.0);
ex.dg_set_feed_setpoint(sim, 12.0);
for (let k = 0; k < 60; k++) ex.dg_step(sim, 1.0);
o = out();
console.log("feed +20%: P_col", o[0].toFixed(1), "drum level", o[32].toFixed(3),
  "D", o[15].toFixed(2));
ex.dg_reset(sim);
o = out();
console.log("after reset: P_col", o[0].toFixed(1), "D", o[15].toFixed(2));
// Autopilot: engage level 2, run the feed +20% case briefly,
// check the status layout and the seat claim/release cycle.
const apPtr = ex.dg_alloc(13);
const apStatus = () => {
  ex.dg_ap_status(sim, apPtr);
  return new Float64Array(mem.buffer, apPtr, 13);
};
ex.dg_set_autopilot(sim, 2);
let aps = apStatus();
console.log("ap on: level", aps[0], "seats", Array.from(aps.slice(2)).join(""));
ex.dg_set_feed(sim, zPtr, 352.0, 300.0);
ex.dg_set_feed_setpoint(sim, 12.0);
for (let k = 0; k < 300; k++) ex.dg_step(sim, 1.0);
o = out();
console.log("ap L2, feed +20%, t=300: drum level", o[32].toFixed(3),
  "reb level", o[33].toFixed(3), "P_col", o[0].toFixed(1),
  "xd", o[40].toFixed(3));
ex.dg_set_opening(sim, 4, 30.0);   // claim the distillate seat
aps = apStatus();
console.log("after claim: distillate seat mode", aps[2 + 4]);
ex.dg_release_seat(sim, 4);
aps = apStatus();
console.log("after release: distillate seat mode", aps[2 + 4]);
ex.dg_set_autopilot(sim, 0);
aps = apStatus();
console.log("ap off: level", aps[0]);
// Feed bubble helper used by the composition disturbances.
new Float64Array(mem.buffer, zPtr, 3).set([0.55, 0.25, 0.20]);
console.log("bubble T of richer feed at 150 kPa:",
  ex.dg_feed_bubble(sim, zPtr, 150.0).toFixed(2), "K");
ex.dg_sim_free(sim);
console.log("SMOKE OK");
