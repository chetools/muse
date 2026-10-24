"""Independent check of the pipe-diameter cost comparison (Colebrook via Lambert W, cross-checked with brentq)."""
import json, math
import numpy as np
from scipy.special import lambertw
from scipy.optimize import brentq

RHO, MU, Q, L = 998.0, 1.002e-3, 0.110, 9000.0
HOURS, CAPF, CAPC, CAPE = 8200.0, 0.12, 2275.0, 1.55
C = 2.0 / math.log(10.0)


def f_lambertw(re, rr):
    # x = 1/sqrt(f); x = -C ln(a + b x), a = rr/3.7, b = 2.51/Re
    # y = a + b x  ->  y = b C W(exp(a/(bC)) / (bC)),  x = -C ln y
    a, b = rr / 3.7, 2.51 / re
    k = b * C
    z = math.exp(a / k) / k
    w = lambertw(z, 0)
    assert abs(w.imag) == 0.0
    y = k * w.real
    x = -C * math.log(y)
    return 1.0 / (x * x)


def f_brent(re, rr):
    a, b = rr / 3.7, 2.51 / re
    g = lambda x: x + C * math.log(a + b * x)
    x = brentq(g, 1.0, 100.0, xtol=1e-15, rtol=4 * np.finfo(float).eps, maxiter=500)
    return 1.0 / (x * x)


RELDIFFS = []


def case(D, eta=0.74, price=0.14, eps=0.045e-3):
    A = math.pi * D * D / 4.0
    v = Q / A
    re = RHO * v * D / MU
    f = f_lambertw(re, eps / D)
    fb = f_brent(re, eps / D)
    RELDIFFS.append(abs(f - fb) / fb)
    dp = f * (L / D) * RHO * v * v / 2.0
    pkw = Q * dp / eta / 1000.0
    energy = pkw * HOURS * price
    capital = CAPC * D ** CAPE * L * CAPF
    return {"f": f, "re": re, "v": v, "dp_kpa": dp / 1000.0, "power_kw": pkw,
            "energy": energy, "capital": capital, "total": math.fsum([energy, capital])}


def saving(**kw):
    return case(0.30, **kw)["total"] - case(0.28, **kw)["total"]


costs = {"0.28": case(0.28), "0.30": case(0.30)}
out = {
    "costs": costs,
    "saving": costs["0.30"]["total"] - costs["0.28"]["total"],
    "sensitivity": {
        "eta_0.70": saving(eta=0.70),
        "price_0.15": saving(price=0.15),
        "eps_0.015mm": saving(eps=0.015e-3),
        "eps_0.090mm": saving(eps=0.090e-3),
    },
    "f_lambertw_vs_brent_max_rel_diff": max(RELDIFFS),
    "method": "Colebrook solved exactly with the principal-branch Lambert W (x=1/sqrt(f)=-(2/ln10)ln(bCW(e^{a/bC}/bC))), cross-checked by brentq on x+(2/ln10)ln(a+bx)=0 with xtol 1e-15; costs evaluated in full double precision.",
}
print(json.dumps(out, indent=1))
