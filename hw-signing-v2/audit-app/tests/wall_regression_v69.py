#!/usr/bin/env python3
"""Browser regression test for the v69 video-wall
durability rebuild: one desired state, one reconciler,
wall proxy files, and the Chrome-first opener's wall
side (the browser the wall runs in is recorded).

The report (the teacher, 2026-11-27, on v68): "All the
videos play initially and then eventually have issues."
The files are playable; failure developed during a
session, under sustained many-tile load, in the
teacher's default browser (Firefox; every wall harness
to date runs Chromium). v69 answers on three fronts —
the app opens in Chrome with a dedicated profile (the
opener is unit-tested in tests/test_web.py §33; a
headless harness cannot exercise it), the wall's
playback supervision is rebuilt around one persisted
desired state (WALLSTATE) and one periodic reconciler
replacing the v64–v68 watchdog's case branches, and
the wall's tiles play low-resolution proxy files so a
screenful of tiles no longer decodes the full
originals for a whole session.

Phases:
  P0 (browser note): loading the wall records the
     browser's user-agent in the Activity log — one
     line naming the browser behind any future report.
  P1 (proxies): proxies are generated for three demo
     videos with the app's own make_video_proxy (the
     measured size effect is printed); after a reload
     those tiles play their .proxy.mp4 and the other
     tiles still play their originals; the zoom view
     on a proxied tile plays the ORIGINAL.
  P2 (stranding with no legacy flags): the wall is set
     playing; one tile is then force-paused, moved to
     a wrong fraction, and its intent registers are
     cleared consistently (_wantPlay and _projPlay both
     false — the flags carry no intent at all) while
     WALLSTATE still says playing at the master
     fraction. No user action follows: the reconciler
     must return the tile to playing at the wall's
     fraction unaided. On the v64–v68 watchdog this
     state had no branch: no target, no intent, no
     error, a frame present.
  P3 (zoom round trip): the wall is paused at 0.45;
     opening the zoom view and pressing Back restores
     every tile to that fraction.
  P4 (zoom whose video never loads): the same round
     trip with the zoom's original file blocked at the
     network layer, so the zoom video never gets a
     duration. Before v69 Back sought the whole wall
     to the zoom video's fraction — 0 in this state —
     and the wall came back at 0%; the persisted
     fraction must survive.

Run:  python3 tests/wall_regression_v69.py
(needs playwright + a Chromium build; on the Muse
machine that is ~/workspace/.venvs/qa-playwright/bin/
python3). Scratch state goes to a temp folder, or to
$WALL_V69_SCRATCH. The app copy under test can be
redirected with $WALL_V69_APPDIR.
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

HERE = Path(os.environ.get("WALL_V69_APPDIR") or
            Path(__file__).resolve().parent.parent)
PORT = 8801
BASE = f"http://127.0.0.1:{PORT}"

STATE_JS = """() => [...document.querySelectorAll('#grid video')].map(v => {
  const tile = v.closest('.tile');
  return {id: tile ? tile.dataset.id : null,
          dur: v.duration || 0,
          frac: v.duration ? v.currentTime / v.duration : 0,
          paused: v.paused, ended: v.ended,
          ready: v.readyState,
          src: v.currentSrc || v.src || ''};
})"""

FAILURES = []


def report(ok, label, detail=""):
    print(("ok: " if ok else "FAIL: ") + label +
          ((" -- " + detail) if detail else ""), flush=True)
    if not ok:
        FAILURES.append(label)


def http(path, method="GET"):
    req = urllib.request.Request(
        BASE + path, method=method,
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
        [sys.executable, "web.py", "--port", str(PORT),
         "--no-browser"],
        cwd=appdir, env=env,
        stdout=open(scratch / "server.log", "w"),
        stderr=subprocess.STDOUT)
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            http("/api/status")
            return proc, appdir, cfgpath
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


def make_proxies(appdir, cfgpath, files):
    """Generate proxies for the given demo files with the
    scratch app's own make_video_proxy, in a subprocess
    that imports the scratch copy's web.py."""
    code = (
        "import sys, json\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "import web\n"
        "out = {}\n"
        "for f in json.loads(sys.argv[2]):\n"
        "    p = web.make_video_proxy(f)\n"
        "    out[f] = str(p) if p else None\n"
        "print(json.dumps(out))\n")
    env = dict(os.environ, TEACHER_AUDIT_CONFIG=str(cfgpath))
    proc = subprocess.run(
        [sys.executable, "-c", code, str(appdir),
         json.dumps([str(f) for f in files])],
        capture_output=True, text=True, timeout=900, env=env)
    if proc.returncode != 0:
        raise RuntimeError("proxy generation failed: "
                           + proc.stderr[-400:])
    return json.loads(proc.stdout.strip().splitlines()[-1])


def probe(path):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {}
    out = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,r_frame_rate",
         "-of", "json", str(path)],
        capture_output=True, text=True)
    try:
        st = json.loads(out.stdout)["streams"][0]
        num, _, den = st.get("r_frame_rate", "0/1").partition("/")
        return {"width": st.get("width"),
                "fps": round(float(num) / float(den or 1), 1)}
    except Exception:
        return {}


async def framed(page, timeout=45):
    t0 = time.time()
    st = []
    while time.time() - t0 < timeout:
        st = await page.evaluate(STATE_JS)
        if st and all(s["dur"] for s in st):
            return st
        await page.wait_for_timeout(500)
    return st


async def wait_until(page, js, timeout=25):
    t0 = time.time()
    val = None
    while time.time() - t0 < timeout:
        val = await page.evaluate(js)
        if val:
            return val
        await page.wait_for_timeout(400)
    return val


async def run(page, scratch, appdir, cfgpath, demos):
    await page.goto(BASE + "/wall")
    await page.wait_for_selector("#grid video", timeout=30000)
    st = await framed(page)
    report(bool(st), f"initial wall paints ({len(st)} tiles)",
           json.dumps(st)[:200])
    # A handful of tiles on screen, as in the v66 harness.
    await page.evaluate("""() => {
      const t = document.getElementById('tilesize');
      t.value = 560; t.dispatchEvent(new Event('input'));
    }""")
    await page.wait_for_timeout(1200)
    st = await framed(page)
    report(len(st) >= 3, f"phases watch {len(st)} tiles",
           json.dumps([s["id"] for s in st]))

    # ---- P0: the browser note reached the Activity log
    noted = False
    for _ in range(10):
        act = http("/api/activity")
        noted = any("video wall opened in" in (e.get("msg") or "")
                    and "Chrome" in (e.get("msg") or "")
                    for e in act.get("entries", []))
        if noted:
            break
        time.sleep(1)
    report(noted, "P0: the wall load recorded the browser "
                  "in the Activity log")

    # ---- P1: proxies — generate for three demo videos,
    # measure, and check which file each tile plays.
    demo_dir = scratch / "data" / "demo-videos"
    targets = []
    for s in demos[:3]:
        name = s["video_url"].split("/")[-1]
        targets.append((s["id"], demo_dir / name))
    made = make_proxies(appdir, cfgpath,
                        [f for _id, f in targets])
    measured = []
    all_made = True
    for sid, f in targets:
        proxy = Path(made[str(f)]) if made.get(str(f)) else None
        if proxy is None or not proxy.exists():
            all_made = False
            continue
        so, sp = f.stat().st_size, proxy.stat().st_size
        po, pp = probe(f), probe(proxy)
        measured.append(
            f"{f.name}: {so} -> {sp} bytes "
            f"({100.0 * sp / max(1, so):.0f}%), "
            f"width {po.get('width')} -> {pp.get('width')}, "
            f"fps {po.get('fps')} -> {pp.get('fps')}")
    for line in measured:
        print("proxy:", line, flush=True)
    report(all_made and len(measured) == len(targets),
           "P1: proxies generated for three demo videos",
           "; ".join(measured))
    tot_o = sum(f.stat().st_size for _i, f in targets)
    tot_p = sum((demo_dir / (f.stem + ".proxy.mp4")).stat().st_size
                for _i, f in targets)
    print(f"proxy totals: {tot_o} -> {tot_p} bytes "
          f"({100.0 * tot_p / max(1, tot_o):.1f}% of the "
          f"originals)", flush=True)

    await page.reload()
    await page.wait_for_selector("#grid video", timeout=30000)
    st = await framed(page)
    proxied_ids = {sid for sid, _f in targets}
    wiring = []
    for s in st:
        want_proxy = s["id"] in proxied_ids
        is_proxy = s["src"].endswith(".proxy.mp4")
        wiring.append(want_proxy == is_proxy)
    report(all(wiring) and st,
           "P1: proxied tiles play their proxy, the rest "
           "play their originals",
           json.dumps([(s["id"], s["src"].split("/")[-1])
                       for s in st]))
    # The zoom view always plays the original.
    first = st[0]
    await page.click(f'.tile[data-id="{first["id"]}"]')
    await page.wait_for_function(
        "() => document.getElementById('zoom').style.display"
        " === 'block'", timeout=15000)
    zsrc = await page.evaluate(
        "() => { const zv = document.getElementById('zv');"
        " return zv.currentSrc || zv.src || ''; }")
    report(zsrc.endswith(first["src"].split("/")[-1].replace(
               ".proxy.mp4", ".mp4"))
           and ".proxy.mp4" not in zsrc,
           "P1: the zoom view plays the original, not the "
           "proxy", zsrc)
    await page.click("#backbtn")
    await page.wait_for_function(
        "() => document.getElementById('zoom').style.display"
        " !== 'block'", timeout=15000)
    await page.wait_for_timeout(800)

    # ---- P2: strand a tile with no legacy flags set.
    await page.evaluate("() => { setFracAll(0.4); playAll(); }")
    playing = await wait_until(page, """() => {
      const vs = [...document.querySelectorAll('#grid video')];
      return vs.length >= 3 && vs.every(v => !v.paused
        && v.duration) ? vs.length : 0;
    }""", timeout=30)
    report(bool(playing), "P2: the wall is playing before "
                          "the stranding")
    await page.evaluate("""() => {
      const v = document.querySelectorAll('#grid video')[1];
      v.pause();
      v.currentTime = 0.05 * v.duration;
      // The intent registers are cleared consistently:
      // the flags carry no intent at all. WALLSTATE is
      // not touched — it still says playing.
      v._wantPlay = false; v._projPlay = false;
      v._autoplay = false;
      v._targetFrac = undefined; v._wantFrac = undefined;
    }""")
    ws = await page.evaluate("() => WALLSTATE.playing")
    report(ws is True, "P2: the desired state still says "
                       "playing after the stranding")
    recovered = await wait_until(page, """() => {
      const vs = [...document.querySelectorAll('#grid video')];
      if (vs.length < 3) return 0;
      const t = vs[1];
      if (t.paused || !t.duration) return 0;
      const others = vs.filter((v, i) => i !== 1 && v.duration)
        .map(v => v.currentTime / v.duration)
        .sort((a, b) => a - b);
      const med = others[Math.floor(others.length / 2)];
      return Math.abs(t.currentTime / t.duration - med) < 0.12
        ? med : 0;
    }""", timeout=30)
    report(bool(recovered),
           "P2: the reconciler returned the stranded tile "
           "to playing at the wall's fraction, unaided",
           f"wall fraction ~{recovered}")
    await page.evaluate("() => pauseAll()")

    # ---- P3: the zoom round trip restores the fraction.
    await page.evaluate("() => setFracAll(0.45)")
    settled = await wait_until(page, """() => {
      const vs = [...document.querySelectorAll('#grid video')];
      return vs.length >= 3 && vs.every(v => v.duration
        && Math.abs(v.currentTime / v.duration - 0.45) < 0.05)
        ? 1 : 0;
    }""", timeout=30)
    report(bool(settled), "P3: the wall settled at 0.45")
    st = await page.evaluate(STATE_JS)
    await page.click(f'.tile[data-id="{st[0]["id"]}"]')
    await page.wait_for_function(
        "() => document.getElementById('zoom').style.display"
        " === 'block'", timeout=15000)
    await page.wait_for_timeout(1000)
    await page.click("#backbtn")
    await page.wait_for_function(
        "() => document.getElementById('zoom').style.display"
        " !== 'block'", timeout=15000)
    back = await wait_until(page, """() => {
      const vs = [...document.querySelectorAll('#grid video')];
      return vs.length >= 3 && vs.every(v => v.duration
        && Math.abs(v.currentTime / v.duration - 0.45) < 0.06)
        ? 1 : 0;
    }""", timeout=20)
    report(bool(back), "P3: Back restored every tile to "
                       "the set fraction (0.45)")

    # ---- P4: the zoom's video never loads — the wall
    # must still come back at the persisted fraction.
    st = await page.evaluate(STATE_JS)
    orig_name = st[0]["src"].split("/")[-1].replace(
        ".proxy.mp4", ".mp4")

    async def _abort69(route):
        await route.abort()

    await page.route("**/" + orig_name, _abort69)
    await page.click(f'.tile[data-id="{st[0]["id"]}"]')
    await page.wait_for_function(
        "() => document.getElementById('zoom').style.display"
        " === 'block'", timeout=15000)
    await page.wait_for_timeout(2500)
    zdur = await page.evaluate(
        "() => document.getElementById('zv').duration")
    report(zdur != zdur or not zdur,
           "P4: the blocked zoom video has no duration "
           "(it never loaded)", f"duration={zdur}")
    await page.click("#backbtn")
    await page.wait_for_function(
        "() => document.getElementById('zoom').style.display"
        " !== 'block'", timeout=15000)
    await page.unroute("**/" + orig_name)
    back4 = await wait_until(page, """() => {
      const vs = [...document.querySelectorAll('#grid video')];
      return vs.length >= 3 && vs.every(v => v.duration
        && Math.abs(v.currentTime / v.duration - 0.45) < 0.06)
        ? 1 : 0;
    }""", timeout=20)
    report(bool(back4), "P4: the wall returned at the "
                        "persisted fraction, not at the "
                        "unloaded zoom video's 0")


async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("SKIP: playwright is not installed")
        return 3
    scratch = Path(os.environ.get("WALL_V69_SCRATCH") or
                   tempfile.mkdtemp(prefix="wall-v69-"))
    scratch.mkdir(parents=True, exist_ok=True)
    proc, appdir, cfgpath = start_app(scratch)
    try:
        demos = seed_demos()
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
            await run(page, scratch, appdir, cfgpath, demos)
            await page.screenshot(
                path=str(scratch / "wall-v69-final.png"))
            await b.close()
    finally:
        proc.terminate()
    if FAILURES:
        print(f"WALL V69 REGRESSION: FAIL ({len(FAILURES)})")
        return 1
    print("WALL V69 REGRESSION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
