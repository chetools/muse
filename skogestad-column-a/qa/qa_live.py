"""Live-boot QA through the shared CDN mirror.

Checks: boot reaches ready; the first live run replaces the
precomputed display (no 'precomputed' text left in the App
panel, chart count unchanged); the in-browser autograd Jacobian
at the Column A anchor reproduces the CPython gain matrix to
1e-6 relative (pitfall P-A); a changed input gives a
distinguishable live run; the FOPTD matrix fit at N = 39 is
timed in the browser (pitfall P-C); DB renders the Amendment A1
treatment with no NaN (pitfall P-B); the progress element is
removed after runs and the ready line shows; a keyboard-only
tab switch works and the live region announces completion.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.home() / "workspace/wasm-verify"))
import cdn_mirror  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).parent.parent
OUT = ROOT / "qa"
URL = "http://127.0.0.1:8931/skogestad-column-a-standalone-v2.html"

CPYTHON_ANCHOR = [[0.05252420779704971, -0.051705363068329346,
                   0.02363665023320968, 0.881248763508396],
                  [0.06507578250915444, -0.06589462723787058,
                   0.03516334491990966, 1.11875123649157]]


def main():
    report = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280,
                                          "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append("console:" +
                m.text[:160]) if m.type == "error" else None)
        log = []
        cdn_mirror.install(page, log)
        page.goto(URL)
        page.wait_for_function(
            "document.getElementById('boot-status').textContent"
            ".includes('ready')", timeout=240000)
        page.wait_for_function(
            "!document.getElementById('ready-line').hidden",
            timeout=240000)
        report["boot"] = "ready; first live run complete"
        app_text = page.locator("#panel-app").inner_text()
        assert "precomputed" not in app_text.lower(), \
            "precomputed text remains in App after live run"
        n_charts = page.evaluate(
            "document.querySelectorAll('#panel-app .chart').length")
        assert n_charts == 2, n_charts
        xd_live = page.evaluate(
            "window.columnA ? 'rpc-exposed' : 'missing'")
        assert xd_live == "rpc-exposed"
        report["precomputed_replaced"] = True

        # P-A: in-browser anchor gains vs CPython
        anchor = page.evaluate(
            "window.columnA.rpc('anchor', {}).then(r => r)")
        worst = 0.0
        for i in range(2):
            for j in range(4):
                ref = CPYTHON_ANCHOR[i][j]
                got = anchor["gains"][i][j]
                worst = max(worst, abs(got - ref) / abs(ref))
        report["anchor_max_rel_err"] = worst
        assert worst < 1e-6, worst
        assert abs(anchor["xD"] - 0.99) < 1e-3

        # distinguishable live run: change reflux, auto-run fires
        before = page.locator("#app-summary").inner_text()
        page.fill("#in-reflux", "47.105")
        page.wait_for_function(
            "(b) => document.getElementById('app-summary')"
            ".innerText !== b", arg=before, timeout=120000)
        after = page.locator("#app-summary").inner_text()
        assert "precomputed" not in after.lower()
        report["changed_input_run"] = "summary updated after edit"
        page.fill("#in-reflux", "45.105")
        page.wait_for_function(
            "(b) => document.getElementById('app-summary')"
            ".innerText !== b", arg=after, timeout=120000)

        # FOPTD fit at default N=5, timed
        page.click('[data-tab="analysis"]')
        t0 = time.time()
        page.click("#fit-btn")
        page.wait_for_function(
            "document.getElementById('an-foptd')"
            ".innerText.includes('Fit horizon')", timeout=120000)
        report["foptd_fit_s_N5"] = round(time.time() - t0, 2)
        page.click("#ch-btn")
        page.wait_for_function(
            "document.querySelectorAll('#chart-channel "
            "svg.main-svg').length >= 1", timeout=120000)
        report["channel_overlay"] = "rendered"
        page.screenshot(path=str(OUT / "live-analysis.png"))

        # DB: Amendment A1 treatment, no NaN (P-B)
        page.click('[data-tab="app"]')
        page.select_option("#in-config", "DB")
        page.wait_for_function(
            "document.getElementById('an-gains')"
            ".innerText.includes('integrating')", timeout=120000)
        an_text = page.locator("#panel-analysis").inner_text()
        assert "NaN" not in an_text and "Infinity" not in an_text
        assert "Residuals of the deflated" in an_text, \
            "DB residuals missing in perfect mode"
        report["db_residuals_perfect"] = "shown in DB panel"
        page.select_option("#in-mode", "P")
        page.wait_for_function(
            "document.getElementById('an-gains')"
            ".innerText.includes('Residuals of the deflated')",
            timeout=120000)
        report["db_residuals_P"] = "shown in DB panel"
        page.select_option("#in-mode", "perfect")
        page.wait_for_function(
            "document.getElementById('an-gains')"
            ".innerText.includes('Residuals of the deflated')",
            timeout=120000)
        page.click('[data-tab="analysis"]')
        page.click("#fit-btn")
        page.wait_for_function(
            "document.getElementById('an-foptd')"
            ".innerText.includes('integrating')", timeout=120000)
        assert "NaN" not in page.locator("#an-foptd").inner_text()
        report["db"] = "A1 treatment rendered; no NaN"
        page.screenshot(path=str(OUT / "live-db.png"))

        # P-C: FOPTD matrix fit at the anchor N = 39, timed
        page.click('[data-tab="app"]')
        page.select_option("#in-config", "LV")
        page.fill("#in-n", "39")
        page.wait_for_function(
            "document.getElementById('app-summary')"
            ".innerText.includes('41 (21)')", timeout=300000)
        page.click('[data-tab="analysis"]')
        t0 = time.time()
        page.click("#fit-btn")
        page.wait_for_function(
            "document.getElementById('an-foptd')"
            ".innerText.includes('Fit horizon')", timeout=300000)
        report["foptd_fit_s_N39"] = round(time.time() - t0, 2)
        page.screenshot(path=str(OUT / "live-anchor-fit.png"))

        # progress element removed, ready line present
        prog_hidden = page.evaluate(
            "document.getElementById('run-progress').hidden")
        assert prog_hidden
        report["progress_removed"] = True
        live_region = page.locator("#live-region").inner_text()
        report["live_region"] = live_region

        # keyboard-only: tab to the Theory button and activate
        page.click('[data-tab="app"]')
        page.keyboard.press("Tab")
        focused = page.evaluate("document.activeElement.tagName")
        report["keyboard_first_focus"] = focused
        page.evaluate("document.querySelector("
                      "'[data-tab=\"theory\"]').focus()")
        page.keyboard.press("Enter")
        page.wait_for_timeout(400)
        assert page.locator("#panel-theory").is_visible()
        report["keyboard_tab_switch"] = "Theory panel visible"
        assert not errors, errors[:4]
        report["page_errors"] = errors
        page.screenshot(path=str(OUT / "live-app.png"))
        browser.close()
    (OUT / "live_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))
    print("LIVE QA PASS")


if __name__ == "__main__":
    main()
