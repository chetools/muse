import { readFileSync, writeFileSync } from 'node:fs';
import { fingerprintFromSamples } from 'rusty-chromaprint-wasm';
function pcm(path) {
  const buf = readFileSync(path);
  return new Int16Array(buf.buffer, buf.byteOffset, buf.length / 2);
}
const t0 = Date.now();
for (const [name, file] of [['a','speech-a.raw'],['b','speech-b.raw'],['aac','speech-a-aac.raw']]) {
  const s = pcm(file);
  const t1 = Date.now();
  const res = fingerprintFromSamples(16000, 1, s);
  const ms = Date.now() - t1;
  console.log(name, 'samples:', s.length, 'raw items:', res.raw.length, 'ms:', ms, 'compressed chars:', res.compressed.length);
  writeFileSync(`rusty-${name}.json`, JSON.stringify(Array.from(res.raw)));
}
console.log('total ms:', Date.now() - t0);
