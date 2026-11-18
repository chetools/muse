# Brief C — Definitions against named sources and figure decoding (independent review, steam ejector page)

You are an independent reviewer. You did not build this page and you have not seen the builder's reasoning or check results. Work only from the frozen draft listed below plus this brief.

Draft (read from disk, do not modify):
- `~/workspace/steam-ejector/dist/steam-ejector-v1.html` (the page; v1)
- `~/workspace/steam-ejector/SPEC.md` (frozen specification)
- `~/workspace/steam-ejector/python/balance.py` (the model)
- `~/workspace/steam-ejector/text/theory.md`, `text/process.md`, `text/economics.md`, `text/safety.md`, `text/references.md` (panel sources)

Do NOT read `BUILD_LOG.md` or any other project note.

## Task

1. Definitions against named sources: for every defined term and symbol the page introduces (including entrainment ratio, compression ratio, expansion ratio, stagnation pressure and temperature, Mach number, specific steam consumption, approach temperature, and every symbol in the Theory derivations), check (a) it is defined at or before first use, with SI units where applicable; (b) the definition matches the named source the page cites for it — where the cited source defines the same term differently (including an inverse ratio or a different symbol), that is a finding, and you must quote both definitions; (c) one term keeps one meaning and one symbol throughout (no silent redefinition between sections). Also check every in-text citation resolves to exactly one bibliography entry, every entry is cited, and the bibliographic data (authors, year, title, venue) match the publisher or Crossref record for at least the three sources the model depends on most; verify those three by web search/open, not from memory.

2. Figure decoding: decode every figure, diagram and chart on the page from its rendered form (read the HTML/SVG source where the rendered values are in doubt). For each: read values off the axes/legend/labels, check axis labels and units, check the legend entries against the prose, check the caption states the finding and the conditions, and check the numbers shown agree with the prose and with the model output for the same inputs. Check the flowsheet schematic: every stream and unit labelled, flow directions consistent with the text, no unit or stream named in the text but missing from the diagram or vice versa. Check every expandable derivation block: the algebra shown actually derives the result it claims (work at least two derivations through yourself, step by step, including one momentum-balance step and one isentropic-relation step).

Report format (token-efficient, follow exactly):
- CONFIRMED findings in full: quoted claim, definition or figure value, source wording or your recomputation, what is wrong.
- Passes as counts per check class, never as full tables.
- NOT A FINDING entries by title only, one line each.
- Return the inventory only as entries that produced a finding or a near miss.
- End with a one-paragraph verdict: fit to deliver as-is, fit with listed fixes, or not fit.
