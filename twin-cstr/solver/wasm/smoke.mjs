// Node.js smoke test for the mhe_rti.wasm C ABI.
//
// Usage:
//   cargo test --release --test wasm_parity   # native reference first
//   node wasm/smoke.mjs                       # this file
//
// The test instantiates the module with WebAssembly.Module /
// WebAssembly.Instance (no imports), checks the raw ABI surface and the
// error status codes, then drives 80 estimator steps (both fixtures,
// through the mhe_api.mjs factory) and asserts agreement with the native
// Rust estimator within 1e-9 on the physical slots and exact equality on
// the diagnostic slots. It also exercises the isStale abort path of
// runSteps. No TextEncoder or browser-only API is used, so the same module
// and factory instantiate in a Web Worker.

import { readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createMheApi } from "./mhe_api.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const wasmBytes = readFileSync(join(here, "mhe_rti.wasm"));

let failures = 0;
function check(cond, label) {
  if (cond) {
    console.log(`ok   ${label}`);
  } else {
    failures += 1;
    console.log(`FAIL ${label}`);
  }
}

// --- 1. Raw ABI surface -------------------------------------------------
{
  const module = new WebAssembly.Module(wasmBytes);
  const instance = new WebAssembly.Instance(module, {});
  const ex = instance.exports;
  check(ex.memory instanceof WebAssembly.Memory, "exports memory");
  for (const name of [
    "mhe_create",
    "mhe_destroy",
    "mhe_alloc",
    "mhe_step",
    "mhe_out_ptr",
    "mhe_out_len",
  ]) {
    check(typeof ex[name] === "function", `exports ${name}`);
  }
  check((ex.mhe_out_len() >>> 0) === 10, "mhe_out_len() === 10");

  // Status codes on a fresh instance (module-global input buffer empty).
  check((ex.mhe_step(999) | 0) === -1, "bad handle -> -1");
  const h0 = ex.mhe_create(8) >>> 0;
  check((ex.mhe_step(h0) | 0) === -2, "no input buffer -> -2");
  ex.mhe_destroy(h0);
  check((ex.mhe_step(h0) | 0) === -1, "destroyed handle -> -1");

  // A second instance has independent module-global state.
  const other = new WebAssembly.Instance(module, {});
  const h1 = other.exports.mhe_create(8) >>> 0;
  check(
    (other.exports.mhe_step(h1) | 0) === -2,
    "fresh instance has empty input buffer"
  );
}

// --- 2. Factory-driven comparison against the native estimator ----------
const api = createMheApi();
await api.init(wasmBytes);

const native = JSON.parse(
  readFileSync(join(tmpdir(), "mhe_native_estimates.json"), "utf8")
);

function toSample(s) {
  return {
    t: s.t,
    tMeas: s.T,
    tjMeas: s.T_j,
    f: s.F,
    t0: s.T0,
    hasLab: s.lab_C_A !== null && s.lab_C_A !== undefined,
    labCA: s.lab_C_A ?? 0.0,
    labTSample: s.lab_t_sample ?? 0.0,
  };
}

function toSlots(e) {
  return [
    e.cA,
    e.t,
    e.tJ,
    e.ua,
    e.residT,
    e.residTj,
    e.fj,
    e.status,
    e.nIter,
    e.nActiveBounds,
  ];
}

let maxDev = 0;
let steps = 0;
for (const name of ["estimator.json", "estimator_lab.json"]) {
  const fx = JSON.parse(
    readFileSync(join(here, "..", "tests", "fixtures", name), "utf8")
  );
  const samples = fx.samples.map(toSample);
  const handle = api.create(8);
  const { aborted, estimates } = await api.runSteps(handle, samples, {
    chunk: 16,
    isStale: () => false,
  });
  check(!aborted, `${name}: runSteps completed`);
  check(
    estimates.length === native[name].length,
    `${name}: ${estimates.length} estimates`
  );
  let worst = 0;
  let diagExact = true;
  for (let i = 0; i < estimates.length; i++) {
    const got = toSlots(estimates[i]);
    const want = native[name][i];
    for (let j = 0; j < 7; j++) {
      worst = Math.max(worst, Math.abs(got[j] - want[j]));
    }
    for (let j = 7; j < 10; j++) {
      if (got[j] !== want[j]) diagExact = false;
    }
  }
  console.log(`     ${name}: max |dev| on physical slots = ${worst}`);
  maxDev = Math.max(maxDev, worst);
  steps += estimates.length;
  check(worst <= 1e-9, `${name}: max deviation <= 1e-9`);
  check(diagExact, `${name}: diagnostic slots exact`);
  api.destroy(handle);
}

// --- 3. isStale abort path ----------------------------------------------
{
  const handle = api.create(8);
  const fx = JSON.parse(
    readFileSync(join(here, "..", "tests", "fixtures", "estimator.json"), "utf8")
  );
  const { aborted, estimates } = await api.runSteps(
    handle,
    fx.samples.map(toSample),
    { chunk: 8, isStale: () => true }
  );
  check(aborted && estimates.length === 0, "isStale aborts before first chunk");
  api.destroy(handle);
}

// --- 4. Factory surfaces step errors as exceptions -----------------------
{
  const handle = api.create(8);
  api.destroy(handle);
  let threw = false;
  try {
    api.step(handle, toSample({ t: 10, T: 370, T_j: 336, F: 0.00167, T0: 300 }));
  } catch {
    threw = true;
  }
  check(threw, "step on destroyed handle throws");
}

console.log(`\n${steps} steps compared, worst deviation ${maxDev}`);
if (failures > 0) {
  console.log(`${failures} FAILURE(S)`);
  process.exit(1);
}
console.log("smoke test passed");
