# Verified anchors — re-computed 2026-11-22, CoolProp 8.0.0, Air (pseudo-pure, HEOS)

Script: `verify_anchors.py` (this directory). All pressures absolute.

## Expansion 568 kPa → 138 kPa

The brief's turbine anchors are the **isentropic endpoints**. The page states
them as isentropic endpoints; the live model applies a stated isentropic
efficiency of 0.80, so its turbine outlet temperatures are warmer.

| Inlet (K) | Isentropic outlet (K) | Turbine outlet, efficiency 0.80 (K) | Valve outlet (K) |
|---|---|---|---|
| 293 | 195.2 | 214.5 | 292.0 |
| 230 | 153.0 | 168.0 | 228.4 |
| 190 | 126.3 | 138.5 | 187.7 |
| 165 | 109.6 | 119.9 | 162.0 |
| 150 | 99.5 | 108.8 | 146.5 |
| 130 | 86.2 | 93.8 | 125.3 |

## Linde sheet stream 8 state (102 K, 568 kPa)

- Dew point at 568 kPa: 100.0 K; at 138 kPa: 84.4 K. Bubble point at 138 kPa: 81.7 K.
- Isentropic endpoint at 138 kPa: 84.1 K. Isenthalpic endpoint: 94.0 K. Both match the brief.

## Saturation at the flash pressure (138 kPa)

Bubble 81.72 K, dew 84.44 K.

## Valve from warm (293 K) to 138 kPa, single pass

5 MPa → 282.0 K; 10 MPa → 272.0 K; 15 MPa → 263.5 K; 20 MPa → 256.9 K.
No liquid in a single pass at any of these pressures; liquefaction in
valve-only operation is itself regenerative and accumulates over passes.

## Joule–Thomson coefficient (finite difference at 568 kPa)

293 K: 0.23 K/bar; 200 K: 0.48 K/bar; 150 K: 0.81 K/bar; 102 K: 1.75 K/bar.
The coefficient grows roughly eightfold between ambient temperature and
102 K — the quantitative form of hard rule 16 for this page.
