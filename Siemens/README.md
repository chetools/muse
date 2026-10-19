# Siemens/

gPROMS (Siemens PSE) simulation material.

## H2S/MDEA packed absorber — illustrative steady-state simulation

| File | Contents |
|---|---|
| `h2s_mdea_absorber.html` | Self-contained static page documenting the simulation: column layout, model equations (KaTeX, server-rendered, no CDN needed), symbol glossary, base-case data, results, full gPROMS listings, and run instructions. Open it directly in a browser. |
| `gproms/H2S_MDEA_Absorber_Model.gproms` | MODEL entity: 12-compartment rate-based absorber, H2S + MDEA ↔ MDEAH⁺ + HS⁻ equilibrium speciation, enhancement-factor mass transfer |
| `gproms/H2S_MDEA_BaseCase.gproms` | PROCESS entity: 100 kmol/h, 5 mol% H2S, 70 bar, 40 °C, 45 wt% MDEA; three-step schedule (base / 80% circulation / lean loading 0.02) |
| `twin.py`, `twin_results.json` | Independent Python twin of the same equations (NumPy/SciPy `fsolve`) and its results — the numbers a gPROMS run should reproduce |

Base case: 4.0 ppmv H2S in treated gas, 99.992% removal, rich loading 0.408 mol H2S/mol MDEA.

To run: paste each `.gproms` file into a new Model / Process entity in gPROMS ModelBuilder and press Run. gPROMS itself is commercial Siemens software and is not included here.
