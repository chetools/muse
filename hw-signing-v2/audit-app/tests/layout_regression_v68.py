#!/usr/bin/env python3
"""Browser regression test for the v68 dashboard layout
fixes: the Setup section's two decoupled columns, the
taller Activity log, and the wider Final grade input.

The reports (the teacher, 2026-11-27, on v67): "a lot of
unnecessary wasted whitespace, and 'how it works' causes
other column to move down. Activity log could be
vertically longer for a more natural aspect ratio.
Finally grade should be wider to fit 2 digits."

Root causes, in the v67 code: (1) the Save settings row,
the course details and the status line sat BELOW the
Setup section's two-column flex row as full-width
siblings, so expanding the "How this works" details in
the Activity column grew the row and pushed all three
down by the details' height (measured on v67: 82 px);
the flex row's default stretch also sized the settings
column's box by the Activity column's content, leaving
a void under the settings fields. (2) The Activity log
stood 190 px tall. (3) The Final grade number input
(input.fin) was 52 px wide — a 32 px content box for
two digits plus the spinner.

This harness measures the rendered geometry: with the
Section-1 "How this works" collapsed vs expanded, every
element of the settings (left) column — its first label,
its fields, the Save settings button, the course
details and the status line — must keep the same Y
position, and the settings column's own height must not
change; the Activity log's client height must be at
least 350 px; and a Final grade input rendered in a
real submissions-table row (injected with the row
markup the dashboard itself builds, since this scratch
app has no Canvas data) must take the widened width and
not overflow its cell. On the v67 code the settings
column's lower elements move 82 px, the log stands
206 px and the input takes 52 px, so all three groups
fail there.

Run:  python3 tests/layout_regression_v68.py
(needs playwright + a Chromium build; on the Muse
machine that is ~/workspace/.venvs/qa-playwright/bin/
python3). Scratch state goes to a temp folder, or to
$LAYOUT_V68_SCRATCH. The app copy under test can be
redirected with $LAYOUT_V68_APPDIR (used to run the
same harness against a v67 checkout).
"""
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(os.environ.get("LAYOUT_V68_APPDIR") or
            Path(__file__).resolve().parent.parent)
PORT = 8799
BASE = f"http://127.0.0.1:{PORT}"

MEASURE_JS = """() => {
  const y = el => el ? Math.round((el.getBoundingClientRect().top
                    + window.scrollY) * 10) / 10 : null;
  return {
    firstLabelY: y(document.querySelector('section .col label')),
    canvasInputY: y(document.getElementById('canvas_base_url')),
    workerInputY: y(document.getElementById('worker_base_url')),
    saveBtnY: y(document.getElementById('savecfg')),
    courseDetailsY: y(document.getElementById('coursedetails')),
    cfgmetaY: y(document.getElementById('cfgmeta')),
    leftColH: Math.round(document.querySelector('section .col')
                         .getBoundingClientRect().height),
    logClientH: document.getElementById('activitylog')
                  .clientHeight,
  };
}"""

FIN_JS = """() => {
  const tb = document.getElementById('subs');
  const cells = Array.from({length: 12}, () => '<td></td>');
  cells[10] = '<td class="fincell">'
    + '<input class="fin priv" type="number" min="0" max="10"'
    + ' value="10"> '
    + '<span class="mut finsign priv">signed 10</span> '
    + '<span class="mut finmsg"></span></td>';
  tb.innerHTML = '<tr>' + cells.join('') + '</tr>';
  const inp = tb.querySelector('input.fin');
  const td = inp.closest('td');
  return {inputW: inp.offsetWidth,
          cellClientW: td.clientWidth,
          cellScrollW: td.scrollWidth};
}"""

FAILURES = []


def report(ok, label, detail=""):
    print(("ok: " if ok else "FAIL: ") + label +
          ((" -- " + detail) if detail else ""), flush=True)
    if not ok:
        FAILURES.append(label)


def http(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return json.loads(r.read().decode())


def start_app(scratch):
    appdir = scratch / "app"
    shutil.copytree(HERE, appdir,
                    ignore=shutil.ignore_patterns(
                        "__pycache__", "config.json", "data"))
    cfg = {"canvas_token": "", "grading_admin_token": "",
           "data_dir": str(scratch / "data")}
    cfgpath = scratch / "config.json"
    cfgpath.write_text(json.dumps(cfg), encoding="utf-8")
    env = dict(os.environ, TEACHER_AUDIT_CONFIG=str(cfgpath),
               TMPDIR=str(scratch))
    proc = subprocess.Popen(
        [sys.executable, "web.py", "--port", str(PORT), "--no-browser"],
        cwd=appdir, env=env,
        stdout=open(scratch / "server.log", "w"),
        stderr=subprocess.STDOUT)
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            http("/api/status")
            return proc
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("app did not start; see server.log")


async def run(page, scratch):
    await page.goto(BASE + "/")
    await page.wait_for_selector("#activitylog", timeout=30000)
    await page.wait_for_timeout(800)
    before = await page.evaluate(MEASURE_JS)
    await page.click("section details.howitworks summary")
    await page.wait_for_timeout(400)
    after = await page.evaluate(MEASURE_JS)
    print("COLLAPSED:", json.dumps(before), flush=True)
    print("EXPANDED: ", json.dumps(after), flush=True)
    moved = [k for k in ("firstLabelY", "canvasInputY",
                         "workerInputY", "saveBtnY",
                         "courseDetailsY", "cfgmetaY",
                         "leftColH")
             if abs(after[k] - before[k]) > 1]
    report(not moved,
           "expanding 'How this works' moves nothing in the "
           "settings column (every element keeps its Y, the "
           "column keeps its height)",
           f"moved: {moved}" if moved else
           f"saveBtnY {before['saveBtnY']} -> "
           f"{after['saveBtnY']}, leftColH "
           f"{before['leftColH']} -> {after['leftColH']}")
    report(before["logClientH"] >= 350,
           f"Activity log stands tall (client height "
           f"{before['logClientH']} px >= 350; v67: 206)",
           json.dumps(before))
    fin = await page.evaluate(FIN_JS)
    print("FIN:", json.dumps(fin), flush=True)
    report(fin["inputW"] >= 74,
           f"Final grade input takes the widened width "
           f"({fin['inputW']} px >= 74; v67: 52)",
           json.dumps(fin))
    report(fin["cellScrollW"] <= fin["cellClientW"] + 1,
           "Final grade input and its signed-grade note fit "
           "their cell without overflow", json.dumps(fin))
    await page.screenshot(path=str(scratch / "dash-v68.png"))


async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("SKIP: playwright is not installed")
        return 3
    scratch = Path(os.environ.get("LAYOUT_V68_SCRATCH") or
                   tempfile.mkdtemp(prefix="layout-v68-"))
    scratch.mkdir(parents=True, exist_ok=True)
    proc = start_app(scratch)
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch()
            ctx = await b.new_context(
                viewport={"width": 1700, "height": 1100})
            page = await ctx.new_page()
            await run(page, scratch)
            await b.close()
    finally:
        proc.terminate()
    if FAILURES:
        print(f"LAYOUT V68 REGRESSION: FAIL ({len(FAILURES)})")
        return 1
    print("LAYOUT V68 REGRESSION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
