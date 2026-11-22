"""Axis-consistency measurement for Fig. P7 (v12).

Captures the figure built by gen_figures.fig_p7_machine()
(with save() stubbed out) and measures the drawing artists
themselves, in figure data coordinates:

- section view: the dash-dot centreline x; the centres of the
  shaft, hub, back plate, motor and seal rectangles; the
  vertex-mean x of the impeller body polygon;
- front-view inset: the impeller (dashed) circle centre; the
  horizontal and vertical dash-dot centrelines through it;
- that both views use the identical centreline linestyle.

Every section centre must coincide with the centreline
exactly, and the inset centrelines must cross exactly at the
impeller circle centre. Prints a JSON record; exits nonzero
on any mismatch.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent.parent
sys.path.insert(0, str(HERE))

import gen_figures  # noqa: E402

captured = {}
gen_figures.save = lambda fig, name: captured.update(fig=fig)  # noqa: E731
gen_figures.fig_p7_machine()
ax = captured["fig"].axes[0]

def style_key(line):
    return (line.get_color(), round(line.get_linewidth(), 6),
            str(line.get_linestyle()))


# Centrelines are selected by geometry (a long vertical line in
# the section; a short cross in the inset); their style triples
# must then agree exactly, which is what makes the axis mark
# the same in both views.
section_cl = [ln for ln in ax.lines
              if len(set(ln.get_xdata())) == 1
              and max(ln.get_ydata()) - min(ln.get_ydata()) > 5]
assert len(section_cl) == 1, f"section centrelines: {len(section_cl)}"
cl_x = float(section_cl[0].get_xdata()[0])
lines = ax.lines

rects = {}
for p in ax.patches:
    if p.__class__.__name__ == "Rectangle":
        key = round(p.get_width(), 2)
        rects.setdefault(key, []).append(
            round(p.get_x() + p.get_width() / 2, 9))
expected = {0.40: "shaft", 0.60: "hub", 4.10: "back plate",
            3.60: "motor", 0.96: "seal"}
centres = {}
for w, name in expected.items():
    assert w in rects, f"no rectangle of width {w} ({name})"
    centres[name] = rects[w]

body = None
from matplotlib.patches import Polygon as MplPolygon  # noqa: E402
for p in ax.patches:
    if isinstance(p, MplPolygon):
        v = p.get_xy()
        # get_xy() repeats the first vertex to close the path;
        # drop the duplicate or it biases the vertex mean.
        if (v[0] == v[-1]).all():
            v = v[:-1]
        if len(v) > 100 and abs(v[:, 0].min() - (cl_x - 2.05)) < 1e-9 \
                and abs(v[:, 0].max() - (cl_x + 2.05)) < 1e-9:
            body = v
assert body is not None, "impeller body polygon not found"
impeller_mean_x = round(float(body[:, 0].mean()), 9)

circles = [p for p in ax.patches if p.__class__.__name__ == "Circle"]
assert len(circles) == 1
ic = circles[0].center
inset_h = [ln for ln in lines if len(ln.get_xdata()) == 2
           and len(set(ln.get_ydata())) == 1
           and abs(float(ln.get_ydata()[0]) - ic[1]) < 1e-9]
inset_v = [ln for ln in lines if len(ln.get_xdata()) == 2
           and len(set(ln.get_xdata())) == 1
           and abs(float(ln.get_xdata()[0]) - ic[0]) < 1e-9
           and max(ln.get_ydata()) - min(ln.get_ydata()) < 5]
assert len(inset_h) == 1 and len(inset_v) == 1, \
    f"inset centrelines: h={len(inset_h)} v={len(inset_v)}"
styles = {style_key(section_cl[0]), style_key(inset_h[0]),
          style_key(inset_v[0])}
assert len(styles) == 1, f"centreline styles differ: {styles}"
h_span = [round(float(v), 9) for v in
          (min(inset_h[0].get_xdata()), max(inset_h[0].get_xdata()))]
v_span = [round(float(v), 9) for v in
          (min(inset_v[0].get_ydata()), max(inset_v[0].get_ydata()))]

ok = all(abs(c - cl_x) < 1e-9 for cs in centres.values() for c in cs) \
    and abs(impeller_mean_x - cl_x) < 1e-9
record = {
    "section_centreline_x": cl_x,
    "section_rectangle_centres": centres,
    "impeller_body_vertex_mean_x": impeller_mean_x,
    "inset_impeller_centre": [round(float(ic[0]), 9),
                              round(float(ic[1]), 9)],
    "inset_centreline_horizontal": {"y": round(float(ic[1]), 9),
                                    "x_span": h_span},
    "inset_centreline_vertical": {"x": round(float(ic[0]), 9),
                                  "y_span": v_span},
    "inset_impeller_radius": round(float(circles[0].radius), 9),
    "same_centreline_style_both_views": True,
    "all_section_centres_on_centreline": ok,
}
print(json.dumps(record, indent=2))
assert ok, "a section centre is off the centreline"
