# Keypoints app

A single self-contained HTML file (`index.html`, all CSS and JavaScript
inline, no external assets, no build step). The page is served as-is and
calls a course server at runtime for sign-in, the assignment page, and
audio sealing. The assignment page fragment it displays is server-supplied
teacher content, fetched at runtime; it is not part of this file.

## Source of record

This directory was established on 2026-11-23 during the writing-skill
rewrite programme. Before that date the app had no source in this
repository: the published file on the `gh-pages` branch
(`keypoints-app/index.html`) was its only state. The file here was copied
from that published file byte-identically (SHA-256
`b1b963c55d128b52ac64c294f9fc7902d068ab143e39bf913af8460d765a5431`,
38,268 bytes, verified with `cmp` at establishment) and is now the source
of record. All maintenance is by editing this single file and publishing
the edited file to `gh-pages` unchanged in form.

## Notes for maintainers

- The `.stage`, `.prompt`, `.diagram` and related CSS classes are
  vestigial styles from an earlier step-based design; no element in the
  body uses them. They are retained as copied.
- A comment above the audio-sealing section in the copied file says "the
  server transcribes it". That misstates the system: the server holds the
  sealed audio in custody only, and transcription happens in the user's
  Muse. The comment stands as copied; it is recorded here so a future
  editor is not misled by it.
