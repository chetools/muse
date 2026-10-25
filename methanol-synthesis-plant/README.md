# Methanol synthesis and purification plant (PFD-104)

Standalone serverless WASM educational page for the methanol synthesis
and purification plant: process flow diagram PFD-104 (sheet Revision 2,
sample design values) with a live two-part Python balance model
(synthesis loop balance and purification balance), a Theory panel with
one headed section per subunit and sub-process flow diagrams, a Code
panel with the full listings and a statically rendered walkthrough,
and a marimo notebook pair (pre-run read-only WASM walkthrough plus an
editable notebook on MoLab).

Build: `python build_page.py` writes `dist/methanol-synthesis-plant-v1.html`;
`python make_molab.py` regenerates the notebook pair from
`python/walkthrough.py`. Verification: `python verify_page.py` and
`python shoot_page.py` (rendered screenshots, header geometry, sticky
tab bar scroll checks). Published page:
`muse-html/methanol-synthesis-plant/methanol-synthesis-plant-v1.html`
on the gh-pages branch.
