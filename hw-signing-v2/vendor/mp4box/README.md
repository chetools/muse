# mp4box.js — vendored

MP4Box.js 2.5.0 (GPAC), BSD-3-Clause — see `LICENSE`.
Copied unmodified from the npm package `mp4box@2.5.0` on 2026-11-19:

- `mp4box.all.mjs` — the library entry point; it imports the two files
  below by relative path, so all three must stay together.
- `styp-BV5G3FS-.mjs`
- `rolldown-runtime-CNh9ExCG.mjs`

Used only by `js/media-mp4.js`, which the page loads dynamically when
the browser's own audio decoder cannot read a chosen MP4/MOV file.
Nothing on the normal path loads this code.
