# Browser QA findings — steam ejector page v1 (parent, 2026-11-18)

Tool: Playwright (own Chromium 1255; the sandbox /opt/meta-chromium/chrome
refuses direct launch: "Hatch WebGL domain policy is required for browser
startup"), local http server, Pyodide v0.26.4 served from a curl-filled
local cache via route interception (page bytes unmodified).

## Passes (qa_browser.py + qa_browser2.py)

- Boot to live Pyodide run: 5.6 s, zero console errors, zero page errors.
- Precomputed display present at first paint; first live run replaces it
  in place; chart count 26 before and after; no "precomputed" remains.
- Live run on input change: suction 2 -> 5 kPa gives total motive steam
  635.2 -> 437.2 kg/h, compression ratio 3.70 -> 2.73, duty 523.6 ->
  386.2 kW, annual cost 170479 -> 118241 USD/yr; live region announces
  "Run complete. Total motive steam ...". (First script's
  metrics_changed=false was a race in the script, not a page defect:
  it read metrics before the debounced run finished.)
- Sticky tab bar: nav top 0 after scrolling 1200 px, desktop and phone.
- Header left/right edges equal body column edges at 1280 px (344/922).
- Desktop scrollWidth 1265 <= 1280. Theory tab renders; <details> opens.
- ?selftest=1: pass, total motive 635.179 kg/h, total duty 523.558 kW.
- Phone screenshots inspected: tabs wrap to two rows, inputs full width,
  labels legible, no overlap in the visible App panel.

## CONFIRMED findings (to fix in v2)

- Q1. Phone horizontal overflow: document scrollWidth 551 at 390 px
  viewport. Cause located by element scan: the stage table inside
  #stagetable is 535 px wide and overflows. (The off-screen skip link
  at left -9999 is intentional and not an offender.) Fix: contain
  tables in a horizontally scrollable wrapper (overflow-x: auto) and
  re-check every table at 390 px.

## Screenshots

shots/desktop-app-live.png, desktop-theory.png, desktop-economics.png,
desktop-code.png, desktop-process.png, phone-app.png, phone-theory.png,
phone-app-overflow.png. Raw QA output: review/qa_browser.out,
qa_browser2 output in exec history (live run + overflow locator).

## v2 re-check (2026-11-18, parent)

- Desktop: boot 7.7 s, precomputed at first paint, charts 26 → 26, live
  replaces precomputed, sticky nav top 0, header = body column (344/922),
  scrollW 1265 ≤ 1280, zero console/page errors. ?selftest=1 pass
  (635.179 kg/h, 523.558 kW).
- Live run (polling check): suction 2 → 5 kPa gives 635.2 → 437.2 kg/h.
  (qa_browser.py's own metrics_changed=false is the known script race:
  it reads before the debounced run finishes; the polling check in
  qa_browser2.py is the valid measurement.)
- Phone: document scrollW 375 ≤ 390 — page-level horizontal overflow
  FIXED. The stage table is still 535 px wide but is now contained in a
  horizontally scrollable wrapper (7 tablewrap divs in the built page);
  the document itself does not scroll sideways.
- v2 desktop App screenshot is byte-identical to v1 at the same scroll
  position (App panel top unchanged); phone App screenshot re-rendered
  clean, tabs wrap, inputs full width.
- Screenshots in shots/ are now the v2 run; QA outputs qa_browser-v2.out,
  qa_browser2-v2.out.

## v4 re-check (2026-11-18, parent; one-phrase change from v3)

- Desktop: boot 5.3 s, precomputed at first paint, charts 26 → 26, live
  replaces precomputed, sticky nav top 0, header = body column,
  scrollW 1265 ≤ 1280, zero console/page errors. ?selftest=1 pass
  (635.179 kg/h, 523.558 kW).
- Live run (polling check): suction 2 → 5 kPa gives 635.2 → 437.2 kg/h.
- Phone: document scrollW 375 ≤ 390. v4 is the publish candidate.
- QA outputs qa_browser-v4.out, qa_browser2-v4.out.
