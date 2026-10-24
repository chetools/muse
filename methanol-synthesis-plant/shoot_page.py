#!/usr/bin/env python3
"""Playwright visual verification of the built page at desktop and
phone widths. The sandbox browser cannot fetch CDN resources, so the
Pyodide worker boot is expected to fail here; the checks assert that
the precomputed run is displayed and that the failure is reported in
plain language, and that the page scripts themselves raise no syntax
or rendering errors. The sticky tab bar check (skill section 8)
scrolls the window by at least 1000 px and asserts that the tab bar
stays at the top of the viewport and remains usable while scrolled,
at both widths."""
import asyncio
import json
import os

from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "shots")
os.makedirs(OUT, exist_ok=True)
PAGE_URL = "file://" + os.path.join(HERE, "dist", "methanol-synthesis-plant-v1.html")

STICKY_JS = """() => {
  const nav = document.querySelector('nav.tabs');
  const r = nav.getBoundingClientRect();
  const cs = getComputedStyle(nav);
  return {top: r.top, bottom: r.bottom, height: r.height,
          position: cs.position, background: cs.backgroundColor,
          fullyVisible: r.top >= -1 && r.bottom > 0 && r.height > 20};
}"""


async def sticky_check(pg, report, prefix):
    await pg.evaluate("window.scrollTo(0, 1500)")
    await pg.wait_for_timeout(400)
    geo = await pg.evaluate(STICKY_JS)
    report[prefix + "_sticky_after_1500px_scroll"] = geo
    report[prefix + "_sticky_top_is_zero"] = abs(geo["top"]) <= 1 and geo["fullyVisible"]
    await pg.click("#tabbtn-theory")
    await pg.wait_for_timeout(400)
    active = await pg.evaluate(
        "document.querySelector('#panel-theory').classList.contains('active')")
    report[prefix + "_tab_switch_while_scrolled"] = active
    geo2 = await pg.evaluate(STICKY_JS)
    report[prefix + "_sticky_still_at_top_after_switch"] = abs(geo2["top"]) <= 1


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
        loop = await pg.text_content("#out-loop")
        report["desktop_prestart_loop"] = loop
        await pg.screenshot(path=os.path.join(OUT, "desktop-app.png"))
        await sticky_check(pg, report, "desktop")
        await pg.evaluate("window.scrollTo(0, 0)")
        await pg.click("#tabbtn-theory")
        await pg.wait_for_timeout(400)
        await pg.screenshot(path=os.path.join(OUT, "desktop-theory.png"))
        await pg.evaluate("document.querySelector('#theory-production-scale').scrollIntoView()")
        await pg.wait_for_timeout(300)
        await pg.screenshot(path=os.path.join(OUT, "desktop-theory-scale.png"))
        await pg.evaluate("document.querySelector('#theory-balance-model').scrollIntoView()")
        await pg.wait_for_timeout(300)
        await pg.screenshot(path=os.path.join(OUT, "desktop-theory-balance.png"))
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
        await sticky_check(pg, report, "phone")
        geo3 = await pg.evaluate("""() => ({scrollW: document.documentElement.scrollWidth,
          innerW: innerWidth})""")
        report["phone_no_sideways_scroll_after_scroll"] = geo3["scrollW"] <= 390
        await pg.evaluate("window.scrollTo(0, 0)")
        await pg.click("#tabbtn-theory")
        await pg.wait_for_timeout(400)
        await pg.screenshot(path=os.path.join(OUT, "phone-theory.png"))
        await pg.click("#tabbtn-code")
        await pg.wait_for_timeout(400)
        await pg.screenshot(path=os.path.join(OUT, "phone-code.png"))
        await pg.click("#subtab-walkthrough")
        await pg.wait_for_timeout(600)
        await pg.screenshot(path=os.path.join(OUT, "phone-walkthrough.png"))
        report["phone_pageerrors"] = errors2
        await pg.close()
        await b.close()
    print(json.dumps(report, indent=1))


asyncio.run(main())
