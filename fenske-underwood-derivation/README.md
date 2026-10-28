# Fenske equation and Underwood equations — derivation

A self-contained derivation page: the Fenske equation (minimum number of equilibrium stages at total reflux) and the Underwood equations (minimum reflux ratio at an infinite number of stages), derived step by step from equilibrium relations and material balances, with every symbol defined before first use, a worked binary example verified by an independent graphical construction, and a McCabe–Thiele figure at minimum reflux.

## Build

- `content.frag` — page source with KaTeX markup (named `.frag` because the repository `.gitignore` excludes built `*.html` on `main`).
- `build.js` — renders all KaTeX server-side with the KaTeX installation under `~/workspace/pbsid-derivations/katex-build/`, embeds the fonts, and writes the standalone `fenske-underwood-derivation.html`. The build fails on any KaTeX error or leftover math delimiter.
- Published on the `gh-pages` branch as `fenske-underwood-derivation/index.html`.
