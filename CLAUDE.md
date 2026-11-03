# chetools/muse: house rules

Rules for any session opened on this repository. Adapted on 2026-10-24 from
`chetools/claude/CLAUDE.md` (section "Visualisation and UI" and related
sections) and from the standing rules under which the pages in this
repository are built. Where a project folder carries its own instructions,
the project instructions govern that project.

## Repository layout and publishing

- One top-level folder per project on the `main` branch. Built deliverables
  publish to the `gh-pages` branch at the root, in a folder with the same
  name as the project folder on `main`; the `gh-pages` root `index.html`
  links to every published page, and a new page is added to that index
  when it is published. Deliverables are never committed on `main`.
- The repository has exactly two branches, `main` and `gh-pages`. Work
  is committed directly to `main`, one project folder at a time; no
  development branch is created for any task, and `gh-pages` is touched
  only for publication.
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

- Before drafting or revising user-facing text (documents, pages, theory and caption text, notebook
  prose, commit messages, long replies), load the `writing-skills` skill (`.claude/skills/writing-skills/`;
  canonical source `chetools/muse:writing-skills/`), name the document type, and run its revision pass
  before delivery. Before drawing or styling a figure, plot or page, load the `stem-visual-style` skill.
- Always on: journal-formal, plain, brief English; no hype or filler; verified facts kept apart from
  inference, with what was not checked named.
- Chat replies: English; voice input is spell-checked against chemical-engineering, coding and AI/ML
  vocabulary. No LaTeX: math-heavy content goes in a self-contained HTML file (KaTeX rendered at build
  time) or a PDF, with every equation checked on a screenshot. Runtime and availability caveats go in the
  reply, never in a document or page. A changed file is re-delivered under a fresh filename. A MoLab link,
  and the link of a changed published page, each stand on their own labelled line.
- Code shown to the user is minimal: existing libraries (Plotly, SciPy, existing routines) over
  hand-written numerics, plain functions over classes. Calculations and plots are in Python, not
  JavaScript, except a requested accelerator with a measured speed-up, the Python reference kept and
  parity shown.
- A request such as "70% technical style" or "STE100" sets the dial in `writing-skills/references/ste100.md`.
- When I give exact wording for a rule, it is recorded verbatim, with no added heading, date or context.

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
  section within a panel carries a fragment identifier. The main tab bar
  is sticky with an opaque background, in-panel contents sit below it,
  and fragment targets have a scroll margin. The theory panel is labelled
  "Theory".
- A long-running step displays a live progress indicator.
- Plotly is the default plotting library. Legends sit outside the plot
  area; log axes carry pinned ranges. Colour is always double-encoded
  and grayscale-readable; the canonical specification is the `stem-visual-style`
  skill (`.claude/skills/stem-visual-style/`).
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
