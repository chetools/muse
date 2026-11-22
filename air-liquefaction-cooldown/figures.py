"""Figures for the cool-down page, drawn at build time.

Fig. P1 is the loop schematic. Its geometry is fixed by the
manifest in SCHEMATIC_STREAMS and SCHEMATIC_GLYPHS: every stream
endpoint lies on an equipment outline, on a junction dot, or on a
labelled terminal at the figure edge; every stream carries at
least one arrowhead; labels are placed clear of glyphs and lines.
The verification script (shots/verify_geometry.py) measures the
rendered SVG against the same manifest and against planted
defects.

Fig. P2 is the default-run temperature and inventory traces,
drawn from the model's sampled series.
"""

INK = "#1b1b1b"
HOT = "#D55E00"
COLD = "#0072B2"

# Stream paths of Fig. P1: id -> (path data, arrow at end?)
SCHEMATIC_STREAMS = {
    "s_feed_in": "M15,262 H58",
    "s_comp_out": "M122,262 H160",
    "s_ac_out": "M230,262 H270",
    "s_hot_out": "M520,262 H590",
    "s_turb_in": "M590,262 V170 H640",
    "s_turb_out": "M730,170 H800 V262",
    "s_valve_in": "M590,262 V380 H645",
    "s_valve_out": "M695,380 H800 V262",
    "s_sep_in": "M800,262 H835",
    "s_vap_top": "M895,191 V95 H545 V254",
    "s_vap_bot": "M545,270 V288 H520",
    "s_ret_b": "M255,254 V120 H15",
    "s_ret_a": "M270,288 H255 V270",
    "s_liquid": "M880,370 V420",
}
# Streams whose path is drawn in two subpaths (hop gaps at line
# crossings) still form one stream for the arrow inventory.
SCHEMATIC_ARROWS = {
    "s_feed_in": "end", "s_comp_out": "end", "s_ac_out": "end",
    "s_turb_in": "end", "s_turb_out": "end", "s_valve_in": "end",
    "s_valve_out": "end", "s_sep_in": "end", "s_vap_bot": "end",
    "s_ret_b": "end", "s_liquid": "end",
}
# Junction dots (x, y).
SCHEMATIC_DOTS = [(590, 262), (800, 262)]


def schematic_svg():
    p = []
    p.append('<svg id="fig-schematic" xmlns="http://www.w3.org/2000/svg" '
             'viewBox="0 0 1000 600" role="img" aria-label="Schematic of '
             'the liquefaction loop: compressor, aftercooler, '
             'regenerative heat exchanger, expansion turbine and '
             'throttling valve in parallel, separator, and the return '
             'path through the exchanger">')
    p.append('<defs>'
             f'<marker id="ahH" markerWidth="7" markerHeight="7" refX="6" '
             f'refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 z" '
             f'fill="{HOT}"/></marker>'
             f'<marker id="ahC" markerWidth="7" markerHeight="7" refX="6" '
             f'refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 z" '
             f'fill="{COLD}"/></marker>'
             f'<marker id="ahI" markerWidth="7" markerHeight="7" refX="6" '
             f'refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 z" '
             f'fill="{INK}"/></marker></defs>')
    # Cold box boundary.
    p.append('<rect id="g-coldbox" x="240" y="55" width="720" height="390" '
             'fill="none" stroke="#8a8a8a" stroke-width="1.2" '
             'stroke-dasharray="7 5"/>')
    p.append(f'<text x="248" y="78" font-size="13" fill="{INK}">Cold box</text>')
    # Exchanger glyph with internal stream lines.
    p.append('<rect id="g-exchanger" x="270" y="235" width="250" height="80" '
             'fill="#eef2f5" stroke="' + INK + '" stroke-width="1.8"/>')
    p.append(f'<line x1="278" y1="262" x2="505" y2="262" stroke="{HOT}" '
             'stroke-width="2.2" marker-end="url(#ahH)"/>')
    p.append(f'<line x1="512" y1="288" x2="285" y2="288" stroke="{COLD}" '
             'stroke-width="2.2" marker-end="url(#ahC)"/>')
    p.append(f'<text x="395" y="218" font-size="13.5" text-anchor="middle" '
             f'fill="{INK}">Regenerative heat exchanger</text>')
    # Compressor and aftercooler.
    p.append(f'<circle id="g-compressor" cx="90" cy="262" r="32" '
             f'fill="#eef2f5" stroke="{INK}" stroke-width="1.8"/>')
    p.append(f'<text x="90" y="318" font-size="13.5" text-anchor="middle" '
             f'fill="{INK}">Compressor</text>')
    p.append(f'<rect id="g-aftercooler" x="160" y="230" width="70" '
             f'height="64" fill="#eef2f5" stroke="{INK}" stroke-width="1.8"/>')
    p.append(f'<text x="195" y="318" font-size="13.5" text-anchor="middle" '
             f'fill="{INK}">Aftercooler</text>')
    # Turbine and valve.
    p.append(f'<polygon id="g-turbine" points="640,140 730,155 730,185 '
             f'640,200" fill="#f7e8dd" stroke="{INK}" stroke-width="1.8"/>')
    p.append(f'<text x="685" y="120" font-size="13.5" text-anchor="middle" '
             f'fill="{INK}">Expansion turbine</text>')
    p.append(f'<polygon id="g-valve" points="645,362 645,398 695,380 '
             f'695,362 695,398 645,380" fill="#eef2f5" stroke="{INK}" '
             'stroke-width="1.8"/>')
    p.append(f'<text x="670" y="425" font-size="13.5" text-anchor="middle" '
             f'fill="{INK}">Throttling valve</text>')
    # Separator.
    p.append('<path id="g-separator" d="M835,215 Q835,190 880,190 '
             'Q925,190 925,215 V345 Q925,370 880,370 Q835,370 835,345 Z" '
             f'fill="#e8f0f7" stroke="{INK}" stroke-width="1.8"/>')
    p.append(f'<line x1="843" y1="320" x2="917" y2="320" stroke="{COLD}" '
             'stroke-width="1.6" stroke-dasharray="5 3"/>')
    p.append(f'<text x="883" y="168" font-size="13.5" text-anchor="end" '
             f'fill="{INK}">Separator</text>')
    # Streams.
    hot_ids = {"s_feed_in", "s_comp_out", "s_ac_out", "s_hot_out",
               "s_turb_in", "s_turb_out", "s_valve_in", "s_valve_out",
               "s_sep_in"}
    for sid, d in SCHEMATIC_STREAMS.items():
        colour = HOT if sid in hot_ids else COLD
        marker = ""
        if sid in SCHEMATIC_ARROWS:
            marker = f' marker-end="url(#ahH)"' if colour == HOT \
                else f' marker-end="url(#ahC)"'
        p.append(f'<path id="{sid}" d="{d}" fill="none" stroke="{colour}" '
                 f'stroke-width="2.4"{marker}/>')
    for (dx, dy) in SCHEMATIC_DOTS:
        p.append(f'<circle cx="{dx}" cy="{dy}" r="4.5" fill="{INK}"/>')
    # Stream and terminal labels.
    p.append(f'<text x="15" y="238" font-size="13.5" fill="{INK}">Air in</text>')
    p.append(f'<text x="60" y="105" font-size="13.5" fill="{INK}">Return vapour</text>')
    p.append(f'<text x="868" y="405" font-size="13.5" text-anchor="end" fill="{INK}">Liquid product</text>')
    p.append(f'<text x="600" y="222" font-size="13.5" fill="{INK}">x = 0.75</text>')
    p.append(f'<text x="600" y="340" font-size="13.5" fill="{INK}">1 &#8722; x = 0.25</text>')
    p.append('</svg>')
    return "".join(p)


def trace_figure(series):
    """Fig. P2: two stacked panels from the default-run series."""
    t = series["t_h"]
    tce = series["T_cold_end"]
    texp = series["T_exp_out"]
    mliq = series["M_liq"]
    X0, X1 = 90.0, 880.0

    def px(v):
        return X0 + (X1 - X0) * v / 10.0

    parts = ['<svg id="fig-trace" xmlns="http://www.w3.org/2000/svg" '
             'viewBox="0 0 920 560" role="img" aria-label="Default-run '
             'traces: cold-end and expander outlet temperatures fall '
             'over about four hours; liquid inventory stays at zero '
             'for 3.1 hours and then grows">']
    # Panel A: temperatures, y 60..300 K over y pixels 60..250.
    def ya(v):
        return 250.0 - (250.0 - 60.0) * (v - 60.0) / 240.0

    for v in (100, 150, 200, 250, 300):
        parts.append(f'<line x1="{X0}" y1="{ya(v):.0f}" x2="{X1}" '
                     f'y2="{ya(v):.0f}" stroke="#cccccc" stroke-width="0.7"/>')
        parts.append(f'<text x="{X0 - 8}" y="{ya(v) + 4:.0f}" font-size="11.5" '
                     f'text-anchor="end" fill="{INK}">{v}</text>')
    parts.append(f'<text x="26" y="155" font-size="12.5" text-anchor="middle" '
                 f'fill="{INK}" transform="rotate(-90 26 155)">T (K)</text>')
    for key, colour, dash in (("T_cold_end", COLD, ""),
                              ("T_exp_out", HOT, ' stroke-dasharray="6 3"')):
        src = tce if key == "T_cold_end" else texp
        pts = " ".join(f"{px(a):.0f},{ya(b):.0f}" for a, b in zip(t, src))
        parts.append(f'<polyline points="{pts}" fill="none" '
                     f'stroke="{colour}" stroke-width="2.4"{dash}/>')
    parts.append(f'<line x1="600" y1="76" x2="640" y2="76" stroke="{COLD}" '
                 'stroke-width="2.4"/>')
    parts.append(f'<text x="648" y="80" font-size="12.5" fill="{INK}">Cold-end temperature</text>')
    parts.append(f'<line x1="600" y1="98" x2="640" y2="98" stroke="{HOT}" '
                 'stroke-width="2.4" stroke-dasharray="6 3"/>')
    parts.append(f'<text x="648" y="102" font-size="12.5" fill="{INK}">Expander outlet temperature</text>')
    # Panel B: inventory, y 0..420 kg over y pixels 330..500.
    def yb(v):
        return 500.0 - (500.0 - 330.0) * v / 420.0

    for v in (0, 100, 200, 300, 400):
        parts.append(f'<line x1="{X0}" y1="{yb(v):.0f}" x2="{X1}" '
                     f'y2="{yb(v):.0f}" stroke="#cccccc" stroke-width="0.7"/>')
        parts.append(f'<text x="{X0 - 8}" y="{yb(v) + 4:.0f}" font-size="11.5" '
                     f'text-anchor="end" fill="{INK}">{v}</text>')
    parts.append(f'<text x="26" y="415" font-size="12.5" text-anchor="middle" '
                 f'fill="{INK}" transform="rotate(-90 26 415)">Liquid inventory (kg)</text>')
    pts = " ".join(f"{px(a):.0f},{yb(b):.0f}" for a, b in zip(t, mliq))
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{COLD}" '
                 'stroke-width="2.4"/>')
    for v in (0, 2, 4, 6, 8, 10):
        parts.append(f'<text x="{px(v):.0f}" y="522" font-size="11.5" '
                     f'text-anchor="middle" fill="{INK}">{v}</text>')
    parts.append(f'<text x="485" y="545" font-size="12.5" text-anchor="middle" '
                 f'fill="{INK}">Simulated time (h)</text>')
    parts.append('</svg>')
    return "".join(parts)
