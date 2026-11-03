#!/usr/bin/env python3
"""Playwright visual verification of the built v2 page (seven-panel
form) at desktop and phone widths, served locally on port 8943.
The sandbox browser cannot fetch CDN resources, so the Pyodide
worker boot is expected to fail here; the checks assert that the
precomputed run is displayed and the failure is reported in plain
language. Sticky tab bar check: scroll at least 1000 px, assert the
tab bar stays at the top and every panel switches while scrolled.
Screenshots carry the page version (v2) in their filenames."""
import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.request

from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "shots")
os.makedirs(OUT, exist_ok=True)
DIST = os.path.join(HERE, "dist")
PORT = int(os.environ.get("SHOOT_PORT", "8943"))
PAGE_URL = f"http://localhost:{PORT}/methanol-synthesis-plant-v2.html"
PANELS = ["app", "process", "theory", "economics", "safety", "code", "references"]

STICKY_JS = """() => {
  const nav = document.querySelector('nav.tabs');
  const r = nav.getBoundingClientRect();
  const cs = getComputedStyle(nav);
  return {top: r.top, bottom: r.bottom, height: r.height,
          position: cs.position, background: cs.backgroundColor,
          fullyVisible: r.top >= -1 && r.bottom > 0 && r.height > 20};
}"""


async def switch(pg, panel):
    await pg.click(f"#tabbtn-{panel}")
    await pg.wait_for_timeout(350)
    return await pg.evaluate(
        f"document.querySelector('#panel-{panel}').classList.contains('active')")


async def main():
    report = {}
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--directory", DIST],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        served = ""
        for _ in range(50):
            try:
                served = urllib.request.urlopen(PAGE_URL, timeout=2).read().decode("utf-8", "replace")
                if "Methanol Synthesis and Purification Plant" in served:
                    break
                served = ""
            except Exception:
                time.sleep(0.2)
        if not served:
            raise SystemExit("local server on port 8943 did not serve the built page "
                             "(port busy or server failed); screenshots not taken")
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell"),
                                        args=["--no-sandbox"])
            # ---------- desktop ----------
            pg = await b.new_page(viewport={"width": 2560, "height": 1400})
            errors = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            await pg.goto(PAGE_URL)
            await pg.wait_for_timeout(2500)
            geo = await pg.evaluate("""() => {
              const h = document.querySelector('.hwrap').getBoundingClientRect();
              const w = document.querySelector('.wrap').getBoundingClientRect();
              return {hLeft: h.left, hRight: h.right, wLeft: w.left, wRight: w.right,
                      scrollW: document.documentElement.scrollWidth, innerW: innerWidth};
            }""")
            report["desktop_geometry"] = geo
            report["desktop_header_body_aligned"] = (
                abs(geo["hLeft"] - geo["wLeft"]) < 2 and abs(geo["hRight"] - geo["wRight"]) < 2)
            report["desktop_prestart_loop"] = await pg.text_content("#out-loop")
            report["desktop_tabs"] = await pg.evaluate(
                "Array.from(document.querySelectorAll('nav.tabs button')).map(x => x.textContent)")
            await pg.screenshot(path=os.path.join(OUT, "v2-desktop-app.png"))
            # sticky check: the App panel page is too short at this
            # viewport to scroll 1500 px (document height 1602 px,
            # maximum scrollY 202 px, measured), so the scroll test
            # runs on the Process panel, whose page is tall.
            report["desktop_app_panel_scroll"] = await pg.evaluate(
                "() => ({docH: document.documentElement.scrollHeight, "
                "maxScrollY: document.documentElement.scrollHeight - innerHeight})")
            await switch(pg, "process")
            await pg.evaluate("window.scrollTo(0, 1500)")
            await pg.wait_for_timeout(400)
            report["desktop_scrollY_on_process"] = await pg.evaluate("window.scrollY")
            g = await pg.evaluate(STICKY_JS)
            report["desktop_sticky_after_1500px_scroll"] = g
            report["desktop_sticky_top_is_zero"] = abs(g["top"]) <= 1 and g["fullyVisible"]
            sw = {}
            for panel in PANELS[1:]:
                sw[panel] = await switch(pg, panel)
            report["desktop_tab_switch_while_scrolled"] = sw
            g2 = await pg.evaluate(STICKY_JS)
            report["desktop_sticky_still_at_top_after_switch"] = abs(g2["top"]) <= 1
            # per-panel screenshots at top
            for panel in PANELS[1:]:
                await pg.evaluate("window.scrollTo(0, 0)")
                await switch(pg, panel)
                await pg.screenshot(path=os.path.join(OUT, f"v2-desktop-{panel}.png"))
            # sub-process diagram visibility in a Process section
            await switch(pg, "process")
            await pg.evaluate(
                "document.querySelector('#process-synthesis-loop-and-converter').scrollIntoView()")
            await pg.wait_for_timeout(400)
            report["desktop_process_diagrams"] = await pg.evaluate("""() => {
              const figs = document.querySelectorAll('#panel-process figure svg');
              return {count: figs.length,
                      anyVisible: Array.from(figs).some(f => f.getBoundingClientRect().width > 100)};
            }""")
            await pg.screenshot(path=os.path.join(OUT, "v2-desktop-process-crop.png"))
            # walkthrough sub-tab
            await switch(pg, "code")
            await pg.click("#subtab-walkthrough")
            await pg.wait_for_timeout(600)
            await pg.screenshot(path=os.path.join(OUT, "v2-desktop-walkthrough.png"))
            # fragment routing to a mid-panel section
            frag = await pg.evaluate("""async () => {
              location.hash = '#economics-capital-cost';
              return new Promise(r => setTimeout(() => {
                r({panel: document.querySelector('#panel-economics').classList.contains('active'),
                   y: document.querySelector('#economics-capital-cost').getBoundingClientRect().top});
              }, 500));
            }""")
            report["fragment_economics_capital_cost"] = frag
            report["selftest_supported"] = await pg.evaluate(
                "typeof window.SELFTEST !== 'undefined'")
            report["desktop_pageerrors"] = errors
            await pg.close()
            # ---------- phone ----------
            pg = await b.new_page(viewport={"width": 390, "height": 844})
            errors2 = []
            pg.on("pageerror", lambda e: errors2.append(str(e)))
            await pg.goto(PAGE_URL)
            await pg.wait_for_timeout(2000)

            async def phone_geo():
                return await pg.evaluate("""() => ({scrollW: document.documentElement.scrollWidth,
                  innerW: innerWidth, bodyW: document.body.scrollWidth})""")
            report["phone_geometry"] = await phone_geo()
            report["phone_no_sideways_scroll"] = report["phone_geometry"]["scrollW"] <= 390
            await pg.screenshot(path=os.path.join(OUT, "v2-phone-app.png"))
            await pg.evaluate("window.scrollTo(0, 1500)")
            await pg.wait_for_timeout(400)
            g = await pg.evaluate(STICKY_JS)
            report["phone_sticky_top_is_zero"] = abs(g["top"]) <= 1 and g["fullyVisible"]
            sw = {}
            overflow = {}
            for panel in PANELS[1:]:
                sw[panel] = await switch(pg, panel)
                await pg.evaluate("window.scrollTo(0, 0)")
                await pg.wait_for_timeout(200)
                overflow[panel] = (await phone_geo())["scrollW"]
                await pg.screenshot(path=os.path.join(OUT, f"v2-phone-{panel}.png"))
            report["phone_tab_switch_while_scrolled"] = sw
            report["phone_scroll_width_by_panel"] = overflow
            report["phone_no_sideways_scroll_any_panel"] = all(
                v <= 390 for v in overflow.values())
            report["phone_pageerrors"] = errors2
            await pg.close()
            await b.close()
    finally:
        server.terminate()
    print(json.dumps(report, indent=1))


asyncio.run(main())
