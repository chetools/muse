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
    FUG_SRC = base64.b64decode("IiIiRmVuc2tlLVVuZGVyd29vZC1HaWxsaWxhbmQgKEZVRykgc2hvcnRjdXQgZGVzaWduIG9mIGEgbXVsdGljb21wb25lbnQKZGlzdGlsbGF0aW9uIGNvbHVtbiwgZm9sbG93aW5nIFNlYWRlciwgSGVubGV5ICYgUm9wZXIsIFNlcGFyYXRpb24gUHJvY2VzcwpQcmluY2lwbGVzLCA0dGggZWQuICgyMDE2KSwgQ2hhcHRlciA5LCBFeGFtcGxlcyA5LjItOS42IChkZWJ1dGFuaXplcikuCgpTeW1ib2xzLCBkZWZpbmVkIGF0IGZpcnN0IHVzZSBpbiB0aGUgd2Fsa3Rocm91Z2ggYW5kIFRoZW9yeSB0ZXh0OgogIGZfaSAgICBtb2xhciBmbG93IHJhdGUgb2YgY29tcG9uZW50IGkgaW4gdGhlIGZlZWQsIGluIGxibW9sL2gKICAgICAgICAgKHBvdW5kLW1vbGVzIHBlciBob3VyLCB0aGUgdW5pdCBvZiB0aGUgc291cmNlIGV4YW1wbGUpCiAgZF9pICAgIG1vbGFyIGZsb3cgcmF0ZSBvZiBjb21wb25lbnQgaSBpbiB0aGUgZGlzdGlsbGF0ZSwgaW4gbGJtb2wvaAogIGJfaSAgICBtb2xhciBmbG93IHJhdGUgb2YgY29tcG9uZW50IGkgaW4gdGhlIGJvdHRvbXMsIGluIGxibW9sL2gKICBhbHBoYV9pICBtZWFuIHJlbGF0aXZlIHZvbGF0aWxpdHkgb2YgY29tcG9uZW50IGkgd2l0aCByZXNwZWN0IHRvIHRoZQogICAgICAgICBoZWF2eSBrZXkgKEhLKSwgZGltZW5zaW9ubGVzczsgYWxwaGEgb2YgdGhlIEhLIGlzIDEgYnkgZGVmaW5pdGlvbgogIExLICAgICBsaWdodCBrZXk7IEhLIGhlYXZ5IGtleSAoYWRqYWNlbnQgaW4gdGhlIHZvbGF0aWxpdHkgb3JkZXIpCiAgTm1pbiAgIG1pbmltdW0gbnVtYmVyIG9mIGVxdWlsaWJyaXVtIHN0YWdlcyAodG90YWwgcmVmbHV4KSwgZGltZW5zaW9ubGVzczsKICAgICAgICAgdGhlIHRvdGFsIGNvbmRlbnNlciBpcyBub3QgYSBzdGFnZSwgdGhlIHBhcnRpYWwgcmVib2lsZXIgaXMgb25lIHN0YWdlCiAgcSAgICAgIGZlZWQgcXVhbGl0eTogbGlxdWlkIGZyYWN0aW9uIG9mIHRoZSBmZWVkIGFzIGl0IGVudGVycyB0aGUgY29sdW1uLAogICAgICAgICBkaW1lbnNpb25sZXNzIChxID0gMSBzYXR1cmF0ZWQgbGlxdWlkLCBxID0gMCBzYXR1cmF0ZWQgdmFwb3VyKQogIHRoZXRhICBVbmRlcndvb2Qgcm9vdCwgZGltZW5zaW9ubGVzcywgaW4gdGhlIHNhbWUgc2NhbGUgYXMgYWxwaGEKICBSbWluICAgbWluaW11bSByZWZsdXggcmF0aW8sIEwvRCBhdCBtaW5pbXVtIHJlZmx1eCwgZGltZW5zaW9ubGVzcwogIFIgICAgICBvcGVyYXRpbmcgcmVmbHV4IHJhdGlvLCBkaW1lbnNpb25sZXNzOyBtdWx0ID0gUiAvIFJtaW4KICBOICAgICAgbnVtYmVyIG9mIGVxdWlsaWJyaXVtIHN0YWdlcyBhdCBSLCBzYW1lIGNvdW50aW5nIGFzIE5taW4KQWxsIGNhbGN1bGF0aW9ucyBhcmUgaW4gUHl0aG9uIChudW1weSwgc2NpcHkpOyB0aGVyZSBpcyBubyBvdGhlcgppbXBsZW1lbnRhdGlvbi4KIiIiCmltcG9ydCBudW1weSBhcyBucApmcm9tIHNjaXB5Lm9wdGltaXplIGltcG9ydCBicmVudHEKCk5BTUVTID0gWyJpc29idXRhbmUiLCAibi1idXRhbmUiLCAiaXNvcGVudGFuZSIsICJuLXBlbnRhbmUiLAogICAgICAgICAibi1oZXhhbmUiLCAibi1oZXB0YW5lIiwgIm4tb2N0YW5lIiwgIm4tbm9uYW5lIl0KTEssIEhLID0gMSwgMiAgICAgICAgICAjIGluZGljZXMgb2Ygbi1idXRhbmUgYW5kIGlzb3BlbnRhbmUgaW4gTkFNRVMKRElTVF9OT05LRVkgPSAzICAgICAgICAjIG4tcGVudGFuZTogdGhlIG9uZSBkaXN0cmlidXRpbmcgbm9uLWtleSAoQ2xhc3MgMikKCgpkZWYgZGVmYXVsdF9pbnB1dHMoKToKICAgICIiIlRoZSBTZWFkZXIgZGVidXRhbml6ZXIgZGVmYXVsdCBjYXNlIChFeGFtcGxlcyA5LjEtOS42KS4iIiIKICAgIHJldHVybiB7CiAgICAgICAgIm5hbWVzIjogbGlzdChOQU1FUyksCiAgICAgICAgImZlZWQiOiBbMTIuMCwgNDQ4LjAsIDM2LjAsIDE1LjAsIDIzLjAsIDM5LjEsIDI3Mi4yLCAzMS4wXSwKICAgICAgICAiYWxwaGEiOiBbMi4zMjksIDEuODY0LCAxLjAwMCwgMC44NDUsIDAuMzg5LCAwLjE4MjUsIDAuMDg1MiwgMC4wNDAxXSwKICAgICAgICAibGsiOiBMSywgImhrIjogSEssCiAgICAgICAgImRfbGsiOiA0NDIuMCwgImJfbGsiOiA2LjAsICAgICAgIyBzcGVjaWZpZWQgc3BsaXQgb2YgdGhlIGxpZ2h0IGtleQogICAgICAgICJkX2hrIjogMTMuMCwgImJfaGsiOiAyMy4wLCAgICAgICMgc3BlY2lmaWVkIHNwbGl0IG9mIHRoZSBoZWF2eSBrZXkKICAgICAgICAicSI6IDAuODY2LCAgICAgICAgICAgICAgICAgICAgICAjIDEzLjQgJSBvZiB0aGUgZmVlZCB2YXBvcmlzZWQKICAgICAgICAibXVsdCI6IDEuMywgICAgICAgICAgICAgICAgICAgICAjIFIgPSAxLjMgKiBSbWluIChFeGFtcGxlIDkuNikKICAgICAgICAiZWZmaWNpZW5jeSI6IDEuMCwgICAgICAgICAgICAgICAjIG92ZXJhbGwgdHJheSBlZmZpY2llbmN5LCBmcmFjdGlvbgogICAgfQoKCmRlZiB2YWxpZGF0ZShpbnApOgogICAgIiIiUmFpc2UgVmFsdWVFcnJvciB3aXRoIGEgcGxhaW4gbWVzc2FnZSBvbiBhbnkgdW51c2FibGUgaW5wdXQuIiIiCiAgICBmID0gbnAuYXNhcnJheShpbnBbImZlZWQiXSwgZmxvYXQpCiAgICBhID0gbnAuYXNhcnJheShpbnBbImFscGhhIl0sIGZsb2F0KQogICAgaWYgZi5zaGFwZSAhPSBhLnNoYXBlIG9yIGYubmRpbSAhPSAxIG9yIGxlbihmKSA8IDM6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiRmVlZCBmbG93cyBhbmQgcmVsYXRpdmUgdm9sYXRpbGl0aWVzIG11c3QgYmUgIgogICAgICAgICAgICAgICAgICAgICAgICAgImxpc3RzIG9mIHRoZSBzYW1lIGxlbmd0aCwgYXQgbGVhc3QgMyBjb21wb25lbnRzLiIpCiAgICBpZiBucC5hbnkoZiA8PSAwKToKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJFdmVyeSBmZWVkIGZsb3cgcmF0ZSBtdXN0IGJlIGdyZWF0ZXIgdGhhbiB6ZXJvLiIpCiAgICBpZiBucC5hbnkoYSA8PSAwKToKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJFdmVyeSByZWxhdGl2ZSB2b2xhdGlsaXR5IG11c3QgYmUgZ3JlYXRlciAiCiAgICAgICAgICAgICAgICAgICAgICAgICAidGhhbiB6ZXJvLiIpCiAgICBpZiBub3QgbnAuYWxsKG5wLmRpZmYoYSkgPCAwKToKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJSZWxhdGl2ZSB2b2xhdGlsaXRpZXMgbXVzdCBkZWNyZWFzZSBzdHJpY3RseSAiCiAgICAgICAgICAgICAgICAgICAgICAgICAiaW4gdGhlIGNvbXBvbmVudCBvcmRlciBnaXZlbi4iKQogICAgbGssIGhrID0gaW50KGlucFsibGsiXSksIGludChpbnBbImhrIl0pCiAgICBpZiBoayAhPSBsayArIDEgb3Igbm90ICgwIDw9IGxrIDwgbGVuKGYpIC0gMSk6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiVGhlIGxpZ2h0IGtleSBhbmQgaGVhdnkga2V5IG11c3QgYmUgYWRqYWNlbnQgIgogICAgICAgICAgICAgICAgICAgICAgICAgImNvbXBvbmVudHMgaW4gdGhlIHZvbGF0aWxpdHkgb3JkZXIuIikKICAgIGlmIGFicyhhW2hrXSAtIDEuMCkgPiAxZS05OgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIlRoZSByZWxhdGl2ZSB2b2xhdGlsaXR5IG9mIHRoZSBoZWF2eSBrZXkgbXVzdCAiCiAgICAgICAgICAgICAgICAgICAgICAgICAiYmUgMSwgYmVjYXVzZSB2b2xhdGlsaXRpZXMgYXJlIHJlbGF0aXZlIHRvIGl0LiIpCiAgICBmb3Iga2V5LCBka2V5LCBia2V5IGluICgoImxpZ2h0IGtleSIsICJkX2xrIiwgImJfbGsiKSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICgiaGVhdnkga2V5IiwgImRfaGsiLCAiYl9oayIpKToKICAgICAgICBpID0gbGsgaWYga2V5ID09ICJsaWdodCBrZXkiIGVsc2UgaGsKICAgICAgICBpZiBpbnBbZGtleV0gPCAwIG9yIGlucFtia2V5XSA8IDA6CiAgICAgICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoZiJUaGUgc3BlY2lmaWVkIHNwbGl0IG9mIHRoZSB7a2V5fSBtdXN0IG5vdCAiCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgImJlIG5lZ2F0aXZlLiIpCiAgICAgICAgaWYgYWJzKGlucFtka2V5XSArIGlucFtia2V5XSAtIGZbaV0pID4gMWUtNiAqIG1heCgxLjAsIGZbaV0pOgogICAgICAgICAgICByYWlzZSBWYWx1ZUVycm9yKAogICAgICAgICAgICAgICAgZiJUaGUgc3BlY2lmaWVkIHNwbGl0IG9mIHRoZSB7a2V5fSBkb2VzIG5vdCBhZGQgdXAgdG8gIgogICAgICAgICAgICAgICAgZiJpdHMgZmVlZCBmbG93IHJhdGUgKHtmW2ldOmd9IGxibW9sL2gpLiIpCiAgICBpZiBub3QgKDAuMCA8PSBmbG9hdChpbnBbInEiXSkgPD0gMS41KToKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKCJUaGUgZmVlZCBxdWFsaXR5IHEgbXVzdCBsaWUgYmV0d2VlbiAwIGFuZCAxLjUgIgogICAgICAgICAgICAgICAgICAgICAgICAgIm9uIHRoaXMgcGFnZSAoMCBzYXR1cmF0ZWQgdmFwb3VyLCAxIHNhdHVyYXRlZCAiCiAgICAgICAgICAgICAgICAgICAgICAgICAibGlxdWlkOyB2YWx1ZXMgYWJvdmUgMSBkZW5vdGUgc3ViY29vbGVkIGxpcXVpZCkuIikKICAgIGlmIGZsb2F0KGlucFsibXVsdCJdKSA8PSAxLjA6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiVGhlIHJlZmx1eCBtdWx0aXBsaWVyIFIvUm1pbiBtdXN0IGJlIGdyZWF0ZXIgIgogICAgICAgICAgICAgICAgICAgICAgICAgInRoYW4gMTsgYXQgdGhlIG1pbmltdW0gdGhlIHN0YWdlIGNvdW50IGlzICIKICAgICAgICAgICAgICAgICAgICAgICAgICJ1bmJvdW5kZWQuIikKICAgIGlmIG5vdCAoMC4wIDwgZmxvYXQoaW5wWyJlZmZpY2llbmN5Il0pIDw9IDEuMCk6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcigiVGhlIG92ZXJhbGwgZWZmaWNpZW5jeSBtdXN0IGJlIGEgZnJhY3Rpb24gIgogICAgICAgICAgICAgICAgICAgICAgICAgImdyZWF0ZXIgdGhhbiAwIGFuZCBhdCBtb3N0IDEuIikKICAgIHJldHVybiBUcnVlCgoKZGVmIGZlbnNrZShpbnApOgogICAgIiIiTWluaW11bSBzdGFnZXMgYW5kIHRoZSBwcm9kdWN0IGRpc3RyaWJ1dGlvbiBhdCB0b3RhbCByZWZsdXguCgogICAgUmV0dXJucyBkaWN0IHdpdGggTm1pbiBhbmQgdGhlIGRpc3RpbGxhdGUgYW5kIGJvdHRvbXMgZmxvdyBhcnJheXMKICAgIGQgYW5kIGIgKGxibW9sL2gpLCBjb21wdXRlZCBmb3IgdGhlIHNtYWxsZXIgc3RyZWFtIG9mIGVhY2ggbm9uLWtleQogICAgY29tcG9uZW50IGZpcnN0LCB0aGUgb3RoZXIgYnkgZGlmZmVyZW5jZSAoU2VhZGVyJ3MgZ3VpZGFuY2UpLgogICAgIiIiCiAgICB2YWxpZGF0ZShpbnApCiAgICBmID0gbnAuYXNhcnJheShpbnBbImZlZWQiXSwgZmxvYXQpCiAgICBhID0gbnAuYXNhcnJheShpbnBbImFscGhhIl0sIGZsb2F0KQogICAgbGssIGhrID0gaW50KGlucFsibGsiXSksIGludChpbnBbImhrIl0pCiAgICBkID0gbnAuemVyb3NfbGlrZShmKQogICAgYiA9IG5wLnplcm9zX2xpa2UoZikKICAgIGRbbGtdLCBiW2xrXSA9IGlucFsiZF9sayJdLCBpbnBbImJfbGsiXQogICAgZFtoa10sIGJbaGtdID0gaW5wWyJkX2hrIl0sIGlucFsiYl9oayJdCiAgICBhX2xrX2hrID0gYVtsa10gLyBhW2hrXQogICAgbl9taW4gPSAobnAubG9nMTAoKGRbbGtdIC8gYltsa10pICogKGJbaGtdIC8gZFtoa10pKQogICAgICAgICAgICAgLyBucC5sb2cxMChhX2xrX2hrKSkKICAgIHJhdGlvX2hrID0gZFtoa10gLyBiW2hrXSAgICAgICAgICAgICAgICMgZC9iIG9mIHRoZSByZWZlcmVuY2UgKEhLKQogICAgZm9yIGkgaW4gcmFuZ2UobGVuKGYpKToKICAgICAgICBpZiBpIGluIChsaywgaGspOgogICAgICAgICAgICBjb250aW51ZQogICAgICAgICMgRmVuc2tlIGZvciBjb21wb25lbnQgaSByZWxhdGl2ZSB0byB0aGUgSEs6IGRfaS9iX2kga25vd24uCiAgICAgICAgciA9IHJhdGlvX2hrICogKGFbaV0gLyBhW2hrXSkgKiogbl9taW4KICAgICAgICBpZiByIDw9IDEuMDogICAgICAgICAgICAgICAgICAgICAgICMgc21hbGxlciBzdHJlYW0gaXMgZGlzdGlsbGF0ZQogICAgICAgICAgICBkW2ldID0gZltpXSAqIHIgLyAoMS4wICsgcikKICAgICAgICAgICAgYltpXSA9IGZbaV0gLSBkW2ldCiAgICAgICAgZWxzZTogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAjIHNtYWxsZXIgc3RyZWFtIGlzIGJvdHRvbXMKICAgICAgICAgICAgYltpXSA9IGZbaV0gLyAoMS4wICsgcikKICAgICAgICAgICAgZFtpXSA9IGZbaV0gLSBiW2ldCiAgICByZXR1cm4geyJuX21pbiI6IGZsb2F0KG5fbWluKSwgImQiOiBkLCAiYiI6IGIsCiAgICAgICAgICAgICJhbHBoYV9sa19oayI6IGZsb2F0KGFfbGtfaGspfQoKCmRlZiB1bmRlcndvb2RfZnVuY3Rpb24odGhldGEsIGFscGhhLCB6LCBxKToKICAgICIiIlVuZGVyd29vZCBmZWVkIGZ1bmN0aW9uIFUodGhldGEpID0gc3VtX2kgYWxwaGFfaSB6X2kvKGFscGhhX2kgLQogICAgdGhldGEpIC0gKDEgLSBxKSwgd2hlcmUgel9pIGlzIHRoZSBtb2xlIGZyYWN0aW9uIG9mIGNvbXBvbmVudCBpIGluCiAgICB0aGUgZmVlZCAoZGltZW5zaW9ubGVzcykgYW5kIHRoZXRhIGlzIGRpbWVuc2lvbmxlc3MuICBSb290cyBvZiBVIGluCiAgICB0aGUgaW50ZXJ2YWxzIGJldHdlZW4gY29uc2VjdXRpdmUgcmVsYXRpdmUgdm9sYXRpbGl0aWVzIGdpdmUgdGhlCiAgICBVbmRlcndvb2QgcGFyYW1ldGVycy4iIiIKICAgIGFscGhhID0gbnAuYXNhcnJheShhbHBoYSwgZmxvYXQpCiAgICB6ID0gbnAuYXNhcnJheSh6LCBmbG9hdCkKICAgIHJldHVybiBucC5zdW0oYWxwaGEgKiB6IC8gKGFscGhhIC0gdGhldGEpKSAtICgxLjAgLSBxKQoKCmRlZiB1bmRlcndvb2Rfcm9vdHMoYWxwaGEsIHosIHEpOgogICAgIiIiQWxsIHJvb3RzIG9mIHRoZSBVbmRlcndvb2QgZmVlZCBlcXVhdGlvbiwgb25lIHBlciBpbnRlcnZhbAogICAgYmV0d2VlbiBjb25zZWN1dGl2ZSBkaXN0aW5jdCByZWxhdGl2ZSB2b2xhdGlsaXRpZXMsIGluIGRlY3JlYXNpbmcKICAgIG9yZGVyIG9mIHRoZXRhLiAgSW50ZXJ2YWxzIHdpdGggbm8gc2lnbiBjaGFuZ2UgYXJlIHNraXBwZWQuIiIiCiAgICBhID0gbnAuc29ydChucC5hc2FycmF5KGFscGhhLCBmbG9hdCkpWzo6LTFdCiAgICByb290cyA9IFtdCiAgICBmb3IgaGksIGxvIGluIHppcChhWzotMV0sIGFbMTpdKToKICAgICAgICBlcHMgPSAxZS0xMCAqIG1heCgxLjAsIGhpKQogICAgICAgIHgwLCB4MSA9IGxvICsgZXBzLCBoaSAtIGVwcwogICAgICAgIHUwID0gdW5kZXJ3b29kX2Z1bmN0aW9uKHgwLCBhbHBoYSwgeiwgcSkKICAgICAgICB1MSA9IHVuZGVyd29vZF9mdW5jdGlvbih4MSwgYWxwaGEsIHosIHEpCiAgICAgICAgaWYgbnAuaXNmaW5pdGUodTApIGFuZCBucC5pc2Zpbml0ZSh1MSkgYW5kIHUwICogdTEgPCAwOgogICAgICAgICAgICByb290cy5hcHBlbmQoZmxvYXQoYnJlbnRxKHVuZGVyd29vZF9mdW5jdGlvbiwgeDAsIHgxLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGFyZ3M9KGFscGhhLCB6LCBxKSwgeHRvbD0xZS0xMykpKQogICAgcmV0dXJuIHJvb3RzCgoKZGVmIHVuZGVyd29vZF9jbGFzczIoaW5wLCBkaXN0KToKICAgICIiIkNsYXNzIDIgbWluaW11bSByZWZsdXgsIGZvbGxvd2luZyBTZWFkZXIgRXhhbXBsZSA5LjUuCgogICAgRGlzdHJpYnV0aW5nIGNvbXBvbmVudHM6IHRoZSB0d28ga2V5cywgZXZlcnkgY29tcG9uZW50IGxpZ2h0ZXIgdGhhbgogICAgdGhlIGxpZ2h0IGtleSAodGFrZW4gdG8gcGFzcyB3aG9sbHkgaW50byB0aGUgZGlzdGlsbGF0ZSksIGFuZCB0aGUKICAgIHNpbmdsZSBub24ta2V5IGltbWVkaWF0ZWx5IGhlYXZpZXIgdGhhbiB0aGUgaGVhdnkga2V5LCB3aG9zZQogICAgZGlzdGlsbGF0ZSBmbG93IGlzIGFuIHVua25vd24uICBBbGwgaGVhdmllciBjb21wb25lbnRzIGFyZSB0YWtlbiB0bwogICAgcGFzcyB3aG9sbHkgaW50byB0aGUgYm90dG9tcy4gIFVua25vd25zOiB0aGUgZGlzdGlsbGF0ZSByYXRlIEQKICAgIChsYm1vbC9oKSwgdGhlIG1pbmltdW0gaW50ZXJuYWwgcmVmbHV4IHJhdGUgTG1pbiAobGJtb2wvaCksIGFuZCB0aGUKICAgIGRpc3RpbGxhdGUgZmxvdyBvZiB0aGUgZGlzdHJpYnV0aW5nIG5vbi1rZXk7IGVxdWF0aW9uczogdGhlCiAgICBVbmRlcndvb2QgZGlzdGlsbGF0ZSBlcXVhdGlvbiBhdCB0aGUgdHdvIHJvb3RzIHRoYXQgYnJhY2tldCB0aGUKICAgIGhlYXZ5IGtleSwgYW5kIHRoZSBvdmVyYWxsIGJhbGFuY2UgRCA9IHN1bSBvZiBkaXN0aWxsYXRlIGZsb3dzLgogICAgUmV0dXJucyBkaWN0IHdpdGggdGhldGFfdXNlZCAodGhlIHR3byByb290cyksIHJfbWluID0gTG1pbi9ELAogICAgZF9kaXN0X25vbmtleSwgRCBhbmQgTG1pbi4KICAgICIiIgogICAgZiA9IG5wLmFzYXJyYXkoaW5wWyJmZWVkIl0sIGZsb2F0KQogICAgYSA9IG5wLmFzYXJyYXkoaW5wWyJhbHBoYSJdLCBmbG9hdCkKICAgIGxrLCBoayA9IGludChpbnBbImxrIl0pLCBpbnQoaW5wWyJoayJdKQogICAgeiA9IGYgLyBmLnN1bSgpCiAgICByb290cyA9IHVuZGVyd29vZF9yb290cyhhLCB6LCBmbG9hdChpbnBbInEiXSkpCiAgICAjIFRoZSB0d28gcm9vdHMgdXNlZCBicmFja2V0IHRoZSBoZWF2eSBrZXkgZnJvbSBhYm92ZSBhbmQgYmVsb3cuCiAgICBhYm92ZSA9IFt0IGZvciB0IGluIHJvb3RzIGlmIGFbaGtdIDwgdCA8IGFbbGtdXQogICAgYmVsb3cgPSBbdCBmb3IgdCBpbiByb290cyBpZiBhW2hrICsgMV0gPCB0IDwgYVtoa11dCiAgICBpZiBsZW4oYWJvdmUpICE9IDEgb3IgbGVuKGJlbG93KSAhPSAxOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIlRoZSBVbmRlcndvb2Qgcm9vdHMgYnJhY2tldGluZyB0aGUgaGVhdnkga2V5ICIKICAgICAgICAgICAgICAgICAgICAgICAgICJ3ZXJlIG5vdCBmb3VuZCB1bmlxdWVseTsgdGhlIHNlcGFyYXRpb24gYXMgIgogICAgICAgICAgICAgICAgICAgICAgICAgInNwZWNpZmllZCBoYXMgbm8gQ2xhc3MgMiBzb2x1dGlvbiBvZiB0aGUgIgogICAgICAgICAgICAgICAgICAgICAgICAgImZvcm0gdXNlZCBvbiB0aGlzIHBhZ2UuIikKICAgIHRoZXRhcyA9IFthYm92ZVswXSwgYmVsb3dbMF1dCiAgICBqID0gaGsgKyAxICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgZGlzdHJpYnV0aW5nIG5vbi1rZXkgaW5kZXgKICAgIGtub3duID0ge2k6IGZsb2F0KGZbaV0pIGZvciBpIGluIHJhbmdlKGxrKX0gICAjIGxpZ2h0ZXIgdGhhbiBMSzogYWxsIHVwCiAgICBrbm93bltsa10gPSBmbG9hdChpbnBbImRfbGsiXSkKICAgIGtub3duW2hrXSA9IGZsb2F0KGlucFsiZF9oayJdKQogICAgIyBVbmtub3duIHZlY3RvciB4ID0gW0QsIExtaW4sIGRfal07IGZvciBlYWNoIHRoZXRhOgogICAgIyAgIHN1bV9rbm93biBhbHBoYV9pIGRfaS8oYWxwaGFfaSAtIHRoZXRhKQogICAgIyAgICAgKyBhbHBoYV9qIGRfai8oYWxwaGFfaiAtIHRoZXRhKSAtIEQgLSBMbWluID0gMAogICAgcm93cywgcmhzID0gW10sIFtdCiAgICBmb3IgdGggaW4gdGhldGFzOgogICAgICAgIHJvdyA9IFstMS4wLCAtMS4wLCBhW2pdIC8gKGFbal0gLSB0aCldCiAgICAgICAgdmFsID0gLXN1bShhW2ldICogZHYgLyAoYVtpXSAtIHRoKSBmb3IgaSwgZHYgaW4ga25vd24uaXRlbXMoKSkKICAgICAgICByb3dzLmFwcGVuZChyb3cpCiAgICAgICAgcmhzLmFwcGVuZCh2YWwpCiAgICByb3dzLmFwcGVuZChbMS4wLCAwLjAsIC0xLjBdKQogICAgcmhzLmFwcGVuZChzdW0oa25vd24udmFsdWVzKCkpKQogICAgc29sID0gbnAubGluYWxnLnNvbHZlKG5wLmFycmF5KHJvd3MpLCBucC5hcnJheShyaHMpKQogICAgRCwgTG1pbiwgZF9qID0gKGZsb2F0KHYpIGZvciB2IGluIHNvbCkKICAgIGlmIEQgPD0gMCBvciBMbWluIDw9IDAgb3IgZF9qIDwgMCBvciBkX2ogPiBmW2pdOgogICAgICAgIHJhaXNlIFZhbHVlRXJyb3IoIlRoZSBDbGFzcyAyIHNvbHZlIGdhdmUgYSBub24tcGh5c2ljYWwgcmVzdWx0ICIKICAgICAgICAgICAgICAgICAgICAgICAgICIoYSBuZWdhdGl2ZSBmbG93IG9yIGEgcmVmbHV4IHJhdGUgYmVsb3cgemVybyk7ICIKICAgICAgICAgICAgICAgICAgICAgICAgICJjaGVjayB0aGUga2V5IHNwbGl0cyBhbmQgdGhlIGZlZWQgcXVhbGl0eS4iKQogICAgcmV0dXJuIHsidGhldGFfYWxsIjogcm9vdHMsICJ0aGV0YV91c2VkIjogdGhldGFzLAogICAgICAgICAgICAicl9taW4iOiBMbWluIC8gRCwgImxfbWluIjogTG1pbiwgIkQiOiBELCAiZF9kaXN0X25vbmtleSI6IGRfaiwKICAgICAgICAgICAgImRpc3Rfbm9ua2V5X2luZGV4Ijogan0KCgpkZWYgZ2lsbGlsYW5kKHJfbWluLCBuX21pbiwgbXVsdCk6CiAgICAiIiJFZHVsamVlJ3MgZXF1YXRpb24gZm9yIHRoZSBHaWxsaWxhbmQgY29ycmVsYXRpb24gKFNlYWRlcgogICAgRXEuIDktMzMpLiAgWCA9IChSIC0gUm1pbikvKFIgKyAxKSBhbmQgWSA9IChOIC0gTm1pbikvKE4gKyAxKSBhcmUKICAgIGRpbWVuc2lvbmxlc3MgY29ycmVsYXRpb24gdmFyaWFibGVzOyBSID0gbXVsdCAqIFJtaW4uIiIiCiAgICBSID0gbXVsdCAqIHJfbWluCiAgICBYID0gKFIgLSByX21pbikgLyAoUiArIDEuMCkKICAgIFkgPSAxLjAgLSBucC5leHAoKCgxLjAgKyA1NC40ICogWCkgKiAoWCAtIDEuMCkpCiAgICAgICAgICAgICAgICAgICAgIC8gKCgxMS4wICsgMTE3LjIgKiBYKSAqIG5wLnNxcnQoWCkpKQogICAgTiA9IChuX21pbiArIFkpIC8gKDEuMCAtIFkpCiAgICByZXR1cm4geyJSIjogZmxvYXQoUiksICJYIjogZmxvYXQoWCksICJZIjogZmxvYXQoWSksICJOIjogZmxvYXQoTil9CgoKZGVmIGZlZWRfc3RhZ2UoaW5wLCBkaXN0LCBuX3N0YWdlcyk6CiAgICAiIiJGZWVkLXN0YWdlIGxvY2F0aW9uLiAgS2lya2JyaWRlJ3MgZXF1YXRpb24gZ2l2ZXMgdGhlIHJhdGlvCiAgICBOUi9OUyBvZiBlcXVpbGlicml1bSBzdGFnZXMgYWJvdmUgdGhlIGZlZWQgKHJlY3RpZnlpbmcgc2VjdGlvbikgdG8KICAgIHN0YWdlcyBiZWxvdyBpdCAoc3RyaXBwaW5nIHNlY3Rpb24pLCBjb3VudGluZyB0aGUgcGFydGlhbCByZWJvaWxlcgogICAgaW4gdGhlIHN0cmlwcGluZyBzZWN0aW9uIGFuZCBleGNsdWRpbmcgdGhlIHRvdGFsIGNvbmRlbnNlci4gIFRoZQogICAgRmVuc2tlIHNlY3Rpb24gcmF0aW8gYXBwbGllcyB0aGUgRmVuc2tlIGVxdWF0aW9uIHRvIGVhY2ggc2VjdGlvbgogICAgc2VwYXJhdGVseSBhdCB0b3RhbCByZWZsdXguICBNb2xlIGZyYWN0aW9uczogeiBpbiB0aGUgZmVlZCwgeEQgaW4KICAgIHRoZSBkaXN0aWxsYXRlLCB4QiBpbiB0aGUgYm90dG9tcyAoYWxsIGRpbWVuc2lvbmxlc3MpLiIiIgogICAgZiA9IG5wLmFzYXJyYXkoaW5wWyJmZWVkIl0sIGZsb2F0KQogICAgbGssIGhrID0gaW50KGlucFsibGsiXSksIGludChpbnBbImhrIl0pCiAgICBkLCBiID0gZGlzdFsiZCJdLCBkaXN0WyJiIl0KICAgIHogPSBmIC8gZi5zdW0oKQogICAgeEQgPSBkIC8gZC5zdW0oKQogICAgeEIgPSBiIC8gYi5zdW0oKQogICAga2lyayA9ICgoeltoa10gLyB6W2xrXSkgKiAoeEJbbGtdIC8geERbaGtdKSAqKiAyCiAgICAgICAgICAgICogKGIuc3VtKCkgLyBkLnN1bSgpKSkgKiogMC4yMDYKICAgIGFfbGtfaGsgPSBkaXN0WyJhbHBoYV9sa19oayJdCiAgICBucl9taW4gPSAobnAubG9nMTAoKHhEW2xrXSAvIHhEW2hrXSkgKiAoeltoa10gLyB6W2xrXSkpCiAgICAgICAgICAgICAgLyBucC5sb2cxMChhX2xrX2hrKSkKICAgIG5zX21pbiA9IChucC5sb2cxMCgoeltsa10gLyB6W2hrXSkgKiAoeEJbaGtdIC8geEJbbGtdKSkKICAgICAgICAgICAgICAvIG5wLmxvZzEwKGFfbGtfaGspKQogICAgZmVuc2tlX3JhdGlvID0gbnJfbWluIC8gbnNfbWluCiAgICBvdXQgPSB7fQogICAgZm9yIGxhYmVsLCByYXRpbyBpbiAoKCJraXJrYnJpZGUiLCBraXJrKSwgKCJmZW5za2UiLCBmZW5za2VfcmF0aW8pKToKICAgICAgICBucyA9IG5fc3RhZ2VzIC8gKDEuMCArIHJhdGlvKQogICAgICAgIG91dFtsYWJlbF0gPSB7InJhdGlvIjogZmxvYXQocmF0aW8pLCAibl9yZWN0IjogZmxvYXQocmF0aW8gKiBucyksCiAgICAgICAgICAgICAgICAgICAgICAibl9zdHJpcCI6IGZsb2F0KG5zKX0KICAgIHJldHVybiBvdXQKCgpkZWYgcGxhaW4obyk6CiAgICAiIiJudW1weSB2YWx1ZXMgLT4gSlNPTi1mcmllbmRseSBwbGFpbiBkYXRhIChOYU4vaW5mIC0+IE5vbmUpLiIiIgogICAgaWYgaXNpbnN0YW5jZShvLCBucC5uZGFycmF5KToKICAgICAgICByZXR1cm4gW3BsYWluKHYpIGZvciB2IGluIG8udG9saXN0KCldIGlmIG8ubmRpbSBlbHNlIHBsYWluKG8uaXRlbSgpKQogICAgaWYgaXNpbnN0YW5jZShvLCAobGlzdCwgdHVwbGUpKToKICAgICAgICByZXR1cm4gW3BsYWluKHYpIGZvciB2IGluIG9dCiAgICBpZiBpc2luc3RhbmNlKG8sIGRpY3QpOgogICAgICAgIHJldHVybiB7azogcGxhaW4odikgZm9yIGssIHYgaW4gby5pdGVtcygpfQogICAgaWYgaXNpbnN0YW5jZShvLCAobnAuZmxvYXRpbmcsIGZsb2F0KSk6CiAgICAgICAgdiA9IGZsb2F0KG8pCiAgICAgICAgcmV0dXJuIHYgaWYgbnAuaXNmaW5pdGUodikgZWxzZSBOb25lCiAgICBpZiBpc2luc3RhbmNlKG8sIChucC5pbnRlZ2VyLCkpOgogICAgICAgIHJldHVybiBpbnQobykKICAgIHJldHVybiBvCgoKZGVmIF9maWdfbGF5b3V0KHhfdGl0bGUsIHlfdGl0bGUpOgogICAgcmV0dXJuIGRpY3QodGVtcGxhdGU9InBsb3RseV93aGl0ZSIsCiAgICAgICAgICAgICAgICB4YXhpcz1kaWN0KHRpdGxlPXhfdGl0bGUpLCB5YXhpcz1kaWN0KHRpdGxlPXlfdGl0bGUpLAogICAgICAgICAgICAgICAgbGVnZW5kPWRpY3QoeD0xLjAyLCB5PTEuMCwgeGFuY2hvcj0ibGVmdCIsIHlhbmNob3I9InRvcCIpLAogICAgICAgICAgICAgICAgbWFyZ2luPWRpY3QobD02MCwgcj0xNzAsIHQ9MzAsIGI9NTUpKQoKCmRlZiBydW5fY2FzZShpbnApOgogICAgIiIiRnVsbCBGVUcgY2FsY3VsYXRpb24gZm9yIG9uZSBpbnB1dCBzZXQuICBSZXR1cm5zIGEgcGxhaW4tZGF0YQogICAgZGljdDogbWV0cmljcywgdGhlIGZsb3cgdGFibGUsIGFuZCB0aGUgdGhyZWUgQXBwIGZpZ3VyZXMgYXMgUGxvdGx5CiAgICB0cmFjZS9sYXlvdXQgZGljdHMuIiIiCiAgICBkaXN0ID0gZmVuc2tlKGlucCkKICAgIHVuZCA9IHVuZGVyd29vZF9jbGFzczIoaW5wLCBkaXN0KQogICAgZ2lsID0gZ2lsbGlsYW5kKHVuZFsicl9taW4iXSwgZGlzdFsibl9taW4iXSwgZmxvYXQoaW5wWyJtdWx0Il0pKQogICAgbl9yb3VuZCA9IGludChucC5jZWlsKGdpbFsiTiJdKSkKICAgIHRyYXlzX3RoZW9yZXRpY2FsID0gbl9yb3VuZCAtIDEgICAgICAgICMgcmVib2lsZXIgaXMgb25lIG9mIHRoZSBzdGFnZXMKICAgIGVmZiA9IGZsb2F0KGlucFsiZWZmaWNpZW5jeSJdKQogICAgdHJheXNfYWN0dWFsID0gaW50KG5wLmNlaWwodHJheXNfdGhlb3JldGljYWwgLyBlZmYpKQogICAgZnMgPSBmZWVkX3N0YWdlKGlucCwgZGlzdCwgZmxvYXQobl9yb3VuZCkpCiAgICBmID0gbnAuYXNhcnJheShpbnBbImZlZWQiXSwgZmxvYXQpCiAgICBhID0gbnAuYXNhcnJheShpbnBbImFscGhhIl0sIGZsb2F0KQogICAgeiA9IGYgLyBmLnN1bSgpCgogICAgIyBGaWcuIEE6IEdpbGxpbGFuZCBjdXJ2ZSAoRWR1bGplZSkgd2l0aCB0aGUgb3BlcmF0aW5nIHBvaW50LgogICAgbXVsdHMgPSBucC5jb25jYXRlbmF0ZSgoWzEuMDAxXSwgbnAubGluc3BhY2UoMS4wMSwgNC4wLCAxMjApKSkKICAgIHhzLCB5cyA9IFtdLCBbXQogICAgZm9yIG0gaW4gbXVsdHM6CiAgICAgICAgZyA9IGdpbGxpbGFuZCh1bmRbInJfbWluIl0sIGRpc3RbIm5fbWluIl0sIGZsb2F0KG0pKQogICAgICAgIHhzLmFwcGVuZChnWyJYIl0pCiAgICAgICAgeXMuYXBwZW5kKGdbIlkiXSkKICAgIGZpZ19naWxsaWxhbmQgPSB7CiAgICAgICAgImRhdGEiOiBbCiAgICAgICAgICAgIGRpY3QodHlwZT0ic2NhdHRlciIsIHg9eHMsIHk9eXMsIG1vZGU9ImxpbmVzIiwKICAgICAgICAgICAgICAgICBuYW1lPSJHaWxsaWxhbmQgY29ycmVsYXRpb24gKEVkdWxqZWUgZXF1YXRpb24pIiwKICAgICAgICAgICAgICAgICBsaW5lPWRpY3QoY29sb3I9IiMwMDcyQjIiLCB3aWR0aD0yKSksCiAgICAgICAgICAgIGRpY3QodHlwZT0ic2NhdHRlciIsIHg9W2dpbFsiWCJdXSwgeT1bZ2lsWyJZIl1dLAogICAgICAgICAgICAgICAgIG1vZGU9Im1hcmtlcnMiLCBuYW1lPSJPcGVyYXRpbmcgcG9pbnQiLAogICAgICAgICAgICAgICAgIG1hcmtlcj1kaWN0KGNvbG9yPSIjRDU1RTAwIiwgc2l6ZT0xMSwgc3ltYm9sPSJjaXJjbGUiLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgIGxpbmU9ZGljdChjb2xvcj0iIzdhMzQwMCIsIHdpZHRoPTEpKSldLAogICAgICAgICJsYXlvdXQiOiBfZmlnX2xheW91dCgiWCAoZGltZW5zaW9ubGVzcykiLCAiWSAoZGltZW5zaW9ubGVzcykiKX0KCiAgICAjIEZpZy4gQjogVW5kZXJ3b29kIGZlZWQgZnVuY3Rpb24gb24gZWFjaCB2b2xhdGlsaXR5IGludGVydmFsLAogICAgIyBjbGlwcGVkIGZvciBkaXNwbGF5OyBhbGwgcm9vdHMgc2hvd24sIHRoZSB0d28gdXNlZCBtYXJrZWQuCiAgICB0cmFjZXMgPSBbXQogICAgYV9zb3J0ZWQgPSBucC5zb3J0KGEpWzo6LTFdCiAgICBmb3IgaGksIGxvIGluIHppcChhX3NvcnRlZFs6LTFdLCBhX3NvcnRlZFsxOl0pOgogICAgICAgIHRoID0gbnAubGluc3BhY2UobG8gKyAxZS00LCBoaSAtIDFlLTQsIDYwKQogICAgICAgIHV1ID0gbnAuYXJyYXkoW3VuZGVyd29vZF9mdW5jdGlvbih0LCBhLCB6LCBmbG9hdChpbnBbInEiXSkpCiAgICAgICAgICAgICAgICAgICAgICAgZm9yIHQgaW4gdGhdKQogICAgICAgIHV1ID0gbnAuY2xpcCh1dSwgLTYuMCwgNi4wKQogICAgICAgIHRyYWNlcy5hcHBlbmQoZGljdCh0eXBlPSJzY2F0dGVyIiwgeD10aC50b2xpc3QoKSwgeT11dS50b2xpc3QoKSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgbW9kZT0ibGluZXMiLCBzaG93bGVnZW5kPUZhbHNlLAogICAgICAgICAgICAgICAgICAgICAgICAgICBsaW5lPWRpY3QoY29sb3I9IiMwMDcyQjIiLCB3aWR0aD0xLjUpKSkKICAgIHRyYWNlcy5hcHBlbmQoZGljdCgKICAgICAgICB0eXBlPSJzY2F0dGVyIiwgeD11bmRbInRoZXRhX2FsbCJdLAogICAgICAgIHk9WzAuMF0gKiBsZW4odW5kWyJ0aGV0YV9hbGwiXSksIG1vZGU9Im1hcmtlcnMiLAogICAgICAgIG5hbWU9IkFsbCByb290cyBvZiB0aGUgZmVlZCBlcXVhdGlvbiIsCiAgICAgICAgbWFya2VyPWRpY3QoY29sb3I9IiM5OTk5OTkiLCBzaXplPTgsIHN5bWJvbD0iY2lyY2xlLW9wZW4iLAogICAgICAgICAgICAgICAgICAgIGxpbmU9ZGljdCh3aWR0aD0yKSkpKQogICAgdHJhY2VzLmFwcGVuZChkaWN0KAogICAgICAgIHR5cGU9InNjYXR0ZXIiLCB4PXVuZFsidGhldGFfdXNlZCJdLCB5PVswLjAsIDAuMF0sCiAgICAgICAgbW9kZT0ibWFya2VycyIsIG5hbWU9IlJvb3RzIHVzZWQgZm9yIHRoZSBDbGFzcyAyIHNvbHZlIiwKICAgICAgICBtYXJrZXI9ZGljdChjb2xvcj0iI0Q1NUUwMCIsIHNpemU9MTEsIHN5bWJvbD0iY2lyY2xlIikpKQogICAgZmlnX3VuZGVyd29vZCA9IHsKICAgICAgICAiZGF0YSI6IHRyYWNlcywKICAgICAgICAibGF5b3V0IjogX2ZpZ19sYXlvdXQoInRoZXRhIChkaW1lbnNpb25sZXNzKSIsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICJVbmRlcndvb2QgZmVlZCBmdW5jdGlvbiAoZGltZW5zaW9ubGVzcykiKX0KCiAgICAjIEZpZy4gQzogY29tcG9uZW50IGRpc3RyaWJ1dGlvbiwgbG9nYXJpdGhtaWMgc2NhbGUgKGZsb3dzIHNwYW4KICAgICMgMTAgb3JkZXJzIG9mIG1hZ25pdHVkZSk7IGRvdWJsZSBlbmNvZGluZyBieSBjb2xvdXIgYW5kIHBhdHRlcm4uCiAgICBuYW1lcyA9IGxpc3QoaW5wWyJuYW1lcyJdKQogICAgZmlnX2Rpc3QgPSB7CiAgICAgICAgImRhdGEiOiBbCiAgICAgICAgICAgIGRpY3QodHlwZT0iYmFyIiwgeD1uYW1lcywgeT1ucC5tYXhpbXVtKGRpc3RbImQiXSwgMWUtMTIpLnRvbGlzdCgpLAogICAgICAgICAgICAgICAgIG5hbWU9IkRpc3RpbGxhdGUgZmxvdyByYXRlIiwgbWFya2VyPWRpY3QoY29sb3I9IiMwMDcyQjIiKSksCiAgICAgICAgICAgIGRpY3QodHlwZT0iYmFyIiwgeD1uYW1lcywgeT1ucC5tYXhpbXVtKGRpc3RbImIiXSwgMWUtMTIpLnRvbGlzdCgpLAogICAgICAgICAgICAgICAgIG5hbWU9IkJvdHRvbXMgZmxvdyByYXRlIiwKICAgICAgICAgICAgICAgICBtYXJrZXI9ZGljdChjb2xvcj0iI0Q1NUUwMCIsIHBhdHRlcm49ZGljdChzaGFwZT0iLyIpKSldLAogICAgICAgICJsYXlvdXQiOiBkaWN0KHRlbXBsYXRlPSJwbG90bHlfd2hpdGUiLCBiYXJtb2RlPSJncm91cCIsCiAgICAgICAgICAgICAgICAgICAgICAgeGF4aXM9ZGljdCh0aXRsZT0iQ29tcG9uZW50IiksCiAgICAgICAgICAgICAgICAgICAgICAgeWF4aXM9ZGljdCh0aXRsZT0iRmxvdyByYXRlIChsYm1vbC9oKSIsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB0eXBlPSJsb2ciKSwKICAgICAgICAgICAgICAgICAgICAgICBsZWdlbmQ9ZGljdCh4PTEuMDIsIHk9MS4wLCB4YW5jaG9yPSJsZWZ0IiwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB5YW5jaG9yPSJ0b3AiKSwKICAgICAgICAgICAgICAgICAgICAgICBtYXJnaW49ZGljdChsPTYwLCByPTE3MCwgdD0zMCwgYj01NSkpfQoKICAgIG1ldHJpY3MgPSB7CiAgICAgICAgIm5fbWluIjogZGlzdFsibl9taW4iXSwgImFscGhhX2xrX2hrIjogZGlzdFsiYWxwaGFfbGtfaGsiXSwKICAgICAgICAiRF9mZW5za2UiOiBmbG9hdChkaXN0WyJkIl0uc3VtKCkpLCAiQl9mZW5za2UiOiBmbG9hdChkaXN0WyJiIl0uc3VtKCkpLAogICAgICAgICJ0aGV0YV91c2VkIjogdW5kWyJ0aGV0YV91c2VkIl0sICJyX21pbiI6IHVuZFsicl9taW4iXSwKICAgICAgICAiRF9jbGFzczIiOiB1bmRbIkQiXSwgImRfZGlzdF9ub25rZXkiOiB1bmRbImRfZGlzdF9ub25rZXkiXSwKICAgICAgICAiZGlzdF9ub25rZXlfbmFtZSI6IG5hbWVzW3VuZFsiZGlzdF9ub25rZXlfaW5kZXgiXV0sCiAgICAgICAgIlIiOiBnaWxbIlIiXSwgIlgiOiBnaWxbIlgiXSwgIlkiOiBnaWxbIlkiXSwgIk4iOiBnaWxbIk4iXSwKICAgICAgICAibl9yb3VuZCI6IG5fcm91bmQsICJ0cmF5c190aGVvcmV0aWNhbCI6IHRyYXlzX3RoZW9yZXRpY2FsLAogICAgICAgICJ0cmF5c19hY3R1YWwiOiB0cmF5c19hY3R1YWwsCiAgICAgICAgImZlZWRfa2lya2JyaWRlIjogZnNbImtpcmticmlkZSJdLCAiZmVlZF9mZW5za2UiOiBmc1siZmVuc2tlIl0sCiAgICB9CiAgICByZXR1cm4gcGxhaW4oewogICAgICAgICJtZXRyaWNzIjogbWV0cmljcywKICAgICAgICAibmFtZXMiOiBuYW1lcywKICAgICAgICAiZmVlZCI6IGYudG9saXN0KCksICJhbHBoYSI6IGEudG9saXN0KCksCiAgICAgICAgImQiOiBkaXN0WyJkIl0udG9saXN0KCksICJiIjogZGlzdFsiYiJdLnRvbGlzdCgpLAogICAgICAgICJmaWdzIjogeyJnaWxsaWxhbmQiOiBmaWdfZ2lsbGlsYW5kLCAidW5kZXJ3b29kIjogZmlnX3VuZGVyd29vZCwKICAgICAgICAgICAgICAgICAiZGlzdHJpYnV0aW9uIjogZmlnX2Rpc3R9LAogICAgfSkKCgpkZWYgY2xhc3MxX2NoZWNrKCk6CiAgICAiIiJTZWFkZXIgRXhhbXBsZSA5LjQgKENsYXNzIDEgZXN0aW1hdGUpLCBmcm9tIHRoZSBxdWFudGl0aWVzIGdpdmVuCiAgICBpbiBFeGFtcGxlcyA5LjEgYW5kIDkuNCBvZiB0aGUgc291cmNlIHRleHQuICBGZWVkIGxpcXVpZCByYXRlCiAgICA3NTkgbGJtb2wvaCBvZiBhIGZlZWQgcmF0ZSBvZiA4NzYuMyBsYm1vbC9oOyBmZWVkLWxpcXVpZCBmbG93cyBvZgogICAgdGhlIGxpZ2h0IGtleSAzNDUuNDEgbGJtb2wvaCBhbmQgb2YgdGhlIGhlYXZ5IGtleSAzMS4yOCBsYm1vbC9oOwogICAgcmVsYXRpdmUgdm9sYXRpbGl0eSBvZiB0aGUga2V5cyBhdCBmZWVkIGNvbmRpdGlvbnMgMS45Njc7CiAgICBkaXN0aWxsYXRlIGZsb3dzIG9mIHRoZSBrZXlzIDQ0MiBhbmQgMTMgbGJtb2wvaC4gIFJldHVybnMgdGhlCiAgICBtaW5pbXVtIGludGVybmFsIHJlZmx1eCBwZXIgdW5pdCBmZWVkLCBpdHMgY29udmVyc2lvbiBwZXIgdW5pdAogICAgZGlzdGlsbGF0ZSBhdCB0aGUgRmVuc2tlIGRpc3RpbGxhdGUgcmF0ZSA0NjguOTUgbGJtb2wvaCwgYW5kCiAgICBTZWFkZXIncyBwcmludGVkIHBlci1kaXN0aWxsYXRlIHZhbHVlLCB3aGljaCBkb2VzIG5vdCBmb2xsb3cgZnJvbQogICAgdGhlIHByaW50ZWQgcGVyLWZlZWQgdmFsdWUgKHNlZSB0aGUgVGhlb3J5IHBhbmVsKS4iIiIKICAgIGxfcGVyX2YgPSAoNzU5LjAgLyA4NzYuMykgKiAoKDQ0Mi4wIC8gMzQ1LjQxKQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAtIDEuOTY3ICogKDEzLjAgLyAzMS4yOCkpIC8gKDEuOTY3IC0gMS4wKQogICAgcGVyX2QgPSBsX3Blcl9mICogODc2LjMgLyA0NjguOTUKICAgIHJldHVybiB7ImxfcGVyX2YiOiBmbG9hdChsX3Blcl9mKSwgInBlcl9kX3JlY29tcHV0ZWQiOiBmbG9hdChwZXJfZCksCiAgICAgICAgICAgICJwZXJfZF9wcmludGVkIjogMC44NjR9Cg==").decode("utf-8")
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

    Combined with $f_i = d_i + b_i$, this fixes every non-key flow. Following Seader's guidance, the smaller of $d_i$ and $b_i$ is computed from the equation first and the larger by difference, which keeps the small flows accurate; several distillate flows are below $10^{-6}$ lbmol/h. The chart uses a logarithmic scale because the flows span ten orders of magnitude; colour and pattern both encode the product, so the chart reads in greyscale. These total-reflux flows are the product distribution used by the rest of the method.
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

    One further point is recorded in this cell's output. Seader prints the Class 1 ratio as $0.864$ per unit distillate. Converted at the distillate rate of Step 3, his per-feed value of $0.414$ gives $0.774$ per unit distillate, not $0.864$; the printed $0.864$ follows from a feed rate of $976.3$ lbmol/h in place of $876.3$ lbmol/h. The page reports both values and uses neither for its headline result.
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

    The symbol $q$ denotes the feed quality, the liquid fraction of the feed as it enters the column, dimensionless. In Seader's Example 9.1 the feed is flashed into the column and $13.4$ percent vaporises, so $q = 0.866$ here, not $1$. The left side is a sum over all components $i$ of the feed. The equation has one root $\theta$ in every interval between consecutive relative volatilities — seven roots for eight components — and the chart shows the left side minus the right side, clipped to the range shown, with every root marked.

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

    Solving $Y = (N - N_{min})/(N + 1)$ for $N$ gives the stage requirement. As $R$ approaches $R_{min}$, $X$ approaches $0$ and $N$ grows without bound; as $R$ grows without bound, $N$ approaches $N_{min}$. The correlation carries no feed-condition parameter, a known limitation Seader records: it is conservative for feeds of low $q$. The chart plots the full curve, not only the operating point.
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
