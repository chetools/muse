# Questions and selected choices

Grill held 2026-11-02. Q2 was answered by the user (Seader, latest
edition); all other recommendations were accepted by the user
("proceed with recommendations", then plan approval "build it").

1. Relation to the existing derivation page — separate new page;
   Theory condenses Fenske/Underwood, links the derivation page,
   Gilliland in full.
2. Textbook — Seader, Henley & Roper, latest edition (4th ed.,
   2016), Chapter 9, debutanizer Examples 9.1–9.6 as the locked
   validation case.
3. Default mixture — the Seader debutanizer (eight components).
4. Keys and splits — LK n-butane 442/6, HK isopentane 13/23 lbmol/h.
5. Volatilities — Seader's geometric-mean relative volatilities,
   one declared table used throughout, editable; Example 9.1
   (ChemCAD/SRK) summarised in Theory, not a live calculation.
6. Underwood — Class 1 only (user instruction, 2026-11-02,
   superseding the earlier Class 1 + Class 2 choice recorded here
   previously): the Class 1 calculation is the headline result,
   with its validity check, which fails for this case, stated
   plainly; no Class 2 calculation is presented.
7. Gilliland — Eduljee equation (Seader Eq. 9-33), full curve
   plotted with the operating point.
8. Operating reflux — multiplier on Rmin, default 1.3 (Seader
   Example 9.6); total condenser, partial reboiler counted.
9. Feed stage — Kirkbride first, Fenske section ratio second.
10. Efficiency — theoretical stages; optional overall efficiency
    input, default 100%.
11. Plots — Gilliland curve, Underwood function with all roots,
    component distribution (logarithmic scale).
12. Audience and exclusions — senior BS chemical engineers;
    directory `fenske-underwood-gilliland`; no rigorous
    tray-by-tray calculation, hydraulics, diameter, or economics.
13. Feed quality — q = 0.866 for the default case (feed flashed,
    13.4% vaporised), an explicit App input.

Discrepancies recorded, not smoothed over: the Class 1 reflux
conversion (0.414 per unit feed recomputes to 0.774 per unit
distillate, not Seader's printed 0.864) and the heaviest component
named n-decane in one extracted table but n-nonane (C9) in the
feed and K-value tables — n-nonane is used. The 4th-edition print
was not available in the sandbox; both items are stated on the
page as they stand in the source copy on file.

Addendum (SI conversion, 2026-11-02): at the user's direction
("always use SI units"), the page was converted throughout from
the source text's imperial units to SI and republished as the v2
build at the same address. Every molar flow was multiplied by
0.45359237 kmol per lbmol and is now stated in kmol/h; the
pressures of Section 2 are now in kPa (70 psia = 482.6 kPa;
105 psia = 723.9 kPa; 74 psia = 510.2 kPa). The original Seader
values remain identifiable in this file above and in the git
history (the v1 build): feed 876.3 lbmol/h with the component
values of item 3, key splits 442/6 and 13/23 lbmol/h, totals
468.95/407.35 lbmol/h. All dimensionless results are unchanged.
Two converted values in Theory Section 7 are the page's own
solutions at the new rounding (n-pentane in distillate
1.554 kmol/h, D = 213.382 kmol/h); the direct conversions of the
source text's rounded totals are 1.556 and 213.370 kmol/h.

Addendum (Class 1 only and in-place derivations, 2026-11-02): at
the user's direction the Underwood scope became Class 1 only
(item 6 as revised above) and the Theory tab was expanded to
carry the full derivations of the Fenske and Underwood equations
in place, adapted from the verified derivation project
(~/workspace/fenske-underwood-derivation/). Headline values are
now: Class 1 Rmin 0.774 per unit distillate (the page's unrounded
evaluation gives 0.773), Gilliland N = 18.1 at a multiplier of
1.3 (19 stages rounded, feed stage 6 of 19 by Kirkbride). The
Class 1 validity check fails for this case and is stated plainly
on the page. This combined revision was published as the v2
build at the same address, together with the SI conversion.
