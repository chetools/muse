import { readFileSync, writeFileSync } from 'node:fs';
import init, { fingerprint } from 'chromaprint-web';
const wasmBytes = readFileSync(new URL('node_modules/chromaprint-web/chromaprint_web_bg.wasm', import.meta.url));
const t0 = Date.now();
await init({ module_or_path: wasmBytes });
console.log('init ms:', Date.now() - t0);
function pcm(path) {
  const buf = readFileSync(path);
  return new Int16Array(buf.buffer, buf.byteOffset, buf.length / 2);
}
for (const [name, file] of [['a','speech-a.raw'],['b','speech-b.raw'],['aac','speech-a-aac.raw']]) {
  const s = pcm(file);
  const t1 = Date.now();
  const fp = fingerprint(16000, s);
  console.log(name, 'ms:', Date.now() - t1, 'compressed chars:', fp.length);
  writeFileSync(`web-${name}.txt`, fp);
}
