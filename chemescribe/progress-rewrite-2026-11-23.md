# ChemEScribe — writing-skill rewrite, progress record

2026-11-23. Part of the writing-skill rewrite programme (audit, rewrite,
independent review, build and publication). The page is a static page
with no build step — `index.html` plus plain JS modules, served as-is
from GitHub Pages; it loads its speech-recognition model from Hugging
Face at runtime. It has no MoLab notebook.

## Audit

12 findings: P1 = 0, P2 = 4, Other = 8. The P2 items: the opening put
the Corrections mechanism section before the workflow it serves (F1);
the load and live progress bars stood at 100% beside their completion
lines (F2, shared with chemescribe-record); one error box in section 3
received every error, from controls in sections 1 and 2 as well (F3,
shared); the decode error named a narrower format set than the page
invites, omitting OGG (F4). The audit also established that
chemescribe-record is a separate published page with its own prose
copy — a separate rewrite item — and recorded the passages the two
pages share. Every other sampled claim verified against the code;
"about 670 MB" and "roughly 2 GB of memory" are stated consistently at
every site but are not verifiable from the repository (see Carried
items).

## Rewrite

All nine in-scope items fixed in the source (index.html, app.js,
README.md). The subtitle now states the audience and the task in order
and qualifies the "no server" claim with the Hugging Face model
download at first use. The decode error names the formats the input
accepts, OGG included. The README bundle counts are corrected to the
verified figures (212 pairs in the bundle, 9 attested; 209 loaded —
149 confident, 60 uncertain). int8, Soundex and edit distance are
explained at first use; the hour-plus timestamp form is stated; step
headings are nominal. Sentence openings in band (about 18–20% "The"
after, by the review's count). No number, requirement, or limit was
added, removed, or altered in value; the 25 s window size is newly
stated at the value the code already uses. The builder listed seven
passages changed here that also stand in chemescribe-record, for that
page's pass to carry.

## Independent review

Clean PASS, no named fixes. All nine in-scope items verified fixed;
the named verifications pass (the decode error against the accept
attribute; the README counts against corrections.js counted directly;
the timestamp form against formatTimestamp; both piece sizes against
their constants; the Hugging Face qualification against the fromHub
call; all seven shared passages against chemescribe-record as it
stands). Behaviour integrity: the diff is confined to reader-facing
strings in the three files. Progression: flag 1 = 0, flag 2 = 0.

## Build step: F1, F2, F3, O6

- F1 section reorder: the Corrections section's markup moved bodily to
  stand after step 3, so the order is now 1. The model; 2. Options,
  audio file and recording; 3. Transcription of a chosen file;
  Corrections; Live progress; Result; Corrections applied; Autosave.
  One text consequence of the move, recorded here: the step-2 note's
  "The corrections described above" became "described below", since
  the section now stands below that note. Static cross-check: all 37
  element ids unique; all 35 ids referenced from the JS modules
  resolve; app.js parses as a module.
- F2 progress completion: in app.js, the load handler now hides the
  load progress bar in its finally block — on success and on failure
  alike — leaving the brief status line ("Model loaded in … s." or
  "Model did not load."). Both transcription completion points (file
  run and recording stop) hide the live bar when they set it to 1,
  leaving the "Done — …" line. The run bar already hid correctly and
  is untouched. New runs show the bars again through the existing
  liveBusy/load paths.
- F3 error placement: showError takes the caller's own error box as a
  third argument (default: step 3's box). Three error elements were
  added in the page's existing .err style: #loadErr in step 1 (model
  load errors), #fileErr in step 2 (file decode errors), #recErr in
  step 2 (microphone, recorder-start and recording-piece errors);
  step 3's #errBox keeps the Transcribe errors. clearError clears all
  four. In the microphone and recorder-start failures the Record
  control's own status (recStatus) is also set — to the error's first
  sentence — since at present nothing changed at that control. Error
  texts are unchanged.
- O6 Copy confirmation: a status span (#copyStatus, class .status) was
  added to the Copy/Download row, and the Copy handler sets it to
  "Transcript copied." after a successful clipboard write.

## Verification

Rendered battery on the to-be-published files (headless Chromium,
static state; the ~670 MB model download was not run and no live
transcription was attempted): section order as built at 390, 1440 and
2560 px; the corrected passages render (subtitle with audience, task
order and the Hugging Face qualification; the timestamps label with
[1:02:05]; the nominal step headings; the Recogniser int8 explanation
and the Glossary Soundex and edit-distance explanations); the three
new error elements sit in their sections in the DOM and step 3's box
in its own; #copyStatus stands in the Copy button's row; both bars
are hidden in the static state; no sideways scroll at any of the
three widths (scrollWidth equals viewport width); smallest font
12.48 px (the network-log monospace); no page or console errors.
First-time-viewer pass on desktop and phone screenshots: clean.

What only a live run can settle: the bars' hide-on-completion and the
error boxes' appearance in an actual failure (a model load, a decode
failure, a denied microphone) — the mechanisms are in the served
files and statically verified, but the 670 MB download and a live
microphone are outside this sandbox.

## Carried items

- Missing figures: the transcription pipeline drawn once — audio file
  or microphone → recogniser → raw transcript piece by piece → the
  four correction passes in order → marked transcript with the
  corrections list; and the correction-mark legend beside the Result
  (lower priority).
- "About 670 MB" and "roughly 2 GB of memory" stand as stated at every
  site; neither is verifiable from the repository.
- F2 and F3 also stand on chemescribe-record, whose own rewrite item
  follows; the shared-passage corrections are listed in the rewrite
  report for that pass.
