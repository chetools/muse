<h1>Inverse Laplace Transform Tables for a Second-Order System</h1>
<p class="subtitle">Step, sine, and cosine inputs for the overdamped, critically damped, and underdamped cases</p>

<h2 id="contents">Contents</h2>
<ol>
<li><a href="#system">System and notation</a></li>
<li><a href="#step-table">Table 1: step input</a></li>
<li><a href="#sinusoidal-setup">Sinusoidal inputs: steady-state part and initial-value constants</a></li>
<li><a href="#transient-table">Table 3: transient part and its coefficients</a></li>
<li><a href="#complete-table">Table 4: complete sinusoidal response</a></li>
<li><a href="#resonance-table">Table 5: input frequency equal to the natural frequency</a></li>
<li><a href="#plots">Illustrative plots</a></li>
<li><a href="#checks">Checks</a></li>
</ol>

<h2 id="system">1 &nbsp; System and notation</h2>
<p>The system is the second-order transfer function stated in Equation (1). All responses are computed for zero initial conditions: the output and the first derivative of the output are both zero at \(t = 0\), where \(t\) denotes time, with the unit s (second), restricted to \(t \ge 0\). Every symbol is defined in this section before its first use in an equation or a table. Symbols introduced for the sinusoidal tables are defined in Section 3, before the tables in which the symbols appear.</p>
<div class="tablewrap"><table class="notation">
<tr><th>Symbol</th><th>Definition</th><th>Unit</th></tr>
<tr><td>\(s\)</td><td>Laplace variable</td><td>s\(^{-1}\) (per second)</td></tr>
<tr><td>\(K\)</td><td>Constant gain</td><td>Output unit per input unit</td></tr>
<tr><td>\(\tau\)</td><td>Constant time constant, with \(\tau &gt; 0\)</td><td>s</td></tr>
<tr><td>\(\zeta\)</td><td>Constant damping coefficient, with \(\zeta &gt; 0\) in every case tabulated</td><td>Dimensionless</td></tr>
<tr><td>\(G(s)\)</td><td>Transfer function of the system, as a function of \(s\)</td><td>Output unit per input unit</td></tr>
<tr><td>\(u(t)\)</td><td>Input, as a function of \(t\)</td><td>Input unit</td></tr>
<tr><td>\(U(s)\)</td><td>Laplace transform of \(u(t)\)</td><td>Input unit multiplied by s</td></tr>
<tr><td>\(y(t)\)</td><td>Output (the inverse Laplace transform tabulated), as a function of \(t\)</td><td>Output unit</td></tr>
<tr><td>\(Y(s)\)</td><td>Laplace transform of \(y(t)\), equal to \(G(s)U(s)\)</td><td>Output unit multiplied by s</td></tr>
<tr><td>\(M\)</td><td>Constant magnitude of the input: the step height for the step input, and the amplitude for the sine and cosine inputs</td><td>Input unit</td></tr>
<tr><td>\(KM\)</td><td>Product of \(K\) and \(M\)</td><td>Output unit</td></tr>
<tr><td>\(\omega\)</td><td>Angular frequency of the sine or cosine input</td><td>rad/s</td></tr>
<tr><td>\(\omega_{n}\)</td><td>Natural (undamped) angular frequency of the system, equal to \(1/\tau\)</td><td>rad/s</td></tr>
<tr><td>\(q\)</td><td>Frequency ratio, equal to \(\omega/\omega_{n}\), equivalently \(\omega\tau\); the input frequency equals the natural frequency exactly when \(q = 1\)</td><td>Dimensionless</td></tr>
<tr><td>\(e\)</td><td>Base of the natural exponential function</td><td>Dimensionless</td></tr>
<tr><td>\(\cos\) and \(\sin\)</td><td>Cosine and sine trigonometric functions, with angles in radians; rad denotes the radian</td><td>Dimensionless</td></tr>
<tr><td>\(\pi\)</td><td>Ratio of the circumference of a circle to its diameter, approximately 3.14159</td><td>Dimensionless</td></tr>
<tr><td>\(\beta\)</td><td>Square root of \(\zeta^{2} - 1\); defined for the overdamped case, \(\zeta &gt; 1\)</td><td>Dimensionless</td></tr>
<tr><td>\(r_{1}\) and \(r_{2}\)</td><td>Poles of the overdamped case, equal to \(\left(-\zeta + \beta\right)/\tau\) and \(\left(-\zeta - \beta\right)/\tau\), respectively</td><td>s\(^{-1}\)</td></tr>
<tr><td>\(\delta\)</td><td>Square root of \(1 - \zeta^{2}\); defined for the underdamped case, \(0 &lt; \zeta &lt; 1\)</td><td>Dimensionless</td></tr>
<tr><td>\(\alpha\)</td><td>Exponential decay rate of the underdamped case, equal to \(\zeta/\tau\)</td><td>s\(^{-1}\)</td></tr>
<tr><td>\(\omega_{d}\)</td><td>Damped angular frequency of the underdamped case, equal to \(\delta/\tau\)</td><td>rad/s</td></tr>
</table></div>
$$G(s) = \frac{K}{\tau^{2}s^{2} + 2\zeta\tau s + 1}, \qquad \omega_{n} = \frac{1}{\tau}, \qquad q = \omega\tau \tag{1}$$

<h2 id="step-table">2 &nbsp; Table 1: step input</h2>
<p>For the step input, \(u(t) = M\) for \(t \ge 0\) and \(U(s) = M/s\), so that \(Y(s) = KM/\left[s\left(\tau^{2}s^{2} + 2\zeta\tau s + 1\right)\right]\). The derivation of Table 1 by partial fractions is given in the companion page, <i>Inverse Laplace Transform of a Second-Order Step Response</i>. The auxiliary quantities \(\beta\), \(r_{1}\), \(r_{2}\), \(\delta\), \(\alpha\), and \(\omega_{d}\) in Table 1 are those defined in Section 1.</p>
<div class="tablewrap"><table class="notation">
<tr><th>Case</th><th>Inverse transform \(y(t)\) for a step input of magnitude \(M\), \(t \ge 0\)</th></tr>
<tr><td>\(\zeta &gt; 1\) (overdamped)</td><td>\(KM\left[1 - \dfrac{\zeta + \beta}{2\beta} e^{r_{1}t} + \dfrac{\zeta - \beta}{2\beta} e^{r_{2}t}\right]\)</td></tr>
<tr><td>\(\zeta = 1\) (critically damped)</td><td>\(KM\left[1 - \left(1 + \dfrac{t}{\tau}\right)e^{-t/\tau}\right]\)</td></tr>
<tr><td>\(0 &lt; \zeta &lt; 1\) (underdamped)</td><td>\(KM\left[1 - e^{-\alpha t}\left(\cos(\omega_{d}t) + \dfrac{\zeta}{\delta}\sin(\omega_{d}t)\right)\right]\)</td></tr>
</table></div>

<h2 id="sinusoidal-setup">3 &nbsp; Sinusoidal inputs: steady-state part and initial-value constants</h2>
<p>The two sinusoidal inputs and the corresponding transforms are \(u(t) = M\cos\left(\omega t\right)\) with \(U(s) = Ms/\left(s^{2} + \omega^{2}\right)\), and \(u(t) = M\sin\left(\omega t\right)\) with \(U(s) = M\omega/\left(s^{2} + \omega^{2}\right)\). In both cases \(Y(s) = G(s)U(s)\) with \(G(s)\) from Equation (1).</p>
<p>Additional symbols for the sinusoidal tables are defined here, before first use. The output \(y(t)\) is decomposed as \(y(t) = y_{ss}(t) + y_{h}(t)\), where \(y_{ss}(t)\), with the output unit, is the steady-state (particular) part, a sinusoid at the input frequency \(\omega\) that persists as \(t\) increases, and \(y_{h}(t)\), with the output unit, is the transient (homogeneous) part, which decays to zero because \(\zeta &gt; 0\). The dimensionless quantity \(S\) is the squared magnitude denominator defined in Equation (2). The dimensionless quantity \(R\) is the steady-state amplitude ratio defined in Equation (2): the amplitude of \(y_{ss}(t)\) is \(KMR\). The quantity \(\phi\), with the unit rad, is the steady-state phase defined in Equation (2), evaluated with the two-argument arctangent function \(\mathrm{atan2}\), in which \(\mathrm{atan2}\left(v, w\right)\) denotes the angle whose tangent is \(v/w\), taken in the quadrant determined by the signs of \(v\) and \(w\); \(\phi\) is negative, corresponding to a phase lag. The dimensionless constants \(P_{0}\) and \(P_{1}\) are the initial value and the scaled initial slope of the steady-state part, defined in Equation (3); the transient coefficients in Table 3 are expressed through \(P_{0}\) and \(P_{1}\), so that one coefficient table serves both inputs and all frequencies.</p>
$$S = \left(1 - q^{2}\right)^{2} + \left(2\zeta q\right)^{2}, \qquad R = \frac{1}{\sqrt{S}}, \qquad \phi = -\mathrm{atan2}\left(2\zeta q,\; 1 - q^{2}\right) \tag{2}$$
$$P_{0} = \frac{y_{ss}(0)}{KM}, \qquad P_{1} = \frac{\tau\, y_{ss}'\left(0\right)}{KM} \tag{3}$$
<p>In Equation (3), \(y_{ss}'\left(0\right)\) denotes the first derivative of \(y_{ss}(t)\) with respect to \(t\), evaluated at \(t = 0\). The steady-state parts are</p>
$$\begin{aligned} u(t) = M\cos\left(\omega t\right): &amp; \quad y_{ss}(t) = KM\, R\cos\left(\omega t + \phi\right) \\ u(t) = M\sin\left(\omega t\right): &amp; \quad y_{ss}(t) = KM\, R\sin\left(\omega t + \phi\right) \end{aligned} \tag{4}$$
<p>Evaluation of Equation (3) for Equation (4), using \(\cos\left(\phi\right) = \left(1 - q^{2}\right)/\sqrt{S}\) and \(\sin\left(\phi\right) = -2\zeta q/\sqrt{S}\) from Equation (2), gives Table 2. The column for \(q \ne 1\) covers every input frequency different from the natural frequency; the column for \(q = 1\) is the evaluation of the same formulas at \(\omega = \omega_{n}\) and is collected separately in Table 5.</p>
<h3>Table 2: Initial-value constants \(P_{0}\) and \(P_{1}\)</h3>
<div class="tablewrap"><table class="notation">
<tr><th>Input</th><th>Constant</th><th>General frequency, \(q \ne 1\)</th><th>Resonance, \(q = 1\)</th></tr>
<tr><td rowspan="2">\(M\cos\left(\omega t\right)\)</td><td>\(P_{0}\)</td><td>\(\dfrac{1 - q^{2}}{S}\)</td><td>\(0\)</td></tr>
<tr><td>\(P_{1}\)</td><td>\(\dfrac{2\zeta q^{2}}{S}\)</td><td>\(\dfrac{1}{2\zeta}\)</td></tr>
<tr><td rowspan="2">\(M\sin\left(\omega t\right)\)</td><td>\(P_{0}\)</td><td>\(\dfrac{-2\zeta q}{S}\)</td><td>\(\dfrac{-1}{2\zeta}\)</td></tr>
<tr><td>\(P_{1}\)</td><td>\(\dfrac{q\left(1 - q^{2}\right)}{S}\)</td><td>\(0\)</td></tr>
</table></div>
<p>The formulas in the column for \(q \ne 1\) remain valid in the limit of \(q\) approaching 1 and agree with the resonance column at \(q = 1\), where \(S = 4\zeta^{2}\). Two columns are shown for the two frequency conditions; mathematically the resonance column is the evaluation of the general column, not a separate solution branch, for every \(\zeta &gt; 0\).</p>

<h2 id="transient-table">4 &nbsp; Table 3: transient part and its coefficients</h2>
<p>The transient part \(y_{h}(t)\) is fixed by the zero initial conditions of Section 1: \(y_{h}(0) = -y_{ss}(0)\) and \(y_{h}'\left(0\right) = -y_{ss}'\left(0\right)\), where \(y_{h}'\left(0\right)\) denotes the first derivative of \(y_{h}(t)\) with respect to \(t\), evaluated at \(t = 0\). Substitution of \(y_{ss}(0) = KMP_{0}\) and \(y_{ss}'\left(0\right) = \left(KM/\tau\right)P_{1}\) from Equation (3) into the homogeneous solution form of each case gives Table 3. In Table 3, \(a_{1}\) and \(a_{2}\) are dimensionless coefficients of the two exponential terms of the overdamped case. The formulas of Table 3 apply to both sinusoidal inputs and to every value of \(q\), including \(q = 1\), with \(P_{0}\) and \(P_{1}\) taken from the corresponding column of Table 2.</p>
<div class="tablewrap"><table class="notation">
<tr><th>Case</th><th>Transient part \(y_{h}(t)\)</th></tr>
<tr><td>\(\zeta &gt; 1\) (overdamped)</td><td>\(KM\left[a_{1} e^{r_{1}t} + a_{2} e^{r_{2}t}\right]\), with \(a_{1} = \dfrac{-P_{1} + \left(-\zeta - \beta\right)P_{0}}{2\beta}\) and \(a_{2} = \dfrac{-P_{1} + \left(-\zeta + \beta\right)P_{0}}{-2\beta}\)</td></tr>
<tr><td>\(\zeta = 1\) (critically damped)</td><td>\(KM\left[-P_{0} - \left(P_{1} + P_{0}\right)\dfrac{t}{\tau}\right] e^{-t/\tau}\)</td></tr>
<tr><td>\(0 &lt; \zeta &lt; 1\) (underdamped)</td><td>\(KM\, e^{-\alpha t}\left[-P_{0}\cos\left(\omega_{d}t\right) + \dfrac{-P_{1} - \zeta P_{0}}{\delta}\sin\left(\omega_{d}t\right)\right]\)</td></tr>
</table></div>

<h2 id="complete-table">5 &nbsp; Table 4: complete sinusoidal response</h2>
<p>Table 4 assembles the complete response \(y(t) = y_{ss}(t) + y_{h}(t)\) for the three cases of \(\zeta\) and the two inputs. The quantities \(R\) and \(\phi\) are those of Equation (2), \(P_{0}\) and \(P_{1}\) are taken from Table 2 (the general column for \(q \ne 1\), the resonance column for \(q = 1\)), and \(a_{1}\) and \(a_{2}\) are those of Table 3.</p>
<div class="tablewrap"><table class="notation">
<tr><th>Case</th><th>Cosine input, \(u(t) = M\cos\left(\omega t\right)\)</th><th>Sine input, \(u(t) = M\sin\left(\omega t\right)\)</th></tr>
<tr><td>\(\zeta &gt; 1\)</td><td>\(KM\, R\cos\left(\omega t + \phi\right) + KM\left[a_{1} e^{r_{1}t} + a_{2} e^{r_{2}t}\right]\)</td><td>\(KM\, R\sin\left(\omega t + \phi\right) + KM\left[a_{1} e^{r_{1}t} + a_{2} e^{r_{2}t}\right]\)</td></tr>
<tr><td>\(\zeta = 1\)</td><td>\(KM\, R\cos\left(\omega t + \phi\right) + KM\left[-P_{0} - \left(P_{1} + P_{0}\right)\dfrac{t}{\tau}\right] e^{-t/\tau}\)</td><td>\(KM\, R\sin\left(\omega t + \phi\right) + KM\left[-P_{0} - \left(P_{1} + P_{0}\right)\dfrac{t}{\tau}\right] e^{-t/\tau}\)</td></tr>
<tr><td>\(0 &lt; \zeta &lt; 1\)</td><td>\(KM\, R\cos\left(\omega t + \phi\right) + KM\, e^{-\alpha t}\left[-P_{0}\cos\left(\omega_{d}t\right) + \dfrac{-P_{1} - \zeta P_{0}}{\delta}\sin\left(\omega_{d}t\right)\right]\)</td><td>\(KM\, R\sin\left(\omega t + \phi\right) + KM\, e^{-\alpha t}\left[-P_{0}\cos\left(\omega_{d}t\right) + \dfrac{-P_{1} - \zeta P_{0}}{\delta}\sin\left(\omega_{d}t\right)\right]\)</td></tr>
</table></div>
<p>In each cell of Table 4, the values of \(P_{0}\) and \(P_{1}\) (and of \(a_{1}\) and \(a_{2}\), which are computed from \(P_{0}\) and \(P_{1}\)) are those of the input named in the column heading: the cosine column uses the cosine rows of Table 2, and the sine column uses the sine rows of Table 2. The transient part is identical in form across the two columns and differs only through those constants.</p>

<h2 id="resonance-table">6 &nbsp; Table 5: input frequency equal to the natural frequency</h2>
<p>At \(q = 1\), equivalently \(\omega = \omega_{n} = 1/\tau\), Equation (2) gives \(S = 4\zeta^{2}\), \(R = 1/\left(2\zeta\right)\), and \(\phi = -\pi/2\) rad. Substitution into Equation (4) gives the steady-state parts of Table 5. The transient part at \(q = 1\) is obtained from Table 3 or Table 4 with the resonance values of \(P_{0}\) and \(P_{1}\) from Table 2; the form of the transient part does not change at \(q = 1\).</p>
<div class="tablewrap"><table class="notation">
<tr><th>Input at \(\omega = \omega_{n}\)</th><th>Steady-state part \(y_{ss}(t)\)</th><th>\(P_{0}\)</th><th>\(P_{1}\)</th></tr>
<tr><td>\(M\cos\left(\omega_{n} t\right)\)</td><td>\(\dfrac{KM}{2\zeta}\sin\left(\omega_{n} t\right)\)</td><td>\(0\)</td><td>\(\dfrac{1}{2\zeta}\)</td></tr>
<tr><td>\(M\sin\left(\omega_{n} t\right)\)</td><td>\(-\dfrac{KM}{2\zeta}\cos\left(\omega_{n} t\right)\)</td><td>\(\dfrac{-1}{2\zeta}\)</td><td>\(0\)</td></tr>
</table></div>
<p>For every \(\zeta &gt; 0\), the response at \(q = 1\) remains bounded: the steady-state amplitude is \(KM/\left(2\zeta\right)\) and the transient part decays. No term of the form \(t\) multiplied by a sinusoid at the input frequency appears at \(q = 1\) when \(\zeta &gt; 0\). Such a secular (linearly growing) term appears only in the undamped case \(\zeta = 0\), which is outside the three cases tabulated; the amplitude ratio \(R\) of Equation (2) grows without bound as \(\zeta\) approaches 0 at \(q = 1\), which is the limiting behaviour associated with that case.</p>

<h2 id="plots">7 &nbsp; Illustrative plots</h2>
<p>Figures 1 to 4 plot the tabulated responses in dimensionless form: the horizontal axis is \(t/\tau\), the output axis is \(y/\left(KM\right)\), and, where the input is drawn, the input axis quantity is \(u/M\). The symbols \(t\), \(\tau\), \(y\), \(K\), \(M\), and \(u\) are those defined in Section 1. Each curve is computed from Table 1 or Table 4 at the values of \(\zeta\) and \(q\) stated in the caption and in the figure legend or panel labels.</p>
<figure>
<!--FIG:fig-step.svg-->
<figcaption>Fig. 1 | Underdamped step responses overshoot the steady value 1, while the critically damped and overdamped responses approach the steady value monotonically. Step responses from Table 1 for \(\zeta\) equal to 0.25 and 0.5 (underdamped), 1 (critically damped), and 1.5 (overdamped). The dashed gray line marks the steady value \(y/\left(KM\right) = 1\).</figcaption>
</figure>
<figure>
<!--FIG:fig-cos.svg-->
<figcaption>Fig. 2 | For a cosine input, the response lags the input, and the response amplitude decreases as \(q\) and \(\zeta\) increase. Complete responses from Table 4 for a cosine input: the solid blue curve is \(y/\left(KM\right)\) and the dashed gray curve is the input \(u/M\). Rows correspond to \(\zeta\) equal to 0.5, 1, and 1.5; columns correspond to \(q\) equal to 0.5 (input frequency below the natural frequency), 1 (input frequency equal to the natural frequency), and 2 (input frequency above the natural frequency).</figcaption>
</figure>
<figure>
<!--FIG:fig-sin.svg-->
<figcaption>Fig. 3 | For a sine input, the response lags the input, and the response amplitude decreases as \(q\) and \(\zeta\) increase. Complete responses from Table 4 for a sine input: the solid blue curve is \(y/\left(KM\right)\) and the dashed gray curve is the input \(u/M\). Rows correspond to \(\zeta\) equal to 0.5, 1, and 1.5; columns correspond to \(q\) equal to 0.5, 1, and 2, with the same frequency meanings as in Fig. 2.</figcaption>
</figure>
<figure>
<!--FIG:fig-freq.svg-->
<figcaption>Fig. 4 | The amplitude ratio \(R\) peaks near \(q = 1\) for \(\zeta = 0.5\) and decreases monotonically for \(\zeta\) equal to 1 and 1.5, while the phase \(\phi\) passes through \(-\pi/2\) rad at \(q = 1\) for every \(\zeta\). Left panel: \(R\) against \(q\) from Equation (2). Right panel: \(\phi\) against \(q\) from Equation (2). The vertical gray line marks \(q = 1\).</figcaption>
</figure>

<h2 id="checks">8 &nbsp; Checks</h2>
<p>Initial conditions. By construction through Table 2 and Table 3, every entry of Table 4 satisfies \(y(0) = 0\) and \(y'\left(0\right) = 0\), where \(y'\left(0\right)\) denotes the first derivative of \(y(t)\) with respect to \(t\), evaluated at \(t = 0\). The step entries of Table 1 likewise satisfy \(y(0) = 0\) and \(y'\left(0\right) = 0\).</p>
<p>Long-time behaviour. For \(\zeta &gt; 0\) every transient term decays as \(t\) increases without bound, so each sinusoidal response approaches its steady-state part of Equation (4) or Table 5, and each step response of Table 1 approaches \(KM\).</p>
<p>Frequency limits. At \(q\) approaching 0, Equation (2) gives \(R\) approaching 1 and \(\phi\) approaching 0, and the sinusoidal steady-state parts approach the response to a constant input of magnitude \(M\), consistent with Table 1. At \(q\) increasing without bound, \(R\) decreases as \(1/q^{2}\), so the steady-state amplitude decreases as \(KM/q^{2}\).</p>
<p>Symbolic and numeric verification. Every entry of Table 4 was compared against an independent symbolic inverse Laplace transform for all combinations of \(\zeta\) equal to 1.5, 1, and 0.5; \(q\) equal to 0.7, 1, and 1.8; cosine and sine inputs; and \(t\) equal to 0, 0.4, 1.3, 4, and 9 s, with the test values \(K = 2\) output units per input unit, \(M = 3\) input units, and \(\tau = 3\) s. The maximum absolute difference over the 90 combinations was \(1.3 \times 10^{-7}\) output units, consistent with the numerical tolerance of the symbolic reference. The test values are verification values only and form no part of the tables.</p>
<p>Plot verification. The curves of Figs. 1 to 3 were compared against an independent numerical integration of the differential equation \(\tau^{2} y''(t) + 2\zeta\tau y'(t) + y(t) = K u(t)\), in which \(y''(t)\) denotes the second derivative of \(y(t)\) with respect to \(t\), for \(\zeta\) equal to 0.5, 1, and 1.5 with step, cosine, and sine inputs at \(q\) equal to 0.5, 1, and 2, and additionally for the step input at \(\zeta\) equal to 0.25, which appears in Fig. 1. The maximum absolute difference over the full time ranges plotted was \(5.5 \times 10^{-10}\) in the dimensionless output \(y/\left(KM\right)\).</p>
