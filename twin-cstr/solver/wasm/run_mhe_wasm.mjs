// Build-time MHE precompute: drive the committed mhe_rti.wasm from Node.js
// over the build-time sample stream and dump the estimates as JSON.
//
// Usage: node run_mhe_wasm.mjs <samples.json> <wasm> <out.json>
// samples.json: {"H": 30, "variants": {"m1": {"samples": [[t,T,Tj,F,T0,has_lab,lab,lab_t], ...]}, ...}}
// out.json: {"estimates": {"m1": [flat n*10], ...}, "ms_per_step": {"m1": ms, ...}}
import { readFileSync, writeFileSync } from "fs";
import { createMheApi } from "./mhe_api.mjs";

const [samplesPath, wasmPath, outPath] = process.argv.slice(2);
const bundle = JSON.parse(readFileSync(samplesPath, "utf-8"));
const wasmBytes = readFileSync(wasmPath);

const api = createMheApi();
await api.init(wasmBytes); // WebAssembly.Module compiled once

const estimates = {};
const msPerStep = {};
for (const key of Object.keys(bundle.variants)) {
  const rows = bundle.variants[key].samples;
  const samples = rows.map((s) => ({
    t: s[0], tMeas: s[1], tjMeas: s[2], f: s[3], t0: s[4],
    hasLab: s[5] !== 0, labCA: s[6], labTSample: s[7],
  }));
  const handle = api.create(bundle.H >>> 0);
  const t0 = Date.now();
  const r = await api.runSteps(handle, samples, { chunk: 480 });
  const dtMs = Date.now() - t0;
  api.destroy(handle);
  if (r.aborted) throw new Error(`run aborted for ${key}`);
  const flat = new Array(r.estimates.length * 10);
  r.estimates.forEach((e, i) => {
    const o = i * 10;
    flat[o] = e.cA; flat[o+1] = e.t; flat[o+2] = e.tJ; flat[o+3] = e.ua;
    flat[o+4] = e.residT; flat[o+5] = e.residTj; flat[o+6] = e.fj;
    flat[o+7] = e.status; flat[o+8] = e.nIter; flat[o+9] = e.nActiveBounds;
  });
  estimates[key] = flat;
  msPerStep[key] = dtMs / samples.length;
  console.log(`[run_mhe_wasm] ${key}: ${samples.length} steps, ` +
              `${msPerStep[key].toFixed(3)} ms/step`);
}
writeFileSync(outPath, JSON.stringify({ estimates, ms_per_step: msPerStep }));
console.log(`[run_mhe_wasm] wrote ${outPath}`);
