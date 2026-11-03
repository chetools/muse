"""Generate frozen briefs for the writing-skill LoRA dataset.

Each brief is a fact base: setting sentences plus every number the two
passages may state, with derived values computed here so the brief is
internally consistent by construction. Output: briefs/briefs.jsonl and
briefs/BRIEFS.md. Usage: uv run python gen_briefs.py <count> <seed>
"""
import json, random, sys
from pathlib import Path

OUT = Path(__file__).parent / "briefs"

def n(x, dp=2):
    """Format a number plainly, trimming trailing zeros."""
    s = f"{x:.{dp}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s

# ---------------- STEM templates ----------------

def t_catalyst(r):
    a, b = r.choice([("structured", "pellet"), ("washcoated monolith", "extruded pellet")])
    prod = r.choice(["methanol", "dimethyl ether", "formaldehyde"])
    temp, pres = r.choice([(250, 50), (280, 40), (230, 60)])
    ya, yb = round(r.uniform(0.6, 1.1), 2), round(r.uniform(0.3, 0.55), 2)
    pa, pb = round(r.uniform(0.1, 0.3), 2), round(r.uniform(0.9, 1.6), 2)
    la, lb = r.randint(3, 9), r.randint(11, 20)
    facts = [
        f"Carbon dioxide and hydrogen react over a copper-zinc oxide catalyst to give {prod}.",
        "Space-time yield is the mass of product per unit catalyst volume per hour (kg L-1 h-1).",
        f"Test conditions: {temp} °C, {pres} bar, feed ratio H2/CO2 = 3, one feed composition.",
        f"{a.capitalize()} catalyst: space-time yield {n(ya)} kg L-1 h-1, pressure drop {n(pa)} bar, activity loss {la}% after 100 h.",
        f"{b.capitalize()} catalyst: space-time yield {n(yb)} kg L-1 h-1, pressure drop {n(pb)} bar, activity loss {lb}% after 100 h.",
        "No sulfur-bearing feed was tested. Yield and pressure drop are seldom reported for the same catalyst charge.",
    ]
    return "stem", "research abstract: catalyst comparison", facts

def t_membrane(r):
    sol = r.choice(["ethanol", "isopropanol", "n-butanol"])
    fa, fb = round(r.uniform(1.5, 2.4), 1), round(r.uniform(0.9, 1.4), 1)
    sa, sb = r.choice([120, 180, 240]), r.choice([320, 420, 560])
    drop = r.randint(6, 15)
    facts = [
        f"Pervaporation is a membrane separation in which a liquid feed contacts one side of a membrane and vacuum on the other side draws the permeating component through as vapour.",
        "Flux is the mass permeating per unit membrane area per hour (kg m-2 h-1). The separation factor is the water-to-alcohol ratio in the permeate divided by the same ratio in the feed (dimensionless).",
        f"Feed: 85 wt% {sol} in water, at 60 °C. One feed composition was tested; no test ran beyond 500 h.",
        f"Polymer membrane: flux {n(fa,1)} kg m-2 h-1, separation factor {sa}, flux fell {drop}% over 500 h.",
        f"Zeolite membrane: flux {n(fb,1)} kg m-2 h-1, separation factor {sb}, flux unchanged over 500 h within measurement error.",
        "Flux, selectivity and stability are seldom reported together for the same membrane.",
    ]
    return "stem", "research abstract: membrane comparison", facts

def t_absorber(r):
    cap = r.randint(82, 92); steam = round(r.uniform(3.0, 3.9), 1)
    loss = round(r.uniform(1.2, 2.4), 1); rate = r.randint(9, 15); days = r.choice([45, 60, 90])
    facts = [
        "An amine absorption unit was tested at pilot scale on gas from a cement kiln.",
        f"Over {days} days at {rate} t of carbon dioxide per day, the unit captured {cap}% of the carbon dioxide in the treated gas.",
        f"Steam demand was {n(steam,1)} gigajoules per tonne of carbon dioxide captured; solvent loss was {n(loss,1)} kg per tonne captured.",
        f"Beyond {days} days, the effect of kiln dust on the solvent is untested.",
    ]
    return "stem", "results passage: pilot absorber", facts

def t_kinetics(r):
    ea = r.randint(55, 95); t1, t2 = 300, 340
    import math
    ratio = math.exp(-ea * 1000 / 8.314 * (1 / t2 - 1 / t1))
    k1 = round(r.uniform(0.01, 0.09), 3)
    k2 = k1 * ratio
    facts = [
        "The rate constant k (s-1) of a first-order liquid-phase reaction was measured at two temperatures.",
        f"At {t1} K, k = {n(k1,3)} s-1. At {t2} K, k = {n(k2,3)} s-1, computed from the Arrhenius relation with activation energy {ea} kJ mol-1 as a derived value.",
        "Each temperature was measured in triplicate; the relative standard deviation of k was 4%.",
        "Above 340 K the solvent evaporated during sampling, so no rate constant is reported above 340 K.",
    ]
    return "stem", "results passage: reaction kinetics", facts

def t_adsorption(r):
    mat = r.choice(["activated carbon", "a zeolite 13X sample", "a metal-organic framework"])
    q = round(r.uniform(120, 260), 0); ph = r.choice([5.0, 6.0, 7.0])
    rem = r.randint(78, 94); dose = round(r.uniform(0.4, 1.2), 1)
    facts = [
        f"Adsorption of a dye from water on {mat} was measured in batch tests at 298 K.",
        f"The fitted Langmuir capacity was {n(q,0)} mg of dye per gram of adsorbent at pH {n(ph,1)}.",
        f"At an adsorbent dose of {n(dose,1)} g L-1, removal after 120 min was {rem}% of the initial dye concentration of 50 mg L-1.",
        "The Langmuir fit is reported for pH " + n(ph, 1) + " only; capacity at other pH values was not measured.",
    ]
    return "stem", "results passage: adsorption", facts

# ---------------- Business templates ----------------

def t_sensors(r):
    pumps = r.choice([180, 214, 260]); hrs = r.randint(900, 1400)
    pct = r.randint(38, 52); cost = r.randint(380, 480); yr = r.randint(55, 80)
    cut = r.randint(18, 28); pilot_n = r.randint(14, 24); pcost = r.randint(30, 45)
    facts = [
        f"{pumps} pumps run at the plant. Maintenance records for 12 months show {hrs} h of unplanned downtime; bearing failures account for {pct}% of the downtime hours.",
        f"A sensor set for all {pumps} pumps is quoted at ${cost}k installed, plus ${yr}k per year.",
        f"In a vendor trial on a comparable unit, the sensors cut downtime by {cut}%; the figure is a vendor figure and was not measured at this plant.",
        f"A pilot on {pilot_n} pumps costs ${pcost}k over three months. Spare-part lead times are unchanged by the sensors.",
        "The memo recommends the three-month pilot; the reliability engineering group owns the pilot and reports before the March capital review; the decision on full installation is held until the pilot results are reported.",
    ]
    return "business", "recommendation memo: maintenance sensors", facts

def t_delivery(r):
    plants = r.choice([2, 3, 4]); rev = r.randint(60, 120); orders = r.randint(11000, 18000)
    ot = r.randint(84, 91); tgt = 95; over = round(r.uniform(1.4, 2.6), 1)
    up = r.randint(15, 30); back = round(r.uniform(2.8, 4.2), 1); back0 = round(r.uniform(1.5, 2.2), 1)
    late = r.randint(52, 68); full = r.randint(260, 360); one = r.randint(110, 160)
    facts = [
        f"A contract packaging firm runs {plants} plants; revenue is ${rev} million per year. Evidence base: order records for 12 months, {orders} orders.",
        f"On-time delivery over the last two quarters was {ot}%, against a target of {tgt}%.",
        f"Overtime cost was ${n(over,1)} million last year, up {up}% on the year before. The order backlog stands at {n(back,1)} weeks, against {n(back0,1)} weeks a year ago.",
        f"Plant 2 accounts for {late}% of late orders. A scheduling system for all plants is quoted at ${full}k; Plant 2 alone is ${one}k.",
        "An internal estimate (not a vendor figure) puts the overtime reduction at Plant 2 at 15-20% in the first year.",
        "The recommendation under consideration: install at Plant 2 first, hold the other plants until Plant 2 results are reported. The operations director owns the scheduling programme.",
    ]
    return "business", "executive summary: delivery performance", facts

def t_energy(r):
    base = r.randint(1800, 2600); save = r.randint(11, 17)
    saved = round(base * save / 100); cap = r.randint(300, 520)
    price = round(r.uniform(0.09, 0.14), 2); money = round(saved * 1000 * price / 1000)
    pb = round(cap / money, 1) if money else 0
    facts = [
        f"A food plant uses {base} MWh of electricity per year in refrigeration.",
        f"A heat-recovery retrofit is projected by the equipment vendor to save {save}% of that use, a derived saving of {saved} MWh per year at the vendor figure.",
        f"Capital cost is ${cap}k. At an electricity price of ${n(price)} per kWh, the derived annual saving is ${money}k and the derived simple payback is {n(pb,1)} years.",
        "The saving figure is a vendor projection and was not measured at this plant; refrigeration load in the summer peak month was not modelled.",
        "The recommendation is a metered trial on one of the three refrigeration lines before any capital decision. The plant engineer owns the trial.",
    ]
    return "business", "executive summary: energy retrofit", facts

# ---------------- Tutorial templates ----------------

def t_reynolds(r):
    import math
    d = r.choice([0.025, 0.05, 0.08]); v = round(r.uniform(0.6, 2.4), 1)
    re = 998 * v * d / 1.00e-3
    facts = [
        "Goal: compute the Reynolds number for water in a pipe and state the flow regime.",
        "The Reynolds number Re (dimensionless) is computed from density rho (kg m-3), mean velocity v (m s-1), pipe diameter D (m) and dynamic viscosity mu (Pa s) by Re = rho v D / mu.",
        f"Water at 293 K: rho = 998 kg m-3, mu = 1.00 x 10-3 Pa s. Pipe diameter D = {n(d,3)} m; mean velocity v = {n(v,1)} m s-1.",
        f"Worked result: Re = {round(re, -2):,.0f}".replace(",", "") + f" (computed as 998 x {n(v,1)} x {n(d,3)} / 0.001).",
        "Flow is laminar below Re = 2300 and turbulent above Re = 4000; between the two values the regime is transitional and is not assigned by the number alone.",
    ]
    return "tutorial", "worked example: Reynolds number", facts

def t_fick(r):
    dd = r.choice([1.6, 2.1, 2.6]); film = r.choice([0.4, 0.5, 0.8])
    dc = r.choice([0.20, 0.25, 0.40]); grad = -dc / (film / 1000)
    j = -dd * 1e-9 * grad
    facts = [
        "Goal: compute the diffusive flux of oxygen through a stagnant water film.",
        "The diffusive flux J (mol m-2 s-1) is computed from the diffusivity D (m2 s-1) and the concentration gradient dC/dx, where C is concentration (mol m-3) and x is position (m). Fick's first law: J = -D dC/dx; the negative sign states that diffusion runs from high concentration to low concentration.",
        f"Oxygen in water: D = {n(dd,1)} x 10-9 m2 s-1. Concentration falls by {n(dc)} mol m-3 across a film {n(film,1)} mm thick, so dC/dx = {n(grad,0)} mol m-4.",
        f"Worked result: J = {j:.2e} mol m-2 s-1.".replace("e-0", "x 10-").replace("e-", "x 10-"),
        "The law as stated covers a stagnant medium; a moving medium adds convection, which the equation does not include.",
    ]
    return "tutorial", "worked example: Fick's first law", facts

def t_halflife(r):
    import math
    k = r.choice([0.012, 0.023, 0.046, 0.069]); th = math.log(2) / k
    frac = math.exp(-k * 60)
    facts = [
        "Goal: compute the half-life of a first-order reaction and the fraction remaining after 60 min.",
        "For a first-order reaction the rate constant k (min-1) fixes the half-life t1/2 (min) by t1/2 = ln(2) / k, and the fraction remaining after time t (min) is exp(-k t).",
        f"Measured rate constant: k = {n(k,3)} min-1 at 323 K, from concentration measurements every 5 min over 90 min.",
        f"Worked results: t1/2 = {n(th,1)} min; the fraction remaining after 60 min is {n(frac)} (dimensionless), both computed from the stated relations.",
        "The relations hold for a first-order reaction only; a reaction of another order follows a different decay law.",
    ]
    return "tutorial", "worked example: first-order half-life", facts

TEMPLATES = [t_catalyst, t_membrane, t_absorber, t_kinetics, t_adsorption,
             t_sensors, t_delivery, t_energy,
             t_reynolds, t_fick, t_halflife]
LOADS = {"stem": ["core", "ai-check"], "business": ["core", "business", "ai-check"],
         "tutorial": ["core", "textbook", "ai-check"]}
TARGETS = {"stem": [240, 280, 320], "business": [220, 260, 300], "tutorial": [240, 280, 320]}

def main():
    count, seed = int(sys.argv[1]), int(sys.argv[2])
    r = random.Random(seed)
    OUT.mkdir(parents=True, exist_ok=True)
    briefs, lines = [], ["# Frozen briefs — writing-skill LoRA dataset\n"]
    for i in range(count):
        t = TEMPLATES[i % len(TEMPLATES)]
        domain, subtype, facts = t(r)
        target = r.choice(TARGETS[domain])
        bid = f"B{i+1:03d}"
        briefs.append({"id": bid, "domain": domain, "subtype": subtype,
                       "target_words": target, "skill_load": LOADS[domain],
                       "fact_base": " ".join(facts)})
        lines.append(f"## {bid} — {subtype}. Target: {target} words per version. "
                     f"With-skill load: {' + '.join(LOADS[domain])}.\n\n{' '.join(facts)}\n")
    (OUT / "briefs.jsonl").write_text("\n".join(json.dumps(b) for b in briefs) + "\n")
    (OUT / "BRIEFS.md").write_text("\n".join(lines))
    print(f"wrote {len(briefs)} briefs")

if __name__ == "__main__":
    main()
