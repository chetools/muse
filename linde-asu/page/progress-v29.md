# Linde ASU page v29 — stream phases made explicit

Change, at the reader's request: the phase of every numbered
stream — all vapour, all liquid, or a mixture of vapour and
liquid — is now stated unmistakably in three places.

- Sheet Revision 9 (record: pfd/compliance-record-v9.md): a
  phase legend below the equipment summary lists the streams
  by phase; the stream table's Phase column is bold; stream 14
  is corrected to Two-phase (isenthalpic flash vapour mole
  fraction 0.133) and four table temperatures are corrected so
  each stated state supports its label (streams 10, 25, 26, 27,
  28).
- Process panel: a new Stream phases section after the Process
  overview, with the three groups in a table (all vapour:
  1–10, 18–24, 28; all liquid: 11–13, 15, 16, 25–27, 29;
  two-phase: 14, 17), the locations of every phase change
  (E-103, E-105, the two throttling valves, the dew-point air
  stream 6), and the statement that the two phases coexist
  inside the columns while every numbered stream entering or
  leaving a column is single-phase except streams 14 and 17.
  Phase is also stated at the stream mentions in the turbine,
  pressure column, condenser/reboiler, subcooler/valve,
  low-pressure column and crude argon sections; the valve
  section gives the flash vapour mole fractions, 0.13 for
  stream 14 and 0.14 for stream 17.
- Fig. P0 and Fig. T0 captions point to the sheet legend and
  the new section. Fig. P0 sheet links updated to the
  Revision 9 files.

Verification:
- Build checks pass: citation check 44 entries, all cited;
  KaTeX 98 expressions, unchanged; boot guard OK.
- Sheet: balances close, audit C1–C10 0 defects, rendered-pixel
  gap check 0 over 20 connections.
- Independent clean-context process review (bubble/dew by
  Raoult/Clausius–Clapeyron, independent flash estimates):
  grouping passed row for row; valve fractions confirmed
  (0.123/0.130 estimated against 0.13/0.14 stated); its two
  hard findings (streams 10 and 28 stated in the liquid range)
  were resolved by the sheet temperature corrections before
  publication.
- Browser: Stream phases section screenshotted at 1440 px and
  390 px and inspected; document scroll width equals viewport
  width at both; the section is in the Process contents.
- Served bytes verified identical to the build output after
  publication.
