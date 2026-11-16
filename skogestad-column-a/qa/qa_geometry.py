"""Geometry + precomputed-display QA with a slow-stubbed boot.

The Pyodide CDN request is stubbed so the runtime never becomes
ready: the page must show its precomputed display, correctly
sized, at 2560, 1280 and 390 px, on every tab.
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent
OUT = ROOT / "qa"
URL = "http://127.0.0.1:8931/skogestad-column-a-standalone-v2.html"

STUB = """
window.loadPyodide = () => new Promise(() => {});
"""

GEOM_JS = """
() => {
  const out = {scrollW: document.documentElement.scrollWidth,
               innerW: window.innerWidth, charts: [], overlaps: []};
  const vis = [...document.querySelectorAll('.chart, .walkfig')]
    .filter(d => d.offsetParent !== null &&
                 d.querySelector('svg.main-svg'));
  for (const d of vis) {
    const svg = d.querySelector('svg.main-svg');
    out.charts.push({id: d.id,
      svgW: Math.round(svg.getBoundingClientRect().width),
      boxW: Math.round(d.getBoundingClientRect().width)});
  }
  for (let i = 0; i < vis.length; i++)
    for (let j = i + 1; j < vis.length; j++) {
      const a = vis[i].getBoundingClientRect(),
            b = vis[j].getBoundingClientRect();
      const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (ox > 2 && oy > 2) out.overlaps.push([vis[i].id, vis[j].id]);
    }
  return out;
}
"""


def main():
    report = {"widths": {}}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in (2560, 1280, 390):
            page = browser.new_page(viewport={"width": width,
                                              "height": 1000})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e))
                    if "importScripts" not in str(e) else None)
            page.route("**/pyodide.js", lambda r: r.fulfill(
                content_type="text/javascript", body=STUB))
            page.goto(URL)
            page.wait_for_timeout(1200)
            w = {"tabs": {}}
            assert page.locator(
                "#chart-profile svg.main-svg").count() >= 1
            app_text = page.locator("#panel-app").inner_text()
            assert "precomputed" in app_text.lower(), \
                "precomputed label missing on App"
            for tab in ("app", "analysis", "theory", "code"):
                page.click(f'[data-tab="{tab}"]')
                page.wait_for_timeout(500)
                if tab == "code":
                    page.click('[data-subtab="walkthrough"]')
                    page.wait_for_timeout(500)
                    walk_text = page.locator(
                        "#sub-walkthrough").text_content()
                    assert "anchor xD = 0.99" in walk_text, \
                        "walkthrough Step 5 anchor xD is not 0.9900"
                    assert "balance closure" in walk_text
                    assert "deflated-system residuals" in walk_text
                    w["walkthrough_step5"] = "anchor xD = 0.9900 shown"
                g = page.evaluate(GEOM_JS)
                bad = [c for c in g["charts"]
                       if abs(c["svgW"] - c["boxW"]) > 2]
                w["tabs"][tab] = {"geometry": g, "bad_charts": bad}
                assert not bad, (width, tab, bad)
                assert g["scrollW"] <= g["innerW"], (width, tab, g)
                assert not g["overlaps"], (width, tab, g["overlaps"])
                page.screenshot(path=str(OUT / f"{width}-{tab}.png"),
                                full_page=False)
            # header/body edge alignment at this width
            edges = page.evaluate("""
              () => { const c = document.querySelector('.col')
                        .getBoundingClientRect();
                      const h = document.querySelector('header.head')
                        .getBoundingClientRect();
                      return {colL: c.left, colR: c.right,
                              headL: h.left, headR: h.right}; }""")
            w["edges"] = edges
            w["pageerrors"] = errors
            assert not errors, (width, errors)
            report["widths"][width] = w
            page.close()
        browser.close()
    (OUT / "geometry_report.json").write_text(json.dumps(report,
                                                         indent=1))
    print("GEOMETRY QA PASS (2560/1280/390, all tabs, precomputed "
          "display, no overlaps, no page errors)")


if __name__ == "__main__":
    main()
