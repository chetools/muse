"""Tests for protect_spans: round-trip identity, span kinds, the
currency rule, placeholder tampering, and the fail-safe."""
import sys

sys.path.insert(0, ".")
from protect_spans import protect, restore  # noqa: E402

REYNOLDS = (
    "The Reynolds number $Re = \\rho v D / \\mu$ uses the density "
    "$\\rho$ (kg m-3), the mean velocity $v$ (m s-1), the diameter "
    "$D$ (m) and the viscosity $\\mu$ (Pa s). For water at 293 K,\n\n"
    "$$Re = \\frac{998 \\times 0.9 \\times 0.08}{0.001} = 71900$$\n\n"
    "and the flow is turbulent."
)
CURRENCY = ("The retrofit is quoted at $392k installed, with a "
            "further $12k for controls, and saves $34k per year.")
CODE = ("Run the balance:\n\n```python\nRe = rho * v * D / mu  # $x$\n"
        "```\n\nThen compare `Re > 4000` with the threshold.")
TABLE = ("| Quantity | Value |\n|---|---|\n| $Re$ | 71900 |\n\n"
         "The table above summarises the run.")
MIXED = ("See <em>Fig. 2</em> ![column](fig2.png) and "
         "[the notes](https://example.org/notes) for `setup`.")

for name, text in [("reynolds", REYNOLDS), ("currency", CURRENCY),
                   ("code", CODE), ("table", TABLE), ("mixed", MIXED)]:
    masked, spans = protect(text)
    assert restore(masked, spans) == text, f"round trip failed: {name}"
    print(f"{name}: {len(spans)} span(s) "
          f"{[s['kind'] for s in spans]}")

masked, spans = protect(REYNOLDS)
assert "\\rho" not in masked and "71900" not in masked.split("$$")[0]
assert "$" not in masked, "no math delimiters may reach the model"
print("reynolds masked:", masked[:110], "...")

masked, spans = protect(CURRENCY)
assert spans == [], f"currency misread as math: {spans}"
print("currency: 0 spans, all prose")

masked, spans = protect("The value $$Re = 71900 is the result.")
assert len(spans) == 1 and spans[0]["kind"] == "document"
assert restore(masked, spans).startswith("The value")
print("fail-safe: unclosed display math protects the whole text")

masked, spans = protect(REYNOLDS)
tampered = masked.replace("⟦P1⟧", "⟦P9⟧")
try:
    restore(tampered, spans)
    raise AssertionError("tampered placeholder accepted")
except ValueError as exc:
    print("tamper rejected:", str(exc)[:70])

dropped = masked.replace("⟦P2⟧", "")
try:
    restore(dropped, spans)
    raise AssertionError("dropped placeholder accepted")
except ValueError:
    print("dropped placeholder rejected")
print("ALL TESTS PASSED")
