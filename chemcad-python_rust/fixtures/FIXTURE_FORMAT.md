# Fixture format (Phase 1)

One JSON file per captured case, in this directory. All values in SI
units; conversion from ChemCAD internal units happens once, in the
reader that builds the fixture from the capture output, and the raw
capture lines are stored in the fixture under "raw" for audit.

Fields:
- case_id: short unique name, e.g. "flash-alk-pr-tp-340k".
- unit: unit code from INVENTORY.md (e.g. "FLAS"), or "IFLASH" for
  interface-level property captures.
- mixture: component names in sim order.
- thermo: {"k_model": name as in the sim ThermalModes record,
  "enthalpy_model": name, "parameters": {...} -- the full parameter
  set the sim used, read from the sim or its databank record; a case
  whose parameters cannot be read is marked "parameters": null and
  counts as a comparison case, not a replication case}.
- inputs: feed streams (T in K, P in kPa, component flows in mol/s)
  and the unit specification (mode and values, SI).
- outputs: outlet streams in the same SI form, plus unit results
  (duty in W, work in W, temperatures in K) as applicable.
- tolerances: the pass tolerances for this case (defaults from
  PLAN.md: T 0.1 K, compositions 0.002, duty 0.5 percent).
- source: {"sim_file": name on the PC, "captured": ISO date,
  "runner": "ccr_capture.py", "chain": "warm" or "run_job"}.
- raw: the CCR lines exactly as printed.

A fixture is frozen once written; a re-capture writes a new file with
a version suffix, never an overwrite.
