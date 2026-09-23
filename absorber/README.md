# Packed Absorber Column — Sizing & Theory Demo 🧪

Interactive Streamlit web app demonstrating **packed gas-absorber calculations and sizing**:

- **Sizing calculator** — set the separation (flows, mole fractions, removal %),
  pick a packing, and get the operating line, transfer units (Kremser / NTU–HTU),
  column diameter from the **Eckert generalized pressure-drop correlation (GPDC)**
  flooding line, pressure drop, and packed height via the **Onda** mass-transfer
  correlations. All with Plotly charts (y–x diagram, GPDC chart, axial profile,
  % flood sensitivity) and a step-by-step audit trail.
- **Theory** — operating line, Henry's-law equilibrium, pinch / minimum L/G,
  absorption factor, NTU integral, Kremser equation, HTU, flooding — with
  fully rendered equations and references.
- **Correlations & packing data** — GPDC, Onda et al. (1968), packing-factor
  table, and pointers to Stichlmair, Billet–Schultes, Kister–Gill, Bravo–Rocha–Fair.
- **Worked example** — NH₃ absorbed from air into water, every step computed live.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub (public).
2. Go to [share.streamlit.io](https://share.streamlit.io) → *New app* →
   select the repo, branch `main`, file `app.py` → *Deploy*.

## Notes

- Educational demo: the GPDC flooding-line fit and ΔP curves are analytical
  approximations of the published Eckert chart — verify against primary sources
  (Eckert 1970; Strigle 1994; Treybal) before detailed design.
- Equations render with KaTeX (via `st.latex`), supported identically in
  Chrome, Safari, and Firefox.
