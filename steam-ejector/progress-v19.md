# Progress — v19 ejector cross-section figure, Fig. P11 (2026-11-22)

User finding: the educational page showed no figure of what a
steam ejector itself looks like — the sheet and its crops show
ejectors as flowsheet symbols and Fig. P10 shows profiles along
a stage, but the apparatus (nozzle, suction chamber, throat,
diffuser) was never drawn. Governed by the clarifying-figures
rule (AGENTS.md / MEMORY.md, 2026-11-22, as amended: real
photographs and 3D cutaways preferred where their licence
permits use) and the chemical-process page skill.

- [x] Tree verified at the v18 head for the steam-ejector
  scope (gh-pull-dir refresh; scope clean) before editing.
  Scope steam-ejector/ only, explicit paths.

## Research record (Step 1 — consulted before drawing)

Diagrams:
1. Spirax Sarco, "SJT Steam Jet Thermocompressor",
   TI-P493-02-US, Issue 3 (2025), and the EN edition
   TI-P493-02 — labelled cross-sections of fixed-nozzle and
   variable-area units. Shows well: the nozzle seated in the
   steam chest, suction entry into the chamber, diffuser as
   one casting; the operation text names the throat as the
   narrowest part of the diffuser where the mixture becomes
   uniform. Adapted: the section layout (axial motive entry,
   nozzle inside the chamber, side suction entry). Improved:
   their sections carry no axial scale and no shock position;
   Fig. P11 adds both, tied to Fig. P10. Added to References
   as [10].
2. Schutte & Koerting, Bulletin 5E-H, "Steam Jet Ejectors:
   Single and Multi-Stage Steam Jet Vacuum Pumps", and
   Blatchley, "Selection of Air Ejectors" (S&K) — Fig. 556
   standard construction: "a converging-diverging steam
   nozzle, a body or suction chamber, and a venturi tail
   (diffuser)"; the selection paper's Fig. 1 nozzle profiles
   and Figs. 2–3 process description. Adapted: the three-part
   construction vocabulary (nozzle / body / venturi tail) and
   the well-rounded nozzle inlet profile. Added to References
   as [11].
3. ChemicalEngineers.in, "Steam Jet Ejector Design" — a
   four-zone cross-section table (nozzle, suction chamber,
   throat, diffuser) with pressure/velocity behaviour per
   zone. Adapted: zone-by-zone organisation, which Fig. P11
   makes quantitative with the P10 axial percentages.
4. Wikipedia, "Vacuum ejector" — "The basic elements of an
   ejector" schematic and the steam ejector text (Power [2],
   already reference [2] on the page). Confirmed the standard
   element set; the schematic is a generic venturi tube
   without a distinct nozzle insert or shock, not adopted.
5. ResearchGate-hosted schematic (steam ejector with axial
   pressure/velocity distributions; four parts: primary
   nozzle, mixing chamber, throat, subsonic diffuser) —
   confirmed the convention of pairing the section with axial
   profiles, which this page already has as Fig. P10; Fig.
   P11 is drawn to the same axial scale so the two pair up.

Photographs and 3D cutaways (amended rule — candidates and
licence decisions):
- Croll Reynolds product photographs and spindle-ejector 3D
  cutaway graphics (croll.com; company Instagram/Facebook,
  2026 posts): clear photographs of skid-mounted ejector
  systems and one labelled cutaway rendering (actuator, body,
  spindle, nozzle, mixing chamber, diffuser). Licence: none
  stated; manufacturer marketing material, all rights
  reserved. NOT embedded. Taken from them: confirmation that
  the real body is a flanged casting with the suction branch
  entering the chamber from the side, as drawn.
- Spirax Sarco SJT photographs/sections in TI-P493-02:
  © Spirax Sarco 2025, no reuse licence. NOT embedded;
  drawn from (above).
- Schutte & Koerting bulletin photographs and construction
  figures: manufacturer bulletin, no reuse licence. NOT
  embedded; drawn from (above).
- Social-media 3D cutaway renderings (Chemical Pedia,
  Mechanical Gyaan, Next Level Engineer, 2026): realistic
  labelled cutaways, but no licence and unverifiable
  provenance; one widely shared variant drew a reader
  correction on its inlet labelling. NOT embedded.
- Wikimedia Commons: no photograph or cutaway of an
  industrial steam-jet ejector exists there (searches for
  ejector/eductor/cutaway return a locomotive cutaway, a
  gasworks exhauster house, and refrigeration diagrams). The
  Wikipedia article's photograph is a brass laboratory water
  aspirator — a different device class; embedding it would
  mislead. NOT embedded.
- Kerr (1918), "Design, construction and test of a steam
  air-ejector" (archive.org; public domain, US, published
  1918): photographs of the actual test apparatus and a
  longitudinal section of the designed ejector. Licence
  permits use, but the photographs are grainy 1918 halftones
  of a laboratory rig; at page scale they fail the clarity
  standard the rule sets. NOT embedded; the longitudinal
  section corroborates the nozzle/chamber/diffuser layout.
Decision: no candidate satisfied both clarity and licence,
so Fig. P11 is the page's own drawing, informed by the
sources above; [10] and [11] are cited where the figure is
introduced and stand in References.

## The figure (Step 2)

Fig. P11, generated by xsection_figure() in build_page.py
(same pattern as pvt_figure()). Longitudinal section, axial
scale x = 250 + 5.9 × (axial %): nozzle 0–22%, mixing
22–51%, throat 51–65%, diffuser 65–100%, normal shock
dashed at 57% — the Fig. P10 zones and shock position. An
axial strip under the section carries the 0/22/51/65/100
ticks so the mapping is read off the figure itself.
Label boxes were placed programmatically and checked
pairwise (≥ 8 units apart) and against the body outline
before first render; no leader crosses another leader; no
line passes through any text.

Element trace — every element, what it shows, what it
supports:
- Motive steam inlet (left flange and pipe, vermillion
  arrow): the 0.8 MPa abs steam entry of Process §"Motive
  steam supply" and the E-101 walk; Theory §T1/§T5 inlet
  state.
- Motive nozzle (converging–diverging), grey insert in the
  steam chest, throat at 13% and exit at 22%: §T5's subject;
  its converging half, throat, and diverging half are the
  three parts §T5 names in its second paragraph.
- Jet cone leaving the nozzle exit, widening into the
  mixing chamber: the supersonic free jet of §T6.
- Suction chamber (the large cavity around the nozzle
  exit): Process E-101 part two; §T6's entrainment volume.
- Suction inlet (bottom branch, blue arrow up): the side
  entry every consulted section shows; Process E-101's
  "gas from the vessel is drawn in around the jet".
- Mixing chamber (converging bore, 22–51%): where the jet
  and suction stream mix (§T6, §T7's constant-pressure
  limiting case); Fig. P10's "Mixing" zone.
- Throat (constant area, 51–65%): §T7's mixing throat;
  Process line "the throat is the constant-area section
  where mixing finishes".
- Normal shock (dashed vermillion line at 57%, inside the
  throat): Fig. P10's shock; §T12's double-choking mode.
- Diffuser (diverging bore, 65–100%): §T8's pressure
  recovery.
- Discharge outlet (right flange, green mixture arrows in
  throat and diffuser): the stage discharge of the Process
  walk (428.3 kg/h at 7.40 kPa abs for stage 1).
- Centreline (dash-dot): the section axis; the axial strip
  below is the Fig. P10 abscissa.
No element is decorative; removing any one removes a part
the text names.

## Placement (Step 3)

Numbering: the new figure is Fig. P11 in both panels.
Renumbering P1–P10 was rejected: those numbers are cited
throughout the text. Theory has no figure series of its
own, so the same number is carried there.
- Process, §"First stage ejector": a two-sentence
  introduction citing [10][11] for the standard
  construction, then the figure, before the Fig. P3 crop.
- Theory, §T5: a short paragraph after the section's first
  paragraph pointing to the figure and its 22% nozzle
  share, then the figure.
All existing text and numbers are unchanged apart from
these additions. One build defect found and fixed during
verification: the two placements initially shared arrowhead
marker IDs, and the motive arrow of the Process copy did
not paint (its marker resolved to the hidden Theory copy);
each placement now carries unique marker IDs.

## Verification (Step 4)

- test_balance.py: 14 passed.
- Build checks pass; KaTeX 624 = 624; citation check in
  the build passes with [10] and [11] cited and listed.
- Three-class audit of Fig. P11 (shots/v19-audit/):
  desktop (both placements) PASS — every label whole,
  every leader traceable to one part, all four arrows
  paint, scale full-column like Figs. P1 and P10.
  CONFUSING: none after the marker-ID fix. ABSURD: none —
  the section is the same width and lettering size as
  Fig. P10's strip. UNNECESSARY: none (element trace
  above). Phone (390 px): labels whole and legible at
  full-column width, document scroll width 375 px (no
  sideways scroll); lettering is small at phone width, the
  same recorded minor note as Fig. P10 — the figure follows
  the page's full-width figure convention.
- Selftest ?selftest=1 on the byte-identical local build:
  see publication record below (sandbox Chromium cannot
  reach the public internet, as for v15–v18).

## Publication record (v19)

- Selftest ?selftest=1 on the local build (Pyodide CDN
  mirrored from the local cache, per the review/qa_browser.py
  technique): PASS — total motive steam 635.18 kg/h, total
  condenser duty 523.56 kW, no page errors. Re-run at
  publication time on the final dist file with the same
  verdict. Published-page selftest stands on the
  byte-identical local build: sandbox Chromium cannot
  reach the public internet, as for v15–v18.
- Pre-publication sanity check at publication time:
  test_balance.py 14 passed; dist/steam-ejector-v19.html
  present (4,573,626 bytes, SHA-256 7e13def4…), built by
  build_page.py at VERSION = "v19"; both Fig. P11
  placements present in the built file with their unique
  marker-ID sets (ahMp/ahSp/ahXp and ahMt/ahSt/ahXt) and
  four "Fig. P11" references.
- Main: commit 30dcf17 pushed 0be55c3 -> 21a86e7 (compare
  view: 11 files, all in steam-ejector/; remote blob SHAs
  match local git hash-object for build_page.py,
  progress-v19.md and BUILD_LOG.md).
- gh-pages: b30f9fb -> 6f0d57a (compare view: only
  steam-ejector/index.html modified; walkthrough
  untouched). Pages run for 6f0d57a completed (success).
  Served bytes byte-identical to dist/steam-ejector-v19.html
  (4,573,626 bytes, SHA-256 7e13def4…).
  MoLab link: https://molab.marimo.io/github/chetools/muse/blob/gh-pages/steam-ejector/walkthrough_molab.py
