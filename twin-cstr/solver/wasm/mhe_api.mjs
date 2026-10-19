// MHE WebAssembly API factory.
//
// Wraps the C ABI exported by mhe_rti.wasm (see README.md for the buffer
// layouts). Dependency-free: the only globals used are WebAssembly,
// Float64Array, Promise, and setTimeout, all present in Node.js and in Web
// Workers. No TextEncoder or other browser-only API is referenced, including
// at module scope.
//
// Intended use (page integration): the page build stringifies this module
// into a Blob URL, constructs a Worker from it, and posts the compiled
// WebAssembly.Module to the worker once. Inside the worker, init() is called
// with the module bytes, then runSteps() drives chunked multi-step runs.
//
// Symbol definitions (SI units):
// - sample: { t: s, sample time; tMeas: K, measured reactor temperature;
//     tjMeas: K, measured jacket temperature; f: L/s, feed flow;
//     t0: K, feed temperature; hasLab: boolean, laboratory sample present;
//     labCA: mol/L, laboratory C_A; labTSample: s, its sampling time }.
//   labCA/labTSample are read only when hasLab is true.
// - estimate: { cA: mol/L; t: K; tJ: K; ua: J/(s K);
//     residT: K, pre-update reactor-temperature residual;
//     residTj: K, pre-update jacket-temperature residual;
//     fj: L/s, coolant flow from the estimator's PI-controller copy;
//     status: dimensionless, 0 on success;
//     nIter: dimensionless, always 1 (one Gauss-Newton SQP iteration per
//       measurement); nActiveBounds: dimensionless, 0..4 }.
// - handle: dimensionless u32 identifying one estimator instance. Instances
//   persist across calls (window, warm start, controller integral state,
//   arrival-cost filter); use one handle per worker, never shared across
//   threads.

export function createMheApi() {
  const IN_SLOTS = 8; // f64 slots per input sample (see README.md)
  const OUT_SLOTS = 10; // f64 slots per output vector (see README.md)

  let wasm = null; // instance exports, set by init()
  let memory = null; // WebAssembly.Memory, set by init()

  function checkInit() {
    if (wasm === null || memory === null) {
      throw new Error("mhe_api: init(wasmBytes) must be called first");
    }
  }

  // Compile and instantiate the module. wasmBytes is any BufferSource
  // (Uint8Array, ArrayBuffer, Node Buffer). Compiles once per worker.
  async function init(wasmBytes) {
    const module = new WebAssembly.Module(wasmBytes);
    const instance = new WebAssembly.Instance(module, {});
    if (!(instance.exports.memory instanceof WebAssembly.Memory)) {
      throw new Error("mhe_api: module exports no memory");
    }
    for (const name of [
      "mhe_create",
      "mhe_destroy",
      "mhe_alloc",
      "mhe_step",
      "mhe_out_ptr",
      "mhe_out_len",
    ]) {
      if (typeof instance.exports[name] !== "function") {
        throw new Error(`mhe_api: module is missing export ${name}`);
      }
    }
    wasm = instance.exports;
    memory = wasm.memory;
    if ((wasm.mhe_out_len() >>> 0) !== OUT_SLOTS) {
      throw new Error("mhe_api: output length mismatch");
    }
  }

  // Create an estimator instance with horizon length H (samples).
  // Returns the u32 handle.
  function create(H) {
    checkInit();
    return wasm.mhe_create(H) >>> 0;
  }

  // Release the estimator instance identified by handle.
  function destroy(handle) {
    checkInit();
    wasm.mhe_destroy(handle);
  }

  // Advance the estimator by one sample; returns the estimate object.
  // Throws when the step reports a nonzero status.
  function step(handle, s) {
    checkInit();
    const ptr = wasm.mhe_alloc(IN_SLOTS);
    const view = new Float64Array(memory.buffer, ptr, IN_SLOTS);
    view[0] = s.t;
    view[1] = s.tMeas;
    view[2] = s.tjMeas;
    view[3] = s.f;
    view[4] = s.t0;
    view[5] = s.hasLab ? 1.0 : 0.0;
    view[6] = s.hasLab ? s.labCA : 0.0;
    view[7] = s.hasLab ? s.labTSample : 0.0;
    const status = wasm.mhe_step(handle) | 0;
    if (status !== 0) {
      throw new Error(`mhe_api: mhe_step failed with status ${status}`);
    }
    const out = new Float64Array(
      memory.buffer,
      wasm.mhe_out_ptr(),
      wasm.mhe_out_len() >>> 0
    );
    return {
      cA: out[0],
      t: out[1],
      tJ: out[2],
      ua: out[3],
      residT: out[4],
      residTj: out[5],
      fj: out[6],
      status: out[7],
      nIter: out[8],
      nActiveBounds: out[9],
    };
  }

  // Drive a multi-step run in chunks, yielding to the event loop between
  // chunks so the worker stays responsive.
  //
  // opts.chunk: samples per chunk (default 200).
  // opts.isStale: () -> boolean, checked before each chunk; when it returns
  //   true the run aborts and { aborted: true } is returned, so a newer
  //   input change discards work not yet started.
  // opts.onProgress: (done, total) -> void, called after each chunk.
  //
  // Returns { aborted: boolean, estimates: [...] }.
  async function runSteps(handle, samples, opts = {}) {
    const chunk = opts.chunk || 200;
    const isStale = opts.isStale || (() => false);
    const onProgress = opts.onProgress || null;
    const estimates = [];
    for (let i = 0; i < samples.length; i += chunk) {
      if (isStale()) {
        return { aborted: true, estimates };
      }
      const end = Math.min(i + chunk, samples.length);
      for (let k = i; k < end; k++) {
        estimates.push(step(handle, samples[k]));
      }
      if (onProgress) {
        onProgress(end, samples.length);
      }
      if (end < samples.length) {
        await new Promise((resolve) => setTimeout(resolve, 0));
      }
    }
    return { aborted: false, estimates };
  }

  return { init, create, destroy, step, runSteps, IN_SLOTS, OUT_SLOTS };
}
