# Inverse Laplace Transform Tables for a Second-Order System

Static page: step, sine, and cosine responses of the transfer function
K / (tau^2 s^2 + 2 zeta tau s + 1) for the overdamped (zeta > 1),
critically damped (zeta = 1), and underdamped (0 < zeta < 1) cases,
with sine and cosine inputs at frequencies below, equal to, and above
the natural frequency. Illustrative plots are computed from the
tabulated formulas.

## Files

- The built page (self-contained; KaTeX rendered at build time,
  figures inlined as SVG) is published on gh-pages at
  `/inverse-laplace-transform-tables/index.html`. Built HTML is not
  committed on `main` (repository `.gitignore` rule for `*.html`).
- `content.frag` — page source with KaTeX delimiters and figure
  placeholders (kept under a non-HTML name so the repository
  `*.html` ignore rule does not hide the source).
- `build.js` — build script: renders KaTeX server-side, inlines the
  KaTeX fonts and the figure SVGs, and fails on any unrendered
  equation, missing figure, or unreplaced placeholder.
- `make_plots.py` — generates `fig-step.svg`, `fig-cos.svg`, `fig-resonance.svg`,
  `fig-sin.svg`, and `fig-freq.svg` (matplotlib); asserts agreement
  with an independent ODE integration before writing each figure.
- `verify_sine.py` — verifies the sinusoidal tables against symbolic
  inverse Laplace transforms (sympy) over all zeta, q, and input
  combinations used in the page checks.
- `fig-*.svg` — generated figures, inlined into `index.html` at build
  time.

## Build

1. `python3 make_plots.py` (regenerates the figures; runs the ODE
   check first).
2. `node build.js` (requires the KaTeX package from the local
   pbsid-derivations build tree; see the path constant in `build.js`).
3. `python3 verify_sine.py` (symbolic verification of the tables).
