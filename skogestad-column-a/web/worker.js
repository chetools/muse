// Pyodide worker: loads the Python runtime, writes column_a.py,
// driver.py and the vendored autograd package into the virtual
// file system, and answers messages of the form {id, type,
// payload} with {id, ok, result|error}.
importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js");

let ready = null;
async function boot() {
  const pyodide = await loadPyodide();
  await pyodide.loadPackage(["numpy", "scipy"]);
  pyodide.FS.writeFile("column_a.py", CORE_SRC);
  pyodide.FS.writeFile("driver.py", DRIVER_SRC);
  const dirs = new Set();
  for (const path of Object.keys(AUTOGRAD_FILES)) {
    const parts = path.split("/").slice(0, -1);
    let cur = "";
    for (const p of parts) { cur = cur ? cur + "/" + p : p; dirs.add(cur); }
  }
  for (const d of [...dirs].sort()) {
    try { pyodide.FS.mkdir(d); } catch (e) { /* already exists */ }
  }
  for (const [path, src] of Object.entries(AUTOGRAD_FILES)) {
    pyodide.FS.writeFile(path, src);
  }
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
