# ChemEScribe Record — writing-skill rewrite, progress record

2026-11-23. Part of the writing-skill rewrite programme (audit,
rewrite, independent review, build and publication). The page is a
static page with no build step — `index.html` plus plain JS modules,
served as-is from GitHub Pages; it loads its speech-recognition model
from Hugging Face at runtime. It records and transcribes only, and
shows the raw transcript; correction is handed to Muse with the
ready-made prompt the page carries. It has no MoLab notebook.

## Audit

The audit stands in the chemescribe audit report (its
chemescribe-record section). The audit established that this page is a
separate published page with its own prose copy — a separate rewrite
item, not a variant of chemescribe — and that it carries no P1/P2 of
its own. The findings applying to both pages: the load and live
progress bars stood at 100% beside their completion lines (F2); one
error box in section 3 received every error, from controls in steps 1
and 2 as well (F3); and one further O-item. Large prose passages are
the same text in both pages, and the chemescribe rewrite listed the
seven shared passages its corrections touched, for this page's pass to
carry.

## Rewrite

All seven carried corrections applied in this page's own forms,
verified against this page's code: the subtitle's "no server" claim
qualified in the same passage by the Hugging Face model-download
sentence; headings 1 and 3 in chemescribe's nominal forms and heading
2 restated under the same rule ("2. Audio file and recording"); the
file note states the window size (about 25 s, at this page's
FILE_WINDOW_S = 25); the recording note's privacy restatement removed
(the fact stands once in full in the subtitle); the Live progress
paragraph refers to the sizes stated in step 2; the Recogniser section
explains int8 at first use and its closing privacy restatement is
removed; the decode error replaced with chemescribe's corrected text
(this page's accept set is identical). One heading of this page's own
brought to nominal form: "Correction in Muse". The prompt text
stands byte-identical in both of its copies (prompt.js and the
index.html box), so its instructions to the receiving Muse keep their
meaning exactly. No number, requirement, or limit was added, removed,
or altered in value; the 25 s window size is newly stated at the value
the code already uses. Sentence openings in band (12% before, 14%
after, by the builder's count).

## Independent review

Clean PASS, no named fixes. All seven carried corrections verified one
by one against the published chemescribe page and this page's own
code; the prompt copies verified byte-identical to each other and to
the committed state; behaviour integrity confirmed (the diff is
confined to reader-facing strings in index.html and app.js).
Progression: flag 1 = 0, flag 2 = 0.

## Build step: F2, F3

- F2 progress completion: in app.js, the load handler now hides the
  load progress bar in its finally block — on success and on failure
  alike — leaving the brief status line ("Model loaded in … s." or
  "Model did not load."). Both transcription completion points (file
  run and recording stop) hide the live bar when they set it to 1,
  leaving the "Done — …" line. The run bar already hid correctly and
  is untouched. New runs show the bars again through the existing
  showLivePiece/liveBusy paths.
- F3 error placement: showError takes the caller's own error box as a
  third argument (default: step 3's box), the same mechanism
  chemescribe took. Three error elements were added in the page's
  existing .err style: #loadErr in step 1 (model load errors),
  #fileErr in step 2 (file decode errors), #recErr in step 2
  (microphone, recorder-start and recording-piece errors); step 3's
  #errBox keeps the Transcribe errors. clearError clears all four. In
  the microphone and recorder-start failures the Record control's own
  status (recStatus) is also set — to the error's first sentence —
  since previously nothing changed at that control. Error texts are
  unchanged.

## Verification

Static cross-check: all 37 element ids unique; all 35 ids referenced
from the JS modules resolve; the edited app.js parses clean as a
module; the prompt box in index.html equals prompt.js's PROMPT_TEXT
byte-for-byte (node evaluation).

Rendered battery on the to-be-published files (headless Chromium over
a local HTTP server, static state; the ~670 MB model download was not
run and no live transcription was attempted): the corrected passages
render (the qualified subtitle; the nominal headings "1. The model",
"2. Audio file and recording", "3. Transcription of a chosen file";
the file note's window size; the Recogniser int8 explanation; the
"Correction in Muse" heading); the prompt box renders and equals
PROMPT_TEXT; the three new error elements sit in their own steps in
the DOM (#loadErr in step 1, #fileErr and #recErr in step 2, #errBox
in step 3) and all three progress bars are hidden in the static state;
no sideways scroll at 390, 1440 or 2560 px (scrollWidth equals
viewport width at each); smallest font 12.48 px (the network-log
monospace); no page or console errors. First-time-viewer pass on
desktop (1440 px) and phone (390 px) screenshots: clean.

What only a live run can settle: the bars' hide-on-completion and the
error boxes' appearance in an actual failure (a model load, a decode
failure, a denied microphone) — the mechanisms are in the served
files and statically verified, but the 670 MB download and a live
microphone are outside this sandbox.

## Carried items

- Missing figure: this page's pipeline in its shorter form — audio
  file or microphone → recogniser → raw transcript → prompt to Muse
  (lower priority).
- "About 670 MB" (the model size, stated on the Load button and in
  the Recogniser section) and "roughly 2 GB of memory" (stated in the
  step-1 note and the Runtime section) stand as stated at every site;
  neither is verifiable from the repository.
