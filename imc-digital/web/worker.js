// Pyodide worker: loads the Python runtime, writes imc_core.py
// and driver.py into the virtual file system, and answers
// messages of the form {id, type, payload} with
// {id, ok, result|error}. Errors are returned as the final line
// of the Python error text, which for a validation failure
// names the offending field in plain language.
importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js");

let ready = null;
async function boot() {
  const pyodide = await loadPyodide();
  await pyodide.loadPackage(["numpy"]);
  pyodide.FS.writeFile("imc_core.py", CORE_SRC);
  pyodide.FS.writeFile("driver.py", DRIVER_SRC);
  await pyodide.runPythonAsync(
    "import driver\n" +
    "_handle = lambda t, p: driver.handle(t, p)\n");
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
    const raw = String((e && e.message) || e);
    const lines = raw.split("\n").map((s) => s.trim()).filter(Boolean);
    self.postMessage({ id, ok: false,
                       error: lines.length ? lines[lines.length - 1] : raw });
  }
};
