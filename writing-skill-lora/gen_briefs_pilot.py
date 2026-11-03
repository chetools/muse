"""Generate 1,000 frozen briefs for the pilot stage of the
writing-skill LoRA dataset (SPEC quotas: STEM 500, business 250,
tutorial 250; kinds passage 700 incl. about 150 equation-bearing,
long 100, fragment 150, identity 50). Splits are assigned by topic:
no topic appears in two splits, balanced to 800/100/100.

Every number in a brief is computed here so the brief is internally
consistent. All quantities are SI. Usage:
    uv run python gen_briefs_pilot.py
Output: briefs-pilot/briefs.jsonl and briefs-pilot/BRIEFS.md.
"""
import hashlib, json, random
from pathlib import Path

from gen_briefs import (t_catalyst, t_membrane, t_absorber, t_kinetics,
                        t_adsorption, t_sensors, t_delivery, t_energy,
                        t_reynolds, t_fick, t_halflife)

OUT = Path(__file__).parent / "briefs-pilot"


def n(x, dp=2):
    s = f"{x:.{dp}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def B(domain, subtype, topic, facts, **kw):
    d = {"domain": domain, "subtype": subtype, "topic": topic,
         "facts": facts}
    d.update(kw)
    return d


def wrap(fn):
    """Adapt a smoke template (domain, subtype, facts) to a brief."""
    def g(r):
        domain, subtype, facts = fn(r)
        return B(domain, subtype, subtype, facts)
    return g


# ---------------- STEM passage templates ----------------

def t_hx(r):
    fluid = r.choice(["crude oil", "cooling water", "propylene glycol"])
    duty = r.randint(400, 2400)
    thi, tho = r.choice([(150, 110), (180, 130), (95, 70)])
    tci = r.choice([25, 30, 35]); tco = tci + r.choice([15, 20, 25])
    import math
    d1, d2 = thi - tco, tho - tci
    lmtd = d1 if d1 == d2 else (d1 - d2) / math.log(d1 / d2)
    area = round(r.uniform(18, 85), 1); u = duty * 1000 / (area * lmtd)
    facts = [
        f"A shell-and-tube exchanger heats {fluid} in a refinery preheat train.",
        f"Duty is {duty} kW. Hot stream: {thi} °C in, {tho} °C out. Cold stream: {tci} °C in, {tco} °C out.",
        f"The log-mean temperature difference is {n(lmtd, 1)} K and the installed area is {n(area, 1)} m2, giving an overall coefficient of {n(u, 0)} W m-2 K-1.",
        "Fouling was assessed from a single 90-day run; no cleaning cycle has been completed.",
    ]
    return B("stem", "results passage: heat exchanger", f"hx:{fluid}", facts)


def t_pump(r):
    fluid = r.choice(["water", "light diesel", "caustic solution"])
    flow = r.randint(20, 120); head = r.randint(18, 65)
    eff = r.randint(62, 84); power = round(flow / 3600 * 1000 * 9.81 * head / (eff / 100) / 1000, 1)
    facts = [
        f"A centrifugal pump moves {fluid} between two vessels at grade.",
        f"At the duty point the flow is {flow} m3 h-1 against a head of {head} m, with pump efficiency {eff}%.",
        f"Shaft power at the duty point is {n(power, 1)} kW. The motor is rated 15% above this value.",
        "Cavitation was not observed in the acceptance test, which ran for 4 h at the duty point only.",
    ]
    return B("stem", "results passage: pump duty", f"pump:{fluid}", facts)


def t_fenske(r):
    pair = r.choice(["benzene/toluene", "propane/propylene", "ethanol/water"])
    alpha = round(r.uniform(1.4, 2.6), 2)
    xd, xw = 0.98, 0.02
    import math
    nmin = math.log((xd / (1 - xd)) * ((1 - xw) / xw)) / math.log(alpha)
    facts = [
        f"A binary distillation separates {pair} at a relative volatility of {n(alpha)} that is taken as constant over the column.",
        f"Specifications: distillate {n(xd * 100, 0)} mol% light component, bottoms {n(xw * 100, 0)} mol% light component.",
        f"The Fenske minimum stage count is {n(nmin, 1)} theoretical stages including the reboiler.",
        "The actual design uses a reflux ratio of 1.3 times the minimum; the stage count at that reflux comes from a separate simulation.",
    ]
    return B("stem", "results passage: Fenske minimum stages", f"fenske:{pair}", facts)


def t_conduction(r):
    mat = r.choice(["carbon steel", "stainless steel", "firebrick"])
    k = {"carbon steel": 45, "stainless steel": 16, "firebrick": 1.1}[mat]
    thick = r.choice([0.012, 0.02, 0.15]); dt = r.randint(80, 420)
    q = k * dt / thick
    facts = [
        f"A flat {mat} wall of thickness {n(thick * 1000, 0)} mm separates two process streams.",
        f"Thermal conductivity of the wall is {k} W m-1 K-1 and the measured temperature difference across it is {dt} K.",
        f"Steady one-dimensional conduction gives a heat flux of {n(q, 0)} W m-2.",
        "Surface (film) resistances are excluded from this estimate; including them lowers the flux.",
    ]
    return B("stem", "worked example: wall conduction", f"conduction:{mat}", facts)


def t_cstr(r):
    sub = r.choice(["an esterification", "a hydrolysis", "a neutralisation"])
    k = round(r.uniform(0.02, 0.3), 3); tau = r.randint(10, 90)
    x = k * tau / (1 + k * tau)
    facts = [
        f"A continuous stirred-tank reactor runs {sub} that is first order in the limiting reactant.",
        f"The rate constant is {n(k, 3)} min-1 at the operating temperature and the mean residence time is {tau} min.",
        f"Steady-state conversion for an ideal CSTR is {n(x * 100, 1)}%.",
        "The estimate assumes perfect mixing and constant density; tracer tests on the actual vessel have not been run.",
    ]
    return B("stem", "worked example: CSTR conversion", f"cstr:{sub}", facts)


def t_compressor(r):
    gas = r.choice(["air", "nitrogen", "natural gas"])
    p1, p2 = r.choice([(1, 4), (1, 6), (2, 9)])
    t1 = r.choice([293, 303, 313]); gam = 1.4
    t2 = t1 * (p2 / p1) ** ((gam - 1) / gam)
    facts = [
        f"A single-stage compressor raises {gas} from {p1} bar to {p2} bar.",
        f"Inlet temperature is {t1} K. For isentropic compression with a heat-capacity ratio of {gam}, the discharge temperature is {n(t2, 0)} K.",
        "The isentropic estimate excludes mechanical losses; the installed machine's measured discharge temperature is higher.",
    ]
    return B("stem", "worked example: compressor discharge", f"compressor:{gas}", facts)


def t_cooling(r):
    tower = r.choice(["a mechanical-draft tower", "a natural-draft tower"])
    twb = r.randint(18, 27); appr = r.randint(3, 7); rng_ = r.randint(5, 11)
    facts = [
        f"Performance of {tower} at a chemical site was logged over one summer month.",
        f"Mean wet-bulb temperature was {twb} °C, the approach was {appr} K and the range was {rng_} K.",
        "Performance outside the logged month, in particular at winter wet-bulb temperatures, was not measured.",
    ]
    return B("stem", "results passage: cooling tower", f"cooling:{tower}", facts)


def t_fridge(r):
    duty = r.choice(["a cold store", "a process chiller", "an ice rink"])
    te, tc = r.choice([(-25, 35), (-10, 40), (0, 45)])
    cop_c = (te + 273) / (tc - te)
    cop = round(cop_c * r.uniform(0.35, 0.5), 2)
    facts = [
        f"A vapour-compression unit serves {duty}, evaporating at {te} °C and condensing at {tc} °C.",
        f"The Carnot coefficient of performance between these temperatures is {n(cop_c, 2)}; the installed unit achieves {n(cop)}.",
        "The achieved value is from the manufacturer's test at full load; part-load performance is not stated.",
    ]
    return B("stem", "worked example: refrigeration COP", f"fridge:{duty}", facts)


def t_settling_design(r):
    solid = r.choice(["calcium carbonate", "activated sludge", "sand"])
    rate = round(r.uniform(0.4, 2.2), 2); flow = r.randint(50, 400)
    area = flow / rate
    facts = [
        f"A gravity settler removes {solid} from a process stream.",
        f"Design overflow rate is {n(rate)} m h-1 at a throughput of {flow} m3 h-1, giving a plan area of {n(area, 0)} m2.",
        "The overflow-rate basis is a vendor rule for this solid; no settling test on the actual slurry has been run.",
    ]
    return B("stem", "results passage: settler sizing", f"settler:{solid}", facts)


def t_extraction(r):
    solute = r.choice(["acetic acid", "phenol", "acetone"])
    dcoef = round(r.uniform(0.4, 2.8), 2); stages = r.randint(3, 8)
    rec = r.randint(88, 99)
    facts = [
        f"Liquid-liquid extraction recovers {solute} from an aqueous stream into an organic solvent.",
        f"The distribution coefficient (organic over aqueous) is {n(dcoef)} at 25 °C and the design uses {stages} countercurrent stages.",
        f"Predicted recovery is {rec}% of the {solute} in the feed.",
        "The prediction assumes equilibrium stages and negligible mutual solubility; neither has been checked on the actual solvents.",
    ]
    return B("stem", "results passage: extraction recovery", f"extraction:{solute}", facts)


# ---------------- Equation-bearing STEM templates ----------------
# Each brief carries `equations`: LaTeX spans (with delimiters) that
# both passages must reproduce byte-identically. Symbols in the prose
# are written as inline math spans, never spelled-out names.

def t_eq_bernoulli(r):
    rho, v, d = 998, round(r.uniform(0.6, 2.4), 1), r.choice([0.05, 0.08, 0.1])
    f_, l = 0.02, r.randint(20, 120)
    dp = f_ * (l / d) * rho * v * v / 2 / 1000
    facts = [
        "Water at 293 K flows in a horizontal pipe. The density $\\rho$ is 998 kg m-3.",
        f"Mean velocity $v$ is {n(v)} m s-1, pipe diameter $D$ is {n(d)} m, pipe length $L$ is {l} m and the Darcy friction factor $f$ is 0.02.",
        f"The friction pressure drop is {n(dp, 1)} kPa.",
    ]
    eqs = ["$$\\Delta P = f \\frac{L}{D} \\frac{\\rho v^2}{2}$$"]
    return B("stem", "worked example with equation: friction loss",
             "eq:bernoulli", facts, equations=eqs)


def t_eq_fourier(r):
    mat = r.choice(["carbon steel", "stainless steel", "firebrick"])
    k = {"carbon steel": 45, "stainless steel": 16, "firebrick": 1.1}[mat]
    thick = r.choice([0.012, 0.02, 0.15]); dt = r.randint(80, 420)
    q = k * dt / thick
    facts = [
        f"A flat {mat} wall has thickness {n(thick * 1000, 0)} mm and thermal conductivity $k$ of {k} W m-1 K-1.",
        f"The temperature difference $\\Delta T$ across the wall is {dt} K, giving a heat flux $q$ of {n(q, 0)} W m-2.",
        "The calculation is steady and one-dimensional; film resistances are excluded.",
    ]
    eqs = ["$$q = k \\frac{\\Delta T}{\\Delta x}$$"]
    return B("stem", "worked example with equation: Fourier conduction",
             f"eq:fourier:{mat}", facts, equations=eqs)


def t_eq_arrhenius(r):
    a = r.choice(["a catalyst ageing test", "a polymer cure", "a food spoilage study"])
    ea = r.randint(40, 120); t1, t2 = 300, 300 + r.choice([20, 30, 40])
    import math
    ratio = math.exp(-ea * 1000 / 8.314 * (1 / t2 - 1 / t1))
    facts = [
        f"Rate constants for {a} were measured at two temperatures.",
        f"With activation energy $E_a$ of {ea} kJ mol-1, raising the temperature from {t1} K to {t2} K multiplies the rate constant $k$ by {n(ratio, 2)}.",
        "The estimate holds the pre-exponential factor $A$ constant over the interval.",
    ]
    eqs = ["$$k = A \\exp\\left(-\\frac{E_a}{R T}\\right)$$"]
    return B("stem", "worked example with equation: Arrhenius ratio",
             f"eq:arrhenius:{a}", facts, equations=eqs)


def t_eq_ergun(r):
    dp_bed = r.choice([0.4, 0.5, 0.6]); mu = 1.8e-5
    v0 = round(r.uniform(0.1, 0.5), 2); rho = 1.2; length = r.randint(1, 4)
    import math
    term = (150 * mu * (1 - dp_bed) ** 2 / (dp_bed ** 3 * 0.001 ** 2) * v0
            + 1.75 * (1 - dp_bed) / (dp_bed ** 3 * 0.001) * rho * v0 ** 2)
    facts = [
        "Gas flows through a packed bed of 1 mm particles. The void fraction $\\varepsilon$ "
        f"is {n(dp_bed)}, the superficial velocity $u$ is {n(v0)} m s-1 and the bed length is {length} m.",
        f"The Ergun equation gives a pressure gradient of {n(term / 1000, 1)} kPa m-1, "
        f"or {n(term * length / 1000, 1)} kPa over the bed.",
        "Particle diameter $d_p$ is 1 mm; gas density is 1.2 kg m-3 and viscosity is 1.8 x 10-5 Pa s.",
    ]
    eqs = ["$$\\frac{\\Delta P}{L} = \\frac{150 \\mu (1-\\varepsilon)^2}{\\varepsilon^3 d_p^2} u "
           "+ \\frac{1.75 (1-\\varepsilon)}{\\varepsilon^3 d_p} \\rho u^2$$"]
    return B("stem", "worked example with equation: Ergun pressure drop",
             "eq:ergun", facts, equations=eqs)


def t_eq_poiseuille(r):
    mu = r.choice([0.001, 0.05, 0.3]); length = r.randint(5, 40)
    rad = r.choice([0.004, 0.006, 0.01]); dp = r.randint(2, 30) * 1000
    import math
    q = math.pi * rad ** 4 * dp / (8 * mu * length) * 3.6e6
    facts = [
        f"A viscous liquid of viscosity $\\mu$ = {n(mu, 3)} Pa s flows laminarly through a tube of radius $R$ = {n(rad * 1000, 0)} mm and length $L$ = {length} m.",
        f"At a pressure drop $\\Delta P$ of {n(dp / 1000, 0)} kPa the volumetric flow $Q$ is {n(q, 1)} L h-1.",
        "The Hagen-Poiseuille equation assumes laminar, fully developed flow of a Newtonian liquid.",
    ]
    eqs = ["$$Q = \\frac{\\pi R^4 \\Delta P}{8 \\mu L}$$"]
    return B("stem", "worked example with equation: Hagen-Poiseuille",
             "eq:poiseuille", facts, equations=eqs)


def t_eq_stokes(r):
    solid = r.choice(["glass beads", "sand grains", "catalyst fines"])
    dp_um = r.choice([50, 100, 200]); rhos = r.choice([2500, 2650, 1400])
    import math
    vt = 9.81 * (dp_um * 1e-6) ** 2 * (rhos - 998) / (18 * 0.001) * 1000
    facts = [
        f"{solid.capitalize()} of diameter $d_p$ = {dp_um} micrometres and density {rhos} kg m-3 settle in water at 293 K.",
        f"Stokes' law gives a terminal velocity $v_t$ of {n(vt, 2)} mm s-1.",
        "The estimate requires creeping flow; the particle Reynolds number must be checked before the value is used.",
    ]
    eqs = ["$$v_t = \\frac{g d_p^2 (\\rho_p - \\rho)}{18 \\mu}$$"]
    return B("stem", "worked example with equation: Stokes settling",
             f"eq:stokes:{solid}", facts, equations=eqs)


def t_eq_lmtd(r):
    thi, tho = r.choice([(160, 120), (200, 150), (120, 85)])
    tci = r.choice([30, 40]); tco = tci + r.choice([25, 35])
    import math
    d1, d2 = thi - tco, tho - tci
    lmtd = d1 if d1 == d2 else (d1 - d2) / math.log(d1 / d2)
    facts = [
        f"A countercurrent exchanger cools a process stream from {thi} °C to {tho} °C with water entering at {tci} °C and leaving at {tco} °C.",
        f"The terminal differences are {d1} K and {d2} K, and the log-mean temperature difference $\\Delta T_{{lm}}$ is {n(lmtd, 1)} K.",
        "The log-mean value assumes constant overall coefficient and no phase change.",
    ]
    eqs = ["$$\\Delta T_{lm} = \\frac{\\Delta T_1 - \\Delta T_2}{\\ln(\\Delta T_1 / \\Delta T_2)}$$"]
    return B("stem", "worked example with equation: log-mean difference",
             "eq:lmtd", facts, equations=eqs)


def t_eq_antoine(r):
    sub = r.choice(["ethanol", "benzene", "acetone"])
    consts = {"ethanol": (8.20417, 1642.89, 230.3), "benzene": (6.90565, 1211.033, 220.79),
              "acetone": (7.11714, 1210.595, 229.664)}[sub]
    a, b, c = consts; temp = r.choice([40, 60, 78])
    import math
    p = 10 ** (a - b / (temp + c)) * 0.133322
    facts = [
        f"The vapour pressure of {sub} at {temp} °C is estimated from the Antoine equation with constants $A$ = {a}, $B$ = {b} and $C$ = {c} (pressure in mmHg, temperature in °C).",
        f"The estimate is {n(p, 1)} kPa.",
        "The constants are valid only over their fitted temperature range; the source databank value governs design.",
    ]
    eqs = ["$$\\log_{10} P = A - \\frac{B}{T + C}$$"]
    return B("stem", "worked example with equation: Antoine vapour pressure",
             f"eq:antoine:{sub}", facts, equations=eqs)


def t_eq_firstorder(r):
    sub = r.choice(["a drug in solution", "a dye in effluent", "a peroxide initiator"])
    k = round(r.uniform(0.01, 0.2), 3); t = r.randint(10, 120)
    import math
    frac = math.exp(-k * t)
    facts = [
        f"{sub.capitalize()} decomposes by first-order kinetics with rate constant $k$ = {n(k, 3)} min-1.",
        f"After {t} min the fraction remaining $C / C_0$ is {n(frac, 3)}.",
        "The rate constant was measured at one temperature; no activation energy is available.",
    ]
    eqs = ["$$\\ln\\frac{C}{C_0} = -k t$$"]
    return B("stem", "worked example with equation: first-order decay",
             f"eq:firstorder:{sub}", facts, equations=eqs)


def t_eq_radiation(r):
    surf = r.choice(["an oxidised steel panel", "a furnace wall", "a blackened plate"])
    eps = r.choice([0.85, 0.9, 0.95]); th, tc = r.choice([(800, 300), (1000, 350), (600, 290)])
    q = eps * 5.67e-8 * (th ** 4 - tc ** 4) / 1000
    facts = [
        f"{surf.capitalize()} at {th} K faces surroundings at {tc} K. Its emissivity $\\varepsilon$ is {n(eps)}.",
        f"Net radiative heat flux $q$ is {n(q, 1)} kW m-2, with the Stefan-Boltzmann constant $\\sigma$ = 5.67 x 10-8 W m-2 K-4.",
        "The estimate treats both surfaces as large and parallel; view factors for the real geometry are not included.",
    ]
    eqs = ["$$q = \\varepsilon \\sigma (T_1^4 - T_2^4)$$"]
    return B("stem", "worked example with equation: radiative exchange",
             f"eq:radiation:{surf}", facts, equations=eqs)


def t_eq_npsh(r):
    fluid = r.choice(["water", "condensate", "light oil"])
    patm = 101.3; pv = r.choice([2.3, 7.4, 19.9]); lift = round(r.uniform(1, 4), 1)
    loss = round(r.uniform(0.3, 1.2), 1)
    npsh = (patm - pv) / 9.79 - lift - loss
    facts = [
        f"A pump draws {fluid} from an open tank at atmospheric pressure, 101.3 kPa.",
        f"Vapour pressure at the pumping temperature is {n(pv, 1)} kPa, the static lift is {n(lift, 1)} m and suction-line friction loss is {n(loss, 1)} m.",
        f"Available net positive suction head $NPSH_a$ is {n(npsh, 1)} m.",
        "The pump's required NPSH at the duty flow comes from the vendor curve and must be exceeded with margin.",
    ]
    eqs = ["$$NPSH_a = \\frac{P_{atm} - P_v}{\\rho g} - h_{lift} - h_f$$"]
    return B("stem", "worked example with equation: available NPSH",
             f"eq:npsh:{fluid}", facts, equations=eqs)


def t_eq_raoult(r):
    sub = r.choice(["benzene in toluene", "ethanol in water (idealised)", "hexane in heptane"])
    x = round(r.uniform(0.2, 0.7), 2); psat = r.choice([12.7, 5.9, 20.1])
    p = x * psat
    facts = [
        f"An ideal liquid mixture holds {sub} at a liquid mole fraction $x$ of {n(x)} for the volatile component.",
        f"Its pure-component vapour pressure $P^*$ at the mixture temperature is {n(psat, 1)} kPa, so the partial pressure $p$ is {n(p, 1)} kPa by Raoult's law.",
        "Raoult's law assumes an ideal solution; activity coefficients for the real mixture are not applied.",
    ]
    eqs = ["$$p = x P^*$$"]
    return B("stem", "worked example with equation: Raoult partial pressure",
             f"eq:raoult:{sub}", facts, equations=eqs)


# ---------------- Business passage templates ----------------

def t_npv(r):
    proj = r.choice(["a bottling line", "a warehouse extension", "a solar array"])
    capex = r.randint(180, 2400); save = round(capex * r.uniform(0.14, 0.3))
    life = r.choice([8, 10, 12]); rate = r.choice([6, 8, 10])
    pv = sum(save / (1 + rate / 100) ** t for t in range(1, life + 1))
    facts = [
        f"Capital appraisal for {proj}: installed cost ${capex}k, expected net saving ${save}k per year for {life} years.",
        f"At a discount rate of {rate}% the present value of the savings is ${n(pv, 0)}k and the net present value is ${n(pv - capex, 0)}k.",
        "Savings are vendor and utility estimates; no saving has yet been measured on a comparable installation.",
    ]
    return B("business", "capital appraisal: NPV", f"npv:{proj}", facts)


def t_pricing(r):
    prod = r.choice(["a contract cleaning service", "a SaaS tier", "a catering contract"])
    price = r.randint(40, 400); vol = r.randint(800, 9000)
    var = round(price * r.uniform(0.45, 0.7)); fixed = r.randint(60, 500) * 1000
    be = fixed / (price - var)
    facts = [
        f"Pricing case for {prod}: price ${price} per unit, variable cost ${var} per unit, fixed costs ${n(fixed / 1000, 0)}k per year.",
        f"Break-even volume is {n(be, 0)} units per year; current volume is {vol} units per year.",
        "Volume figures are last year's actuals; the effect of the price on volume is not estimated.",
    ]
    return B("business", "pricing case: break-even", f"pricing:{prod}", facts)


def t_inventory(r):
    item = r.choice(["a packaging film", "a resin grade", "a spare motor"])
    dem = r.randint(200, 4000); lead = r.randint(2, 9); sd = round(dem * r.uniform(0.1, 0.3))
    import math
    ss = round(1.65 * sd * math.sqrt(lead))
    facts = [
        f"Inventory policy for {item}: mean demand {dem} units per week, standard deviation {sd} units per week, replenishment lead time {lead} weeks.",
        f"Safety stock for a 95% cycle service level is {ss} units.",
        "Demand is treated as normal and independent between weeks; seasonal peaks are excluded.",
    ]
    return B("business", "inventory case: safety stock", f"inventory:{item}", facts)


def t_quality(r):
    line = r.choice(["a filling line", "a moulding cell", "a packing line"])
    before = round(r.uniform(2.5, 6), 1); after = round(before * r.uniform(0.4, 0.7), 1)
    units = r.randint(50, 400) * 1000
    facts = [
        f"A defect-reduction project on {line} cut the reject rate from {n(before, 1)}% to {n(after, 1)}% over one quarter.",
        f"At {n(units / 1000, 0)}k units per year the change avoids about {n(units * (before - after) / 100, 0)} rejected units per year.",
        "The quarter included a planned shutdown; rates are not adjusted for it.",
    ]
    return B("business", "operations case: defect reduction", f"quality:{line}", facts)


def t_logistics(r):
    route = r.choice(["a regional delivery route", "a cross-dock transfer", "a returns flow"])
    km = r.randint(120, 900); cost = round(r.uniform(0.9, 2.1), 2)
    trips = r.randint(200, 900)
    facts = [
        f"Cost review of {route}: {km} km per trip at ${n(cost)} per km, {trips} trips per year.",
        f"Annual transport cost is ${n(km * cost * trips / 1000, 0)}k.",
        "Costs are carrier invoices for the last 12 months; empty running is included in the trip count.",
    ]
    return B("business", "operations case: transport cost", f"logistics:{route}", facts)


def t_staffing(r):
    dept = r.choice(["a maintenance crew", "a quality laboratory", "a dispatch office"])
    fte = r.randint(4, 18); over = r.randint(6, 22)
    cost = r.randint(55, 95)
    facts = [
        f"Staffing review for {dept}: {fte} full-time staff, overtime at {over}% of paid hours last year.",
        f"Replacing half the overtime with one additional hire costs ${cost}k per year fully loaded.",
        "Overtime is concentrated in two seasonal peaks; a hire is paid for the full year.",
    ]
    return B("business", "staffing case: overtime", f"staffing:{dept}", facts)


# ---------------- Tutorial passage templates ----------------

def t_tut_dimensionless(r):
    group = r.choice(["the Nusselt number", "the Prandtl number", "the Sherwood number"])
    defs = {"the Nusselt number": "the ratio of convective to conductive heat transfer at a surface",
            "the Prandtl number": "the ratio of momentum diffusivity to thermal diffusivity",
            "the Sherwood number": "the ratio of convective to diffusive mass transfer at a surface"}
    facts = [
        f"A tutorial passage explains {group} to second-year students.",
        f"Definition in words: {group} is {defs[group]}.",
        "The passage must state what a value near 1 means and what a large value means, without inventing numerical examples.",
    ]
    return B("tutorial", "explainer: dimensionless group", f"tut:{group}", facts)


def t_tut_control(r):
    loop = r.choice(["a level loop", "a temperature loop", "a flow loop"])
    facts = [
        f"A tutorial passage explains feedback control through {loop} on a process vessel.",
        "The passage covers the sensor, the controller, the final element and the sign of the feedback, in that order.",
        "No tuning numbers are given; the passage explains structure, not settings.",
    ]
    return B("tutorial", "explainer: feedback control", f"tut:control:{loop}", facts)


def t_tut_phase(r):
    sys_ = r.choice(["a pure component at its boiling point", "a binary mixture at fixed pressure",
                     "a partially miscible liquid pair"])
    facts = [
        f"A tutorial passage explains phase equilibrium for {sys_}.",
        "The passage states the equilibrium condition in words (equality of chemical potential across phases) before any equation is named.",
        "No numerical data are introduced; the passage is conceptual.",
    ]
    return B("tutorial", "explainer: phase equilibrium", f"tut:phase:{sys_}", facts)


def t_tut_error(r):
    meas = r.choice(["a flow measurement", "a temperature measurement", "a pressure measurement"])
    val = r.randint(50, 400); tol = r.choice([0.5, 1, 2])
    facts = [
        f"A tutorial passage explains absolute and relative error through {meas}.",
        f"Worked figures: reading {val} units, tolerance {n(tol)}% of reading, so the absolute error is {n(val * tol / 100)} units.",
        "The passage distinguishes error from uncertainty and does not merge the two terms.",
    ]
    return B("tutorial", "explainer: measurement error", f"tut:error:{meas}", facts)


def t_tut_affinity(r):
    facts = [
        "A tutorial passage explains the pump affinity laws for a centrifugal pump at varying speed.",
        "The passage states the three proportionalities in words: flow with speed, head with speed squared, power with speed cubed.",
        "A worked check is included: doubling speed multiplies power by 8. No other numbers are introduced.",
    ]
    return B("tutorial", "explainer: affinity laws", "tut:affinity", facts)


def t_tut_sampling(r):
    stream = r.choice(["an effluent stream", "a powder blend", "a gas emission"])
    facts = [
        f"A tutorial passage explains representative sampling of {stream}.",
        "The passage covers where samples are taken, how many increments form one sample, and why a single grab sample misleads.",
        "No numerical limits are quoted; regulatory limits belong to the site's permit, not to the passage.",
    ]
    return B("tutorial", "explainer: sampling", f"tut:sampling:{stream}", facts)


# ---------------- Long-document templates ----------------

def t_long_assessment(r):
    site = r.choice(["a dairy plant", "a brewery", "a paper mill"])
    elec = r.randint(900, 4200); pct = r.randint(8, 22)
    save = elec * pct / 100; capex = r.randint(150, 900)
    facts = [
        f"Energy assessment of {site}, in four sections: current use, refrigeration, steam, and recommendation.",
        f"Electricity use is {elec} MWh per year; refrigeration takes the largest share.",
        f"A heat-recovery retrofit is projected to save {pct}% of electricity use, a derived saving of {n(save, 0)} MWh per year, at a capital cost of ${capex}k.",
        f"At $0.12 per kWh the derived annual saving is ${n(save * 120, 0)} and the derived simple payback is {n(capex * 1000 / (save * 120), 1)} years.",
        "Steam figures are from one winter month and are flagged as seasonal in the recommendation.",
    ]
    return B("business", "long document: energy assessment", f"long:assess:{site}",
             facts, sections=["Current use", "Refrigeration", "Steam", "Recommendation"])


def t_long_design(r):
    unit = r.choice(["an amine absorber", "a distillation column", "a spray dryer"])
    cap = r.randint(5, 60); eff = r.randint(88, 99)
    facts = [
        f"Design report for {unit}, in four sections: basis, sizing, materials, and risks.",
        f"Design throughput is {cap} t per day and the removal or separation duty is {eff}% of the key component.",
        "Materials are 316L stainless steel for wetted parts; the basis section states this once.",
        "The risks section names fouling and turndown as open items; neither is resolved in the report.",
    ]
    return B("stem", "long document: design report", f"long:design:{unit}",
             facts, sections=["Basis", "Sizing", "Materials", "Risks"])


def t_long_chapter(r):
    topic = r.choice(["distillation", "heat exchangers", "process control"])
    facts = [
        f"A textbook chapter section on {topic}, in four parts: principle, equipment, a worked example, and limits.",
        "The worked example uses only the numbers given in the principle part; no new data appear later in the chapter.",
        "The limits part states where the simple model fails, in plain terms, without new equations.",
    ]
    return B("tutorial", "long document: textbook chapter", f"long:chapter:{topic}",
             facts, sections=["Principle", "Equipment", "Worked example", "Limits"])


def t_long_proposal(r):
    proj = r.choice(["a rooftop solar installation", "a fleet electrification", "a water recycling plant"])
    capex = r.randint(300, 3000); yrs = r.choice([7, 10, 15])
    facts = [
        f"Project proposal for {proj}, in four sections: case, costs, schedule, and decision requested.",
        f"Capital cost is ${capex}k with a {yrs}-year appraisal horizon.",
        "The schedule section gives a start one quarter after approval; no contractor is named.",
        "The decision requested is approval to proceed to detailed design, not to construction.",
    ]
    return B("business", "long document: project proposal", f"long:proposal:{proj}",
             facts, sections=["Case", "Costs", "Schedule", "Decision requested"])


def t_long_review(r):
    field = r.choice(["membrane separations for solvent recovery",
                      "catalysts for carbon dioxide hydrogenation",
                      "adsorbents for gas drying"])
    yrs = r.randint(6, 14); papers = r.randint(40, 160)
    facts = [
        f"A review passage on {field}, in four parts: scope, established results, disagreements, and gaps.",
        f"The review covers {papers} papers from the last {yrs} years.",
        "The disagreements part names the quantity on which reports conflict; the gaps part names the measurement nobody reports.",
    ]
    return B("stem", "long document: literature review", f"long:review:{field}",
             facts, sections=["Scope", "Established results", "Disagreements", "Gaps"])


def t_long_manual(r):
    equip = r.choice(["a centrifugal pump", "a plate heat exchanger", "a pressure relief valve"])
    facts = [
        f"An operating-manual chapter for {equip}, in four sections: start-up, normal operation, alarms, and shutdown.",
        "The alarms section lists two alarms and the operator action for each; no other alarms are introduced.",
        "The chapter addresses the operator directly and uses imperative verbs for actions.",
    ]
    return B("tutorial", "long document: operating manual", f"long:manual:{equip}",
             facts, sections=["Start-up", "Normal operation", "Alarms", "Shutdown"])


# ---------------- Fragment templates ----------------

def _packet(title, defined, names, position):
    return {"title": title, "defined": defined, "fixed_names": names,
            "position": position}


def t_frag_design(r):
    unit = r.choice(["absorber", "reboiler", "compressor"])
    val = r.randint(12, 90)
    facts = [
        f"Excerpt content: the {unit} wall thickness is {val} mm after the corrosion allowance is added.",
        "The excerpt compares two gasket materials on temperature limit only and prefers the higher-rated one.",
        "The excerpt ends mid-argument; it neither summarises the report nor previews the next section.",
    ]
    pkt = _packet("Design report: gas treatment unit",
                  ["$\\Delta P$ (pressure drop)", "NPSH (net positive suction head)"],
                  ["the absorber", "the lean solvent pump"],
                  "Section 3 of 5, middle")
    return B("stem", "fragment: design report", f"frag:design:{unit}", facts,
             context_packet=pkt)


def t_frag_chapter(r):
    topic = r.choice(["mass transfer", "momentum transfer", "heat transfer"])
    facts = [
        "Excerpt content: the analogy between the transfer processes is stated, then qualified by the case where it fails.",
        "The excerpt works one short numerical check with numbers given inside the excerpt itself.",
        "The excerpt assumes the chapter's earlier definitions and adds none.",
    ]
    pkt = _packet(f"Chapter: {topic} fundamentals",
                  ["$j_D$ (mass-transfer factor)", "$f$ (friction factor)"],
                  ["the Chilton-Colburn analogy"],
                  "Chapter middle, after the definitions section")
    return B("tutorial", "fragment: textbook chapter", f"frag:chapter:{topic}",
             facts, context_packet=pkt)


def t_frag_proposal(r):
    item = r.choice(["the contingency allowance", "the schedule float", "the staffing ramp"])
    pct = r.randint(5, 20)
    facts = [
        f"Excerpt content: {item} is set at {pct}% and the excerpt defends that figure against a lower alternative.",
        "The excerpt refers to the project's cost table by section name and does not repeat its figures.",
    ]
    pkt = _packet("Proposal: plant upgrade",
                  ["FID (final investment decision)"],
                  ["the upgrade project", "the steering group"],
                  "Costs section, middle")
    return B("business", "fragment: project proposal", f"frag:proposal:{item}",
             facts, context_packet=pkt)


def t_frag_manual(r):
    step = r.choice(["a seal replacement", "a strainer cleaning", "a calibration check"])
    mins = r.randint(20, 90)
    facts = [
        f"Excerpt content: {step} takes about {mins} min with the unit isolated; the excerpt gives the isolation steps only.",
        "The excerpt warns once about stored pressure and does not repeat the warning.",
    ]
    pkt = _packet("Operating manual: utilities area",
                  ["PTW (permit to work)"],
                  ["the duty pump", "the standby pump"],
                  "Maintenance procedures, middle")
    return B("tutorial", "fragment: operating manual", f"frag:manual:{step}",
             facts, context_packet=pkt)


def t_frag_review(r):
    qty = r.choice(["selectivity", "lifetime", "pressure drop"])
    facts = [
        f"Excerpt content: two groups report conflicting {qty} values for the same material class; the excerpt weighs their test conditions.",
        "The excerpt reaches a limited preference and states the condition on which it rests.",
    ]
    pkt = _packet("Review: porous materials for gas separation",
                  ["IAST (ideal adsorbed solution theory)"],
                  ["the benchmark material"],
                  "Disagreements section, middle")
    return B("stem", "fragment: literature review", f"frag:review:{qty}",
             facts, context_packet=pkt)


def t_frag_memo(r):
    topic = r.choice(["a supplier delay", "a budget overrun", "a staffing gap"])
    wks = r.randint(2, 8)
    facts = [
        f"Excerpt content: {topic} of {wks} weeks is reported with its cause; the excerpt proposes one mitigation and its owner.",
        "The excerpt does not open or close the memo and does not restate its subject line.",
    ]
    pkt = _packet("Memo: project status",
                  ["EPC (engineering, procurement and construction)"],
                  ["the project board"],
                  "Middle of the memo body")
    return B("business", "fragment: status memo", f"frag:memo:{topic}",
             facts, context_packet=pkt)


# ---------------- Driver ----------------

LOADS = {"stem": ["core", "ai-check"],
         "business": ["core", "business", "ai-check"],
         "tutorial": ["core", "textbook", "ai-check"]}
WORDS = {"passage": {"stem": [240, 280, 320], "business": [220, 260, 300],
                     "tutorial": [240, 280, 320]},
         "long": [900, 1100, 1300], "fragment": [200, 260, 320],
         "identity": [220, 280]}

STEM_PASSAGE = [wrap(t_catalyst), wrap(t_membrane), wrap(t_absorber),
                wrap(t_kinetics), wrap(t_adsorption), t_hx, t_pump,
                t_fenske, t_conduction, t_cstr, t_compressor, t_cooling,
                t_fridge, t_settling_design, t_extraction]
EQ_POOL = [t_eq_bernoulli, t_eq_fourier, t_eq_arrhenius, t_eq_ergun,
           t_eq_poiseuille, t_eq_stokes, t_eq_lmtd, t_eq_antoine,
           t_eq_firstorder, t_eq_radiation, t_eq_npsh, t_eq_raoult]
BIZ_PASSAGE = [wrap(t_sensors), wrap(t_delivery), wrap(t_energy), t_npv,
               t_pricing, t_inventory, t_quality, t_logistics, t_staffing]
TUT_PASSAGE = [wrap(t_reynolds), wrap(t_fick), wrap(t_halflife),
               t_tut_dimensionless, t_tut_control, t_tut_phase,
               t_tut_error, t_tut_affinity, t_tut_sampling]
LONG_POOL = {"stem": [t_long_design, t_long_review],
             "business": [t_long_assessment, t_long_proposal],
             "tutorial": [t_long_chapter, t_long_manual]}
FRAG_POOL = {"stem": [t_frag_design, t_frag_review],
             "business": [t_frag_proposal, t_frag_memo],
             "tutorial": [t_frag_chapter, t_frag_manual]}

# (kind, domain, pool, count)
SLOTS = [("passage", "stem", STEM_PASSAGE, 220),
         ("passage", "stem", EQ_POOL, 150),
         ("passage", "business", BIZ_PASSAGE, 165),
         ("passage", "tutorial", TUT_PASSAGE, 165),
         ("long", "stem", LONG_POOL["stem"], 40),
         ("long", "business", LONG_POOL["business"], 30),
         ("long", "tutorial", LONG_POOL["tutorial"], 30),
         ("fragment", "stem", FRAG_POOL["stem"], 70),
         ("fragment", "business", FRAG_POOL["business"], 40),
         ("fragment", "tutorial", FRAG_POOL["tutorial"], 40),
         ("identity", "stem", STEM_PASSAGE, 20),
         ("identity", "business", BIZ_PASSAGE, 15),
         ("identity", "tutorial", TUT_PASSAGE, 15)]


def assign_splits(briefs, targets):
    """Assign whole topics to splits, largest topics first, each to
    the split with the largest remaining quota. Returns split per
    brief index."""
    from collections import Counter
    sizes = Counter(b["topic"] for b in briefs)
    remaining = dict(targets)
    topic_split = {}
    for topic, _ in sorted(sizes.items(), key=lambda kv: -kv[1]):
        split = max(remaining, key=lambda s: remaining[s])
        topic_split[topic] = split
        remaining[split] -= sizes[topic]
    return [topic_split[b["topic"]] for b in briefs], topic_split


def main():
    r = random.Random(20261103)
    briefs = []
    for kind, domain, pool, count in SLOTS:
        for i in range(count):
            b = pool[i % len(pool)](r)
            assert b["domain"] == domain, (b["subtype"], domain)
            words = (r.choice(WORDS["passage"][domain]) if kind == "passage"
                     else r.choice(WORDS[kind]))
            rec = {"domain": b["domain"], "subtype": b["subtype"],
                   "kind": kind, "topic": b["topic"],
                   "target_words": words, "skill_load": LOADS[domain],
                   "fact_base": " ".join(b["facts"])}
            for key in ("equations", "sections", "context_packet"):
                if key in b:
                    rec[key] = b[key]
            briefs.append(rec)
    r.shuffle(briefs)
    splits, _ = assign_splits(briefs, {"train": 800, "validation": 100,
                                       "test": 100})
    for i, (b, split) in enumerate(zip(briefs, splits)):
        b["id"] = f"P{i + 1:04d}"
        b["split"] = split
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "briefs.jsonl").write_text(
        "".join(json.dumps(b) + "\n" for b in briefs))
    from collections import Counter
    print("total", len(briefs))
    print("domain", Counter(b["domain"] for b in briefs))
    print("kind", Counter(b["kind"] for b in briefs))
    print("split", Counter(b["split"] for b in briefs))
    print("topics", len(set(b["topic"] for b in briefs)))
    print("equation pairs", sum(1 for b in briefs if "equations" in b))
    assert len(briefs) == 1000
    seen = {}
    for b in briefs:
        if b["topic"] in seen:
            assert seen[b["topic"]] == b["split"], "topic in two splits"
        seen[b["topic"]] = b["split"]
    print("topic purity OK")


if __name__ == "__main__":
    main()
