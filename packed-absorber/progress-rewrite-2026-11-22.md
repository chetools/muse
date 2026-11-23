# Packed absorber — writing-skill rewrite, progress record (2026-11-22)

## What changed

- Full prose rewrite of `packed_absorber.py` under the writing skill:
  the published export's prose was first reconciled into the source
  (the published page carried a partial revision the source lacked),
  the transfer-units derivation was reordered before the sizing that
  uses it, sections were renumbered and every cross-reference updated,
  a contents list was added after the opening, and the opening now
  states the default design's outcome with values (D = 1.3 m,
  Z = 11.22 m, N_OG = 6.12, H_OG = 1.83 m at 65.9% of flood).
- Citations rebuilt so the layer resolves in both directions: nine
  verified entries added (Mahmud et al. 2019; Sander 2023; Li & Shen
  1993; Deshmukh & Mather 1981; Ji et al. 2016; Sherwood, Shipley &
  Holloway 1938; Leva 1954; Eckert 1970; Green & Perry 2008), three
  orphan entries removed (Treybal 1980; Seader et al. 2011; Kohl &
  Nielsen 1997). The Leva entry states only verified fields; the
  Norton chart is named as data provenance with no entry, no
  verifiable publication record existing.
- §3 states the model's compressibility treatment and its consequence:
  Z_g is held at 0.93 (the value near 50 bar); Peng–Robinson gives
  0.964 at 20 bar, 40 °C, so the gas density and the hydraulic results
  run about 3.5% high at the defaults. The model constant itself is
  unchanged (see carried items).
- §4 states one K(T) form, the code's, with the attribution corrected
  to the project record; §5's Weber-number sentence corrected to the
  display's grouping; display (11)'s unit bracket corrected so the
  817.3 Pa/m conversion attaches to Δp; all 16 displays numbered
  (1)–(16) and referred to by number; captions added under all five
  figures and the in-figure titles removed.
- Delta fix D1 applied at build: §5's "wetting is hard to buy with
  liquid rate alone" now reads "wetting increases only slightly with
  liquid rate". One contents slug corrected at build to the heading id
  marimo renders (`4-vaporliquid-equilibrium-of-h2s-in-aqueous-mdea`).

## Audit and review chain

- Audit: 26 findings (P1 = 0, P2 = 6, Other = 20). Independent
  review: pass after one named fix (§5's figurative "a_w collapses",
  since corrected); delta re-review: pass after D1, applied above.

## Build and verification

- Export: marimo 0.24.2 (the version the published export records;
  the dedicated venv `~/workspace/.venvs/marimo242`),
  `marimo export html-wasm --mode run`. The page carries no version
  marker; none was invented. All 710 asset files and the
  icons/manifest are byte-identical to the previously published tree;
  only `index.html` changed (190,827 bytes). The main-repo
  `packed_absorber_wasm.html` is the same bytes as the published
  `index.html` and was regenerated with it.
- PEP 723 header declares every import (marimo, numpy, plotly,
  scipy).
- `marimo check` passes (20 warnings, all the pre-existing
  markdown-indentation class).
- Project tests: `test_packhyd.py` cannot run against this source —
  it hardcodes a working copy at `~/workspace/packed-absorber/work/`
  and expects an `sbf_dp_irr` definition the committed notebook has
  never contained (absent at HEAD before the rewrite). Pre-existing
  divergence, unrelated to the rewrite; the notebook itself executes
  end to end, and the rewrite's outputs were verified identical to
  the before state during the rewrite step.
- Rendered battery: the sandbox browser cannot reach the Pyodide
  CDN, so the WASM page does not boot locally. The battery was run
  on a server-executed export of the same notebook rendered with the
  same marimo 0.24.2 frontend, its CDN paths rewritten to the
  export's local assets: contents anchors 13/13 resolve against the
  rendered heading ids; 16 KaTeX displays render with their numbers
  (Eq. (1) and Eq. (2) spot-checked in the rendered view, references
  resolving); all five figure captions present in the rendered page
  and true to their figures; figure fonts are set at 13 px in the
  figure code (one annotation at 11 px), at or above the 10 px
  floor, and plotly does not scale fonts with container width; the
  GPDC chart's axes are log type with plotly's default decade ticks
  (no override in the code); no sideways page scroll at 390 px
  (document scroll width 390 px) or at 1440 px. At 390 px the four
  figures with a 170 px right legend margin leave about 160 px of
  plot width: each figure stays whole in one viewport, with phone
  readability limited — carried to the figure step. Desktop and
  phone screenshots inspected as a first-time viewer: clean
  (opening states goal, audience and outcome values; contents
  follows; the validation table and known-bias note read as
  intended).
- Progress indicator: the page has no page-authored long-running
  step; execution feedback is marimo's native cell status.
- Served bytes: fetched page byte-compared with the export
  (recorded in the publication report).

## Carried items

- Five missing figures, for the separate figure step: a schematic
  of the absorber and its internals; a packing-geometry figure at a
  common scale; a wetting schematic for §5 (film and rivulets,
  a_w against a_t); a Δp-against-gas-rate curve through loading to
  flooding; a driving-force or local H_OG profile along the bed.
  The phone-width plot-area item above belongs to the same step.
- Validation row 2's model α stands as data at 0.191 against the
  code's recomputed 0.193 (audit Q6); not changed in the rewrite.
- The Z_g model constant (0.93 at every state) is unchanged. Making
  the code compute Z_g at each state is a separate content
  correction awaiting the user's decision.
