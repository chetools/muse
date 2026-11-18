# Brief A — Constraints and bounds inventory (independent review, steam ejector page)

You are an independent reviewer. You did not build this page and you have not seen the builder's reasoning or check results. Work only from the frozen draft listed below plus this brief.

Draft (read from disk, do not modify):
- `~/workspace/steam-ejector/dist/steam-ejector-v1.html` (the page; v1)
- `~/workspace/steam-ejector/SPEC.md` (frozen specification)
- `~/workspace/steam-ejector/python/balance.py` (the model)
- `~/workspace/steam-ejector/text/theory.md`, `text/process.md`, `text/economics.md`, `text/safety.md`, `text/references.md` (panel sources)

Do NOT read `BUILD_LOG.md` or any other project note.

## Task

Build the inventory of every constraint and bound the page states or relies on, then check each one. Constraints include: validity ranges of every correlation and relation used (compression ratio, entrainment ratio, motive pressure, temperatures, pressures, stage count, suction pressure, cooling-water temperature, steam quality, economics basis year and capacity basis); every stated limit, threshold, flag condition and warning trigger in the model and the text; every "valid for / applies only to / limited to" claim; every range on an input control.

For each entry: quote the claim as it appears on the page, state the constraint or bound, give the numbers, and verify it in two ways where possible — (a) against the model code (does the code enforce exactly the bound the text states, with the same numbers and the same strictness, e.g. `<` vs `<=`?), and (b) against the named source where the page cites one (does the source state that bound?). Recompute at least three boundary values by hand or with your own short calculation (do not re-run the page's own code as your only check).

Report format (token-efficient, follow exactly):
- CONFIRMED findings in full: quoted claim, constraint, numbers, what is wrong and what the correct value or wording is.
- Passes as counts per check class (e.g. "correlation ranges: 7 checked, 0 failed"), never as full tables.
- NOT A FINDING entries by title only, one line each.
- Return the constraint inventory only as entries that produced a finding or a near miss.
- End with a one-paragraph verdict: fit to deliver as-is, fit with listed fixes, or not fit.
