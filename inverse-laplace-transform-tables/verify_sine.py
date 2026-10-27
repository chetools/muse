import sympy as sp
import mpmath as mp

s, t = sp.symbols('s t')
K_v, M_v, tau_v = 2.0, 3.0, 3.0
KM = K_v * M_v

def assembled(tval, zeta, q, kind):
    w = q / tau_v
    S = (1 - q**2)**2 + (2 * zeta * q)**2
    R = 1 / mp.sqrt(S)
    phi = -mp.atan2(2 * zeta * q, 1 - q**2)
    if kind == 'cos':
        yss = KM * R * mp.cos(w * tval + phi)
        P0 = (1 - q**2) / S
        P1 = 2 * zeta * q**2 / S
    else:
        yss = KM * R * mp.sin(w * tval + phi)
        P0 = -2 * zeta * q / S
        P1 = q * (1 - q**2) / S
    if zeta > 1:
        beta = mp.sqrt(zeta**2 - 1)
        r1 = (-zeta + beta) / tau_v; r2 = (-zeta - beta) / tau_v
        a1 = (-P1 + (r2 * tau_v) * P0) / ((r1 - r2) * tau_v)
        a2 = (-P1 + (r1 * tau_v) * P0) / ((r2 - r1) * tau_v)
        yh = KM * (a1 * mp.e**(r1 * tval) + a2 * mp.e**(r2 * tval))
    elif zeta == 1:
        A1 = -KM * P0
        A2 = (KM / tau_v) * (-P1 - P0)
        yh = (A1 + A2 * tval) * mp.e**(-tval / tau_v)
    else:
        delta = mp.sqrt(1 - zeta**2)
        alpha = zeta / tau_v; wd = delta / tau_v
        A1 = -KM * P0
        A2 = KM * (-P1 - zeta * P0) / delta
        yh = mp.e**(-alpha * tval) * (A1 * mp.cos(wd * tval) + A2 * mp.sin(wd * tval))
    return yss + yh

def reference(tval, zeta, q, kind):
    w = q / tau_v
    G = K_v / (tau_v**2 * s**2 + 2 * zeta * tau_v * s + 1)
    U = M_v * s / (s**2 + w**2) if kind == 'cos' else M_v * w / (s**2 + w**2)
    y = sp.inverse_laplace_transform(G * U, s, t)
    val = complex(y.subs(t, tval).evalf())
    assert abs(val.imag) < 1e-8, val
    return val.real

maxerr = 0.0
for zeta in [1.5, 1.0, 0.5]:
    for q in [0.7, 1.0, 1.8]:
        for kind in ['cos', 'sin']:
            for tv in [0, 0.4, 1.3, 4, 9]:
                a = assembled(tv, zeta, q, kind)
                r = reference(tv, zeta, q, kind)
                err = abs(a - r)
                maxerr = max(maxerr, err)
                if err > 1e-6:
                    print("MISMATCH", zeta, q, kind, tv, a, r, err)
            print(f"zeta={zeta} q={q} {kind}: assembled(9)={float(assembled(9, zeta, q, kind)):.6f} reference(9)={float(reference(9, zeta, q, kind)):.6f}")
print("MAX ERROR over all cases:", maxerr)
# resonance steady-state checks
for zeta in [1.5, 1.0, 0.5]:
    print("resonance amplitude 1/(2 zeta) =", 1/(2*zeta), " R(q=1) =", 1/mp.sqrt((2*zeta)**2))
