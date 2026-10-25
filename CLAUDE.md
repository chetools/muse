# chetools/muse: house rules

Rules for any session opened on this repository. Adapted on 2026-10-24 from
`chetools/claude/CLAUDE.md` (section "Visualisation and UI" and related
sections) and from the standing rules under which the pages in this
repository are built. Where a project folder carries its own instructions,
the project instructions govern that project.

## Repository layout and publishing

- One top-level folder per project on the `main` branch. Built deliverables
  publish to the `gh-pages` branch under `muse-html/`; deliverables are
  never committed on `main`.
- Never stage a whole-repository addition. Stage explicit paths, one
  project directory at a time.
- Pull before pushing, review the compare view against the intended change
  set after every push, and byte-verify every pushed file against the
  local build. Never force-push.
- Publication is verified by served bytes: compare the served page with
  the build output, and confirm that the Pages run actually started.
  An HTTP 200 response alone is not verification.
- Builds fail loudly. An unfilled template placeholder, a missing input
  file, or an unregistered module is a build failure, never a skipped
  substitution.

## Writing and notation

- Journal-formal register in all user-facing writing: nominal, impersonal
  headings; no hype, no conversational fragments, no second-person asides.
- Define every symbol before its first use, with SI units where
  applicable, in prose, equations, captions, tables, figures, and code
  shown to the reader. A symbols table alone does not satisfy the rule
  when a symbol first appears far from the table.
- Every abbreviation, legend entry, and axis label used on a page appears
  at least once on that page adjacent to its full form and meaning.
- Verify every citation before delivery: each in-text citation resolves
  to exactly one bibliography entry, and authors, year, title, journal,
  volume, pages, or DOI are checked against the publisher record or
  Crossref.

## Pages and user interface

- **The page header matches the body text width.** On wide monitors the
  title, intro and status/progress bar must not span the whole window:
  wrap them in one block with the same `max-width` as the body column,
  set in the body font (a `ch` width set on the larger title font comes
  out wider). Check with Playwright at 2560 px that the header and body
  share left and right edges.
- Calculations and plots are implemented in Python only. A page whose
  Python runtime fails to load shows an explicit error; no JavaScript
  calculation fallback is provided.
- Every long tab, section, or panel carries a table of contents derived
  from its rendered headings, with URL fragment navigation so any view
  is shareable by copying the address. Every panel and every headed
  section within a panel carries a fragment identifier.
- A long-running step displays a live progress indicator.
- Plotly is the default plotting library. Legends sit outside the plot
  area; log axes carry pinned ranges. Colour is always double-encoded
  and grayscale-readable; the canonical specification is the STEM visual
  style specification held with the project sources.
- Visual scales follow the displayed data's statistics. Animation is
  defined in simulated time. Compared panels show equal density. Shown
  values and control steps are nice numbers. Presets carry display
  settings.
- Journal-quality visual verification on every page: rendered screenshots
  at desktop and mobile widths, checked for margins, overlaps, spacing,
  and alignment, before delivery. Code inspection alone is not
  verification.

## Notebooks

- A marimo notebook targeting WASM or MoLab declares every non-default
  dependency in its PEP 723 script header. A notebook mirrored to MoLab
  is self-contained: no repository-local imports.
- The pre-run read-only WASM export and the editable MoLab notebook are
  separate deliverables, each labelled by role.
