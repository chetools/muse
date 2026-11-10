# Smith and Corripio PID tuning page

Static WASM educational page: Smith and Corripio ITAE tuning for
first-order plus dead time models, with a higher-order model
approximation panel (manual, Skogestad half rule, least-squares
fit), parameter sweeps, a derivative filter, output amplitude and
slew limits, and anti-windup. See SPEC.md for the frozen build
contract.

Build (marimo-export venv carries markdown-it and pygments):

    ~/workspace/.venvs/marimo-export/bin/python python/make_molab.py
    ~/workspace/.venvs/marimo-export/bin/python build.py

Tests: `python -m pytest python/test_pid_core.py` (couette venv).
Browser QA: serve dist/ on port 8911, then
`~/workspace/.venvs/marimo-export/bin/python qa_playwright.py`.
Output: dist/smith-corripio-pid-standalone-v1.html plus the
MoLab notebook copy dist/walkthrough_molab.py.
