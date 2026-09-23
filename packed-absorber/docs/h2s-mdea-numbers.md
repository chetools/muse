# H2S–MDEA equilibrium & physical-property numbers (verified 2026-09-21)

Source data for the packed-absorber marimo notebook. Every constant below was
retrieved from an open online source on 2026-09-21; verification status is noted
per item. Units are SI unless stated.

## 1. Recommended equilibrium model: Kent–Eisenberg (ideal-solution, H2S only)

For the tertiary amine MDEA no carbamate forms; the H2S system needs only three
reactions (concentrations in mol/L, ideal solution, activity coefficients = 1):

- (R1) H2O ⇌ H⁺ + OH⁻,            Kw(T)   = [H⁺][OH⁻]
- (R2) H2S ⇌ H⁺ + HS⁻,             K2(T)   = [H⁺][HS⁻]/[H2S]
- (R3) MDEAH⁺ ⇌ MDEA + H⁺,         Ka,am(T)= [MDEA][H⁺]/[MDEAH⁺]

Balances (C_am = total amine molarity, mol/L; α = loading, mol H2S / mol amine):

- Amine:   C_am = [MDEA] + [MDEAH⁺]
- Sulfide: α·C_am = [H2S] + [HS⁻]
- Charge:  [MDEAH⁺] + [H⁺] = [HS⁻] + [OH⁻]

Eliminate to one equation in [H⁺] and solve (bracket pH 4–12, Brent):

    [MDEAH⁺] = C_am·[H⁺]/([H⁺]+Ka,am) ; [HS⁻] = α·C_am·K2/([H⁺]+K2) ;
    [OH⁻] = Kw/[H⁺]
    f([H⁺]) = [MDEAH⁺] + [H⁺] − [HS⁻] − [OH⁻] = 0

Then [H2S] = [HS⁻][H⁺]/K2 and the equilibrium partial pressure follows Henry's law

    p*_H2S = H_H2S(T, wt%) · [H2S]        (H in Pa·m³/mol, [H2S] in mol/m³)

## 2. Equilibrium constants vs temperature

General form used throughout:  ln K = a/T + b·ln(T) + d   (T in K).

| Constant | a | b | d | validity | source / status |
|---|---|---|---|---|---|
| Kw (R1) | −13445.9 | −22.4773 | 140.932 | 273–498 K | Mahmud et al., *Processes* 2019, 7, 81, Table 3 (citing ref [54]); VERIFIED: gives Kw = 1.01e-14 mol²/L² at 25 °C (pKw = 13.998 vs CRC 13.995) |
| Ka,am (R3, MDEAH⁺ dissociation) | −8483.95 | −13.8328 | 87.39717 | 293–333 K | Mahmud et al. 2019, Table 3 (citing ref [53]); VERIFIED: Ka = 2.33e-9 mol/L at 25 °C → pKa = 8.63 (literature 8.52–8.57); T-slope gives dpKa/dT ≈ −0.020/K, correct sign and magnitude |
| K2 (R2, H2S 1st dissociation) | 294.912649 | −16432.9943 | −44.904864 | 283–333 K (fit range) | FITTED here to secondary pKa table (see §3); max residual 0.0074 pKa units. Status: SECONDARY — needs primary-source confirmation |

Check values at 25 °C: pKw = 14.00, pKa(MDEAH⁺) = 8.63, pKa1(H2S) = 6.97.

## 3. H2S first-dissociation data used for the K2 fit (secondary)

pKa1 values from a secondary dissociation table (scribd reproduction of a
textbook table; primary source not established):

    T (°C):  10    15    20    25    30    40    50    60
    pKa1:    7.24  7.13  7.05  6.97  6.90  6.79  6.69  6.62

Note: the CRC Handbook gives pKa1 = 7.05 at 25 °C, 0.08 units above the table's
6.97. The fit reproduces the table; treat absolute values as ±0.1 pKa uncertain.
Fit: ln K2 = 294.912649 − 16432.9943/T − 44.904864·ln(T).

## 4. Henry's constant of H2S

### 4a. In water (temperature dependence)
Sander (2023) compilation, "Compilation of Henry's law constants", ESSD:

- H^cp(298.15 K) = 9.5×10⁻³ mol/(m³·Pa)  →  H(px) = 1164.7 Pa·m³/mol
- d ln H^cp / d(1/T) = 2100 K  →  H(T) = 1164.7·exp[−2100·(1/T − 1/298.15)] Pa·m³/mol

VERIFIED against the compilation's printed values (recomputed 1164.7 from 9.5e-3).

### 4b. In aqueous MDEA at 25 °C (concentration dependence)
Rinker (sulfur-team data) and Posey, as reproduced in the open Atlantis Press
paper (2016), Table 1, "H (atm·m³/kmol)":

    MDEA vol%:   20     40     60     80     100
    H:           10.35  11.54  13.79  19.15  31.44   (atm·m³/kmol)

Convert ×101.325 → Pa·m³/mol, and vol% → wt% (ρ_MDEA = 1.038 g/mL):

    MDEA wt%:    20.6   40.9   60.9   80.6   100.0
    H_25°C:      1048.7 1169.3 1397.3 1940.4 3185.7  (Pa·m³/mol)

Sanity: the 20.6 wt% value (1049) is within 10% of Sander's water value (1165) —
consistent, since the solution is ~80% water.

### 4c. Recommended combined form for the notebook

    H_H2S(T, wt%) = interp(wt% | table in §4b) × exp[−2100·(1/T − 1/298.15)]

The temperature factor is Sander's water value applied to the MDEA-solution
data — a stated approximation (flagged in the notebook). Interpolate linearly in
wt%; refuse wt% outside 20–100% (no silent extrapolation to 0%).

## 5. Validation of the ideal-solution Kent–Eisenberg model

| # | Conditions | Reference value | Model prediction | Deviation |
|---|---|---|---|---|
| V1 | 23.8 wt% MDEA, 40 °C, p_H2S = 1 kPa | α = 0.134 (Jou et al. 1982, as reported by Shoukat, Pinto & Knuutila, *Processes* 2019 — within 4.6% of their own measurement) | α = 0.103 | −23% in loading |
| V2 | 30 wt% MDEA, 40 °C, p_H2S = 5 kPa | α ≈ 0.3 (Li & Shen 1993 Fig.5 / Huttenhuis et al. 2007 Fig.3, via U. Maryland course notes) | α = 0.191 | −36% in loading |

The model systematically UNDERpredicts H2S solubility by ~25–35% in loading
(overpredicts p* by ~75% at fixed loading). Cause: ideal-solution assumption —
activity coefficients at 2–4 M ionic strength are neglected. The direction is
conservative for design (predicts a taller bed than needed). The notebook must
show this validation table and the bias warning; do NOT tune constants to hide it.

More accurate alternatives to cite (not implemented — data not openly available):
Deshmukh–Mather activity-coefficient model; Kent–Eisenberg with apparent
constants fitted to the Jou et al. (1982) dataset (I&EC Proc. Des. Dev. 21,
539–544).

## 6. Aqueous MDEA density and viscosity at 25 °C (Al-Ghawas et al., via Atlantis 2016)

    MDEA vol% (→wt%):  20 (20.6)  40 (40.9)  60 (60.9)  80 (80.6)  100 (100)
    ρ (g/mL):          1.0169     1.0371     1.0518     1.0556     1.2313
    μ (mPa·s):         2.262      6.452      20.109     54.254     104.689

Status: secondary reproduction, but from a named primary source (Al-Ghawas et
al.). The 100 vol% density (1.2313) looks inconsistent with pure-MDEA density
(1.038 g/mL at 20 °C) — possible transcription error in the reproduction; do not
use the 100% density point without checking. Temperature dependence of μ and ρ
not recovered — the notebook keeps μ_L and ρ_L as user inputs; the table above
is shown as a 25 °C reference.

## 7. H2S diffusivity in MDEA solutions — NOT usable as extracted

The same Atlantis table lists a diffusivity row "D (10⁻⁹ m²/s): 10235.49,
4787.26, 2099.7, 1022.47, 634.87" attributed to Rinker/Posey. The extracted
units are garbled and the implied values (≈10⁻⁸ m²/s) are unphysically large for
liquid diffusion. DO NOT use these numbers; the notebook keeps D_L as a user
input with a stated default. Recover from Rinker/Posey originals if needed.

## 8. Amine data

- MDEA molar mass: 119.16 g/mol; pure density 1.038–1.044 g/cm³ at 20 °C;
  pKa(MDEAH⁺) 8.52–8.57 at 25 °C (benchchem / literature); model uses 8.63 from §2.
- MDEA protonation is exothermic; pKa falls ~0.02/K (from §2 correlation).

## 9. Applicability limits for the notebook

- Equilibrium model: 20–60 °C (K2 fit range 10–60 °C; Ka,am 20–60 °C), MDEA
  20–100 wt% (Henry table), α in (0, 1). Outside → hard warning, no silent
  extrapolation.
- Ideal-solution bias: −25 to −35% in loading vs Jou/Li–Shen data; conservative.
- Second dissociation of H2S (HS⁻ → S²⁻) neglected: justified (pKa2 ≈ 19 in
  water; negligible at absorber pH 8–11).
- CO2 co-absorption not modeled (H2S-selective service assumed); amine
  degradation, heat effects, and electrolyte non-ideality not modeled.

## 10. Sources (all open, retrieved 2026-09-21)

1. Sander, R., "Compilation of Henry's law constants (version 5.0.0)", ESSD
   2023 — H2S: H^cp = 9.5e-3 mol/(m³·Pa) at 298.15 K, d ln H^cp/d(1/T) = 2100 K.
   https://essd.copernicus.org/articles/15/2689/2023/
2. Mahmud, N. et al., "Reaction Kinetics of Carbon Dioxide in Aqueous Blends of
   N-Methyldiethanolamine and L-Arginine", *Processes* 2019, 7, 81, Table 3 —
   Kw and MDEA protonation-constant correlations (ai, bi, di).
   https://www.mdpi.com/2227-9717/7/2/81
3. Jou, F.-Y., Mather, A.E. & Otto, F.D., "Solubility of H2S and CO2 in Aqueous
   Methyldiethanolamine Solutions", I&EC Proc. Des. Dev. 1982, 21, 539–544
   (paywalled; data via secondary sources below). https://doi.org/10.1021/i200019a001
4. Shoukat, U., Pinto, D.D.D. & Knuutila, H.K., "Vapor–Liquid Equilibrium
   Measurements of H2S in Aqueous MDEA", *ChemEngineering* 2019 (MDPI) —
   validation point: 23.8 wt%, 40 °C, 1 kPa → α = 0.14 (Jou: 0.134, −4.6%).
   https://www.mdpi.com/2305-7084/3/3/71
5. Atlantis Press (2016), GC3178 paper, Table 1 — MDEA solution ρ, μ, H, D at
   25 °C (ρ/μ from Al-Ghawas et al.; H/D from Rinker/Posey).
   https://www.atlantis-press.com/article/25864029.pdf
6. IAPWS Guideline on Henry's constant (2019) — H2S correlation coefficients
   A=−4.51499, B=5.23538, C=4.42126 (273.15–533.09 K); anchor ln(H/1 GPa) =
   −2.8784 at 300 K. Exact printed equation form uncertain — recorded as
   reference only, not coded. http://www.iapws.org/relguide/Henry-Guideline.html
7. U. Maryland CHBE446 course notes (H2SRemoval-MaterialBalance.pdf) —
   Li & Shen (1993) / Huttenhuis et al. (2007) rule of thumb: 30 wt% MDEA,
   p_H2S = 5 kPa → α ≈ 0.1–0.3 (40–100 °C).
   https://user.eng.umd.edu/~nsw/chbe446/H2S/H2SRemoval-MaterialBalance.pdf
