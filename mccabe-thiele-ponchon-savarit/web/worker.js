// Pyodide worker: runs mtps_core.solve_column in Python only.
importScripts("https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js");

let pyodide = null;
let ready = false;

function b64ToText(b64) {
  const bin = atob(b64.replace(/\s+/g, ""));
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new TextDecoder("utf-8").decode(bytes);
}

async function init(dataB64, coreB64) {
  pyodide = await loadPyodide();
  await pyodide.loadPackage(["numpy", "scipy"]);
  pyodide.FS.writeFile("mtps_data.py", b64ToText(dataB64));
  pyodide.FS.writeFile("mtps_core.py", b64ToText(coreB64));
  pyodide.runPython("import mtps_core");
  ready = true;
  postMessage({ type: "ready" });
}

self.onmessage = async (ev) => {
  const msg = ev.data;
  if (msg.type === "init") {
    try {
      await init(msg.dataB64, msg.coreB64);
    } catch (err) {
      console.error(err);
      postMessage({ type: "fatal", message: "The Python runtime failed to load." });
    }
    return;
  }
  if (msg.type === "solve") {
    if (!ready) {
      postMessage({ type: "error", id: msg.id,
        message: "The Python runtime is not ready yet. Wait for the ready message and press Run again." });
      return;
    }
    try {
      pyodide.globals.set("spec_json", JSON.stringify(msg.spec));
      const out = pyodide.runPython(
        "import json, mtps_core\n" +
        "json.dumps(mtps_core.solve_column(json.loads(spec_json)))");
      postMessage({ type: "result", id: msg.id, result: JSON.parse(out) });
    } catch (err) {
      console.error(err);
      postMessage({ type: "error", id: msg.id,
        message: "The calculation failed for these inputs. Check that xB < zF < xD and that the feed pressure is at or above the column pressure." });
    }
  }
};
