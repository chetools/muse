# Build brief — Mechanical Vapor Recompression (MVR) educational WASM page

User approved plan (2026-11-22). Build end to end, publish, and report with evidence. Do NOT ask the user questions; use the defaults below.

## Governing skills (read before building)
- ~/workspace/custom-skills/local-chemical-process-wasm-page/SKILL.md (seven panels: App, Process, Theory, Economics, Safety, Code, References)
- ~/AGENTS.md hard rules (symbols defined at first use with SI units; citations verified two layers; journal-quality visual QA at desktop + 390px; versioned filenames, never re-deliver changed file under same name; page link and MoLab link each on own labelled line in handover; TOC for every long panel; builds fail loudly; served-bytes verification)
- Template to clone and adapt: ~/workspace/steam-ejector/ (proven structure: template.html, build_page.py, make_molab.py, python/balance.py + test_balance.py + walkthrough.py, text/*.md, sheet.svg, notebook/walkthrough_molab.py, review/qa_browser*.py). Copy its build pipeline, runner, QA scripts and adapt — do not invent a new pipeline. Work in ~/workspace/mechanical-vapor-recompression/ as the project dir (copy steam-ejector files there as starting point, then replace content).
- Writing: journal-formal, plain, no origin/compliance block on page, no prompt commentary on page. SI units throughout. No LaTeX issues: page uses KaTeX build pipeline from template.

## Scope / defaults (approved)
- Core modelled process: single-effect falling-film evaporator with MVR. Process/Theory also cover multi-effect MVR, crystallizers, distillation vapor recompression, desalination as applications.
- Design basis (sample values, labelled as such): evaporation 5,000 kg/h water at 80 °C; temperature lift 10 K (condensing side 90 °C); feed preheated by condensate; balance must close exactly on displayed values.
- Model inputs (reader-variable, whole range swept): evaporation rate (e.g. 1,000–20,000 kg/h), evaporator temperature (60–100 °C), temperature lift (5–20 K), compressor isentropic efficiency (0.60–0.85). Economics inputs: electricity price and steam price for annual cost / payback comparison vs live-steam single effect.
- Model physics (derive step-by-step in Theory, implement exactly what Theory derives):
  - Saturation pressure of water vs temperature: Antoine equation (state constants, source, valid range) or steam-table correlation — state which, define every symbol.
  - Latent heat vs temperature correlation.
  - Pressure ratio from saturation pressures at T and T+lift; boiling-point elevation and heat-transfer ΔT separated explicitly: total lift = BPE + ΔT_transfer (+ losses) — this separation is a named pitfall, handle it.
  - Isentropic compression work for steam: use ideal-gas form with heat-capacity ratio and compressibility discussion, and/or enthalpy form w = (h2s − h1)/η_is; state assumptions, superheat at discharge, specific work kJ/kg.
  - Compressor shaft/electric power, COP = condensing duty / electric power, specific energy kWh per tonne evaporated, equivalent steam economy (kg evaporated per kg live steam equivalent) and comparison with single-effect (~0.9), multi-effect, TVR.
  - Calandria duty Q = m_evap * latent heat (+ feed sensible correction as modelled), heat-transfer area from Q = U A ΔT with stated U (assumed, labelled).
  - Annual operating cost MVR (electricity) vs steam-driven; simple payback from stated capital cost correlation/estimate (labelled estimate, basis year).
  - Tests: default reproduces design basis, balance closure, whole-range sweep, invalid-input plain-language errors.

## Research dossier (do FIRST, persist as dossier.md in project dir)
Use browser.search / browser.open to verify facts against publisher/vendor/operator/agency records. Record for each reference: bibliographic data, how verified, exact facts read. Only recorded verified facts may appear on page. Cover:
- Process description, compressor types (centrifugal blower/fan, single-stage centrifugal, Roots, turbo), materials, fouling/scaling, demisters, start-up steam, non-condensables.
- Theory sources: Perry's, Sinnott & Towler, Walas, steam tables (IAPWS), compressor texts.
- Economics: capital/operating figures with basis year/capacity basis; typical specific energy 10–30 kWh/tonne water evaporated etc. — only if sourced.
- Safety/environment.
- LARGEST COMMERCIAL SITES (user emphasised): list the largest documented MVR installations by evaporation capacity / installed compressor power, across dairy evaporation (e.g. GEA/Arla/FrieslandCampina-scale plants), salt/potash crystallisation, pulp black liquor (Andritz), lithium brine, desalination, chemical plants. For EACH site: operator, location, application, capacity as stated by source, vendor if stated, background/economics as stated by source. Attribute vendor claims as vendor claims. If a definitive global ranking is not verifiable, present a sourced list of the largest documented installations and say so in dossier (page wording must not overstate). Every site needs a checked source URL recorded.

## PFD
Draw sheet.svg (adapt steam-ejector sheet approach / hand-built SVG acceptable at same quality): feed tank/pump, condensate preheater, falling-film evaporator + separator, demister, MVR compressor, calandria (evaporator body), condensate out, concentrate out, start-up steam line, non-condensable vent, CIP note. Stream table with design-basis values closing exactly. Sub-process crops in Process panel: re-embed sheet SVG with cropped viewBox per subunit section (feed preheat; evaporation/separation; compression; condensation/heat recovery), captioned Fig. P1, P2, … Screenshot-inspect every crop.

## Panels text (text/process.md, theory.md, economics.md, safety.md, references.md)
- Process: very detailed, subunit by subunit in diagram order, intuition and physical explanation connecting to common sense, operating issues (fouling, scaling, foaming, entrainment, compressor surge, BPE in concentrated solutions, turndown).
- Theory: step-by-step derivations of EVERY equation the model uses, each symbol defined at/before first use with SI units, limiting cases checked (lift→small, COP behaviour).
- Economics: scale of use, capital, operating, payback sensitivity to electricity/steam price ratio, plus the commercial-sites table with background per site.
- Safety: pressure, hot surfaces, compressor machinery, cleaning chemicals, product/food safety where relevant.
- References: all cited, mechanical + factual check in build.

## Build / verify / publish
- build_page.py produces dist/mechanical-vapor-recompression-v1.html (increment version on changes).
- Run: pytest on model, build assertions, Playwright QA at desktop/2560/390px on every panel + figures + math, live Pyodide run via ~/workspace/wasm-verify/cdn_mirror.py method if available (as steam-ejector QA did), ?selftest verdict.
- Independent review: spawn at least one clean-context subagent reviewer (Brief A constraints/bounds; ideally also process plausibility per skill §8.3) on the frozen draft; adjudicate findings, fix upheld ones.
- Publish: scoped workflow for chetools/muse — standing clones ~/workspace/muse-repo-main and ~/workspace/muse-repo-pages; refresh scoped dir first per AGENTS.md scoped workflow; sources to main under mechanical-vapor-recompression/, built page + walkthrough + MoLab notebook to gh-pages under mechanical-vapor-recompression/, update gh-pages root index.html, byte-verify served/pushed blobs, confirm Pages run.
- Chunked writes: never emit a whole large file in one response; write files in small appended chunks via tools, persist inputs first. This is a long build — checkpoint progress to ~/workspace/mechanical-vapor-recompression/BUILD_LOG.md as you go so a restart can resume.

## Report back (final)
Published page URL, MoLab link, design-basis anchor numbers the model reproduces, verification results (tests, browser checks, widths, selftest, served-byte comparison), defaults used, anything not verified labelled as expectation. Attach/link the built page file (fresh versioned filename).
