#!/usr/bin/env python3
"""Browser regression test for the v67 video-wall fix:
recovery of a tile whose video element errors.

The report (the teacher, 2026-11-27, on v66): some wall
tiles stop and stay black while others continue. The
instrumentation below (per-tile event timelines and
readyState/networkState/frame samples through load, a
master scrub, Play all and a scrub while playing, on
twelve tiles of differing durations) separates the
candidate causes:

- H2 (tiles that had not loaded when Play all was pressed
  never acquired play intent) is refuted by the v66 code:
  playTile records _wantPlay on every showing tile before
  any readiness check. Phases P2/P3 exercise it anyway.
- H4 (the server cannot serve twelve tiles at once) is
  not a server defect: the app serves media from a
  threading server with Range support; contention shows
  up as fetch latency, which the watchdog windows price
  in. The phases run unshaped first (P0-P3).
- H1 (a video element error strands the tile) is the
  demonstrated cause. Before v67 no 'error' handler
  existed anywhere on the wall, and every stall-watchdog
  branch passes an errored tile by: the target branch
  needs an unlanded scrub target, the v66 intent branch
  and the generic branch both need a duration, and an
  error early in a load destroys the duration. Phases E1
  and E2 put a tile into exactly that state — its media
  fetches fail fatally (route aborts) during a grid
  rebuild (E1: no target, no intent) and during playback
  with play intent recorded (E2) — then heal the route.
  On v66 the tile stays black (readyState 0, videoWidth
  0, error set) for the whole observation window; on v67
  the error recovery reloads it and it frames again
  (E1), playing again (E2).
- A second state was observed on v66 in the P3
  scenario, intermittently (two of six probe runs): a
  tile a scrub left paused — play intent set, data
  ready (readyState 3), not seeking, fraction at its
  target — standing across many watchdog visits whose
  play() calls did not restart it, a manual watchdog
  pass included. The v66 intent branch has no remedy
  beyond repeating play(); v67 escalates that branch to
  a reload at the tile's position after three visits.
  P3 asserts the end state (landed and playing) either
  way; E1/E2 are the deterministic v66 failures.

The twelve tiles are the eight generated demo takes plus
four extra demo entries rendered into the same demo
folder by this harness (durations 95-320 s), so the wall
holds a class-sized grid of differing lengths.

Run:  python3 tests/wall_regression_v67.py
(needs playwright + a Chromium build; on the Muse machine
that is ~/workspace/.venvs/qa-playwright/bin/python3).
Scratch state goes to a temp folder, or to $WALL_V67_SCRATCH.
The app copy under test can be redirected with
$WALL_V67_APPDIR (used to run the same harness against a
v66 checkout: phases E1 and E2 fail there).
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

HERE = Path(os.environ.get("WALL_V67_APPDIR") or
            Path(__file__).resolve().parent.parent)
PORT = 8799
BASE = f"http://127.0.0.1:{PORT}"
EXTRA = [("demo-09", "Demo: Extra Nine", 95, 262),
         ("demo-10", "Demo: Extra Ten", 150, 330),
         ("demo-11", "Demo: Extra Eleven", 240, 392),
         ("demo-12", "Demo: Extra Twelve", 320, 440)]

STATE_JS = """() => [...document.querySelectorAll('#grid video')].map(v => {
  const tile = v.closest('.tile');
  return {rs: v.readyState, ns: v.networkState,
          vw: v.videoWidth,
          t: Math.round(v.currentTime*10)/10,
          dur: Math.round((v.duration||0)*10)/10,
          frac: v.duration ? Math.round(v.currentTime/v.duration*1000)/1000 : 0,
          seeking: v.seeking, paused: v.paused, ended: v.ended,
          err: v.error ? v.error.code : null,
          wantPlay: !!v._wantPlay,
          src: v.src || "",
          id: tile ? tile.dataset.id : null};
})"""

INSTR_JS = """
window.__TL = {};
window.__instr = function(v){
  if (v.__instrDone) return; v.__instrDone = true;
  const tile = v.closest('.tile');
  const id = tile ? tile.dataset.id : (v.id || 'zv');
  const tl = window.__TL[id] || (window.__TL[id] = {events: [], samples: []});
  tl.el = v;
  ['error','stalled','waiting','playing','canplay','seeked','seeking',
   'ended','abort','emptied','loadedmetadata','loadeddata','suspend']
   .forEach(e => v.addEventListener(e, () => {
     tl.events.push([Math.round(performance.now()/100)/10, e,
                     v.error ? v.error.code : null,
                     v.readyState, v.networkState]);
     if (tl.events.length > 300) tl.events.shift();
   }));
};
try {
  new MutationObserver(() => {
    document.querySelectorAll('#grid video').forEach(window.__instr);
  }).observe(document.documentElement, {subtree: true, childList: true});
} catch (e) {}
setInterval(() => {
  document.querySelectorAll('#grid video').forEach(v => {
    window.__instr(v);
    const tile = v.closest('.tile'); if (!tile) return;
    const tl = window.__TL[tile.dataset.id]; if (!tl) return;
    tl.samples.push([Math.round(performance.now()/100)/10,
                     v.readyState, v.networkState, v.videoWidth,
                     Math.round(v.currentTime*10)/10, v.paused,
                     v.seeking, v.error ? v.error.code : null,
                     !!v._wantPlay,
                     v.duration ? Math.round(v.currentTime/v.duration*1000)/1000 : null]);
    if (tl.samples.length > 240) tl.samples.shift();
  });
}, 500);
"""

FAILURES = []


def report(ok, label, detail=""):
    print(("ok: " if ok else "FAIL: ") + label +
          ((" -- " + detail) if detail else ""), flush=True)
    if not ok:
        FAILURES.append(label)


def http(path, method="GET"):
    req = urllib.request.Request(BASE + path, method=method,
                                 data=b"{}" if method == "POST" else None,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
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


def seed_demos(scratch):
    http("/api/demos/generate", "POST")
    # Wait for the GENERATED set's data file (the wall can
    # show the bundled set first; the extras must extend the
    # generated folder the app will prefer).
    ddir = scratch / "data" / "demo-videos"
    dfile = ddir / "demo-data.json"
    deadline = time.time() + 240
    data = None
    while time.time() < deadline:
        try:
            data = json.loads(dfile.read_text(encoding="utf-8"))
            if len(data) >= 8:
                break
        except Exception:
            pass
        time.sleep(2)
    if not data or len(data) < 8:
        raise RuntimeError("demo generation did not finish")
    # Four extra demo takes in the same folder, so the wall
    # holds twelve tiles of differing durations.
    for sid, name, dur, tone in EXTRA:
        out = ddir / f"{sid}.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error",
             "-f", "lavfi", "-i",
             f"testsrc2=size=640x360:rate=10:duration={dur}",
             "-f", "lavfi", "-i",
             f"sine=frequency={tone}:duration={dur}",
             "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-crf", "30", "-c:a", "aac", str(out)], check=True)
        data.append({
            "id": sid, "name": name, "email": "",
            "source": "demo", "video_file": out.name,
            "duration_s": dur, "completeness": 4, "accuracy": 4,
            "integrity": "clean",
            "critique": "Harness demo take.",
            "transcript": [{"t": 0, "text": "harness demo take"}]})
    (ddir / "demo-data.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8")
    deadline = time.time() + 60
    while time.time() < deadline:
        j = http("/api/wall?local=1")
        demos = [s for s in j["students"] if s.get("video_url")]
        if len(demos) >= 12:
            return demos
        time.sleep(1)
    raise RuntimeError("extended demo set did not reach 12 tiles")


async def wait_until(page, pred_js, timeout, label):
    t0 = time.time()
    st = await page.evaluate(STATE_JS)
    while time.time() - t0 < timeout:
        st = await page.evaluate(STATE_JS)
        if await page.evaluate(pred_js, st):
            return st, True
        await page.wait_for_timeout(700)
    return st, False


async def digest(page, tid):
    return await page.evaluate("""(id) => {
      const tl = window.__TL[id];
      if (!tl) return 'no timeline';
      return JSON.stringify({
        events: tl.events.slice(-14),
        samples: tl.samples.slice(-6)});
    }""", tid)


async def run(page):
    await page.goto(BASE + "/wall")
    await page.wait_for_selector("#grid video", timeout=30000)
    await page.evaluate("""() => {
      const t = document.getElementById('tilesize');
      t.value = 260; t.dispatchEvent(new Event('input'));
    }""")
    await page.wait_for_timeout(1800)
    st, ok = await wait_until(
        page, """st => st.length >= 12 && st.every(s => s.rs >= 2 && s.vw > 0)""",
        60, "framed")
    report(ok and len(st) >= 12,
           f"P0 load: all {len(st)} tiles frame on load",
           "" if ok else json.dumps(st))

    # ---- P1: master scrub to 0.26 ----
    await page.evaluate("""() => {
      const sc = document.getElementById('scrub');
      sc.value = 260; sc.dispatchEvent(new Event('input'));
      sc.dispatchEvent(new Event('change'));
    }""")
    st, ok = await wait_until(
        page, """st => st.every(s => s.dur && Math.abs(s.frac - 0.26) <= 0.06 && s.vw > 0)""",
        45, "scrubbed")
    report(ok, "P1 scrub: every tile lands framed at 0.26",
           "" if ok else json.dumps(
               [s for s in st if not (s["dur"] and abs(s["frac"] - 0.26) <= 0.06 and s["vw"] > 0)]))

    # ---- P2: Play all, sustained ----
    await page.click("#playall")
    await page.wait_for_timeout(3000)
    before = {s["id"]: s["t"] for s in await page.evaluate(STATE_JS)}
    await page.wait_for_timeout(12000)
    st = await page.evaluate(STATE_JS)
    stopped = [s for s in st
               if s["paused"] or s["vw"] == 0
               or s["t"] - before.get(s["id"], 0) < 1.0]
    report(not stopped,
           "P2 play-all: every tile is playing and advancing "
           "after 15 s", json.dumps(stopped))

    # ---- P3: scrub while playing, to 0.60 ----
    f0 = sum(s["frac"] for s in st) / len(st)
    box = await page.locator("#grid .tile").nth(1).bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + 60
    travel = 0.60 - f0
    await page.mouse.move(cx, cy)
    await page.mouse.down(button="right")
    for f in (0.4, 0.75, 1.0):
        await page.mouse.move(cx + box["width"] * travel * f, cy)
        await page.wait_for_timeout(60)
    await page.mouse.up(button="right")
    st, ok = await wait_until(
        page, """st => st.every(s => s.dur && Math.abs(s.frac - 0.60) <= 0.06 && !s.paused && s.vw > 0)""",
        45, "scrub-playing")
    report(ok, "P3 scrub while playing: every tile lands at "
           "0.60 and is playing",
           "" if ok else json.dumps(
               [s for s in st if not (s["dur"] and abs(s["frac"] - 0.60) <= 0.06 and not s["paused"] and s["vw"] > 0)]))

    async def kill_route(fname):
        async def handler(route):
            await route.abort()
        await page.route(f"**/media/demo/{fname}", handler)
        return handler

    # ---- E1: fatal error during a rebuild (no target, no intent) ----
    await page.click("#pauseall")
    await page.wait_for_timeout(600)
    st = await page.evaluate(STATE_JS)
    victim = st[5]
    fname = victim["src"].split("/")[-1]
    handler = await kill_route(fname)
    await page.evaluate("() => render()")
    t0 = time.time()
    err_seen = False
    while time.time() - t0 < 20:
        cur = await page.evaluate(STATE_JS)
        row = next((s for s in cur if s["id"] == victim["id"]), None)
        if row and row["err"] is not None:
            err_seen = True
            break
        await page.wait_for_timeout(500)
    report(err_seen,
           "E1: the rebuilt tile's element errors while its "
           "fetches fail (non-vacuous)", json.dumps(row or {}))
    await page.unroute(f"**/media/demo/{fname}", handler)
    t0 = time.time()
    ok = False
    while time.time() - t0 < 30:
        cur = await page.evaluate(STATE_JS)
        row = next((s for s in cur if s["id"] == victim["id"]), None)
        if row and row["rs"] >= 2 and row["vw"] > 0 and row["err"] is None:
            ok = True
            break
        await page.wait_for_timeout(700)
    report(ok, "E1: the errored tile frames again once its "
           "fetches heal (v66: stranded black)",
           "" if ok else await digest(page, victim["id"]))

    # ---- E2: fatal error under play intent ----
    # The victim must itself be playing; the whole wall
    # need not be (on v66 the E1 victim is already dead —
    # that is E1's failure, not E2's precondition).
    await page.click("#playall")
    st, okp = await wait_until(
        page, """st => st.length >= 3 && !st[2].paused && st[2].rs >= 2""",
        45, "victim2-playing")
    report(okp, "E2 precondition: the victim tile is playing "
           "before its error is induced", json.dumps(st[2] if len(st) > 2 else st))
    victim2 = st[2]
    fname2 = victim2["src"].split("/")[-1]
    handler2 = await kill_route(fname2)
    await page.evaluate("""(id) => {
      const t = [...document.querySelectorAll('.tile')]
        .find(x => x.dataset.id === id);
      const v = t && t.querySelector('video');
      if (v) v.load();
    }""", victim2["id"])
    t0 = time.time()
    err_seen = False
    while time.time() - t0 < 20:
        cur = await page.evaluate(STATE_JS)
        row = next((s for s in cur if s["id"] == victim2["id"]), None)
        if row and row["err"] is not None:
            err_seen = True
            break
        await page.wait_for_timeout(500)
    report(err_seen,
           "E2: the playing tile's element errors when its "
           "reload fetches fail (non-vacuous)",
           json.dumps(row or {}))
    await page.unroute(f"**/media/demo/{fname2}", handler2)
    t0 = time.time()
    ok = False
    while time.time() - t0 < 45:
        cur = await page.evaluate(STATE_JS)
        row = next((s for s in cur if s["id"] == victim2["id"]), None)
        if row and row["rs"] >= 2 and row["vw"] > 0 \
                and row["err"] is None and not row["paused"]:
            ok = True
            break
        await page.wait_for_timeout(700)
    report(ok, "E2: the errored playing tile frames and plays "
           "again once its fetches heal (v66: stranded — the "
           "intent branch needs a duration the error destroyed)",
           "" if ok else await digest(page, victim2["id"]))
    await page.click("#pauseall")


async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("SKIP: playwright is not installed")
        return 3
    scratch = Path(os.environ.get("WALL_V67_SCRATCH") or
                   tempfile.mkdtemp(prefix="wall-v67-"))
    scratch.mkdir(parents=True, exist_ok=True)
    proc = start_app(scratch)
    try:
        seed_demos(scratch)
        async with async_playwright() as pw:
            b = await pw.chromium.launch(
                args=["--autoplay-policy=no-user-gesture-required",
                      "--media-cache-size=0",
                      "--disk-cache-size=0"])
            ctx = await b.new_context(
                viewport={"width": 1700, "height": 1100})
            await ctx.add_init_script(INSTR_JS)
            page = await ctx.new_page()
            page.on("console", lambda m: print(
                "CONSOLE:", m.type, m.text[:160], flush=True))
            await run(page)
            await page.screenshot(
                path=str(scratch / "wall-v67-final.png"))
            await b.close()
    finally:
        proc.terminate()
    if FAILURES:
        print(f"WALL V67 REGRESSION: FAIL ({len(FAILURES)})")
        return 1
    print("WALL V67 REGRESSION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
