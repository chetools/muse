# molab-test

Minimal end-to-end test of the MoLab workflow: a marimo notebook that
minimizes the Rosenbrock function with `scipy.optimize.minimize` (BFGS) and
draws the iterate path on a plotly 3D surface. The run button re-solves from
a fresh random start, exercising widget → kernel interaction.

Run on MoLab (signed-in server run) via the GitHub mirror:

https://molab.marimo.io/github/chetools/muse/blob/main/molab-test/rosenbrock_opt.py
