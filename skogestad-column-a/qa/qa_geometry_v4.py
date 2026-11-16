"""Geometry + precomputed-display QA for v4, slow-stubbed boot.

Adapted from qa_geometry_v3.py. Differences for v4:
- URL points at the v4 standalone page; screenshots and the
  report carry v4 names.
- Added v4 check per width: on the Analysis tab, before any
  fit (the boot is stubbed, so no live run can occur), the
  #chart-channel area shows the channel-overlay placeholder
  text and contains no svg.
- Theory is now the landing panel and panel-app is hidden on
  load, so the App precomputed text and the '#chart-profile svg'
  existence assert run AFTER clicking the App tab (inner_text of
  a hidden panel is empty).
- Added landing checks per width: tab button order in the DOM
  (Theory, App, Analysis, Code), Theory visible / others hidden
  on fresh load, and the Theory table of contents entries.
- Added guide pop-up checks per width: each of the four Guide
  buttons opens its pop-up, a screenshot of the first pop-up is
  taken, the pop-up is dismissed via its Close button, and at
  390 px a pop-up open must not cause sideways scroll.
All v2 checks are kept: chart svg width == container (+/-2 px)
on visible charts, no overlaps, no sideways scroll per tab,
header/body edge alignment recorded, walkthrough Step 5
asserts, zero page errors.
"""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent
OUT = ROOT / "qa"
URL = "http://127.0.0.1:8931/skogestad-column-a-standalone-v4.html"

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

POP_STATE_JS = """
(id) => {
  const el = document.getElementById(id);
  if (!el) return {found: false};
  let popOpen = false;
  try { popOpen = el.matches(':popover-open'); } catch (e) {}
  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  return {found: true, popOpen: popOpen, display: cs.display,
          hidden: el.hidden, openClass: el.classList.contains('open'),
          w: Math.round(r.width), h: Math.round(r.height)};
}
"""


def pop_visible(state):
    """A pop-up counts as visible when it is open as a native
    popover, or (fallback route) displayed with real size."""
    if not state.get("found"):
        return False
    if state.get("popOpen"):
        return True
    return (state.get("display") not in (None, "none")
            and not state.get("hidden")
            and state.get("w", 0) > 0 and state.get("h", 0) > 0)


TOC_REQUIRED = ["Introduction", "Relevance",
                "Key points to be demonstrated",
                "How this is demonstrated", "Guided experiments",
                "13. Conclusion and discussion"]
GUIDES = ["guide-column", "guide-config", "guide-step",
          "guide-results"]


def main():
    report = {"widths": {}}
    failures = []
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

            # ---- landing checks (fresh load, Theory first) ----
            order = page.evaluate(
                "[...document.querySelectorAll('#tabbar .tabbtn')]"
                ".map(b => b.dataset.tab)")
            labels = page.evaluate(
                "[...document.querySelectorAll('#tabbar .tabbtn')]"
                ".map(b => b.textContent.trim())")
            landing = {"tab_order": order, "tab_labels": labels}
            assert order == ["theory", "app", "analysis", "code"], \
                (width, "tab order", order)
            assert labels == ["Theory", "App", "Analysis", "Code"], \
                (width, "tab labels", labels)
            vis = {t: page.locator(f"#panel-{t}").is_visible()
                   for t in ("theory", "app", "analysis", "code")}
            landing["panel_visible_on_load"] = vis
            assert vis["theory"] is True, (width, "theory hidden", vis)
            for t in ("app", "analysis", "code"):
                assert vis[t] is False, (width, f"{t} visible", vis)
            toc_text = page.locator("#theory-toc").inner_text()
            landing["toc_text"] = toc_text
            for entry in TOC_REQUIRED:
                assert entry in toc_text, \
                    (width, "TOC entry missing", entry)
            landing["toc_required_present"] = TOC_REQUIRED
            w["landing"] = landing

            # ---- App precomputed display (after showing App) ----
            page.click('[data-tab="app"]')
            page.wait_for_timeout(500)
            assert page.locator(
                "#chart-profile svg.main-svg").count() >= 1, \
                (width, "chart-profile svg missing after App shown")
            app_text = page.locator("#panel-app").inner_text()
            assert "precomputed" in app_text.lower(), \
                "precomputed label missing on App"

            # ---- per-tab geometry (all v2 checks kept) ----
            for tab in ("theory", "app", "analysis", "code"):
                page.click(f'[data-tab="{tab}"]')
                page.wait_for_timeout(500)
                if tab == "analysis":
                    ch_text = page.locator(
                        "#chart-channel").inner_text()
                    ch_svg = page.locator(
                        "#chart-channel svg").count()
                    w["channel_placeholder"] = ch_text.strip()
                    assert "No channel overlay yet" in ch_text, \
                        (width, "channel placeholder missing",
                         ch_text[:120])
                    assert ch_svg == 0, (width, "channel svg in "
                                         "precomputed paint")
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
                page.screenshot(
                    path=str(OUT / f"v4-{width}-{tab}.png"),
                    full_page=False)

            # ---- guide pop-up checks ----
            page.click('[data-tab="app"]')
            page.wait_for_timeout(500)
            pops = {}
            for idx, target in enumerate(GUIDES):
                btn = page.locator(
                    f'button.guidebtn[popovertarget="{target}"]')
                assert btn.count() == 1, (width, target, "guide btn")
                btn.first.scroll_into_view_if_needed()
                btn.first.click()
                page.wait_for_timeout(400)
                state = page.evaluate(POP_STATE_JS, target)
                pops[target] = {"open_state": state}
                assert pop_visible(state), \
                    (width, target, "pop-up not visible", state)
                if idx == 0:
                    page.screenshot(
                        path=str(OUT / f"v4-{width}-popup.png"),
                        full_page=False)
                if width == 390:
                    sw = page.evaluate(
                        "({sw: document.documentElement.scrollWidth,"
                        " iw: window.innerWidth})")
                    pops[target]["scroll_390"] = sw
                    assert sw["sw"] <= sw["iw"], \
                        (width, target, "sideways scroll w/ pop-up", sw)
                close = page.locator(f"#{target} button.guideclose")
                assert close.count() == 1, (width, target, "close btn")
                close.first.click()
                page.wait_for_timeout(400)
                state2 = page.evaluate(POP_STATE_JS, target)
                pops[target]["closed_state"] = state2
                assert not pop_visible(state2), \
                    (width, target, "pop-up still visible", state2)
            w["popups"] = pops

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
    (OUT / "geometry_report_v4.json").write_text(
        json.dumps(report, indent=1))
    print("GEOMETRY QA V4 PASS (2560/1280/390, landing order + "
          "Theory-first visibility + TOC, all tabs, precomputed "
          "display, guide pop-ups, no overlaps, no page errors)")


if __name__ == "__main__":
    main()
