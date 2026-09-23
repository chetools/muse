"""Theory panel content: step-by-step derivations.

Each section is (title, blocks, function_name_in_physics) where blocks is a
list of ("md", markdown_text) and ("tex", latex_string) tuples.  Display
equations go through st.latex (direct KaTeX, no markdown interference);
prose with inline $...$ math goes through st.markdown.  The app renders the
*actual* source of the corresponding physics function (via inspect) beside
each section, so equations and code can never drift apart.
"""

SECTIONS = [
    (
        "1. Model setup",
        [
            ("md",
             "**System.** A tube of total volume $V$ carries a steady "
             "volumetric flow $Q$. Its mean residence time is $\\tau = V/Q$."),
            ("tex", r"\tau = \frac{V}{Q}"),
            ("md",
             "**Approximation.** Replace the tube by $N$ equal, perfectly "
             "mixed tanks in series. Each tank has volume $V_i = V/N$ and "
             "residence time"),
            ("tex", r"\tau_i = \frac{V}{Q}\cdot\frac{1}{N} = \frac{\tau}{N}"),
            ("md",
             "**Assumptions.** Incompressible flow, constant $Q$, passive "
             "tracer (no reaction, no adsorption), isothermal, each tank "
             "perfectly mixed so the outlet concentration of tank $i$ equals "
             "its bulk concentration $C_i$.\n\n"
             "**Feed.** A rectangular tracer pulse of height $C_p$ and width "
             "$t_p$ enters tank 1:"),
            ("tex",
             r"C_0(t) = \begin{cases} C_p & 0 \le t \le t_p \\"
             r" 0 & \text{otherwise} \end{cases}"),
            ("md",
             "The injected tracer mass is $M = Q\\,C_p\\,t_p$."),
        ],
        "rectangular_pulse",
    ),
    (
        "2. Component balance on tank i",
        [
            ("md",
             "Write the unsteady tracer balance over tank $i$ (in $-$ out "
             "$=$ accumulation; no reaction):"),
            ("tex",
             r"\frac{d}{dt}(V_i C_i) = Q\,(C_{i-1} - C_i)"),
            ("md",
             "$V_i$ is constant, so divide by $V_i = V/N$ and use "
             "$\\tau = V/Q$:"),
            ("tex",
             r"\boxed{\frac{dC_i}{dt} = \frac{N}{\tau}\,"
             r"\big(C_{i-1} - C_i\big)}, \qquad i = 1 \dots N"),
            ("md",
             "with $C_0(t)$ the pulse above and $C_i(0) = 0$. This is a "
             "linear system of $N$ ODEs. In vector form, with "
             "$\\mathbf{C} = (C_1, \\dots, C_N)^T$:"),
            ("tex",
             r"\frac{d\mathbf{C}}{dt} = \frac{N}{\tau}\,"
             r"(S\,\mathbf{C} + \mathbf{e}_1\, C_0(t))"),
            ("md",
             "where $S$ is the shift-minus-identity matrix ($S_{i,i} = -1$, "
             "$S_{i,i-1} = +1$). The code builds the right-hand side without "
             "ever forming $S$: the feed vector is `pulse` in row 0 and the "
             "previous tank's concentration in every other row — a fully "
             "vectorized $O(N)$ evaluation."),
        ],
        "rhs",
    ),
    (
        "3. Numerical integration",
        [
            ("md",
             "The system is integrated with `scipy.integrate.solve_ivp` "
             "using the **Radau** method (implicit Runge–Kutta, L-stable). "
             "Two reasons:\n\n"
             "1. The fastest mode decays at rate $N/\\tau$ (up to "
             "$200/\\tau$ here), so the system is mildly stiff at large "
             "$N$ — an implicit method stays stable with large steps.\n"
             "2. `vectorized=True` lets the RHS evaluate all $N$ components "
             "at once.\n\n"
             "The feed has a kink at $t = t_p$ where the pulse switches off. "
             "Integrating straight across it makes the solver's interpolant "
             "overshoot and leak spurious mass, so the integration is split "
             "into a pulse-on phase $[0, t_p]$ and a pulse-off phase "
             "$[t_p, t_\\mathrm{end}]$, stitched at $t_p$.\n\n"
             "The time grid pins the pulse edges $t = 0$ and $t = t_p$ so "
             "the discontinuities are resolved exactly, and extends to "
             "$\\tau + t_p + 5\\tau$ so the $N = 1$ exponential tail (down "
             "to $e^{-5}$) is captured."),
        ],
        "simulate",
    ),
    (
        "4. Residence-time distribution of N tanks in series",
        [
            ("md",
             "Take Laplace transforms of the tank balances with a "
             "unit-impulse feed. One tank gives $G_1(s) = 1/(1 + \\tau_i s)$; "
             "$N$ identical tanks in series multiply:"),
            ("tex", r"G_N(s) = \left(1 + \frac{\tau s}{N}\right)^{-N}"),
            ("md",
             "The inverse Laplace transform is the Erlang (gamma) "
             "distribution:"),
            ("tex",
             r"\boxed{E(t) = \frac{(N/\tau)^N}{(N-1)!}\; t^{N-1}\,"
             r"e^{-Nt/\tau}}, \qquad t \ge 0"),
            ("md", "with mean and variance"),
            ("tex", r"\bar t = \tau, \qquad \sigma^2 = \frac{\tau^2}{N}"),
            ("md",
             "For large $N$ the code evaluates $E(t)$ in log space "
             "($\\log E = N\\log(N/\\tau) + (N-1)\\log t - Nt/\\tau - "
             "\\log\\Gamma(N)$) so that neither $(N/\\tau)^N$ nor $(N-1)!$ "
             "overflows."),
        ],
        "rtd_gamma",
    ),
    (
        "5. Exact response to the rectangular pulse",
        [
            ("md",
             "The effluent is the convolution of the feed with the RTD:"),
            ("tex",
             r"C_N(t) = \int_0^t C_0(t-s)\,E(s)\,ds"),
            ("md",
             "For the rectangular pulse $C_0 = C_p$ on $[0, t_p]$, the "
             "integral is a difference of two gamma CDFs $F(t)$ (shape $N$, "
             "scale $\\tau/N$):"),
            ("tex", r"\boxed{C_N(t) = C_p\,\big[\,F(t) - F(t - t_p)\,\big]}"),
            ("md",
             "This closed form is the independent check on the numerics "
             "(see the \"Plug-flow limit\" tab). Variances add under "
             "convolution, so the effluent variance is the RTD variance "
             "plus the pulse's own variance $t_p^2/12$:"),
            ("tex",
             r"\sigma^2_{\text{effluent}} = "
             r"\frac{\tau^2}{N} + \frac{t_p^2}{12}"),
        ],
        "analytical_pulse_response",
    ),
    (
        "6. Plug-flow limit (N → ∞)",
        [
            ("md", "Let $N \\to \\infty$ in the transfer function:"),
            ("tex",
             r"\lim_{N\to\infty}\left(1 + \frac{\tau s}{N}\right)^{-N}"
             r" = e^{-\tau s}"),
            ("md",
             "Multiplication by $e^{-\\tau s}$ in Laplace domain is a "
             "**pure time delay** $\\tau$ in the time domain. Hence the "
             "effluent tends to the feed shifted by $\\tau$, with zero "
             "broadening:"),
            ("tex",
             r"\boxed{C_N(t) \;\xrightarrow[N\to\infty]{}\;"
             r"C_0(t-\tau) ="
             r"\begin{cases} C_p & \tau \le t \le \tau + t_p \\"
             r" 0 & \text{otherwise} \end{cases}}"),
            ("md",
             "Consistently, $\\sigma^2 = \\tau^2/N \\to 0$: all tracer "
             "molecules spend exactly $\\tau$ in the tube. The \"Plug-flow "
             "limit\" tab verifies this by overlaying the numerical "
             "effluent at large $N$ on this rectangle and by checking that "
             "the measured variance follows $\\tau^2/N + t_p^2/12$."),
        ],
        "plug_flow_response",
    ),
    (
        "7. Moment checks",
        [
            ("md",
             "Three integral checks are evaluated on every numerical "
             "effluent curve $C_N(t)$ with the trapezoidal rule:"),
            ("tex",
             r"\int_0^\infty C_N\,dt = C_p\,t_p"
             r"\qquad\text{(mass recovery; }Q\text{ cancels)}"),
            ("tex",
             r"\bar t = \frac{\int t\,C_N\,dt}{\int C_N\,dt}"
             r" = \tau + \frac{t_p}{2}"
             r"\qquad\text{(RTD mean + pulse mean)}"),
            ("tex",
             r"\sigma^2 = \frac{\int t^2 C_N\,dt}{\int C_N\,dt} - \bar t^2"
             r" = \frac{\tau^2}{N} + \frac{t_p^2}{12}"),
            ("md",
             "Any violation flags a numerical or modelling error."),
        ],
        "effluent_moments",
    ),
]
