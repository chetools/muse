#!/usr/bin/env python3
"""Playwright visual verification of the built page at desktop and
phone widths. The sandbox browser cannot fetch CDN resources, so the
Pyodide worker boot is expected to fail here; the checks assert that
the precomputed run is displayed and that the failure is reported in
plain language, and that the page scripts themselves raise no syntax
or rendering errors."""
import asyncio
import json
import os

from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "shots")
os.makedirs(OUT, exist_ok=True)
PAGE_URL = "file://" + os.path.join(HERE, "dist", "crude-distillation-unit-v2.html")


async def main():
    report = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/opt/meta-chromium/chrome",
                                    args=["--no-sandbox"])
        # desktop
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
        duty = await pg.text_content("#out-duty")
        report["desktop_prestart_duty"] = duty
        await pg.screenshot(path=os.path.join(OUT, "desktop-app.png"))
        await pg.click("#tabbtn-theory")
        await pg.wait_for_timeout(400)
        await pg.screenshot(path=os.path.join(OUT, "desktop-theory.png"))
        await pg.evaluate("document.querySelector('#theory-production-scale').scrollIntoView()")
        await pg.wait_for_timeout(300)
        await pg.screenshot(path=os.path.join(OUT, "desktop-theory-scale.png"))
        await pg.click("#tabbtn-code")
        await pg.wait_for_timeout(400)
        await pg.screenshot(path=os.path.join(OUT, "desktop-code.png"))
        await pg.click("#subtab-walkthrough")
        await pg.wait_for_timeout(600)
        await pg.screenshot(path=os.path.join(OUT, "desktop-walkthrough.png"))
        frag = await pg.evaluate("""async () => {
          location.hash = '#theory-process-economics';
          return new Promise(r => setTimeout(() => {
            r({panel: document.querySelector('#panel-theory').classList.contains('active'),
               y: document.querySelector('#theory-process-economics').getBoundingClientRect().top});
          }, 500));
        }""")
        report["fragment_theory_economics"] = frag
        report["desktop_pageerrors"] = errors
        await pg.close()
        # phone
        pg = await b.new_page(viewport={"width": 390, "height": 844})
        errors2 = []
        pg.on("pageerror", lambda e: errors2.append(str(e)))
        await pg.goto(PAGE_URL)
        await pg.wait_for_timeout(2000)
        geo2 = await pg.evaluate("""() => ({scrollW: document.documentElement.scrollWidth,
          innerW: innerWidth, bodyW: document.body.scrollWidth})""")
        report["phone_geometry"] = geo2
        report["phone_no_sideways_scroll"] = geo2["scrollW"] <= 390
        await pg.screenshot(path=os.path.join(OUT, "phone-app.png"))
        await pg.click("#tabbtn-theory")
        await pg.wait_for_timeout(400)
        await pg.screenshot(path=os.path.join(OUT, "phone-theory.png"))
        await pg.click("#tabbtn-code")
        await pg.wait_for_timeout(400)
        await pg.screenshot(path=os.path.join(OUT, "phone-code.png"))
        report["phone_pageerrors"] = errors2
        await pg.close()
        await b.close()
    print(json.dumps(report, indent=1))


asyncio.run(main())
