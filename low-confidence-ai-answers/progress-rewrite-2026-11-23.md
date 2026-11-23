# Progress record — writing-skill rewrite, 2026-11-23

## Source of record established

The page had no source anywhere: it survived only as the published
file on gh-pages (`low-confidence-ai-answers/index.html`, 4,196,239
bytes, SHA-256 6fa8bb05…). This directory was established on
2026-11-23 with `index.html` as a byte-identical copy of that
published file, taken from the pages clone, and a README recording
the establishment — the route used earlier for fopdt-fitting. The
page is a static single file, maintained directly as HTML; there is
no build step and no MoLab notebook.

## Rewrite, review, delta

The audit found 10 findings (F1–F10) in the framing prose; the 32
Appendix A entries, the five Appendix B prompts and the 128
Appendix D responses are quoted material and stood unchanged,
verified byte-identical by region hashes after every step. F1–F8
were fixed in the rewrite; F9 and F10 are figure-work and are
carried (below). Principal corrections: §3 and the §2 third-test
summary table now name the held-out problems by the labels the
tables and Appendix D use (A4, C2, D1, D5; D2, G1), replacing the
H-codes that appeared nowhere else on the page (F1); the Contents
names for nine problem types and three parts now match the body
headings (F2); seven article-deleted sentence openings restored
(F3); the §1 opening states the outcome with values, names the
reader and the assumed knowledge, and "skill" is defined at its
first use (F4); the meta-signpost chain closing Step 4 removed
(F5); the two omitted subsections added to the Contents, which now
carries 59 links (F6); "Signs Used" reduced to the three
page-specific conventions (F7); the workspace and standing-memory
frame glossed in plain terms at each site (F8). One terminology
fix under the standing rule for reports: Appendix C's "canary pair"
restated as "one trial pair run first"; the word "canary" no longer
occurs in the file.

The independent review passed after two named fixes, both in the
new opening paragraph: N1 — the warnings trajectory split by
problem set (20 of 32 → 32 of 32 on the original problems; 22 of 32
→ 32 of 32 on the new problems — the bundled form had implied 20
for both, against the third test's table value of 22); N2 — the
closing compliance clause ("each term from AI practice is explained
where it is first used") restated as an assumption ("no knowledge
of AI practice"). The delta re-review passed with no further fixes.
Reports:
`~/workspace/goals/writing-skill-rewrite-of-all-existing-work/hidden_files/low-confidence-ai-answers-{audit,rewrite-review,delta-review}.md`.

## Closing-tag repair at build

The first build attempt stopped, correctly: the `</body></html>`
pair at lines 491–492 of the source (before Appendix C) was the
file's *only* closing pair, and the file ended with
`</div></details>` and no closers — the description of the fix had
implied a second pair at the end that does not exist. On the
coordinator's adjudication (option 1 of the stop report), the
mid-file pair was removed and `</body>` and `</html>` were appended
at the end of the file, so the document carries exactly one closing
pair, at the end. Verification: the file diff is confined to those
two removed lines and the two appended lines (file size unchanged,
4,197,073 bytes); the extracted visible text before and after is
identical — all 78,499 non-whitespace text chunks identical in
order, the whitespace-normalised text identical, and the total
whitespace character count unchanged (3,121), the newlines having
only changed position.

## Rendered battery (final file, headless Chromium)

- Contents links: 59 of 59 resolve to existing anchors.
- The corrected passages render: the §1 opening with both warnings
  trajectories (20 → 32 and 22 → 32) and the audience sentence
  ending "no knowledge of AI practice"; §3's labels A4, C2, D1, D5
  present; no H-code in the visible text; "canary" absent.
- No sideways page scroll at 390 px, 1440 px or 2560 px
  (scrollWidth equals innerWidth at each). At 390 px, 52 of the
  page's 197 tables are wider than their containers and scroll
  inside their own blocks; the page itself does not scroll.
- First-time-viewer pass on desktop and phone screenshots: clean —
  title, Contents and §1 opening legible at both widths; the §2
  summary table fits the phone viewport with wrapped cells.

Final file: 4,197,073 bytes, SHA-256
7135501fb9a916e0fc29d3a448220e1939c9f837c8cc7c1711a3bfd557646d81.

## Carried items

- **F9 — the four-step loop diagram** (work answers → examine for
  low confidence → write defensive prompts → retest, with the
  feedback path drawn). The loop is the study's title concept and
  is carried entirely in prose; no figure of it exists.
- **F10 — the before/after results as a paired bar chart** (lower
  priority): three scored questions × two tests × two halves. The
  two summary tables are complete and verified, so the chart is an
  aid for a first reader, not a correction.
