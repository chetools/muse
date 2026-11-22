# Progress — v12 Theory framing wording fixes (2026-11-22)

Text only, in text/theory.md. No model, number, structure or
layout changes; every quoted experiment total is unchanged.
Source: independent review of the v9 Theory framing (delta
review after the v10/v11 layout fixes; the page was at v11, so
this delta ships as v12).

- [x] Fix 1 (Key point 4): the surviving-vapour sentence now
  states the equilibrium cap correctly — the entering vapour or
  the equilibrium amount at the condenser outlet temperature,
  whichever is smaller; warmer cooling water raises the
  equilibrium amount, so more vapour can survive each condenser.
  The Conclusion's condenser sentence fixed the same way
  (removal down to the equilibrium amount where the entering
  vapour exceeds it, none where it does not).
- [x] Fix 2 (Key points preamble): pressures are in kPa
  absolute, except the motive steam pressure, which the App
  takes in MPa absolute (Key point 2's experiment unit).
- [x] Fix 3: (a) Key point 5 heading — "the strongest cost
  lever" superlative dropped ("a major cost lever");
  (b) Conclusion — the cooling-water/suction-pressure
  cross-comparison removed; (c) "How the demonstration is
  done" — total motive steam and its uncertainty band listed
  as two metric-card items; (d) opening claim qualified —
  every relation the App computes except the cost relations,
  which the Economics panel carries.
- [x] test_balance.py 14 passed; build checks pass (622
  KaTeX expressions = 622 elements, citations, placeholders);
  dist/steam-ejector-v12.html 4,519,699 bytes; v5–v11
  untouched.
- [x] Live run via the local CDN cache (page bytes
  unmodified): SELFTEST pass (total motive 635.18 kg/h,
  total duty 523.56 kW); precomputed display replaced.
  Layout spot-checks: desktop 1440px scrollWidth 1425 <=
  clientWidth 1440, side contents beside the text; phone
  390px scrollWidth 375, no sideways scroll
  (shots/v12-theory-desktop.png, v12-app-desktop.png,
  v12-theory-phone.png).
- [x] Published: main local commit 120acc8 pushed as remote
  head d03126c (steam-ejector scope only, 7 blobs, 0 deleted;
  remote blob SHA of text/theory.md verified equal to local);
  gh-pages local commit fdba726 pushed as remote head
  9b7d2df (1 file, steam-ejector/index.html). Served bytes
  SHA-256 85b8e7d08b39a539b4de5d2de37bdc05ec98f9508f73e67b8
  ad05f1b398ee87b, equal to dist/steam-ejector-v12.html; the
  served hash was observed changing from the v11 hash after
  the gh-pages push, confirming the Pages deployment ran.
