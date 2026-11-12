// Hand-rolled loader for the vendored rusty-chromaprint-wasm bg files,
// as the static webapp will load them (no bundler).
import { readFileSync } from 'node:fs';
import * as bg from 'rusty-chromaprint-wasm/dist/rusty_chromaprint_wasm_bg.js';
const bytes = readFileSync('node_modules/rusty-chromaprint-wasm/dist/rusty_chromaprint_wasm_bg.wasm');
const mod = new WebAssembly.Module(bytes);
const importModules = [...new Set(WebAssembly.Module.imports(mod).map(i => i.module))];
console.log('wasm import modules:', JSON.stringify(importModules));
const imports = {};
for (const m of importModules) imports[m] = bg;
const instance = await WebAssembly.instantiate(mod, imports);
bg.__wbg_set_wasm(instance.exports);
instance.exports.__wbindgen_start();
function pcm(path) {
  const buf = readFileSync(path);
  return new Int16Array(buf.buffer, buf.byteOffset, buf.length / 2);
}
const res = bg.fingerprintFromSamples(16000, 1, pcm('speech-a.raw'));
console.log('loader fingerprint items:', res.raw.length, 'compressed chars:', res.compressed.length);
const ref = JSON.parse(readFileSync('rusty-a.json', 'utf8'));
console.log('raw identical to direct-import run:', JSON.stringify(Array.from(res.raw)) === JSON.stringify(ref));
