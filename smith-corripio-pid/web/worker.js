// Pyodide worker: loads the Python runtime, writes pid_core.py and
// driver.py into the virtual file system, and answers messages of
// the form {id, type, payload} with {id, ok, result|error}.
// Progress during sweeps arrives as {type: "progress", frac}.
importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js");

let ready = null;
async function boot() {
  const pyodide = await loadPyodide();
  await pyodide.loadPackage(["numpy", "scipy"]);
  pyodide.FS.writeFile("pid_core.py", CORE_SRC);
  pyodide.FS.writeFile("driver.py", DRIVER_SRC);
  pyodide.globals.set("post_progress", (frac) => {
    self.postMessage({ type: "progress", frac: frac });
  });
  await pyodide.runPythonAsync(
    "import driver\n" +
    "_prog = lambda f: post_progress(float(f))\n" +
    "_handle = lambda t, p: driver.handle(t, p, progress=_prog)\n");
  return pyodide;
}
ready = boot();
ready.then(() => self.postMessage({ type: "ready" }))
     .catch((e) => self.postMessage({ type: "fatal", error: String(e) }));

self.onmessage = async (ev) => {
  const { id, type, payload } = ev.data;
  let pyodide;
  try {
    pyodide = await ready;
  } catch (e) {
    self.postMessage({ id, ok: false, error: "runtime failed: " + String(e) });
    return;
  }
  try {
    pyodide.globals.set("_payload_json", JSON.stringify(payload || {}));
    const out = await pyodide.runPythonAsync(
      "import json\n" +
      "json.dumps(_handle('" + type + "', json.loads(_payload_json)))");
    self.postMessage({ id, ok: true, result: JSON.parse(out) });
  } catch (e) {
    // Pass the Python error text through (its final line, which for
    // a validation failure names the offending field); the page
    // displays this message in its note field.
    const raw = String((e && e.message) || e);
    const lines = raw.split("\n").map((s) => s.trim()).filter(Boolean);
    self.postMessage({ id, ok: false,
                       error: lines.length ? lines[lines.length - 1] : raw });
  }
};
