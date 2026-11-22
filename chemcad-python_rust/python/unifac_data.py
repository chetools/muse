"""Published original-UNIFAC (VLE) group data set.

Symbols, defined at first use: subgroup k is a structural unit of a
molecule; R_k is the subgroup volume parameter (dimensionless) and
Q_k is the subgroup surface parameter (dimensionless); a main group
m is a set of subgroups treated as identical for interactions;
a_mn is the published interaction parameter in kelvin (K) for main
group m interacting with main group n (a_mn is not equal to a_nm in
general); nu_k^(i) is the number of subgroups k in component i
(dimensionless count); the activity coefficient gamma_i is
dimensionless; temperature T is in kelvin (K).

Sources (every value below was transcribed from a retrieved copy of
one of these, not reconstructed from memory):
1. H. K. Hansen, P. Rasmussen, Aa. Fredenslund, M. Schiller and
   J. Gmehling, "Vapor-liquid equilibria by UNIFAC group
   contribution. 5. Revision and extension", Ind. Eng. Chem. Res.
   30, 2352-2355 (1991) -- the published source of the table.
2. Transcription used for R_k, Q_k and a_mn: "UNIFAC Structural
   Groups and Parameters", AIM, University of East Anglia,
   http://www.aim.env.uea.ac.uk/aim/info/UNIFACgroups.html
   (states Hansen et al. 1991 as its source for the standard set;
   retrieved 2026-11-21). Its Table 1 gives R_k and Q_k by subgroup
   and its Table 2 gives a_mn by main-group number pair.
3. Cross-check of R_k and Q_k and of the a_mn submatrix over main
   groups 1, 3, 4, 5, 7, 9, 13, 15, 19: Smith, Van Ness, Abbott and
   Swihart, Introduction to Chemical Engineering Thermodynamics,
   Appendix G, Tables G.1 and G.2 (which cite Hansen et al. 1991),
   https://wwwcourses.sens.buffalo.edu/ce407/notes/ce407_notes_Smith_etal_2018_Appendix_G.pdf
   (retrieved 2026-11-21). One discrepancy was found and resolved
   in favour of source 3 / Hansen: source 2 prints Q = 1.448 for
   subgroup CH3CO, while source 3 prints Q = 1.488; 1.488 is used.
   The CHn / OH / H2O a_mn block (986.5, 1318, 156.4, 353.5, 300.0,
   -229.1 K) was additionally cross-checked against Marcolli and
   Peter, Atmos. Chem. Phys. 5, 1545-1555 (2005), Table 2, which
   reproduces the Hansen et al. 1991 values.

Scope: main groups 1 (CH2, alkanes), 3 (ACH, aromatics), 4 (ACCH2),
5 (OH), 6 (CH3OH, methanol), 7 (H2O), 9 (CH2CO, ketones), 14
(CNH2, primary amines), 15 (CNH, secondary amines) and 16 (CN,
tertiary amines) -- the groups needed by ethanol/water and by the
other anchored systems of this programme (n-alkanes, aromatics,
methanol, acetone/ketones, amines).

MISSING (not in the retrieved source 2 list for these main-group
pairs; listed here, never guessed, and interaction_matrix raises
if a requested system needs one):
- a_mn for (m, n) = (9, 14) and (14, 9): the CH2CO / CNH2 pair is
  absent from Table 2 of source 2 (the entries jump from
  (13, 14) to (15, 14) in one direction and from (13, 9) to
  (15, 9) in the other).
All other main-group pairs within the scope above are present.
Main groups outside the scope (for example 2, 8, 10-13, 17-56 of
source 2) are MISSING from this module by scope, not transcribed.
"""

# Main group number -> descriptive name (source 2, Table 1).
MAIN_GROUPS = {
    1: "CH2",
    3: "ACH",
    4: "ACCH2",
    5: "OH",
    6: "CH3OH",
    7: "H2O",
    9: "CH2CO",
    14: "CNH2",
    15: "CNH",
    16: "CN",
}

# Subgroup name -> (main group number, R_k, Q_k); R_k and Q_k are
# dimensionless (sources 1-3 above).
SUBGROUPS = {
    # Main group 1, alkanes.
    "CH3": (1, 0.9011, 0.848),
    "CH2": (1, 0.6744, 0.540),
    "CH": (1, 0.4469, 0.228),
    "C": (1, 0.2195, 0.000),
    # Main group 3, aromatic carbon.
    "ACH": (3, 0.5313, 0.400),
    "AC": (3, 0.3652, 0.120),
    # Main group 4, aromatic carbon with an alkane chain.
    "ACCH3": (4, 1.2663, 0.968),
    "ACCH2": (4, 1.0396, 0.660),
    "ACCH": (4, 0.8121, 0.348),
    # Main group 5, alcohol.
    "OH": (5, 1.0000, 1.200),
    # Main group 6, methanol (a main group of its own in UNIFAC).
    "CH3OH": (6, 1.4311, 1.432),
    # Main group 7, water.
    "H2O": (7, 0.9200, 1.400),
    # Main group 9, ketones.
    "CH3CO": (9, 1.6724, 1.488),
    "CH2CO": (9, 1.4457, 1.180),
    # Main group 14, primary amines.
    "CH3NH2": (14, 1.5959, 1.544),
    "CH2NH2": (14, 1.3692, 1.236),
    "CHNH2": (14, 1.1417, 0.924),
    # Main group 15, secondary amines.
    "CH3NH": (15, 1.4337, 1.244),
    "CH2NH": (15, 1.2070, 0.936),
    "CHNH": (15, 0.9795, 0.624),
    # Main group 16, tertiary amines.
    "CH3N": (16, 1.1865, 0.940),
    "CH2N": (16, 0.9597, 0.632),
}

# Interaction parameters a_mn in kelvin (K), keyed by
# (main group m, main group n); diagonal entries are 0. Pairs not
# listed here are MISSING (see the module header).
A_MN = {
    (1, 1): 0.0, (1, 3): 61.13, (1, 4): 76.50, (1, 5): 986.5,
    (1, 6): 697.2, (1, 7): 1318.0, (1, 9): 476.4, (1, 14): 391.5,
    (1, 15): 255.7, (1, 16): 206.60,
    (3, 1): -11.12, (3, 3): 0.0, (3, 4): 167.00, (3, 5): 636.1,
    (3, 6): 637.35, (3, 7): 903.8, (3, 9): 25.77, (3, 14): 161.7,
    (3, 15): 122.8, (3, 16): 90.49,
    (4, 1): -69.70, (4, 3): -146.80, (4, 4): 0.0, (4, 5): 803.2,
    (4, 6): 603.25, (4, 7): 5695.0, (4, 9): -52.10, (4, 14): 19.02,
    (4, 15): -49.29, (4, 16): 23.50,
    (5, 1): 156.4, (5, 3): 89.60, (5, 4): 25.82, (5, 5): 0.0,
    (5, 6): -137.1, (5, 7): 353.5, (5, 9): 84.00, (5, 14): 83.02,
    (5, 15): 42.70, (5, 16): -323.00,
    (6, 1): 16.51, (6, 3): -50.00, (6, 4): -44.50, (6, 5): 249.1,
    (6, 6): 0.0, (6, 7): -181.00, (6, 9): 23.39, (6, 14): 359.3,
    (6, 15): -20.98, (6, 16): 53.90,
    (7, 1): 300.0, (7, 3): 362.3, (7, 4): 377.6, (7, 5): -229.1,
    (7, 6): 289.6, (7, 7): 0.0, (7, 9): -195.4, (7, 14): 48.89,
    (7, 15): 168.00, (7, 16): 304.00,
    (9, 1): 26.76, (9, 3): 140.10, (9, 4): 365.8, (9, 5): 164.5,
    (9, 6): 108.70, (9, 7): 472.5, (9, 9): 0.0,
    (9, 15): -174.20, (9, 16): -169.00,
    (14, 1): -30.48, (14, 3): -44.85, (14, 4): 296.4,
    (14, 5): -242.80, (14, 6): -481.7, (14, 7): -330.48,
    (14, 14): 0.0, (14, 15): -107.20, (14, 16): -41.11,
    (15, 1): 65.33, (15, 3): -22.31, (15, 4): 223.00,
    (15, 5): -150.00, (15, 6): -370.3, (15, 7): -448.20,
    (15, 9): 147.10, (15, 14): 127.40, (15, 15): 0.0,
    (15, 16): -189.20,
    (16, 1): -83.98, (16, 3): -223.90, (16, 4): 109.90,
    (16, 5): 28.60, (16, 6): -406.8, (16, 7): -598.80,
    (16, 9): 225.30, (16, 14): 38.89, (16, 15): 865.90,
    (16, 16): 0.0,
}

# Component decompositions as {subgroup name: count nu_k^(i)} for
# the anchored systems (examples in source 2, Table 1).
COMPONENT_GROUPS = {
    "ethanol": {"CH3": 1, "CH2": 1, "OH": 1},
    "water": {"H2O": 1},
    "methanol": {"CH3OH": 1},
    "acetone": {"CH3CO": 1, "CH3": 1},
    "benzene": {"ACH": 6},
    "toluene": {"ACH": 5, "ACCH3": 1},
    "ethylbenzene": {"ACH": 5, "ACCH2": 1, "CH3": 1},
    "n-pentane": {"CH3": 2, "CH2": 3},
    "n-hexane": {"CH3": 2, "CH2": 4},
    "n-heptane": {"CH3": 2, "CH2": 5},
    "methylamine": {"CH3NH2": 1},
    "ethylamine": {"CH3": 1, "CH2NH2": 1},
    "dimethylamine": {"CH3NH": 1, "CH3": 1},
    "diethylamine": {"CH3": 2, "CH2": 1, "CH2NH": 1},
    "trimethylamine": {"CH3N": 1, "CH3": 2},
    "triethylamine": {"CH3": 3, "CH2": 2, "CH2N": 1},
}


def subgroup_table(subgroup_names):
    """(R, Q, main) lists for subgroup_names, in the given order.

    R and Q are the dimensionless subgroup parameters R_k and Q_k;
    main is the main-group number of each subgroup.
    """
    R, Q, main = [], [], []
    for name in subgroup_names:
        mg, rk, qk = SUBGROUPS[name]
        main.append(mg)
        R.append(rk)
        Q.append(qk)
    return R, Q, main


def interaction_matrix(main_groups):
    """Square a_mn matrix in kelvin (K) over main_groups (numbers).

    Raises ValueError naming every MISSING pair, so a system that
    needs an unsourced interaction is never silently completed.
    """
    missing = [(m, n) for m in main_groups for n in main_groups
               if (m, n) not in A_MN]
    if missing:
        raise ValueError(
            "UNIFAC interaction parameters MISSING for main-group "
            f"pairs {missing}; see unifac_data.py header")
    return [[A_MN[(m, n)] for n in main_groups] for m in main_groups]


def build_case(component_names):
    """(nu, R, Q, a) for gamma_unifac, from COMPONENT_GROUPS.

    nu[i][k] is the count of subgroup k in component i over the
    union of subgroups (first-appearance order); R and Q are the
    dimensionless subgroup parameters; a is the interaction matrix
    in kelvin (K) expanded from main groups to subgroups (all
    subgroups of one main group share its a_mn row and column).
    """
    order = []
    for name in component_names:
        for sg in COMPONENT_GROUPS[name]:
            if sg not in order:
                order.append(sg)
    R, Q, main = subgroup_table(order)
    a_main = interaction_matrix(sorted(set(main)))
    main_sorted = sorted(set(main))
    a = [[a_main[main_sorted.index(main[i])][main_sorted.index(main[j])]
          for j in range(len(order))] for i in range(len(order))]
    nu = [[COMPONENT_GROUPS[name].get(sg, 0) for sg in order]
          for name in component_names]
    return nu, R, Q, a
