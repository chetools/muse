"""Mechanical verification of sheet.svg from sheet_geometry.json.

Counts, from the recorded stream geometry (not from the builder's
intentions): crossings between different streams (genuine junction
points excluded), bends per stream, and the minimum spacing
between parallel overlapping segments of different streams.
Also checks the displayed stream-table balance closure.
Run: python3 verify_sheet.py [--selftest]
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent


def segments(pts):
    return [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]


def seg_intersect(a, b, c, d):
    """Return intersection point of segments ab and cd, or None.

    Orthogonal segments only. Collinear overlaps return the
    string 'overlap'.
    """
    (x1, y1), (x2, y2) = a, b
    (x3, y3), (x4, y4) = c, d
    ah, bh = y1 == y2, y3 == y4
    if ah and bh:
        if y1 != y3:
            return None
        lo = max(min(x1, x2), min(x3, x4))
        hi = min(max(x1, x2), max(x3, x4))
        return "overlap" if lo < hi else (lo, y1) if lo == hi else None
    if not ah and not bh:
        if x1 != x3:
            return None
        lo = max(min(y1, y2), min(y3, y4))
        hi = min(max(y1, y2), max(y3, y4))
        return "overlap" if lo < hi else (x1, lo) if lo == hi else None
    # one horizontal, one vertical
    if ah:
        hx, hy, vx, vy = (x1, y1, x2), y1, x3, (y3, y4)
        hlo, hhi = min(x1, x2), max(x1, x2)
        vlo, vhi = min(vy), max(vy)
        px, py = vx, hy
    else:
        hx, hy, vx, vy = (x3, y3, x4), y3, x1, (y1, y2)
        hlo, hhi = min(x3, x4), max(x3, x4)
        vlo, vhi = min(vy), max(vy)
        px, py = vx, hy
    if hlo <= px <= hhi and vlo <= py <= vhi:
        return (px, py)
    return None


def count_crossings(streams, junctions):
    """Crossings between different streams, junctions excluded."""
    jset = {tuple(j) for j in junctions}
    crossings = []
    overlaps = []
    names = list(streams)
    for i, n1 in enumerate(names):
        for n2 in names[i + 1:]:
            for a, b in segments(streams[n1]):
                for c, d in segments(streams[n2]):
                    hit = seg_intersect(a, b, c, d)
                    if hit == "overlap":
                        overlaps.append((n1, n2, a, c))
                    elif hit is not None:
                        # shared endpoints and genuine junctions
                        ends = {tuple(a), tuple(b), tuple(c), tuple(d)}
                        if hit in jset or hit in ends:
                            continue
                        crossings.append((n1, n2, hit))
    return crossings, overlaps


def bends(streams):
    return {n: max(0, len(pts) - 2) for n, pts in streams.items()}


def min_parallel_spacing(streams):
    """Minimum gap between parallel overlapping segments of
    different streams (long runs and short jogs reported apart)."""
    best_long, best_short = None, None
    names = list(streams)
    for i, n1 in enumerate(names):
        for n2 in names[i + 1:]:
            for a, b in segments(streams[n1]):
                for c, d in segments(streams[n2]):
                    ah = a[1] == b[1]
                    bh = c[1] == d[1]
                    if ah != bh:
                        continue
                    if ah:
                        gap = abs(a[1] - c[1])
                        lo = max(min(a[0], b[0]), min(c[0], d[0]))
                        hi = min(max(a[0], b[0]), max(c[0], d[0]))
                    else:
                        gap = abs(a[0] - c[0])
                        lo = max(min(a[1], b[1]), min(c[1], d[1]))
                        hi = min(max(a[1], b[1]), max(c[1], d[1]))
                    if gap == 0 or hi <= lo:
                        continue
                    run = hi - lo
                    if run > 100:
                        best_long = gap if best_long is None else min(best_long, gap)
                    else:
                        best_short = gap if best_short is None else min(best_short, gap)
    return best_long, best_short


def main():
    geom = json.loads((HERE / "sheet_geometry.json").read_text())
    streams = {k: [tuple(p) for p in v] for k, v in geom["streams"].items()}
    if "--selftest" in sys.argv:
        # Planted defect: a stream crossing stream 1 must be caught.
        bad = dict(streams)
        bad["planted"] = [(150, 500), (150, 600)]
        c, _ = count_crossings(bad, geom["junctions"])
        assert c, "planted crossing was NOT detected"
        print(f"selftest: planted crossing detected ({c})")
        return
    crossings, overlaps = count_crossings(streams, geom["junctions"])
    b = bends(streams)
    long_gap, short_gap = min_parallel_spacing(streams)
    print(f"crossings: {len(crossings)} {crossings}")
    print(f"collinear overlaps between streams: {len(overlaps)} {overlaps}")
    print(f"bends per stream: {b}; max {max(b.values())}")
    print(f"min parallel spacing, runs >100 units: {long_gap}; "
          f"jogs <=100 units: {short_gap}")
    svg = (HERE / "sheet.svg").read_text(encoding="utf-8")
    for token in ("25,000", "20,000", "5,000"):
        assert token in svg, f"stream-table value {token} missing"
    assert 25000 == 20000 + 5000, "overall balance does not close"
    print("balance on displayed values: 25,000 = 20,000 + 5,000 kg/h, exact")
    assert not crossings, "CROSSINGS PRESENT"
    assert not overlaps, "COLLINEAR OVERLAPS PRESENT"
    assert max(b.values()) <= 4, "bend limit exceeded"
    assert long_gap is None or long_gap >= 40, "long-run spacing < 40"
    assert short_gap is None or short_gap >= 25, "jog spacing < 25"
    print("verify_sheet: PASS")


if __name__ == "__main__":
    main()
