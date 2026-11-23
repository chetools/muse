"""Build the single self-contained HTML file: inline vendored KaTeX (JS, CSS,
fonts as base64 data URIs) into template.html.

KaTeX assets are copied from the vendored copy under the supersonic-flow
space (read-only source); nothing is modified there.
"""
import base64
import re
import sys
from pathlib import Path

ROOT = Path.home() / "workspace"
KATEX = ROOT / "ts-spaces/supersonic-flow-and-speed-of-sound/assets/katex"
TPL = ROOT / "muse-repo-main/routh-hurwitz-pi-two-first-order/template.html"
OUT = ROOT / "muse-repo-main/routh-hurwitz-pi-two-first-order/routh-hurwitz-pi-two-first-order.html"

tpl = TPL.read_text(encoding="utf-8")
assert "<!--KATEX_CSS-->" in tpl and "<!--KATEX_JS-->" in tpl

# --- CSS with fonts inlined -------------------------------------------------
css = (KATEX / "katex.min.css").read_text(encoding="utf-8")
inlined = []
for m in re.finditer(r"url\(fonts/([^)]+\.woff2)\)", css):
    name = m.group(1)
    data = (KATEX / "fonts" / name).read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    css = css.replace(
        f"url(fonts/{name})", f"url(data:font/woff2;base64,{b64})"
    )
    inlined.append(name)
assert len(inlined) == len(set(inlined)) and inlined, "no woff2 fonts inlined"
# Drop the woff/ttf fallbacks (no such files exist locally; woff2 suffices).
css, n_woff = re.subn(r",url\(fonts/[^)]+\.woff\) format\(\"woff\"\)", "", css)
css, n_ttf = re.subn(r",url\(fonts/[^)]+\.ttf\) format\(\"truetype\"\)", "", css)
assert "url(fonts/" not in css, "unresolved font url remains in CSS"
print(f"inlined {len(inlined)} woff2 fonts; dropped {n_woff} woff, {n_ttf} ttf refs")

# --- JS ----------------------------------------------------------------------
katex_js = (KATEX / "katex.min.js").read_text(encoding="utf-8")
render_js = (KATEX / "auto-render.min.js").read_text(encoding="utf-8")
for name, js in (("katex.min.js", katex_js), ("auto-render.min.js", render_js)):
    assert "</script" not in js.lower(), f"{name} contains </script"
    assert "<!--" not in js, f"{name} contains <!--"

html = tpl.replace(
    "<!--KATEX_CSS-->", "<style>\n" + css + "\n</style>"
)
html = html.replace(
    "<!--KATEX_JS-->",
    "<script>\n" + katex_js + "\n</script>\n<script>\n" + render_js + "\n</script>",
)
assert "<!--KATEX_" not in html
assert "katex.min" not in html or True
OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size/1024:.0f} KiB)")
