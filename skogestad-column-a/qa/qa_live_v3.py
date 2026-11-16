"""Live-boot QA for v3 through the shared CDN mirror.

Adapted from qa_live.py (v2). All v2 checks are kept: boot
reaches ready; the first live run replaces the precomputed
display; the in-browser autograd Jacobian at the Column A
anchor reproduces the CPython gain matrix to 1e-6 relative;
a changed input gives a distinguishable live run; the FOPTD
matrix fit at N = 5 and at N = 39 is timed in the browser;
DB renders the Amendment A1 treatment with no NaN in both
level modes; the progress element is removed after runs and
the ready line shows; a keyboard-only tab switch works; zero
page/console errors.

v3 adaptations: the URL and all screenshot/report names carry
v3; Theory is the landing panel, so the App tab is shown
before reading App panel text or filling App inputs.

Added for v3: the guided-experiment verifications E1-E6 from
the Theory panel, performed live with actual values recorded,
and a pop-up-during-run check (an open guide pop-up must not
block the automatic re-run).
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.home() / "workspace/wasm-verify"))
import cdn_mirror  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).parent.parent
OUT = ROOT / "qa"
URL = "http://127.0.0.1:8931/skogestad-column-a-standalone-v3.html"

CPYTHON_ANCHOR = [[0.05252420779704971, -0.051705363068329346,
                   0.02363665023320968, 0.881248763508396],
                  [0.06507578250915444, -0.06589462723787058,
                   0.03516334491990966, 1.11875123649157]]

SUMMARY_JS = """
() => {
  const rows = {};
  document.querySelectorAll('#app-summary tr').forEach(tr => {
    const th = tr.querySelector('th'), td = tr.querySelector('td');
    if (th && td) rows[th.textContent.trim()] =
      td.textContent.trim();
  });
  return rows;
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
          hidden: el.hidden, w: Math.round(r.width),
          h: Math.round(r.height)};
}
"""

FOPTD_ROWS_JS = """
() => {
  const rows = [];
  document.querySelectorAll('#an-foptd table tr').forEach(tr => {
    const th = tr.querySelector('th');
    const tds = [...tr.querySelectorAll('td')];
    if (!th || !tds.length) return;
    rows.push({label: th.textContent.trim(),
      cells: tds.map(td => td.textContent.trim()),
      classes: tds.map(td => td.className)});
  });
  return rows;
}
"""


def pop_visible(state):
    if not state.get("found"):
        return False
    if state.get("popOpen"):
        return True
    return (state.get("display") not in (None, "none")
            and not state.get("hidden")
            and state.get("w", 0) > 0 and state.get("h", 0) > 0)


def read_summary(page):
    """App summary table as a dict of row label -> value text,
    plus the parsed floats the experiments need."""
    rows = page.evaluate(SUMMARY_JS)
    out = {"rows": rows}
    for key, pat in (("xD", "Distillate composition xD"),
                     ("xB", "Bottoms composition xB")):
        for label, val in rows.items():
            if label.startswith(pat):
                out[key] = float(val)
    for label, val in rows.items():
        if label.startswith("Dominant time constant"):
            out["tau_dom"] = float(val)
        if label.startswith("Stages NT"):
            out["stages"] = val
        if label.startswith("Configuration"):
            out["config_mode"] = val
    return out


def read_rga(page):
    """(full note text, matrix-formula string, shortcut string,
    matrix-formula float) from the Analysis RGA note. The caller
    must have the Analysis panel visible."""
    txt = page.locator("#an-rga").inner_text()
    m = re.search(r"matrix formula:\s*(-?[0-9]+\.[0-9]+);\s*from the "
                  r"shortcut.*?:\s*(-?[0-9]+\.[0-9]+)", txt, re.S)
    assert m, ("RGA note not parseable", txt[:300])
    return txt, m.group(1), m.group(2), float(m.group(1))


def read_step_note(page):
    """(text, linear xD, linear xB, nonlinear xD, nonlinear xB)
    parsed from the App step note."""
    txt = page.locator("#app-step-note").inner_text()
    m = re.search(r"Linear final values: xD (-?[0-9]+\.[0-9]+), xB "
                  r"(-?[0-9]+\.[0-9]+).*?Nonlinear final values: xD "
                  r"(-?[0-9]+\.[0-9]+), xB (-?[0-9]+\.[0-9]+)",
                  txt, re.S)
    assert m, ("step note not parseable", txt[:300])
    return (txt, float(m.group(1)), float(m.group(2)),
            float(m.group(3)), float(m.group(4)))


def wait_summary_change(page, before, timeout=180000):
    page.wait_for_function(
        "(b) => document.getElementById('app-summary')"
        ".innerText !== b", arg=before, timeout=timeout)
    page.wait_for_function(
        "document.getElementById('run-progress').hidden",
        timeout=60000)


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
        try:
            page.wait_for_function(
                "document.getElementById('boot-status').textContent"
                ".includes('ready')", timeout=240000)
            page.wait_for_function(
                "!document.getElementById('ready-line').hidden",
                timeout=240000)
        except Exception:
            status = page.locator("#boot-status").inner_text()
            report["boot_failed"] = {"boot_status": status,
                                     "errors": errors,
                                     "mirror_log_tail": log[-20:]}
            (OUT / "live_report_v3.json").write_text(
                json.dumps(report, indent=1))
            print("BOOT FAILED")
            print("boot-status:", status)
            print("errors:", errors)
            raise
        report["boot"] = "ready; first live run complete"

        # v3: Theory is the landing panel; show App before
        # reading its text (v2 read it on the landing panel).
        page.click('[data-tab="app"]')
        page.wait_for_timeout(400)
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
        page.wait_for_function(
            "document.getElementById('run-progress').hidden",
            timeout=60000)

        # ================= guided experiments =================
        exp = {}
        findings = []

        # --- E3 + E2 (default reading): RGA note at defaults ---
        page.click('[data-tab="analysis"]')
        page.wait_for_timeout(400)
        rga_txt, lam_str, short_str, lam_def = read_rga(page)
        exp["E3"] = {"rga_note": rga_txt.strip(),
                     "lambda11_matrix_str": lam_str,
                     "lambda11_shortcut_str": short_str,
                     "strings_equal": lam_str == short_str}
        assert lam_str == short_str, exp["E3"]
        assert abs(lam_def - 19.3585) <= 0.01, ("E2 default", lam_def)
        exp["E2"] = {"lambda11_N5_LV": lam_def}

        # --- E6: Perfect vs Proportional-only at defaults ---
        # Delta QA re-run (corrected Theory): HARD asserts that
        # the displayed lambda11 and the displayed dominant time
        # constant are IDENTICAL between Perfect and
        # Proportional-only at the defaults, and that the pole
        # count changes 12 -> 14 (read from both the Analysis
        # poles area text and the RPC pole count).
        poles_perf = page.locator("#an-poles").inner_text()
        page.click('[data-tab="app"]')
        page.wait_for_timeout(300)
        s_perf = read_summary(page)
        rpc_base = {"n_trays": 5, "alpha": 1.5,
                    "feed_flow": 16.667, "feed_comp": 0.5,
                    "feed_q": 1.0, "reflux": 45.105,
                    "boilup": 53.438, "config": "LV",
                    "kc_drum": 0.1667, "kc_reb": 0.1667,
                    "step_col": 0, "step_size": 1.0,
                    "with_step": False}
        full_perf = page.evaluate(
            "(p) => window.columnA.rpc('run', p).then(r => r)",
            dict(rpc_base, mode="perfect"))
        full_prop = page.evaluate(
            "(p) => window.columnA.rpc('run', p).then(r => r)",
            dict(rpc_base, mode="P"))
        before = page.locator("#app-summary").inner_text()
        page.select_option("#in-mode", "P")
        wait_summary_change(page, before)
        s_prop = read_summary(page)
        page.click('[data-tab="analysis"]')
        page.wait_for_timeout(300)
        _, _, _, lam_prop = read_rga(page)
        poles_prop = page.locator("#an-poles").inner_text()
        page.click('[data-tab="app"]')
        page.wait_for_timeout(300)
        e6_differs = (lam_prop != lam_def
                      or s_prop["tau_dom"] != s_perf["tau_dom"])
        exp["E6"] = {
            "perfect": {"lambda11": lam_def,
                        "tau_dom": s_perf["tau_dom"],
                        "poles_text": poles_perf.strip(),
                        "lambda11_full": full_perf["rga11"],
                        "tau_dom_full": full_perf["poles"]["tau_dom"],
                        "pole_count": full_perf["poles"]["count"]},
            "proportional": {
                "lambda11": lam_prop,
                "tau_dom": s_prop["tau_dom"],
                "poles_text": poles_prop.strip(),
                "lambda11_full": full_prop["rga11"],
                "tau_dom_full": full_prop["poles"]["tau_dom"],
                "pole_count": full_prop["poles"]["count"]},
            "displayed_values_differ": e6_differs,
            "displayed_values_identical": not e6_differs}
        # HARD asserts (delta QA): identical displayed values,
        # pole count 12 -> 14 in both text and RPC counts.
        assert lam_prop == lam_def, (
            "E6 lambda11 differs", lam_def, lam_prop)
        assert s_prop["tau_dom"] == s_perf["tau_dom"], (
            "E6 tau_dom differs", s_perf["tau_dom"],
            s_prop["tau_dom"])
        assert "Number of poles: 12" in poles_perf, (
            "E6 perfect poles text", poles_perf[:200])
        assert "Number of poles: 14" in poles_prop, (
            "E6 proportional poles text", poles_prop[:200])
        assert full_perf["poles"]["count"] == 12, (
            "E6 perfect pole count", full_perf["poles"]["count"])
        assert full_prop["poles"]["count"] == 14, (
            "E6 proportional pole count",
            full_prop["poles"]["count"])
        before = page.locator("#app-summary").inner_text()
        page.select_option("#in-mode", "perfect")
        wait_summary_change(page, before)

        # --- E1: linear vs nonlinear separation, size 1 vs 10 ---
        page.select_option("#in-step-col", "0")
        page.wait_for_timeout(300)
        _, lx1, _, nx1, _ = read_step_note(page)
        sep1 = abs(lx1 - nx1)
        note_before = page.locator("#app-step-note").inner_text()
        page.fill("#in-step-size", "10")
        page.wait_for_function(
            "(b) => document.getElementById('app-step-note')"
            ".innerText !== b", arg=note_before, timeout=180000)
        page.wait_for_function(
            "document.getElementById('run-progress').hidden",
            timeout=60000)
        _, lx10, _, nx10, _ = read_step_note(page)
        sep10 = abs(lx10 - nx10)
        exp["E1"] = {"size1": {"lin_xD": lx1, "nonlin_xD": nx1,
                               "sep_xD": sep1},
                     "size10": {"lin_xD": lx10, "nonlin_xD": nx10,
                                "sep_xD": sep10},
                     "separation_grows": sep10 > sep1}
        assert sep10 > sep1, exp["E1"]
        note_before = page.locator("#app-step-note").inner_text()
        page.fill("#in-step-size", "1")
        page.wait_for_function(
            "(b) => document.getElementById('app-step-note')"
            ".innerText !== b", arg=note_before, timeout=180000)
        page.wait_for_function(
            "document.getElementById('run-progress').hidden",
            timeout=60000)

        # --- E2 continued: N=39 anchor, then DV, then restore ---
        before = page.locator("#app-summary").inner_text()
        page.fill("#in-n", "39")
        page.wait_for_function(
            "document.getElementById('app-summary')"
            ".innerText.includes('41 (21)')", timeout=300000)
        page.wait_for_function(
            "document.getElementById('run-progress').hidden",
            timeout=60000)
        s39 = read_summary(page)
        exp["E2"]["N39_summary"] = s39["rows"]
        exp["E2"]["xD_N39"] = s39["xD"]
        assert "0.9900" in page.locator(
            "#app-summary").inner_text(), s39["rows"]
        assert abs(s39["xD"] - 0.9900) < 1e-4, s39["xD"]
        page.click('[data-tab="analysis"]')
        page.wait_for_timeout(300)
        _, _, _, lam39 = read_rga(page)
        full39 = page.evaluate(
            "(p) => window.columnA.rpc('run', p).then(r => r)",
            dict(rpc_base, n_trays=39, mode="perfect"))
        exp["E2"]["lambda11_N39_LV"] = lam39
        exp["E2"]["lambda11_N39_LV_full"] = full39["rga11"]
        exp["E2"]["lambda11_N39_LV_expected"] = 35.8970
        assert abs(lam39 - 35.8970) <= 0.01, ("E2 N39 LV", lam39)
        page.click('[data-tab="app"]')
        page.wait_for_timeout(300)
        before = page.locator("#app-summary").inner_text()
        page.select_option("#in-config", "DV")
        wait_summary_change(page, before, timeout=300000)
        page.click('[data-tab="analysis"]')
        page.wait_for_timeout(300)
        _, _, _, lam_dv = read_rga(page)
        exp["E2"]["lambda11_N39_DV"] = lam_dv
        assert abs(lam_dv - 0.4445) <= 0.01, ("E2 DV", lam_dv)
        page.click('[data-tab="app"]')
        page.wait_for_timeout(300)
        page.select_option("#in-config", "LV")
        page.fill("#in-n", "5")
        page.wait_for_function(
            "document.getElementById('app-summary')"
            ".innerText.includes('7 (4)')", timeout=300000)
        page.wait_for_function(
            "document.getElementById('run-progress').hidden",
            timeout=60000)
        page.click('[data-tab="analysis"]')
        page.wait_for_timeout(300)
        _, _, _, lam_back = read_rga(page)
        exp["E2"]["lambda11_restored_N5_LV"] = lam_back
        assert abs(lam_back - 19.3585) <= 0.01, ("E2 restore", lam_back)
        page.click('[data-tab="app"]')
        page.wait_for_timeout(300)

        # --- E4: DB finite gains, residuals, no RGA ---
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
        gains_txt = page.locator("#an-gains").inner_text()
        rga_db_txt = page.locator("#an-rga").inner_text()
        panel_txt = page.locator("#panel-analysis").inner_text()
        mres = re.search(
            r"balanced split\s*([0-9.]+e[+-]?[0-9]+|[0-9.]+),"
            r"\s*feed composition\s*"
            r"([0-9.]+e[+-]?[0-9]+|[0-9.]+)", gains_txt)
        assert "Residuals of the deflated" in gains_txt, gains_txt[:300]
        assert mres, ("E4 residuals not parseable", gains_txt[:400])
        res_bal, res_xf = float(mres.group(1)), float(mres.group(2))
        exp["E4"] = {"residual_balanced": res_bal,
                     "residual_xf": res_xf,
                     "rga_text": rga_db_txt.strip()}
        assert res_bal < 1e-8 and res_xf < 1e-8, exp["E4"]
        assert "No relative gain" in rga_db_txt, rga_db_txt[:200]
        assert "NaN" not in panel_txt and "Infinity" not in panel_txt
        page.click('[data-tab="app"]')
        page.wait_for_timeout(300)
        before = page.locator("#app-summary").inner_text()
        page.select_option("#in-config", "LV")
        wait_summary_change(page, before)

        # --- E5: FOPTD fit errors at defaults + worst overlay ---
        page.click('[data-tab="analysis"]')
        page.wait_for_timeout(300)
        page.click("#fit-btn")
        page.wait_for_function(
            "document.getElementById('an-foptd')"
            ".innerText.includes('Fit horizon')", timeout=180000)
        page.wait_for_function(
            "document.getElementById('run-progress').hidden",
            timeout=60000)
        rows = page.evaluate(FOPTD_ROWS_JS)
        parsed = []
        for idx, r in enumerate(rows):
            entry = {"label": r["label"], "cells": r["cells"],
                     "i": idx // 4, "j": idx % 4, "err": None,
                     "flagged": False}
            if len(r["cells"]) >= 4:
                merr = re.search(r"([0-9.]+)", r["cells"][3])
                if merr:
                    entry["err"] = float(merr.group(1))
                entry["flagged"] = (
                    "flag" in r["classes"][3]
                    or "above 10" in r["cells"][3])
            parsed.append(entry)
        fitted = [e for e in parsed if e["err"] is not None]
        assert fitted, ("E5 no fitted rows", parsed)
        worst_e = max(fitted, key=lambda e: e["err"])
        flagged = [e["label"] for e in fitted if e["err"] > 10]
        exp["E5"] = {"rows": parsed,
                     "max_fit_error_pct": worst_e["err"],
                     "max_channel": worst_e["label"],
                     "channels_over_10pct": flagged,
                     "flagged_in_dom": [e["label"] for e in fitted
                                         if e["flagged"]]}
        # HARD asserts (delta QA): maximum is 1.56 % +/- 0.1 on
        # channel xB <- F, no channel exceeds 10 %, none flagged.
        assert abs(worst_e["err"] - 1.56) <= 0.1, (
            "E5 max fit error", worst_e)
        assert worst_e["label"] == "xB \u2190 F", (
            "E5 max channel", worst_e["label"])
        assert flagged == [], ("E5 channels over 10%", flagged)
        assert exp["E5"]["flagged_in_dom"] == [], (
            "E5 flagged in DOM", exp["E5"]["flagged_in_dom"])
        assert all(e["err"] <= 10 for e in fitted), (
            "E5 a channel exceeds 10%", fitted)
        # Overlay for the worst channel (xB <- F) must render.
        page.select_option("#ch-out", str(worst_e["i"]))
        page.select_option("#ch-in", str(worst_e["j"]))
        page.click("#ch-btn")
        page.wait_for_function(
            "document.querySelectorAll('#chart-channel "
            "svg.main-svg').length >= 1", timeout=120000)
        exp["E5"]["worst_channel_overlay"] = "rendered"
        exp["E5"]["overlay_channel"] = worst_e["label"]
        page.screenshot(path=str(OUT / "live-v3-e5-overlay.png"))

        # --- pop-up open during an automatic run ---
        page.click('[data-tab="app"]')
        page.wait_for_timeout(400)
        btn = page.locator(
            'button.guidebtn[popovertarget="guide-column"]')
        btn.first.scroll_into_view_if_needed()
        btn.first.click()
        page.wait_for_timeout(400)
        st_open = page.evaluate(POP_STATE_JS, "guide-column")
        assert pop_visible(st_open), ("popup-run open", st_open)
        before = page.locator("#app-summary").inner_text()
        # Set the value by script so no pointer event can
        # light-dismiss the popover; the input/change events
        # are what the page's auto-run listens to.
        page.evaluate(
            "() => { const el = document.getElementById("
            "'in-reflux'); el.value = '47.105';"
            " el.dispatchEvent(new Event('input',"
            " {bubbles: true}));"
            " el.dispatchEvent(new Event('change',"
            " {bubbles: true})); }")
        page.wait_for_function(
            "(b) => document.getElementById('app-summary')"
            ".innerText !== b", arg=before, timeout=180000)
        st_still = page.evaluate(POP_STATE_JS, "guide-column")
        exp["popup_during_run"] = {
            "open_before_run": st_open,
            "open_after_run": st_still,
            "summary_updated_with_popup_open": True,
            "popup_still_open_after_run": pop_visible(st_still)}
        assert pop_visible(st_still), exp["popup_during_run"]
        page.screenshot(path=str(OUT / "live-v3-popup-run.png"))
        page.locator("#guide-column button.guideclose").first.click()
        page.wait_for_timeout(400)
        st_closed = page.evaluate(POP_STATE_JS, "guide-column")
        assert not pop_visible(st_closed), ("popup-run close",
                                            st_closed)
        after = page.locator("#app-summary").inner_text()
        page.fill("#in-reflux", "45.105")
        page.wait_for_function(
            "(b) => document.getElementById('app-summary')"
            ".innerText !== b", arg=after, timeout=180000)
        page.wait_for_function(
            "document.getElementById('run-progress').hidden",
            timeout=60000)
        report["experiments"] = exp
        report["findings"] = findings

        # ============ v2 checks kept below this line ============
        # FOPTD fit at default N=5, timed. The pop-up phase runs
        # above reset the FOPTD panel to 'Not fitted', so the
        # 'Fit horizon' wait below waits for this fresh fit.
        page.click('[data-tab="analysis"]')
        page.wait_for_timeout(300)
        page.select_option("#ch-out", "0")
        page.select_option("#ch-in", "0")
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
        page.screenshot(path=str(OUT / "live-v3-analysis.png"))

        # DB: Amendment A1 treatment, no NaN (P-B)
        page.click('[data-tab="app"]')
        page.select_option("#in-config", "DB")
        page.wait_for_function(
            "document.getElementById('an-gains')"
            ".innerText.includes('integrating')", timeout=120000)
        page.click('[data-tab="analysis"]')
        page.wait_for_timeout(300)
        an_text = page.locator("#panel-analysis").inner_text()
        assert "NaN" not in an_text and "Infinity" not in an_text
        assert "Residuals of the deflated" in an_text, \
            "DB residuals missing in perfect mode"
        report["db_residuals_perfect"] = "shown in DB panel"
        page.click('[data-tab="app"]')
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
        page.screenshot(path=str(OUT / "live-v3-db.png"))

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
        page.screenshot(path=str(OUT / "live-v3-anchor-fit.png"))

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
        page.screenshot(path=str(OUT / "live-v3-app.png"))
        browser.close()
    (OUT / "live_report_v3.json").write_text(json.dumps(report,
                                                         indent=1))
    print(json.dumps(report, indent=1))
    if report.get("findings"):
        print("LIVE QA V3 COMPLETED WITH FINDINGS:",
              report["findings"])
    else:
        print("LIVE QA V3 PASS")


if __name__ == "__main__":
    main()
