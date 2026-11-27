#!/usr/bin/env python3
"""Browser regression test for the v66 video-wall fixes:
fraction-true group playback, stall resume tied to play
intent, and privacy coverage of the wall's text surfaces.

The reports (the teacher, 2026-11-27, on v65): "Videos
fall out of sync (stop playing still not robust) in wall
view" — tiles that started together drifted apart (the
screenshot showed tiles at 82-85% after playing together)
and stalled tiles stayed stopped.

Root causes, in the v65 code: (1) the wall's model is
fraction-based (the master scrub seeks every tile to the
same fraction, the badges show fractions) but setSpeed()
set the SAME playbackRate on every tile regardless of
duration, so a short tile's fraction advanced faster
than a long tile's by the duration ratio (about 2.5x
between a 19:44 and a 50:35 take) and the shortest tile
ended and stopped; (2) a tile whose playback stopped
mid-play (a cancelled play(), a buffer underrun on a long
take) had no resume path tied to the wall's playing
intent — _autoplay existed only for the zoom round trip
and seek landings.

Phase A (sync): Play-all on tiles of differing durations
(the demo takes run 58-210 s); after a settle, the tiles'
fractions must stay within 0.10 of each other over a 12 s
window, and each tile's playbackRate divided by its
duration — its fraction rate — must agree across tiles
within 15% (the direct fraction-true property). On v65
the rates are all 1, so the fraction rates disagree by
the duration ratio and the spread grows past tolerance.

Phase B (the user's sequence, tiles playing): deep range
fetches are held for HOLD_S seconds (the v65 harness's
latency model), one tile is scrubbed forward by a real
right-button drag, the holds are released, and every tile
that was playing must land at the scrub fraction AND be
playing; a control tile paused beforehand through the
wall's own pause state (intent cleared, as Pause-all
leaves it) must land and stay paused.

Phase B2 (stall resume, state level): a tile left paused
with its frame gone but its play intent recorded — the
state a cancelled play() leaves behind on a long take —
must resume playing on its own; a tile without intent
must not. On v65 the intent does not exist and nothing
resumes the tile.

Phase P (privacy): with the Hide names & grades choice
on, the wall's hover panel must contain no student name
outside a .priv element, and the transcript block must
carry the priv class (free text is barred whole).

Run:  python3 tests/wall_regression_v66.py
(needs playwright + a Chromium build; on the Muse machine
that is ~/workspace/.venvs/qa-playwright/bin/python3).
Scratch state goes to a temp folder, or to $WALL_V66_SCRATCH.
The app copy under test can be redirected with
$WALL_V66_APPDIR (used to run the same harness against a
v65 checkout: Phase A, B and B2 fail there).
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

HERE = Path(os.environ.get("WALL_V66_APPDIR") or
            Path(__file__).resolve().parent.parent)
PORT = 8798
BASE = f"http://127.0.0.1:{PORT}"
HOLD_S = float(os.environ.get("WALL_V66_HOLD_S", "7"))
TARGET = 0.85

STATE_JS = """() => [...document.querySelectorAll('#grid video')].map(v => {
  const tile = v.closest('.tile');
  return {rs: v.readyState, t: Math.round(v.currentTime*10)/10,
          dur: Math.round((v.duration||0)*10)/10,
          frac: v.duration ? Math.round(v.currentTime/v.duration*1000)/1000 : 0,
          rate: v.playbackRate,
          seeking: v.seeking, paused: v.paused, ended: v.ended,
          wantPlay: !!v._wantPlay,
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
        if st and all(s["rs"] >= 2 for s in st):
            return st
        await page.wait_for_timeout(500)
    return st


async def run(page, demo_names):
    # ---- Phase P: privacy coverage of the wall text ----
    await page.goto(BASE + "/wall")
    await page.wait_for_selector("#grid video", timeout=30000)
    st = await framed(page)
    report(bool(st), f"initial wall paints ({len(st)} tiles)",
           json.dumps(st))
    box = await page.locator("#grid .tile").nth(0).bounding_box()
    await page.mouse.move(box["x"] + box["width"] / 2,
                          box["y"] + 60)
    await page.wait_for_timeout(2500)
    priv = await page.evaluate("""(names) => {
      const out = {root: document.documentElement.classList
                     .contains('privacy-on'),
                   transPriv: document.getElementById('hptrans')
                     .classList.contains('priv'),
                   found: 0, leaks: []};
      const panel = document.getElementById('hoverpanel');
      const walker = document.createTreeWalker(panel,
        NodeFilter.SHOW_TEXT);
      let node;
      while (node = walker.nextNode()) {
        if (!names.some(nm => node.textContent.includes(nm)))
          continue;
        out.found += 1;
        let el = node.parentElement, covered = false;
        while (el && el !== panel) {
          if (el.classList && el.classList.contains('priv'))
            { covered = true; break; }
          el = el.parentElement;
        }
        if (!covered) out.leaks.push(node.textContent.trim());
      }
      return out;
    }""", demo_names)
    report(priv["root"] and priv["transPriv"] and priv["found"] > 0
           and not priv["leaks"],
           "privacy on: no student name is visible in the wall "
           "hover panel and the transcript block is priv-barred",
           json.dumps(priv))
    await page.mouse.move(5, 5)
    await page.click("#pauseall")
    await page.evaluate(
        "() => localStorage.setItem('ta-privacy-v1', '0')")
    await page.reload()
    await page.wait_for_selector("#grid video", timeout=30000)
    # Shrink the page capacity so the phases below watch a
    # handful of tiles, not a dozen.
    await page.evaluate("""() => {
      const t = document.getElementById('tilesize');
      t.value = 560; t.dispatchEvent(new Event('input'));
    }""")
    await page.wait_for_timeout(1200)
    st = await framed(page)
    durs = [s["dur"] for s in st if s["dur"]]
    report(len(st) >= 3 and max(durs) / min(durs) >= 2,
           f"sync phases watch {len(st)} tiles with durations "
           f"{sorted(durs)} (ratio >= 2)", json.dumps(st))
    n = len(st)

    # ---- Phase A: fraction-true group playback ----
    await page.click("#playall")
    await page.wait_for_timeout(3000)
    samples = []
    for _ in range(12):
        samples.append(await page.evaluate(STATE_JS))
        await page.wait_for_timeout(1000)
    last = samples[-1]
    live = [s for s in last if s["dur"] and not s["ended"]]
    spread = (max(s["frac"] for s in live)
              - min(s["frac"] for s in live)) if live else 1
    advanced = (sum(s["frac"] for s in live) / len(live)
                if live else 0)
    frates = [s["rate"] / s["dur"] for s in live if s["dur"]]
    fr_spread = (max(frates) / min(frates)) if frates else 99
    print("PHASE-A samples: " + " | ".join(
        f"t+{i*1}s spread="
        f"{(max(s['frac'] for s in sm if s['dur']) - min(s['frac'] for s in sm if s['dur'])):.3f}"
        for i, sm in enumerate(samples[::4])), flush=True)
    report(advanced > 0.04 and spread <= 0.10,
           f"Play-all: tiles stay in fraction sync (spread "
           f"{spread:.3f} <= 0.10 after ~15 s, mean fraction "
           f"{advanced:.3f})", json.dumps(last))
    report(fr_spread <= 1.15,
           f"Play-all: fraction rates agree across tiles "
           f"(max/min {fr_spread:.2f} <= 1.15)",
           json.dumps([{ "dur": s["dur"], "rate": s["rate"]}
                       for s in live]))

    # ---- Phase B: scrub while playing, fetches held ----
    # Control tile: paused through the wall's own pause
    # state — intent cleared exactly as Pause-all leaves it.
    await page.evaluate("""() => {
      const v = document.querySelectorAll('#grid video')[0];
      v._wantPlay = false; v._autoplay = false; v.pause();
    }""")
    holds = {"live": True, "held": 0}

    async def handler(route):
        rng = route.request.headers.get("range", "")
        deep = False
        if rng.startswith("bytes="):
            try:
                deep = int(rng[6:].split("-")[0] or 0) > 65536
            except ValueError:
                deep = False
        if deep and holds["live"]:
            holds["held"] += 1
            await asyncio.sleep(HOLD_S)
        try:
            await route.continue_()
        except Exception:
            pass

    await page.route("**/media/demo/*", handler)
    # The wall's scrub is relative: the drag distance is
    # added to the master fraction where the drag starts
    # (the tiles are playing, at ~0.15 by now), so the
    # travel is TARGET minus the current mean fraction.
    st_now = await page.evaluate(STATE_JS)
    f0 = sum(s["frac"] for s in st_now) / len(st_now)
    box = await page.locator("#grid .tile").nth(1).bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + 60
    travel = TARGET - f0
    await page.mouse.move(cx, cy)
    await page.mouse.down(button="right")
    for f in (0.4, 0.75, 1.0):
        await page.mouse.move(cx + box["width"] * travel * f, cy)
        await page.wait_for_timeout(60)
    await page.mouse.up(button="right")
    await page.wait_for_timeout(3000)
    holds["live"] = False
    t0 = time.time()
    st = await page.evaluate(STATE_JS)
    while time.time() - t0 < 45:
        st = await page.evaluate(STATE_JS)
        others = st[1:]
        if all(abs(s["frac"] - TARGET) <= 0.06 and not s["paused"]
               for s in others) and st[0]["paused"]:
            break
        await page.wait_for_timeout(1000)
    others = st[1:]
    report(all(abs(s["frac"] - TARGET) <= 0.06 for s in others),
           f"scrub while playing: every playing tile lands at "
           f"{TARGET} ({holds['held']} deep fetches held)",
           json.dumps(st))
    report(all(not s["paused"] for s in others),
           "scrub while playing: every tile that was playing "
           "is playing again after the scrub lands",
           json.dumps(st))
    report(st[0]["paused"]
           and abs(st[0]["frac"] - TARGET) <= 0.06,
           "scrub while playing: the user-paused control tile "
           "lands at the target and is NOT resumed",
           json.dumps(st[0]))
    await page.unroute("**/media/demo/*", handler)

    # ---- Phase B2: stall resume from play intent ----
    await page.evaluate("""() => {
      const vs = document.querySelectorAll('#grid video');
      const v = vs[1];
      // The state a cancelled play() leaves on a long take:
      // intent recorded, element paused, frame gone.
      v._wantPlay = true;
      const p = v.play(); if (p) p.catch(() => {});
      v.load();
      const c = vs[0];
      c._wantPlay = false; c._autoplay = false; c.pause();
    }""")
    t0 = time.time()
    st = await page.evaluate(STATE_JS)
    while time.time() - t0 < 45:
        st = await page.evaluate(STATE_JS)
        if not st[1]["paused"] and st[0]["paused"]:
            break
        await page.wait_for_timeout(1000)
    report(not st[1]["paused"],
           "stall resume: a paused tile carrying play intent "
           "resumes on its own", json.dumps(st[1]))
    report(st[0]["paused"],
           "stall resume: a tile without play intent is never "
           "revived", json.dumps(st[0]))
    return n


async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("SKIP: playwright is not installed")
        return 3
    scratch = Path(os.environ.get("WALL_V66_SCRATCH") or
                   tempfile.mkdtemp(prefix="wall-v66-"))
    scratch.mkdir(parents=True, exist_ok=True)
    proc = start_app(scratch)
    try:
        demos = seed_demos()
        demo_names = [d["name"] for d in demos]
        async with async_playwright() as pw:
            b = await pw.chromium.launch(
                args=["--autoplay-policy=no-user-gesture-required",
                      "--media-cache-size=0",
                      "--disk-cache-size=0"])
            ctx = await b.new_context(
                viewport={"width": 1700, "height": 1100})
            await ctx.add_init_script(
                "try{localStorage.setItem('ta-privacy-v1','1')}"
                "catch(e){}")
            page = await ctx.new_page()
            page.on("console", lambda m: print(
                "CONSOLE:", m.type, m.text[:160], flush=True))
            await run(page, demo_names)
            await page.screenshot(
                path=str(scratch / "wall-v66-final.png"))
            await b.close()
    finally:
        proc.terminate()
    if FAILURES:
        print(f"WALL V66 REGRESSION: FAIL ({len(FAILURES)})")
        return 1
    print("WALL V66 REGRESSION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
