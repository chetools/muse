# /// script
# requires-python = ">=3.12"
# dependencies = ["marimo", "numpy", "scipy", "plotly"]
# ///
"""Notebook generated from walkthrough.py CELLS by make_molab.py.
Do not edit by hand; regenerate."""
import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import base64
    import plotly.graph_objects as go
    import sys as _sys, types as _types
    FUG_SRC = base64.b64decode("IiIiRmVuc2tlLVVuZGVyd29vZC1HaWxsaWxhbmQgKEZVRykgc2hvcnRjdXQgZGVzaWduIG9mIGEgbXVsdGljb21wb25lbnQKZGlzdGlsbGF0aW9uIGNvbHVtbiwgZm9sbG93aW5nIFNlYWRlciwgSGVubGV5ICYgUm9wZXIsIFNlcGFyYXRpb24gUHJvY2VzcwpQcmluY2lwbGVzLCA0dGggZWQuICgyMDE2KSwgQ2hhcHRlciA5LCBFeGFtcGxlcyA5LjItOS42IChkZWJ1dGFuaXplcikuCgpTeW1ib2xzLCBkZWZpbmVkIGF0IGZpcnN0IHVzZSBpbiB0aGUgd2Fsa3Rocm91Z2ggYW5kIFRoZW9yeSB0ZXh0OgogIGZfaSAgICBtb2xhciBmbG93IHJhdGUgb2YgY29tcG9uZW50IGkgaW4gdGhlIGZlZWQsIGluIGxibW9sL2gKICAgICAgICAgKHBvdW5kLW1vbGVzIHBlciBob3VyLCB0aGUgdW5pdCBvZiB0aGUgc291cmNlIGV4YW1wbGUpCiAgZF9pICAgIG1vbGFyIGZsb3cgcmF0ZSBvZiBjb21wb25lbnQgaSBpbiB0aGUgZGlzdGlsbGF0ZSwgaW4gbGJtb2wvaAogIGJfaSAgICBtb2xhciBmbG93IHJhdGUgb2YgY29tcG9uZW50IGkgaW4gdGhlIGJvdHRvbXMsIGluIGxibW9sL2gKICBhbHBoYV9pICBtZWFuIHJlbGF0aXZlIHZvbGF0aWxpdHkgb2YgY29tcG9uZW50IGkgd2l0aCByZXNwZWN0IHRvIHRoZQogICAgICAgICBoZWF2eSBrZXkgKEhLKSwgZGltZW5zaW9ubGVzczsgYWxwaGEgb2YgdGhlIEhLIGlzIDEgYnkgZGVmaW5pdGlvbgogIExLICAgICBsaWdodCBrZXk7IEhLIGhlYXZ5IGtleSAoYWRqYWNlbnQgaW4gdGhlIHZvbGF0aWxpdHkgb3JkZXIpCiAgTm1pbiAgIG1pbmltdW0gbnVtYmVyIG9mIGVxdWlsaWJyaXVtIHN0YWdlcyAodG90YWwgcmVmbHV4KSwgZGltZW5zaW9ubGVzczsKICAgICAgICAgdGhlIHRvdGFsIGNvbmRlbnNlciBpcyBub3QgYSBzdGFnZSwgdGhlIHBhcnRpYWwgcmVib2lsZXIgaXMgb25lIHN0YWdlCiAgcSAgICAgIGZlZWQgcXVhbGl0eTogdGhlIGxpcXVpZCBmcmFjdGlvbiBmb3IgYSB0d28tcGhhc2UgZmVlZCBhcyBpdCBlbnRlcnMKICAgICAgICAgdGhlIGNvbHVtbjsgYWJvdmUgMSBmb3IgYSBzdWJjb29sZWQgbGlxdWlkIGZlZWQsCiAgICAgICAgIGRpbWVuc2lvbmxlc3MgKHEgPSAxIHNhdHVyYXRlZCBsaXF1aWQsIHEgPSAwIHNhdHVyYXRlZCB2YXBvdXIsCiAgICAgICAgIHEgPiAxIHN1YmNvb2xlZCBsaXF1aWQpCiAgdGhldGEgIFVuZGVyd29vZCByb290LCBkaW1lbnNpb25sZXNzLCBpbiB0aGUgc2FtZSBzY2FsZSBhcyBhbHBoYQogIFJtaW4gICBtaW5pbXVtIHJlZmx1eCByYXRpbywgTC9EIGF0IG1pbmltdW0gcmVmbHV4LCBkaW1lbnNpb25sZXNzCiAgUiAgICAgIG9wZXJhdGluZyByZWZsdXggcmF0aW8sIGRpbWVuc2lvbmxlc3M7IG11bHQgPSBSIC8gUm1pbgogIE4gICAgICBudW1iZXIgb2YgZXF1aWxpYnJpdW0gc3RhZ2VzIGF0IFIsIHNhbWUgY291bnRpbmcgYXMgTm1pbgpBbGwgY2FsY3VsYXRpb25zIGFyZSBpbiBQeXRob24gKG51bXB5LCBzY2lweSk7IHRoZXJlIGlzIG5vIG90aGVyCmltcGxlbWVudGF0aW9uLgoiIiIKaW1wb3J0IG51bXB5IGFzIG5wCmZyb20gc2NpcHkub3B0aW1pemUgaW1wb3J0IGJyZW50cQoKTkFNRVMgPSBbImlzb2J1dGFuZSIsICJuLWJ1dGFuZSIsICJpc29wZW50YW5lIiwgIm4tcGVudGFuZSIsCiAgICAgICAgICJuLWhleGFuZSIsICJuLWhlcHRhbmUiLCAibi1vY3RhbmUiLCAibi1ub25hbmUiXQpMSywgSEsgPSAxLCAyICAgICAgICAgICMgaW5kaWNlcyBvZiBuLWJ1dGFuZSBhbmQgaXNvcGVudGFuZSBpbiBOQU1FUwpESVNUX05PTktFWSA9IDMgICAgICAgICMgbi1wZW50YW5lOiB0aGUgb25lIGRpc3RyaWJ1dGluZyBub24ta2V5IChDbGFzcyAyKQoKCmRlZiBkZWZhdWx0X2lucHV0cygpOgogICAgIiIiVGhlIFNlYWRlciBkZWJ1dGFuaXplciBkZWZhdWx0IGNhc2UgKEV4YW1wbGVzIDkuMS05LjYpLiIiIgogICAgcmV0dXJuIHsKICAgICAgICAibmFtZXMiOiBsaXN0KE5BTUVTKSwKICAgICAgICAiZmVlZCI6IFsxMi4wLCA0NDguMCwgMzYuMCwgMTUuMCwgMjMuMCwgMzkuMSwgMjcyLjIsIDMxLjBdLAogICAgICAgICJhbHBoYSI6IFsyLjMyOSwgMS44NjQsIDEuMDAwLCAwLjg0NSwgMC4zODksIDAuMTgyNSwgMC4wODUyLCAwLjA0MDFdLAogICAgICAgICJsayI6IExLLCAiaGsiOiBISywKICAgICAgICAiZF9sayI6IDQ0Mi4wLCAiYl9sayI6IDYuMCwgICAgICAjIHNwZWNpZmllZCBzcGxpdCBvZiB0aGUgbGlnaHQga2V5CiAgICAgICAgImRfaGsiOiAxMy4wLCAiYl9oayI6IDIzLjAsICAgICAgIyBzcGVjaWZpZWQgc3BsaXQgb2YgdGhlIGhlYXZ5IGtleQogICAgICAgICJxIjogMC44NjYsICAgICAgICAgICAgICAgICAgICAgICMgMTMuNCAlIG9mIHRoZSBmZWVkIHZhcG9yaXNlZAogICAgICAgICJtdWx0IjogMS4zLCAgICAgICAgICAgICAgICAgICAgICMgUiA9IDEuMyAqIFJtaW4gKEV4YW1wbGUgOS42KQogICAgICAgICJlZmZpY2llbmN5IjogMS4wLCAgICAgICAgICAgICAgICMgb3ZlcmFsbCB0cmF5IGVmZmljaWVuY3ksIGZyYWN0aW9uCiAgICB9CgoKZGVmIHZhbGlkYXRlKGlucCk6CiAgICAiIiJSYWlzZSBWYWx1ZUVycm9yIHdpdGggYSBwbGFpbiBtZXNzYWdlIG9uIGFueSB1bnVzYWJsZSBpbnB1dC4iIiIKICAgIGYgPSBucC5hc2FycmF5KGlucFsiZmVlZCJdLCBmbG9hdCkKICAgIGEgPSBucC5hc2FycmF5KGlucFsiYWxwaGEiXSwgZmxvYXQpCiAgICBpZiBmLnNoYXBlICE9IGEuc2hhcGUgb3IgZi5uZGltICE9IDEgb3IgbGVuKGYpIDwgMzoKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJGZWVkIGZsb3dzIGFuZCByZWxhdGl2ZSB2b2xhdGlsaXRpZXMgbXVzdCBiZSAiCiAgICAgICAgICAgICAgICAgICAgICAgICAibGlzdHMgb2YgdGhlIHNhbWUgbGVuZ3RoLCBhdCBsZWFzdCAzIGNvbXBvbmVudHMuIikKICAgIGlmIG5wLmFueShmIDw9IDApOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIkV2ZXJ5IGZlZWQgZmxvdyByYXRlIG11c3QgYmUgZ3JlYXRlciB0aGFuIHplcm8uIikKICAgIGlmIG5wLmFueShhIDw9IDApOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIkV2ZXJ5IHJlbGF0aXZlIHZvbGF0aWxpdHkgbXVzdCBiZSBncmVhdGVyICIKICAgICAgICAgICAgICAgICAgICAgICAgICJ0aGFuIHplcm8uIikKICAgIGlmIG5vdCBucC5hbGwobnAuZGlmZihhKSA8IDApOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIlJlbGF0aXZlIHZvbGF0aWxpdGllcyBtdXN0IGRlY3JlYXNlIHN0cmljdGx5ICIKICAgICAgICAgICAgICAgICAgICAgICAgICJpbiB0aGUgY29tcG9uZW50IG9yZGVyIGdpdmVuLiIpCiAgICBsaywgaGsgPSBpbnQoaW5wWyJsayJdKSwgaW50KGlucFsiaGsiXSkKICAgIGlmIGhrICE9IGxrICsgMSBvciBub3QgKDAgPD0gbGsgPCBsZW4oZikgLSAxKToKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJUaGUgbGlnaHQga2V5IGFuZCBoZWF2eSBrZXkgbXVzdCBiZSBhZGphY2VudCAiCiAgICAgICAgICAgICAgICAgICAgICAgICAiY29tcG9uZW50cyBpbiB0aGUgdm9sYXRpbGl0eSBvcmRlci4iKQogICAgaWYgYWJzKGFbaGtdIC0gMS4wKSA+IDFlLTk6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiVGhlIHJlbGF0aXZlIHZvbGF0aWxpdHkgb2YgdGhlIGhlYXZ5IGtleSBtdXN0ICIKICAgICAgICAgICAgICAgICAgICAgICAgICJiZSAxLCBiZWNhdXNlIHZvbGF0aWxpdGllcyBhcmUgcmVsYXRpdmUgdG8gaXQuIikKICAgIGZvciBrZXksIGRrZXksIGJrZXkgaW4gKCgibGlnaHQga2V5IiwgImRfbGsiLCAiYl9sayIpLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgKCJoZWF2eSBrZXkiLCAiZF9oayIsICJiX2hrIikpOgogICAgICAgIGkgPSBsayBpZiBrZXkgPT0gImxpZ2h0IGtleSIgZWxzZSBoawogICAgICAgIGlmIGlucFtka2V5XSA8IDAgb3IgaW5wW2JrZXldIDwgMDoKICAgICAgICAgICAgcmFpc2UgVmFsdWVFcnJvcihmIlRoZSBzcGVjaWZpZWQgc3BsaXQgb2YgdGhlIHtrZXl9IG11c3Qgbm90ICIKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAiYmUgbmVnYXRpdmUuIikKICAgICAgICBpZiBhYnMoaW5wW2RrZXldICsgaW5wW2JrZXldIC0gZltpXSkgPiAxZS02ICogbWF4KDEuMCwgZltpXSk6CiAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoCiAgICAgICAgICAgICAgICBmIlRoZSBzcGVjaWZpZWQgc3BsaXQgb2YgdGhlIHtrZXl9IGRvZXMgbm90IGFkZCB1cCB0byAiCiAgICAgICAgICAgICAgICBmIml0cyBmZWVkIGZsb3cgcmF0ZSAoe2ZbaV06Z30gbGJtb2wvaCkuIikKICAgIGlmIG5vdCAoMC4wIDw9IGZsb2F0KGlucFsicSJdKSA8PSAxLjUpOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIlRoZSBmZWVkIHF1YWxpdHkgcSBtdXN0IGxpZSBiZXR3ZWVuIDAgYW5kIDEuNSAiCiAgICAgICAgICAgICAgICAgICAgICAgICAib24gdGhpcyBwYWdlICgwIHNhdHVyYXRlZCB2YXBvdXIsIDEgc2F0dXJhdGVkICIKICAgICAgICAgICAgICAgICAgICAgICAgICJsaXF1aWQ7IHZhbHVlcyBhYm92ZSAxIGRlbm90ZSBzdWJjb29sZWQgbGlxdWlkKS4iKQogICAgaWYgZmxvYXQoaW5wWyJtdWx0Il0pIDw9IDEuMDoKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJUaGUgcmVmbHV4IG11bHRpcGxpZXIgUi9SbWluIG11c3QgYmUgZ3JlYXRlciAiCiAgICAgICAgICAgICAgICAgICAgICAgICAidGhhbiAxOyBhdCB0aGUgbWluaW11bSB0aGUgc3RhZ2UgY291bnQgaXMgIgogICAgICAgICAgICAgICAgICAgICAgICAgInVuYm91bmRlZC4iKQogICAgaWYgbm90ICgwLjAgPCBmbG9hdChpbnBbImVmZmljaWVuY3kiXSkgPD0gMS4wKToKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJUaGUgb3ZlcmFsbCBlZmZpY2llbmN5IG11c3QgYmUgYSBmcmFjdGlvbiAiCiAgICAgICAgICAgICAgICAgICAgICAgICAiZ3JlYXRlciB0aGFuIDAgYW5kIGF0IG1vc3QgMS4iKQogICAgcmV0dXJuIFRydWUKCgpkZWYgZmVuc2tlKGlucCk6CiAgICAiIiJNaW5pbXVtIHN0YWdlcyBhbmQgdGhlIHByb2R1Y3QgZGlzdHJpYnV0aW9uIGF0IHRvdGFsIHJlZmx1eC4KCiAgICBSZXR1cm5zIGRpY3Qgd2l0aCBObWluIGFuZCB0aGUgZGlzdGlsbGF0ZSBhbmQgYm90dG9tcyBmbG93IGFycmF5cwogICAgZCBhbmQgYiAobGJtb2wvaCksIGNvbXB1dGVkIGZvciB0aGUgc21hbGxlciBzdHJlYW0gb2YgZWFjaCBub24ta2V5CiAgICBjb21wb25lbnQgZmlyc3QsIHRoZSBvdGhlciBieSBkaWZmZXJlbmNlIChTZWFkZXIncyBndWlkYW5jZSkuCiAgICAiIiIKICAgIHZhbGlkYXRlKGlucCkKICAgIGYgPSBucC5hc2FycmF5KGlucFsiZmVlZCJdLCBmbG9hdCkKICAgIGEgPSBucC5hc2FycmF5KGlucFsiYWxwaGEiXSwgZmxvYXQpCiAgICBsaywgaGsgPSBpbnQoaW5wWyJsayJdKSwgaW50KGlucFsiaGsiXSkKICAgIGQgPSBucC56ZXJvc19saWtlKGYpCiAgICBiID0gbnAuemVyb3NfbGlrZShmKQogICAgZFtsa10sIGJbbGtdID0gaW5wWyJkX2xrIl0sIGlucFsiYl9sayJdCiAgICBkW2hrXSwgYltoa10gPSBpbnBbImRfaGsiXSwgaW5wWyJiX2hrIl0KICAgIGFfbGtfaGsgPSBhW2xrXSAvIGFbaGtdCiAgICBuX21pbiA9IChucC5sb2cxMCgoZFtsa10gLyBiW2xrXSkgKiAoYltoa10gLyBkW2hrXSkpCiAgICAgICAgICAgICAvIG5wLmxvZzEwKGFfbGtfaGspKQogICAgcmF0aW9faGsgPSBkW2hrXSAvIGJbaGtdICAgICAgICAgICAgICAgIyBkL2Igb2YgdGhlIHJlZmVyZW5jZSAoSEspCiAgICBmb3IgaSBpbiByYW5nZShsZW4oZikpOgogICAgICAgIGlmIGkgaW4gKGxrLCBoayk6CiAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgIyBGZW5za2UgZm9yIGNvbXBvbmVudCBpIHJlbGF0aXZlIHRvIHRoZSBISzogZF9pL2JfaSBrbm93bi4KICAgICAgICByID0gcmF0aW9faGsgKiAoYVtpXSAvIGFbaGtdKSAqKiBuX21pbgogICAgICAgIGlmIHIgPD0gMS4wOiAgICAgICAgICAgICAgICAgICAgICAgIyBzbWFsbGVyIHN0cmVhbSBpcyBkaXN0aWxsYXRlCiAgICAgICAgICAgIGRbaV0gPSBmW2ldICogciAvICgxLjAgKyByKQogICAgICAgICAgICBiW2ldID0gZltpXSAtIGRbaV0KICAgICAgICBlbHNlOiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgc21hbGxlciBzdHJlYW0gaXMgYm90dG9tcwogICAgICAgICAgICBiW2ldID0gZltpXSAvICgxLjAgKyByKQogICAgICAgICAgICBkW2ldID0gZltpXSAtIGJbaV0KICAgIHJldHVybiB7Im5fbWluIjogZmxvYXQobl9taW4pLCAiZCI6IGQsICJiIjogYiwKICAgICAgICAgICAgImFscGhhX2xrX2hrIjogZmxvYXQoYV9sa19oayl9CgoKZGVmIHVuZGVyd29vZF9mdW5jdGlvbih0aGV0YSwgYWxwaGEsIHosIHEpOgogICAgIiIiVW5kZXJ3b29kIGZlZWQgZnVuY3Rpb24gVSh0aGV0YSkgPSBzdW1faSBhbHBoYV9pIHpfaS8oYWxwaGFfaSAtCiAgICB0aGV0YSkgLSAoMSAtIHEpLCB3aGVyZSB6X2kgaXMgdGhlIG1vbGUgZnJhY3Rpb24gb2YgY29tcG9uZW50IGkgaW4KICAgIHRoZSBmZWVkIChkaW1lbnNpb25sZXNzKSBhbmQgdGhldGEgaXMgZGltZW5zaW9ubGVzcy4gIFJvb3RzIG9mIFUgaW4KICAgIHRoZSBpbnRlcnZhbHMgYmV0d2VlbiBjb25zZWN1dGl2ZSByZWxhdGl2ZSB2b2xhdGlsaXRpZXMgZ2l2ZSB0aGUKICAgIFVuZGVyd29vZCBwYXJhbWV0ZXJzLiIiIgogICAgYWxwaGEgPSBucC5hc2FycmF5KGFscGhhLCBmbG9hdCkKICAgIHogPSBucC5hc2FycmF5KHosIGZsb2F0KQogICAgcmV0dXJuIG5wLnN1bShhbHBoYSAqIHogLyAoYWxwaGEgLSB0aGV0YSkpIC0gKDEuMCAtIHEpCgoKZGVmIHVuZGVyd29vZF9yb290cyhhbHBoYSwgeiwgcSk6CiAgICAiIiJBbGwgcm9vdHMgb2YgdGhlIFVuZGVyd29vZCBmZWVkIGVxdWF0aW9uLCBvbmUgcGVyIGludGVydmFsCiAgICBiZXR3ZWVuIGNvbnNlY3V0aXZlIGRpc3RpbmN0IHJlbGF0aXZlIHZvbGF0aWxpdGllcywgaW4gZGVjcmVhc2luZwogICAgb3JkZXIgb2YgdGhldGEuICBJbnRlcnZhbHMgd2l0aCBubyBzaWduIGNoYW5nZSBhcmUgc2tpcHBlZC4iIiIKICAgIGEgPSBucC5zb3J0KG5wLmFzYXJyYXkoYWxwaGEsIGZsb2F0KSlbOjotMV0KICAgIHJvb3RzID0gW10KICAgIGZvciBoaSwgbG8gaW4gemlwKGFbOi0xXSwgYVsxOl0pOgogICAgICAgIGVwcyA9IDFlLTEwICogbWF4KDEuMCwgaGkpCiAgICAgICAgeDAsIHgxID0gbG8gKyBlcHMsIGhpIC0gZXBzCiAgICAgICAgdTAgPSB1bmRlcndvb2RfZnVuY3Rpb24oeDAsIGFscGhhLCB6LCBxKQogICAgICAgIHUxID0gdW5kZXJ3b29kX2Z1bmN0aW9uKHgxLCBhbHBoYSwgeiwgcSkKICAgICAgICBpZiBucC5pc2Zpbml0ZSh1MCkgYW5kIG5wLmlzZmluaXRlKHUxKSBhbmQgdTAgKiB1MSA8IDA6CiAgICAgICAgICAgIHJvb3RzLmFwcGVuZChmbG9hdChicmVudHEodW5kZXJ3b29kX2Z1bmN0aW9uLCB4MCwgeDEsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgYXJncz0oYWxwaGEsIHosIHEpLCB4dG9sPTFlLTEzKSkpCiAgICByZXR1cm4gcm9vdHMKCgpkZWYgdW5kZXJ3b29kX2NsYXNzMihpbnAsIGRpc3QpOgogICAgIiIiQ2xhc3MgMiBtaW5pbXVtIHJlZmx1eCwgZm9sbG93aW5nIFNlYWRlciBFeGFtcGxlIDkuNS4KCiAgICBEaXN0cmlidXRpbmcgY29tcG9uZW50czogdGhlIHR3byBrZXlzLCBldmVyeSBjb21wb25lbnQgbGlnaHRlciB0aGFuCiAgICB0aGUgbGlnaHQga2V5ICh0YWtlbiB0byBwYXNzIHdob2xseSBpbnRvIHRoZSBkaXN0aWxsYXRlKSwgYW5kIHRoZQogICAgc2luZ2xlIG5vbi1rZXkgaW1tZWRpYXRlbHkgaGVhdmllciB0aGFuIHRoZSBoZWF2eSBrZXksIHdob3NlCiAgICBkaXN0aWxsYXRlIGZsb3cgaXMgYW4gdW5rbm93bi4gIEFsbCBoZWF2aWVyIGNvbXBvbmVudHMgYXJlIHRha2VuIHRvCiAgICBwYXNzIHdob2xseSBpbnRvIHRoZSBib3R0b21zLiAgVW5rbm93bnM6IHRoZSBkaXN0aWxsYXRlIHJhdGUgRAogICAgKGxibW9sL2gpLCB0aGUgbWluaW11bSBpbnRlcm5hbCByZWZsdXggcmF0ZSBMbWluIChsYm1vbC9oKSwgYW5kIHRoZQogICAgZGlzdGlsbGF0ZSBmbG93IG9mIHRoZSBkaXN0cmlidXRpbmcgbm9uLWtleTsgZXF1YXRpb25zOiB0aGUKICAgIFVuZGVyd29vZCBkaXN0aWxsYXRlIGVxdWF0aW9uIGF0IHRoZSB0d28gcm9vdHMgdGhhdCBicmFja2V0IHRoZQogICAgaGVhdnkga2V5LCBhbmQgdGhlIG92ZXJhbGwgYmFsYW5jZSBEID0gc3VtIG9mIGRpc3RpbGxhdGUgZmxvd3MuCiAgICBSZXR1cm5zIGRpY3Qgd2l0aCB0aGV0YV91c2VkICh0aGUgdHdvIHJvb3RzKSwgcl9taW4gPSBMbWluL0QsCiAgICBkX2Rpc3Rfbm9ua2V5LCBEIGFuZCBMbWluLgogICAgIiIiCiAgICBmID0gbnAuYXNhcnJheShpbnBbImZlZWQiXSwgZmxvYXQpCiAgICBhID0gbnAuYXNhcnJheShpbnBbImFscGhhIl0sIGZsb2F0KQogICAgbGssIGhrID0gaW50KGlucFsibGsiXSksIGludChpbnBbImhrIl0pCiAgICB6ID0gZiAvIGYuc3VtKCkKICAgIHJvb3RzID0gdW5kZXJ3b29kX3Jvb3RzKGEsIHosIGZsb2F0KGlucFsicSJdKSkKICAgICMgVGhlIHR3byByb290cyB1c2VkIGJyYWNrZXQgdGhlIGhlYXZ5IGtleSBmcm9tIGFib3ZlIGFuZCBiZWxvdy4KICAgIGFib3ZlID0gW3QgZm9yIHQgaW4gcm9vdHMgaWYgYVtoa10gPCB0IDwgYVtsa11dCiAgICBiZWxvdyA9IFt0IGZvciB0IGluIHJvb3RzIGlmIGFbaGsgKyAxXSA8IHQgPCBhW2hrXV0KICAgIGlmIGxlbihhYm92ZSkgIT0gMSBvciBsZW4oYmVsb3cpICE9IDE6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiVGhlIFVuZGVyd29vZCByb290cyBicmFja2V0aW5nIHRoZSBoZWF2eSBrZXkgIgogICAgICAgICAgICAgICAgICAgICAgICAgIndlcmUgbm90IGZvdW5kIHVuaXF1ZWx5OyB0aGUgc2VwYXJhdGlvbiBhcyAiCiAgICAgICAgICAgICAgICAgICAgICAgICAic3BlY2lmaWVkIGhhcyBubyBDbGFzcyAyIHNvbHV0aW9uIG9mIHRoZSAiCiAgICAgICAgICAgICAgICAgICAgICAgICAiZm9ybSB1c2VkIG9uIHRoaXMgcGFnZS4iKQogICAgdGhldGFzID0gW2Fib3ZlWzBdLCBiZWxvd1swXV0KICAgIGogPSBoayArIDEgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIyBkaXN0cmlidXRpbmcgbm9uLWtleSBpbmRleAogICAga25vd24gPSB7aTogZmxvYXQoZltpXSkgZm9yIGkgaW4gcmFuZ2UobGspfSAgICMgbGlnaHRlciB0aGFuIExLOiBhbGwgdXAKICAgIGtub3duW2xrXSA9IGZsb2F0KGlucFsiZF9sayJdKQogICAga25vd25baGtdID0gZmxvYXQoaW5wWyJkX2hrIl0pCiAgICAjIFVua25vd24gdmVjdG9yIHggPSBbRCwgTG1pbiwgZF9qXTsgZm9yIGVhY2ggdGhldGE6CiAgICAjICAgc3VtX2tub3duIGFscGhhX2kgZF9pLyhhbHBoYV9pIC0gdGhldGEpCiAgICAjICAgICArIGFscGhhX2ogZF9qLyhhbHBoYV9qIC0gdGhldGEpIC0gRCAtIExtaW4gPSAwCiAgICByb3dzLCByaHMgPSBbXSwgW10KICAgIGZvciB0aCBpbiB0aGV0YXM6CiAgICAgICAgcm93ID0gWy0xLjAsIC0xLjAsIGFbal0gLyAoYVtqXSAtIHRoKV0KICAgICAgICB2YWwgPSAtc3VtKGFbaV0gKiBkdiAvIChhW2ldIC0gdGgpIGZvciBpLCBkdiBpbiBrbm93bi5pdGVtcygpKQogICAgICAgIHJvd3MuYXBwZW5kKHJvdykKICAgICAgICByaHMuYXBwZW5kKHZhbCkKICAgIHJvd3MuYXBwZW5kKFsxLjAsIDAuMCwgLTEuMF0pCiAgICByaHMuYXBwZW5kKHN1bShrbm93bi52YWx1ZXMoKSkpCiAgICBzb2wgPSBucC5saW5hbGcuc29sdmUobnAuYXJyYXkocm93cyksIG5wLmFycmF5KHJocykpCiAgICBELCBMbWluLCBkX2ogPSAoZmxvYXQodikgZm9yIHYgaW4gc29sKQogICAgaWYgRCA8PSAwIG9yIExtaW4gPD0gMCBvciBkX2ogPCAwIG9yIGRfaiA+IGZbal06CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiVGhlIENsYXNzIDIgc29sdmUgZ2F2ZSBhIG5vbi1waHlzaWNhbCByZXN1bHQgIgogICAgICAgICAgICAgICAgICAgICAgICAgIihhIG5lZ2F0aXZlIGZsb3cgb3IgYSByZWZsdXggcmF0ZSBiZWxvdyB6ZXJvKTsgIgogICAgICAgICAgICAgICAgICAgICAgICAgImNoZWNrIHRoZSBrZXkgc3BsaXRzIGFuZCB0aGUgZmVlZCBxdWFsaXR5LiIpCiAgICByZXR1cm4geyJ0aGV0YV9hbGwiOiByb290cywgInRoZXRhX3VzZWQiOiB0aGV0YXMsCiAgICAgICAgICAgICJyX21pbiI6IExtaW4gLyBELCAibF9taW4iOiBMbWluLCAiRCI6IEQsICJkX2Rpc3Rfbm9ua2V5IjogZF9qLAogICAgICAgICAgICAiZGlzdF9ub25rZXlfaW5kZXgiOiBqfQoKCmRlZiBnaWxsaWxhbmQocl9taW4sIG5fbWluLCBtdWx0KToKICAgICIiIkVkdWxqZWUncyBlcXVhdGlvbiBmb3IgdGhlIEdpbGxpbGFuZCBjb3JyZWxhdGlvbiAoU2VhZGVyCiAgICBFcS4gOS0zMykuICBYID0gKFIgLSBSbWluKS8oUiArIDEpIGFuZCBZID0gKE4gLSBObWluKS8oTiArIDEpIGFyZQogICAgZGltZW5zaW9ubGVzcyBjb3JyZWxhdGlvbiB2YXJpYWJsZXM7IFIgPSBtdWx0ICogUm1pbi4iIiIKICAgIFIgPSBtdWx0ICogcl9taW4KICAgIFggPSAoUiAtIHJfbWluKSAvIChSICsgMS4wKQogICAgWSA9IDEuMCAtIG5wLmV4cCgoKDEuMCArIDU0LjQgKiBYKSAqIChYIC0gMS4wKSkKICAgICAgICAgICAgICAgICAgICAgLyAoKDExLjAgKyAxMTcuMiAqIFgpICogbnAuc3FydChYKSkpCiAgICBOID0gKG5fbWluICsgWSkgLyAoMS4wIC0gWSkKICAgIHJldHVybiB7IlIiOiBmbG9hdChSKSwgIlgiOiBmbG9hdChYKSwgIlkiOiBmbG9hdChZKSwgIk4iOiBmbG9hdChOKX0KCgpkZWYgZmVlZF9zdGFnZShpbnAsIGRpc3QsIG5fc3RhZ2VzKToKICAgICIiIkZlZWQtc3RhZ2UgbG9jYXRpb24uICBLaXJrYnJpZGUncyBlcXVhdGlvbiBnaXZlcyB0aGUgcmF0aW8KICAgIE5SL05TIG9mIGVxdWlsaWJyaXVtIHN0YWdlcyBhYm92ZSB0aGUgZmVlZCAocmVjdGlmeWluZyBzZWN0aW9uKSB0bwogICAgc3RhZ2VzIGJlbG93IGl0IChzdHJpcHBpbmcgc2VjdGlvbiksIGNvdW50aW5nIHRoZSBwYXJ0aWFsIHJlYm9pbGVyCiAgICBpbiB0aGUgc3RyaXBwaW5nIHNlY3Rpb24gYW5kIGV4Y2x1ZGluZyB0aGUgdG90YWwgY29uZGVuc2VyLiAgVGhlCiAgICBGZW5za2Ugc2VjdGlvbiByYXRpbyBhcHBsaWVzIHRoZSBGZW5za2UgZXF1YXRpb24gdG8gZWFjaCBzZWN0aW9uCiAgICBzZXBhcmF0ZWx5IGF0IHRvdGFsIHJlZmx1eC4gIE1vbGUgZnJhY3Rpb25zOiB6IGluIHRoZSBmZWVkLCB4RCBpbgogICAgdGhlIGRpc3RpbGxhdGUsIHhCIGluIHRoZSBib3R0b21zIChhbGwgZGltZW5zaW9ubGVzcykuIiIiCiAgICBmID0gbnAuYXNhcnJheShpbnBbImZlZWQiXSwgZmxvYXQpCiAgICBsaywgaGsgPSBpbnQoaW5wWyJsayJdKSwgaW50KGlucFsiaGsiXSkKICAgIGQsIGIgPSBkaXN0WyJkIl0sIGRpc3RbImIiXQogICAgeiA9IGYgLyBmLnN1bSgpCiAgICB4RCA9IGQgLyBkLnN1bSgpCiAgICB4QiA9IGIgLyBiLnN1bSgpCiAgICBraXJrID0gKCh6W2hrXSAvIHpbbGtdKSAqICh4Qltsa10gLyB4RFtoa10pICoqIDIKICAgICAgICAgICAgKiAoYi5zdW0oKSAvIGQuc3VtKCkpKSAqKiAwLjIwNgogICAgYV9sa19oayA9IGRpc3RbImFscGhhX2xrX2hrIl0KICAgIG5yX21pbiA9IChucC5sb2cxMCgoeERbbGtdIC8geERbaGtdKSAqICh6W2hrXSAvIHpbbGtdKSkKICAgICAgICAgICAgICAvIG5wLmxvZzEwKGFfbGtfaGspKQogICAgbnNfbWluID0gKG5wLmxvZzEwKCh6W2xrXSAvIHpbaGtdKSAqICh4Qltoa10gLyB4Qltsa10pKQogICAgICAgICAgICAgIC8gbnAubG9nMTAoYV9sa19oaykpCiAgICBmZW5za2VfcmF0aW8gPSBucl9taW4gLyBuc19taW4KICAgIG91dCA9IHt9CiAgICBmb3IgbGFiZWwsIHJhdGlvIGluICgoImtpcmticmlkZSIsIGtpcmspLCAoImZlbnNrZSIsIGZlbnNrZV9yYXRpbykpOgogICAgICAgIG5zID0gbl9zdGFnZXMgLyAoMS4wICsgcmF0aW8pCiAgICAgICAgb3V0W2xhYmVsXSA9IHsicmF0aW8iOiBmbG9hdChyYXRpbyksICJuX3JlY3QiOiBmbG9hdChyYXRpbyAqIG5zKSwKICAgICAgICAgICAgICAgICAgICAgICJuX3N0cmlwIjogZmxvYXQobnMpfQogICAgcmV0dXJuIG91dAoKCmRlZiBwbGFpbihvKToKICAgICIiIm51bXB5IHZhbHVlcyAtPiBKU09OLWZyaWVuZGx5IHBsYWluIGRhdGEgKE5hTi9pbmYgLT4gTm9uZSkuIiIiCiAgICBpZiBpc2luc3RhbmNlKG8sIG5wLm5kYXJyYXkpOgogICAgICAgIHJldHVybiBbcGxhaW4odikgZm9yIHYgaW4gby50b2xpc3QoKV0gaWYgby5uZGltIGVsc2UgcGxhaW4oby5pdGVtKCkpCiAgICBpZiBpc2luc3RhbmNlKG8sIChsaXN0LCB0dXBsZSkpOgogICAgICAgIHJldHVybiBbcGxhaW4odikgZm9yIHYgaW4gb10KICAgIGlmIGlzaW5zdGFuY2UobywgZGljdCk6CiAgICAgICAgcmV0dXJuIHtrOiBwbGFpbih2KSBmb3IgaywgdiBpbiBvLml0ZW1zKCl9CiAgICBpZiBpc2luc3RhbmNlKG8sIChucC5mbG9hdGluZywgZmxvYXQpKToKICAgICAgICB2ID0gZmxvYXQobykKICAgICAgICByZXR1cm4gdiBpZiBucC5pc2Zpbml0ZSh2KSBlbHNlIE5vbmUKICAgIGlmIGlzaW5zdGFuY2UobywgKG5wLmludGVnZXIsKSk6CiAgICAgICAgcmV0dXJuIGludChvKQogICAgcmV0dXJuIG8KCgpkZWYgX2ZpZ19sYXlvdXQoeF90aXRsZSwgeV90aXRsZSk6CiAgICByZXR1cm4gZGljdCh0ZW1wbGF0ZT0icGxvdGx5X3doaXRlIiwKICAgICAgICAgICAgICAgIHhheGlzPWRpY3QodGl0bGU9eF90aXRsZSksIHlheGlzPWRpY3QodGl0bGU9eV90aXRsZSksCiAgICAgICAgICAgICAgICBsZWdlbmQ9ZGljdCh4PTEuMDIsIHk9MS4wLCB4YW5jaG9yPSJsZWZ0IiwgeWFuY2hvcj0idG9wIiksCiAgICAgICAgICAgICAgICBtYXJnaW49ZGljdChsPTYwLCByPTE3MCwgdD0zMCwgYj01NSkpCgoKZGVmIHJ1bl9jYXNlKGlucCk6CiAgICAiIiJGdWxsIEZVRyBjYWxjdWxhdGlvbiBmb3Igb25lIGlucHV0IHNldC4gIFJldHVybnMgYSBwbGFpbi1kYXRhCiAgICBkaWN0OiBtZXRyaWNzLCB0aGUgZmxvdyB0YWJsZSwgYW5kIHRoZSB0aHJlZSBBcHAgZmlndXJlcyBhcyBQbG90bHkKICAgIHRyYWNlL2xheW91dCBkaWN0cy4iIiIKICAgIGRpc3QgPSBmZW5za2UoaW5wKQogICAgdW5kID0gdW5kZXJ3b29kX2NsYXNzMihpbnAsIGRpc3QpCiAgICBnaWwgPSBnaWxsaWxhbmQodW5kWyJyX21pbiJdLCBkaXN0WyJuX21pbiJdLCBmbG9hdChpbnBbIm11bHQiXSkpCiAgICBuX3JvdW5kID0gaW50KG5wLmNlaWwoZ2lsWyJOIl0pKQogICAgdHJheXNfdGhlb3JldGljYWwgPSBuX3JvdW5kIC0gMSAgICAgICAgIyByZWJvaWxlciBpcyBvbmUgb2YgdGhlIHN0YWdlcwogICAgZWZmID0gZmxvYXQoaW5wWyJlZmZpY2llbmN5Il0pCiAgICB0cmF5c19hY3R1YWwgPSBpbnQobnAuY2VpbCh0cmF5c190aGVvcmV0aWNhbCAvIGVmZikpCiAgICBmcyA9IGZlZWRfc3RhZ2UoaW5wLCBkaXN0LCBmbG9hdChuX3JvdW5kKSkKICAgIGYgPSBucC5hc2FycmF5KGlucFsiZmVlZCJdLCBmbG9hdCkKICAgIGEgPSBucC5hc2FycmF5KGlucFsiYWxwaGEiXSwgZmxvYXQpCiAgICB6ID0gZiAvIGYuc3VtKCkKCiAgICAjIEZpZy4gQTogR2lsbGlsYW5kIGN1cnZlIChFZHVsamVlKSB3aXRoIHRoZSBvcGVyYXRpbmcgcG9pbnQuCiAgICBtdWx0cyA9IG5wLmNvbmNhdGVuYXRlKChbMS4wMDFdLCBucC5saW5zcGFjZSgxLjAxLCA0LjAsIDEyMCkpKQogICAgeHMsIHlzID0gW10sIFtdCiAgICBmb3IgbSBpbiBtdWx0czoKICAgICAgICBnID0gZ2lsbGlsYW5kKHVuZFsicl9taW4iXSwgZGlzdFsibl9taW4iXSwgZmxvYXQobSkpCiAgICAgICAgeHMuYXBwZW5kKGdbIlgiXSkKICAgICAgICB5cy5hcHBlbmQoZ1siWSJdKQogICAgZmlnX2dpbGxpbGFuZCA9IHsKICAgICAgICAiZGF0YSI6IFsKICAgICAgICAgICAgZGljdCh0eXBlPSJzY2F0dGVyIiwgeD14cywgeT15cywgbW9kZT0ibGluZXMiLAogICAgICAgICAgICAgICAgIG5hbWU9IkdpbGxpbGFuZCBjb3JyZWxhdGlvbiAoRWR1bGplZSBlcXVhdGlvbikiLAogICAgICAgICAgICAgICAgIGxpbmU9ZGljdChjb2xvcj0iIzAwNzJCMiIsIHdpZHRoPTIpKSwKICAgICAgICAgICAgZGljdCh0eXBlPSJzY2F0dGVyIiwgeD1bZ2lsWyJYIl1dLCB5PVtnaWxbIlkiXV0sCiAgICAgICAgICAgICAgICAgbW9kZT0ibWFya2VycyIsIG5hbWU9Ik9wZXJhdGluZyBwb2ludCIsCiAgICAgICAgICAgICAgICAgbWFya2VyPWRpY3QoY29sb3I9IiNENTVFMDAiLCBzaXplPTExLCBzeW1ib2w9ImNpcmNsZSIsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgbGluZT1kaWN0KGNvbG9yPSIjN2EzNDAwIiwgd2lkdGg9MSkpKV0sCiAgICAgICAgImxheW91dCI6IF9maWdfbGF5b3V0KCJYIChkaW1lbnNpb25sZXNzKSIsICJZIChkaW1lbnNpb25sZXNzKSIpfQoKICAgICMgRmlnLiBCOiBVbmRlcndvb2QgZmVlZCBmdW5jdGlvbiBvbiBlYWNoIHZvbGF0aWxpdHkgaW50ZXJ2YWwsCiAgICAjIGNsaXBwZWQgZm9yIGRpc3BsYXk7IGFsbCByb290cyBzaG93biwgdGhlIHR3byB1c2VkIG1hcmtlZC4KICAgIHRyYWNlcyA9IFtdCiAgICBhX3NvcnRlZCA9IG5wLnNvcnQoYSlbOjotMV0KICAgIGZvciBoaSwgbG8gaW4gemlwKGFfc29ydGVkWzotMV0sIGFfc29ydGVkWzE6XSk6CiAgICAgICAgdGggPSBucC5saW5zcGFjZShsbyArIDFlLTQsIGhpIC0gMWUtNCwgNjApCiAgICAgICAgdXUgPSBucC5hcnJheShbdW5kZXJ3b29kX2Z1bmN0aW9uKHQsIGEsIHosIGZsb2F0KGlucFsicSJdKSkKICAgICAgICAgICAgICAgICAgICAgICBmb3IgdCBpbiB0aF0pCiAgICAgICAgdXUgPSBucC5jbGlwKHV1LCAtNi4wLCA2LjApCiAgICAgICAgdHJhY2VzLmFwcGVuZChkaWN0KHR5cGU9InNjYXR0ZXIiLCB4PXRoLnRvbGlzdCgpLCB5PXV1LnRvbGlzdCgpLAogICAgICAgICAgICAgICAgICAgICAgICAgICBtb2RlPSJsaW5lcyIsIHNob3dsZWdlbmQ9RmFsc2UsCiAgICAgICAgICAgICAgICAgICAgICAgICAgIGxpbmU9ZGljdChjb2xvcj0iIzAwNzJCMiIsIHdpZHRoPTEuNSkpKQogICAgdHJhY2VzLmFwcGVuZChkaWN0KAogICAgICAgIHR5cGU9InNjYXR0ZXIiLCB4PXVuZFsidGhldGFfYWxsIl0sCiAgICAgICAgeT1bMC4wXSAqIGxlbih1bmRbInRoZXRhX2FsbCJdKSwgbW9kZT0ibWFya2VycyIsCiAgICAgICAgbmFtZT0iQWxsIHJvb3RzIG9mIHRoZSBmZWVkIGVxdWF0aW9uIiwKICAgICAgICBtYXJrZXI9ZGljdChjb2xvcj0iIzk5OTk5OSIsIHNpemU9OCwgc3ltYm9sPSJjaXJjbGUtb3BlbiIsCiAgICAgICAgICAgICAgICAgICAgbGluZT1kaWN0KHdpZHRoPTIpKSkpCiAgICB0cmFjZXMuYXBwZW5kKGRpY3QoCiAgICAgICAgdHlwZT0ic2NhdHRlciIsIHg9dW5kWyJ0aGV0YV91c2VkIl0sIHk9WzAuMCwgMC4wXSwKICAgICAgICBtb2RlPSJtYXJrZXJzIiwgbmFtZT0iUm9vdHMgdXNlZCBmb3IgdGhlIENsYXNzIDIgc29sdmUiLAogICAgICAgIG1hcmtlcj1kaWN0KGNvbG9yPSIjRDU1RTAwIiwgc2l6ZT0xMSwgc3ltYm9sPSJjaXJjbGUiKSkpCiAgICBmaWdfdW5kZXJ3b29kID0gewogICAgICAgICJkYXRhIjogdHJhY2VzLAogICAgICAgICJsYXlvdXQiOiBfZmlnX2xheW91dCgidGhldGEgKGRpbWVuc2lvbmxlc3MpIiwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIlVuZGVyd29vZCBmZWVkIGZ1bmN0aW9uIChkaW1lbnNpb25sZXNzKSIpfQoKICAgICMgRmlnLiBDOiBjb21wb25lbnQgZGlzdHJpYnV0aW9uLCBsb2dhcml0aG1pYyBzY2FsZSAoZmxvd3Mgc3BhbgogICAgIyAxMiBvcmRlcnMgb2YgbWFnbml0dWRlKTsgZG91YmxlIGVuY29kaW5nIGJ5IGNvbG91ciBhbmQgcGF0dGVybi4KICAgIG5hbWVzID0gbGlzdChpbnBbIm5hbWVzIl0pCiAgICBmaWdfZGlzdCA9IHsKICAgICAgICAiZGF0YSI6IFsKICAgICAgICAgICAgZGljdCh0eXBlPSJiYXIiLCB4PW5hbWVzLCB5PW5wLm1heGltdW0oZGlzdFsiZCJdLCAxZS0xMikudG9saXN0KCksCiAgICAgICAgICAgICAgICAgbmFtZT0iRGlzdGlsbGF0ZSBmbG93IHJhdGUiLCBtYXJrZXI9ZGljdChjb2xvcj0iIzAwNzJCMiIpKSwKICAgICAgICAgICAgZGljdCh0eXBlPSJiYXIiLCB4PW5hbWVzLCB5PW5wLm1heGltdW0oZGlzdFsiYiJdLCAxZS0xMikudG9saXN0KCksCiAgICAgICAgICAgICAgICAgbmFtZT0iQm90dG9tcyBmbG93IHJhdGUiLAogICAgICAgICAgICAgICAgIG1hcmtlcj1kaWN0KGNvbG9yPSIjRDU1RTAwIiwgcGF0dGVybj1kaWN0KHNoYXBlPSIvIikpKV0sCiAgICAgICAgImxheW91dCI6IGRpY3QodGVtcGxhdGU9InBsb3RseV93aGl0ZSIsIGJhcm1vZGU9Imdyb3VwIiwKICAgICAgICAgICAgICAgICAgICAgICB4YXhpcz1kaWN0KHRpdGxlPSJDb21wb25lbnQiKSwKICAgICAgICAgICAgICAgICAgICAgICB5YXhpcz1kaWN0KHRpdGxlPSJGbG93IHJhdGUgKGxibW9sL2gpIiwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHR5cGU9ImxvZyIpLAogICAgICAgICAgICAgICAgICAgICAgIGxlZ2VuZD1kaWN0KHg9MS4wMiwgeT0xLjAsIHhhbmNob3I9ImxlZnQiLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHlhbmNob3I9InRvcCIpLAogICAgICAgICAgICAgICAgICAgICAgIG1hcmdpbj1kaWN0KGw9NjAsIHI9MTcwLCB0PTMwLCBiPTU1KSl9CgogICAgbWV0cmljcyA9IHsKICAgICAgICAibl9taW4iOiBkaXN0WyJuX21pbiJdLCAiYWxwaGFfbGtfaGsiOiBkaXN0WyJhbHBoYV9sa19oayJdLAogICAgICAgICJEX2ZlbnNrZSI6IGZsb2F0KGRpc3RbImQiXS5zdW0oKSksICJCX2ZlbnNrZSI6IGZsb2F0KGRpc3RbImIiXS5zdW0oKSksCiAgICAgICAgInRoZXRhX3VzZWQiOiB1bmRbInRoZXRhX3VzZWQiXSwgInJfbWluIjogdW5kWyJyX21pbiJdLAogICAgICAgICJEX2NsYXNzMiI6IHVuZFsiRCJdLCAiZF9kaXN0X25vbmtleSI6IHVuZFsiZF9kaXN0X25vbmtleSJdLAogICAgICAgICJkaXN0X25vbmtleV9uYW1lIjogbmFtZXNbdW5kWyJkaXN0X25vbmtleV9pbmRleCJdXSwKICAgICAgICAiUiI6IGdpbFsiUiJdLCAiWCI6IGdpbFsiWCJdLCAiWSI6IGdpbFsiWSJdLCAiTiI6IGdpbFsiTiJdLAogICAgICAgICJuX3JvdW5kIjogbl9yb3VuZCwgInRyYXlzX3RoZW9yZXRpY2FsIjogdHJheXNfdGhlb3JldGljYWwsCiAgICAgICAgInRyYXlzX2FjdHVhbCI6IHRyYXlzX2FjdHVhbCwKICAgICAgICAiZmVlZF9raXJrYnJpZGUiOiBmc1sia2lya2JyaWRlIl0sICJmZWVkX2ZlbnNrZSI6IGZzWyJmZW5za2UiXSwKICAgIH0KICAgIHJldHVybiBwbGFpbih7CiAgICAgICAgIm1ldHJpY3MiOiBtZXRyaWNzLAogICAgICAgICJuYW1lcyI6IG5hbWVzLAogICAgICAgICJmZWVkIjogZi50b2xpc3QoKSwgImFscGhhIjogYS50b2xpc3QoKSwKICAgICAgICAiZCI6IGRpc3RbImQiXS50b2xpc3QoKSwgImIiOiBkaXN0WyJiIl0udG9saXN0KCksCiAgICAgICAgImZpZ3MiOiB7ImdpbGxpbGFuZCI6IGZpZ19naWxsaWxhbmQsICJ1bmRlcndvb2QiOiBmaWdfdW5kZXJ3b29kLAogICAgICAgICAgICAgICAgICJkaXN0cmlidXRpb24iOiBmaWdfZGlzdH0sCiAgICB9KQoKCmRlZiBjbGFzczFfY2hlY2soKToKICAgICIiIlNlYWRlciBFeGFtcGxlIDkuNCAoQ2xhc3MgMSBlc3RpbWF0ZSksIGZyb20gdGhlIHF1YW50aXRpZXMgZ2l2ZW4KICAgIGluIEV4YW1wbGVzIDkuMSBhbmQgOS40IG9mIHRoZSBzb3VyY2UgdGV4dC4gIEZlZWQgbGlxdWlkIHJhdGUKICAgIDc1OSBsYm1vbC9oIG9mIGEgZmVlZCByYXRlIG9mIDg3Ni4zIGxibW9sL2g7IGZlZWQtbGlxdWlkIGZsb3dzIG9mCiAgICB0aGUgbGlnaHQga2V5IDM0NS40MSBsYm1vbC9oIGFuZCBvZiB0aGUgaGVhdnkga2V5IDMxLjI4IGxibW9sL2g7CiAgICByZWxhdGl2ZSB2b2xhdGlsaXR5IG9mIHRoZSBrZXlzIGF0IGZlZWQgY29uZGl0aW9ucyAxLjk2NzsKICAgIGRpc3RpbGxhdGUgZmxvd3Mgb2YgdGhlIGtleXMgNDQyIGFuZCAxMyBsYm1vbC9oLiAgUmV0dXJucyB0aGUKICAgIG1pbmltdW0gaW50ZXJuYWwgcmVmbHV4IHBlciB1bml0IGZlZWQsIGl0cyBjb252ZXJzaW9uIHBlciB1bml0CiAgICBkaXN0aWxsYXRlIGF0IHRoZSBGZW5za2UgZGlzdGlsbGF0ZSByYXRlIDQ2OC45NSBsYm1vbC9oLCBhbmQKICAgIFNlYWRlcidzIHByaW50ZWQgcGVyLWRpc3RpbGxhdGUgdmFsdWUsIHdoaWNoIGRvZXMgbm90IGZvbGxvdyBmcm9tCiAgICB0aGUgcHJpbnRlZCBwZXItZmVlZCB2YWx1ZSAoc2VlIHRoZSBUaGVvcnkgcGFuZWwpLiIiIgogICAgbF9wZXJfZiA9ICg3NTkuMCAvIDg3Ni4zKSAqICgoNDQyLjAgLyAzNDUuNDEpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIC0gMS45NjcgKiAoMTMuMCAvIDMxLjI4KSkgLyAoMS45NjcgLSAxLjApCiAgICBwZXJfZCA9IGxfcGVyX2YgKiA4NzYuMyAvIDQ2OC45NQogICAgcmV0dXJuIHsibF9wZXJfZiI6IGZsb2F0KGxfcGVyX2YpLCAicGVyX2RfcmVjb21wdXRlZCI6IGZsb2F0KHBlcl9kKSwKICAgICAgICAgICAgInBlcl9kX3ByaW50ZWQiOiAwLjg2NH0K").decode("utf-8")
    _mod = _types.ModuleType('fug')
    exec(compile(FUG_SRC, 'fug', 'exec'), _mod.__dict__)
    _sys.modules['fug'] = _mod
    F = _mod
    def figure(data, layout=None, **kw):
        return go.Figure(data=data, layout=layout or kw)
    return (mo, np, go, F, FUG_SRC, figure)


@app.cell
def _(mo):
    mo.md(r"""
    # Fenske-Underwood-Gilliland (FUG) Shortcut Distillation

    An editable breakdown of the FUG shortcut design of a multicomponent distillation column, worked on the debutanizer of Seader, Henley & Roper, Separation Process Principles, 4th ed. (2016), Chapter 9. Edit a value in a cell and re-run; every downstream cell recomputes. Flow rates are in lbmol/h (pound-moles per hour).
    """)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 1: Feed, key components and specified splits

    The column separates a feed of eight hydrocarbon components, listed in order of decreasing volatility. The symbol $f_i$ denotes the molar flow rate of component $i$ in the feed, in lbmol/h (pound-moles per hour). The symbol $F$ denotes the total feed rate, the sum of the $f_i$, in lbmol/h. The symbol $z_i$ denotes the mole fraction of component $i$ in the feed, $z_i = f_i / F$, dimensionless.

    Two adjacent components are chosen as the key components, whose split between the products is specified. The light key (LK) is n-butane: it is the heaviest component that must pass mainly into the distillate. The heavy key (HK) is isopentane: it is the lightest component that must pass mainly into the bottoms. The symbol $d_i$ denotes the molar flow rate of component $i$ in the distillate and $b_i$ its molar flow rate in the bottoms, both in lbmol/h, with $f_i = d_i + b_i$ for every component. The specified splits are $d = 442$ and $b = 6$ lbmol/h for the light key, and $d = 13$ and $b = 23$ lbmol/h for the heavy key.

    The symbol $\alpha_i$ denotes the mean relative volatility of component $i$ with respect to the heavy key, dimensionless: the ratio of the distribution coefficients (the equilibrium vapour-to-liquid mole-fraction ratios) of component $i$ and the heavy key, geometrically averaged between the distillate and bottoms conditions of Seader's Example 9.1. By this definition $\alpha = 1$ for the heavy key itself. One volatility set is used in every step of this walkthrough. The column has a total condenser, which is not counted as an equilibrium stage, and a partial reboiler, which is counted as one equilibrium stage.
    """)


@app.cell
def _(F, figure, np):
    inp = F.default_inputs()
    feed_arr = np.array(inp["feed"])
    print("total feed rate F =", feed_arr.sum(), "lbmol/h")
    for nm1, fv1, av1 in zip(inp["names"], inp["feed"], inp["alpha"]):
        print(f"{nm1:12s} f = {fv1:7.1f} lbmol/h   alpha = {av1:g}")
    figure([dict(type="bar", x=inp["names"],
                 y=(feed_arr / feed_arr.sum()).tolist(),
                 marker=dict(color="#0072B2"), name="Feed mole fraction")],
           xaxis=dict(title="Component"),
           yaxis=dict(title="Feed mole fraction z (dimensionless)"),
           template="plotly_white", showlegend=False)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 2: Fenske equation: minimum stages at total reflux

    The minimum number of equilibrium stages, $N_{min}$ (dimensionless, with the stage counting stated in Step 1), is reached at total reflux, when all condensed vapour is returned to the column and no products are withdrawn. The Fenske equation {{cite:fenske-1932}} gives $N_{min}$ from the key splits and the relative volatility of the light key with respect to the heavy key, $\alpha_{LK,HK}$ (dimensionless), here equal to the tabulated $\alpha$ of the light key because the heavy key is the reference component:

    $$N_{min} = \frac{\log_{10}\left[\left(d_{LK}/b_{LK}\right)\left(b_{HK}/d_{HK}\right)\right]}{\log_{10} \alpha_{LK,HK}}$$

    Each bracket is the split ratio of one key between the two products. A sharper specified separation, or a smaller $\alpha_{LK,HK}$, requires more stages. The equation is exact only when the relative volatility is constant through the column; the mean volatility of Step 1 is the approximation used here.
    """)


@app.cell
def _(F, inp):
    dist = F.fenske(inp)
    n_min = dist["n_min"]
    print("alpha of light key w.r.t. heavy key:", dist["alpha_lk_hk"])
    print("minimum stages Nmin =", round(n_min, 4), " (Seader: 7.82)")


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 3: Distribution of the non-key components

    The Fenske equation is not restricted to the keys. For any component $i$, applied against the heavy key as reference, it gives the split ratio $d_i / b_i$ at total reflux:

    $$\frac{d_i}{b_i} = \frac{d_{HK}}{b_{HK}} \; \alpha_i^{\,N_{min}}$$

    Combined with $f_i = d_i + b_i$, this fixes every non-key flow. Following Seader's guidance, the smaller of $d_i$ and $b_i$ is computed from the equation first and the larger by difference, which keeps the small flows accurate; several distillate flows are below $10^{-6}$ lbmol/h. The chart uses a logarithmic scale because the flows span twelve orders of magnitude; colour and pattern both encode the product, so the chart reads in greyscale. These total-reflux flows are the product distribution used by the rest of the method.
    """)


@app.cell
def _(dist, figure, inp, np):
    darr3 = dist["d"]
    barr3 = dist["b"]
    for nm3, fv3, dv3, bv3 in zip(inp["names"], inp["feed"], darr3, barr3):
        print(f"{nm3:12s} f = {fv3:8.2f}   d = {dv3:12.5g}   b = {bv3:10.3f}")
    print("totals: D =", round(darr3.sum(), 2), " B =", round(barr3.sum(), 2),
          " (Seader: 468.95 / 407.35 lbmol/h)")
    figure([dict(type="bar", x=inp["names"],
                 y=np.maximum(darr3, 1e-12).tolist(),
                 name="Distillate flow rate", marker=dict(color="#0072B2")),
            dict(type="bar", x=inp["names"],
                 y=np.maximum(barr3, 1e-12).tolist(), name="Bottoms flow rate",
                 marker=dict(color="#D55E00", pattern=dict(shape="/")))],
           xaxis=dict(title="Component"),
           yaxis=dict(title="Flow rate (lbmol/h)", type="log"),
           barmode="group", template="plotly_white",
           legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"))


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 4: Underwood Class 1 estimate and its failed check

    The minimum reflux ratio, $R_{min}$ (dimensionless), is the reflux ratio $R = L/D$ at which the stage count becomes unbounded, where $L$ denotes the liquid reflux flow rate and $D$ the distillate flow rate, both in lbmol/h. Underwood's method {{cite:underwood-1948}} distinguishes two classes of separation. In a Class 1 separation every component appears in both products. In a Class 2 separation at least one component appears in only one product.

    Seader's Example 9.4 evaluates the Class 1 shortcut for this feed from the feed-liquid flows of his Example 9.1 and obtains a minimum internal reflux rate of $0.414$ per unit feed. The check then fails: applied to the heavy non-keys, the Class 1 relations return negative distillate flow rates, and the isobutane distillate rate exceeds its feed rate. Only n-pentane, of the non-keys, genuinely distributes. The separation is therefore Class 2, and the Class 1 value is not used further, except as the comparison in Step 6.

    One further point is recorded in this cell's output. Seader prints the Class 1 ratio as $0.864$ per unit distillate. Converted at the distillate rate of Step 3, his per-feed value of $0.414$ gives $0.774$ per unit distillate, not $0.864$; the printed $0.864$ would follow from a feed rate of $978.7$ lbmol/h in place of $876.3$ lbmol/h. The page reports both values and uses neither for its headline result.
    """)


@app.cell
def _(F):
    c1res = F.class1_check()
    print("Class 1 minimum internal reflux per unit feed:",
          round(c1res["l_per_f"], 3), " (Seader: 0.414)")
    print("converted per unit distillate:",
          round(c1res["per_d_recomputed"], 3),
          " (Seader prints 0.864; the two do not agree)")


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 5: Underwood Class 2: roots and minimum reflux

    For a Class 2 separation, Underwood {{cite:underwood-1948}} introduces a parameter $\theta$ (dimensionless, on the same scale as the relative volatilities) defined separately in the rectifying and stripping pinch zones, and assumes the two values coincide. Eliminating the unknown pinch compositions gives the feed equation:

    $$\sum_i \frac{\alpha_i z_i}{\alpha_i - \theta} = 1 - q$$

    The symbol $q$ denotes the feed quality, dimensionless; for a two-phase feed it is the liquid fraction of the feed as it enters the column, and a subcooled liquid feed has $q$ above 1. In Seader's Example 9.1 the feed is flashed into the column and $13.4$ percent vaporises, so $q = 0.866$ here, not $1$. The left side is a sum over all components $i$ of the feed. The equation has one root $\theta$ in every interval between consecutive relative volatilities — seven roots for eight components — and the chart shows the left side minus the right side, clipped to the range shown, with every root marked.

    Only two roots enter the minimum-reflux solve for this separation: the root between the volatilities of the two keys, and the root between the heavy key and the next heavier component, n-pentane, the one distributing non-key. With the distillate flow rates of the distributing components written against each root,

    $$\sum_i \frac{\alpha_i d_i}{\alpha_i - \theta} = D + L_{min}$$

    where $L_{min}$ denotes the minimum internal reflux rate, in lbmol/h. The two root equations, together with the balance $D$ equals the sum of the distillate flow rates, are three linear equations in the three unknowns $D$, $L_{min}$, and the distillate flow rate of n-pentane. Components lighter than the light key are taken to pass wholly into the distillate, and components heavier than n-pentane wholly into the bottoms. The minimum reflux ratio is then $R_{min} = L_{min} / D$, dimensionless.
    """)


@app.cell
def _(F, dist, figure, inp, np):
    und = F.underwood_class2(inp, dist)
    print("all roots of the feed equation:",
          [round(t, 4) for t in und["theta_all"]])
    print("roots used:", [round(t, 4) for t in und["theta_used"]],
          " (Seader: 1.0443, 0.8587)")
    print("D =", round(und["D"], 1), "lbmol/h;  n-pentane in distillate =",
          round(und["d_dist_nonkey"], 2), "lbmol/h")
    print("Rmin =", round(und["r_min"], 3), " (Seader: 0.521)")
    z5 = np.array(inp["feed"]) / sum(inp["feed"])
    a5 = np.array(inp["alpha"])
    traces5 = []
    a_sorted5 = np.sort(a5)[::-1]
    for hi5, lo5 in zip(a_sorted5[:-1], a_sorted5[1:]):
        th5 = np.linspace(lo5 + 1e-4, hi5 - 1e-4, 60)
        uu5 = np.clip([F.underwood_function(t, a5, z5, inp["q"]) for t in th5],
                      -6, 6)
        traces5.append(dict(type="scatter", x=th5.tolist(), y=list(uu5),
                            mode="lines", showlegend=False,
                            line=dict(color="#0072B2", width=1.5)))
    traces5.append(dict(type="scatter", x=und["theta_all"],
                        y=[0.0] * len(und["theta_all"]), mode="markers",
                        name="All roots of the feed equation",
                        marker=dict(color="#999999", size=8,
                                    symbol="circle-open", line=dict(width=2))))
    traces5.append(dict(type="scatter", x=und["theta_used"], y=[0.0, 0.0],
                        mode="markers", name="Roots used for the Class 2 solve",
                        marker=dict(color="#D55E00", size=11, symbol="circle")))
    figure(traces5, xaxis=dict(title="theta (dimensionless)"),
           yaxis=dict(title="Underwood feed function (dimensionless)"),
           template="plotly_white",
           legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"))


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 6: Gilliland correlation: stages at the operating reflux

    The operating reflux ratio $R$ is chosen as a multiple of the minimum: $R = 1.3 \, R_{min}$ in Seader's Example 9.6, where $1.3$ is the reflux multiplier (dimensionless). The Gilliland correlation {{cite:gilliland-1940}} relates the stage count at finite reflux to the two limits, total reflux and minimum reflux, through the dimensionless variables $X = (R - R_{min}) / (R + 1)$ and $Y = (N - N_{min}) / (N + 1)$, where $N$ denotes the number of equilibrium stages at $R$, with the stage counting of Step 1. The page evaluates the correlation with the explicit equation of Eduljee {{cite:eduljee-1975}}, Seader's Eq. (9-33):

    $$Y = 1 - \exp\left(\frac{(1 + 54.4 X)(X - 1)}{(11 + 117.2 X)\sqrt{X}}\right)$$

    Solving $Y = (N - N_{min})/(N + 1)$ for $N$ gives the stage requirement. As $R$ approaches $R_{min}$, $X$ approaches $0$ and $N$ grows without bound; as $R$ grows without bound, $N$ approaches $N_{min}$. The correlation carries no feed-condition parameter, a known limitation Seader records: it is conservative for feeds of low $q$. The chart plots the curve for reflux multipliers from 1.001 to 4, not only the operating point.
    """)


@app.cell
def _(F, figure, inp, n_min, np, und):
    gil = F.gilliland(und["r_min"], n_min, inp["mult"])
    print("R =", round(gil["R"], 3), " X =", round(gil["X"], 4),
          " Y =", round(gil["Y"], 4))
    print("N =", round(gil["N"], 2), "equilibrium stages (Seader: 19.1)")
    mults6 = np.concatenate(([1.001], np.linspace(1.01, 4.0, 120)))
    xs6 = []
    ys6 = []
    for m6 in mults6:
        g6 = F.gilliland(und["r_min"], n_min, float(m6))
        xs6.append(g6["X"])
        ys6.append(g6["Y"])
    figure([dict(type="scatter", x=xs6, y=ys6, mode="lines",
                 name="Gilliland correlation (Eduljee equation)",
                 line=dict(color="#0072B2", width=2)),
            dict(type="scatter", x=[gil["X"]], y=[gil["Y"]], mode="markers",
                 name="Operating point",
                 marker=dict(color="#D55E00", size=11, symbol="circle"))],
           xaxis=dict(title="X (dimensionless)"),
           yaxis=dict(title="Y (dimensionless)"),
           template="plotly_white",
           legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"))


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 7: Feed-stage location and anchor checks

    The stage count is split between the rectifying section, above the feed, and the stripping section, below it. The symbol $N_R$ denotes the number of equilibrium stages in the rectifying section and $N_S$ the number in the stripping section, the partial reboiler counted in the stripping section. Kirkbride's empirical equation {{cite:kirkbride-1944}} gives the ratio

    $$\frac{N_R}{N_S} = \left[ \frac{z_{HK}}{z_{LK}} \left(\frac{x_{LK,B}}{x_{HK,D}}\right)^{2} \frac{B}{D} \right]^{0.206}$$

    where $x_{LK,B}$ denotes the mole fraction of the light key in the bottoms, $x_{HK,D}$ the mole fraction of the heavy key in the distillate, $B$ the total bottoms rate and $D$ the total distillate rate, both in lbmol/h. The second estimate applies the Fenske equation to each section separately at total reflux. Seader reports Kirkbride as the better of the two on his test problem, and it is listed first here. The total stage count is rounded up to a whole number before the split, because a column is built of whole stages; the reboiler is one of them, so the number of theoretical trays is one less than the rounded stage count.

    The anchor checks assert the values verified against Seader's Examples 9.2 to 9.6. A failed assertion means the calculation has drifted from the verified case.
    """)


@app.cell
def _(F, barr3, darr3, dist, feed_arr, gil, inp, n_min, und):
    res7 = F.run_case(inp)
    m7 = res7["metrics"]
    fs7 = F.feed_stage(inp, dist, float(m7["n_round"]))
    print("rounded stages:", m7["n_round"],
          "; theoretical trays:", m7["trays_theoretical"])
    print("Kirkbride: NR/NS =", round(fs7["kirkbride"]["ratio"], 3),
          " NR =", round(fs7["kirkbride"]["n_rect"], 2),
          " NS =", round(fs7["kirkbride"]["n_strip"], 2))
    print("Fenske sections: NR/NS =", round(fs7["fenske"]["ratio"], 3))
    assert abs(n_min - 7.8206) < 0.01, "Nmin anchor failed"
    assert abs(und["theta_used"][0] - 1.0443) < 0.002, "theta 1 anchor failed"
    assert abs(und["theta_used"][1] - 0.8587) < 0.002, "theta 2 anchor failed"
    assert abs(gil["N"] - 19.08) < 0.15, "Gilliland anchor failed"
    assert abs(darr3.sum() + barr3.sum() - feed_arr.sum()) < 1e-9, \
        "balance closure failed"
    print("all anchor checks passed")


if __name__ == "__main__":
    app.run()
