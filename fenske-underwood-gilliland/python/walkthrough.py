"""Breakdown cells for the Fenske-Underwood-Gilliland (FUG) page.

One idea per cell.  Cells share one namespace, executed in order by
runner.py at build time and by the generated marimo notebook on MoLab.
Every symbol is defined in the markdown of the cell where it first
appears.  Flow rates are in kmol/h (kilomoles per hour), for the
source example of Seader, Henley & Roper, Separation Process
Principles, 4th ed. (2016), Chapter 9.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fug as F

CELLS = [
    dict(
        title="Feed, key components and specified splits",
        md=r"""The column separates a feed of eight hydrocarbon components, listed in order of decreasing volatility. The symbol $f_i$ denotes the molar flow rate of component $i$ in the feed, in kmol/h (kilomoles per hour). The symbol $F$ denotes the total feed rate, the sum of the $f_i$, in kmol/h. The symbol $z_i$ denotes the mole fraction of component $i$ in the feed, $z_i = f_i / F$, dimensionless.

Two adjacent components are chosen as the key components, whose split between the products is specified. The light key (LK) is n-butane: it is the heaviest component that must pass mainly into the distillate. The heavy key (HK) is isopentane: it is the lightest component that must pass mainly into the bottoms. The symbol $d_i$ denotes the molar flow rate of component $i$ in the distillate and $b_i$ its molar flow rate in the bottoms, both in kmol/h, with $f_i = d_i + b_i$ for every component. The specified splits are $d = 200.488$ and $b = 2.722$ kmol/h for the light key, and $d = 5.897$ and $b = 10.433$ kmol/h for the heavy key.

The symbol $\alpha_i$ denotes the mean relative volatility of component $i$ with respect to the heavy key, dimensionless: the ratio of the distribution coefficients (the equilibrium vapour-to-liquid mole-fraction ratios) of component $i$ and the heavy key, geometrically averaged between the distillate and bottoms conditions of Seader's Example 9.1. By this definition $\alpha = 1$ for the heavy key itself. One volatility set is used in every step of this walkthrough. The column has a total condenser, which is not counted as an equilibrium stage, and a partial reboiler, which is counted as one equilibrium stage.""",
        code=r"""
import numpy as np
import fug as F

inp = F.default_inputs()
feed_arr = np.array(inp["feed"])
print("total feed rate F =", feed_arr.sum(), "kmol/h")
for nm1, fv1, av1 in zip(inp["names"], inp["feed"], inp["alpha"]):
    print(f"{nm1:12s} f = {fv1:7.1f} kmol/h   alpha = {av1:g}")
figure([dict(type="bar", x=inp["names"],
             y=(feed_arr / feed_arr.sum()).tolist(),
             marker=dict(color="#0072B2"), name="Feed mole fraction")],
       xaxis=dict(title="Component"),
       yaxis=dict(title="Feed mole fraction z (dimensionless)"),
       template="plotly_white", showlegend=False)
""",
    ),
    dict(
        title="Fenske equation: minimum stages at total reflux",
        md=r"""The minimum number of equilibrium stages, $N_{min}$ (dimensionless, with the stage counting stated in Step 1), is reached at total reflux, when all condensed vapour is returned to the column and no products are withdrawn. The Fenske equation {{cite:fenske-1932}} gives $N_{min}$ from the key splits and the relative volatility of the light key with respect to the heavy key, $\alpha_{LK,HK}$ (dimensionless), here equal to the tabulated $\alpha$ of the light key because the heavy key is the reference component:

$$N_{min} = \frac{\log_{10}\left[\left(d_{LK}/b_{LK}\right)\left(b_{HK}/d_{HK}\right)\right]}{\log_{10} \alpha_{LK,HK}}$$

Each bracket is the split ratio of one key between the two products. A sharper specified separation, or a smaller $\alpha_{LK,HK}$, requires more stages. The equation is exact only when the relative volatility is constant through the column; the mean volatility of Step 1 is the approximation used here.""",
        code=r"""
dist = F.fenske(inp)
n_min = dist["n_min"]
print("alpha of light key w.r.t. heavy key:", dist["alpha_lk_hk"])
print("minimum stages Nmin =", round(n_min, 4), " (Seader: 7.82)")
""",
    ),
    dict(
        title="Distribution of the non-key components",
        md=r"""The Fenske equation is not restricted to the keys. For any component $i$, applied against the heavy key as reference, it gives the split ratio $d_i / b_i$ at total reflux:

$$\frac{d_i}{b_i} = \frac{d_{HK}}{b_{HK}} \; \alpha_i^{\,N_{min}}$$

Combined with $f_i = d_i + b_i$, this fixes every non-key flow. Following Seader's guidance, the smaller of $d_i$ and $b_i$ is computed from the equation first and the larger by difference, which keeps the small flows accurate; several distillate flows are below $10^{-6}$ kmol/h. The chart uses a logarithmic scale because the flows span twelve orders of magnitude; colour and pattern both encode the product, so the chart reads in greyscale. These total-reflux flows are the product distribution used by the rest of the method.""",
        code=r"""
darr3 = dist["d"]
barr3 = dist["b"]
for nm3, fv3, dv3, bv3 in zip(inp["names"], inp["feed"], darr3, barr3):
    print(f"{nm3:12s} f = {fv3:8.2f}   d = {dv3:12.5g}   b = {bv3:10.3f}")
print("totals: D =", round(darr3.sum(), 2), " B =", round(barr3.sum(), 2),
      " (Seader: 212.71 / 184.77 kmol/h)")
figure([dict(type="bar", x=inp["names"],
             y=np.maximum(darr3, 1e-12).tolist(),
             name="Distillate flow rate", marker=dict(color="#0072B2")),
        dict(type="bar", x=inp["names"],
             y=np.maximum(barr3, 1e-12).tolist(), name="Bottoms flow rate",
             marker=dict(color="#D55E00", pattern=dict(shape="/")))],
       xaxis=dict(title="Component"),
       yaxis=dict(title="Flow rate (kmol/h)", type="log"),
       barmode="group", template="plotly_white",
       legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"))
""",
    ),
    dict(
        title="Underwood Class 1: minimum reflux and its check",
        md=r"""The minimum reflux ratio, $R_{min}$ (dimensionless), is the reflux ratio $R = L/D$ at which the stage count becomes unbounded, where $L$ denotes the liquid reflux flow rate and $D$ the distillate flow rate, both in kmol/h. Underwood's method {{cite:underwood-1948}} distinguishes two classes of separation. In a Class 1 separation every component appears in both products; in a Class 2 separation at least one component appears in only one product. This page carries out the Class 1 calculation only, following Seader's Example 9.4.

The Class 1 shortcut works from the feed liquid left by the feed flash of Example 9.1. The symbol $F_L$ denotes that feed liquid rate, $344.277$ kmol/h, and the symbols $f^L_{LK}$ and $f^L_{HK}$ denote the feed-liquid rates of the two keys, $156.675$ and $14.188$ kmol/h. The symbol $\alpha_f$ denotes the relative volatility of the light key with respect to the heavy key at feed conditions, $1.967$, dimensionless; it is distinct from the mean volatility $1.864$ of Step 1, which the Fenske equation uses. With $L_{min}$ denoting the minimum internal reflux rate, in kmol/h, the Class 1 result is

$$\frac{L_{min}}{F} = \frac{F_L}{F} \, \frac{\left(d_{LK}/f^L_{LK}\right) - \alpha_f \left(d_{HK}/f^L_{HK}\right)}{\alpha_f - 1}$$

which gives $L_{min}/F = 0.414$ per unit feed, and the headline minimum reflux ratio is per unit distillate: $R_{min} = L_{min}/D$ at the Fenske distillate rate of Step 3. As derivation and check material, this cell also evaluates the root of the Underwood feed equation in the interval between the key volatilities, $1.0443$; the Theory panel derives that equation. No second root is used and no Class 2 solve is carried out.

The validity check on the Class 1 assumption then fails, and the failure is stated plainly. Seader's Example 9.4 applies the Class 1 relations to the non-key components and obtains negative distillate flow rates for the heavy non-keys and an isobutane distillate flow rate above its feed rate. The debutanizer separation is therefore not in fact Class 1: most non-keys appear in one product only. The Class 1 minimum reflux ratio, and the Gilliland stage count that follows from it in Step 5, are the formal Class 1 results, reported as such.

One further point is recorded in this cell's output. Seader prints the Class 1 ratio as $0.864$ per unit distillate. Converted at the distillate rate of Step 3, his per-feed value of $0.414$ gives $0.774$ per unit distillate, not $0.864$; the printed $0.864$ would follow from a feed rate of $444.0$ kmol/h in place of $397.5$ kmol/h. The page reports both values; its headline result is the recomputed $0.774$.""",
        code=r"""
und = F.underwood_class1(inp, dist)
print("Class 1 minimum internal reflux per unit feed:",
      round(und["l_per_f"], 3), " (Seader: 0.414)")
print("Lmin =", round(und["l_min"], 1), "kmol/h")
print("Rmin =", round(und["r_min"], 3),
      " per unit distillate (recomputed; Seader prints 0.864)")
print("feed-equation root in the key interval (check material):",
      round(und["theta_key_interval"], 4), " (Seader: 1.0443)")
print("feed rate implied by the printed 0.864:",
      round(und["implied_feed_printed"], 1), "kmol/h")
""",
    ),
    dict(
        title="Gilliland correlation: stages at the operating reflux",
        md=r"""The operating reflux ratio $R$ is chosen as a multiple of the minimum: $R = 1.3 \, R_{min}$, the multiplier of Seader's Example 9.6, where $1.3$ is the reflux multiplier (dimensionless). Example 9.6 tabulates the correlation for both of his minimum-reflux rows; this page follows the Class 1 row, at the recomputed Class 1 minimum reflux ratio of Step 4. The Gilliland correlation {{cite:gilliland-1940}} relates the stage count at finite reflux to the two limits, total reflux and minimum reflux, through the dimensionless variables $X = (R - R_{min}) / (R + 1)$ and $Y = (N - N_{min}) / (N + 1)$, where $N$ denotes the number of equilibrium stages at $R$, with the stage counting of Step 1. The page evaluates the correlation with the explicit equation of Eduljee {{cite:eduljee-1975}}, Seader's Eq. (9-33):

$$Y = 1 - \exp\left(\frac{(1 + 54.4 X)(X - 1)}{(11 + 117.2 X)\sqrt{X}}\right)$$

Solving $Y = (N - N_{min})/(N + 1)$ for $N$ gives the stage requirement. As $R$ approaches $R_{min}$, $X$ approaches $0$ and $N$ grows without bound; as $R$ grows without bound, $N$ approaches $N_{min}$. The correlation carries no feed-condition parameter, a known limitation Seader records: it is conservative for feeds of low $q$. The chart plots the curve for reflux multipliers from 1.001 to 4, not only the operating point.""",
        code=r"""
gil = F.gilliland(und["r_min"], n_min, inp["mult"])
print("R =", round(gil["R"], 3), " X =", round(gil["X"], 4),
      " Y =", round(gil["Y"], 4))
print("N =", round(gil["N"], 2), "equilibrium stages (Seader's Class 1 row, from his printed 0.864: 17.8)")
mults6 = np.concatenate(([1.001], np.linspace(1.01, 4.0, 120)))
xs6 = []
ys6 = []
for m6 in mults6:
    g6 = F.gilliland(und["r_min"], n_min, float(m6))
    xs6.append(g6["X"])
    ys6.append(g6["Y"])
figure([dict(type="scatter", x=xs6, y=ys6, mode="lines",
             name="Gilliland correlation (Eduljee equation)",
             line=dict(color="#0072B2", width=2)),
        dict(type="scatter", x=[gil["X"]], y=[gil["Y"]], mode="markers",
             name="Operating point",
             marker=dict(color="#D55E00", size=11, symbol="circle"))],
       xaxis=dict(title="X (dimensionless)"),
       yaxis=dict(title="Y (dimensionless)"),
       template="plotly_white",
       legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"))
""",
    ),
    dict(
        title="Feed-stage location and anchor checks",
        md=r"""The stage count is split between the rectifying section, above the feed, and the stripping section, below it. The symbol $N_R$ denotes the number of equilibrium stages in the rectifying section and $N_S$ the number in the stripping section, the partial reboiler counted in the stripping section. Kirkbride's empirical equation {{cite:kirkbride-1944}} gives the ratio

$$\frac{N_R}{N_S} = \left[ \frac{z_{HK}}{z_{LK}} \left(\frac{x_{LK,B}}{x_{HK,D}}\right)^{2} \frac{B}{D} \right]^{0.206}$$

where $x_{LK,B}$ denotes the mole fraction of the light key in the bottoms, $x_{HK,D}$ the mole fraction of the heavy key in the distillate, $B$ the total bottoms rate and $D$ the total distillate rate, both in kmol/h. The second estimate applies the Fenske equation to each section separately at total reflux. Seader reports Kirkbride as the better of the two on his test problem, and it is listed first here. The total stage count is rounded up to a whole number before the split, because a column is built of whole stages; the reboiler is one of them, so the number of theoretical trays is one less than the rounded stage count.

The anchor checks assert the values verified against Seader's Examples 9.2, 9.4 and 9.6 (the Class 1 row). A failed assertion means the calculation has drifted from the verified case.""",
        code=r"""
res7 = F.run_case(inp)
m7 = res7["metrics"]
fs7 = F.feed_stage(inp, dist, float(m7["n_round"]))
print("rounded stages:", m7["n_round"],
      "; theoretical trays:", m7["trays_theoretical"])
print("Kirkbride: NR/NS =", round(fs7["kirkbride"]["ratio"], 3),
      " NR =", round(fs7["kirkbride"]["n_rect"], 2),
      " NS =", round(fs7["kirkbride"]["n_strip"], 2))
print("Fenske sections: NR/NS =", round(fs7["fenske"]["ratio"], 3))
print("feed stage (Kirkbride):", int(fs7["kirkbride"]["n_rect"]) + 1,
      "of", m7["n_round"])
assert abs(n_min - 7.8206) < 0.01, "Nmin anchor failed"
assert abs(und["theta_key_interval"] - 1.0443) < 0.002, "theta anchor failed"
assert abs(und["r_min"] - 0.774) < 0.002, "Class 1 Rmin anchor failed"
assert abs(gil["N"] - 18.09) < 0.15, "Gilliland anchor failed"
assert m7["n_round"] == 19, "rounded stage anchor failed"
assert abs(darr3.sum() + barr3.sum() - feed_arr.sum()) < 5e-3, \
    "balance closure failed (tolerance is the rounding of the specified splits)"
print("all anchor checks passed")
""",
    ),
]
