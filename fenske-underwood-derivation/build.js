const fs = require('fs');
const path = require('path');

const DIR = __dirname;
const KATEX_DIR = '/home/hatch/workspace/pbsid-derivations/katex-build/node_modules/katex';
const katex = require(KATEX_DIR);

let html = fs.readFileSync(path.join(DIR, 'content.frag'), 'utf8');

let displayCount = 0, inlineCount = 0;
const failures = [];

function render(src, displayMode, context) {
  try {
    return katex.renderToString(src, { displayMode, throwOnError: true, trust: false, strict: true });
  } catch (e) {
    failures.push({ context: context.slice(0, 60), error: String(e).split('\n')[0], src: src.slice(0, 120) });
    return null;
  }
}

html = html.replace(/\$\$(.+?)\$\$/gs, (m, src) => {
  const out = render(src, true, m);
  if (out === null) return m;
  displayCount++;
  return out;
});

html = html.replace(/\\\((.+?)\\\)/gs, (m, src) => {
  const out = render(src, false, m);
  if (out === null) return m;
  inlineCount++;
  return out;
});

if (failures.length) {
  console.error('KATEX FAILURES:');
  failures.forEach(f => console.error(' -', f.error, '| ctx:', f.context, '| src:', f.src));
  process.exit(1);
}

for (const bad of ['$$', '\\(', '\\)']) {
  if (html.includes(bad)) { console.error('LEFTOVER DELIMITER:', JSON.stringify(bad)); process.exit(1); }
}
if (html.includes('katex-error')) { console.error('KATEX ERROR ELEMENT PRESENT'); process.exit(1); }

let css = fs.readFileSync(path.join(KATEX_DIR, 'dist', 'katex.min.css'), 'utf8');
const fontsDir = path.join(KATEX_DIR, 'dist', 'fonts');
css = css.replace(/@font-face\s*{[^}]*}/g, (block) => {
  const m = block.match(/url\(fonts\/([A-Za-z0-9_.-]+)\.woff2\)/);
  if (!m) return block;
  const fp = path.join(fontsDir, m[1] + '.woff2');
  if (!fs.existsSync(fp)) return block;
  const b64 = fs.readFileSync(fp).toString('base64');
  return block.replace(/src:[^;}]+/, `src:url(data:font/woff2;base64,${b64}) format("woff2")`);
});
if (/url\(fonts\//.test(css)) { console.error('UNRESOLVED FONT URL IN CSS'); process.exit(1); }

const page = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Derivation of the Fenske Equation and the Underwood Equations for Minimum Reflux</title>
<style>
${css}
body { font-family: Georgia, 'Times New Roman', serif; line-height: 1.65; color: #1a1a1a; max-width: 840px; margin: 0 auto; padding: 24px 20px 64px; background: #fff; }
h1 { font-size: 1.65em; line-height: 1.3; margin-bottom: 0.15em; }
.subtitle { color: #555; margin-top: 0; font-style: italic; }
h2 { font-size: 1.25em; margin-top: 2em; border-bottom: 1px solid #ddd; padding-bottom: 0.25em; }
table.notation { border-collapse: collapse; width: 100%; font-size: 0.92em; margin: 1em 0; }
table.notation th, table.notation td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; vertical-align: top; }
table.notation th { background: #f4f4f4; }
.katex-display { margin: 1.1em 0; overflow-x: auto; overflow-y: hidden; }
ul, ol { padding-left: 1.4em; }
li { margin-bottom: 0.4em; }
nav.contents { background: #f8f8f8; border: 1px solid #e2e2e2; padding: 12px 20px; margin: 1.5em 0; }
nav.contents .contents-title { font-weight: bold; margin: 0 0 0.4em 0; }
nav.contents ol { margin: 0; }
nav.contents li { margin-bottom: 0.15em; }
figure { margin: 1.5em 0; }
figcaption { font-size: 0.92em; color: #333; margin-top: 0.6em; }
.summarybox { background: #f8f8f8; border: 1px solid #ddd; padding: 6px 18px; }
.refs li { margin-bottom: 0.5em; }
.footer { margin-top: 3em; color: #777; font-size: 0.85em; border-top: 1px solid #ddd; padding-top: 1em; }
</style>
</head>
<body>
${html}
<div class="footer">Rendered ${new Date().toISOString().slice(0,10)}. KaTeX rendered server-side; this file has no external dependencies.</div>
</body>
</html>`;

const outPath = path.join(DIR, 'fenske-underwood-derivation.html');
fs.writeFileSync(outPath, page);
console.log(`OK: ${displayCount} display + ${inlineCount} inline equations rendered -> ${outPath} (${(fs.statSync(outPath).size/1024).toFixed(0)} KB)`);
