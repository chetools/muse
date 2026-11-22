# ChemCAD Replication — Phase 0 Inventory

Source: unit-name table in CCXToolKit.dll of the installed CHEMCAD NXT
1.2.1.18804, recovered 2026-10-24 (dump at
~/workspace/chemcad-vs-claude/chemcad/table_out.txt). The table is a
contiguous array of 8-byte records starting at DIVI. The itype of a unit
is its 1-based position in the array. Calibration against known units is
exact: DIVI 1, CSEP 2, MIXE 3, FLAS 4, REAC 5, VALV 6, HTXR 7, COMP 17,
LNGH 18, SCDS 21, KREA 25, GIBS 28, EREA 29.

Scope decision (user, 2026-11-21): every group below is to be built,
including solids and batch. Batch and dynamics units are sequenced last
but are build phases of this programme, not inventory-only.

## Unit operations by itype

| itype | code | unit | group |
|---|---|---|---|
| 1 | DIVI | divider / splitter | stream |
| 2 | CSEP | component separator | stream |
| 3 | MIXE | mixer | stream |
| 4 | FLAS | multi-purpose flash (two-phase) | flash |
| 5 | REAC | stoichiometric reactor | reactor |
| 6 | VALV | valve | pressure |
| 7 | HTXR | heat exchanger (simple and rigorous modes) | heat |
| 8 | PUMP | pump | pressure |
| 9 | LLVF | three-phase flash (liquid-liquid-vapour) | flash |
| 10 | PGEN | name expansion to be confirmed from program help | other |
| 11 | FIRE | fired heater | heat |
| 12 | TPLS | name expansion to be confirmed | other |
| 13 | SREF | name expansion to be confirmed | other |
| 14 | SHOR | shortcut distillation column | column |
| 15 | CONT | controller (design specification) | flowsheet |
| 16 | VESL | vessel / flash with vessel options | flash |
| 17 | COMP | compressor | pressure |
| 18 | LNGH | multi-stream (LNG) heat exchanger | heat |
| 19 | EXPN | expander / turbine | pressure |
| 20 | TOWR | rigorous tower column | column |
| 21 | SCDS | rigorous column system (SCDS) | column |
| 22-24 | ADD1-ADD3 | user-added unit slots | extension |
| 25 | KREA | kinetic reactor (CSTR / PFR forms) | reactor |
| 26 | PIPE | pipe (pressure drop) | pressure |
| 27 | EXTR | liquid-liquid extraction column | column |
| 28 | GIBS | Gibbs free-energy reactor | reactor |
| 29 | EREA | equilibrium reactor | reactor |
| 30 | FLTR | filter | solids |
| 31 | CFUG | centrifuge | solids |
| 32 | WASH | solids washer | solids |
| 33 | CYCL | gas cyclone | solids |
| 34 | HCYC | hydrocyclone | solids |
| 35 | VSCR | name expansion to be confirmed | solids |
| 36 | ESPT | electrostatic precipitator (to be confirmed) | solids |
| 37 | SCRE | screen | solids |
| 38 | BAGH | baghouse filter | solids |
| 39 | DRYE | dryer | solids |
| 40 | CRYS | crystalliser | solids |
| 41 | CSED | name expansion to be confirmed | solids |
| 42 | CRSH | crusher / grinder | solids |
| 43-49 | ADD4-ADD9, AD10 | user-added unit slots | extension |
| 50 | BATC | batch column | batch |
| 51 | TANK | tank (dynamic holdup) | dynamics |
| 52 | TSWT | time switch | dynamics |
| 53 | LOOP | recycle loop block | flowsheet |
| 54 | SREC | name expansion to be confirmed | flowsheet |
| 55 | BREA | batch reactor | batch |
| 56 | DVSL | dynamic vessel | dynamics |
| 57 | DLAY | time delay | dynamics |
| 58 | CVAL | control valve (dynamic) | dynamics |
| 59 | PIDC | PID controller | dynamics |
| 60 | CALC | calculator block | flowsheet |
| 61 | RAMP | ramp block | dynamics |
| 62 | PLMR | name expansion to be confirmed | reactor |
| 63 | NODE | node (dynamic junction) | dynamics |
| 64 | META | meta unit (encapsulated flowsheet) | flowsheet |
| 65 | EXCL | Excel unit | extension |
| 66 | CSBR | name expansion to be confirmed | batch |

User-added slots (ADD, AD) and the Excel unit are extension mechanisms,
not calculation units; they are recorded here for completeness and are
out of the build scope. Every other code above is in the build scope.

## Thermodynamic models (from the installed program's help)

K-value models named in the installed help: SRK, API SRK, Peng-Robinson,
BWRS, Grayson-Streed, ESSO, ESD, SAFT, UNIFAC, Wilson, ideal (vapour
pressure), NRTL, UNIQUAC, Margules (4-suffix), T. K. Wilson, Hiranuma,
regular solution, van Laar, modified SRK, predictive SRK, Wilson salt,
Henry's law, amine, sour water, K tables, polynomial user K, TSRK,
PPAQ (electrolyte), TEG, Flory-Huggins (polymers), UNIFAC for polymers,
user-specified activity coefficients, VTPR.
Enthalpy pairings per the same help: equation-of-state models use their
own enthalpy; activity models use latent-heat (LATE) enthalpy; amine
uses AMIN; PPAQ uses SRK or LATE with heat-of-solution terms; VTPR uses
VTPR.

Build order for models: ideal, Peng-Robinson, SRK, BWRS first (gas and
hydrocarbon cases); NRTL, UNIQUAC, Wilson, van Laar, Margules, UNIFAC
second (liquid cases, three test mixtures); Henry's law third;
specialty packages (electrolyte, amine, sour water, SAFT, ESD, polymer,
TEG) each with its own anchored case, last among the models.

## Status

Phase 0 inventory: complete from the recovered table and installed help,
except the marked name expansions, which are confirmed from the program
help as each unit's fixture work begins. No ChemCAD run was needed for
this phase, and none was made: a ChemCAD anchor session from the
distillation-game chat is active on the same computer, and concurrent
COM sessions on one ChemCAD installation are a named interference risk
(orphaned processes and timeouts were already observed there today).
Phase 1 capture work in this programme waits for that session to finish,
or for the user's word to take over the ChemCAD slot.
