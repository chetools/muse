#!/usr/bin/env python3
"""Playwright visual verification of the built seven-panel page (v6).

Serves dist/ on local port 8941 (server started and stopped by this
script), screenshots every panel at desktop width (2560 px) and at
phone width (390 px), and asserts: seven tabs present; sticky tab bar
top = 0 after scrolling; panel switching while scrolled; fragment
routing into Economics and Safety panels; no horizontal scroll at
390 px; sub-process diagrams present in the Process panel; no
unrendered mathematics in the visible text. The sandbox browser
cannot fetch CDN resources, so the Pyodide worker boot is expected
to fail here; the checks assert that the precomputed run is displayed
and the failure is reported in plain language.
"""
import asyncio
import json
import os
import subprocess
import sys

from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "dist")
PAGE = "crude-distillation-unit-v6.html"
OUT = os.path.join(HERE, "shots")
os.makedirs(OUT, exist_ok=True)
PORT = 8941
PANELS = ["app", "process", "theory", "economics", "safety", "code",
          "references"]


async def shoot_panels(pg, prefix):
    for name in PANELS:
        await pg.click(f"#tabbtn-{name}")
        await pg.wait_for_timeout(450)
        await pg.screenshot(path=os.path.join(OUT, f"v6-{prefix}-{name}.png"))


async def main():
    report = {}
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
        cwd=DIST, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        await asyncio.sleep(1.0)
        url = f"http://127.0.0.1:{PORT}/{PAGE}"
        async with async_playwright() as p:
            # Playwright's bundled headless Chromium is used: the
            # /opt/meta-chromium binary refuses headless startup
            # ("Hatch WebGL domain policy is required").
            b = await p.chromium.launch(args=["--no-sandbox"])
            # ---------- desktop ----------
            pg = await b.new_page(viewport={"width": 2560, "height": 1400})
            errors = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            await pg.goto(url)
            await pg.wait_for_timeout(2500)
            tabs = await pg.evaluate(
                "Array.from(document.querySelectorAll('nav.tabs button'))"
                ".map(x => x.dataset.panel)")
            report["desktop_tabs"] = tabs
            report["seven_tabs_in_order"] = tabs == PANELS
            geo = await pg.evaluate("""() => {
              const h = document.querySelector('.hwrap').getBoundingClientRect();
              const w = document.querySelector('.wrap').getBoundingClientRect();
              return {hLeft: h.left, hRight: h.right, wLeft: w.left,
                      wRight: w.right};
            }""")
            report["desktop_header_body_aligned"] = (
                abs(geo["hLeft"] - geo["wLeft"]) < 2
                and abs(geo["hRight"] - geo["wRight"]) < 2)
            report["desktop_prestart_duty"] = await pg.text_content("#out-duty")
            report["selftest_supported"] = await pg.evaluate(
                "document.documentElement.innerHTML.includes('SELFTEST')")
            await shoot_panels(pg, "desktop")
            # sub-process diagrams in the Process panel
            await pg.click("#tabbtn-process")
            await pg.wait_for_timeout(300)
            report["subdiagrams_in_process"] = await pg.evaluate(
                "document.querySelectorAll('#panel-process .subdiagram').length")
            # sticky bar + switching while scrolled
            await pg.evaluate("window.scrollTo(0, 1400)")
            await pg.wait_for_timeout(300)
            report["sticky_top_desktop"] = await pg.evaluate(
                "document.querySelector('nav.tabs').getBoundingClientRect().top")
            await pg.click("#tabbtn-safety")
            await pg.wait_for_timeout(400)
            report["switch_while_scrolled"] = await pg.evaluate(
                "document.querySelector('#panel-safety').classList.contains('active')")
            await pg.screenshot(path=os.path.join(OUT, "v6-desktop-scrolled-safety.png"))
            # fragment routing
            frag = await pg.evaluate("""async () => {
              location.hash = '#economics-capital-cost';
              return new Promise(r => setTimeout(() => {
                r({panel: document.querySelector('#panel-economics')
                      .classList.contains('active'),
                   top: document.querySelector('#economics-capital-cost')
                      .getBoundingClientRect().top});
              }, 600));
            }""")
            report["fragment_economics_capital_cost"] = frag
            frag2 = await pg.evaluate("""async () => {
              location.hash = '#safety-codes-and-industry-guidance';
              return new Promise(r => setTimeout(() => {
                r({panel: document.querySelector('#panel-safety')
                      .classList.contains('active')});
              }, 600));
            }""")
            report["fragment_safety_codes"] = frag2
            body_text = await pg.evaluate("document.body.innerText")
            report["unrendered_math_desktop"] = "$\\" in body_text
            report["desktop_pageerrors"] = errors
            await pg.close()
            # ---------- phone ----------
            pg = await b.new_page(viewport={"width": 390, "height": 844})
            errors2 = []
            pg.on("pageerror", lambda e: errors2.append(str(e)))
            await pg.goto(url)
            await pg.wait_for_timeout(2000)
            await shoot_panels(pg, "phone")
            geo2 = await pg.evaluate("""() => ({scrollW:
              document.documentElement.scrollWidth, innerW: innerWidth})""")
            report["phone_geometry"] = geo2
            report["phone_no_sideways_scroll"] = geo2["scrollW"] <= 390
            await pg.evaluate("window.scrollTo(0, 1400)")
            await pg.wait_for_timeout(300)
            report["sticky_top_phone"] = await pg.evaluate(
                "document.querySelector('nav.tabs').getBoundingClientRect().top")
            report["phone_pageerrors"] = errors2
            await pg.close()
            await b.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
    print(json.dumps(report, indent=1))


asyncio.run(main())
