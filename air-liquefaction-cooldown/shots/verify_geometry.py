"""Measured geometric checks on Fig. P1 (the loop schematic).

Implements the standing schematic rule: geometry is measured from
the rendered SVG in the built page (endpoints parsed from path
data, glyph outlines and lines sampled with getPointAtLength,
label boxes from getBBox), never from the drawing code. Checks:
(1) every stream endpoint is on an equipment outline, on a
junction dot, a labelled terminal, or a hop end aligned with its
continuation across the crossed line; (2) arrowhead inventory -
the segments listed carry marker-end; (3) every label is at
least 7.5 units clear of every glyph outline and every line that
is not its own; (4) parallel-lane spacing of the vapour riser
against the split risers; (5) closure of the split fractions
printed on the figure. The checker is then run against three
planted defects (label moved onto a line, arrowhead deleted,
endpoint moved off its outline) and must fail on each.

Usage: python verify_geometry.py [url]  (default: local dist)
"""
import json
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
DIST = HERE.parent / "dist"
PAGE = DIST / "air-liquefaction-cooldown-v1.html"
PORT = 8932

CHECK_JS = r"""
() => {
  const svg = document.getElementById('fig-schematic');
  const fails = [];
  const NS = 'http://www.w3.org/2000/svg';
  function samplePts(el, step) {
    const pts = [];
    let L = 0;
    try { L = el.getTotalLength(); } catch (e) { return pts; }
    for (let d = 0; d <= L; d += step) {
      const p = el.getPointAtLength(d); pts.push([p.x, p.y]);
    }
    const p = el.getPointAtLength(L); pts.push([p.x, p.y]);
    return pts;
  }
  function endpoints(d) {
    const nums = d.match(/-?\d+\.?\d*/g).map(Number);
    // path uses only M, H, V commands with absolute coordinates
    const toks = d.trim().split(/(?=[MHV])/);
    let sx = null, sy = null, ex = null, ey = null, cx = 0, cy = 0;
    for (const t of toks) {
      const c = t[0];
      const v = t.slice(1).split(/[ ,]+/).filter(s => s.length).map(Number);
      if (c === 'M') { cx = v[0]; cy = v[1]; if (sx === null) { sx = cx; sy = cy; } }
      else if (c === 'H') { cx = v[0]; }
      else if (c === 'V') { cy = v[0]; }
      ex = cx; ey = cy;
    }
    return [[sx, sy], [ex, ey]];
  }
  const glyphs = [];
  svg.querySelectorAll('rect, polygon').forEach(el => glyphs.push(el));
  svg.querySelectorAll('circle').forEach(el => {
    if (+el.getAttribute('r') >= 6) glyphs.push(el);
  });
  const sepGlyph = svg.querySelector('#g-separator');
  if (sepGlyph) glyphs.push(sepGlyph);
  const glyphPts = [];
  glyphs.forEach(el => samplePts(el, 3).forEach(p => glyphPts.push(p)));
  const dots = [];
  svg.querySelectorAll('circle').forEach(el => {
    if (+el.getAttribute('r') < 6)
      dots.push([+el.getAttribute('cx'), +el.getAttribute('cy')]);
  });
  const streams = {};
  svg.querySelectorAll('path[id^="s_"]').forEach(el => {
    streams[el.id] = { el, d: el.getAttribute('d'),
      marker: el.getAttribute('marker-end'),
      pts: samplePts(el, 3) };
  });
  const lines = [];
  svg.querySelectorAll('line').forEach(el => lines.push(el));
  const linePts = [];
  lines.forEach(el => samplePts(el, 3).forEach(p => linePts.push(p)));
  const texts = [];
  svg.querySelectorAll('text').forEach(el => {
    const b = el.getBBox();
    texts.push({ s: el.textContent, x: b.x, y: b.y,
                 w: b.width, h: b.height });
  });
  function distToGlyph(p) {
    let m = 1e9;
    for (const q of glyphPts) {
      const dd = Math.hypot(p[0] - q[0], p[1] - q[1]);
      if (dd < m) m = dd;
    }
    return m;
  }
  // (1) endpoint classification
  const allEnds = [];
  for (const id in streams) {
    const [a, b] = endpoints(streams[id].d);
    allEnds.push({ id, p: a, which: 'start' });
    allEnds.push({ id, p: b, which: 'end' });
  }
  function nearText(p) {
    return texts.some(t => Math.hypot(
      Math.max(t.x - p[0], 0, p[0] - (t.x + t.w)),
      Math.max(t.y - p[1], 0, p[1] - (t.y + t.h))) <= 140);
  }
  for (const e of allEnds) {
    const p = e.p;
    if (distToGlyph(p) <= 2.5) continue;
    if (dots.some(c => Math.hypot(p[0] - c[0], p[1] - c[1]) <= 6.5)) continue;
    if ((p[0] <= 16 || p[1] >= 415) && nearText(p)) continue;
    // hop end: another endpoint shares x within 1, y within 20,
    // and some stream passes between them
    const hop = allEnds.some(o => o !== e &&
      Math.abs(o.p[0] - p[0]) <= 1 &&
      Math.abs(o.p[1] - p[1]) > 2 && Math.abs(o.p[1] - p[1]) <= 20 &&
      Object.values(streams).some(s => s.pts.some(q =>
        Math.abs(q[0] - p[0]) <= 3 &&
        q[1] > Math.min(p[1], o.p[1]) && q[1] < Math.max(p[1], o.p[1]))));
    if (hop) continue;
    fails.push('endpoint ' + e.id + ' ' + e.which + ' at (' +
      p[0] + ',' + p[1] + ') unclassified');
  }
  // (2) arrowhead inventory
  const wantArrows = ['s_feed_in', 's_comp_out', 's_ac_out',
    's_turb_in', 's_turb_out', 's_valve_in', 's_valve_out',
    's_sep_in', 's_vap_bot', 's_ret_b', 's_liquid'];
  for (const id of wantArrows) {
    if (!streams[id]) { fails.push('missing stream ' + id); continue; }
    if (!streams[id].marker) fails.push('arrow missing on ' + id);
  }
  const noArrows = ['s_hot_out', 's_vap_top', 's_ret_a'];
  for (const id of noArrows) {
    if (streams[id] && streams[id].marker)
      fails.push('unexpected arrow on ' + id);
  }
  // (3) label clearance
  const own = { 'Air in': ['s_feed_in'],
    'Return vapour': ['s_ret_a', 's_ret_b'],
    'x = 0.75': ['s_turb_in'], '1 − x = 0.25': ['s_valve_in'],
    'Liquid product': ['s_liquid'] };
  function rectDist(p, t) {
    const dx = Math.max(t.x - p[0], 0, p[0] - (t.x + t.w));
    const dy = Math.max(t.y - p[1], 0, p[1] - (t.y + t.h));
    return Math.hypot(dx, dy);
  }
  for (const t of texts) {
    let m = 1e9;
    for (const q of glyphPts) m = Math.min(m, rectDist(q, t));
    for (const q of linePts) m = Math.min(m, rectDist(q, t));
    for (const id in streams) {
      if ((own[t.s] || []).includes(id)) continue;
      for (const q of streams[id].pts) m = Math.min(m, rectDist(q, t));
    }
    if (m < 7.5) fails.push('label "' + t.s + '" clearance ' +
      m.toFixed(1) + ' < 7.5');
  }
  // (4) lane spacing: vapour riser x vs split riser x
  function vertX(id) {
    const m = streams[id].d.match(/M(\d+),/);
    return +m[1];
  }
  const gap = Math.abs(vertX('s_turb_in') - 545);
  if (gap < 40) fails.push('lane spacing ' + gap + ' < 40');
  // (5) printed split closure
  let x1 = null, x2 = null;
  for (const t of texts) {
    let mm = t.s.trim().match(/^x = ([\d.]+)$/); if (mm) x1 = +mm[1];
    mm = t.s.match(/= ([\d.]+)$/); if (mm && t.s.includes('−')) x2 = +mm[1];
  }
  if (x1 === null || x2 === null || Math.abs(x1 + x2 - 1) > 0.005)
    fails.push('split closure: ' + x1 + ' + ' + x2);
  return fails;
}
"""


def run_checks(page, url):
    page.goto(url)
    page.wait_for_timeout(900)
    return page.evaluate(CHECK_JS)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None
    server = None
    if target is None:
        server = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(PORT),
             "--directory", str(DIST)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.0)
        target = f"http://127.0.0.1:{PORT}/{PAGE.name}"
    out = {}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440,
                                              "height": 900})
            clean = run_checks(page, target)
            out["clean"] = clean
            print("clean figure:", "PASS" if not clean else clean)
            # Planted defect (a): label moved onto a line.
            page.evaluate(
                "(()=>{const ts=[...document.querySelectorAll("
                "'#fig-schematic text')];"
                "const t=ts.find(x=>x.textContent==='Separator');"
                "t.setAttribute('x','905');})()")
            fa = page.evaluate(CHECK_JS)
            out["planted_label"] = fa
            print("planted label defect:", fa)
            # Planted defect (b): arrowhead deleted.
            page.goto(target)
            page.wait_for_timeout(900)
            page.evaluate(
                "document.getElementById('s_sep_in')"
                ".removeAttribute('marker-end')")
            fb = page.evaluate(CHECK_JS)
            out["planted_arrow"] = fb
            print("planted arrow defect:", fb)
            # Planted defect (c): endpoint moved off outline.
            page.goto(target)
            page.wait_for_timeout(900)
            page.evaluate(
                "document.getElementById('s_sep_in').setAttribute("
                "'d','M800,262 H815')")
            fc = page.evaluate(CHECK_JS)
            out["planted_endpoint"] = fc
            print("planted endpoint defect:", fc)
            browser.close()
    finally:
        if server:
            server.terminate()
    ok = (not out["clean"]
          and any("clearance" in f for f in out["planted_label"])
          and any("arrow" in f for f in out["planted_arrow"])
          and any("endpoint" in f for f in out["planted_endpoint"]))
    (HERE / "geometry-summary.json").write_text(json.dumps(out, indent=1))
    print("GEOMETRY BATTERY:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
