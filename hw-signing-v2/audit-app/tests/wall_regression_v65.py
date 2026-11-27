#!/usr/bin/env python3
"""Browser regression test for the v65 video-wall fix: a
quick forward scrub of one tile strands the other tiles.

The report (the teacher, 2026-11-27, on v64): on the wall,
scrubbing one video forward quickly left most tiles at the
scrub fraction (84-85%) but several black at 0% (0:00 of
long takes), and those tiles "fail when hovered over and
get lost in the view" — they never recovered without a
reload.

Reproduction model: the wall runs against the app's demo
students (58-210 s takes). Real takes are 20-50 minutes
served from the teacher's disk under load, so a far seek's
range fetch takes seconds — longer than the stall
watchdog's 3 s patience and the 1.5 s time-boxed hover
play. The harness models exactly that latency, and nothing
else, by request interception: every media request whose
Range starts deep in its file (a far seek's fetch) is held
for HOLD_S seconds before it is allowed to continue. The
initial bytes=0- fetches pass at once. This does not model
the media server serialising requests (it does not: the
server is threaded with no locks) — it models per-fetch
latency, which is the part of the load that reaches the
wall's seek machinery.

The sequence is the user's: tiles are reloaded so no seek
can be served from a whole-file buffer, the holds are
armed, one tile is scrubbed forward quickly by a real
right-button drag (the wall's own scrub path, WALLSEEK ->
setFracAll), and the wall is then watched. A stranded tile
is hovered, as the user did.

Asserts (v65): every tile reaches the scrub fraction
(±0.06, keyframe tolerance) framed within 25 s of the
scrub — about three times the modelled fetch latency —
no tile sits frameless (black) at any sample from 4 s
after the scrub on, a hovered stranded tile does not lose
its seek, and the displayed percentage of a tile with an
unlanded scrub target is the target, not 0%.

On v64 this harness FAILS, and the failure is the
demonstrated root cause (traces in the v65 work record):
the stall watchdog's patience (3 s) is shorter than a real
far-seek fetch, so it reloads each network-dependent tile
while its seek fetch is still in flight — discarding the
fetch, the frame and the position (the tile sits black at
0%, readyState 0, for tens of seconds) — re-seeks, and
repeats until its 3-retry budget is exhausted; the tile
recovers only if the last re-issued fetch happens to
survive uninterrupted (~40 s at a 7 s fetch latency, and
not at all if anything interrupts that fetch too).

Run:  python3 tests/wall_regression_v65.py
(needs playwright + a Chromium build; on the Muse machine
that is ~/workspace/.venvs/qa-playwright/bin/python3).
Scratch state goes to a temp folder, or to $WALL_V65_SCRATCH.
The app copy under test can be redirected with
$WALL_V65_APPDIR (used to run the same harness against a
v64 checkout during development).
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

HERE = Path(os.environ.get("WALL_V65_APPDIR") or
            Path(__file__).resolve().parent.parent)
PORT = 8797
BASE = f"http://127.0.0.1:{PORT}"
HOLD_S = float(os.environ.get("WALL_V65_HOLD_S", "7"))
TARGET = 0.85

STATE_JS = """() => [...document.querySelectorAll('#grid video')].map(v => {
  let px = null;
  try {
    const c = document.createElement('canvas'); c.width = 32; c.height = 18;
    const g = c.getContext('2d'); g.drawImage(v, 0, 0, 32, 18);
    const d = g.getImageData(0, 0, 32, 18).data;
    let sum = 0, n = 0;
    for (let i = 0; i < d.length; i += 4) { sum += d[i] + d[i+1] + d[i+2]; n++; }
    px = Math.round(sum / n * 10) / 10;
  } catch (e) { px = -1; }
  const tile = v.closest('.tile');
  const badge = tile ? document.getElementById('pct_' + tile.dataset.id) : null;
  return {rs: v.readyState, t: Math.round(v.currentTime*10)/10,
          dur: Math.round((v.duration||0)*10)/10,
          frac: v.duration ? Math.round(v.currentTime/v.duration*1000)/1000 : 0,
          seeking: v.seeking, paused: v.paused, px,
          retries: v._stallRetries || 0,
          wantFrac: (v._wantFrac === undefined ? null : v._wantFrac),
          targetFrac: (v._targetFrac === undefined ? null : v._targetFrac),
          buf: [...Array(v.buffered.length)].map((_, i) =>
            Math.round(v.buffered.start(i)) + '-' +
            Math.round(v.buffered.end(i))).join(','),
          badge: badge ? badge.textContent : null};
})"""

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


def seed_demos():
    http("/api/demos/generate", "POST")
    deadline = time.time() + 240
    while time.time() < deadline:
        try:
            j = http("/api/wall?local=1")
            demos = [s for s in j["students"] if s.get("video_url")]
            if len(demos) >= 8:
                return demos
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError("demo students did not appear on the wall")


async def clear_http_cache(page):
    try:
        ses = await page.context.new_cdp_session(page)
        await ses.send("Network.enable")
        await ses.send("Network.clearBrowserCache")
        await ses.detach()
    except Exception:
        pass


def landed(st):
    return [abs(s["frac"] - TARGET) <= 0.06 and s["rs"] >= 2
            and s["px"] is not None and s["px"] > 0 for s in st]


async def run(page):
    await page.goto(BASE + "/wall")
    await page.wait_for_selector("#grid video", timeout=30000)
    # Every tile framed at the start.
    t0 = time.time()
    st = []
    while time.time() - t0 < 45:
        st = await page.evaluate(STATE_JS)
        if st and all(s["rs"] >= 2 and s["px"] and s["px"] > 0
                      for s in st):
            break
        await page.wait_for_timeout(500)
    report(bool(st) and all(s["rs"] >= 2 and s["px"] and s["px"] > 0
                            for s in st),
           f"initial wall paints every tile ({len(st)} tiles)",
           json.dumps(st))
    n = len(st)

    # Reload every tile so the scrub's seeks cannot be
    # served from a whole-file buffer: after load() only the
    # metadata is fetched (preload=metadata), and a far seek
    # genuinely needs the network the harness then holds.
    await clear_http_cache(page)
    await page.evaluate("""() => {
      document.querySelectorAll('#grid video').forEach(v => v.load());
    }""")
    await page.wait_for_function(
        "[...document.querySelectorAll('#grid video')]"
        ".every(v => v.duration > 0)", timeout=30000)

    # Arm the holds: every deep range request (a far seek's
    # fetch) waits HOLD_S seconds before continuing.
    holds = {"live": True, "held": 0, "seen": []}

    async def handler(route):
        rng = route.request.headers.get("range", "")
        deep = False
        if rng.startswith("bytes="):
            try:
                deep = int(rng[6:].split("-")[0] or 0) > 65536
            except ValueError:
                deep = False
        holds["seen"].append(
            f"{route.request.url.split('/')[-1]}:{rng or '-'}")
        if deep and holds["live"]:
            holds["held"] += 1
            await asyncio.sleep(HOLD_S)
        try:
            await route.continue_()
        except Exception:
            pass

    await page.route("**/media/demo/*", handler)

    # The user's sequence: a quick right-button drag on one
    # tile, forward to 85% of the take, in a few quick steps
    # (the wall's own scrub path: WALLSEEK -> setFracAll).
    # The drag starts at the tile's centre, so the pointer
    # travels TARGET tile-widths from there.
    box = await page.locator("#grid .tile").nth(0).bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + 60
    await page.mouse.move(cx, cy)
    await page.mouse.down(button="right")
    for f in (0.3, 0.55, TARGET):
        await page.mouse.move(cx + box["width"] * f, cy)
        await page.wait_for_timeout(60)
    await page.mouse.up(button="right")
    print("REQUESTS: " + "; ".join(holds["seen"]), flush=True)
    t_scrub = time.time()
    report(True, f"quick right-drag scrub to {TARGET} done "
                 f"(tile width {box['width']:.0f} px)")

    # Watch the wall for up to 30 s, tracing each tile.
    trace = []
    deadline = time.time() + 30
    st = await page.evaluate(STATE_JS)
    while time.time() < deadline:
        st = await page.evaluate(STATE_JS)
        trace.append((round(time.time() - t_scrub, 1), st))
        if all(landed(st)):
            break
        await page.wait_for_timeout(1000)
    for ts, snap in trace[::2]:
        print(f"TRACE t={ts:5.1f} " + " | ".join(
            f"#{i}:f={s['frac']:.2f},rs={s['rs']},sk={int(s['seeking'])},"
            f"r={s['retries']},px={s['px']},buf={s['buf']}"
            for i, s in enumerate(snap)), flush=True)
    print("REQUESTS-TOTAL: held=" + str(holds["held"]) + " seen="
          + "; ".join(holds["seen"]), flush=True)
    ok = all(landed(st))
    report(ok, f"every tile reaches the scrub fraction {TARGET} "
               f"framed within 25 s of the scrub "
               f"({time.time()-t_scrub:.0f} s, {holds['held']} "
               f"deep fetches held)", json.dumps(st))
    black = [(ts, i) for ts, snap in trace if ts >= 4.0
             for i, s in enumerate(snap)
             if not s["px"] or s["px"] <= 0]
    report(not black,
           "no tile sits frameless (black) at any sample from "
           "4 s after the scrub on",
           f"black samples (t, tile): {black[:12]}")
    stranded = [i for i, s in enumerate(st)
                if not (abs(s["frac"] - TARGET) <= 0.06)]
    report(not stranded or all(st[i]["seeking"] or
                               st[i]["targetFrac"] is not None
                               for i in stranded),
           "no tile is abandoned: any tile not at the target "
           "is still seeking or carries a live target",
           f"stranded={stranded} " + json.dumps(
               [st[i] for i in stranded]))

    # The displayed percentage of a tile with an unlanded
    # target must be the target, never a reset 0%.
    bad_badge = [i for i, s in enumerate(st)
                 if abs(s["frac"] - TARGET) > 0.06 and s["badge"]
                 and s["badge"].startswith("0%")]
    report(not bad_badge,
           "no tile with an unlanded scrub target displays 0%",
           f"badges={[st[i]['badge'] for i in bad_badge]}")

    # Hover a tile that is not at the target (or tile 3 if
    # all landed): hovering must not lose its seek — after
    # the hover leaves, the tile must still land.
    hi = stranded[0] if stranded else 3
    holds["live"] = False   # network recovers; recovery is the app's
    box = await page.locator("#grid .tile").nth(hi).bounding_box()
    await page.mouse.move(box["x"] + box["width"] / 2,
                          box["y"] + 60)
    await page.wait_for_timeout(2500)
    await page.mouse.move(5, 5)
    t0 = time.time()
    st = await page.evaluate(STATE_JS)
    while time.time() - t0 < 40:
        st = await page.evaluate(STATE_JS)
        if abs(st[hi]["frac"] - TARGET) <= 0.06 and st[hi]["rs"] >= 2:
            break
        await page.wait_for_timeout(1000)
    report(abs(st[hi]["frac"] - TARGET) <= 0.06 and st[hi]["rs"] >= 2,
           f"hovered tile #{hi} still lands at the scrub "
           f"fraction after the hover", json.dumps(st[hi]))

    await page.unroute("**/media/demo/*", handler)
    return n


async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("SKIP: playwright is not installed")
        return 3
    scratch = Path(os.environ.get("WALL_V65_SCRATCH") or
                   tempfile.mkdtemp(prefix="wall-v65-"))
    scratch.mkdir(parents=True, exist_ok=True)
    proc = start_app(scratch)
    try:
        seed_demos()
        async with async_playwright() as pw:
            b = await pw.chromium.launch(
                args=["--autoplay-policy=no-user-gesture-required",
                      "--media-cache-size=0",
                      "--disk-cache-size=0"])
            page = await b.new_page(viewport={"width": 1700,
                                              "height": 1100})
            page.on("console", lambda m: print(
                "CONSOLE:", m.type, m.text[:160], flush=True))
            await run(page)
            await page.screenshot(
                path=str(scratch / "wall-v65-final.png"))
            await b.close()
    finally:
        proc.terminate()
    if FAILURES:
        print(f"WALL V65 REGRESSION: FAIL ({len(FAILURES)})")
        return 1
    print("WALL V65 REGRESSION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
