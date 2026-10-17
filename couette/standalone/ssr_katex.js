// Server-side KaTeX rendering for the Distill demo build.
// Same katex package, options, and replacement logic as build.js / build3d.js
// (the project's proven convention): <span class="m"> -> inline math,
// <div class="dm"> -> display math wrapped in <div class="eq">.
// Usage: node ssr_katex.js <input.html> <output.html>
// Exits nonzero if any expression fails to render (throwOnError: true).
const fs = require('fs');
const katex = require('/home/hatch/workspace/pbsid-tutorial/build/node_modules/katex');

const [inPath, outPath] = process.argv.slice(2);
if (!inPath || !outPath) { console.error('usage: node ssr_katex.js <in> <out>'); process.exit(2); }

let body = fs.readFileSync(inPath, 'utf8');

function unescapeHtml(s) {
  return s.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
}

let inlineCount = 0, displayCount = 0;
const errors = [];

body = body.replace(/<span class="m">([\s\S]*?)<\/span>/g, (m, tex) => {
  inlineCount++;
  try {
    return katex.renderToString(unescapeHtml(tex), { displayMode: false, throwOnError: true, strict: false, trust: true });
  } catch (e) { errors.push('INLINE: ' + tex.slice(0, 80) + ' :: ' + e.message); return '<span class="katex-error">' + tex + '</span>'; }
});
body = body.replace(/<div class="dm">([\s\S]*?)<\/div>/g, (m, tex) => {
  displayCount++;
  try {
    return '<div class="eq">' + katex.renderToString(unescapeHtml(tex), { displayMode: true, throwOnError: true, strict: false, trust: true }) + '</div>';
  } catch (e) { errors.push('DISPLAY: ' + tex.slice(0, 80) + ' :: ' + e.message); return '<div class="katex-error">' + tex + '</div>'; }
});

fs.writeFileSync(outPath, body);
console.log(`katex inline=${inlineCount} display=${displayCount} errors=${errors.length}`);
errors.forEach(e => console.error('KATEX ERROR: ' + e));
if (errors.length) process.exit(1);
