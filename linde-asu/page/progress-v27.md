# Linde ASU page v27 — full sheet at the front of Theory

Change: the full process flow diagram now stands in the Theory panel's
opening, so a first-time reader sees the whole plant before the key
points and the derivations. The sheet is inserted as Fig. T0 at the end
of the Introduction, after a short tracing paragraph in
`content/theory.md` that names the main units in flow order (C-101,
E-101, V-101, E-102, X-101, T-101, T-102, E-103, T-103, E-105, E-104,
E-106, VLV-101, VLV-102). Numbered T0 so the saturation curves keep
their Fig. T1 number and their `theory-fig-t1` fragment; the new
fragment is `theory-fig-t0`, with a Theory contents entry under
Introduction. The figure uses the same `.pfdbox` treatment as the
Process panel's Fig. P0 (full reading-column width, internal sideways
scroll available); the Process panel keeps its own copy of the sheet
and all its crops unchanged. No model, number, equation or other text
changed.

Verification:
- Build checks pass: citation check 44 entries, all cited; KaTeX 98
  expressions, unchanged from v26; boot guard OK (parity, plain-language
  errors).
- Fragment audit: the set of element ids in v27 differs from v26 by
  exactly one addition, `theory-fig-t0`; no existing identifier changed.
- Key point 1 reproduced through the built page's own boot/model code
  (the code the served page runs): oxygen recovery 0.97 gives contained
  oxygen 156.111 t/d, displayed as 156.1 t/d. The in-browser Pyodide
  run itself was not executed from this sandbox (runtime CDN
  unreachable), as in v26.
- Screenshots inspected (page/shots/v27-*): Fig. T0 whole and legible
  at 1440 px (figure 916 px wide, the full reading column), whole at
  390 px with no sliced labels; page scroll width equals viewport width
  at both 1440 px and 390 px; header edges at 2560 px identical to v26
  (left 696, right 1864 by the probe used for both builds).
- Served bytes verified identical to the build output after
  publication.
