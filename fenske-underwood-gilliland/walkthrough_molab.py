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
    FUG_SRC = base64.b64decode("IiIiRmVuc2tlLVVuZGVyd29vZC1HaWxsaWxhbmQgKEZVRykgc2hvcnRjdXQgZGVzaWduIG9mIGEgbXVsdGljb21wb25lbnQKZGlzdGlsbGF0aW9uIGNvbHVtbiwgZm9sbG93aW5nIFNlYWRlciwgSGVubGV5ICYgUm9wZXIsIFNlcGFyYXRpb24gUHJvY2VzcwpQcmluY2lwbGVzLCA0dGggZWQuICgyMDE2KSwgQ2hhcHRlciA5LCBFeGFtcGxlcyA5LjItOS42IChkZWJ1dGFuaXplcikuCgpTeW1ib2xzLCBkZWZpbmVkIGF0IGZpcnN0IHVzZSBpbiB0aGUgd2Fsa3Rocm91Z2ggYW5kIFRoZW9yeSB0ZXh0OgogIGZfaSAgICBtb2xhciBmbG93IHJhdGUgb2YgY29tcG9uZW50IGkgaW4gdGhlIGZlZWQsIGluIGttb2wvaAogICAgICAgICAoa2lsb21vbGVzIHBlciBob3VyKQogIGRfaSAgICBtb2xhciBmbG93IHJhdGUgb2YgY29tcG9uZW50IGkgaW4gdGhlIGRpc3RpbGxhdGUsIGluIGttb2wvaAogIGJfaSAgICBtb2xhciBmbG93IHJhdGUgb2YgY29tcG9uZW50IGkgaW4gdGhlIGJvdHRvbXMsIGluIGttb2wvaAogIGFscGhhX2kgIG1lYW4gcmVsYXRpdmUgdm9sYXRpbGl0eSBvZiBjb21wb25lbnQgaSB3aXRoIHJlc3BlY3QgdG8gdGhlCiAgICAgICAgIGhlYXZ5IGtleSAoSEspLCBkaW1lbnNpb25sZXNzOyBhbHBoYSBvZiB0aGUgSEsgaXMgMSBieSBkZWZpbml0aW9uCiAgTEsgICAgIGxpZ2h0IGtleTsgSEsgaGVhdnkga2V5IChhZGphY2VudCBpbiB0aGUgdm9sYXRpbGl0eSBvcmRlcikKICBObWluICAgbWluaW11bSBudW1iZXIgb2YgZXF1aWxpYnJpdW0gc3RhZ2VzICh0b3RhbCByZWZsdXgpLCBkaW1lbnNpb25sZXNzOwogICAgICAgICB0aGUgdG90YWwgY29uZGVuc2VyIGlzIG5vdCBhIHN0YWdlLCB0aGUgcGFydGlhbCByZWJvaWxlciBpcyBvbmUgc3RhZ2UKICBxICAgICAgZmVlZCBxdWFsaXR5OiB0aGUgbGlxdWlkIGZyYWN0aW9uIGZvciBhIHR3by1waGFzZSBmZWVkIGFzIGl0IGVudGVycwogICAgICAgICB0aGUgY29sdW1uOyBhYm92ZSAxIGZvciBhIHN1YmNvb2xlZCBsaXF1aWQgZmVlZCwKICAgICAgICAgZGltZW5zaW9ubGVzcyAocSA9IDEgc2F0dXJhdGVkIGxpcXVpZCwgcSA9IDAgc2F0dXJhdGVkIHZhcG91ciwKICAgICAgICAgcSA+IDEgc3ViY29vbGVkIGxpcXVpZCkKICB0aGV0YSAgVW5kZXJ3b29kIHJvb3QsIGRpbWVuc2lvbmxlc3MsIGluIHRoZSBzYW1lIHNjYWxlIGFzIGFscGhhCiAgYWxwaGFfZiAgcmVsYXRpdmUgdm9sYXRpbGl0eSBvZiB0aGUgbGlnaHQga2V5IHdpdGggcmVzcGVjdCB0byB0aGUKICAgICAgICAgaGVhdnkga2V5IGF0IGZlZWQgY29uZGl0aW9ucywgZGltZW5zaW9ubGVzcyAoMS45NjcgZm9yIHRoaXMKICAgICAgICAgY2FzZSwgZGlzdGluY3QgZnJvbSB0aGUgbWVhbiB2YWx1ZSAxLjg2NCB1c2VkIGJ5IEZlbnNrZSkKICBGbCAgICAgZmVlZCBsaXF1aWQgbW9sYXIgZmxvdyByYXRlIGFmdGVyIHRoZSBmZWVkIGZsYXNoLCBpbiBrbW9sL2gKICBmbF9MSywgZmxfSEsgIGZlZWQtbGlxdWlkIG1vbGFyIGZsb3cgcmF0ZXMgb2YgdGhlIHR3byBrZXlzLCBpbiBrbW9sL2gKICBMbWluICAgbWluaW11bSBpbnRlcm5hbCByZWZsdXggbW9sYXIgZmxvdyByYXRlLCBpbiBrbW9sL2gKICBSbWluICAgbWluaW11bSByZWZsdXggcmF0aW8sIEwvRCBhdCBtaW5pbXVtIHJlZmx1eCwgZGltZW5zaW9ubGVzcwogIFIgICAgICBvcGVyYXRpbmcgcmVmbHV4IHJhdGlvLCBkaW1lbnNpb25sZXNzOyBtdWx0ID0gUiAvIFJtaW4KICBOICAgICAgbnVtYmVyIG9mIGVxdWlsaWJyaXVtIHN0YWdlcyBhdCBSLCBzYW1lIGNvdW50aW5nIGFzIE5taW4KQWxsIGNhbGN1bGF0aW9ucyBhcmUgaW4gUHl0aG9uIChudW1weSwgc2NpcHkpOyB0aGVyZSBpcyBubyBvdGhlcgppbXBsZW1lbnRhdGlvbi4KIiIiCmltcG9ydCBudW1weSBhcyBucApmcm9tIHNjaXB5Lm9wdGltaXplIGltcG9ydCBicmVudHEKCk5BTUVTID0gWyJpc29idXRhbmUiLCAibi1idXRhbmUiLCAiaXNvcGVudGFuZSIsICJuLXBlbnRhbmUiLAogICAgICAgICAibi1oZXhhbmUiLCAibi1oZXB0YW5lIiwgIm4tb2N0YW5lIiwgIm4tbm9uYW5lIl0KTEssIEhLID0gMSwgMiAgICAgICAgICAjIGluZGljZXMgb2Ygbi1idXRhbmUgYW5kIGlzb3BlbnRhbmUgaW4gTkFNRVMKCgpkZWYgZGVmYXVsdF9pbnB1dHMoKToKICAgICIiIlRoZSBTZWFkZXIgZGVidXRhbml6ZXIgZGVmYXVsdCBjYXNlIChFeGFtcGxlcyA5LjEtOS42KS4iIiIKICAgIHJldHVybiB7CiAgICAgICAgIm5hbWVzIjogbGlzdChOQU1FUyksCiAgICAgICAgImZlZWQiOiBbNS40NDMsIDIwMy4yMDksIDE2LjMyOSwgNi44MDQsIDEwLjQzMywgMTcuNzM1LCAxMjMuNDY4LCAxNC4wNjFdLAogICAgICAgICJhbHBoYSI6IFsyLjMyOSwgMS44NjQsIDEuMDAwLCAwLjg0NSwgMC4zODksIDAuMTgyNSwgMC4wODUyLCAwLjA0MDFdLAogICAgICAgICJsayI6IExLLCAiaGsiOiBISywKICAgICAgICAiZF9sayI6IDIwMC40ODgsICJiX2xrIjogMi43MjIsICAjIHNwZWNpZmllZCBzcGxpdCBvZiB0aGUgbGlnaHQga2V5CiAgICAgICAgImRfaGsiOiA1Ljg5NywgImJfaGsiOiAxMC40MzMsICAgIyBzcGVjaWZpZWQgc3BsaXQgb2YgdGhlIGhlYXZ5IGtleQogICAgICAgICJmZWVkX2xpcXVpZCI6IDM0NC4yNzY3LCAgICAgICAgICMgZmVlZCBsaXF1aWQgcmF0ZSBhZnRlciB0aGUgZmxhc2gsIGttb2wvaAogICAgICAgICJsa19mZWVkX2xpcXVpZCI6IDE1Ni42NzQ1LCAgICAgICMgZmVlZC1saXF1aWQgcmF0ZSBvZiB0aGUgTEssIGttb2wvaAogICAgICAgICJoa19mZWVkX2xpcXVpZCI6IDE0LjE4ODQsICAgICAgICMgZmVlZC1saXF1aWQgcmF0ZSBvZiB0aGUgSEssIGttb2wvaAogICAgICAgICJhbHBoYV9mZWVkIjogMS45NjcsICAgICAgICAgICAgICMga2V5IHZvbGF0aWxpdHkgYXQgZmVlZCBjb25kaXRpb25zCiAgICAgICAgInEiOiAwLjg2NiwgICAgICAgICAgICAgICAgICAgICAgIyAxMy40ICUgb2YgdGhlIGZlZWQgdmFwb3Jpc2VkCiAgICAgICAgIm11bHQiOiAxLjMsICAgICAgICAgICAgICAgICAgICAgIyBSID0gMS4zICogUm1pbiAoRXhhbXBsZSA5LjYpCiAgICAgICAgImVmZmljaWVuY3kiOiAxLjAsICAgICAgICAgICAgICAgIyBvdmVyYWxsIHRyYXkgZWZmaWNpZW5jeSwgZnJhY3Rpb24KICAgIH0KCgpkZWYgdmFsaWRhdGUoaW5wKToKICAgICIiIlJhaXNlIFZhbHVlRXJyb3Igd2l0aCBhIHBsYWluIG1lc3NhZ2Ugb24gYW55IHVudXNhYmxlIGlucHV0LiIiIgogICAgZiA9IG5wLmFzYXJyYXkoaW5wWyJmZWVkIl0sIGZsb2F0KQogICAgYSA9IG5wLmFzYXJyYXkoaW5wWyJhbHBoYSJdLCBmbG9hdCkKICAgIGlmIGYuc2hhcGUgIT0gYS5zaGFwZSBvciBmLm5kaW0gIT0gMSBvciBsZW4oZikgPCAzOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIkZlZWQgZmxvd3MgYW5kIHJlbGF0aXZlIHZvbGF0aWxpdGllcyBtdXN0IGJlICIKICAgICAgICAgICAgICAgICAgICAgICAgICJsaXN0cyBvZiB0aGUgc2FtZSBsZW5ndGgsIGF0IGxlYXN0IDMgY29tcG9uZW50cy4iKQogICAgaWYgbnAuYW55KGYgPD0gMCk6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiRXZlcnkgZmVlZCBmbG93IHJhdGUgbXVzdCBiZSBncmVhdGVyIHRoYW4gemVyby4iKQogICAgaWYgbnAuYW55KGEgPD0gMCk6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiRXZlcnkgcmVsYXRpdmUgdm9sYXRpbGl0eSBtdXN0IGJlIGdyZWF0ZXIgIgogICAgICAgICAgICAgICAgICAgICAgICAgInRoYW4gemVyby4iKQogICAgaWYgbm90IG5wLmFsbChucC5kaWZmKGEpIDwgMCk6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiUmVsYXRpdmUgdm9sYXRpbGl0aWVzIG11c3QgZGVjcmVhc2Ugc3RyaWN0bHkgIgogICAgICAgICAgICAgICAgICAgICAgICAgImluIHRoZSBjb21wb25lbnQgb3JkZXIgZ2l2ZW4uIikKICAgIGxrLCBoayA9IGludChpbnBbImxrIl0pLCBpbnQoaW5wWyJoayJdKQogICAgaWYgaGsgIT0gbGsgKyAxIG9yIG5vdCAoMCA8PSBsayA8IGxlbihmKSAtIDEpOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIlRoZSBsaWdodCBrZXkgYW5kIGhlYXZ5IGtleSBtdXN0IGJlIGFkamFjZW50ICIKICAgICAgICAgICAgICAgICAgICAgICAgICJjb21wb25lbnRzIGluIHRoZSB2b2xhdGlsaXR5IG9yZGVyLiIpCiAgICBpZiBhYnMoYVtoa10gLSAxLjApID4gMWUtOToKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJUaGUgcmVsYXRpdmUgdm9sYXRpbGl0eSBvZiB0aGUgaGVhdnkga2V5IG11c3QgIgogICAgICAgICAgICAgICAgICAgICAgICAgImJlIDEsIGJlY2F1c2Ugdm9sYXRpbGl0aWVzIGFyZSByZWxhdGl2ZSB0byBpdC4iKQogICAgZm9yIGtleSwgZGtleSwgYmtleSBpbiAoKCJsaWdodCBrZXkiLCAiZF9sayIsICJiX2xrIiksCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAoImhlYXZ5IGtleSIsICJkX2hrIiwgImJfaGsiKSk6CiAgICAgICAgaSA9IGxrIGlmIGtleSA9PSAibGlnaHQga2V5IiBlbHNlIGhrCiAgICAgICAgaWYgaW5wW2RrZXldIDwgMCBvciBpbnBbYmtleV0gPCAwOgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKGYiVGhlIHNwZWNpZmllZCBzcGxpdCBvZiB0aGUge2tleX0gbXVzdCBub3QgIgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICJiZSBuZWdhdGl2ZS4iKQogICAgICAgIGlmIGFicyhpbnBbZGtleV0gKyBpbnBbYmtleV0gLSBmW2ldKSA+IG1heCgxZS02ICogZltpXSwgMmUtMyk6CiAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoCiAgICAgICAgICAgICAgICBmIlRoZSBzcGVjaWZpZWQgc3BsaXQgb2YgdGhlIHtrZXl9IGRvZXMgbm90IGFkZCB1cCB0byAiCiAgICAgICAgICAgICAgICBmIml0cyBmZWVkIGZsb3cgcmF0ZSAoe2ZbaV06Z30ga21vbC9oKS4iKQogICAgaWYgZmxvYXQoaW5wWyJmZWVkX2xpcXVpZCJdKSA8PSAwIG9yIGZsb2F0KGlucFsibGtfZmVlZF9saXF1aWQiXSkgPD0gMCBcCiAgICAgICAgICAgIG9yIGZsb2F0KGlucFsiaGtfZmVlZF9saXF1aWQiXSkgPD0gMDoKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJUaGUgZmVlZC1saXF1aWQgZmxvdyByYXRlcyBvZiB0aGUgQ2xhc3MgMSAiCiAgICAgICAgICAgICAgICAgICAgICAgICAiY2FsY3VsYXRpb24gbXVzdCBiZSBncmVhdGVyIHRoYW4gemVyby4iKQogICAgaWYgZmxvYXQoaW5wWyJhbHBoYV9mZWVkIl0pIDw9IDEuMDoKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJUaGUgcmVsYXRpdmUgdm9sYXRpbGl0eSBvZiB0aGUga2V5cyBhdCBmZWVkICIKICAgICAgICAgICAgICAgICAgICAgICAgICJjb25kaXRpb25zIG11c3QgYmUgZ3JlYXRlciB0aGFuIDEuIikKICAgIGlmIG5vdCAoMC4wIDw9IGZsb2F0KGlucFsicSJdKSA8PSAxLjUpOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIlRoZSBmZWVkIHF1YWxpdHkgcSBtdXN0IGxpZSBiZXR3ZWVuIDAgYW5kIDEuNSAiCiAgICAgICAgICAgICAgICAgICAgICAgICAib24gdGhpcyBwYWdlICgwIHNhdHVyYXRlZCB2YXBvdXIsIDEgc2F0dXJhdGVkICIKICAgICAgICAgICAgICAgICAgICAgICAgICJsaXF1aWQ7IHZhbHVlcyBhYm92ZSAxIGRlbm90ZSBzdWJjb29sZWQgbGlxdWlkKS4iKQogICAgaWYgZmxvYXQoaW5wWyJtdWx0Il0pIDw9IDEuMDoKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJUaGUgcmVmbHV4IG11bHRpcGxpZXIgUi9SbWluIG11c3QgYmUgZ3JlYXRlciAiCiAgICAgICAgICAgICAgICAgICAgICAgICAidGhhbiAxOyBhdCB0aGUgbWluaW11bSB0aGUgc3RhZ2UgY291bnQgaXMgIgogICAgICAgICAgICAgICAgICAgICAgICAgInVuYm91bmRlZC4iKQogICAgaWYgbm90ICgwLjAgPCBmbG9hdChpbnBbImVmZmljaWVuY3kiXSkgPD0gMS4wKToKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJUaGUgb3ZlcmFsbCBlZmZpY2llbmN5IG11c3QgYmUgYSBmcmFjdGlvbiAiCiAgICAgICAgICAgICAgICAgICAgICAgICAiZ3JlYXRlciB0aGFuIDAgYW5kIGF0IG1vc3QgMS4iKQogICAgcmV0dXJuIFRydWUKCgpkZWYgZmVuc2tlKGlucCk6CiAgICAiIiJNaW5pbXVtIHN0YWdlcyBhbmQgdGhlIHByb2R1Y3QgZGlzdHJpYnV0aW9uIGF0IHRvdGFsIHJlZmx1eC4KCiAgICBSZXR1cm5zIGRpY3Qgd2l0aCBObWluIGFuZCB0aGUgZGlzdGlsbGF0ZSBhbmQgYm90dG9tcyBmbG93IGFycmF5cwogICAgZCBhbmQgYiAoa21vbC9oKSwgY29tcHV0ZWQgZm9yIHRoZSBzbWFsbGVyIHN0cmVhbSBvZiBlYWNoIG5vbi1rZXkKICAgIGNvbXBvbmVudCBmaXJzdCwgdGhlIG90aGVyIGJ5IGRpZmZlcmVuY2UgKFNlYWRlcidzIGd1aWRhbmNlKS4KICAgICIiIgogICAgdmFsaWRhdGUoaW5wKQogICAgZiA9IG5wLmFzYXJyYXkoaW5wWyJmZWVkIl0sIGZsb2F0KQogICAgYSA9IG5wLmFzYXJyYXkoaW5wWyJhbHBoYSJdLCBmbG9hdCkKICAgIGxrLCBoayA9IGludChpbnBbImxrIl0pLCBpbnQoaW5wWyJoayJdKQogICAgZCA9IG5wLnplcm9zX2xpa2UoZikKICAgIGIgPSBucC56ZXJvc19saWtlKGYpCiAgICBkW2xrXSwgYltsa10gPSBpbnBbImRfbGsiXSwgaW5wWyJiX2xrIl0KICAgIGRbaGtdLCBiW2hrXSA9IGlucFsiZF9oayJdLCBpbnBbImJfaGsiXQogICAgYV9sa19oayA9IGFbbGtdIC8gYVtoa10KICAgIG5fbWluID0gKG5wLmxvZzEwKChkW2xrXSAvIGJbbGtdKSAqIChiW2hrXSAvIGRbaGtdKSkKICAgICAgICAgICAgIC8gbnAubG9nMTAoYV9sa19oaykpCiAgICByYXRpb19oayA9IGRbaGtdIC8gYltoa10gICAgICAgICAgICAgICAjIGQvYiBvZiB0aGUgcmVmZXJlbmNlIChISykKICAgIGZvciBpIGluIHJhbmdlKGxlbihmKSk6CiAgICAgICAgaWYgaSBpbiAobGssIGhrKToKICAgICAgICAgICAgY29udGludWUKICAgICAgICAjIEZlbnNrZSBmb3IgY29tcG9uZW50IGkgcmVsYXRpdmUgdG8gdGhlIEhLOiBkX2kvYl9pIGtub3duLgogICAgICAgIHIgPSByYXRpb19oayAqIChhW2ldIC8gYVtoa10pICoqIG5fbWluCiAgICAgICAgaWYgciA8PSAxLjA6ICAgICAgICAgICAgICAgICAgICAgICAjIHNtYWxsZXIgc3RyZWFtIGlzIGRpc3RpbGxhdGUKICAgICAgICAgICAgZFtpXSA9IGZbaV0gKiByIC8gKDEuMCArIHIpCiAgICAgICAgICAgIGJbaV0gPSBmW2ldIC0gZFtpXQogICAgICAgIGVsc2U6ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIyBzbWFsbGVyIHN0cmVhbSBpcyBib3R0b21zCiAgICAgICAgICAgIGJbaV0gPSBmW2ldIC8gKDEuMCArIHIpCiAgICAgICAgICAgIGRbaV0gPSBmW2ldIC0gYltpXQogICAgcmV0dXJuIHsibl9taW4iOiBmbG9hdChuX21pbiksICJkIjogZCwgImIiOiBiLAogICAgICAgICAgICAiYWxwaGFfbGtfaGsiOiBmbG9hdChhX2xrX2hrKX0KCgpkZWYgdW5kZXJ3b29kX2Z1bmN0aW9uKHRoZXRhLCBhbHBoYSwgeiwgcSk6CiAgICAiIiJVbmRlcndvb2QgZmVlZCBmdW5jdGlvbiBVKHRoZXRhKSA9IHN1bV9pIGFscGhhX2kgel9pLyhhbHBoYV9pIC0KICAgIHRoZXRhKSAtICgxIC0gcSksIHdoZXJlIHpfaSBpcyB0aGUgbW9sZSBmcmFjdGlvbiBvZiBjb21wb25lbnQgaSBpbgogICAgdGhlIGZlZWQgKGRpbWVuc2lvbmxlc3MpIGFuZCB0aGV0YSBpcyBkaW1lbnNpb25sZXNzLiAgUm9vdHMgb2YgVSBpbgogICAgdGhlIGludGVydmFscyBiZXR3ZWVuIGNvbnNlY3V0aXZlIHJlbGF0aXZlIHZvbGF0aWxpdGllcyBnaXZlIHRoZQogICAgVW5kZXJ3b29kIHBhcmFtZXRlcnMuIiIiCiAgICBhbHBoYSA9IG5wLmFzYXJyYXkoYWxwaGEsIGZsb2F0KQogICAgeiA9IG5wLmFzYXJyYXkoeiwgZmxvYXQpCiAgICByZXR1cm4gbnAuc3VtKGFscGhhICogeiAvIChhbHBoYSAtIHRoZXRhKSkgLSAoMS4wIC0gcSkKCgpkZWYgZmVlZF9lcXVhdGlvbl9yb290KGFscGhhLCB6LCBxLCBsaywgaGspOgogICAgIiIiVGhlIHJvb3Qgb2YgdGhlIFVuZGVyd29vZCBmZWVkIGVxdWF0aW9uIGluIHRoZSBpbnRlcnZhbCBiZXR3ZWVuCiAgICB0aGUgcmVsYXRpdmUgdm9sYXRpbGl0aWVzIG9mIHRoZSB0d28ga2V5cy4gIFVzZWQgb24gdGhpcyBwYWdlIG9ubHkKICAgIGFzIGRlcml2YXRpb24gYW5kIGNoZWNrIG1hdGVyaWFsICh0aGUgQ2xhc3MgMSBjYWxjdWxhdGlvbiBpdHNlbGYKICAgIHdvcmtzIGZyb20gdGhlIGZlZWQtbGlxdWlkIGZsb3dzKS4iIiIKICAgIGEgPSBucC5hc2FycmF5KGFscGhhLCBmbG9hdCkKICAgIGxvLCBoaSA9IGFbaGtdLCBhW2xrXQogICAgZXBzID0gMWUtMTAgKiBtYXgoMS4wLCBoaSkKICAgIHIgPSBicmVudHEodW5kZXJ3b29kX2Z1bmN0aW9uLCBsbyArIGVwcywgaGkgLSBlcHMsCiAgICAgICAgICAgICAgIGFyZ3M9KGEsIG5wLmFzYXJyYXkoeiwgZmxvYXQpLCBxKSwgeHRvbD0xZS0xMykKICAgIHJldHVybiBmbG9hdChyKQoKCmRlZiB1bmRlcndvb2RfY2xhc3MxKGlucCwgZGlzdCk6CiAgICAiIiJDbGFzcyAxIG1pbmltdW0gcmVmbHV4LCBmb2xsb3dpbmcgU2VhZGVyIEV4YW1wbGUgOS40LgoKICAgIFRoZSBtaW5pbXVtIGludGVybmFsIHJlZmx1eCByYXRlIHBlciB1bml0IGZlZWQgZm9sbG93cyBmcm9tIHRoZQogICAgZmVlZC1saXF1aWQgZmxvd3Mgb2YgdGhlIGtleXMgYW5kIHRoZWlyIGRpc3RpbGxhdGUgZmxvd3MsIHdpdGggdGhlCiAgICBrZXkgcmVsYXRpdmUgdm9sYXRpbGl0eSBhdCBmZWVkIGNvbmRpdGlvbnMgKGFscGhhX2ZlZWQsIGRpc3RpbmN0CiAgICBmcm9tIHRoZSBtZWFuIHZvbGF0aWxpdHkgdXNlZCBieSB0aGUgRmVuc2tlIGVxdWF0aW9uKToKCiAgICAgICAgTG1pbi9GID0gKEZsL0YpICogWyhkX0xLL2ZsX0xLKSAtIGFscGhhX2YgKGRfSEsvZmxfSEspXQogICAgICAgICAgICAgICAgIC8gKGFscGhhX2YgLSAxKQoKICAgIHdoZXJlIEZsIGlzIHRoZSBmZWVkIGxpcXVpZCByYXRlIGFmdGVyIHRoZSBmbGFzaCBhbmQgZmxfTEssIGZsX0hLCiAgICBhcmUgdGhlIGZlZWQtbGlxdWlkIHJhdGVzIG9mIHRoZSBrZXlzLCBhbGwgaW4ga21vbC9oLiAgVGhlIGhlYWRsaW5lCiAgICBtaW5pbXVtIHJlZmx1eCByYXRpbyBpcyBwZXIgdW5pdCBkaXN0aWxsYXRlLCBhdCB0aGUgRmVuc2tlCiAgICBkaXN0aWxsYXRlIHJhdGUgRCAoa21vbC9oKTogUm1pbiA9IExtaW4vRC4gIEFsc28gcmV0dXJuZWQ6IHRoZQogICAgZmVlZC1lcXVhdGlvbiByb290IGluIHRoZSBrZXkgaW50ZXJ2YWwgKGNoZWNrIG1hdGVyaWFsKSBhbmQKICAgIFNlYWRlcidzIHByaW50ZWQgcGVyLWRpc3RpbGxhdGUgdmFsdWUgMC44NjQsIHdoaWNoIGRvZXMgbm90IGZvbGxvdwogICAgZnJvbSB0aGUgcGVyLWZlZWQgdmFsdWUgKHNlZSB0aGUgVGhlb3J5IHBhbmVsKTsgdGhlIGZlZWQgcmF0ZSB0aGF0CiAgICB0aGUgcHJpbnRlZCB2YWx1ZSB3b3VsZCBpbXBseSBpcyByZXR1cm5lZCBhcyB3ZWxsLgogICAgIiIiCiAgICB2YWxpZGF0ZShpbnApCiAgICBmID0gbnAuYXNhcnJheShpbnBbImZlZWQiXSwgZmxvYXQpCiAgICBsaywgaGsgPSBpbnQoaW5wWyJsayJdKSwgaW50KGlucFsiaGsiXSkKICAgIEYgPSBmbG9hdChmLnN1bSgpKQogICAgRCA9IGZsb2F0KGRpc3RbImQiXS5zdW0oKSkKICAgIGFmID0gZmxvYXQoaW5wWyJhbHBoYV9mZWVkIl0pCiAgICBsX3Blcl9mID0gKGZsb2F0KGlucFsiZmVlZF9saXF1aWQiXSkgLyBGKSAqICgKICAgICAgICAoZmxvYXQoaW5wWyJkX2xrIl0pIC8gZmxvYXQoaW5wWyJsa19mZWVkX2xpcXVpZCJdKSkKICAgICAgICAtIGFmICogKGZsb2F0KGlucFsiZF9oayJdKSAvIGZsb2F0KGlucFsiaGtfZmVlZF9saXF1aWQiXSkpKSAvIChhZiAtIDEuMCkKICAgIGxfbWluID0gbF9wZXJfZiAqIEYKICAgIHogPSBmIC8gRgogICAgdGhldGEgPSBmZWVkX2VxdWF0aW9uX3Jvb3QoaW5wWyJhbHBoYSJdLCB6LCBmbG9hdChpbnBbInEiXSksIGxrLCBoaykKICAgIHJldHVybiB7ImxfcGVyX2YiOiBmbG9hdChsX3Blcl9mKSwgImxfbWluIjogZmxvYXQobF9taW4pLAogICAgICAgICAgICAicl9taW4iOiBmbG9hdChsX21pbiAvIEQpLCAiRCI6IEQsCiAgICAgICAgICAgICJ0aGV0YV9rZXlfaW50ZXJ2YWwiOiB0aGV0YSwKICAgICAgICAgICAgInBlcl9kX3ByaW50ZWQiOiAwLjg2NCwKICAgICAgICAgICAgImltcGxpZWRfZmVlZF9wcmludGVkIjogZmxvYXQoMC44NjQgKiBEIC8gbF9wZXJfZil9CgoKZGVmIGdpbGxpbGFuZChyX21pbiwgbl9taW4sIG11bHQpOgogICAgIiIiRWR1bGplZSdzIGVxdWF0aW9uIGZvciB0aGUgR2lsbGlsYW5kIGNvcnJlbGF0aW9uIChTZWFkZXIKICAgIEVxLiA5LTMzKS4gIFggPSAoUiAtIFJtaW4pLyhSICsgMSkgYW5kIFkgPSAoTiAtIE5taW4pLyhOICsgMSkgYXJlCiAgICBkaW1lbnNpb25sZXNzIGNvcnJlbGF0aW9uIHZhcmlhYmxlczsgUiA9IG11bHQgKiBSbWluLiIiIgogICAgUiA9IG11bHQgKiByX21pbgogICAgWCA9IChSIC0gcl9taW4pIC8gKFIgKyAxLjApCiAgICBZID0gMS4wIC0gbnAuZXhwKCgoMS4wICsgNTQuNCAqIFgpICogKFggLSAxLjApKQogICAgICAgICAgICAgICAgICAgICAvICgoMTEuMCArIDExNy4yICogWCkgKiBucC5zcXJ0KFgpKSkKICAgIE4gPSAobl9taW4gKyBZKSAvICgxLjAgLSBZKQogICAgcmV0dXJuIHsiUiI6IGZsb2F0KFIpLCAiWCI6IGZsb2F0KFgpLCAiWSI6IGZsb2F0KFkpLCAiTiI6IGZsb2F0KE4pfQoKCmRlZiBmZWVkX3N0YWdlKGlucCwgZGlzdCwgbl9zdGFnZXMpOgogICAgIiIiRmVlZC1zdGFnZSBsb2NhdGlvbi4gIEtpcmticmlkZSdzIGVxdWF0aW9uIGdpdmVzIHRoZSByYXRpbwogICAgTlIvTlMgb2YgZXF1aWxpYnJpdW0gc3RhZ2VzIGFib3ZlIHRoZSBmZWVkIChyZWN0aWZ5aW5nIHNlY3Rpb24pIHRvCiAgICBzdGFnZXMgYmVsb3cgaXQgKHN0cmlwcGluZyBzZWN0aW9uKSwgY291bnRpbmcgdGhlIHBhcnRpYWwgcmVib2lsZXIKICAgIGluIHRoZSBzdHJpcHBpbmcgc2VjdGlvbiBhbmQgZXhjbHVkaW5nIHRoZSB0b3RhbCBjb25kZW5zZXIuICBUaGUKICAgIEZlbnNrZSBzZWN0aW9uIHJhdGlvIGFwcGxpZXMgdGhlIEZlbnNrZSBlcXVhdGlvbiB0byBlYWNoIHNlY3Rpb24KICAgIHNlcGFyYXRlbHkgYXQgdG90YWwgcmVmbHV4LiAgTW9sZSBmcmFjdGlvbnM6IHogaW4gdGhlIGZlZWQsIHhEIGluCiAgICB0aGUgZGlzdGlsbGF0ZSwgeEIgaW4gdGhlIGJvdHRvbXMgKGFsbCBkaW1lbnNpb25sZXNzKS4iIiIKICAgIGYgPSBucC5hc2FycmF5KGlucFsiZmVlZCJdLCBmbG9hdCkKICAgIGxrLCBoayA9IGludChpbnBbImxrIl0pLCBpbnQoaW5wWyJoayJdKQogICAgZCwgYiA9IGRpc3RbImQiXSwgZGlzdFsiYiJdCiAgICB6ID0gZiAvIGYuc3VtKCkKICAgIHhEID0gZCAvIGQuc3VtKCkKICAgIHhCID0gYiAvIGIuc3VtKCkKICAgIGtpcmsgPSAoKHpbaGtdIC8geltsa10pICogKHhCW2xrXSAvIHhEW2hrXSkgKiogMgogICAgICAgICAgICAqIChiLnN1bSgpIC8gZC5zdW0oKSkpICoqIDAuMjA2CiAgICBhX2xrX2hrID0gZGlzdFsiYWxwaGFfbGtfaGsiXQogICAgbnJfbWluID0gKG5wLmxvZzEwKCh4RFtsa10gLyB4RFtoa10pICogKHpbaGtdIC8geltsa10pKQogICAgICAgICAgICAgIC8gbnAubG9nMTAoYV9sa19oaykpCiAgICBuc19taW4gPSAobnAubG9nMTAoKHpbbGtdIC8geltoa10pICogKHhCW2hrXSAvIHhCW2xrXSkpCiAgICAgICAgICAgICAgLyBucC5sb2cxMChhX2xrX2hrKSkKICAgIGZlbnNrZV9yYXRpbyA9IG5yX21pbiAvIG5zX21pbgogICAgb3V0ID0ge30KICAgIGZvciBsYWJlbCwgcmF0aW8gaW4gKCgia2lya2JyaWRlIiwga2lyayksICgiZmVuc2tlIiwgZmVuc2tlX3JhdGlvKSk6CiAgICAgICAgbnMgPSBuX3N0YWdlcyAvICgxLjAgKyByYXRpbykKICAgICAgICBvdXRbbGFiZWxdID0geyJyYXRpbyI6IGZsb2F0KHJhdGlvKSwgIm5fcmVjdCI6IGZsb2F0KHJhdGlvICogbnMpLAogICAgICAgICAgICAgICAgICAgICAgIm5fc3RyaXAiOiBmbG9hdChucyl9CiAgICByZXR1cm4gb3V0CgoKZGVmIHBsYWluKG8pOgogICAgIiIibnVtcHkgdmFsdWVzIC0+IEpTT04tZnJpZW5kbHkgcGxhaW4gZGF0YSAoTmFOL2luZiAtPiBOb25lKS4iIiIKICAgIGlmIGlzaW5zdGFuY2UobywgbnAubmRhcnJheSk6CiAgICAgICAgcmV0dXJuIFtwbGFpbih2KSBmb3IgdiBpbiBvLnRvbGlzdCgpXSBpZiBvLm5kaW0gZWxzZSBwbGFpbihvLml0ZW0oKSkKICAgIGlmIGlzaW5zdGFuY2UobywgKGxpc3QsIHR1cGxlKSk6CiAgICAgICAgcmV0dXJuIFtwbGFpbih2KSBmb3IgdiBpbiBvXQogICAgaWYgaXNpbnN0YW5jZShvLCBkaWN0KToKICAgICAgICByZXR1cm4ge2s6IHBsYWluKHYpIGZvciBrLCB2IGluIG8uaXRlbXMoKX0KICAgIGlmIGlzaW5zdGFuY2UobywgKG5wLmZsb2F0aW5nLCBmbG9hdCkpOgogICAgICAgIHYgPSBmbG9hdChvKQogICAgICAgIHJldHVybiB2IGlmIG5wLmlzZmluaXRlKHYpIGVsc2UgTm9uZQogICAgaWYgaXNpbnN0YW5jZShvLCAobnAuaW50ZWdlciwpKToKICAgICAgICByZXR1cm4gaW50KG8pCiAgICByZXR1cm4gbwoKCmRlZiBfZmlnX2xheW91dCh4X3RpdGxlLCB5X3RpdGxlKToKICAgIHJldHVybiBkaWN0KHRlbXBsYXRlPSJwbG90bHlfd2hpdGUiLAogICAgICAgICAgICAgICAgeGF4aXM9ZGljdCh0aXRsZT14X3RpdGxlKSwgeWF4aXM9ZGljdCh0aXRsZT15X3RpdGxlKSwKICAgICAgICAgICAgICAgIGxlZ2VuZD1kaWN0KHg9MS4wMiwgeT0xLjAsIHhhbmNob3I9ImxlZnQiLCB5YW5jaG9yPSJ0b3AiKSwKICAgICAgICAgICAgICAgIG1hcmdpbj1kaWN0KGw9NjAsIHI9MTcwLCB0PTMwLCBiPTU1KSkKCgpkZWYgcnVuX2Nhc2UoaW5wKToKICAgICIiIkZ1bGwgRlVHIGNhbGN1bGF0aW9uIGZvciBvbmUgaW5wdXQgc2V0LiAgUmV0dXJucyBhIHBsYWluLWRhdGEKICAgIGRpY3Q6IG1ldHJpY3MsIHRoZSBmbG93IHRhYmxlLCBhbmQgdGhlIHRocmVlIEFwcCBmaWd1cmVzIGFzIFBsb3RseQogICAgdHJhY2UvbGF5b3V0IGRpY3RzLiIiIgogICAgZGlzdCA9IGZlbnNrZShpbnApCiAgICB1bmQgPSB1bmRlcndvb2RfY2xhc3MxKGlucCwgZGlzdCkKICAgIGdpbCA9IGdpbGxpbGFuZCh1bmRbInJfbWluIl0sIGRpc3RbIm5fbWluIl0sIGZsb2F0KGlucFsibXVsdCJdKSkKICAgIG5fcm91bmQgPSBpbnQobnAuY2VpbChnaWxbIk4iXSkpCiAgICB0cmF5c190aGVvcmV0aWNhbCA9IG5fcm91bmQgLSAxICAgICAgICAjIHJlYm9pbGVyIGlzIG9uZSBvZiB0aGUgc3RhZ2VzCiAgICBlZmYgPSBmbG9hdChpbnBbImVmZmljaWVuY3kiXSkKICAgIHRyYXlzX2FjdHVhbCA9IGludChucC5jZWlsKHRyYXlzX3RoZW9yZXRpY2FsIC8gZWZmKSkKICAgIGZzID0gZmVlZF9zdGFnZShpbnAsIGRpc3QsIGZsb2F0KG5fcm91bmQpKQogICAgZiA9IG5wLmFzYXJyYXkoaW5wWyJmZWVkIl0sIGZsb2F0KQogICAgYSA9IG5wLmFzYXJyYXkoaW5wWyJhbHBoYSJdLCBmbG9hdCkKICAgIHogPSBmIC8gZi5zdW0oKQoKICAgICMgRmlnLiBBOiBHaWxsaWxhbmQgY3VydmUgKEVkdWxqZWUpIHdpdGggdGhlIG9wZXJhdGluZyBwb2ludC4KICAgIG11bHRzID0gbnAuY29uY2F0ZW5hdGUoKFsxLjAwMV0sIG5wLmxpbnNwYWNlKDEuMDEsIDQuMCwgMTIwKSkpCiAgICB4cywgeXMgPSBbXSwgW10KICAgIGZvciBtIGluIG11bHRzOgogICAgICAgIGcgPSBnaWxsaWxhbmQodW5kWyJyX21pbiJdLCBkaXN0WyJuX21pbiJdLCBmbG9hdChtKSkKICAgICAgICB4cy5hcHBlbmQoZ1siWCJdKQogICAgICAgIHlzLmFwcGVuZChnWyJZIl0pCiAgICBmaWdfZ2lsbGlsYW5kID0gewogICAgICAgICJkYXRhIjogWwogICAgICAgICAgICBkaWN0KHR5cGU9InNjYXR0ZXIiLCB4PXhzLCB5PXlzLCBtb2RlPSJsaW5lcyIsCiAgICAgICAgICAgICAgICAgbmFtZT0iR2lsbGlsYW5kIGNvcnJlbGF0aW9uIChFZHVsamVlIGVxdWF0aW9uKSIsCiAgICAgICAgICAgICAgICAgbGluZT1kaWN0KGNvbG9yPSIjMDA3MkIyIiwgd2lkdGg9MikpLAogICAgICAgICAgICBkaWN0KHR5cGU9InNjYXR0ZXIiLCB4PVtnaWxbIlgiXV0sIHk9W2dpbFsiWSJdXSwKICAgICAgICAgICAgICAgICBtb2RlPSJtYXJrZXJzIiwgbmFtZT0iT3BlcmF0aW5nIHBvaW50IiwKICAgICAgICAgICAgICAgICBtYXJrZXI9ZGljdChjb2xvcj0iI0Q1NUUwMCIsIHNpemU9MTEsIHN5bWJvbD0iY2lyY2xlIiwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICBsaW5lPWRpY3QoY29sb3I9IiM3YTM0MDAiLCB3aWR0aD0xKSkpXSwKICAgICAgICAibGF5b3V0IjogX2ZpZ19sYXlvdXQoIlggKGRpbWVuc2lvbmxlc3MpIiwgIlkgKGRpbWVuc2lvbmxlc3MpIil9CgogICAgIyBGaWcuIEI6IGVxdWlsaWJyaXVtIHN0YWdlcyBhZ2FpbnN0IHRoZSByZWZsdXggbXVsdGlwbGllciwgZnJvbQogICAgIyB0aGUgR2lsbGlsYW5kL0VkdWxqZWUgcmVsYXRpb24gYXQgdGhlIENsYXNzIDEgbWluaW11bSByZWZsdXgKICAgICMgcmF0aW87IHRoZSBvcGVyYXRpbmcgcG9pbnQgaXMgbWFya2VkLiAgVGhlIGN1cnZlIGlzIGNsaXBwZWQgYXQKICAgICMgNjAgc3RhZ2VzIGZvciBkaXNwbGF5LCBjbG9zZSB0byB0aGUgbWluaW11bS1yZWZsdXggZW5kLgogICAgbXZhbHMgPSBucC5jb25jYXRlbmF0ZSgoWzEuMDJdLCBucC5saW5zcGFjZSgxLjAzLCA0LjAsIDE0MCkpKQogICAgbnZhbHMgPSBbZ2lsbGlsYW5kKHVuZFsicl9taW4iXSwgZGlzdFsibl9taW4iXSwgZmxvYXQobSkpWyJOIl0KICAgICAgICAgICAgIGZvciBtIGluIG12YWxzXQogICAgZmlnX3N0YWdlcyA9IHsKICAgICAgICAiZGF0YSI6IFsKICAgICAgICAgICAgZGljdCh0eXBlPSJzY2F0dGVyIiwgeD1tdmFscy50b2xpc3QoKSwKICAgICAgICAgICAgICAgICB5PVttaW4odiwgNjAuMCkgZm9yIHYgaW4gbnZhbHNdLCBtb2RlPSJsaW5lcyIsCiAgICAgICAgICAgICAgICAgbmFtZT0iRXF1aWxpYnJpdW0gc3RhZ2VzIGZyb20gdGhlIEdpbGxpbGFuZCBjb3JyZWxhdGlvbiIsCiAgICAgICAgICAgICAgICAgbGluZT1kaWN0KGNvbG9yPSIjMDA3MkIyIiwgd2lkdGg9MikpLAogICAgICAgICAgICBkaWN0KHR5cGU9InNjYXR0ZXIiLCB4PVtmbG9hdChpbnBbIm11bHQiXSldLCB5PVtnaWxbIk4iXV0sCiAgICAgICAgICAgICAgICAgbW9kZT0ibWFya2VycyIsIG5hbWU9Ik9wZXJhdGluZyBwb2ludCIsCiAgICAgICAgICAgICAgICAgbWFya2VyPWRpY3QoY29sb3I9IiNENTVFMDAiLCBzaXplPTExLCBzeW1ib2w9ImNpcmNsZSIsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgbGluZT1kaWN0KGNvbG9yPSIjN2EzNDAwIiwgd2lkdGg9MSkpKV0sCiAgICAgICAgImxheW91dCI6IF9maWdfbGF5b3V0KCJSZWZsdXggbXVsdGlwbGllciBSL1JtaW4gKGRpbWVuc2lvbmxlc3MpIiwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIkVxdWlsaWJyaXVtIHN0YWdlcyBOIChkaW1lbnNpb25sZXNzIGNvdW50KSIpfQoKICAgICMgRmlnLiBDOiBjb21wb25lbnQgZGlzdHJpYnV0aW9uLCBsb2dhcml0aG1pYyBzY2FsZSAoZmxvd3Mgc3BhbgogICAgIyAxMiBvcmRlcnMgb2YgbWFnbml0dWRlKTsgZG91YmxlIGVuY29kaW5nIGJ5IGNvbG91ciBhbmQgcGF0dGVybi4KICAgIG5hbWVzID0gbGlzdChpbnBbIm5hbWVzIl0pCiAgICBmaWdfZGlzdCA9IHsKICAgICAgICAiZGF0YSI6IFsKICAgICAgICAgICAgZGljdCh0eXBlPSJiYXIiLCB4PW5hbWVzLCB5PW5wLm1heGltdW0oZGlzdFsiZCJdLCAxZS0xMikudG9saXN0KCksCiAgICAgICAgICAgICAgICAgbmFtZT0iRGlzdGlsbGF0ZSBmbG93IHJhdGUiLCBtYXJrZXI9ZGljdChjb2xvcj0iIzAwNzJCMiIpKSwKICAgICAgICAgICAgZGljdCh0eXBlPSJiYXIiLCB4PW5hbWVzLCB5PW5wLm1heGltdW0oZGlzdFsiYiJdLCAxZS0xMikudG9saXN0KCksCiAgICAgICAgICAgICAgICAgbmFtZT0iQm90dG9tcyBmbG93IHJhdGUiLAogICAgICAgICAgICAgICAgIG1hcmtlcj1kaWN0KGNvbG9yPSIjRDU1RTAwIiwgcGF0dGVybj1kaWN0KHNoYXBlPSIvIikpKV0sCiAgICAgICAgImxheW91dCI6IGRpY3QodGVtcGxhdGU9InBsb3RseV93aGl0ZSIsIGJhcm1vZGU9Imdyb3VwIiwKICAgICAgICAgICAgICAgICAgICAgICB4YXhpcz1kaWN0KHRpdGxlPSJDb21wb25lbnQiKSwKICAgICAgICAgICAgICAgICAgICAgICB5YXhpcz1kaWN0KHRpdGxlPSJGbG93IHJhdGUgKGttb2wvaCkiLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgdHlwZT0ibG9nIiksCiAgICAgICAgICAgICAgICAgICAgICAgbGVnZW5kPWRpY3QoeD0xLjAyLCB5PTEuMCwgeGFuY2hvcj0ibGVmdCIsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgeWFuY2hvcj0idG9wIiksCiAgICAgICAgICAgICAgICAgICAgICAgbWFyZ2luPWRpY3QobD02MCwgcj0xNzAsIHQ9MzAsIGI9NTUpKX0KCiAgICBtZXRyaWNzID0gewogICAgICAgICJuX21pbiI6IGRpc3RbIm5fbWluIl0sICJhbHBoYV9sa19oayI6IGRpc3RbImFscGhhX2xrX2hrIl0sCiAgICAgICAgIkRfZmVuc2tlIjogZmxvYXQoZGlzdFsiZCJdLnN1bSgpKSwgIkJfZmVuc2tlIjogZmxvYXQoZGlzdFsiYiJdLnN1bSgpKSwKICAgICAgICAibF9wZXJfZiI6IHVuZFsibF9wZXJfZiJdLCAibF9taW4iOiB1bmRbImxfbWluIl0sCiAgICAgICAgInJfbWluIjogdW5kWyJyX21pbiJdLCAidGhldGFfa2V5X2ludGVydmFsIjogdW5kWyJ0aGV0YV9rZXlfaW50ZXJ2YWwiXSwKICAgICAgICAiUiI6IGdpbFsiUiJdLCAiWCI6IGdpbFsiWCJdLCAiWSI6IGdpbFsiWSJdLCAiTiI6IGdpbFsiTiJdLAogICAgICAgICJuX3JvdW5kIjogbl9yb3VuZCwgInRyYXlzX3RoZW9yZXRpY2FsIjogdHJheXNfdGhlb3JldGljYWwsCiAgICAgICAgInRyYXlzX2FjdHVhbCI6IHRyYXlzX2FjdHVhbCwKICAgICAgICAiZmVlZF9raXJrYnJpZGUiOiBmc1sia2lya2JyaWRlIl0sICJmZWVkX2ZlbnNrZSI6IGZzWyJmZW5za2UiXSwKICAgIH0KICAgIHJldHVybiBwbGFpbih7CiAgICAgICAgIm1ldHJpY3MiOiBtZXRyaWNzLAogICAgICAgICJuYW1lcyI6IG5hbWVzLAogICAgICAgICJmZWVkIjogZi50b2xpc3QoKSwgImFscGhhIjogYS50b2xpc3QoKSwKICAgICAgICAiZCI6IGRpc3RbImQiXS50b2xpc3QoKSwgImIiOiBkaXN0WyJiIl0udG9saXN0KCksCiAgICAgICAgImZpZ3MiOiB7ImdpbGxpbGFuZCI6IGZpZ19naWxsaWxhbmQsICJ1bmRlcndvb2QiOiBmaWdfc3RhZ2VzLAogICAgICAgICAgICAgICAgICJkaXN0cmlidXRpb24iOiBmaWdfZGlzdH0sCiAgICB9KQo=").decode("utf-8")
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

    An editable breakdown of the FUG shortcut design of a multicomponent distillation column, worked on the debutanizer of Seader, Henley & Roper, Separation Process Principles, 4th ed. (2016), Chapter 9. Edit a value in a cell and re-run; every downstream cell recomputes. Flow rates are in kmol/h (kilomoles per hour).
    """)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 1: Feed, key components and specified splits

    The column separates a feed of eight hydrocarbon components, listed in order of decreasing volatility. The symbol $f_i$ denotes the molar flow rate of component $i$ in the feed, in kmol/h (kilomoles per hour). The symbol $F$ denotes the total feed rate, the sum of the $f_i$, in kmol/h. The symbol $z_i$ denotes the mole fraction of component $i$ in the feed, $z_i = f_i / F$, dimensionless.

    Two adjacent components are chosen as the key components, whose split between the products is specified. The light key (LK) is n-butane: it is the heaviest component that must pass mainly into the distillate. The heavy key (HK) is isopentane: it is the lightest component that must pass mainly into the bottoms. The symbol $d_i$ denotes the molar flow rate of component $i$ in the distillate and $b_i$ its molar flow rate in the bottoms, both in kmol/h, with $f_i = d_i + b_i$ for every component. The specified splits are $d = 200.488$ and $b = 2.722$ kmol/h for the light key, and $d = 5.897$ and $b = 10.433$ kmol/h for the heavy key.

    The symbol $\alpha_i$ denotes the mean relative volatility of component $i$ with respect to the heavy key, dimensionless: the ratio of the distribution coefficients (the equilibrium vapour-to-liquid mole-fraction ratios) of component $i$ and the heavy key, geometrically averaged between the distillate and bottoms conditions of Seader's Example 9.1. By this definition $\alpha = 1$ for the heavy key itself. One volatility set is used in every step of this walkthrough. The column has a total condenser, which is not counted as an equilibrium stage, and a partial reboiler, which is counted as one equilibrium stage.
    """)


@app.cell
def _(F, figure, np):
    inp = F.default_inputs()
    feed_arr = np.array(inp["feed"])
    print("total feed rate F =", feed_arr.sum(), "kmol/h")
    for nm1, fv1, av1 in zip(inp["names"], inp["feed"], inp["alpha"]):
        print(f"{nm1:12s} f = {fv1:7.1f} kmol/h   alpha = {av1:g}")
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

    Combined with $f_i = d_i + b_i$, this fixes every non-key flow. Following Seader's guidance, the smaller of $d_i$ and $b_i$ is computed from the equation first and the larger by difference, which keeps the small flows accurate; several distillate flows are below $10^{-6}$ kmol/h. The chart uses a logarithmic scale because the flows span twelve orders of magnitude; colour and pattern both encode the product, so the chart reads in greyscale. These total-reflux flows are the product distribution used by the rest of the method.
    """)


@app.cell
def _(dist, figure, inp, np):
    darr3 = dist["d"]
    barr3 = dist["b"]
    for nm3, fv3, dv3, bv3 in zip(inp["names"], inp["feed"], darr3, barr3):
        print(f"{nm3:12s} f = {fv3:8.2f}   d = {dv3:12.5g}   b = {bv3:10.3f}")
    print("totals: D =", round(darr3.sum(), 2), " B =", round(barr3.sum(), 2),
          " (Seader: 212.71 / 184.77 kmol/h)")
    figure([dict(type="bar", x=inp["names"],
                 y=np.maximum(darr3, 1e-12).tolist(),
                 name="Distillate flow rate", marker=dict(color="#0072B2")),
            dict(type="bar", x=inp["names"],
                 y=np.maximum(barr3, 1e-12).tolist(), name="Bottoms flow rate",
                 marker=dict(color="#D55E00", pattern=dict(shape="/")))],
           xaxis=dict(title="Component"),
           yaxis=dict(title="Flow rate (kmol/h)", type="log"),
           barmode="group", template="plotly_white",
           legend=dict(x=1.02, y=1.0, xanchor="left", yanchor="top"))


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 4: Underwood Class 1: minimum reflux and its check

    The minimum reflux ratio, $R_{min}$ (dimensionless), is the reflux ratio $R = L/D$ at which the stage count becomes unbounded, where $L$ denotes the liquid reflux flow rate and $D$ the distillate flow rate, both in kmol/h. Underwood's method {{cite:underwood-1948}} distinguishes two classes of separation. In a Class 1 separation every component appears in both products; in a Class 2 separation at least one component appears in only one product. This page carries out the Class 1 calculation only, following Seader's Example 9.4.

    The Class 1 shortcut works from the feed liquid left by the feed flash of Example 9.1. The symbol $F_L$ denotes that feed liquid rate, $344.277$ kmol/h, and the symbols $f^L_{LK}$ and $f^L_{HK}$ denote the feed-liquid rates of the two keys, $156.675$ and $14.188$ kmol/h. The symbol $\alpha_f$ denotes the relative volatility of the light key with respect to the heavy key at feed conditions, $1.967$, dimensionless; it is distinct from the mean volatility $1.864$ of Step 1, which the Fenske equation uses. With $L_{min}$ denoting the minimum internal reflux rate, in kmol/h, the Class 1 result is

    $$\frac{L_{min}}{F} = \frac{F_L}{F} \, \frac{\left(d_{LK}/f^L_{LK}\right) - \alpha_f \left(d_{HK}/f^L_{HK}\right)}{\alpha_f - 1}$$

    which gives $L_{min}/F = 0.414$ per unit feed, and the headline minimum reflux ratio is per unit distillate: $R_{min} = L_{min}/D$ at the Fenske distillate rate of Step 3. As derivation and check material, this cell also evaluates the root of the Underwood feed equation in the interval between the key volatilities, $1.0443$; the Theory panel derives that equation. No second root is used and no Class 2 solve is carried out.

    The validity check on the Class 1 assumption then fails, and the failure is stated plainly. Seader's Example 9.4 applies the Class 1 relations to the non-key components and obtains negative distillate flow rates for the heavy non-keys and an isobutane distillate flow rate above its feed rate. The debutanizer separation is therefore not in fact Class 1: most non-keys appear in one product only. The Class 1 minimum reflux ratio, and the Gilliland stage count that follows from it in Step 5, are the formal Class 1 results, reported as such.

    One further point is recorded in this cell's output. Seader prints the Class 1 ratio as $0.864$ per unit distillate. Converted at the distillate rate of Step 3, his per-feed value of $0.414$ gives $0.774$ per unit distillate, not $0.864$; the printed $0.864$ would follow from a feed rate of $444.0$ kmol/h in place of $397.5$ kmol/h. The page reports both values; its headline result is the recomputed $0.774$.
    """)


@app.cell
def _(F, dist, inp):
    und = F.underwood_class1(inp, dist)
    print("Class 1 minimum internal reflux per unit feed:",
          round(und["l_per_f"], 3), " (Seader: 0.414)")
    print("Lmin =", round(und["l_min"], 1), "kmol/h")
    print("Rmin =", round(und["r_min"], 3),
          " per unit distillate (recomputed; Seader prints 0.864)")
    print("feed-equation root in the key interval (check material):",
          round(und["theta_key_interval"], 4), " (Seader: 1.0443)")
    print("feed rate implied by the printed 0.864:",
          round(und["implied_feed_printed"], 1), "kmol/h")


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 5: Gilliland correlation: stages at the operating reflux

    The operating reflux ratio $R$ is chosen as a multiple of the minimum: $R = 1.3 \, R_{min}$, the multiplier of Seader's Example 9.6, where $1.3$ is the reflux multiplier (dimensionless). Example 9.6 tabulates the correlation for both of his minimum-reflux rows; this page follows the Class 1 row, at the recomputed Class 1 minimum reflux ratio of Step 4. The Gilliland correlation {{cite:gilliland-1940}} relates the stage count at finite reflux to the two limits, total reflux and minimum reflux, through the dimensionless variables $X = (R - R_{min}) / (R + 1)$ and $Y = (N - N_{min}) / (N + 1)$, where $N$ denotes the number of equilibrium stages at $R$, with the stage counting of Step 1. The page evaluates the correlation with the explicit equation of Eduljee {{cite:eduljee-1975}}, Seader's Eq. (9-33):

    $$Y = 1 - \exp\left(\frac{(1 + 54.4 X)(X - 1)}{(11 + 117.2 X)\sqrt{X}}\right)$$

    Solving $Y = (N - N_{min})/(N + 1)$ for $N$ gives the stage requirement. As $R$ approaches $R_{min}$, $X$ approaches $0$ and $N$ grows without bound; as $R$ grows without bound, $N$ approaches $N_{min}$. The correlation carries no feed-condition parameter, a known limitation Seader records: it is conservative for feeds of low $q$. The chart plots the curve for reflux multipliers from 1.001 to 4, not only the operating point.
    """)


@app.cell
def _(F, figure, inp, n_min, np, und):
    gil = F.gilliland(und["r_min"], n_min, inp["mult"])
    print("R =", round(gil["R"], 3), " X =", round(gil["X"], 4),
          " Y =", round(gil["Y"], 4))
    print("N =", round(gil["N"], 2), "equilibrium stages (Seader's Class 1 row, from his printed 0.864: 17.8)")
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
    ## Step 6: Feed-stage location and anchor checks

    The stage count is split between the rectifying section, above the feed, and the stripping section, below it. The symbol $N_R$ denotes the number of equilibrium stages in the rectifying section and $N_S$ the number in the stripping section, the partial reboiler counted in the stripping section. Kirkbride's empirical equation {{cite:kirkbride-1944}} gives the ratio

    $$\frac{N_R}{N_S} = \left[ \frac{z_{HK}}{z_{LK}} \left(\frac{x_{LK,B}}{x_{HK,D}}\right)^{2} \frac{B}{D} \right]^{0.206}$$

    where $x_{LK,B}$ denotes the mole fraction of the light key in the bottoms, $x_{HK,D}$ the mole fraction of the heavy key in the distillate, $B$ the total bottoms rate and $D$ the total distillate rate, both in kmol/h. The second estimate applies the Fenske equation to each section separately at total reflux. Seader reports Kirkbride as the better of the two on his test problem, and it is listed first here. The total stage count is rounded up to a whole number before the split, because a column is built of whole stages; the reboiler is one of them, so the number of theoretical trays is one less than the rounded stage count.

    The anchor checks assert the values verified against Seader's Examples 9.2, 9.4 and 9.6 (the Class 1 row). A failed assertion means the calculation has drifted from the verified case.
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
    print("feed stage (Kirkbride):", int(fs7["kirkbride"]["n_rect"]) + 1,
          "of", m7["n_round"])
    assert abs(n_min - 7.8206) < 0.01, "Nmin anchor failed"
    assert abs(und["theta_key_interval"] - 1.0443) < 0.002, "theta anchor failed"
    assert abs(und["r_min"] - 0.774) < 0.002, "Class 1 Rmin anchor failed"
    assert abs(gil["N"] - 18.09) < 0.15, "Gilliland anchor failed"
    assert m7["n_round"] == 19, "rounded stage anchor failed"
    assert abs(darr3.sum() + barr3.sum() - feed_arr.sum()) < 5e-3, \
        "balance closure failed (tolerance is the rounding of the specified splits)"
    print("all anchor checks passed")


if __name__ == "__main__":
    app.run()
