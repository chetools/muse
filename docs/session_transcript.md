# Session transcript — JANAF thermodynamics demo

*Reconstructed on 2026-09-16 from the record of the chat session in which
this app was designed and built. User messages are quoted verbatim as
recorded; assistant replies are summarized faithfully.*

---

**User:** Build a separate public Streamlit thermodynamics demo on a new
branch **`JANAF`** in `chetools/muse`, using NIST Chemistry WebBook /
JANAF-style data. Requirements: use the NIST WebBook; licensing option 3
(redistribute derived coefficients with attribution/provenance, not copied
WebBook tables); "full JANAF if possible" but never claim it unless rights
and coverage justify it; store coefficients with standard interpolation and
strict out-of-range practices; support gases, condensed phases, phase
transitions, pressure corrections, fugacity/activity models, reactions, pure
species and mixtures; bundle legally usable public binary parameters where
possible, otherwise disclose standard fallback mixing rules; SI units;
single-temperature, temperature-sweep and multi-species comparison modes;
typical validation tolerances and visible uncertainties; Parquet/SQLite
caching; explicitly show assumptions, out-of-range events, calculation
details and data sources; a detailed theory panel covering all calculations;
professional rendering in Firefox, Chrome and Safari; keep it separate from
the absorber app.

**Assistant:** Built and pushed the `JANAF` branch of
`github.com/chetools/muse`. Contents: a NIST WebBook build pipeline
(`data/build_webbook.py`) producing derived Parquet/SQLite artifacts (24
species, 45 coefficient/reference records, 24 phase-change rows, 49 Antoine
rows); a thermodynamic engine (`janaf/`) with Shomate evaluation, ideal-gas
mixtures, Peng–Robinson fugacity (largest real root, ChemSep kᵢⱼ via the
MIT-licensed `thermo` package, disclosed kᵢⱼ = 0 fallback), ideal-solution
and binary NRTL models; pure-species, sweep, multi-species comparison,
mixture, reaction, theory and provenance UI; strict no-extrapolation range
handling with plotted gaps; 13 passing tests. Public branch:
`github.com/chetools/muse/tree/JANAF`.

---

**User:** *"Yes, expand the species list."*

**Assistant:** Added 20 species — C₂H₂, HCN, O₃, HF, F₂, HBr, HI, COS, CS₂,
SF₆, SO₃, N₂H₄, N₂O₄, HNO₃, H₂O₂, PH₃, SiH₄, BF₃ (full Shomate gas data)
plus C₆H₆ and C₇H₈ (298.15 K reference only, since their Cₚ(T) tables are
TRC-subscription data). Dataset grew to 44 species and 83 coefficient
segments. All 44 CAS Registry Numbers were verified against the numbers
printed on the fetched WebBook pages, and acentric factors resolve for
every new species.

---

**User:** *"Using a separate agent with clean context, double check
everything for correctness."*

**Assistant:** An independent auditor re-derived results from the code,
artifacts and live NIST pages. Findings: Shomate math PASS (hand-verified
against the live WebBook argon page: Cₚ = 20.786 J/mol/K at 500 K);
data pipeline PASS; Peng–Robinson fugacity matched an from-scratch
reimplementation to 9 decimals (Z = 0.978636809, φ = 0.978687499 for CH₄
at 300 K, 10 bar); NRTL matched an independent implementation to 10⁻¹²;
K = exp(−ΔG/RT) sign correct; methane combustion ≈ −800.7 kJ/mol;
provenance/licensing PASS (no raw tables committed, attribution and
non-affiliation text present, `thermo` confirmed MIT, no "full JANAF"
claim anywhere); all tests non-vacuous and passing. Four issues found and
fixed: (1, important) unbalanced reactions were silently accepted and
returned meaningless ΔrH° — an atom-balance check was added to the parser;
(2, minor) cumulative Antoine counts in build provenance made per-species;
(3, minor) reaction-grid out-of-range behavior aligned with its documented
no-extrapolation behavior (NaN gap rows); (4, minor) ideal-gas mixtures now
raise on missing component properties instead of propagating silent NaNs.
Tests grew to 17/17 passing and the fixes were pushed.

---

**User:** *"For the reactions, create a UI that allows users to pick
reactants/products from available ones. Automatically balance
stoichiometry - notify if impossible. Allow user to pick base species that
has stoichiometry of 1. Extensively test UI and calculation to ensure this
works correctly."*

**Assistant:** Added a **Reaction builder** section to the Reactions tab:
reactant/product multiselects drawn from every species/phase with data, a
base-species selector (its stoichiometric coefficient is normalized to 1,
e.g. base O₂ yields ½CH₄ + O₂ → ½CO₂ + H₂O), and one-click balancing. The
engine builds the integer element–species composition matrix and solves
Aν = 0 via SVD null space, converting to exact rational coefficients that
are verified symbolically. Impossible sets are refused with actionable
messages (naming elements stranded on one side, or naming a species that
must move to the other side); non-unique species sets are resolved to one
sparse valid solution by linear programming and flagged with a warning.
Balanced results reuse the manual-entry rendering (metrics, species
contributions, temperature sweep). The theory panel documents the method.
13 new balancer tests plus headless UI scenarios (happy path, base
normalization, impossible/wrong-side errors, error recovery, sweep
rendering, warnings, phase-change reactions) — 30/30 passing, pushed to
`JANAF`.

---

**User:** *"include a panel in the webapp with a transcript of this entire
chat."*

**Assistant:** This panel.
