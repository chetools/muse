#!/usr/bin/env python3
"""Browser regression test for the v68 video-wall fix:
the audible tile plays at exactly the wall speed.

The report (the teacher, 2026-11-27, on v67): the wall's
videos "have audio that sound strange and are playing
at different rates" — since v66, group playback is
fraction-true: each tile's playbackRate is the wall
speed scaled by its duration against the longest
showing tile, so every tile audibly plays at a
different rate, including the one tile the teacher is
listening to (the hover-audio owner). The differing
rates are the app's own scaling — a recording's frame
rate does not drive HTML5 playback timing — so v68
changes the sync reference: while a tile owns the
audio (claimAudio records the owner, AUDIOOWNER), the
reference is that tile's duration, so its rate is
exactly the wall speed and the muted tiles are rated
relative to it; with no audible tile the reference is
the longest showing tile, as in v66. Pitch is
preserved (preservesPitch, set explicitly).

Phases (tiles of differing durations, wall speed set
to 1.5 so the rates are unmistakable):
  R0 (no audio owner): the longest tile's rate is the
     wall speed and the fraction rates agree — the v66
     behaviour stands when nothing is audible.
  R1 (hover the second-longest tile): that tile owns
     the audio (it is the one unmuted tile), its
     playbackRate is exactly the wall speed, the muted
     tiles' fraction rates still agree (now against
     the owner's duration), and preservesPitch is set
     on every tile. On v67 the owner's rate is
     1.5 x (its duration / the longest duration) and
     this phase fails.
  R2 (hover the longest tile instead): ownership and
     the reference move — the new owner's rate is
     exactly the wall speed and the previous owner is
     re-rated relative to it.
  R3 (pointer leaves the wall): ownership is released
     and the reference returns to the longest tile.

Run:  python3 tests/wall_regression_v68.py
(needs playwright + a Chromium build; on the Muse
machine that is ~/workspace/.venvs/qa-playwright/bin/
python3). Scratch state goes to a temp folder, or to
$WALL_V68_SCRATCH. The app copy under test can be
redirected with $WALL_V68_APPDIR (used to run the
same harness against a v67 checkout: R1-R3 fail there).
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

HERE = Path(os.environ.get("WALL_V68_APPDIR") or
            Path(__file__).resolve().parent.parent)
PORT = 8800
BASE = f"http://127.0.0.1:{PORT}"
SPEED = 1.5

STATE_JS = """() => [...document.querySelectorAll('#grid video')].map(v => {
  const tile = v.closest('.tile');
  return {dur: Math.round((v.duration||0)*10)/10,
          rate: v.playbackRate, muted: v.muted,
          pitch: v.preservesPitch,
          id: tile ? tile.dataset.id : null};
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


async def framed(page, timeout=45):
    t0 = time.time()
    st = []
    while time.time() - t0 < timeout:
        st = await page.evaluate(STATE_JS)
        if st and all(s["dur"] for s in st):
            return st
        await page.wait_for_timeout(500)
    return st


def frate_spread(st):
    fr = [s["rate"] / s["dur"] for s in st if s["dur"]]
    return (max(fr) / min(fr)) if fr else 99


async def hover_tile(page, tile_id):
    box = await page.locator(
        f'.tile[data-id="{tile_id}"]').bounding_box()
    await page.mouse.move(box["x"] + box["width"] / 2,
                          box["y"] + 40)
    await page.wait_for_timeout(900)


async def run(page):
    await page.goto(BASE + "/wall")
    await page.wait_for_selector("#grid video", timeout=30000)
    st = await framed(page)
    report(bool(st), f"initial wall paints ({len(st)} tiles)",
           json.dumps(st))
    # Watch a handful of tiles, as in the v66 harness.
    await page.evaluate("""() => {
      const t = document.getElementById('tilesize');
      t.value = 560; t.dispatchEvent(new Event('input'));
    }""")
    await page.wait_for_timeout(1200)
    st = await framed(page)
    durs = sorted(s["dur"] for s in st if s["dur"])
    report(len(st) >= 3 and durs[-1] / durs[0] >= 2,
           f"rate phases watch {len(st)} tiles with durations "
           f"{durs} (ratio >= 2)", json.dumps(st))
    by_dur = sorted(st, key=lambda s: s["dur"])
    longest = by_dur[-1]
    second = by_dur[-2]
    # Set the wall speed to 1.5 through the wall's own
    # control, so the rates below are unmistakable.
    await page.evaluate("""() => {
      const sp = document.getElementById('speed');
      sp.value = '1.5';
      sp.dispatchEvent(new Event('change'));
    }""")
    await page.wait_for_timeout(400)

    # ---- R0: no audio owner — the v66 reference stands
    st = await page.evaluate(STATE_JS)
    cur = {s["id"]: s for s in st}
    report(abs(cur[longest["id"]]["rate"] - SPEED) < 0.01
           and frate_spread(st) <= 1.15,
           f"R0 no owner: the longest tile plays at the wall "
           f"speed and fraction rates agree (spread "
           f"{frate_spread(st):.2f})", json.dumps(st))

    # ---- R1: hover the second-longest tile — it owns
    # the audio and must play at exactly the wall speed.
    await hover_tile(page, second["id"])
    st = await page.evaluate(STATE_JS)
    cur = {s["id"]: s for s in st}
    owner = cur[second["id"]]
    unmuted = [s["id"] for s in st if not s["muted"]]
    report(unmuted == [second["id"]],
           "R1: the hovered tile is the one unmuted tile "
           "(it owns the audio)", json.dumps(st))
    report(abs(owner["rate"] - SPEED) < 1e-9,
           f"R1: the audible tile's playbackRate is exactly "
           f"the wall speed ({owner['rate']} == {SPEED})",
           json.dumps(owner))
    report(frate_spread(st) <= 1.15,
           f"R1: the muted tiles' fraction rates still "
           f"agree, rated relative to the owner (spread "
           f"{frate_spread(st):.2f})", json.dumps(st))
    report(all(s["pitch"] for s in st),
           "R1: preservesPitch is set on every tile",
           json.dumps(st))

    # ---- R2: hover the longest tile — ownership and
    # the reference move with it.
    await hover_tile(page, longest["id"])
    st = await page.evaluate(STATE_JS)
    cur = {s["id"]: s for s in st}
    expect_second = SPEED * second["dur"] / longest["dur"]
    report(abs(cur[longest["id"]]["rate"] - SPEED) < 1e-9
           and abs(cur[second["id"]]["rate"] - expect_second)
               < 0.01
           and frate_spread(st) <= 1.15,
           f"R2: the new owner plays at exactly the wall "
           f"speed and the previous owner is re-rated "
           f"relative to it ({cur[second['id']]['rate']:.3f} "
           f"~= {expect_second:.3f})", json.dumps(st))

    # ---- R3: pointer leaves — ownership released, the
    # reference returns to the longest tile.
    await page.mouse.move(5, 5)
    await page.wait_for_timeout(900)
    st = await page.evaluate(STATE_JS)
    cur = {s["id"]: s for s in st}
    report(abs(cur[longest["id"]]["rate"] - SPEED) < 0.01
           and abs(cur[second["id"]]["rate"] - expect_second)
               < 0.01
           and all(s["muted"] for s in st),
           "R3: with the pointer gone every tile is muted "
           "and the longest tile is the reference again",
           json.dumps(st))


async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("SKIP: playwright is not installed")
        return 3
    scratch = Path(os.environ.get("WALL_V68_SCRATCH") or
                   tempfile.mkdtemp(prefix="wall-v68-"))
    scratch.mkdir(parents=True, exist_ok=True)
    proc = start_app(scratch)
    try:
        seed_demos()
        async with async_playwright() as pw:
            b = await pw.chromium.launch(
                args=["--autoplay-policy=no-user-gesture-required",
                      "--media-cache-size=0",
                      "--disk-cache-size=0"])
            ctx = await b.new_context(
                viewport={"width": 1700, "height": 1100})
            page = await ctx.new_page()
            page.on("console", lambda m: print(
                "CONSOLE:", m.type, m.text[:160], flush=True))
            await run(page)
            await page.screenshot(
                path=str(scratch / "wall-v68-final.png"))
            await b.close()
    finally:
        proc.terminate()
    if FAILURES:
        print(f"WALL V68 REGRESSION: FAIL ({len(FAILURES)})")
        return 1
    print("WALL V68 REGRESSION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
