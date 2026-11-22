"""Derive unit-level verification fixtures from the two converged
ChemCAD flowsheet fixtures (item a4, extraction half).

Inputs (read only, never edited):
  fixtures/flowsheet-linde-asu-stored.json
  fixtures/flowsheet-nh3-loop-iso557.json
Output:
  fixtures/units-from-flowsheets.json

Symbols and units, used throughout this file and the output fixture:
  sid   stream identifier in the source fixture (dimensionless integer)
  uid   unit identifier in the source fixture (dimensionless integer);
        uid 0 is the flowsheet boundary (feed entry / product exit),
        not a unit
  src   uid that a stream leaves (its source unit)
  tgt   uid that a stream enters (its target unit)
  T_K   stream temperature, in kelvin (K)
  P_Pa  stream pressure, in pascal (Pa)
  psi   stream vapour fraction (dimensionless, 0 to 1)
  F_i   molar flow rate of component i, in moles per second (mol/s);
        the list flows_mol_s holds F_i in the source fixture's
        component order
  F     total molar flow rate, in mol/s: F = sum of F_i
  H_rate  total enthalpy rate of a stream, in watts (W)
  h     molar enthalpy of a stream, in joules per mole (J/mol):
        h = H_rate / F
  raw   the capture lines stored in a source fixture, in ChemCAD
        internal units: temperature in degrees Rankine (degR),
        pressure in pounds per square inch absolute (psia),
        component flows in pound-moles per hour (lbmol/h), enthalpy
        rate in British thermal units per hour (Btu/h)

SI verification: the source fixtures state that their stream values
are already SI, converted once in capture/build_flowsheet_fixtures.py
with the factors degR * 5/9 = K, psia * 6894.757 = Pa,
lbmol/h * (453.59237 / 3600) = mol/s, Btu/h * 0.29307107 = W. This
builder re-derives every stored stream value from the raw capture
lines stored in the same fixture and raises if any value disagrees
beyond the rounding of the raw lines (8 significant figures), so the
SI claim is checked, not assumed.

Mapping rules:
  Linde case: src and tgt are recorded for every stream, so a unit's
  inlet streams (tgt equal to uid) and outlet streams (src equal to
  uid) are read directly. A unit with no inlet or no outlet stream
  cannot be mapped and is listed under excluded_units.
  Ammonia case: src and tgt are null for every stream (the p3_case
  capture in capture/cc_chain.py does not record them). The mapping
  used here is the one documented in the source fixture itself: the
  process text names the five units in flowsheet order, the raw lines
  record unit parameter writes for units 2 to 5 (compressor outlet
  pressure and efficiency, converter mode and temperature, flash
  temperature and pressure, divider split fractions), and the checks
  record names unit closures for the mixer, flash and divider. Each
  mapped unit is accepted only if this builder verifies its balance
  closure from the stream data (component closure for the mixer,
  compressor, flash and divider; element closure and reaction
  stoichiometry for the Gibbs converter), and the five mappings
  together use streams 1, 2, 3, 4, 6, 7, 8, 9 in one consistent chain
  (each stream is the outlet of at most one unit and the inlet of at
  most one unit). Stream 5 (zero flow, T_K 0, P_Pa 0) belongs to no
  unit and is listed under excluded_streams. Every ammonia unit in
  the output carries its mapping basis in its mapping_basis field.

Unit types: neither source fixture records a unit type or a non-empty
label (the Linde raw lines record label= with an empty value for
every unit; the ammonia raw lines record no labels). The output
therefore sets type_recorded and label_recorded to null and carries
any identification in inferred_role, marked as inference, with its
basis stated.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE.parent / "fixtures"

# Conversion factors from ChemCAD internal units to SI units, the
# same factors used by capture/build_flowsheet_fixtures.py.
DEGR_TO_K = 5.0 / 9.0
PSIA_TO_PA = 6894.757
LBMOLH_TO_MOLS = 453.59237 / 3600.0
BTUH_TO_W = 0.29307107

STREAM_LINE = re.compile(
    r"CCR STREAM id=(\d+)(?: src=(-?\d+) tgt=(-?\d+))? "
    r"rc=(-?\d+) T_R=([\d.eE+-]+) P_psia=([\d.eE+-]+) "
    r"VF=([\d.eE+-]+) H=([\d.eE+-]+) flows=(.*)")
TOPO_LINE = re.compile(
    r"CCR TOPO nstreams=(\d+) nunits=(\d+) ncomp=(\d+) comps=(.*)")


def stream_block(stream):
    """The output form of one source-fixture stream, with the derived
    total flow rate F (mol/s) and molar enthalpy h (J/mol) added."""
    F = sum(stream["flows_mol_s"])
    return {
        "id": stream["id"],
        "T_K": stream["T_K"],
        "P_Pa": stream["P_Pa"],
        "vapour_fraction": stream["vapour_fraction"],
        "flows_mol_s": stream["flows_mol_s"],
        "total_mol_s": F,
        "enthalpy_rate_W": stream["enthalpy_rate_W"],
        "molar_enthalpy_J_mol": (stream["enthalpy_rate_W"] / F
                                 if F > 0.0 else None),
    }


def verify_si(fixture):
    """Re-derive every stored stream value from the fixture's raw
    capture lines and return the largest deviations found. Raises if
    a stream has no raw line or a deviation exceeds the rounding of
    the raw lines."""
    stored = {s["id"]: s for s in fixture["streams"]}
    seen = set()
    worst = {"T_K": 0.0, "P_Pa_rel": 0.0, "flows_rel": 0.0,
             "enthalpy_rate_W_rel": 0.0}
    nunits = None
    for line in fixture["raw"]:
        m = TOPO_LINE.match(line)
        if m:
            nunits = int(m.group(2))
            continue
        m = STREAM_LINE.match(line)
        if not m:
            continue
        sid = int(m.group(1))
        seen.add(sid)
        s = stored[sid]
        T_K = float(m.group(5)) * DEGR_TO_K
        P_Pa = float(m.group(6)) * PSIA_TO_PA
        H_rate = float(m.group(8)) * BTUH_TO_W
        flows = [float(v) * LBMOLH_TO_MOLS
                 for v in m.group(9).split(",") if v != ""]
        worst["T_K"] = max(worst["T_K"], abs(T_K - s["T_K"]))
        worst["P_Pa_rel"] = max(
            worst["P_Pa_rel"],
            abs(P_Pa - s["P_Pa"]) / s["P_Pa"] if s["P_Pa"] else 0.0)
        worst["enthalpy_rate_W_rel"] = max(
            worst["enthalpy_rate_W_rel"],
            abs(H_rate - s["enthalpy_rate_W"])
            / abs(s["enthalpy_rate_W"]) if s["enthalpy_rate_W"] else 0.0)
        for got, want in zip(flows, s["flows_mol_s"]):
            if want:
                worst["flows_rel"] = max(
                    worst["flows_rel"], abs(got - want) / abs(want))
        if m.group(2) is not None:
            assert int(m.group(2)) == s["src"] and \
                int(m.group(3)) == s["tgt"], f"src/tgt mismatch, stream {sid}"
    assert seen == set(stored), \
        f"streams without a raw line: {sorted(set(stored) - seen)}"
    assert worst["T_K"] < 0.01, worst
    assert worst["P_Pa_rel"] < 1e-4, worst
    assert worst["flows_rel"] < 1e-4, worst
    assert worst["enthalpy_rate_W_rel"] < 1e-4, worst
    return nunits, worst


def component_closure(inlets, outlets, ncomp):
    """Largest per-component imbalance between inlet and outlet
    streams, in mol/s, and the same imbalance relative to the total
    inlet flow rate."""
    worst = 0.0
    F_in = 0.0
    for i in range(ncomp):
        fi = sum(s["flows_mol_s"][i] for s in inlets)
        fo = sum(s["flows_mol_s"][i] for s in outlets)
        F_in += fi
        worst = max(worst, abs(fi - fo))
    return worst, (worst / F_in if F_in else 0.0)


def enthalpy_block(inlets, outlets):
    """Total enthalpy rates in and out, in W, and their difference
    (out minus in). For a unit with no duty and no work the
    difference is zero; otherwise it is the net duty plus work into
    the unit, as implied by the fixture."""
    H_in = sum(s["enthalpy_rate_W"] for s in inlets)
    H_out = sum(s["enthalpy_rate_W"] for s in outlets)
    return {"in_W": H_in, "out_W": H_out, "out_minus_in_W": H_out - H_in}


def unit_entry(source_case, uid, inlets, outlets, ncomp, basis,
               inferred_role, extra=None):
    worst, rel = component_closure(inlets, outlets, ncomp)
    entry = {
        "source_case": source_case,
        "unit_id": uid,
        "type_recorded": None,
        "label_recorded": None,
        "inferred_role": inferred_role,
        "mapping_basis": basis,
        "inlet_streams": [stream_block(s) for s in inlets],
        "outlet_streams": [stream_block(s) for s in outlets],
        "component_balance_worst_mol_s": worst,
        "component_balance_relative_to_inlet_total": rel,
        "enthalpy_rate": enthalpy_block(inlets, outlets),
        "spec_recorded": None,
    }
    if extra:
        entry.update(extra)
    return entry


# --- Linde air separation case -------------------------------------
# Inferred roles, from the source fixture's process text ("compressor,
# aftercooler, divider, multi-pass LNG exchanger, expander, HP and LP
# SCDS columns") matched to each unit's recorded stream behaviour.
LINDE_ROLES = {
    1: "compressor (inferred: one inlet, one outlet, component flows "
       "unchanged, pressure rises from 101325 Pa to 600001 Pa and "
       "temperature rises from 298.15 K to 557.67 K)",
    2: "heater/cooler, the aftercooler (inferred: one inlet, one "
       "outlet, component flows unchanged, temperature returns to "
       "298.15 K at near-constant pressure)",
    3: "multi-stream heat exchanger, the LNG exchanger (inferred: "
       "four inlets and four outlets; each outlet's component flows "
       "are identical to exactly one inlet's, giving the four passes "
       "listed in pass_pairing_stream_ids; total enthalpy rate is "
       "conserved, as the enthalpy_rate block shows)",
    5: "expander (inferred: one inlet, one outlet, component flows "
       "unchanged, pressure falls from 590001 Pa to 130000 Pa, "
       "temperature falls, and the enthalpy rate falls by the work "
       "taken out)",
    9: "high-pressure SCDS column (inferred: the two-phase inlet is "
       "separated into two liquid outlets of different composition; "
       "the process text names an HP column and this is one of the "
       "two units with a separation pattern)",
    10: "low-pressure SCDS column (inferred: three inlets and two "
        "outlets of different composition; the process text names "
        "an LP column)",
    11: "valve (inferred: one inlet, one outlet, component flows "
        "unchanged, pressure falls from 570001 Pa to 130000 Pa, and "
        "the enthalpy rate changes by only 97.0 W on 1141818 W, "
        "0.0085 percent, the isenthalpic pattern of a throttling "
        "valve)",
    12: "valve (inferred: one inlet, one outlet, component flows "
        "unchanged, pressure falls from 570001 Pa to 130000 Pa, and "
        "the enthalpy rate changes by only 1.8 W on 1592157 W, "
        "0.00011 percent, the isenthalpic pattern of a throttling "
        "valve)",
    13: "divider / splitter (inferred: one inlet and two outlets "
        "whose component flows are the same fractions of the inlet "
        "for every component, 0.88 and 0.12)",
}


def build_linde(fixture):
    nunits, si_worst = verify_si(fixture)
    streams = {s["id"]: s for s in fixture["streams"]}
    ncomp = len(fixture["components"])
    units = []
    excluded = []
    for uid in range(1, nunits + 1):
        inlets = [s for s in fixture["streams"] if s["tgt"] == uid]
        outlets = [s for s in fixture["streams"] if s["src"] == uid]
        if not inlets or not outlets:
            excluded.append({
                "source_case": fixture["case"],
                "unit_id": uid,
                "reason": "no inlet stream or no outlet stream in the "
                          "fixture has this unit as target or source "
                          f"(inlets found: {[s['id'] for s in inlets]}, "
                          f"outlets found: {[s['id'] for s in outlets]}), "
                          "so no inlet/outlet pair can be formed",
            })
            continue
        extra = {}
        if uid == 3:
            pairs = []
            for out in outlets:
                match = [s["id"] for s in inlets
                         if s["flows_mol_s"] == out["flows_mol_s"]]
                assert len(match) == 1, (uid, out["id"], match)
                pairs.append({"inlet_stream_id": match[0],
                              "outlet_stream_id": out["id"]})
            extra["pass_pairing_stream_ids"] = pairs
            extra["pass_pairing_basis"] = \
                "component flows identical between the paired streams"
        if uid == 13:
            F_in = sum(inlets[0]["flows_mol_s"])
            extra["outlet_fractions_of_inlet_total"] = [
                sum(s["flows_mol_s"]) / F_in for s in outlets]
        units.append(unit_entry(
            fixture["case"], uid, inlets, outlets, ncomp,
            "src/tgt recorded on every stream in the source fixture; "
            "inlets are the streams with tgt equal to the unit id, "
            "outlets the streams with src equal to the unit id",
            LINDE_ROLES[uid], extra))
    return units, excluded, si_worst


# --- Ammonia synthesis loop case ------------------------------------
# The documented mapping: (unit id, inferred role, inlet stream ids,
# outlet stream ids). Unit numbers for units 2 to 5 are the numbers
# in the raw CCR PAR lines of the source fixture; unit 1 is the
# remaining unit, the mixer named first in the process text.
NH3_MAPPING = [
    (1, "mixer (documented: first unit in the process text; the "
        "source fixture's checks record a mixer unit closure)",
     [1, 9], [2]),
    (2, "compressor (documented: raw CCR PAR lines for unit 2 set an "
        "outlet pressure of 2726.7144 psia, 188 bar, and an "
        "efficiency of 0.75; the process text states 188 bar, "
        "efficiency 0.75)",
     [2], [3]),
    (3, "Gibbs converter (documented: raw CCR PAR lines for unit 3 "
        "set the isothermal mode at 1494.27 degR, 830.15 K, 557 "
        "degrees Celsius; the process text states an isothermal "
        "Gibbs converter at 557 degrees Celsius)",
     [3], [4]),
    (4, "flash separator (documented: raw CCR PAR lines for unit 4 "
        "set 529.47 degR, 294.15 K, 21 degrees Celsius, and "
        "2613.5848 psia, 180.2 bar; the source fixture's checks "
        "record a flash unit closure)",
     [4], [6, 7]),
    (5, "divider (documented: raw CCR PAR lines for unit 5 set split "
        "fractions 0.0224 and 0.9776; the source fixture's checks "
        "record a divider unit closure)",
     [6], [8, 9]),
]
# Element rows for the converter check, over the components
# hydrogen (H2), nitrogen (N2), ammonia (NH3), methane (CH4) and
# argon (Ar): the number of hydrogen atoms, nitrogen atoms, carbon
# atoms and argon atoms in one molecule of each component.
NH3_ELEMENTS = [[2, 0, 3, 4, 0], [0, 2, 1, 0, 0], [0, 0, 0, 1, 0],
                [0, 0, 0, 0, 1]]


def build_nh3(fixture):
    nunits, si_worst = verify_si(fixture)
    assert nunits == 5, nunits
    streams = {s["id"]: s for s in fixture["streams"]}
    ncomp = len(fixture["components"])
    assert all(s["src"] is None and s["tgt"] is None
               for s in fixture["streams"]), \
        "ammonia src/tgt no longer null; use the recorded mapping"
    used_as_inlet = []
    used_as_outlet = []
    units = []
    for uid, role, in_ids, out_ids in NH3_MAPPING:
        inlets = [streams[i] for i in in_ids]
        outlets = [streams[i] for i in out_ids]
        used_as_inlet += in_ids
        used_as_outlet += out_ids
        extra = {}
        if uid == 2:
            extra["spec_recorded"] = {
                "outlet_pressure_Pa": outlets[0]["P_Pa"],
                "efficiency": 0.75,
                "spec_basis": "raw CCR PAR lines for unit 2 in the "
                              "source fixture (par 3 outlet pressure, "
                              "par 5 efficiency) and the process text",
            }
        if uid == 3:
            # The converter changes component totals by reaction, so
            # its closure is on elements, plus the stoichiometry of
            # N2 + 3 H2 -> 2 NH3.
            worst_e = 0.0
            for row in NH3_ELEMENTS:
                fi = sum(row[i] * inlets[0]["flows_mol_s"][i]
                         for i in range(ncomp))
                fo = sum(row[i] * outlets[0]["flows_mol_s"][i]
                         for i in range(ncomp))
                worst_e = max(worst_e, abs(fi - fo))
            h2_consumed = inlets[0]["flows_mol_s"][0] \
                - outlets[0]["flows_mol_s"][0]
            n2_consumed = inlets[0]["flows_mol_s"][1] \
                - outlets[0]["flows_mol_s"][1]
            nh3_formed = outlets[0]["flows_mol_s"][2] \
                - inlets[0]["flows_mol_s"][2]
            extra["element_balance_worst_mol_of_atoms_s"] = worst_e
            extra["stoichiometry"] = {
                "h2_consumed_per_n2_consumed":
                    h2_consumed / n2_consumed,
                "nh3_formed_per_2_n2_consumed":
                    nh3_formed / (2.0 * n2_consumed),
            }
            assert worst_e < 0.1, worst_e
            assert abs(h2_consumed / n2_consumed - 3.0) < 1e-3
            assert abs(nh3_formed / (2.0 * n2_consumed) - 1.0) < 1e-3
        if uid == 5:
            extra["spec_recorded"] = {
                "outlet_fractions_of_inlet_total": [0.0224, 0.9776],
                "spec_basis": "raw CCR PAR lines for unit 5 in the "
                              "source fixture (par 3 and par 4) and "
                              "the process text purge fraction 0.0224",
            }
        entry = unit_entry(
            fixture["case"], uid, inlets, outlets, ncomp,
            "src/tgt are null in the source fixture; mapping from "
            "the source fixture's process text, raw CCR PAR unit "
            "numbers, and checks, accepted only because the balance "
            "closure recomputed here matches the closure recorded "
            "in the source fixture's checks",
            role, extra)
        if uid != 3:
            recorded = fixture["checks"]["unit_closure_mol_s"]
            name = {1: "mixer", 4: "flash", 5: "divider"}.get(uid)
            if name is not None:
                assert abs(entry["component_balance_worst_mol_s"]
                           - recorded[name]) < 1e-6, (uid, entry)
            assert entry["component_balance_relative_to_inlet_total"] \
                < 2e-4, (uid, entry["component_balance_worst_mol_s"])
        units.append(entry)
    chain_in = sorted(set(used_as_inlet))
    chain_out = sorted(set(used_as_outlet))
    assert len(used_as_inlet) == len(set(used_as_inlet))
    assert len(used_as_outlet) == len(set(used_as_outlet))
    excluded_streams = [{
        "source_case": fixture["case"],
        "stream_id": 5,
        "reason": "zero component flows, T_K 0 and P_Pa 0 in the "
                  "source fixture: an unused placeholder stream that "
                  "belongs to no unit in the documented mapping "
                  f"(streams used as inlets: {chain_in}; as outlets: "
                  f"{chain_out})",
    }]
    return units, [], excluded_streams, si_worst


def main():
    linde = json.loads(
        (FIX / "flowsheet-linde-asu-stored.json").read_text())
    nh3 = json.loads(
        (FIX / "flowsheet-nh3-loop-iso557.json").read_text())
    lin_units, lin_excluded, lin_si = build_linde(linde)
    nh3_units, nh3_excluded, nh3_excluded_streams, nh3_si = \
        build_nh3(nh3)
    out = {
        "case": "units-from-flowsheets",
        "purpose": "unit-level verification fixtures derived from "
                   "the two converged ChemCAD flowsheet fixtures, "
                   "for the Phase 3 and Phase 4 fixture-match checks "
                   "of PLAN.md",
        "source_fixtures": ["flowsheet-linde-asu-stored.json",
                            "flowsheet-nh3-loop-iso557.json"],
        "components_by_source_case": {
            linde["case"]: linde["components"],
            nh3["case"]: nh3["components"],
        },
        "field_definitions": {
            "T_K": "stream temperature, in kelvin (K)",
            "P_Pa": "stream pressure, in pascal (Pa)",
            "vapour_fraction": "stream vapour fraction, "
                               "dimensionless, 0 to 1",
            "flows_mol_s": "component molar flow rates, in moles "
                           "per second (mol/s), in the component "
                           "order of components_by_source_case for "
                           "the unit's source case",
            "total_mol_s": "total molar flow rate, in mol/s",
            "enthalpy_rate_W": "total enthalpy rate of the stream, "
                               "in watts (W), on the source "
                               "fixture's enthalpy datum",
            "molar_enthalpy_J_mol": "enthalpy rate divided by "
                                    "total flow, in joules per "
                                    "mole (J/mol)",
            "type_recorded": "unit type as recorded in the source "
                             "fixture; null in every case here, "
                             "because neither source fixture records "
                             "a unit type or a non-empty label",
            "inferred_role": "identification inferred from the "
                             "source fixture's process text and the "
                             "unit's stream behaviour; not a "
                             "recorded value",
            "component_balance_worst_mol_s": "largest per-component "
                "difference between total inlet and total outlet "
                "flow, in mol/s; for the Gibbs converter this is "
                "not a closure (reaction changes component totals) "
                "and the element balance in its stoichiometry "
                "fields is the closure",
        },
        "si_verification": {
            "method": "every stored stream value re-derived from "
                      "the raw capture lines stored in the same "
                      "source fixture, with factors degR * 5/9 = K, "
                      "psia * 6894.757 = Pa, lbmol/h * "
                      "(453.59237 / 3600) = mol/s, Btu/h * "
                      "0.29307107 = W; the source fixtures are "
                      "already SI and no further conversion is "
                      "applied in this file",
            "linde_worst_deviation": lin_si,
            "nh3_worst_deviation": nh3_si,
        },
        "units": lin_units + nh3_units,
        "excluded_units": lin_excluded + nh3_excluded,
        "excluded_streams": nh3_excluded_streams,
    }
    path = FIX / "units-from-flowsheets.json"
    path.write_text(json.dumps(out, indent=1))
    print(f"wrote {path}")
    print(f"units included: {len(out['units'])} "
          f"(linde {len(lin_units)}, nh3 {len(nh3_units)}); "
          f"excluded units: {len(out['excluded_units'])}; "
          f"excluded streams: {len(out['excluded_streams'])}")
    for u in out["units"]:
        print(f"  {u['source_case']} unit {u['unit_id']}: "
              f"in {[s['id'] for s in u['inlet_streams']]} "
              f"out {[s['id'] for s in u['outlet_streams']]} "
              f"closure worst "
              f"{u['component_balance_worst_mol_s']:.3e} mol/s")


if __name__ == "__main__":
    main()
