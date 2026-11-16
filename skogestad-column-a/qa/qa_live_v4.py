"""Live-boot QA for v4 through the shared CDN mirror.

v4 scope (the channel-overlay fix):
- At 1280 px and 390 px, on a fresh page: open Analysis and
  assert the placeholder text is visible inside #chart-channel
  before any fit.
- Press ONLY the "Fit FOPTD matrix" button (the "Show channel
  overlay" button is not pressed in this phase); assert the
  channel overlay is drawn automatically: an svg is present
  inside #chart-channel, the svg width equals the container
  width (+/-2 px), and the placeholder text is gone.
- At 1280 px only, after the auto-render assertion: select a
  different channel and press "Show channel overlay" to verify
  the button still re-renders explicitly.
- Integrating-channel exercise: switch the configuration to
  DB (App tab), return to Analysis, fit again; the default
  channel (xD from the first manipulated variable) is
  integrating for DB, and the chart area must show the
  integrating note text in place of a chart (no svg). At the
  LV defaults every channel is fitted, so no integrating or
  negligible channel is reachable without the config change.
- Stale-note scenario (after the overlay is drawn, so the
  channel note under the chart is visible): change an App
  input in one synchronous evaluate (dispatching "input", and
  planting a sentinel in #run-note before the debounced
  auto-run can fire) so the analysis is marked stale; assert
  #chart-channel shows the placeholder AND #an-channel-note
  is empty. Then wait for the sentinel to be replaced by
  "Run complete.", i.e. the debounced auto-run has finished,
  restore the changed input by the same method, and wait for
  that auto-run too, so later steps run at the defaults.
- Balanced-split scenario (LV configuration): select the
  "Balanced split (DB only)" channel and press "Fit FOPTD
  matrix"; assert the FOPTD matrix renders, #ch-err shows the
  DB-only message, and #chart-channel contains that DB-only
  explanation text with no placeholder text and no svg.
- Zero console/page errors throughout.
Screenshots: qa/390-analysis-v4-overlay.png shows the drawn
overlay at 390 px; qa/1280-analysis-v4-overlay.png likewise.
Report: qa/live_report_v4.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "workspace/wasm-verify"))
import cdn_mirror  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).parent.parent
OUT = ROOT / "qa"
URL = "http://127.0.0.1:8931/skogestad-column-a-standalone-v4.html"
PLACEHOLDER = "No channel overlay yet"
DB_ONLY = "The balanced-split channel exists only for DB."

SVG_WIDTH_JS = """
() => {
  const box = document.getElementById('chart-channel');
  const svg = box.querySelector('svg.main-svg');
  if (!svg) return null;
  return {svgW: Math.round(svg.getBoundingClientRect().width),
          boxW: Math.round(box.getBoundingClientRect().width)};
}
"""


def boot(page):
    page.wait_for_function(
        "document.getElementById('boot-status').textContent"
        ".includes('ready')", timeout=240000)
    page.wait_for_function(
        "!document.getElementById('ready-line').hidden",
        timeout=240000)
    page.wait_for_function(
        "document.getElementById('run-progress').hidden",
        timeout=60000)


def fit_and_wait(page):
    page.click("#fit-btn")
    page.wait_for_function(
        "document.getElementById('an-foptd')"
        ".innerText.includes('Fit horizon')", timeout=180000)
    page.wait_for_function(
        "document.getElementById('run-progress').hidden",
        timeout=60000)


def run_width(pw_browser, width, report):
    page = pw_browser.new_page(viewport={"width": width,
                                         "height": 1000})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append("console:" +
            m.text[:160]) if m.type == "error" else None)
    log = []
    cdn_mirror.install(page, log)
    page.goto(URL)
    boot(page)
    w = {}

    # ---- placeholder before any fit ----
    page.click('[data-tab="analysis"]')
    page.wait_for_timeout(500)
    ch_text = page.locator("#chart-channel").inner_text()
    ph_visible = page.locator(
        "#chart-channel .chart-placeholder").is_visible()
    w["placeholder_before_fit"] = {"text": ch_text.strip(),
                                   "visible": ph_visible}
    assert PLACEHOLDER in ch_text, (width, "placeholder", ch_text[:120])
    assert ph_visible, (width, "placeholder not visible")
    assert page.locator("#chart-channel svg").count() == 0

    # ---- fit only; overlay must auto-render ----
    fit_and_wait(page)
    page.wait_for_function(
        "document.querySelectorAll('#chart-channel "
        "svg.main-svg').length >= 1", timeout=120000)
    dims = page.evaluate(SVG_WIDTH_JS)
    w["overlay_after_fit_only"] = dims
    assert dims and abs(dims["svgW"] - dims["boxW"]) <= 2, dims
    ch_text = page.locator("#chart-channel").inner_text()
    assert PLACEHOLDER not in ch_text, (width, "placeholder remains")
    note = page.locator("#an-channel-note").inner_text()
    w["channel_note_after_fit"] = note.strip()
    assert "tau =" in note, (width, "channel note", note[:160])
    page.locator("#chart-channel").scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    page.screenshot(path=str(OUT / f"{width}-analysis-v4-overlay.png"))
    w["screenshot"] = f"qa/{width}-analysis-v4-overlay.png"

    # ---- stale-note: a stale input change must clear the
    # channel note together with the chart area. The change
    # and the reads happen in one synchronous evaluate, so
    # the debounced auto-run (350 ms) cannot fire in between;
    # the sentinel planted in #run-note in the same evaluate
    # makes the auto-run's completion waitable afterwards. ----
    assert page.locator("#an-channel-note").inner_text().strip(), \
        (width, "channel note empty before stale change")
    stale = page.evaluate("""
      () => {
        const el = document.getElementById('in-reflux');
        el.value = (parseFloat(el.value) + 1).toString();
        el.dispatchEvent(new Event('input', {bubbles: true}));
        const out = {
          channel: document.getElementById('chart-channel')
            .innerText,
          note: document.getElementById('an-channel-note')
            .innerText,
          note_html: document.getElementById('an-channel-note')
            .innerHTML,
          stale_shown: !document.getElementById('an-stale')
            .hidden,
        };
        document.getElementById('run-note').textContent =
          'STALE-SENTINEL';
        return out;
      }""")
    w["stale_note"] = {"channel": stale["channel"].strip(),
                       "note": stale["note"].strip(),
                       "stale_shown": stale["stale_shown"]}
    assert stale["stale_shown"], (width, "not marked stale", stale)
    assert PLACEHOLDER in stale["channel"], \
        (width, "stale channel not placeholder", stale)
    assert stale["note"].strip() == "", \
        (width, "stale channel note not cleared", stale)
    assert stale["note_html"] == "", \
        (width, "stale channel note html not cleared", stale)
    page.wait_for_function(
        "document.getElementById('run-note').textContent"
        " === 'Run complete.'", timeout=180000)
    page.wait_for_function(
        "document.getElementById('run-progress').hidden",
        timeout=60000)
    # Restore the changed input (same sentinel method) so the
    # later scenarios run at the exact default inputs again.
    page.evaluate("""
      () => {
        const el = document.getElementById('in-reflux');
        el.value = (parseFloat(el.value) - 1).toString();
        el.dispatchEvent(new Event('input', {bubbles: true}));
        document.getElementById('run-note').textContent =
          'STALE-SENTINEL';
      }""")
    page.wait_for_function(
        "document.getElementById('run-note').textContent"
        " === 'Run complete.'", timeout=180000)
    page.wait_for_function(
        "document.getElementById('run-progress').hidden",
        timeout=60000)
    w["stale_note"]["input_restored"] = True

    # ---- explicit button re-render (1280 only, after the
    # fit-only assertion above is complete) ----
    if width == 1280:
        note_before = page.locator("#an-channel-note").inner_text()
        page.select_option("#ch-out", "1")
        page.select_option("#ch-in", "2")
        page.click("#ch-btn")
        page.wait_for_function(
            "(b) => document.getElementById('an-channel-note')"
            ".innerText !== b", arg=note_before, timeout=120000)
        page.wait_for_function(
            "document.querySelectorAll('#chart-channel "
            "svg.main-svg').length >= 1", timeout=60000)
        title = page.evaluate(
            "() => { const t = document.getElementById("
            "'chart-channel').layout.title;"
            " return typeof t === 'string' ? t :"
            " (t && t.text) || ''; }")
        w["button_rerender"] = {"note": page.locator(
            "#an-channel-note").inner_text().strip(),
            "chart_title": title}
        assert "xB" in title, (width, "button title", title)

    # ---- balanced-split channel on a non-DB (LV) config:
    # the fit itself succeeds, the channel request fails, and
    # the chart area must carry the DB-only explanation
    # instead of the (now false) placeholder wording. ----
    page.select_option("#ch-out", "0")
    page.select_option("#ch-in", "4")
    fit_and_wait(page)
    page.wait_for_function(
        "!document.getElementById('ch-err').hidden &&"
        " document.getElementById('ch-err').innerText"
        ".includes('balanced-split')", timeout=120000)
    page.wait_for_function(
        "document.getElementById('chart-channel').innerText"
        ".includes('balanced-split channel exists only')",
        timeout=60000)
    foptd_text = page.locator("#an-foptd").inner_text()
    ch_err = page.locator("#ch-err").inner_text().strip()
    ch_text = page.locator("#chart-channel").inner_text()
    w["balanced_split"] = {"foptd_rendered":
                           "Fit horizon" in foptd_text,
                           "ch_err": ch_err,
                           "chart_channel": ch_text.strip(),
                           "svg_count": page.locator(
                               "#chart-channel svg").count()}
    assert "Fit horizon" in foptd_text, \
        (width, "FOPTD matrix not rendered", foptd_text[:160])
    assert ch_err == DB_ONLY, (width, "ch-err", ch_err)
    assert DB_ONLY in ch_text, (width, "chart explanation", ch_text[:160])
    assert PLACEHOLDER not in ch_text, \
        (width, "placeholder remains in chart area", ch_text[:160])
    assert page.locator("#chart-channel svg").count() == 0, \
        (width, "svg present for balanced-split error")

    # ---- integrating channel via DB ----
    page.click('[data-tab="app"]')
    page.wait_for_timeout(300)
    page.select_option("#in-config", "DB")
    page.wait_for_function(
        "document.getElementById('an-gains')"
        ".innerText.includes('Residuals of the deflated')",
        timeout=180000)
    page.wait_for_function(
        "document.getElementById('run-progress').hidden",
        timeout=60000)
    page.click('[data-tab="analysis"]')
    page.wait_for_timeout(400)
    # the auto-run for the new inputs reset the channel area
    ch_text = page.locator("#chart-channel").inner_text()
    w["placeholder_after_DB_run"] = ch_text.strip()
    assert PLACEHOLDER in ch_text, (width, "DB placeholder", ch_text[:120])
    page.select_option("#ch-out", "0")
    page.select_option("#ch-in", "0")
    fit_and_wait(page)
    page.wait_for_function(
        "document.getElementById('chart-channel')"
        ".innerText.includes('is integrating')", timeout=120000)
    ch_text = page.locator("#chart-channel").inner_text()
    w["integrating_chart_area"] = ch_text.strip()
    assert "is integrating" in ch_text, (width, ch_text[:160])
    assert "ramp rate" in ch_text, (width, ch_text[:160])
    assert page.locator("#chart-channel svg").count() == 0, \
        (width, "svg present for integrating channel")
    assert "is integrating" in page.locator(
        "#an-channel-note").inner_text()

    assert not errors, (width, errors[:4])
    w["page_errors"] = errors
    report["widths"][str(width)] = w
    page.close()


def main():
    report = {"widths": {}}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in (1280, 390):
            run_width(browser, width, report)
        browser.close()
    (OUT / "live_report_v4.json").write_text(json.dumps(report,
                                                         indent=1))
    print(json.dumps(report, indent=1))
    print("LIVE QA V4 PASS")


if __name__ == "__main__":
    main()
