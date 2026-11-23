# routh-hurwitz-pi-two-first-order

Source of record for the published page "Stability limits of two first-order
systems in series under proportional–integral control"
(https://chetools.github.io/muse/routh-hurwitz-pi-two-first-order/).

## Maintenance form

Single-project static page. The page is maintained as one source file,
`template.html`, plus its build script `build.py`. The build inlines vendored
KaTeX (CSS, JS, and woff2 fonts as base64 data URIs) into the template at the
`<!--KATEX_CSS-->` and `<!--KATEX_JS-->` placeholders and writes the single
self-contained HTML file that is published. There is no walkthrough notebook
and no interactive app.

## Establishment

Established in this repository on 2026-11-23, during the writing-skill rewrite
programme, because the page had no source of record in the repository (not at
HEAD, not in history). Before this date the only source stood outside version
control at `~/workspace/routh-hurwitz-pi/` (`template.html` and `build.py`).
The two files here are byte-identical copies of that outside source, verified
by hash at establishment:

- `template.html` — MD5 `76ab3f485efc6c7eda702d0972fcf7aa`,
  SHA-256 `ca0ec40c49b988dc3a09d4d52a88b7c77e8f6da2c7bb4557ae1c9ea43ca6a922`
- `build.py` — MD5 `bf56df2afea9042654ee4e2ece5273a8`,
  SHA-256 `85c107085b3d4b23736f88a9cbd03820c83ad9b5913f6e4b5b3b3bdd7ce3ba8c`

The published file as it stood at establishment is
`muse-repo-pages/routh-hurwitz-pi-two-first-order/index.html` (683,268 bytes,
MD5 `c3bc5a1f7b54e1665d767a1bab5fd600`); a build from the copied sources
reproduces it byte-identically.

## Build dependency

`build.py` reads the vendored KaTeX tree at
`~/workspace/ts-spaces/supersonic-flow-and-speed-of-sound/assets/katex/`
(`katex.min.css`, `katex.min.js`, `auto-render.min.js`, `fonts/*.woff2`). That
tree belongs to another project and is read only; it is not copied here.
`build.py` as copied names the outside source directory
(`~/workspace/routh-hurwitz-pi/`) as its template path and
`~/workspace/your_files/routh-hurwitz-pi-two-first-order.html` as its output
path. At the rewrite's build step (2026-11-23) those two paths were adjusted
to this project: the template path is this directory's `template.html` and
the output path is this directory's `routh-hurwitz-pi-two-first-order.html`.
No other line of `build.py` was changed.
