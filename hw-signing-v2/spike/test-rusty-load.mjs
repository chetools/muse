const t0 = Date.now();
await import('rusty-chromaprint-wasm');
console.log('import ms (fresh process):', Date.now() - t0);
