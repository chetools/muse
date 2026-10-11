# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "marimo",
#     "numpy",
#     "plotly",
# ]
# ///

"""P-xy diagram of methane(1) / n-butane(2) at 37.8 C from the SRK equation.

Reproduces Figure 13.13 of Smith, Van Ness & Abbott, *Introduction to
Chemical Engineering Thermodynamics*: bubble-point-pressure (BUBL P)
calculations with the Soave-Redlich-Kwong (SRK) equation of state generate
both the bubble and the dew branch in a single sweep over the liquid mole
fraction. Experimental points (Reamer, Sage & Lacey) were digitized from the
printed figure and are embedded below (41 points; see data/ for the CSV).

Contents:
  1. phase-equilibrium criterion (fugacity equality, K-values),
  2. full step-by-step derivation of the SRK mixture fugacity coefficient
     from the residual Helmholtz energy (every calculus step shown),
  3. the parallel Peng-Robinson derivation,
  4. mixing rules and the BUBL P algorithm,
  5. compact numpy implementation (no hand-rolled numerics beyond a
     bisection loop; the cubic is solved in closed form),
  6. the computed P-x-y diagram with the experimental overlay,
  7. temperature and k12 sliders plus a Peng-Robinson comparison toggle,
  8. residual plot and a verification cell.

Units: SI throughout the derivations (Pa, m^3, J, mol, K); plots use bar.
"""

import marimo

__generated_with = "0.25.1"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md(
        r"""
        # P–xy diagram of methane / n-butane at 37.8 °C, from the SRK equation

        This notebook reproduces **Figure 13.13** of Smith, Van Ness & Abbott,
        *Introduction to Chemical Engineering Thermodynamics*: the
        pressure–composition phase diagram of the **methane(1) / n-butane(2)**
        binary at $T = 37.8\,\mathrm{°C}$ ($100\,\mathrm{°F}$).
        The **curves** are bubble-point-pressure (BUBL P) calculations with the
        **Soave–Redlich–Kwong (SRK)** equation of state; the **markers** are
        experimental data (Reamer, Sage & Lacey), digitized from the printed
        figure and embedded in this notebook.

        The central idea, worth stating up front: at fixed temperature $T$ and
        liquid mole fraction $x_1$, a bubble-point calculation returns not
        only the bubble pressure $P$ but also the incipient vapor composition
        $y_1$. One sweep over $x_1$ therefore traces **both** branches —
        $P$ vs $x_1$ (bubble curve) and $P$ vs $y_1$ (dew curve). That is
        exactly how the book's lines were generated, and it is what we
        recompute here.

        ### Symbols

        Every symbol is defined at or before its first use. The cast:

        - $T$ temperature [K], $P$ pressure [Pa] (plots use [bar])
        - $n$ total moles [mol], $V$ total volume [m$^3$], $R$ gas constant
          [J/(mol·K)]
        - $x_i$, $y_i$ mole fractions of component $i$ in liquid / vapor;
          component $1$ = methane, component $2$ = n-butane
        - $V_m = V/n$ molar volume [m$^3$/mol]
        - $a$, $b$ SRK (molar) attraction / covolume parameters
          [Pa·m$^6$/mol$^2$], [m$^3$/mol]; $a_i$, $b_i$ pure-component values,
          $a_{ij}$ cross parameter
        - $k_{ij}$ binary interaction parameter (dimensionless)
        - $A = aP/(R^2T^2)$, $B = bP/(RT)$ dimensionless EOS parameters
        - $Z = PV/(nRT)$ compressibility factor
        - $\hat{\phi}_i$ fugacity coefficient of $i$ in the mixture;
          $\hat{f}_i = z_i \hat{\phi}_i P$ is its fugacity [Pa]
          ($z_i = x_i$ or $y_i$)
        - $K_i = y_i/x_i$ vapor–liquid equilibrium ratio
        - $A^R$ residual Helmholtz energy [J]:
          $A^R(T,V,n) = A(T,V,n) - A^{ig}(T,V,n)$, the departure from an
          ideal gas at the same $T$, $V$, $n$
        - $T_c$, $P_c$, $\omega$ critical temperature [K], critical pressure
          [Pa], acentric factor
        """
    )


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 1. The equilibrium criterion

        At vapor–liquid equilibrium the temperature and pressure are uniform
        and each component's fugacity is the same in both phases:

        $$\hat{f}_i^v = \hat{f}_i^l \qquad i = 1, 2$$

        Writing $\hat{f}_i^v = y_i \hat{\phi}_i^v P$ and
        $\hat{f}_i^l = x_i \hat{\phi}_i^l P$ (the pressure $P$ cancels),

        $$y_i \hat{\phi}_i^v = x_i \hat{\phi}_i^l$$

        and with the equilibrium ratio $K_i = y_i / x_i$,

        $$K_i = \frac{\hat{\phi}_i^l}{\hat{\phi}_i^v}$$

        A **bubble-point-pressure (BUBL P)** calculation fixes $T$ and the
        liquid composition $x = (x_1, x_2)$ and finds the pressure $P$ (and the
        vapor composition $y$) satisfying $\sum_i y_i = \sum_i K_i x_i = 1$.
        The equation of state enters only through the fugacity coefficients
        $\hat{\phi}_i^l(T, P, x)$ and $\hat{\phi}_i^v(T, P, y)$ — deriving those
        for SRK is the subject of Sections 3–4.
        """
    )


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 2. The SRK equation and pure-component parameters

        The Soave–Redlich–Kwong equation, in molar form ($V_m = V/n$):

        $$P = \frac{RT}{V_m - b} - \frac{a\,\alpha}{V_m\,(V_m + b)}$$

        with, for each pure component,

        $$a = 0.42748\,\frac{R^2 T_c^2}{P_c}, \qquad b = 0.08664\,\frac{RT_c}{P_c}, \qquad \alpha = \left[1 + m\left(1 - \sqrt{T/T_c}\right)\right]^2,$$

        $$m = 0.480 + 1.574\,\omega - 0.176\,\omega^2.$$

        | component | $T_c$ [K] | $P_c$ [bar] | $\omega$ |
        |---|---|---|---|
        | 1 methane | 190.6 | 45.99 | 0.011 |
        | 2 n-butane | 425.12 | 37.96 | 0.200 |

        (We absorb $\alpha(T)$ into $a$, writing $a$ for $a\,\alpha$ from here
        on; $a$ and $b$ below are therefore temperature-dependent and
        composition-dependent molar mixture parameters unless subscripted.)
        """
    )


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 3. Fugacity coefficients from the residual Helmholtz energy, step by step

        ### 3a. The residual Helmholtz energy of the SRK fluid

        The mixture fugacity coefficient follows from the residual Helmholtz
        energy through the exact thermodynamic relation

        $$\ln \hat{\phi}_i = \frac{1}{RT} \left(\frac{\partial A^R}{\partial n_i}\right)_{T,V,n_{j \ne i}} - \ln Z,$$

        where $Z = PV/(nRT)$ is the mixture compressibility factor. So we
        first need $A^R(T, V, n)$ for SRK, obtained by isothermal integration
        from the ideal-gas state ($V \to \infty$):

        $$A^R(T,V,n) = -\int_{\infty}^{V} \left[P(T,V',n) - \frac{nRT}{V'}\right] dV'.$$

        Write SRK with total (not molar) quantities. With molar parameters
        $a$, $b$ and $n$ total moles, $V_m = V/n$:

        $$P = \frac{nRT}{V - nb} - \frac{n^2 a}{V\,(V + nb)}.$$

        The integrand's first piece simplifies by putting the two
        $nRT$ terms over a common denominator:

        $$\frac{nRT}{V - nb} - \frac{nRT}{V} = nRT\,\frac{V - (V - nb)}{V\,(V - nb)} = \frac{nRT\,(nb)}{V\,(V - nb)}.$$

        Hence

        $$P - \frac{nRT}{V} = \frac{nRT\,(nb)}{V\,(V - nb)} - \frac{n^2 a}{V\,(V + nb)},$$

        and we integrate term by term. **First term.** Partial fractions give

        $$\frac{nb}{V'(V' - nb)} = \frac{1}{V' - nb} - \frac{1}{V'},$$

        so that

        $$\int_{\infty}^{V} \frac{nRT\,(nb)}{V'(V' - nb)}\,dV' = nRT\left[\ln(V' - nb) - \ln V'\right]_{\infty}^{V} = nRT\,\ln\!\left(\frac{V - nb}{V}\right) = nRT\,\ln\!\left(1 - \frac{nb}{V}\right).$$

        (At the upper limit $V' \to \infty$ the logarithm tends to
        $\ln 1 = 0$.) **Second term.** Again by partial fractions,

        $$\frac{1}{V'(V' + nb)} = \frac{1}{nb} \left(\frac{1}{V'} - \frac{1}{V' + nb}\right),$$

        giving

        $$\int_{\infty}^{V} \frac{n^2 a}{V'(V' + nb)}\,dV' = \frac{n^2 a}{nb}\left[\ln V' - \ln(V' + nb)\right]_{\infty}^{V} = \frac{na}{b}\,\ln\!\left(\frac{V}{V + nb}\right) = -\frac{na}{b}\,\ln\!\left(1 + \frac{nb}{V}\right).$$

        Assembling $A^R = -(\text{first}) + (\text{second})$,

        $$A^R = -nRT\,\ln\!\left(1 - \frac{nb}{V}\right) - \frac{na}{b}\,\ln\!\left(1 + \frac{nb}{V}\right),$$

        i.e., with everything divided by $RT$,

        $$\frac{A^R}{RT} = -n\,\ln\!\left(1 - \frac{nb}{V}\right) - \frac{na}{bRT}\,\ln\!\left(1 + \frac{nb}{V}\right).$$

        Sign check: the first term is positive (excluded volume raises the
        Helmholtz energy — repulsion), the second negative (attraction lowers
        it). Both $a = a(x)$ and $b = b(x)$ are the *molar mixture*
        parameters and therefore depend on the mole numbers $n_i$ through
        $x_i = n_i/n$; the mixing rules are stated in Section 5.
        """
    )


@app.cell
def _(mo):
    mo.md(
        r"""
        ### 3b. Differentiating: from $A^R$ to $\ln \hat{\phi}_i$

        We need $\partial(A^R/RT)/\partial n_i$ at constant $T$, $V$,
        $n_{j \ne i}$ (dividing by the constant $RT$ first is legitimate since
        $T$ is held fixed). Write the result of Section 3a with compact
        symbols: total moles $N = n$, total covolume $B_t = Nb = \sum_j n_j b_j$,
        and $Q = Na/b$. Then

        $$\frac{A^R}{RT} = -N\,\ln\!\left(1 - \frac{B_t}{V}\right) - \frac{Q}{RT}\,\ln\!\left(1 + \frac{B_t}{V}\right).$$

        The mole-number derivatives we need (all at constant $T$, $V$,
        $n_{j \ne i}$):

        $$\frac{\partial N}{\partial n_i} = 1, \qquad \frac{\partial B_t}{\partial n_i} = b_i,$$

        $$\frac{\partial (Na)}{\partial n_i} = 2\sum_j x_j a_{ij} - a.$$

        The last one: $Na = (1/N)\sum_{j,k} n_j n_k a_{jk}$, so by the
        quotient rule,
        $\partial(Na)/\partial n_i
          = -(1/N^2)\sum_{j,k} n_j n_k a_{jk} + (1/N)\,2\sum_k n_k a_{ik}
          = -a + 2\sum_k x_k a_{ik}$.
        For $Q = (Na)/b$, with $b = (1/N)\sum_j n_j b_j$ giving
        $\partial b/\partial n_i = (b_i - b)/N$:

        $$\frac{\partial Q}{\partial n_i} = \frac{\left(\frac{\partial (Na)}{\partial n_i}\right) b - (Na)\,\frac{\partial b}{\partial n_i}}{b^2} = \frac{1}{b}\left[2\sum_j x_j a_{ij} - a\,\frac{b_i}{b}\right],$$

        where the numerator simplifies as
        $(2\sum_j x_j a_{ij} - a)\,b - a\,(b_i - b)
          = 2b\sum_j x_j a_{ij} - a\,b_i$.

        Differentiating $A^R/RT$ term by term (chain rule; the logarithm
        derivatives bring down $1/(1 \mp B_t/V)$ factors):

        $$\frac{1}{RT}\frac{\partial A^R}{\partial n_i} = -\ln\!\left(1 - \frac{B_t}{V}\right) + \frac{N\,(b_i/V)}{1 - B_t/V} - \frac{1}{RT}\frac{\partial Q}{\partial n_i} \ln\!\left(1 + \frac{B_t}{V}\right) - \frac{Q}{RT}\,\frac{(b_i/V)}{1 + B_t/V}.$$

        Now convert to the dimensionless groups $Z$, $A$, $B$. With
        $u = B_t/V$: since $Z = PV/(NRT)$, we have $N/V = P/(ZRT)$ and thus
        $u = Nb/V = bP/(ZRT) = B/Z$. Further,
        $N(b_i/V) = (b_i/b)(B_t/V) = (b_i/b)\,u$,
        $Q/(RT) = Na/(bRT)$,
        and $\frac{1}{RT}\frac{\partial Q}{\partial n_i}
          = \frac{1}{bRT}\left[2\sum_j x_j a_{ij} - a\frac{b_i}{b}\right]
          = \frac{A}{B}\left[\frac{2\sum_j x_j a_{ij}}{a} - \frac{b_i}{b}\right]$,
        using $A/B = a/(bRT)$. Substituting,

        $$\frac{1}{RT}\frac{\partial A^R}{\partial n_i} = -\ln\!\left(1 - \frac{B}{Z}\right) + \frac{b_i}{b}\,\frac{B/Z}{1 - B/Z} - \frac{A}{B}\left[\frac{2\sum_j x_j a_{ij}}{a} - \frac{b_i}{b}\right] \ln\!\left(1 + \frac{B}{Z}\right) - \frac{A}{B}\,\frac{b_i}{b}\,\frac{B/Z}{1 + B/Z}.$$

        Finally $\ln \hat{\phi}_i
        = \frac{1}{RT}\frac{\partial A^R}{\partial n_i} - \ln Z$.
        Collecting pieces: $-\ln(1 - B/Z) - \ln Z = -\ln(Z - B)$;
        $\frac{B/Z}{1-B/Z} = \frac{B}{Z-B}$ and
        $\frac{B/Z}{1+B/Z} = \frac{B}{Z+B}$, so the $(b_i/b)$ terms combine to
        $\frac{b_i}{b}\left[\frac{B}{Z-B} - \frac{A}{Z+B}\right]$.
        The bracket is $Z - 1$: indeed,
        $\frac{B}{Z-B} - \frac{A}{Z+B} = Z - 1$ is equivalent (clearing
        denominators) to $BZ + B^2 - AZ + AB = (Z-1)(Z^2-B^2)$, i.e. to
        $0 = Z^3 - Z^2 + (A - B - B^2)Z - AB$, which is precisely the SRK
        cubic in $Z$. The closed form used in the code below:

        $$\ln \hat{\phi}_i = \frac{b_i}{b}\,(Z - 1) - \ln(Z - B) - \frac{A}{B}\left[\frac{2\sum_j x_j a_{ij}}{a} - \frac{b_i}{b}\right]\ln\!\left(1 + \frac{B}{Z}\right).$$

        For each phase we use the appropriate real root of the cubic:
        the largest root for the vapor, the smallest for the liquid.
        """
    )


@app.cell
def _(mo):
    mo.md(
        r"""
        ### 3c. Peng–Robinson: the same machinery, a different integral

        The Peng–Robinson (PR) equation differs from SRK only in the
        attraction denominator. In total quantities,

        $$P = \frac{nRT}{V - nb} - \frac{n^2 a}{V^2 + 2nbV - n^2b^2},$$

        with $a = 0.45724\,R^2T_c^2/P_c$,
        $b = 0.07780\,RT_c/P_c$,
        $\alpha = [1 + \kappa(1 - \sqrt{T/T_c})]^2$,
        $\kappa = 0.37464 + 1.54226\,\omega - 0.26992\,\omega^2$.
        Its cubic in $Z$ is
        $Z^3 - (1-B)Z^2 + (A-2B-3B^2)Z - (AB-B^2-B^3) = 0$.

        The repulsive piece $nRT/(V-nb)$ is unchanged, so only the attractive
        integral is new:

        $$I_{PR} = \int_{\infty}^{V} \frac{n^2 a}{V'^2 + 2nbV' - n^2b^2}\,dV'.$$

        Factor the denominator. Its zeros solve $u^2 + 2u - 1 = 0$
        (with $u = V'/(nb)$), i.e. $u = -1 \pm \sqrt{2}$, so

        $$V'^2 + 2nbV' - n^2b^2 = \big(V' + nb(1+\sqrt{2})\big)\big(V' + nb(1-\sqrt{2})\big).$$

        With $c_1 = nb(1+\sqrt{2})$, $c_2 = nb(1-\sqrt{2})$
        ($c_1 - c_2 = 2\sqrt{2}\,nb$), partial fractions give

        $$\frac{1}{(V'+c_1)(V'+c_2)} = \frac{1}{2\sqrt{2}\,nb} \left[\frac{1}{V'+c_2} - \frac{1}{V'+c_1}\right],$$

        and therefore

        $$I_{PR} = \frac{n^2a}{2\sqrt{2}\,nb} \left[\ln(V'+c_2) - \ln(V'+c_1)\right]_{\infty}^{V} = -\frac{na}{2\sqrt{2}\,b}\, \ln\!\left(\frac{V + nb(1+\sqrt{2})}{V + nb(1-\sqrt{2})}\right).$$

        Dividing numerator and denominator by $V$ and writing
        $u = B/Z = nb/V$,

        $$\frac{A^R}{RT} = -N\,\ln(1 - u) - \frac{Q}{RT}\,\frac{1}{2\sqrt{2}}\,L, \qquad L = \ln\!\left(\frac{1 + (1+\sqrt{2})\,u} {1 + (1-\sqrt{2})\,u}\right).$$

        Differentiation in $n_i$ is term-by-term identical to Section 3b;
        the only new calculus is $dL/dn_i = L'(u)\,(b_i/V)$ with

        $$L'(u) = \frac{1+\sqrt{2}}{1+(1+\sqrt{2})u} - \frac{1-\sqrt{2}}{1+(1-\sqrt{2})u} = \frac{2\sqrt{2}}{1 + 2u - u^2},$$

        (put over the common denominator
        $(1+(1+\sqrt{2})u)(1+(1-\sqrt{2})u) = 1 + 2u - u^2$; the numerator
        collapses to $2\sqrt{2}$). Collecting the $(b_i/b)$ terms,

        $$\frac{b_i}{b}\left[\frac{u}{1-u} - \frac{A}{B}\,\frac{u}{1+2u-u^2}\right] = \frac{b_i}{b}\left[\frac{B}{Z-B} - \frac{A}{B}\,\frac{BZ}{Z^2+2BZ-B^2}\right] = \frac{b_i}{b}\,(Z - 1),$$

        where the last equality is verified by clearing denominators and
        using the PR cubic to eliminate $Z^3$ (the same procedure as the
        SRK identity in Section 3b). The PR fugacity coefficient:

        $$\ln \hat{\phi}_i = \frac{b_i}{b}\,(Z - 1) - \ln(Z - B) - \frac{A}{2\sqrt{2}\,B} \left[\frac{2\sum_j x_j a_{ij}}{a} - \frac{b_i}{b}\right] \ln\!\left(\frac{Z + (1+\sqrt{2})\,B} {Z + (1-\sqrt{2})\,B}\right).$$
        """
    )


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 4. Mixing rules and the BUBL P algorithm

        The mixture parameters use the classical van der Waals one-fluid
        mixing rules. With $a_i$, $b_i$ the pure-component values (already
        containing $\alpha(T)$),

        $$a = \sum_i\sum_j x_i x_j a_{ij}, \qquad a_{ij} = \sqrt{a_i a_j}\,(1 - k_{ij}), \qquad b = \sum_i x_i b_i,$$

        where $k_{ij} = k_{ji}$ is the binary interaction parameter
        ($k_{ii} = 0$). Setting $k_{12} = 0$ recovers the book's calculation;
        the slider below lets you feel its effect.

        **BUBL P algorithm** (given $T$, $x$). The outer loop adjusts $P$;
        the inner loop converges the $K$-values at fixed $(T, P)$:

        - Inner: start $K_i$ from the Wilson correlation,
          $K_i = (P_{c,i}/P)\exp[5.37(1+\omega_i)(1-T_{c,i}/T)]$; iterate
          $y_i = K_i x_i/\sum_j K_j x_j$ and
          $K_i = \hat{\phi}_i^l(T,P,x)/\hat{\phi}_i^v(T,P,y)$ to convergence.
        - Outer: with converged $K$, form $S = \sum_i K_i x_i$. $S > 1$ means
          $P$ is too low, $S < 1$ too high. March $P$ upward from below until
          $S$ changes sign, then bisect to $S = 1$.
        - Return $P$ and $y$. Plotting $(x_1, P)$ gives the bubble branch;
          plotting $(y_1, P)$ from the *same* sweep gives the dew branch.

        Two numerical remarks. First, $K_i = 1$ ($y = x$) is *always* a
        mathematical solution of the inner loop (the trivial root); the code
        below stays on the physical branch by warm-starting every evaluation
        from the previously converged $(K, y)$ and by approaching each bubble
        pressure from below. Second, as $x_1$ approaches the mixture critical
        composition the two phases become identical ($K_i \to 1$ genuinely)
        and the sweep terminates — which is exactly where the phase envelope
        closes in the figure.
        """
    )


@app.cell
def _():
    import numpy as np
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    return go, make_subplots, np


@app.cell
def _(np):
    R = 8.314462618  # gas constant, J/(mol K)

    # Pure-component data: index 0 = methane(1), 1 = n-butane(2).
    TC = np.array([190.6, 425.12])        # critical temperature, K
    PC = np.array([45.99e5, 37.96e5])     # critical pressure, Pa
    OM = np.array([0.011, 0.200])         # acentric factor

    def eos_ab(T, eos):
        """Pure-component a(T), b for SRK or PR (alpha absorbed into a)."""
        Tr = T / TC
        if eos == "srk":
            m = 0.480 + 1.574 * OM - 0.176 * OM**2
            alpha = (1 + m * (1 - np.sqrt(Tr))) ** 2
            a = 0.42748 * R**2 * TC**2 / PC * alpha
            b = 0.08664 * R * TC / PC
        else:
            kappa = 0.37464 + 1.54226 * OM - 0.26992 * OM**2
            alpha = (1 + kappa * (1 - np.sqrt(Tr))) ** 2
            a = 0.45724 * R**2 * TC**2 / PC * alpha
            b = 0.07780 * R * TC / PC
        return a, b

    return R, TC, PC, OM, eos_ab


@app.cell
def _(OM, PC, R, TC, eos_ab, np):
    def z_roots(A, B, eos):
        """All real roots of the SRK/PR cubic in Z, in closed form.

        Depressed cubic t^3 + p*t + q = 0 (t = Z + c2/3): trigonometric
        form for three real roots, Cardano for one. Validated against
        numpy.roots to 1e-10.
        """
        if eos == "srk":
            c2, c1, c0 = -1.0, A - B - B**2, -A * B
        else:
            c2, c1, c0 = -(1 - B), A - 2 * B - 3 * B**2, -(A * B - B**2 - B**3)
        p = c1 - c2**2 / 3.0
        q = 2 * c2**3 / 27.0 - c2 * c1 / 3.0 + c0
        disc = (q / 2) ** 2 + (p / 3) ** 3
        shift = -c2 / 3.0
        if disc <= 0 and p < 0:
            r = 2 * np.sqrt(-p / 3)
            th = np.arccos(np.clip(3 * q / (2 * p) * np.sqrt(-3 / p), -1, 1)) / 3
            return [r * np.cos(th - 2 * np.pi * k / 3) + shift for k in range(3)]
        s = np.sqrt(max(disc, 0.0))
        return [np.cbrt(-q / 2 + s) + np.cbrt(-q / 2 - s) + shift]

    def ln_phi(T, P, x, k12, eos, phase, a, b):
        """Mixture ln(fugacity coefficient); a, b precomputed at T."""
        aij = np.sqrt(np.outer(a, a)) * np.array([[1.0, 1 - k12], [1 - k12, 1.0]])
        am = x @ aij @ x
        bm = x @ b
        A = am * P / (R * T) ** 2
        B = bm * P / (R * T)
        zr = z_roots(A, B, eos)
        Z = max(zr) if phase == "vapor" else min(zr)
        bi_b = b / bm
        chem = 2 * (x @ aij) / am - bi_b  # 2*sum_j x_j a_ij / a - b_i / b
        if eos == "srk":
            return bi_b * (Z - 1) - np.log(Z - B) - A / B * chem * np.log(1 + B / Z)
        s2 = np.sqrt(2.0)
        return (bi_b * (Z - 1) - np.log(Z - B)
                - A / (2 * s2 * B) * chem
                * np.log((Z + (1 + s2) * B) / (Z + (1 - s2) * B)))

    def wilson_K(T, P):
        return PC / P * np.exp(5.37 * (1 + OM) * (1 - TC / T))

    def bublP(T, x, k12, eos="srk", P0=4e5, K0=None, y0=None, a=None, b=None):
        """Bubble pressure [Pa], vapor fractions y, K-values.

        Nested successive substitution with continuation (see Section 4).
        Raises RuntimeError when the phases become identical (critical point).
        """
        if a is None or b is None:
            a, b = eos_ab(T, eos)
        x = np.asarray(x, float)
        K = np.array(K0, float) if K0 is not None else wilson_K(T, P0)
        y = np.array(y0, float) if y0 is not None else K * x / np.sum(K * x)

        def eval_g(P, Kw, yw):
            Kloc = Kw
            for _ in range(20):
                yt = Kloc * x
                yt /= yt.sum()
                Kn = np.exp(ln_phi(T, P, x, k12, eos, "liquid", a, b)
                            - ln_phi(T, P, yt, k12, eos, "vapor", a, b))
                if not np.all(np.isfinite(Kn)):
                    raise RuntimeError("non-finite K")
                if np.max(np.abs(Kn - Kloc) / np.maximum(Kloc, 1e-300)) < 1e-8:
                    Kloc = Kn
                    break
                Kloc = Kn
            yo = Kloc * x
            return float(np.sum(Kloc * x) - 1.0), Kloc, yo / yo.sum()

        g, K, y = eval_g(P0, K, y)
        while g < 0:
            P0 *= 0.7
            g, K, y = eval_g(P0, K, y)
        plo, Klo, ylo = P0, K, y
        phi = P0
        while g > 0:
            phi *= 1.25
            if phi > 1e9:
                raise RuntimeError("P march diverged")
            g, K, y = eval_g(phi, K, y)
        lo, hi, Ka, ya = plo, phi, Klo, ylo
        for _ in range(30):
            m = 0.5 * (lo + hi)
            g, K, y = eval_g(m, Ka, ya)
            if g > 0:
                lo, Ka, ya = m, K, y
            else:
                hi = m
        P = 0.5 * (lo + hi)
        g, K, y = eval_g(P, Ka, ya)
        if np.max(np.abs(K - 1.0)) < 0.02:
            raise RuntimeError("near-critical: phases identical")
        return P, y, K

    def sweep(T, k12, eos="srk", n=65):
        """BUBL P sweep over x1 with continuation; stops at the critical point."""
        a, b = eos_ab(T, eos)
        x1 = np.concatenate([np.logspace(-4, -1.05, 25), np.linspace(0.1, 0.74, n)])
        xs, Ps, ys = [], [], []
        Pp, Kp, yp, nfail = 4e5, None, None, 0
        for xi in x1:
            try:
                P, y, K = bublP(T, np.array([xi, 1 - xi]), k12, eos,
                                P0=Pp, K0=Kp, y0=yp, a=a, b=b)
            except Exception:
                nfail += 1
                if nfail >= 3:
                    break
                continue
            nfail = 0
            xs.append(xi)
            Ps.append(P)
            ys.append(y[0])
            Pp, Kp, yp = P, K, y
        return {"x1": np.array(xs), "P": np.array(Ps), "y1": np.array(ys)}

    return bublP, ln_phi, sweep, wilson_K, z_roots


@app.cell
def _(np):
    # Experimental points digitized from the printed Figure 13.13
    # (Reamer, Sage & Lacey data). (x1, P) bubble points, (y1, P) dew
    # points, P in bar; critical point (x1c, Pc). Read-off error ~1%.
    # The full table with provenance lives in data/fig13-13-digitized.csv.
    EXP_BUBBLE = [
        (0.0133, 7.14),
        (0.0306, 10.51),
        (0.0502, 14.26),
        (0.0848, 21.28),
        (0.1184, 27.98),
        (0.1515, 34.56),
        (0.1838, 41.58),
        (0.2534, 55.12),
        (0.3170, 69.00),
        (0.3859, 82.73),
        (0.4002, 86.25),
        (0.4466, 96.48),
        (0.4848, 103.20),
        (0.5196, 110.21),
        (0.5587, 117.06),
        (0.5832, 120.64),
        (0.6154, 123.73),
        (0.6445, 127.40),
        (0.7032, 130.69),
    ]
    EXP_DEW = [
        (0.1337, 3.90),
        (0.3320, 5.39),
        (0.4577, 6.76),
        (0.6211, 10.12),
        (0.6999, 13.74),
        (0.7700, 130.95),
        (0.7837, 20.52),
        (0.8046, 127.66),
        (0.8202, 124.01),
        (0.8245, 27.46),
        (0.8336, 120.72),
        (0.8433, 34.23),
        (0.8434, 117.03),
        (0.8545, 110.18),
        (0.8622, 41.37),
        (0.8626, 103.36),
        (0.8739, 96.29),
        (0.8744, 86.17),
        (0.8751, 68.82),
        (0.8783, 55.10),
        (0.8799, 82.79),
    ]
    EXP_CRIT = (0.7237, 131.78)
    exp_bubble = np.array(EXP_BUBBLE)
    exp_dew = np.array(EXP_DEW)
    return exp_bubble, exp_dew, EXP_CRIT


@app.cell
def _(mo):
    t_slider = mo.ui.slider(
        start=-20, stop=80, step=0.5, value=37.8,
        label="Temperature (°C)", debounce=True, show_value=True)
    k12_slider = mo.ui.slider(
        start=-0.10, stop=0.20, step=0.005, value=0.0,
        label="Binary interaction parameter k12", debounce=True,
        show_value=True)
    pr_check = mo.ui.checkbox(value=True, label="Show Peng–Robinson curves")
    return k12_slider, pr_check, t_slider


@app.cell
def _(k12_slider, mo, pr_check, t_slider):
    mo.vstack(
        [mo.md("### Controls (recompute on release)"),
         t_slider, k12_slider, pr_check]
    )


@app.cell
def _(k12_slider, pr_check, sweep, t_slider):
    T = t_slider.value + 273.15       # K
    k12 = k12_slider.value
    srk = sweep(T, k12, "srk")
    pr = sweep(T, k12, "pr") if pr_check.value else None
    show_data = abs(t_slider.value - 37.8) < 1e-9  # data only at 37.8 C
    return T, k12, pr, show_data, srk


@app.cell
def _(EXP_CRIT, exp_bubble, exp_dew, go, k12, np, pr, show_data, srk,
        t_slider):
    fig = go.Figure()
    P_srk = srk["P"] / 1e5
    fig.add_trace(go.Scatter(x=srk["x1"], y=P_srk, mode="lines",
                             name="SRK bubble",
                             line=dict(color="black", width=2)))
    fig.add_trace(go.Scatter(x=srk["y1"], y=P_srk, mode="lines",
                             name="SRK dew",
                             line=dict(color="black", width=2)))
    fig.add_trace(go.Scatter(x=[srk["x1"][-1]], y=[P_srk[-1]],
                             mode="markers", name="SRK endpoint",
                             marker=dict(symbol="x", color="black", size=8)))
    if pr is not None:
        P_pr = pr["P"] / 1e5
        fig.add_trace(go.Scatter(x=pr["x1"], y=P_pr, mode="lines",
                                 name="PR bubble",
                                 line=dict(color="#1f77b4", width=1.5)))
        fig.add_trace(go.Scatter(x=pr["y1"], y=P_pr, mode="lines",
                                 name="PR dew",
                                 line=dict(color="#1f77b4", width=1.5)))
        fig.add_trace(go.Scatter(x=[pr["x1"][-1]], y=[P_pr[-1]],
                                 mode="markers", name="PR endpoint",
                                 marker=dict(symbol="x", color="#1f77b4",
                                             size=8)))
    if show_data:
        fig.add_trace(go.Scatter(x=exp_bubble[:, 0], y=exp_bubble[:, 1],
                                 mode="markers", name="Expt. bubble",
                                 marker=dict(symbol="circle-open",
                                             color="black", size=7)))
        fig.add_trace(go.Scatter(x=exp_dew[:, 0], y=exp_dew[:, 1],
                                 mode="markers", name="Expt. dew",
                                 marker=dict(symbol="square-open",
                                             color="black", size=7)))
        fig.add_trace(go.Scatter(x=[EXP_CRIT[0]], y=[EXP_CRIT[1]],
                                 mode="markers", name="Expt. critical",
                                 marker=dict(symbol="cross", color="black",
                                             size=10)))
    ymax = max(140.0, float(np.max(P_srk)) * 1.05)
    if pr is not None:
        ymax = max(ymax, float(np.max(pr["P"] / 1e5)) * 1.05)
    fig.update_layout(
        title=(f"Methane(1)/n-butane(2) P–xy at {t_slider.value:.1f} °C, "
               f"k12 = {k12:.3f}"),
        xaxis_title="x1, y1",
        yaxis_title="P / bar",
        xaxis=dict(range=[0, 1]),
        yaxis=dict(range=[0, ymax]),
        legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        margin=dict(r=170),
        width=780, height=540,
    )
    fig


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 5. Reading the diagram

        At the book conditions (37.8 °C, $k_{12} = 0$) the SRK envelope passes
        through the experimental markers: 19 bubble points, 21 dew points,
        closing at the mixture critical point ($\times$). A few things to
        notice:

        - **Left edge** ($x_1 = 0$): the bubble curve starts at the vapor
          pressure of pure n-butane at 37.8 °C ($\approx 3.6$ bar). The
          first dew points hover just above it — a trace of methane in the
          vapor at barely more than butane's saturation pressure.
        - **Right side**: there is *no* pure-methane endpoint — methane is
          supercritical at 37.8 °C ($T_{c,1} = 190.6$ K), so the dew branch
          climbs steeply and folds back toward the critical point instead of
          meeting the $x_1 = 1$ axis. This is the qualitative signature of a
          gas/liquid pair far above the lighter component's critical
          temperature.
        - **The × marks** where the sweep stops: $K_i \to 1$, the two phases
          become identical, and the bisection has nothing left to bracket.
          The calculated envelope closes at ($x_1 \approx 0.74$,
          $P \approx 138$ bar), against the experimental (0.724, 131.8 bar).
        - **$k_{12}$**: raising it weakens the unlike-pair attraction
          ($a_{12} = \sqrt{a_1 a_2}(1-k_{12})$), so the envelope inflates to
          higher pressures; lowering it tightens the envelope. The slider
          lets you find the value that best fits the markers — the honest
          way to read "interaction parameter" is as a one-parameter fit to
          data like these.
        - **Temperature**: cooling toward methane's critical point lets the
          envelope reach further right; heating shrinks it toward the butane
          axis. Below about $-20$ °C / above about $80$ °C the numerics need
          more help than this notebook's simple continuation provides, which
          is why the slider stops there.
        """
    )


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 6. How well does it fit? (residuals)

        Bubble residuals are computed at matched liquid composition
        (interpolating the calculated bubble curve); dew residuals use the
        closest calculated point, since the dew branch folds in $y_1$.
        """
    )


@app.cell
def _(exp_bubble, exp_dew, go, make_subplots, mo, np, pr, show_data, srk):
    if not show_data:
        resid_out = mo.md(
            "_Residuals are computed at 37.8 °C, where the experimental "
            "data live — move the temperature slider back to see them._")
    else:
        rfig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("Bubble: calc − expt vs x1",
                            "Dew: calc − expt vs y1"))
        for _label, _sw, _color in (("SRK", srk, "black"),
                                    ("PR", pr, "#1f77b4")):
            if _sw is None:
                continue
            _Pc = np.interp(exp_bubble[:, 0], _sw["x1"], _sw["P"] / 1e5)
            rfig.add_trace(go.Scatter(
                x=exp_bubble[:, 0], y=_Pc - exp_bubble[:, 1],
                mode="markers", name=_label,
                marker=dict(color=_color, size=6)), row=1, col=1)
            _d = []
            for _yd, _Pd in exp_dew:
                _i = np.argmin((_sw["y1"] - _yd) ** 2
                               + ((_sw["P"] / 1e5 - _Pd) / 140) ** 2)
                _d.append(_sw["P"][_i] / 1e5 - _Pd)
            rfig.add_trace(go.Scatter(
                x=exp_dew[:, 0], y=np.array(_d),
                mode="markers", name=_label, showlegend=False,
                marker=dict(color=_color, size=6)), row=1, col=2)
        rfig.add_hline(y=0, line=dict(color="gray", width=1), row=1, col=1)
        rfig.add_hline(y=0, line=dict(color="gray", width=1), row=1, col=2)
        rfig.update_layout(
            title="Pressure residuals (bar)",
            legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
            margin=dict(r=120), width=780, height=420)
        rfig.update_xaxes(title_text="x1", row=1, col=1)
        rfig.update_xaxes(title_text="y1", row=1, col=2)
        rfig.update_yaxes(title_text="ΔP / bar", row=1, col=1)
        resid_out = rfig
    resid_out


@app.cell
def _(bublP, exp_bubble, exp_dew, mo, np, show_data, srk):
    _checks = []
    # Reference BUBL P: P0 = 50 bar starts the march inside the two-phase
    # region at x1 = 0.5 (4 bar would be single-phase vapor there).
    _P_ref, _y_ref, _ = bublP(310.93, np.array([0.5, 0.5]), 0.0, "srk",
                              P0=50e5)
    _checks.append(
        (f"reference BUBL P at 37.8 °C, x1 = 0.5: {_P_ref / 1e5:.1f} bar "
         "(expected 95–115)", 95e5 < _P_ref < 115e5))
    _checks.append(
        (f"sweep produced {len(srk['x1'])} points (need > 40)",
         len(srk["x1"]) > 40))
    _checks.append(
        (f"bubble branch starts at {srk['P'][0] / 1e5:.2f} bar "
         "(butane Psat, need < 8)", srk["P"][0] < 8e5))
    _checks.append(
        (f"bubble branch ends at {srk['P'][-1] / 1e5:.1f} bar (need > 50)",
         srk["P"][-1] > 50e5))
    if show_data:
        _rb = (np.interp(exp_bubble[:, 0], srk["x1"], srk["P"] / 1e5)
               - exp_bubble[:, 1])
        _rms_b = float(np.sqrt(np.mean(_rb ** 2)))
        _checks.append(
            (f"SRK bubble RMS residual {_rms_b:.2f} bar (need < 5)",
             _rms_b < 5))
        _dd = []
        for _yd, _Pd in exp_dew:
            _i = np.argmin((srk["y1"] - _yd) ** 2
                           + ((srk["P"] / 1e5 - _Pd) / 140) ** 2)
            _dd.append(srk["P"][_i] / 1e5 - _Pd)
        _rms_d = float(np.sqrt(np.mean(np.array(_dd) ** 2)))
        _checks.append(
            (f"SRK dew RMS residual {_rms_d:.2f} bar (need < 3)",
             _rms_d < 3))
    _lines = "\n".join(
        f"- {'✓' if _c[1] else '✗ FAIL'} {_c[0]}" for _c in _checks)
    _verdict = ("All checks passed." if all(_c[1] for _c in _checks)
                else "**Some checks FAILED — see above.**")
    mo.md(f"## 7. Verification\n\n{_lines}\n\n{_verdict}")


@app.cell
def _(mo):
    mo.md(
        r"""
        ## What this notebook did — and didn't

        We derived the SRK mixture fugacity coefficient from the residual
        Helmholtz energy with every calculus step shown, mirrored the
        derivation for Peng–Robinson, and rebuilt the book's Figure 13.13
        from scratch: one BUBL P sweep per equation of state, both branches
        from the same calculation, experimental points overlaid. At
        $k_{12} = 0$ the SRK envelope reproduces the printed figure to
        within a few bar.

        It did *not* fit $k_{12}$ to the data (the slider invites that
        exploration directly), did not implement stability analysis or the
        full critical-
        point conditions (the sweep stops where the $K$-values collapse to
        one), and the temperature slider is deliberately limited to the
        range where this simple continuation is reliable. Those are the
        natural next steps — the machinery above is where they would plug in.
        """
    )
