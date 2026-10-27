"""Illustrative plots for the inverse Laplace transform tables page.

All curves are dimensionless: time is t/tau, output is y/(KM), input is u/M.
Formulas are the verified formulas of Tables 1-4 of the page (tau = 1, KM = 1).
Each plotted family is spot-checked against an independent ODE integration
(scipy solve_ivp) before the figure is written.
"""
import io
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 10, "axes.labelsize": 10,
    "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 3, "ytick.major.size": 3,
    "xtick.direction": "out", "ytick.direction": "out",
    "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 1.4,
    "legend.frameon": False,
    "svg.fonttype": "none",
})

OKABE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7"]


def step_y(th, zeta):
    if zeta > 1:
        beta = np.sqrt(zeta**2 - 1)
        r1 = -zeta + beta
        r2 = -zeta - beta
        return 1 - (zeta + beta) / (2 * beta) * np.exp(r1 * th) + (zeta - beta) / (2 * beta) * np.exp(r2 * th)
    if zeta == 1:
        return 1 - (1 + th) * np.exp(-th)
    delta = np.sqrt(1 - zeta**2)
    return 1 - np.exp(-zeta * th) * (np.cos(delta * th) + zeta / delta * np.sin(delta * th))


def sine_response(th, zeta, q, kind):
    """Complete response y/(KM) for tau = 1, KM = 1; q = omega (tau = 1)."""
    S = (1 - q**2)**2 + (2 * zeta * q)**2
    R = 1 / np.sqrt(S)
    phi = -np.arctan2(2 * zeta * q, 1 - q**2)
    if kind == "cos":
        yss = R * np.cos(q * th + phi)
        P0 = (1 - q**2) / S
        P1 = 2 * zeta * q**2 / S
    else:
        yss = R * np.sin(q * th + phi)
        P0 = -2 * zeta * q / S
        P1 = q * (1 - q**2) / S
    if zeta > 1:
        beta = np.sqrt(zeta**2 - 1)
        r1 = -zeta + beta
        r2 = -zeta - beta
        a1 = (-P1 + (-zeta - beta) * P0) / (2 * beta)
        a2 = (-P1 + (-zeta + beta) * P0) / (-2 * beta)
        yh = a1 * np.exp(r1 * th) + a2 * np.exp(r2 * th)
    elif zeta == 1:
        yh = (-P0 - (P1 + P0) * th) * np.exp(-th)
    else:
        delta = np.sqrt(1 - zeta**2)
        yh = np.exp(-zeta * th) * (-P0 * np.cos(delta * th) + (-P1 - zeta * P0) / delta * np.sin(delta * th))
    return yss + yh


def ode_check():
    """Independent check: integrate tau^2 y'' + 2 zeta tau y' + y = K u with tau=1, K=1."""
    worst = 0.0
    th = np.linspace(0, 20, 401)
    for zeta in (0.5, 1.0, 1.5):
        for q in (0.5, 1.0, 2.0):
            for kind in ("cos", "sin"):
                u = (lambda tt: np.cos(q * tt)) if kind == "cos" else (lambda tt: np.sin(q * tt))
                rhs = lambda tt, yy: [yy[1], u(tt) - 2 * zeta * yy[1] - yy[0]]
                sol = solve_ivp(rhs, [0, 20], [0.0, 0.0], t_eval=th, rtol=1e-9, atol=1e-11)
                err = np.max(np.abs(sol.y[0] - sine_response(th, zeta, q, kind)))
                worst = max(worst, err)
        sol = solve_ivp(lambda tt, yy: [yy[1], 1.0 - 2 * zeta * yy[1] - yy[0]],
                        [0, 15], [0.0, 0.0], t_eval=np.linspace(0, 15, 301), rtol=1e-9, atol=1e-11)
        err = np.max(np.abs(sol.y[0] - step_y(np.linspace(0, 15, 301), zeta)))
        worst = max(worst, err)
    # resonance figure cases (Fig. 5): q = 1, zeta down to 0.1, t/tau to 40
    th40 = np.linspace(0, 40, 801)
    for zeta in (0.1, 0.25, 0.5, 1.0):
        for kind in ("cos", "sin"):
            u = (lambda tt: np.cos(tt)) if kind == "cos" else (lambda tt: np.sin(tt))
            rhs = lambda tt, yy: [yy[1], u(tt) - 2 * zeta * yy[1] - yy[0]]
            sol = solve_ivp(rhs, [0, 40], [0.0, 0.0], t_eval=th40, rtol=1e-9, atol=1e-11)
            err = np.max(np.abs(sol.y[0] - sine_response(th40, zeta, 1.0, kind)))
            worst = max(worst, float(err))
    # step case at zeta = 0.25 (plotted in Fig. 1, outside the loop above)
    zeta = 0.25
    th15 = np.linspace(0, 15, 301)
    sol = solve_ivp(lambda tt, yy: [yy[1], 1.0 - 2 * zeta * yy[1] - yy[0]],
                    [0, 15], [0.0, 0.0], t_eval=th15, rtol=1e-9, atol=1e-11)
    worst = max(worst, float(np.max(np.abs(sol.y[0] - step_y(th15, zeta)))))
    print(f"ODE spot check, maximum absolute difference: {worst:.2e}")
    assert worst < 2e-6, worst


def save_svg(fig, name):
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    svg = buf.getvalue()
    start = svg.find("<svg")
    svg = svg[start:]
    path = f"/home/hatch/workspace/inverse-laplace-tables/{name}"
    with open(path, "w") as f:
        f.write(svg)
    print(f"wrote {name}: {len(svg)//1024} KB")


def fig_step():
    th = np.linspace(0, 15, 900)
    fig, ax = plt.subplots(figsize=(10, 5.4))
    styles = {0.25: "-", 0.5: "--", 1.0: "-", 1.5: ":"}
    for i, zeta in enumerate((0.25, 0.5, 1.0, 1.5)):
        ax.plot(th, step_y(th, zeta), color=OKABE[i], linestyle=styles[zeta],
                label=f"$\\zeta$ = {zeta:g}")
    ax.axhline(1.0, color="#888888", linewidth=0.7, linestyle=(0, (5, 4)))
    ax.set_xlim(0, 15)
    ax.set_ylim(-0.1, 1.6)
    ax.set_xlabel("$t/\\tau$")
    ax.set_ylabel("$y/(KM)$")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), title=None)
    save_svg(fig, "fig-step.svg")


def fig_sine(kind):
    zetas = (0.5, 1.0, 1.5)
    qs = (0.5, 1.0, 2.0)
    th = np.linspace(0, 20, 1600)
    fig, axes = plt.subplots(3, 3, figsize=(10.5, 8.2), sharex=True, sharey=True)
    for i, zeta in enumerate(zetas):
        for j, q in enumerate(qs):
            ax = axes[i][j]
            u = np.cos(q * th) if kind == "cos" else np.sin(q * th)
            ax.plot(th, u, color="#888888", linewidth=0.9, linestyle=(0, (5, 4)), label="$u/M$")
            ax.plot(th, sine_response(th, zeta, q, kind), color=OKABE[0], label="$y/(KM)$")
            ax.set_title(f"$\\zeta$ = {zeta:g},  $q$ = {q:g}", fontsize=9.5)
            ax.set_xlim(0, 20)
            ax.set_ylim(-1.55, 1.55)
            ax.set_xticks([0, 5, 10, 15, 20])
            ax.set_yticks([-1.5, -0.75, 0, 0.75, 1.5])
    for ax in axes[-1]:
        ax.set_xlabel("$t/\\tau$")
    for row in axes:
        row[0].set_ylabel("$y/(KM)$")
    handles, labels = axes[0][0].get_legend_handles_labels()
    order = [1, 0]
    fig.legend([handles[k] for k in order], [labels[k] for k in order],
               loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.015))
    save_svg(fig, f"fig-{kind}.svg")


def fig_freq():
    q = np.logspace(-1, 1, 600)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharex=True)
    styles = {0.5: "-", 1.0: "--", 1.5: ":"}
    for i, zeta in enumerate((0.5, 1.0, 1.5)):
        S = (1 - q**2)**2 + (2 * zeta * q)**2
        R = 1 / np.sqrt(S)
        phi = -np.arctan2(2 * zeta * q, 1 - q**2)
        axes[0].plot(q, R, color=OKABE[i], linestyle=styles[zeta], label=f"$\\zeta$ = {zeta:g}")
        axes[1].plot(q, phi, color=OKABE[i], linestyle=styles[zeta], label=f"$\\zeta$ = {zeta:g}")
    for ax in axes:
        ax.axvline(1.0, color="#888888", linewidth=0.7)
        ax.set_xscale("log")
        ax.set_xlim(0.1, 10)
        ax.set_xlabel("$q = \\omega/\\omega_n$")
    axes[0].set_ylabel("$R$")
    axes[0].set_ylim(0, 2.1)
    axes[1].set_ylabel("$\\phi$ (rad)")
    axes[1].set_ylim(-3.3, 0.15)
    axes[1].set_yticks([-np.pi, -np.pi / 2, 0])
    axes[1].set_yticklabels(["$-\\pi$", "$-\\pi/2$", "0"])
    axes[0].legend(loc="upper left", bbox_to_anchor=(0.0, 1.16), ncol=3)
    save_svg(fig, "fig-freq.svg")


def fig_resonance():
    zetas = (0.1, 0.25, 0.5, 1.0)
    colors = {0.1: "#CC79A7", 0.25: "#0072B2", 0.5: "#D55E00", 1.0: "#009E73"}
    styles = {0.1: "-", 0.25: "-", 0.5: "--", 1.0: "-."}
    th = np.linspace(0, 40, 3200)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.9), sharex=True, sharey=True)
    for ax, kind in zip(axes, ("cos", "sin")):
        u = np.cos(th) if kind == "cos" else np.sin(th)
        ax.plot(th, u, color="#888888", linewidth=0.9, linestyle=(0, (5, 4)), label="$u/M$")
        for zeta in zetas:
            ax.plot(th, sine_response(th, zeta, 1.0, kind), color=colors[zeta],
                    linestyle=styles[zeta], label=f"$\\zeta$ = {zeta:g}")
        ax.set_title("Cosine input" if kind == "cos" else "Sine input", fontsize=10)
        ax.set_xlim(0, 40)
        ax.set_ylim(-5.5, 5.5)
        ax.set_yticks([-5, -2.5, 0, 2.5, 5])
        ax.set_xlabel("$t/\\tau$")
    axes[0].set_ylabel("$y/(KM)$")
    handles, labels = axes[0].get_legend_handles_labels()
    order = [1, 2, 3, 4, 0]
    fig.legend([handles[k] for k in order], [labels[k] for k in order],
               loc="upper center", ncol=5, bbox_to_anchor=(0.5, 1.06))
    save_svg(fig, "fig-resonance.svg")


if __name__ == "__main__":
    ode_check()
    fig_step()
    fig_sine("cos")
    fig_sine("sin")
    fig_freq()
    fig_resonance()
    # data ranges for the record
    th = np.linspace(0, 20, 2001)
    for kind in ("cos", "sin"):
        vals = [sine_response(th, z, q, kind) for z in (0.5, 1.0, 1.5) for q in (0.5, 1.0, 2.0)]
        allv = np.concatenate(vals)
        print(kind, "response range:", float(allv.min()), float(allv.max()))
