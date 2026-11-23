# Keypoints app — writing-skill rewrite, progress record

2026-11-23. Part of the writing-skill rewrite programme (audit, rewrite,
independent review, build and publication). The page is a single
self-contained HTML file, served as-is from GitHub Pages; it has no
MoLab notebook.

## Source of record

The project was established in this repository during the rewrite: before
2026-11-23 the app had no source here, and the published file on the
`gh-pages` branch was its only state. The source `index.html` was copied
from that published file byte-identically (38,268 bytes, SHA-256
`b1b963c55d128b52ac64c294f9fc7902d068ab143e39bf913af8460d765a5431`) and
is now maintained in `keypoints-app/` on `main`.

## Audit

14 findings: P1 = 1, P2 = 5, Other = 8. The P1 (F1): two panels stated
that nothing leaves the device, while a signed-in take's audio is sent
to the course server and sealed there. Further P2 items: no source of
record (F2); panel order put Record before the sign-in it depends on,
with Record disabled at load and its reason stated in another panel
(F3); one identifier under three names (F4); sealing progress reporting
"slide" numbers on a page with no slides (F5); an unsupported
"within about a minute" pickup claim resting on an undefined "watch"
(F6).

## Rewrite

All 12 in-scope findings fixed in the source. Both F1 notes now state
both halves at their own panel: the video never leaves the device; a
signed-in take's audio is sent to the course server at the end of the
take and sealed there. The identifier is "assignment code" at every
student-visible site, including the paste-block label (checked against
every consumer of the block: no consumer parses the literal label). The
sealing message uses the page's parts vocabulary. The pickup claim now
states only what the page establishes: the block holds the session code,
and the user's Muse transcribes the sealed audio and compares the
explanation against the standard. The purpose line states the audience
(student and teacher on the same page) and the outcome; "the standard
for the assignment" is defined at first use. On sealing success the
status beside the hidden progress bar ends on the brief completion line
"Audio sealed on the course server." Sentence openings: static prose
about 6% "The"-openings after (about 12% before), JS strings about 8% —
natural constructions, ruled a below-band near miss at review. No
number, requirement, or time limit was added or altered.

## Independent review

Clean PASS, no named fixes. All 12 in-scope findings verified fixed
against the file and the code; the six named verifications pass (F1
against the sealing flow in the code; the paste-block label against its
consumers; the sealing counters; the handover text; the completion
line; the MediaRecorder failure texts). Behaviour integrity: the diff
against the published baseline is reader-facing strings plus the one
completion-status call; the server-supplied assignment fragment
rendering is untouched. Progression: flag 1 = 0, flag 2 = 0.

## Build step: F3 panel reorder

The sign-in panel (`sealPanel`) was moved before the Record panel
(`recordPanel`). Panel order as built: Response (in the header), Camera,
Sign-in and transcript sealing, Record, Recordings, The assignment page.
The move is markup only: a line-multiset comparison against the
pre-move file shows exactly one changed line — the Record panel status
line's cross-reference "(see Sign-in and transcript sealing, below)"
became "above", the direction-word correction named in this step's
licence. (The same sentence's "the whole assignment page below" stands:
the assignment page panel remains below Record.) Static cross-check:
all 44 element ids are present exactly once, and all 38 id references
in the script resolve; the extracted script passes `node --check`.

## Verification (rendered battery, static state)

Headless Chromium on the file as published; no course server is
reachable in the sandbox, so no live sign-in or sealing was attempted.

- Corrected passages render: both F1 notes, the purpose line with
  audience and outcome, the "Assignment code" labels, the sealing
  parts vocabulary, the end-screen handover text, the completion line.
  The superseded strings ("48 hours", "recording fingerprint",
  "Exam code", "about a minute", the "below" cross-reference) are
  absent.
- Panel order as built (above), at desktop and phone widths.
- Record is disabled at load, with its reason stated in the Record
  panel.
- Error placement stands by static structure: the sign-in status line
  stands inside the sign-in panel beside its controls, and the
  assignment-page status line stands inside its panel.
- No sideways scroll at 390 px, 1440 px, or 2560 px (scrollWidth
  equals the viewport width at each). Smallest font 13 px.
- No page errors in the static state.
- First-time-viewer pass on desktop (1440 px) and phone (390 px)
  screenshots: clean — panels in the new order, no clipping, overlap,
  or sideways overflow.

## Publication

- `main`: the project committed (index.html force-added past the
  repository's `*.html` ignore rule, as the file is the source of
  record; README.md; this record) and pushed with the push scoped to
  `keypoints-app/`.
- `gh-pages`: `keypoints-app/index.html` replaced with the built file
  and pushed with the push scoped to `keypoints-app/`.
- Served bytes verified byte-identical to the source file after
  publication.

## Carried items

- Missing figure, main item: the take's path drawn once at the opening
  — sign in (link opened on this device), record in one take, audio
  sent to and sealed on the course server with the video never sent,
  session code handed to the user's Muse, transcription and
  comparison against the standard. The path is currently carried in
  words across four panels and the end screen.
- Missing figure, lower priority and optional: a small step graphic at
  the sealing panel for the sign-in link sequence (request, email,
  open on this device) — the same-device condition is the step
  students get wrong.
- O4 placement: the MediaRecorder failure texts state the consequence
  and the next step, but the messages still surface in the Camera
  panel rather than beside the Record control. Placement is a code
  change, outside the rewrite.
- Vestigial step/stage CSS classes and a code comment misstating that
  "the server transcribes it" stand as copied from the published file;
  both are recorded in the project's README.md.
