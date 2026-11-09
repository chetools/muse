"""Browser QA for the built page: screenshots of every tab at
1440 px and 390 px, a 2560 px header-width check, sticky tab bar,
console-error collection, and (if the CDN is reachable) a live
Pyodide run. Run with the marimo-export venv python."""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
QA = ROOT / "dist" / "qa"
QA.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8907/mccabe-thiele-ponchon-savarit-standalone-v7.html"

report = {"console_errors": [], "page_errors": []}


def shot(page, name, full=True):
    page.screenshot(path=str(QA / name), full_page=full)
    print("shot", name)


with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.on("console", lambda m: report["console_errors"].append(m.text)
            if m.type == "error" else None)
    page.on("pageerror", lambda e: report["page_errors"].append(str(e)))
    page.goto(URL)
    page.wait_for_timeout(2500)
    report["fig_mt_svg"] = page.locator("#fig-mt svg").count()
    report["fig_psxy_svg"] = page.locator("#fig-psxy svg").count()
    # Fig. 3 geometry, read from the drawn traces (v7): the
    # Ponchon-Savarit trace must run from (xD, xD) to (xB, xB)
    # through the core operating points, bowed away from the
    # light-grey straight-line trace by the benzene-toluene default
    # deviation (0.0086 in mole fraction, band 0.005 to 0.012).
    report["psxy_check"] = page.evaluate("""() => {
      const gd = document.querySelector('#fig-psxy');
      if (!gd || !gd.data) return null;
      const grey = gd.data.find(
        t => t.name && t.name.includes('McCabe'));
      const ps = gd.data.find(
        t => t.name && t.name.includes('Ponchon'));
      if (!grey || !ps) return {grey: !!grey, ps: !!ps};
      const lineY = (x) => {
        const [xb, xi, xd] = grey.x, [yb, yi, yd] = grey.y;
        return x >= xi ? yi + (yd - yi) * (x - xi) / (xd - xi)
                       : yb + (yi - yb) * (x - xb) / (xi - xb);
      };
      let maxDev = 0;
      for (let i = 1; i < ps.x.length - 1; i++)
        maxDev = Math.max(maxDev,
          Math.abs(ps.y[i] - lineY(ps.x[i])));
      return {n_points: ps.x.length, max_dev: maxDev,
        first: [ps.x[0], ps.y[0]],
        last: [ps.x[ps.x.length - 1], ps.y[ps.y.length - 1]],
        grey_x: grey.x, grey_y: grey.y};
    }""")
    _psxy = report["psxy_check"]
    assert _psxy and _psxy["n_points"] == 16 \
        and 0.005 < _psxy["max_dev"] < 0.012 \
        and _psxy["first"] == [0.95, 0.95] \
        and _psxy["last"] == [0.05, 0.05], _psxy
    report["metric_cards"] = page.locator("#metrics .metric").count()
    page.locator("#app-psxy").screenshot(path=str(QA / "app-psxy-1440.png"))
    print("shot app-psxy-1440.png")
    report["stage_rows"] = page.locator("#stage-rows tr").count()
    report["step_label"] = page.locator("#stepct").inner_text()
    shot(page, "app-1440.png")
    # sticky tab bar: scroll and measure
    page.evaluate("window.scrollTo(0, 900)")
    page.wait_for_timeout(300)
    box = page.locator("nav.tabs").bounding_box()
    report["sticky_top_after_scroll"] = None if box is None else round(box["y"], 1)
    page.evaluate("window.scrollTo(0, 0)")
    # live run if the runtime becomes ready (CDN reachable)
    status = ""
    for _ in range(30):
        status = page.locator("#run-status").inner_text()
        if "ready" in status or "failed" in status:
            break
        page.wait_for_timeout(1000)
    report["run_status_after_boot"] = status
    report["live_run"] = "not attempted (runtime not ready in sandbox)"
    if "ready" in status:
        page.select_option("#sys", "ethanol-water")
        page.wait_for_timeout(200)
        page.click("#run")
        for _ in range(60):
            s = page.locator("#run-status").inner_text()
            if "complete" in s or "failed" in s:
                break
            page.wait_for_timeout(1000)
        report["live_run_status"] = page.locator("#run-status").inner_text()
        report["live_metrics_first"] = page.locator(
            "#metrics .metric .v").first.inner_text()
        report["live_run"] = "ethanol-water live solve attempted"
        shot(page, "app-live-ethanol-1440.png")
        page.reload()
        page.wait_for_timeout(2500)
    # stages mode: drive the render functions with synthetic result
    # objects (live Pyodide is unavailable in the sandbox). First the
    # control-state checks, then a solved hold-xD result, then an
    # unsolved one; the prestart run is restored afterwards.
    page.check("input[name='specmode'][value='stages']")
    page.wait_for_timeout(200)
    report["stages_controls"] = page.evaluate("""() => ({
      N_visible: document.getElementById('ctl-N').style.display !== 'none',
      RabsIn_visible: document.getElementById('ctl-RabsIn').style.display !== 'none',
      Rmult_hidden: document.getElementById('ctl-Rmult').style.display === 'none',
      xB_disabled: document.getElementById('xB').disabled,
      xD_disabled: document.getElementById('xD').disabled })""")
    page.check("input[name='prodbasis'][value='D']")
    page.wait_for_timeout(200)
    report["stages_controls_D"] = page.evaluate("""() => ({
      Drate_visible: document.getElementById('ctl-Drate').style.display !== 'none',
      xD_disabled: document.getElementById('xD').disabled,
      xB_disabled: document.getElementById('xB').disabled })""")
    page.check("input[name='prodbasis'][value='hold_xD']")
    page.check("input[name='specmode'][value='compositions']")
    page.wait_for_timeout(200)
    stages_js = """() => {
      const pre = JSON.parse(
        document.getElementById('prestart-data').textContent);
      const r = JSON.parse(JSON.stringify(pre.result));
      r.mode = 'stages'; r.hold = 'xD'; r.product_basis = 'hold_xD';
      r.reflux_basis = 'abs'; r.N_stages = 15; r.D_spec = null;
      r.R_mult_implied = 1.3;
      Object.assign(r.mt, {xD_out: r.xD, xB_out: 0.0206,
        stages_solved: true, limit: 'none', note: null,
        R_out: r.R, Rmin_out: r.R_min, D_kmol_s: 0.4082,
        B_kmol_s: 0.5918, condenser_T_C: r.condenser_T_C,
        reboiler_T_C: 110.9});
      Object.assign(r.ps, {xD_out: r.xD, xB_out: 0.0374,
        stages_solved: true, limit: 'none', note: null,
        R_out: r.R, Rmin_out: r.R_min, D_kmol_s: 0.399,
        B_kmol_s: 0.601, condenser_T_C: r.condenser_T_C,
        reboiler_T_C: 109.6});
      displayResult(r, pre.spec);
      return r;
    }"""
    page.evaluate(stages_js)
    page.wait_for_timeout(600)
    txt = page.locator("#metrics").inner_text()
    report["stages_metrics_has_calculated"] = "calculated" in txt
    report["stages_metrics_has_specified_N"] = "15 (specified)" in txt
    # the reboiler row of the per-stage table must substitute the
    # Ponchon-Savarit run's own B (0.601 here), not the top-level
    # value (0.6111 in the prestart run)
    report["stages_table_last_row_L"] = page.locator(
        "#stage-rows tr").last.locator("td").nth(4).inner_text()
    shot(page, "app-stages-1440.png")
    page.evaluate("""() => {
      const pre = JSON.parse(
        document.getElementById('prestart-data').textContent);
      const r = JSON.parse(JSON.stringify(pre.result));
      r.mode = 'stages'; r.hold = 'xD'; r.product_basis = 'hold_xD';
      r.reflux_basis = 'abs'; r.N_stages = 15; r.D_spec = null;
      const un = {stages_solved: false, limit: 'pinch',
        note: '15 stages are not attainable at this reflux: the ' +
          'stepping pinches at every composition past the limit shown'};
      Object.assign(r.mt, {xD_out: r.xD, xB_out: 0.31,
        R_out: r.R, Rmin_out: r.R_min, D_kmol_s: 0.3, B_kmol_s: 0.7,
        condenser_T_C: r.condenser_T_C, reboiler_T_C: 99.0}, un);
      Object.assign(r.ps, {xD_out: r.xD, xB_out: 0.33,
        R_out: r.R, Rmin_out: r.R_min, D_kmol_s: 0.29, B_kmol_s: 0.71,
        condenser_T_C: r.condenser_T_C, reboiler_T_C: 98.0}, un);
      r.R_mult_implied = 1.0;
      displayResult(r, pre.spec);
    }""")
    page.wait_for_timeout(600)
    txt = page.locator("#metrics").inner_text()
    report["stages_unsolved_card"] = "not attainable at this reflux ratio" in txt
    report["stages_unsolved_suffix_pinch"] = "(pinch limit)" in txt
    report["stages_unsolved_banner"] = page.locator("#az-banner").inner_text()
    shot(page, "app-stages-unsolved-1440.png")
    # unsolved-card suffixes for the other limit kinds: the finite
    # count classes read "(limiting composition)" and the azeotrope
    # class "(azeotrope limit)", never "(pinch limit)"
    for limit, suffix in (("short", "(limiting composition)"),
                          ("exceeds", "(limiting composition)"),
                          ("azeotrope", "(azeotrope limit)")):
        page.evaluate("""(limit) => {
          const pre = JSON.parse(
            document.getElementById('prestart-data').textContent);
          const r = JSON.parse(JSON.stringify(pre.result));
          r.mode = 'stages'; r.hold = 'xD'; r.product_basis = 'hold_xD';
          r.reflux_basis = 'abs'; r.N_stages = 15; r.D_spec = null;
          const un = {stages_solved: false, limit: limit,
            note: 'synthetic unsolved run for suffix QA'};
          Object.assign(r.mt, {xD_out: r.xD, xB_out: 0.31,
            R_out: r.R, Rmin_out: r.R_min, D_kmol_s: 0.3, B_kmol_s: 0.7,
            condenser_T_C: r.condenser_T_C, reboiler_T_C: 99.0}, un);
          Object.assign(r.ps, {xD_out: r.xD, xB_out: 0.33,
            R_out: r.R, Rmin_out: r.R_min, D_kmol_s: 0.29, B_kmol_s: 0.71,
            condenser_T_C: r.condenser_T_C, reboiler_T_C: 98.0}, un);
          r.R_mult_implied = 1.0;
          displayResult(r, pre.spec);
        }""", limit)
        page.wait_for_timeout(300)
        txt = page.locator("#metrics").inner_text()
        report["stages_suffix_" + limit] = (
            suffix in txt and "(pinch limit)" not in txt)
    page.evaluate("""() => {
      const pre = JSON.parse(
        document.getElementById('prestart-data').textContent);
      displayResult(pre.result, pre.spec);
    }""")
    page.wait_for_timeout(400)
    # F1 validation: stages mode, distillate-rate basis, D typed as
    # 0.999 at zF = 0.40 must be rejected by runSolve before any
    # solve (workerReady is forced so the validation is reached in
    # the sandbox, where the Pyodide CDN is unreachable)
    page.check("input[name='specmode'][value='stages']")
    page.check("input[name='prodbasis'][value='D']")
    page.wait_for_timeout(200)
    page.evaluate("""() => {
      document.getElementById('DrateNum').value = '0.999';
      workerReady = true;
      document.getElementById('run').disabled = false;
    }""")
    page.click("#run")
    page.wait_for_timeout(300)
    report["f1_banner"] = page.locator("#az-banner").inner_text()
    report["f1_metrics_cleared"] = page.locator("#metrics .metric").count() == 0
    page.check("input[name='specmode'][value='compositions']")
    page.wait_for_timeout(200)
    # Ray-endpoint assertions (v6 amendment): every Ponchon-Savarit
    # construction ray must start at its section pole and end at the
    # farther of the stage's liquid point and the next stage's vapour
    # point, with the nearer point on the drawn segment. Checked on
    # the prestart run and on a core-produced stages-mode state, in
    # the full view and in a 3-shown stepped view.
    raycheck_js = """(shown) => {
      const r = current;
      const trace = document.querySelector('#fig-ps').data
        .find(t => t.name === 'Rays to difference points');
      const segs = []; let cur = [];
      for (let i = 0; i <= trace.x.length; i++) {
        if (i === trace.x.length || trace.x[i] === null) {
          if (cur.length) segs.push(cur); cur = [];
        } else cur.push([trace.x[i], trace.y[i]]);
      }
      const eq = r.eq_curve, st = r.ps.stages;
      const ip = (xs, ys, x) => {
        if (x <= xs[0]) return ys[0];
        if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
        let lo = 0, hi = xs.length - 1;
        while (hi - lo > 1) { const m = (lo + hi) >> 1;
          if (xs[m] <= x) lo = m; else hi = m; }
        const t = (x - xs[lo]) / (xs[hi] - xs[lo]);
        return ys[lo] + t * (ys[hi] - ys[lo]);
      };
      const xDp = r.mode === 'stages' ? r.ps.xD_out : r.xD;
      const xBp = r.mode === 'stages' ? r.ps.xB_out : r.xB;
      const nShow = Math.min(shown, st.length);
      const T = 1e-9;
      const out = {segments: segs.length, expected: 0, start_ok: 0,
        end_ok: 0, near_ok: 0, rect: 0, strip: 0, end_liquid: 0,
        end_vapour: 0, fails: []};
      let idx = 0;
      for (let k = 1; k <= nShow; k++) {
        if (k >= st.length) break;
        out.expected++;
        const s = st[k - 1];
        const hL = ip(eq.x, eq.h_liq, s.x);
        const rect = s.x > r.ps.x_tie_feed;
        const px = rect ? xDp : xBp, pH = rect ? r.ps.H_DD : r.ps.H_DB;
        const yn = st[k].y, Hn = ip(eq.y, eq.H_vap, yn);
        const liqFar = Math.abs(hL - pH) >= Math.abs(Hn - pH);
        const far = liqFar ? [s.x, hL] : [yn, Hn];
        const near = liqFar ? [yn, Hn] : [s.x, hL];
        if (rect) out.rect++; else out.strip++;
        if (liqFar) out.end_liquid++; else out.end_vapour++;
        const seg = segs[idx++];
        if (!seg || seg.length !== 2) {
          out.fails.push('k=' + k + ': segment missing or not a pair');
          continue;
        }
        const a = seg[0], b = seg[1];
        if (Math.abs(a[0] - px) <= T && Math.abs(a[1] - pH) <= T) {
          out.start_ok++;
        } else out.fails.push('k=' + k + ': start != pole');
        if (Math.abs(b[0] - far[0]) <= T &&
            Math.abs(b[1] - far[1]) <= T) {
          out.end_ok++;
        } else out.fails.push('k=' + k + ': end != farther point');
        const dx = b[0] - a[0], dy = b[1] - a[1];
        let t, dev;
        if (Math.abs(dy) >= Math.abs(dx)) {
          t = (near[1] - a[1]) / dy; dev = Math.abs(a[0] + t * dx - near[0]);
        } else {
          t = (near[0] - a[0]) / dx; dev = Math.abs(a[1] + t * dy - near[1]);
        }
        if (dev <= T && t >= -T && t <= 1 + T) out.near_ok++;
        else out.fails.push('k=' + k + ': nearer point off segment');
      }
      out.all_ok = out.segments === out.expected && !out.fails.length &&
        out.start_ok === out.expected && out.end_ok === out.expected &&
        out.near_ok === out.expected;
      return out;
    }"""
    page.click("#tabbtn-app")
    page.evaluate("""() => {
      const pre = JSON.parse(
        document.getElementById('prestart-data').textContent);
      displayResult(pre.result, pre.spec);
    }""")
    page.wait_for_timeout(500)
    report["ray_prestart_full"] = page.evaluate(raycheck_js, 1000000)
    page.evaluate("stepShown = 3; renderPS(current, stepShown);")
    page.wait_for_timeout(300)
    report["ray_prestart_step3"] = page.evaluate(raycheck_js, 3)
    sys.path.insert(0, str(ROOT / "python"))
    import mtps_core as _mc
    ray_spec = {"system": "alpha", "alpha_value": 2.5,
                "latent_ratio": 1.0, "zF": 0.40, "feed_mode": "q",
                "q": 1.0, "P_atm": 1.0, "spec_mode": "stages",
                "product_basis": "hold_xB", "reflux_basis": "abs",
                "xB": 0.05, "R_abs": 0.77, "N_stages": 15}
    ray_res = json.loads(json.dumps(_mc.solve_column(ray_spec)))
    page.evaluate("""([res, spec]) => displayResult(res, spec)""",
                  [ray_res, ray_spec])
    page.wait_for_timeout(500)
    report["ray_stages_full"] = page.evaluate(raycheck_js, 1000000)
    page.locator("#fig-ps").screenshot(path=str(QA / "ps-stages-full.png"))
    print("shot ps-stages-full.png")
    page.evaluate("stepShown = 3; renderPS(current, stepShown);")
    page.wait_for_timeout(300)
    report["ray_stages_step3"] = page.evaluate(raycheck_js, 3)
    page.evaluate("""() => {
      const pre = JSON.parse(
        document.getElementById('prestart-data').textContent);
      displayResult(pre.result, pre.spec);
    }""")
    page.wait_for_timeout(400)
    page.click("#tabbtn-theory")
    page.wait_for_timeout(600)
    shot(page, "theory-1440.png")
    report["theory_toc_links"] = page.locator("#theory-toc a").count()
    report["katex_spans"] = page.locator("#theory-body .katex").count()
    page.click("#tabbtn-code")
    page.wait_for_timeout(400)
    shot(page, "code-listings-1440.png")
    page.click("button[data-sub='walkthrough']")
    page.wait_for_timeout(1200)
    shot(page, "code-walkthrough-1440.png")
    report["walk_figs"] = page.locator(".walkfig").count()
    # phone width
    page.set_viewport_size({"width": 390, "height": 844})
    page.click("#tabbtn-app")
    page.wait_for_timeout(800)
    report["hscroll_390"] = page.evaluate(
        "document.documentElement.scrollWidth")
    shot(page, "app-390.png")
    page.click("#tabbtn-theory")
    page.wait_for_timeout(500)
    shot(page, "theory-390.png")
    # wide monitor: header vs body column edges
    page.set_viewport_size({"width": 2560, "height": 1200})
    page.click("#tabbtn-app")
    page.wait_for_timeout(600)
    edges = page.evaluate("""() => {
      const col = document.querySelector('.page-col').getBoundingClientRect();
      const head = document.querySelector('header.page-head').getBoundingClientRect();
      return {colL: col.left, colR: col.right, headL: head.left, headR: head.right,
              scrollW: document.documentElement.scrollWidth};
    }""")
    report["edges_2560"] = edges
    shot(page, "app-2560.png", full=False)
    # Fig. 3 in a pinched run and at one shown stage (v7): a pinched
    # Ponchon-Savarit run (synthetic preset, latent-heat ratio 2.0)
    # stalls at liquid mole fraction about 0.529, so the drawn curve
    # must stay open there and must not close at (xB, xB); and with
    # one stage shown the curve must already carry the first
    # operating point, as Figs. 1 and 2 carry that stage's corner
    # and ray.
    pinch_spec = {"system": "alpha", "alpha_value": 2.5,
                  "latent_ratio": 2.0, "zF": 0.5, "xD": 0.95,
                  "xB": 0.05, "R_mult": 1.3, "feed_mode": "q",
                  "q": 1.0, "P_atm": 1.0}
    pinch_res = json.loads(json.dumps(_mc.solve_column(pinch_spec)))
    assert pinch_res["ps"]["pinched"]
    page.evaluate("""([res, spec]) => displayResult(res, spec)""",
                  [pinch_res, pinch_spec])
    page.wait_for_timeout(500)
    report["psxy_pinched"] = page.evaluate("""() => {
      const gd = document.querySelector('#fig-psxy');
      const ps = gd.data.find(
        t => t.name && t.name.includes('Ponchon'));
      return {n: ps.x.length,
        last: [ps.x[ps.x.length - 1], ps.y[ps.y.length - 1]]};
    }""")
    _pp = report["psxy_pinched"]
    assert _pp["last"][0] > 0.5 and _pp["last"] != [0.05, 0.05], _pp
    page.evaluate("stepShown = 1; renderPSXY(current, stepShown);")
    page.wait_for_timeout(300)
    report["psxy_step1_points"] = page.evaluate("""() => {
      const gd = document.querySelector('#fig-psxy');
      const ps = gd.data.find(
        t => t.name && t.name.includes('Ponchon'));
      return ps.x.length;
    }""")
    assert report["psxy_step1_points"] == 2, report["psxy_step1_points"]
    page.locator("#app-psxy").screenshot(
        path=str(QA / "app-psxy-pinched-1440.png"))
    print("shot app-psxy-pinched-1440.png")
    browser.close()

print(json.dumps(report, indent=1))
(QA / "report.json").write_text(json.dumps(report, indent=1))
bad = report["console_errors"] or report["page_errors"]
sys.exit(1 if bad else 0)
