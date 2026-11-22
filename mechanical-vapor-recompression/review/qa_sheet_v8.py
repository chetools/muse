"""Sheet/crop screenshots for the v8 merged sheet: standalone sheet,
Process panel, each crop figure at desktop and phone, Economics."""
import os
import subprocess
import sys
import time

BASE = os.path.expanduser("~/workspace/mechanical-vapor-recompression")
SHOTS = os.path.join(BASE, "shots")
PORT = 8475
sys.path.insert(0, os.path.expanduser(
    "~/workspace/.venvs/qa-playwright/lib/python3.12/site-packages"))
from playwright.sync_api import sync_playwright  # noqa: E402

PAGE = f"http://127.0.0.1:{PORT}/dist/mechanical-vapor-recompression-v8.html"
SHEET = f"http://127.0.0.1:{PORT}/sheet.svg"


def main():
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT),
         "--bind", "127.0.0.1"], cwd=BASE,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1.0)
        with sync_playwright() as pw:
            b = pw.chromium.launch(args=["--no-sandbox"])
            # Standalone sheet at native size.
            p = b.new_page(viewport={"width": 1240, "height": 760})
            p.goto(SHEET, wait_until="load")
            p.wait_for_timeout(500)
            p.screenshot(path=os.path.join(SHOTS, "v8-sheet-full.png"))
            # Desktop panels.
            p2 = b.new_page(viewport={"width": 1280, "height": 900})
            errs = []
            p2.on("pageerror", lambda e: errs.append(str(e)))
            p2.goto(PAGE, wait_until="domcontentloaded")
            p2.wait_for_selector("#panel-theory h2", timeout=30000, state="attached")
            p2.click("#tab-process")
            p2.wait_for_timeout(800)
            p2.screenshot(path=os.path.join(SHOTS, "v8-process-desktop.png"))
            figs = p2.query_selector_all("#panel-process figure")
            print("crop figures:", len(figs))
            for i, f in enumerate(figs, 1):
                f.scroll_into_view_if_needed()
                p2.wait_for_timeout(300)
                f.screenshot(path=os.path.join(
                    SHOTS, f"v8-crop-p{i}-desktop.png"))
            sw = p2.query_selector(".sheetwrap")
            if sw:
                sw.scroll_into_view_if_needed()
                p2.wait_for_timeout(300)
                sw.screenshot(path=os.path.join(SHOTS, "v8-sheet-panel.png"))
            p2.click("#tab-economics")
            p2.wait_for_timeout(600)
            p2.screenshot(path=os.path.join(SHOTS, "v8-economics-desktop.png"))
            print("desktop page errors:", errs)
            # Phone crops + economics.
            p3 = b.new_page(viewport={"width": 390, "height": 844})
            p3.goto(PAGE, wait_until="domcontentloaded")
            p3.wait_for_selector("#panel-theory h2", timeout=30000, state="attached")
            p3.click("#tab-process")
            p3.wait_for_timeout(600)
            figs3 = p3.query_selector_all("#panel-process figure")
            for i, f in enumerate(figs3, 1):
                f.scroll_into_view_if_needed()
                p3.wait_for_timeout(300)
                f.screenshot(path=os.path.join(
                    SHOTS, f"v8-crop-p{i}-phone.png"))
            p3.click("#tab-economics")
            p3.wait_for_timeout(600)
            p3.screenshot(path=os.path.join(SHOTS, "v8-economics-phone.png"))
            print("phone scrollW:", p3.evaluate(
                "() => document.documentElement.scrollWidth"))
            b.close()
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
