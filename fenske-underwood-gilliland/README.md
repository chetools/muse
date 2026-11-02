# Fenske–Underwood–Gilliland (FUG) Shortcut Distillation

An educational WASM page teaching the FUG shortcut design of a
multicomponent distillation column: the Fenske equation (minimum
stages at total reflux and the distribution of non-key components),
the Underwood equations (minimum reflux, Class 1 estimate and its
failed check, then the Class 2 solve), the Gilliland correlation in
the Eduljee form (stages at the operating reflux), and feed-stage
location by the Kirkbride and Fenske section-ratio methods.

The worked case is the debutanizer of Seader, Henley & Roper,
*Separation Process Principles*, 4th ed. (2016), Chapter 9,
Examples 9.1–9.6.

Layout:

- `python/` — `fug.py` (the calculation), `walkthrough.py` (the
  single-source breakdown cells), `runner.py`, `make_molab.py`
  (marimo notebook generator), `test_fug.py`, `test_boot.py`.
- `standalone/` — `template.html`, `theory.md`, `build_page.py`;
  the build emits `dist/fenske-underwood-gilliland-v1.html`.
- `notebook/walkthrough_molab.py` — generated, self-contained,
  editable on MoLab.
- `PLAN.md` — the approved build plan, with pitfalls and checks.
- `references-verified.md` — the citation verification record.

Build (with the project virtual environment):

    python3 standalone/build_page.py          # full page
    python3 standalone/build_page.py --stub   # layout-check build

Published page: https://chetools.github.io/muse/fenske-underwood-gilliland/
Editable notebook: https://molab.marimo.io/github/chetools/muse/blob/gh-pages/fenske-underwood-gilliland/walkthrough_molab.py
