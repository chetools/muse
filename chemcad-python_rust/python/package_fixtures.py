"""Slate definitions, stream-level consistency checker and
speciation structures for the four stored-state specialty-package
fixtures frozen in the 2026-11-21 completion session (GAPS.md):
TEG dehydration (ThermalModes model code 25), sour water
(code 13), hydrogen chloride (HCl) column (code 23) and MEA
sweetening (code 12).

Symbols, defined at first use: component molar flow rate of
component i in a stream, F_i, in moles per second (mol/s);
temperature T in kelvin (K); pressure P in pascal (Pa); vapour
fraction psi (dimensionless); enthalpy rate H_rate in watts (W);
unit index u (dimensionless integer; index 0 is the environment,
so a stream with source 0 is a feed and a stream with target 0
is a product); per-component balance residual for a unit,
R_i = (sum of F_i over outlet streams) - (sum of F_i over inlet
streams), in mol/s; relative residual r_i (dimensionless),
r_i = |R_i| / max(F_i in, F_i out) with the larger of the inlet
and outlet component totals as the scale; total relative
residual r_tot (dimensionless), the same ratio formed on total
molar flow rates in mol/s; acid dissociation constant K_a
(dimensionless, molality scale, standard molality 1 mol/kg),
reported through pKa = -log10(K_a) (dimensionless); standard-
state equilibrium constant of a reaction, K (dimensionless),
supplied to the framework of thermo_packages.py through its
natural logarithm ln K (dimensionless), with ln K = -pKa * ln 10
for a dissociation written in dissociation form; charge of a
species, z (dimensionless, signed); element count of element e
in a species, E_{e,i} (dimensionless).

What this module is: (1) the exact component slate of each
fixture, checked against the fixture file itself; (2) a checker
that quantifies how well the STORED fixture closes component
balances at each unit and overall -- it evaluates the fixture,
not a local package model, and no package evaluation is claimed
from it; (3) process-performance quantities that the stored
streams determine directly (removal fractions, solvent
loadings, product compositions), each a ratio of stored flows;
(4) speciation structures (species, charges, element matrix,
reactions) whose equilibrium constants are entered ONLY where
a published value was in hand at build time, converted as
above, and are otherwise recorded as None with the missing
source named. No constant is fitted to any fixture in this
module, and no databank identifier is asserted for any
component (the fixtures record component names only).

Published constants used (all at T = 298.15 K, dilute aqueous,
zero ionic strength, unless stated):
- pKa(NH4+) = 9.25, pKa1(H2S) = 7.05, pKa1(carbonic acid,
  apparent, CO2(aq) + H2CO3 combined) = 6.35, pKa2(HCO3-) =
  10.33, pKw(water) = 13.995: CRC Handbook of Chemistry and
  Physics, "Dissociation Constants of Inorganic Acids and
  Bases" (Haynes, W. M., ed.; underlying compilation Perrin,
  D. D., Ionization Constants of Inorganic Acids and Bases in
  Aqueous Solution, 2nd ed., Pergamon, 1982).
- pKa(MEAH+, the protonated monoethanolamine ion) = 9.50:
  amine dissociation-constant measurements reported for
  monoethanolamine (MEA) at 298.15 K (potentiometric studies
  of alkanolamine pKa values, 293-333 K, in which MEA is the
  benchmark amine; values 9.43-9.50 appear across studies, and
  9.50 is the value carried here, so derived constants inherit
  an uncertainty of about 0.07 in pKa, about 0.16 in ln K).
- pKa(HCl) approximately -7: hydrogen chloride is a strong
  acid, levelled in water; the value is an estimate, not a
  measurement in water (Harris, D. C., Quantitative Chemical
  Analysis, strong-acid table; CRC Handbook lists HCl as
  completely dissociated). It is used only to demonstrate
  near-complete dissociation at a dilute stated composition,
  never at a fixture concentration.
Constants deliberately NOT entered:
- MEA carbamate formation: a published correlation exists
  (Aroua, M. K., Benamor, A. and Haji-Sulaiman, M. Z.,
  J. Chem. Eng. Data 44 (1999) 887-891) but its coefficients
  were not in hand at build time, so ln K is None.
- Second dissociation of H2S (HS- -> H+ + S2-): published
  pKa2 values disagree widely (the CRC table above gives 19;
  other compilations give about 13-14), so the reaction and
  the S2- species are excluded rather than guessed.
- Temperature dependence of every constant above: no enthalpy
  of dissociation was in hand, so all ln K values apply at
  298.15 K only. The fixture streams span 299-478 K, so no
  quantitative speciation solve of a fixture state is claimed.
Speciation model-form sources (structure, not constants):
Edwards, T. J., Maurer, G., Newman, J. and Prausnitz, J. M.,
AIChE J. 24 (1978) 966-976 (volatile weak electrolytes in
water: the sour-water reaction set); Kent, R. L. and
Eisenberg, B., Hydrocarbon Process. 55(2) (1976) 87-90, and
Deshmukh, R. D. and Mather, A. E., Chem. Eng. Sci. 36 (1981)
355-362 (acid-gas / alkanolamine reaction sets, the basis of
the MEA structure below and of thermo_packages_amine.py).
TEG data sources for a future build (no TEG constant is
entered here): Herskowitz, M. and Gottlieb, M., J. Chem. Eng.
Data 29 (1984), vapour-liquid equilibrium in aqueous glycol
solutions series; Parrish, W. R., Won, K. W. and Baltatu,
M. E., Proc. 65th GPA Annual Convention (1986) 202-210
(TEG-water phase behaviour); Qvistgaard, D. et al., Fluid
Phase Equilib. 565 (2023) 113660 (TEG / water / natural-gas
vapour-liquid equilibrium measurements and modelling).
"""
import json
import math
from pathlib import Path

import numpy as np

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures"
LN10 = math.log(10.0)
T_CONSTANTS = 298.15  # K; every published constant below is at this T

# ------------------------------------------------------------------
# Slates: component names exactly as recorded in each fixture,
# in fixture order. test_package_fixtures.py asserts equality
# with the fixture files, so a slate cannot drift silently.
# ------------------------------------------------------------------
SLATES = {
    "teg": {
        "fixture": "flowsheet-teg-dehydration-stored.json",
        "model_code": 25,
        "package_kind": "teg",
        "components": [
            "Nitrogen", "Carbon Dioxide", "Hydrogen Sulfide",
            "Methane", "Ethane", "Propane", "I-Butane", "N-Butane",
            "I-Pentane", "N-Pentane", "N-Hexane", "N-Heptane",
            "Water", "Triglycol"],
        "solvent": "Triglycol",
        "reacting": False,
    },
    "sour_water": {
        "fixture": "flowsheet-sour-water-stored.json",
        "model_code": 13,
        "package_kind": "sour_water",
        "components": ["Hydrogen Sulfide", "Water", "Ammonia"],
        "solvent": "Water",
        "reacting": True,
    },
    "hcl": {
        "fixture": "flowsheet-hcl-column-stored.json",
        "model_code": 23,
        "package_kind": "electrolyte",
        "components": ["Nitrogen", "Oxygen", "HydrogenChloride",
                       "Water"],
        "solvent": "Water",
        "reacting": True,
    },
    "mea_sweetening": {
        "fixture": "flowsheet-mea-sweetening-stored.json",
        "model_code": 12,
        "package_kind": "amine",
        "components": ["Monoethanolamine", "Hydrogen Sulfide",
                       "Carbon Dioxide", "Water", "Methane",
                       "Ethane"],
        "solvent": "Water",
        "reacting": True,
    },
}


def load_fixture(key):
    """Load the stored-state fixture for a slate key and check
    its recorded slate against SLATES. Returns the fixture
    dictionary (streams carry T in K, P in Pa, F_i in mol/s,
    psi dimensionless, H_rate in W)."""
    fx = json.loads((FIXTURE_DIR / SLATES[key]["fixture"]).read_text())
    if fx["components"] != SLATES[key]["components"]:
        raise ValueError(f"{key}: fixture slate != SLATES slate")
    for s in fx["streams"]:
        if len(s["flows_mol_s"]) != len(fx["components"]):
            raise ValueError(f"{key}: stream {s['id']} flow count")
        if s["T_K"] <= 0.0 or s["P_Pa"] <= 0.0:
            raise ValueError(f"{key}: stream {s['id']} T or P")
        if not (0.0 <= s["vapour_fraction"] <= 1.0):
            raise ValueError(f"{key}: stream {s['id']} psi range")
    return fx


# ------------------------------------------------------------------
# Stream-level consistency checker (evaluates the stored fixture)
# ------------------------------------------------------------------
def _totals(streams, ncomp):
    out = np.zeros(ncomp)
    for s in streams:
        out += np.asarray(s["flows_mol_s"], dtype=float)
    return out


def unit_balances(fx):
    """Per-unit component balances of a stored fixture.

    Units are the indices u = 1..nunits appearing as stream
    source/target (0 is the environment). For each unit returns
    inlet and outlet stream ids, per-component residuals R_i in
    mol/s, per-component relative residuals r_i (dimensionless),
    the total relative residual r_tot (dimensionless), and the
    worst r_i over significant components (inlet or outlet flow
    at least 1e-6 of the unit total flow, so trace components
    stored at round-off do not dominate the headline number;
    the all-component worst is returned as well).
    """
    ncomp = len(fx["components"])
    units = sorted({s["src"] for s in fx["streams"] if s["src"] != 0}
                   | {s["tgt"] for s in fx["streams"] if s["tgt"] != 0})
    results = {}
    for u in units:
        ins = [s for s in fx["streams"] if s["tgt"] == u]
        outs = [s for s in fx["streams"] if s["src"] == u]
        fi = _totals(ins, ncomp)
        fo = _totals(outs, ncomp)
        resid = fo - fi
        scale = np.maximum(np.abs(fi), np.abs(fo))
        rel = np.where(scale > 0.0, np.abs(resid) / np.maximum(scale, 1e-300), 0.0)
        tot_in = float(fi.sum())
        tot_out = float(fo.sum())
        r_tot = abs(tot_out - tot_in) / max(tot_in, tot_out)
        sig = scale >= 1e-6 * max(tot_in, tot_out)
        results[u] = {
            "in_ids": [s["id"] for s in ins],
            "out_ids": [s["id"] for s in outs],
            "resid_mol_s": resid,
            "rel": rel,
            "r_tot": r_tot,
            "worst_rel_all": float(rel.max()) if ncomp else 0.0,
            "worst_rel_sig": float(rel[sig].max()) if sig.any() else 0.0,
            "worst_sig_component": (
                fx["components"][int(np.argmax(np.where(sig, rel, -1.0)))]
                if sig.any() else None),
            "total_in_mol_s": tot_in,
            "total_out_mol_s": tot_out,
        }
    return results


def overall_balance(fx):
    """Overall balance: environment feeds (source 0) against
    products (target 0). Returns per-component residuals in
    mol/s, relative residuals on the max(in, out) scale, the
    total relative residual, and the same total residual scaled
    by the total internal throughput (sum of all stream totals
    in mol/s), which is the meaningful scale for a flowsheet
    with a circulating solvent and no solvent makeup feed."""
    ncomp = len(fx["components"])
    feeds = [s for s in fx["streams"] if s["src"] == 0]
    prods = [s for s in fx["streams"] if s["tgt"] == 0]
    fi = _totals(feeds, ncomp)
    fo = _totals(prods, ncomp)
    resid = fo - fi
    scale = np.maximum(np.abs(fi), np.abs(fo))
    rel = np.where(scale > 0.0, np.abs(resid) / np.maximum(scale, 1e-300), 0.0)
    throughput = float(sum(sum(s["flows_mol_s"]) for s in fx["streams"]))
    return {"resid_mol_s": resid, "rel": rel,
            "r_tot": abs(float(fo.sum()) - float(fi.sum()))
            / max(float(fi.sum()), float(fo.sum())),
            "total_resid_on_throughput": abs(float(fo.sum() - fi.sum()))
            / throughput,
            "feed_ids": [s["id"] for s in feeds],
            "product_ids": [s["id"] for s in prods]}


def phase_split_units(fx):
    """Units with one inlet and two outlets, one outlet at
    psi = 1 (vapour) and one at psi = 0 (liquid): the stored
    split determines an apparent equilibrium ratio for each
    component, K_app,i = (F_i,vap / F_tot,vap) / (F_i,liq /
    F_tot,liq) (dimensionless), and a vapour split fraction
    F_tot,vap / F_tot,in (dimensionless). Returns a dictionary
    keyed by unit index."""
    by_id = {s["id"]: s for s in fx["streams"]}
    out = {}
    bals = unit_balances(fx)
    for u, b in bals.items():
        if len(b["in_ids"]) != 1 or len(b["out_ids"]) != 2:
            continue
        o = [by_id[i] for i in b["out_ids"]]
        vap = [s for s in o if s["vapour_fraction"] == 1.0]
        liq = [s for s in o if s["vapour_fraction"] == 0.0]
        if len(vap) != 1 or len(liq) != 1:
            continue
        fv = np.asarray(vap[0]["flows_mol_s"], dtype=float)
        fl = np.asarray(liq[0]["flows_mol_s"], dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            k_app = np.where(fl > 0.0,
                             (fv / fv.sum()) / np.maximum(fl / fl.sum(), 1e-300),
                             np.inf)
        out[u] = {"vap_id": vap[0]["id"], "liq_id": liq[0]["id"],
                  "vap_split": float(fv.sum() / (fv.sum() + fl.sum())),
                  "K_app": k_app}
    return out


# ------------------------------------------------------------------
# Performance quantities determined directly by the stored streams
# (ratios of stored flows in mol/s; no model is evaluated)
# ------------------------------------------------------------------
def _stream(fx, sid):
    return next(s for s in fx["streams"] if s["id"] == sid)


def _flow(fx, sid, component):
    i = fx["components"].index(component)
    return float(_stream(fx, sid)["flows_mol_s"][i])


def _total(fx, sid):
    return float(sum(_stream(fx, sid)["flows_mol_s"]))


def performance(key):
    """Stored-state performance ratios for one fixture. Every
    value is a ratio of stored molar flows (dimensionless);
    stream ids refer to the fixture's own numbering."""
    fx = load_fixture(key)
    if key == "teg":
        # Contactor is unit 1: wet gas stream 1 in, dry gas
        # stream 8 and rich glycol stream 2 out; lean glycol
        # returns on stream 16, wet gas enters with no glycol.
        water_in = _flow(fx, 1, "Water")
        water_dry = _flow(fx, 8, "Water")
        lean = _stream(fx, 16)["flows_mol_s"]
        rich = _stream(fx, 2)["flows_mol_s"]
        teg_loss = sum(_flow(fx, s, "Triglycol") for s in (3, 6, 9))
        return {
            "water_removal_contactor": 1.0 - water_dry / water_in,
            "lean_teg_water_molfrac": lean[12] / sum(lean),
            "rich_teg_water_molfrac": rich[12] / sum(rich),
            "teg_in_products_mol_s": teg_loss,
            "teg_circulation_mol_s": _flow(fx, 16, "Triglycol"),
            "teg_loss_on_circulation": teg_loss / _flow(fx, 16, "Triglycol"),
        }
    if key == "sour_water":
        # Single stripper unit 1: feed 1, vapour product 2,
        # stripped water 3.
        return {
            "h2s_stripped": 1.0 - _flow(fx, 3, "Hydrogen Sulfide")
            / _flow(fx, 1, "Hydrogen Sulfide"),
            "nh3_stripped": 1.0 - _flow(fx, 3, "Ammonia")
            / _flow(fx, 1, "Ammonia"),
            "vapour_h2s_molfrac": _flow(fx, 2, "Hydrogen Sulfide")
            / _total(fx, 2),
            "vapour_nh3_molfrac": _flow(fx, 2, "Ammonia") / _total(fx, 2),
            "bottoms_h2s_molfrac": _flow(fx, 3, "Hydrogen Sulfide")
            / _total(fx, 3),
        }
    if key == "hcl":
        # Packed column unit 1: liquid feed 1 and gas feed 2 in;
        # treated gas 3 and acid product 4 out.
        return {
            "hcl_capture_from_gas": 1.0 - _flow(fx, 3, "HydrogenChloride")
            / _flow(fx, 2, "HydrogenChloride"),
            "acid_hcl_molfrac": _flow(fx, 4, "HydrogenChloride")
            / _total(fx, 4),
            "acid_water_molfrac": _flow(fx, 4, "Water") / _total(fx, 4),
            "gas_water_pickup_mol_s": _flow(fx, 3, "Water"),
        }
    if key == "mea_sweetening":
        # Absorber unit 1: sour gas 1 and lean amine 13 in;
        # sweet gas 7 and rich amine 8 out. Regenerator unit 2:
        # rich 9 in, lean 10 and acid gas 12 out.
        def loading(sid):
            acid = (_flow(fx, sid, "Hydrogen Sulfide")
                    + _flow(fx, sid, "Carbon Dioxide"))
            return acid / _flow(fx, sid, "Monoethanolamine")
        return {
            "h2s_removal": 1.0 - _flow(fx, 7, "Hydrogen Sulfide")
            / _flow(fx, 1, "Hydrogen Sulfide"),
            "co2_removal": 1.0 - _flow(fx, 7, "Carbon Dioxide")
            / _flow(fx, 1, "Carbon Dioxide"),
            "rich_loading_mol_per_mol_mea": loading(8),
            "lean_loading_mol_per_mol_mea": loading(4),
            "cyclic_loading": loading(8) - loading(4),
            "sweet_gas_h2s_molfrac": _flow(fx, 7, "Hydrogen Sulfide")
            / _total(fx, 7),
            "acid_gas_co2_molfrac": _flow(fx, 12, "Carbon Dioxide")
            / _total(fx, 12),
        }
    raise ValueError(key)


# ------------------------------------------------------------------
# Speciation structures. Each reaction carries ln K at
# T_CONSTANTS in K, or None where no published value was in
# hand. Element rows are full atom counts (H, and the hetero
# atoms of the system) so element conservation of every
# reaction can be checked exactly, water included as a species.
# ------------------------------------------------------------------
def _lnk_from_pka(pka):
    """ln K (dimensionless) of a dissociation from its pKa
    (dimensionless): ln K = -pKa * ln 10."""
    return -float(pka) * LN10


PKA = {  # published values, sources in the module header
    "NH4+": 9.25,
    "H2S_1": 7.05,
    "carbonic_1": 6.35,
    "carbonic_2": 10.33,
    "water": 13.995,       # pKw
    "MEAH+": 9.50,
    "HCl": -7.0,           # estimated (strong acid, levelled)
}

SPECIATION = {
    "sour_water": {
        "species": ["H2S(aq)", "HS-", "NH3(aq)", "NH4+", "H+",
                    "OH-", "H2O"],
        "z": [0, -1, 0, 1, 1, -1, 0],
        # element rows: H, S, N, O
        "elements": [[2, 1, 3, 4, 1, 1, 2],
                     [1, 1, 0, 0, 0, 0, 0],
                     [0, 0, 1, 1, 0, 0, 0],
                     [0, 0, 0, 0, 0, 1, 1]],
        "reactions": [
            {"name": "H2S dissociation",
             "nu": [-1.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0],
             "lnK": _lnk_from_pka(PKA["H2S_1"]),
             "source": "pKa1(H2S) = 7.05, CRC/Perrin table"},
            {"name": "NH4+ dissociation",
             "nu": [0.0, 0.0, 1.0, -1.0, 1.0, 0.0, 0.0],
             "lnK": _lnk_from_pka(PKA["NH4+"]),
             "source": "pKa(NH4+) = 9.25, CRC/Perrin table"},
            {"name": "water autoprotolysis",
             "nu": [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, -1.0],
             "lnK": _lnk_from_pka(PKA["water"]),
             "source": "pKw = 13.995, CRC/Perrin table"},
            {"name": "NH3 + H2S salt formation (derived)",
             "nu": [-1.0, 1.0, -1.0, 1.0, 0.0, 0.0, 0.0],
             "lnK": _lnk_from_pka(PKA["H2S_1"])
             - _lnk_from_pka(PKA["NH4+"]),
             "source": "derived: Ka(H2S) / Ka(NH4+), both CRC"},
        ],
        "excluded": [
            "HS- -> H+ + S2-: published pKa2 values disagree "
            "(19 in the CRC table; about 13-14 elsewhere); "
            "excluded rather than guessed."],
        "framework_note": "Not a thermo_packages.PackageCase: "
                        "the reactions carry H2O and H+ as "
                        "species, outside the framework's "
                        "inert-solvent scope, and the constants "
                        "hold at 298.15 K while the fixture "
                        "stripper spans 333-377 K with no "
                        "dissociation enthalpy in hand.",
    },
    "hcl": {
        "species": ["HCl(aq)", "H+", "Cl-", "H2O"],
        "z": [0, 1, -1, 0],
        # element rows: H, Cl, O
        "elements": [[1, 1, 0, 2],
                     [1, 0, 1, 0],
                     [0, 0, 0, 1]],
        "reactions": [
            {"name": "HCl dissociation",
             "nu": [-1.0, 1.0, 1.0, 0.0],
             "lnK": _lnk_from_pka(PKA["HCl"]),
             "source": "pKa(HCl) approx -7, estimated (strong "
                       "acid, levelled in water)"},
        ],
        "excluded": [
            "Water autoprotolysis is not entered in this "
            "structure: it would need OH- added as a species; "
            "pKw = 13.995 (CRC table) would supply its ln K."],
        "framework_note": "The reduced reaction HCl(aq) -> H+ "
                          "+ Cl- (water not a reactant) fits "
                          "the framework and is demonstrated "
                          "in test_package_fixtures.py at a "
                          "dilute stated composition only; "
                          "the fixture acid product is about "
                          "7.6 mol of HCl per kilogram of water "
                          "(stored flows), far outside the "
                          "Debye-Huckel range of the framework "
                          "activity model.",
    },
    "mea_sweetening": {
        "species": ["MEA", "MEAH+", "MEACOO-", "CO2(aq)",
                    "HCO3-", "CO3--", "H2S(aq)", "HS-", "H+",
                    "OH-", "H2O"],
        "z": [0, 1, -1, 0, -1, -2, 0, -1, 1, -1, 0],
        # element rows: H, C, N, O, S (MEA = C2H7NO,
        # MEACOO- = C3H6NO3-, CO2-derived carbon counted in C)
        "elements": [[7, 8, 6, 0, 1, 0, 2, 1, 1, 1, 2],
                     [2, 2, 3, 1, 1, 1, 0, 0, 0, 0, 0],
                     [1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
                     [1, 1, 3, 2, 3, 3, 0, 0, 0, 1, 1],
                     [0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0]],
        "reactions": [
            {"name": "MEAH+ dissociation",
             "nu": [1.0, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                    1.0, 0.0, 0.0],
             "lnK": _lnk_from_pka(PKA["MEAH+"]),
             "source": "pKa(MEAH+) = 9.50, amine pKa studies"},
            {"name": "MEA + CO2 + H2O -> MEAH+ + HCO3- (derived)",
             "nu": [-1.0, 1.0, 0.0, -1.0, 1.0, 0.0, 0.0, 0.0,
                    0.0, 0.0, -1.0],
             "lnK": _lnk_from_pka(PKA["carbonic_1"])
             - _lnk_from_pka(PKA["MEAH+"]),
             "source": "derived: Ka1(carbonic, apparent) / "
                       "Ka(MEAH+), CRC and amine pKa values"},
            {"name": "2 MEA + CO2 -> MEAH+ + MEACOO- (carbamate)",
             "nu": [-2.0, 1.0, 1.0, -1.0, 0.0, 0.0, 0.0, 0.0,
                    0.0, 0.0, 0.0],
             "lnK": None,
             "source": "MISSING: carbamate equilibrium "
                       "correlation of Aroua et al. (1999) "
                       "named in the header; coefficients not "
                       "in hand, not guessed"},
            {"name": "MEA + H2S -> MEAH+ + HS- (derived)",
             "nu": [-1.0, 1.0, 0.0, 0.0, 0.0, 0.0, -1.0, 1.0,
                    0.0, 0.0, 0.0],
             "lnK": _lnk_from_pka(PKA["H2S_1"])
             - _lnk_from_pka(PKA["MEAH+"]),
             "source": "derived: Ka(H2S) / Ka(MEAH+)"},
            {"name": "HCO3- dissociation",
             "nu": [0.0, 0.0, 0.0, 0.0, -1.0, 1.0, 0.0, 0.0,
                    1.0, 0.0, 0.0],
             "lnK": _lnk_from_pka(PKA["carbonic_2"]),
             "source": "pKa2(HCO3-) = 10.33, CRC/Perrin table"},
            {"name": "water autoprotolysis",
             "nu": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                    1.0, 1.0, -1.0],
             "lnK": _lnk_from_pka(PKA["water"]),
             "source": "pKw = 13.995, CRC/Perrin table"},
        ],
        "excluded": [
            "Methane and ethane (fixture slate) are physically "
            "dissolved only; no reaction is asserted for them.",
            "The fitted MEA/CO2-only data set of "
            "thermo_packages_amine.py (ln K fitted at the "
            "393 K, 0.20-loading anchor) is a separate, "
            "labelled fit and is not reused here."],
        "framework_note": "Structure only: the carbamate ln K "
                          "is missing, the entered constants "
                          "hold at 298.15 K while the fixture "
                          "spans 300-397 K, and no heat of "
                          "solution per reaction is in hand, "
                          "so no PackageCase is built and no "
                          "speciation of a fixture state is "
                          "claimed.",
    },
    "teg": {
        "species": [],
        "z": [],
        "elements": [],
        "reactions": [],
        "excluded": [
            "No speciation: TEG dehydration is physical "
            "absorption. The package content is vapour-liquid "
            "equilibrium data for TEG / water / hydrocarbons "
            "and acid gases, not reactions."],
        "framework_note": "No PackageCase applies (the "
                          "framework case requires reactions). "
                          "The deliverable for TEG is the "
                          "slate, the checker and the stored-"
                          "state performance ratios.",
    },
}


def validate_speciation(key):
    """Exact element and charge conservation of every reaction
    in a speciation structure. Returns a list of per-reaction
    dictionaries with the largest absolute element residual
    (dimensionless count) and the charge residual
    (dimensionless)."""
    spec = SPECIATION[key]
    if not spec["reactions"]:
        return []
    E = np.asarray(spec["elements"], dtype=float)
    z = np.asarray(spec["z"], dtype=float)
    out = []
    for r in spec["reactions"]:
        nu = np.asarray(r["nu"], dtype=float)
        out.append({"name": r["name"],
                    "element_residual": float(np.max(np.abs(E @ nu))),
                    "charge_residual": float(z @ nu),
                    "lnK": r["lnK"]})
    return out


def hcl_framework_case():
    """The reduced HCl dissociation as a thermo_packages
    PackageCase at T_CONSTANTS in K, for the dilute
    demonstration in the test file. Species HCl(aq), H+, Cl-
    (charges z = 0, +1, -1); element rows H and Cl; activity
    model: extended Debye-Huckel with A_gamma = 1.17
    (kg/mol)^0.5 (the 298.15 K water value on the natural-log
    scale, as recorded in thermo_packages_amine.py) and
    b_param = 1.2 (dimensionless); heat of solution
    delta_h_soln = 0 J/mol is a placeholder required by the
    framework structure, not data: no enthalpy claim is made
    and the case is never used in an enthalpy balance."""
    from thermo_packages import ActivityParams, PackageCase
    return PackageCase(
        package_kind="electrolyte", T=T_CONSTANTS, W=1.0,
        species_names=["HCl(aq)", "H+", "Cl-"], z=[0, 1, -1],
        elements=[[1, 1, 0], [1, 0, 1]],
        nu=[[-1.0, 1.0, 1.0]],
        lnK=[_lnk_from_pka(PKA["HCl"])],
        activity=ActivityParams(mode="dh", A_gamma=1.17,
                                b_param=1.2),
        delta_h_soln=[0.0])
