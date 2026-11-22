# Linde ASU page — progress v32 (2026-11-22)

Correction of Fig. P7 and the turbine section, directed by the user after the EOS check of the regenerative-cooling account exposed the errors.

## The errors
- Fig. P7 drew the turbine path as isentropic from stream 8 (102 K, 568 kPa) to stream 9 (91 K, 138 kPa) and the valve path to ~101 K; the caption stated falls of 11 K and about 1 K.
- The turbine section attributed the valve figure to a Joule–Thomson coefficient of 0.2 K/bar, an ordinary-temperature value applied at 102 K.

## Verified endpoints (CoolProp 8.0.0, pseudo-pure Air, 102 K / 568 kPa → 138 kPa)
- Isentropic: 84.1 K; dew point at 138 kPa 84.4 K — the reversible path reaches the vapour boundary.
- Isenthalpic: 94.0 K.
- Cross-scale checks: from superheated inlets the turbine/valve contrast is wide (165 K: 110 vs 162 K; 293 K: 195 vs 292 K); at stream 8's dew-point inlet the endpoints crowd (84/91/94 K).

## Changes
- make_figures.py fig_ts redrawn: isentropic limit line and endpoint at 84 K, turbine path to stream 9 at 91 K, valve path to 94 K, work shading between turbine and valve paths.
- process.md turbine section rewritten at the two passages; build_page.py Fig. P7 caption rewritten; VERSION v32.
- Sheet Revision 10 unchanged (stream 9 = 91 K was always the machine outlet, not an endpoint error).

## Verification and publication
- Build checks pass (99 KaTeX); Fig. P7 inspected in the built page at desktop width.
- Main 007347d, gh-pages a6359df, both pushed scope linde-asu; served bytes identical to the v32 build (sha256 0b774f38…).
