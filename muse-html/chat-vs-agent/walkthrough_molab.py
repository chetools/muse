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
    MODULE_SRC = base64.b64decode("IiIiQ2FsY3VsYXRpb25zIGZvciB0aGUgY2hhdC1tb2RlIHZlcnN1cyBhZ2VudC1tb2RlIGNvbXBhcmlzb24gcGFnZS4KCkV2ZXJ5IHF1YW50aXR5IGluIHRoaXMgbW9kdWxlIGlzIG9uZSBvZiB0aGUgZm91ciBxdWFudGl0aWVzIHRoYXQgYQpmcm9udGllciBtb2RlbCAoTXVzZSBTcGFyayAxLjMpLCB0ZXN0ZWQgaW4gY2hhdCBtb2RlIG9uIDI0IE9jdG9iZXIgMjAyNiwKcmVwb3J0ZWQgd2l0aCBhIG1hdGVyaWFsIGVycm9yLCByZWNvbXB1dGVkIGhlcmUgYnkgcHJvZ3JhbSBleGVjdXRpb24uClRoZSByZWNvcmRlZCBjaGF0LW1vZGUgYW5zd2VycyBhcmUgc3RvcmVkIGFzIGRhdGEgKENIQVRfMSB0byBDSEFUXzQpCnNvIHRoZSBwYWdlIGNhbiBwbGFjZSB0aGVtIGJlc2lkZSB0aGUgY29tcHV0ZWQgdmFsdWVzLiAgVGhlIHNjcmVlbmluZwpwcm90b2NvbCBhbmQgdGhlIHZlcmlmaWVkIHZhbHVlcyBhcmUgcmVjb3JkZWQgaW4gdGhlIGNvbXBhbmlvbgpicmllZmluZyBkb2N1bWVudCwgIlJlc2lkdWFsIEVycm9yIEFmdGVyIEZyb250aWVyLU1vZGVsCkNyb3NzLVZlcmlmaWNhdGlvbiBpbiBDaGVtaWNhbCBFbmdpbmVlcmluZyBEZXNpZ24iLCBTZWN0aW9uIDExLgoKVW5pdHMgYXJlIFNJIHRocm91Z2hvdXQsIHdpdGggYW1vdW50cyBvZiBzdWJzdGFuY2UgY29uY2VudHJhdGlvbiBpbgptb2wvTCBhbmQgbW9uZXkgaW4gZG9sbGFycyBwZXIgeWVhciAoZG9sbGFycy95cikgYXMgc3RhdGVkIHBlciBmdW5jdGlvbi4KIiIiCmltcG9ydCBudW1weSBhcyBucApmcm9tIHNjaXB5Lm9wdGltaXplIGltcG9ydCBjdXJ2ZV9maXQsIGZzb2x2ZQoKIyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KIyBSZWNvcmRlZCBjaGF0LW1vZGUgYW5zd2VycyAoZGF0YSwgcXVvdGVkIGZyb20gdGhlIHNjcmVlbmluZyByZWNvcmQpLgojIGsgaXMgdGhlIHJhdGUgY29uc3RhbnQgaW4gKG1vbC9MKV4oMS1uKSBtaW5eLTEsIHdoZXJlIG4gaXMgdGhlCiMgcmVhY3Rpb24gb3JkZXIgKGRpbWVuc2lvbmxlc3MpOyBTRSBkZW5vdGVzIHN0YW5kYXJkIGVycm9yLgojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQpDSEFUXzEgPSB7Im4iOiAxLjgwLCAiayI6IDAuMDM4LCAic2VfbiI6IDAuMDMsICJzZV9rIjogMC4wMDIsCiAgICAgICAgICAicm1zZSI6IDAuMDA5LCAiY18yNDAiOiAwLjA3N30gICAgICAgICAgIyBFeGFtcGxlIDEsIDQxIHBvaW50cwpDSEFUXzIgPSB7Im4iOiAxLjgsICJrIjogMC4wMzksICJybXNlIjogMC4wMTMsCiAgICAgICAgICAiY18xNTAiOiAwLjEyfSAgICAgICAgICAgICAgICAgICAgICAgICAgIyBFeGFtcGxlIDIsIDI1IHBvaW50cwpDSEFUXzMgPSB7ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgRXhhbXBsZSAzLCBwaXBlIGNvc3RzCiAgICAwLjI4OiB7ImRwX2twYSI6IDc3MS4wLCAicG93ZXJfa3ciOiAxMTQuNywgImVuZXJneSI6IDEzMTYwMC4wLAogICAgICAgICAgICJjYXBpdGFsIjogMzQxNjAwLjAsICJ0b3RhbCI6IDQ3MzIwMC4wfSwKICAgIDAuMzA6IHsiZHBfa3BhIjogNTQ2LjAsICJwb3dlcl9rdyI6IDgxLjIsICJlbmVyZ3kiOiA5MzIwMC4wLAogICAgICAgICAgICJjYXBpdGFsIjogMzgwMTAwLjAsICJ0b3RhbCI6IDQ3MzMwMC4wfSwKICAgICJzYXZpbmciOiAxNDAuMH0KQ0hBVF80ID0geyJBQiI6IDAuMTM0LCAiQkMiOiAwLjA4NCwgIkNEIjogLTAuMDQxLCAiREEiOiAtMC4xNjYsCiAgICAgICAgICAiQ0UiOiAwLjA0NSwgIkVGIjogLTAuMDA1LCAiRkQiOiAtMC4wNTUsCiAgICAgICAgICAiaGVhZF9kIjogMzguNSwgImhlYWRfZiI6IDM3LjB9ICAgICAgICAgICMgRXhhbXBsZSA0LCBuZXR3b3JrCgojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQojIEV4YW1wbGUgMSBkYXRhOiBiYXRjaCByZWFjdG9yLCBjb25jZW50cmF0aW9uIENfQSAobW9sL0wpIG9mIHJlYWN0YW50CiMgQSBhdCB0aW1lIHQgKG1pbikuICBHZW5lcmF0ZWQgZnJvbSBrID0gMC4wMzggKG1vbC9MKV4oMS1uKSBtaW5eLTEgYW5kCiMgbiA9IDEuOCB3aXRoIEdhdXNzaWFuIG5vaXNlIG9mIHN0YW5kYXJkIGRldmlhdGlvbiAwLjAxMCBtb2wvTCwgdGhlbgojIHJvdW5kZWQgdG8gdGhyZWUgZGVjaW1hbHM7IHRoZSBnZW5lcmF0aW5nIHZhbHVlcyBhcmUgbm90IHVzZWQgaW4gdGhlCiMgZml0LCBvbmx5IGluIHRoZSB0ZXN0cy4KIyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KQ19BMCA9IDEuODAgICMgbW9sL0wsIGluaXRpYWwgY29uY2VudHJhdGlvbiBvZiBBIGluIGJvdGgga2luZXRpYyBleGFtcGxlcwpUX1Y1ID0gW2Zsb2F0KHQpIGZvciB0IGluIHJhbmdlKDAsIDIwMSwgNSldICAjIG1pbiwgNDEgcG9pbnRzCkNfVjUgPSBbMS44MDAsIDEuMzg1LCAxLjEwOSwgMC45MDIsIDAuNzY3LCAwLjY2MCwgMC41OTAsIDAuNTE5LCAwLjQ3NCwKICAgICAgICAwLjQwNCwgMC40MDEsIDAuMzUzLCAwLjMzMywgMC4zMDEsIDAuMjc4LCAwLjI2OCwgMC4yNTYsIDAuMjMxLAogICAgICAgIDAuMjE4LCAwLjIxNSwgMC4xODksIDAuMTcyLCAwLjE4MiwgMC4xNjQsIDAuMTQ0LCAwLjE0OCwgMC4xNDUsCiAgICAgICAgMC4xMzEsIDAuMTIzLCAwLjEzMywgMC4xMzcsIDAuMTIxLCAwLjExMiwgMC4xMTksIDAuMTE4LCAwLjEwNSwKICAgICAgICAwLjExMCwgMC4xMTIsIDAuMDk2LCAwLjA4NywgMC4wOTZdICAjIG1vbC9MCgojIEV4YW1wbGUgMiBkYXRhOiBzYW1lIGV4cGVyaW1lbnQgYXQgcGlsb3Qgc2NhbGUsIDI1IHBvaW50cywgbm9pc2UKIyBzdGFuZGFyZCBkZXZpYXRpb24gMC4wMTIgbW9sL0wgYmVmb3JlIHJvdW5kaW5nLgpUX0U1ID0gW2Zsb2F0KHQpIGZvciB0IGluIHJhbmdlKDAsIDEyMSwgNSldICAjIG1pbiwgMjUgcG9pbnRzCkNfRTUgPSBbMS44MDAsIDEuMzc1LCAxLjA5MywgMC44OTcsIDAuNzY0LCAwLjY1NCwgMC41ODUsIDAuNTM1LCAwLjQ2MCwKICAgICAgICAwLjQxNSwgMC4zOTEsIDAuMzU4LCAwLjMyOCwgMC4yOTIsIDAuMjgyLCAwLjI3MiwgMC4yMzEsIDAuMjI3LAogICAgICAgIDAuMTk3LCAwLjE5MiwgMC4xNzUsIDAuMTg1LCAwLjE2MywgMC4xNzQsIDAuMTY1XSAgIyBtb2wvTAoKCmRlZiBraW5ldGljc19tb2RlbCh0LCBrLCBuKToKICAgICIiIkNvbmNlbnRyYXRpb24gb2YgQSAobW9sL0wpIGF0IHRpbWUgdCAobWluKSBmb3IgdGhlIHJhdGUgbGF3CiAgICAtZENfQS9kdCA9IGsgQ19BXm4gd2l0aCBpbml0aWFsIGNvbmNlbnRyYXRpb24gQ19BMCAobW9sL0wpLAogICAgaW50ZWdyYXRlZCBpbiBjbG9zZWQgZm9ybS4gIGsgaXMgaW4gKG1vbC9MKV4oMS1uKSBtaW5eLTEgYW5kIG4gaXMKICAgIGRpbWVuc2lvbmxlc3MuIiIiCiAgICB0ID0gbnAuYXNhcnJheSh0LCBkdHlwZT1mbG9hdCkKICAgIHJldHVybiAoQ19BMCAqKiAoMS4wIC0gbikgKyAobiAtIDEuMCkgKiBrICogdCkgKiogKDEuMCAvICgxLjAgLSBuKSkKCgpkZWYgZml0X2tpbmV0aWNzKHQsIGMpOgogICAgIiIiTm9ubGluZWFyIGxlYXN0LXNxdWFyZXMgZml0IG9mIGsgYW5kIG4gdG8gYWxsIHBvaW50cyAodCwgYyksCiAgICB3aXRoIHQgaW4gbWluIGFuZCBjIGluIG1vbC9MLiAgUmV0dXJucyBhIGRpY3Qgd2l0aCB0aGUgZml0dGVkCiAgICBwYXJhbWV0ZXJzLCB0aGVpciBzdGFuZGFyZCBlcnJvcnMgZnJvbSB0aGUgY292YXJpYW5jZSBtYXRyaXgKICAgIHNeMiAoSl5UIEopXi0xIChKIHRoZSBKYWNvYmlhbiBvZiB0aGUgbW9kZWwgd2l0aCByZXNwZWN0IHRvIChrLCBuKQogICAgYXQgdGhlIGZpdCwgc14yIHRoZSByZXNpZHVhbCB2YXJpYW5jZSB3aXRoIE4gLSAyIGRlZ3JlZXMgb2YKICAgIGZyZWVkb20sIE4gdGhlIG51bWJlciBvZiBwb2ludHMpLCB0aGUgcGFyYW1ldGVyIGNvcnJlbGF0aW9uLCB0aGUKICAgIHJlc2lkdWFsIHN1bSBvZiBzcXVhcmVzIFNTRSAobW9sL0wpXjIsIGFuZCB0aGUgcm9vdC1tZWFuLXNxdWFyZQogICAgZXJyb3IgUk1TRSAobW9sL0wpLiIiIgogICAgdCA9IG5wLmFzYXJyYXkodCwgZHR5cGU9ZmxvYXQpCiAgICBjID0gbnAuYXNhcnJheShjLCBkdHlwZT1mbG9hdCkKICAgIHBvcHQsIHBjb3YgPSBjdXJ2ZV9maXQoa2luZXRpY3NfbW9kZWwsIHQsIGMsIHAwPVswLjAyLCAxLjVdLAogICAgICAgICAgICAgICAgICAgICAgICAgICBib3VuZHM9KFsxZS01LCAwLjVdLCBbMS4wLCAzLjBdKSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgbWF4ZmV2PTIwMDAwMCkKICAgIGssIG4gPSAoZmxvYXQocG9wdFswXSksIGZsb2F0KHBvcHRbMV0pKQogICAgc2UgPSBucC5zcXJ0KG5wLmRpYWcocGNvdikpCiAgICByZXNpZCA9IGMgLSBraW5ldGljc19tb2RlbCh0LCBrLCBuKQogICAgc3NlID0gZmxvYXQobnAuc3VtKHJlc2lkICoqIDIpKQogICAgcmV0dXJuIHsiayI6IGssICJuIjogbiwgInNlX2siOiBmbG9hdChzZVswXSksICJzZV9uIjogZmxvYXQoc2VbMV0pLAogICAgICAgICAgICAiY29ycl9rbiI6IGZsb2F0KHBjb3ZbMCwgMV0gLyAoc2VbMF0gKiBzZVsxXSkpLAogICAgICAgICAgICAic3NlIjogc3NlLCAicm1zZSI6IGZsb2F0KG5wLnNxcnQoc3NlIC8gbGVuKHQpKSksCiAgICAgICAgICAgICJuX3BvaW50cyI6IGludChsZW4odCkpfQoKCmRlZiBleGFtcGxlMSgpOgogICAgIiIiRXhhbXBsZSAxICg0MSBwb2ludHMpOiBmaXQsIHN0YW5kYXJkIGVycm9ycywgcHJlZGljdGlvbiBhdAogICAgdCA9IDI0MCBtaW4sIGFuZCB0aGUgZml0IGZpZ3VyZSBhcyBhIFBsb3RseSBkaWN0LiIiIgogICAgciA9IGZpdF9raW5ldGljcyhUX1Y1LCBDX1Y1KQogICAgclsiY18yNDAiXSA9IGZsb2F0KGtpbmV0aWNzX21vZGVsKDI0MC4wLCByWyJrIl0sIHJbIm4iXSkpCiAgICB0dCA9IG5wLmxpbnNwYWNlKDAuMCwgMjAwLjAsIDIwMSkKICAgIHJbImZpZyJdID0gX2ZpdF9maWcoVF9WNSwgQ19WNSwgdHQsIGtpbmV0aWNzX21vZGVsKHR0LCByWyJrIl0sIHJbIm4iXSksCiAgICAgICAgICAgICAgICAgICAgICAgICJFeGFtcGxlIDEgZGF0YSBhbmQgZml0dGVkIGN1cnZlIikKICAgIHJldHVybiByCgoKZGVmIGV4YW1wbGUyKCk6CiAgICAiIiJFeGFtcGxlIDIgKDI1IHBvaW50cyk6IGZpdCwgcm9vdC1tZWFuLXNxdWFyZSBlcnJvciwgcHJlZGljdGlvbgogICAgYXQgdCA9IDE1MCBtaW4sIGFuZCB0aGUgZml0IGZpZ3VyZSBhcyBhIFBsb3RseSBkaWN0LiIiIgogICAgciA9IGZpdF9raW5ldGljcyhUX0U1LCBDX0U1KQogICAgclsiY18xNTAiXSA9IGZsb2F0KGtpbmV0aWNzX21vZGVsKDE1MC4wLCByWyJrIl0sIHJbIm4iXSkpCiAgICB0dCA9IG5wLmxpbnNwYWNlKDAuMCwgMTIwLjAsIDEyMSkKICAgIHJbImZpZyJdID0gX2ZpdF9maWcoVF9FNSwgQ19FNSwgdHQsIGtpbmV0aWNzX21vZGVsKHR0LCByWyJrIl0sIHJbIm4iXSksCiAgICAgICAgICAgICAgICAgICAgICAgICJFeGFtcGxlIDIgZGF0YSBhbmQgZml0dGVkIGN1cnZlIikKICAgIHJldHVybiByCgoKZGVmIF9maXRfZmlnKHQsIGMsIHR0LCBjYywgX3RpdGxlKToKICAgICIiIlBsb3RseSBkaWN0OiBtZWFzdXJlZCBjb25jZW50cmF0aW9ucyAobWFya2VycykgYW5kIHRoZSBmaXR0ZWQKICAgIGN1cnZlIChsaW5lKSwgY29uY2VudHJhdGlvbnMgaW4gbW9sL0wgYWdhaW5zdCB0aW1lIGluIG1pbi4iIiIKICAgIHJldHVybiB7CiAgICAgICAgImRhdGEiOiBbCiAgICAgICAgICAgIHsidHlwZSI6ICJzY2F0dGVyIiwgIm1vZGUiOiAibWFya2VycyIsICJuYW1lIjogIk1lYXN1cmVkIiwKICAgICAgICAgICAgICJ4IjogbGlzdCh0KSwgInkiOiBsaXN0KGMpLAogICAgICAgICAgICAgIm1hcmtlciI6IHsiY29sb3IiOiAiIzAwNzJCMiIsICJzaXplIjogNn19LAogICAgICAgICAgICB7InR5cGUiOiAic2NhdHRlciIsICJtb2RlIjogImxpbmVzIiwgIm5hbWUiOiAiRml0dGVkIiwKICAgICAgICAgICAgICJ4IjogW2Zsb2F0KHYpIGZvciB2IGluIHR0XSwgInkiOiBbZmxvYXQodikgZm9yIHYgaW4gY2NdLAogICAgICAgICAgICAgImxpbmUiOiB7ImNvbG9yIjogIiNENTVFMDAiLCAid2lkdGgiOiAyfX1dLAogICAgICAgICJsYXlvdXQiOiB7CiAgICAgICAgICAgICJ4YXhpcyI6IHsidGl0bGUiOiAidCAobWluKSJ9LAogICAgICAgICAgICAieWF4aXMiOiB7InRpdGxlIjogIkNfQSAobW9sL0wpIn0sCiAgICAgICAgICAgICJtYXJnaW4iOiB7ImwiOiA1NSwgInIiOiAxMTAsICJ0IjogMTAsICJiIjogNDV9LAogICAgICAgICAgICAibGVnZW5kIjogeyJ4IjogMS4wMiwgInkiOiAxLjAsICJ4YW5jaG9yIjogImxlZnQiLAogICAgICAgICAgICAgICAgICAgICAgICJ5YW5jaG9yIjogInRvcCJ9fX0KCgojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQojIEV4YW1wbGUgMzogc2VsZWN0aW9uIGJldHdlZW4gdHdvIHBpcGUgZGlhbWV0ZXJzLgojIFdhdGVyIGF0IDIwIGRlZ0M6IGRlbnNpdHkgcmhvID0gOTk4IGtnL21eMywgZHluYW1pYyB2aXNjb3NpdHkKIyBtdSA9IDEuMDAyZS0zIFBhIHMuICBGbG93IHJhdGUgUSA9IDAuMTEwIG1eMy9zLCBsaW5lIGxlbmd0aAojIEwgPSA5MDAwIG0sIGFic29sdXRlIHJvdWdobmVzcyBlcHMgPSAwLjA0NSBtbSBmb3IgYm90aCBkaWFtZXRlcnMuCiMgLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tClJITyA9IDk5OC4wICAgICAgICAjIGtnL21eMwpNVSA9IDEuMDAyZS0zICAgICAgIyBQYSBzClFfRkxPVyA9IDAuMTEwICAgICAjIG1eMy9zCkxfTElORSA9IDkwMDAuMCAgICAjIG0KRVBTID0gMC4wNDVlLTMgICAgICMgbQpFVEEgPSAwLjc0ICAgICAgICAgIyBjb21iaW5lZCBwdW1wIGFuZCBtb3RvciBlZmZpY2llbmN5LCBkaW1lbnNpb25sZXNzClBSSUNFID0gMC4xNCAgICAgICAjIGRvbGxhcnMgcGVyIGtXaApIT1VSUyA9IDgyMDAuMCAgICAgIyBoL3lyCkNSRiA9IDAuMTIgICAgICAgICAjIGNhcGl0YWwgcmVjb3ZlcnkgZmFjdG9yLCAxL3lyCgoKZGVmIGNvbGVicm9va19mKHJleW5vbGRzLCBlcHMsIGRpYW1ldGVyKToKICAgICIiIkRhcmN5IGZyaWN0aW9uIGZhY3RvciBmIChkaW1lbnNpb25sZXNzKSBmcm9tIHRoZSBDb2xlYnJvb2sKICAgIGVxdWF0aW9uIGJ5IGZpeGVkLXBvaW50IGl0ZXJhdGlvbjsgcmV5bm9sZHMgaXMgdGhlIFJleW5vbGRzIG51bWJlcgogICAgKGRpbWVuc2lvbmxlc3MpLCBlcHMgdGhlIGFic29sdXRlIHJvdWdobmVzcyAobSkgYW5kIGRpYW1ldGVyIHRoZQogICAgaW5zaWRlIGRpYW1ldGVyIChtKS4iIiIKICAgIGYgPSAwLjAyCiAgICBmb3IgXyBpbiByYW5nZSgyMDApOgogICAgICAgIGZfbmV3ID0gKC0yLjAgKiBucC5sb2cxMChlcHMgLyAoMy43ICogZGlhbWV0ZXIpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICsgMi41MSAvIChyZXlub2xkcyAqIG5wLnNxcnQoZikpKSkgKiogLTIKICAgICAgICBpZiBhYnMoZl9uZXcgLSBmKSA8IDFlLTE0OgogICAgICAgICAgICByZXR1cm4gZmxvYXQoZl9uZXcpCiAgICAgICAgZiA9IGZfbmV3CiAgICByZXR1cm4gZmxvYXQoZikKCgpkZWYgcGlwZV9jb3N0KGRpYW1ldGVyLCBldGE9RVRBLCBwcmljZT1QUklDRSwgZXBzPUVQUyk6CiAgICAiIiJBbm51YWxpc2VkIGNvc3QgYnJlYWtkb3duIGZvciBvbmUgaW5zaWRlIGRpYW1ldGVyIChtKSwgd2l0aCB0aGUKICAgIGNvbWJpbmVkIGVmZmljaWVuY3kgZXRhLCB0aGUgZWxlY3RyaWNpdHkgcHJpY2UgKGRvbGxhcnMgcGVyIGtXaCkKICAgIGFuZCB0aGUgYWJzb2x1dGUgcm91Z2huZXNzIGVwcyAobSkgZGVmYXVsdGluZyB0byB0aGUgc3RhdGVkIGlucHV0cy4KICAgIFJldHVybnMgdGhlIERhcmN5IGZyaWN0aW9uIGZhY3RvciBmLCB0aGUgcHJlc3N1cmUgZHJvcCBpbiBrUGEsCiAgICB0aGUgcHVtcGluZyBwb3dlciBpbiBrVywgYW5kIHRoZSBhbm51YWwgZWxlY3RyaWNpdHkgY29zdCwgdGhlCiAgICBhbm51YWxpc2VkIGNhcGl0YWwgY29zdCBhbmQgdGhlaXIgdG90YWwsIGluIGRvbGxhcnMveXIuIiIiCiAgICBhcmVhID0gbnAucGkgKiBkaWFtZXRlciAqKiAyIC8gNC4wICAgICAgICAgICAgIyBtXjIKICAgIHYgPSBRX0ZMT1cgLyBhcmVhICAgICAgICAgICAgICAgICAgICAgICAgICAgICAjIG0vcywgbWVhbiB2ZWxvY2l0eQogICAgcmV5bm9sZHMgPSBSSE8gKiB2ICogZGlhbWV0ZXIgLyBNVSAgICAgICAgICAgICMgZGltZW5zaW9ubGVzcwogICAgZiA9IGNvbGVicm9va19mKHJleW5vbGRzLCBlcHMsIGRpYW1ldGVyKQogICAgZHAgPSBmICogKExfTElORSAvIGRpYW1ldGVyKSAqIFJITyAqIHYgKiogMiAvIDIuMCAgICMgUGEKICAgIHBvd2VyID0gUV9GTE9XICogZHAgLyBldGEgLyAxMDAwLjAgICAgICAgICAgICAgICAgICAjIGtXCiAgICBlbmVyZ3kgPSBwb3dlciAqIEhPVVJTICogcHJpY2UgICAgICAgICAgICAgICAgICAgICAgIyBkb2xsYXJzL3lyCiAgICBjYXBpdGFsID0gMjI3NS4wICogZGlhbWV0ZXIgKiogMS41NSAqIExfTElORSAqIENSRiAgIyBkb2xsYXJzL3lyCiAgICByZXR1cm4geyJmIjogZiwgImRwX2twYSI6IGRwIC8gMTAwMC4wLCAicG93ZXJfa3ciOiBwb3dlciwKICAgICAgICAgICAgImVuZXJneSI6IGVuZXJneSwgImNhcGl0YWwiOiBjYXBpdGFsLAogICAgICAgICAgICAidG90YWwiOiBlbmVyZ3kgKyBjYXBpdGFsfQoKCmRlZiBleGFtcGxlMygpOgogICAgIiIiRXhhbXBsZSAzOiBib3RoIGRpYW1ldGVycyBhdCBmdWxsIHByZWNpc2lvbiwgdGhlIGFubnVhbCBzYXZpbmcKICAgIG9mIHRoZSBjaGVhcGVyIGRpYW1ldGVyLCBhbmQgdGhlIHRvdGFscyBmaWd1cmUgYXMgYSBQbG90bHkgZGljdC4iIiIKICAgIGNvc3RzID0ge2Q6IHBpcGVfY29zdChkKSBmb3IgZCBpbiAoMC4yOCwgMC4zMCl9CiAgICBzYXZpbmcgPSBjb3N0c1swLjMwXVsidG90YWwiXSAtIGNvc3RzWzAuMjhdWyJ0b3RhbCJdCiAgICBmaWcgPSB7CiAgICAgICAgImRhdGEiOiBbCiAgICAgICAgICAgIHsidHlwZSI6ICJiYXIiLCAibmFtZSI6ICJFbGVjdHJpY2l0eSIsCiAgICAgICAgICAgICAieCI6IFsiRCA9IDAuMjggbSIsICJEID0gMC4zMCBtIl0sCiAgICAgICAgICAgICAieSI6IFtjb3N0c1swLjI4XVsiZW5lcmd5Il0sIGNvc3RzWzAuMzBdWyJlbmVyZ3kiXV0sCiAgICAgICAgICAgICAibWFya2VyIjogeyJjb2xvciI6ICIjMDA3MkIyIn19LAogICAgICAgICAgICB7InR5cGUiOiAiYmFyIiwgIm5hbWUiOiAiQ2FwaXRhbCAoYW5udWFsaXNlZCkiLAogICAgICAgICAgICAgIngiOiBbIkQgPSAwLjI4IG0iLCAiRCA9IDAuMzAgbSJdLAogICAgICAgICAgICAgInkiOiBbY29zdHNbMC4yOF1bImNhcGl0YWwiXSwgY29zdHNbMC4zMF1bImNhcGl0YWwiXV0sCiAgICAgICAgICAgICAibWFya2VyIjogeyJjb2xvciI6ICIjRDU1RTAwIn19XSwKICAgICAgICAibGF5b3V0IjogewogICAgICAgICAgICAiYmFybW9kZSI6ICJzdGFjayIsCiAgICAgICAgICAgICJ5YXhpcyI6IHsidGl0bGUiOiAiQ29zdCAoZG9sbGFycy95cikiLCAicmFuZ2UiOiBbMCwgNTIwMDAwXX0sCiAgICAgICAgICAgICJtYXJnaW4iOiB7ImwiOiA2MCwgInIiOiAxMzAsICJ0IjogMTAsICJiIjogNDV9LAogICAgICAgICAgICAibGVnZW5kIjogeyJ4IjogMS4wMiwgInkiOiAxLjAsICJ4YW5jaG9yIjogImxlZnQiLAogICAgICAgICAgICAgICAgICAgICAgICJ5YW5jaG9yIjogInRvcCJ9fX0KICAgIHJldHVybiB7ImNvc3RzIjoge3N0cihkKTogY29zdHNbZF0gZm9yIGQgaW4gY29zdHN9LAogICAgICAgICAgICAic2F2aW5nIjogc2F2aW5nLCAic2Vuc2l0aXZpdHkiOiBzYXZpbmdfc2Vuc2l0aXZpdHkoKSwKICAgICAgICAgICAgImZpZyI6IGZpZ30KCgojIE9uZSBpbnB1dCBjaGFuZ2VkIGF0IGEgdGltZSBieSBhIG1vZGVzdCBhbW91bnQ6CiMgKGxhYmVsLCBrZXl3b3JkIG9mIHBpcGVfY29zdCwgY2hhbmdlZCB2YWx1ZSkuClNFTlNJVElWSVRZX0NBU0VTID0gWwogICAgKCJDb21iaW5lZCBlZmZpY2llbmN5IDAuNzQgLT4gMC43MCIsICJldGEiLCAwLjcwKSwKICAgICgiRWxlY3RyaWNpdHkgcHJpY2UgMC4xNCAtPiAwLjE1IGRvbGxhcnMgcGVyIGtXaCIsICJwcmljZSIsIDAuMTUpLAogICAgKCJSb3VnaG5lc3MgMC4wNDUgLT4gMC4wMTUgbW0iLCAiZXBzIiwgMC4wMTVlLTMpLAogICAgKCJSb3VnaG5lc3MgMC4wNDUgLT4gMC4wOTAgbW0iLCAiZXBzIiwgMC4wOTBlLTMpLApdCgoKZGVmIHNhdmluZ19zZW5zaXRpdml0eSgpOgogICAgIiIiQW5udWFsIHNhdmluZyBvZiBEID0gMC4yOCBtIG92ZXIgRCA9IDAuMzAgbSAoZG9sbGFycy95cikgd2hlbgogICAgb25lIGlucHV0IGlzIGNoYW5nZWQgYXQgYSB0aW1lIChTRU5TSVRJVklUWV9DQVNFUyk7IGEgbmVnYXRpdmUKICAgIHNhdmluZyBtZWFucyBEID0gMC4zMCBtIGlzIHRoZSBjaGVhcGVyIGRpYW1ldGVyLiIiIgogICAgcm93cyA9IFtdCiAgICBmb3IgbGFiZWwsIGtleSwgdmFsdWUgaW4gU0VOU0lUSVZJVFlfQ0FTRVM6CiAgICAgICAga3cgPSB7a2V5OiB2YWx1ZX0KICAgICAgICBzYXZpbmcgPSBwaXBlX2Nvc3QoMC4zMCwgKiprdylbInRvdGFsIl0gLSBwaXBlX2Nvc3QoMC4yOCwgKiprdylbInRvdGFsIl0KICAgICAgICByb3dzLmFwcGVuZCh7ImxhYmVsIjogbGFiZWwsICJzYXZpbmciOiBmbG9hdChzYXZpbmcpfSkKICAgIHJldHVybiByb3dzCgoKZGVmIHJvdW5kZWRfZGlmZmVyZW5jZSh1bml0KToKICAgICIiIkRpZmZlcmVuY2Ugb2YgdGhlIHR3byB0b3RhbCBhbm51YWxpc2VkIGNvc3RzIChkb2xsYXJzL3lyKSB3aGVuCiAgICBlYWNoIHRvdGFsIGlzIGZpcnN0IHJvdW5kZWQgdG8gdGhlIG5lYXJlc3QgdW5pdCAoZG9sbGFycy95ciksIGFzCiAgICB0aGUgY2hhdC1tb2RlIHJlcGx5IHJvdW5kZWQgdG8gdGhlIG5lYXJlc3QgMTAwIGRvbGxhcnMveXIuICBBbHNvCiAgICByZXR1cm5zIHRoZSB0d28gcm91bmRlZCB0b3RhbHMgYW5kIHRoZSByZWxhdGl2ZSBlcnJvciBvZiB0aGUKICAgIHJvdW5kZWQgZGlmZmVyZW5jZSBhZ2FpbnN0IHRoZSBleGFjdCBzYXZpbmcuIiIiCiAgICBjb3N0cyA9IGV4YW1wbGUzKClbImNvc3RzIl0KICAgIHQyOCA9IHJvdW5kKGNvc3RzWyIwLjI4Il1bInRvdGFsIl0gLyB1bml0KSAqIHVuaXQKICAgIHQzMCA9IHJvdW5kKGNvc3RzWyIwLjMiXVsidG90YWwiXSAvIHVuaXQpICogdW5pdAogICAgZGlmZiA9IHQzMCAtIHQyOAogICAgZXhhY3QgPSBjb3N0c1siMC4zIl1bInRvdGFsIl0gLSBjb3N0c1siMC4yOCJdWyJ0b3RhbCJdCiAgICByZXR1cm4geyJ1bml0IjogdW5pdCwgInRvdGFsXzAyOCI6IHQyOCwgInRvdGFsXzAzMCI6IHQzMCwKICAgICAgICAgICAgImRpZmZlcmVuY2UiOiBkaWZmLCAiZXhhY3QiOiBleGFjdCwKICAgICAgICAgICAgInJlbF9lcnJvciI6IChkaWZmIC0gZXhhY3QpIC8gZXhhY3R9CgoKZGVmIHJvdW5kaW5nX3N3ZWVwKCk6CiAgICAiIiJSb3VuZGVkIGRpZmZlcmVuY2UgYW5kIGl0cyByZWxhdGl2ZSBlcnJvciBmb3Igcm91bmRpbmcgdW5pdHMKICAgIGZyb20gMC4wMSB0byAxMDAwIGRvbGxhcnMveXI7IHRoZSBmaWd1cmUgcGxvdHMgdGhlIG1hZ25pdHVkZSBvZgogICAgdGhlIHJlbGF0aXZlIGVycm9yIGFnYWluc3QgdGhlIHVuaXQgb24gbG9nYXJpdGhtaWMgYXhlcy4iIiIKICAgIHVuaXRzID0gWzAuMDEsIDAuMSwgMS4wLCAxMC4wLCA1MC4wLCAxMDAuMCwgMjAwLjAsIDUwMC4wLCAxMDAwLjBdCiAgICByb3dzID0gW3JvdW5kZWRfZGlmZmVyZW5jZSh1KSBmb3IgdSBpbiB1bml0c10KICAgIGZpZyA9IHsKICAgICAgICAiZGF0YSI6IFt7InR5cGUiOiAic2NhdHRlciIsICJtb2RlIjogImxpbmVzK21hcmtlcnMiLAogICAgICAgICAgICAgICAgICAibmFtZSI6ICJFcnJvciBtYWduaXR1ZGUiLAogICAgICAgICAgICAgICAgICAieCI6IHVuaXRzLAogICAgICAgICAgICAgICAgICAieSI6IFthYnMoclsicmVsX2Vycm9yIl0pICogMTAwLjAgZm9yIHIgaW4gcm93c10sCiAgICAgICAgICAgICAgICAgICJsaW5lIjogeyJjb2xvciI6ICIjMDA3MkIyIiwgIndpZHRoIjogMn0sCiAgICAgICAgICAgICAgICAgICJtYXJrZXIiOiB7ImNvbG9yIjogIiMwMDcyQjIiLCAic2l6ZSI6IDZ9fV0sCiAgICAgICAgImxheW91dCI6IHsKICAgICAgICAgICAgInhheGlzIjogeyJ0aXRsZSI6ICJSb3VuZGluZyB1bml0IChkb2xsYXJzL3lyKSIsCiAgICAgICAgICAgICAgICAgICAgICAidHlwZSI6ICJsb2cifSwKICAgICAgICAgICAgInlheGlzIjogeyJ0aXRsZSI6ICJFcnJvciBpbiB0aGUgZGlmZmVyZW5jZSAoJSkiLAogICAgICAgICAgICAgICAgICAgICAgInR5cGUiOiAibG9nIn0sCiAgICAgICAgICAgICJtYXJnaW4iOiB7ImwiOiA2MCwgInIiOiAxMTAsICJ0IjogMTAsICJiIjogNDV9LAogICAgICAgICAgICAibGVnZW5kIjogeyJ4IjogMS4wMiwgInkiOiAxLjAsICJ4YW5jaG9yIjogImxlZnQiLAogICAgICAgICAgICAgICAgICAgICAgICJ5YW5jaG9yIjogInRvcCJ9fX0KICAgIHJldHVybiB7InJvd3MiOiByb3dzLCAiZmlnIjogZmlnfQoKCiMgLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tCiMgRXhhbXBsZSA0OiBsb29wZWQgd2F0ZXIgZGlzdHJpYnV0aW9uIG5ldHdvcmsuICBXYXRlciBwcm9wZXJ0aWVzIGFzCiMgaW4gRXhhbXBsZSAzLiAgSW5mbG93IGF0IG5vZGUgQSBpcyAwLjMwMCBtXjMvczsgZGVtYW5kcyAob3V0Zmxvd3MpIGluCiMgbV4zL3MgYXJlIEIgMC4wNTAsIEMgMC4wODAsIEQgMC4wNzAsIEUgMC4wNTAsIEYgMC4wNTAuICBQaXBlIGxlbmd0aHMKIyBMIChtKSBhbmQgaW5zaWRlIGRpYW1ldGVycyBEIChtKSBhcmUgaW4gUElQRVM7IHRoZSBzaWduIGNvbnZlbnRpb24KIyB0YWtlcyB0aGUgbmFtZWQgZGlyZWN0aW9uIChBLT5CLCBCLT5DLCAuLi4pIGFzIHBvc2l0aXZlLgojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQpHID0gOS44MSAgIyBtL3NeMiwgZ3Jhdml0YXRpb25hbCBhY2NlbGVyYXRpb24KUElQRVMgPSB7IkFCIjogKDI0MC4wLCAwLjMwKSwgIkJDIjogKDE4MC4wLCAwLjI1KSwgIkNEIjogKDIyMC4wLCAwLjI4KSwKICAgICAgICAgIkRBIjogKDI2MC4wLCAwLjMwKSwgIkNFIjogKDE1MC4wLCAwLjIwKSwgIkVGIjogKDE3MC4wLCAwLjIwKSwKICAgICAgICAgIkZEIjogKDE5MC4wLCAwLjIyKX0gICMgbmFtZTogKEwgaW4gbSwgRCBpbiBtKQpIRUFEX0EgPSA0Mi4wICAjIG0sIHRvdGFsIGhlYWQgYXQgbm9kZSBBCgoKZGVmIF9oZWFkX2xvc3MocSwgbmFtZSk6CiAgICAiIiJTaWduZWQgaGVhZCBsb3NzIChtKSBpbiBwaXBlIG5hbWUgYXQgc2lnbmVkIGZsb3cgcSAobV4zL3MpLAogICAgcG9zaXRpdmUgd2hlbiB0aGUgbG9zcyBhY3RzIGluIHRoZSBuYW1lZCBkaXJlY3Rpb24uIiIiCiAgICBsZW5ndGgsIGRpYW1ldGVyID0gUElQRVNbbmFtZV0KICAgIGlmIGFicyhxKSA8IDFlLTEyOgogICAgICAgIHJldHVybiAwLjAKICAgIGFyZWEgPSBucC5waSAqIGRpYW1ldGVyICoqIDIgLyA0LjAKICAgIHYgPSBxIC8gYXJlYQogICAgcmV5bm9sZHMgPSBSSE8gKiBhYnModikgKiBkaWFtZXRlciAvIE1VCiAgICBmID0gY29sZWJyb29rX2YocmV5bm9sZHMsIEVQUywgZGlhbWV0ZXIpCiAgICByZXR1cm4gZiAqIChsZW5ndGggLyBkaWFtZXRlcikgKiB2ICogYWJzKHYpIC8gKDIuMCAqIEcpCgoKTE9PUDEgPSBbIkFCIiwgIkJDIiwgIkNEIiwgIkRBIl0KTE9PUDIgPSBbIkNFIiwgIkVGIiwgIkZEIl0gICMgY2xvc2VkIHRocm91Z2ggQ0QsIHRyYXZlcnNlZCBiYWNrd2FyZHMKCgpkZWYgbG9vcF9yZXNpZHVhbHMocSk6CiAgICAiIiJIZWFkLWxvc3Mgc3VtcyAobSkgYXJvdW5kIHRoZSB0d28gbG9vcHMgZm9yIHNpZ25lZCBwaXBlIGZsb3dzIHEKICAgIChtXjMvcyk7IGJvdGggYXJlIHplcm8gZm9yIGEgc29sdXRpb24gb2YgdGhlIG5ldHdvcmsuIiIiCiAgICBlMSA9IHN1bShfaGVhZF9sb3NzKHFbbmFtZV0sIG5hbWUpIGZvciBuYW1lIGluIExPT1AxKQogICAgZTIgPSAoc3VtKF9oZWFkX2xvc3MocVtuYW1lXSwgbmFtZSkgZm9yIG5hbWUgaW4gTE9PUDIpCiAgICAgICAgICAtIF9oZWFkX2xvc3MocVsiQ0QiXSwgIkNEIikpCiAgICByZXR1cm4gW2Zsb2F0KGUxKSwgZmxvYXQoZTIpXQoKCmRlZiBzb2x2ZV9uZXR3b3JrKCk6CiAgICAiIiJTb2x2ZSB0aGUgdHdvIGxvb3AgZXF1YXRpb25zIG9mIHRoZSBuZXR3b3JrIGJ5IGEgTmV3dG9uLXR5cGUKICAgIG1ldGhvZCAoc2NpcHkub3B0aW1pemUuZnNvbHZlKSBvbiB0d28gbG9vcC1mbG93IGNvcnJlY3Rpb25zLgogICAgUmV0dXJucyB0aGUgc2lnbmVkIHBpcGUgZmxvd3MgKG1eMy9zKSwgdGhlIHRvdGFsIGhlYWRzIChtKSBhdCBhbGwKICAgIG5vZGVzLCB0aGUgdHdvIGxvb3AgcmVzaWR1YWxzIChtKSwgYW5kIHRoZSBub2RlLUUgYmFsYW5jZSB0ZXJtczoKICAgIHRoZSBDRSBpbmZsb3cgKG1eMy9zKSwgdGhlIEUgZGVtYW5kIChtXjMvcykgYW5kIHRoZWlyIGRpZmZlcmVuY2UsCiAgICB3aGljaCBpcyB0aGUgRUYgZmxvdy4iIiIKICAgIGJhc2UgPSB7IkFCIjogMC4yOCwgIkJDIjogMC4yMywgIkNEIjogMC4wNSwgIkRBIjogLTAuMDIsCiAgICAgICAgICAgICJDRSI6IDAuMTAsICJFRiI6IDAuMDUsICJGRCI6IDAuMH0gICMgbV4zL3MsIHNhdGlzZmllcyBjb250aW51aXR5CiAgICBkZWYgZmxvd3MoeHkpOgogICAgICAgIHgsIHkgPSB4eQogICAgICAgIHEgPSBkaWN0KGJhc2UpCiAgICAgICAgZm9yIG5hbWUgaW4gTE9PUDE6CiAgICAgICAgICAgIHFbbmFtZV0gKz0geAogICAgICAgIHFbIkNEIl0gLT0geQogICAgICAgIGZvciBuYW1lIGluIExPT1AyOgogICAgICAgICAgICBxW25hbWVdICs9IHkKICAgICAgICByZXR1cm4gcQoKICAgIHEgPSBmbG93cyhmc29sdmUobGFtYmRhIHh5OiBsb29wX3Jlc2lkdWFscyhmbG93cyh4eSkpLCBbMC4wLCAwLjBdLAogICAgICAgICAgICAgICAgICAgICB4dG9sPTFlLTEzKSkKICAgIGhlYWRzID0geyJBIjogSEVBRF9BfQogICAgaGVhZHNbIkIiXSA9IEhFQURfQSAtIF9oZWFkX2xvc3MocVsiQUIiXSwgIkFCIikKICAgIGhlYWRzWyJDIl0gPSBoZWFkc1siQiJdIC0gX2hlYWRfbG9zcyhxWyJCQyJdLCAiQkMiKQogICAgaGVhZHNbIkQiXSA9IGhlYWRzWyJDIl0gLSBfaGVhZF9sb3NzKHFbIkNEIl0sICJDRCIpCiAgICBoZWFkc1siRSJdID0gaGVhZHNbIkMiXSAtIF9oZWFkX2xvc3MocVsiQ0UiXSwgIkNFIikKICAgIGhlYWRzWyJGIl0gPSBoZWFkc1siRSJdIC0gX2hlYWRfbG9zcyhxWyJFRiJdLCAiRUYiKQogICAgcmV0dXJuIHsiZmxvd3MiOiB7azogZmxvYXQodikgZm9yIGssIHYgaW4gcS5pdGVtcygpfSwKICAgICAgICAgICAgImhlYWRzIjoge2s6IGZsb2F0KHYpIGZvciBrLCB2IGluIGhlYWRzLml0ZW1zKCl9LAogICAgICAgICAgICAibG9vcF9yZXNpZHVhbHMiOiBsb29wX3Jlc2lkdWFscyhxKSwKICAgICAgICAgICAgIm5vZGVfZSI6IHsiY2VfaW5mbG93IjogZmxvYXQocVsiQ0UiXSksICJkZW1hbmQiOiAwLjA1MCwKICAgICAgICAgICAgICAgICAgICAgICAiZWZfZmxvdyI6IGZsb2F0KHFbIkVGIl0pfX0KCgpkZWYgZXhhbXBsZTQoKToKICAgICIiIkV4YW1wbGUgNDogbmV0d29yayBzb2x1dGlvbiBhbmQgdGhlIGZsb3dzIGZpZ3VyZSAoY29tcHV0ZWQKICAgIGZsb3dzIGJlc2lkZSB0aGUgcmVjb3JkZWQgY2hhdC1tb2RlIGZsb3dzKSBhcyBhIFBsb3RseSBkaWN0LiIiIgogICAgciA9IHNvbHZlX25ldHdvcmsoKQogICAgIyBUaGUgcmVjb3JkZWQgY2hhdC1tb2RlIGZsb3dzIHN1YnN0aXR1dGVkIGludG8gdGhlIHNhbWUgbG9vcAogICAgIyBlcXVhdGlvbnM6IHRoZSBjaGVjayBhIHJlYWRlciBjYW4gYXBwbHkgdG8gYSBjaGF0IGFuc3dlciwgd2hpY2gKICAgICMgaXMgaXRzZWxmIGEgY2FsY3VsYXRpb24gdG8gYmUgZXhlY3V0ZWQuCiAgICByWyJjaGF0X2xvb3BfcmVzaWR1YWxzIl0gPSBsb29wX3Jlc2lkdWFscyhDSEFUXzQpCiAgICBuYW1lcyA9IFsiQUIiLCAiQkMiLCAiQ0QiLCAiREEiLCAiQ0UiLCAiRUYiLCAiRkQiXQogICAgZmlnID0gewogICAgICAgICJkYXRhIjogWwogICAgICAgICAgICB7InR5cGUiOiAiYmFyIiwgIm5hbWUiOiAiQ2hhdCBtb2RlIiwKICAgICAgICAgICAgICJ4IjogbmFtZXMsICJ5IjogW0NIQVRfNFtubV0gZm9yIG5tIGluIG5hbWVzXSwKICAgICAgICAgICAgICJtYXJrZXIiOiB7ImNvbG9yIjogIiM5OTk5OTkifX0sCiAgICAgICAgICAgIHsidHlwZSI6ICJiYXIiLCAibmFtZSI6ICJDb21wdXRlZCIsCiAgICAgICAgICAgICAieCI6IG5hbWVzLCAieSI6IFtyWyJmbG93cyJdW25tXSBmb3Igbm0gaW4gbmFtZXNdLAogICAgICAgICAgICAgIm1hcmtlciI6IHsiY29sb3IiOiAiIzAwNzJCMiJ9fV0sCiAgICAgICAgImxheW91dCI6IHsKICAgICAgICAgICAgImJhcm1vZGUiOiAiZ3JvdXAiLAogICAgICAgICAgICAieWF4aXMiOiB7InRpdGxlIjogIkZsb3cgKG1eMy9zKSJ9LAogICAgICAgICAgICAibWFyZ2luIjogeyJsIjogNTUsICJyIjogMTEwLCAidCI6IDEwLCAiYiI6IDQ1fSwKICAgICAgICAgICAgImxlZ2VuZCI6IHsieCI6IDEuMDIsICJ5IjogMS4wLCAieGFuY2hvciI6ICJsZWZ0IiwKICAgICAgICAgICAgICAgICAgICAgICAieWFuY2hvciI6ICJ0b3AifX19CiAgICByWyJmaWciXSA9IGZpZwogICAgcmV0dXJuIHIKCgpkZWYgcGxhaW4ob2JqKToKICAgICIiIkNvbnZlcnQgbnVtcHkgdmFsdWVzIGluIG5lc3RlZCBkaWN0cywgbGlzdHMgYW5kIHR1cGxlcyB0byBwbGFpbgogICAgUHl0aG9uIGRhdGEgc3VpdGFibGUgZm9yIGpzb24uZHVtcHMuIiIiCiAgICBpZiBpc2luc3RhbmNlKG9iaiwgZGljdCk6CiAgICAgICAgcmV0dXJuIHtrOiBwbGFpbih2KSBmb3IgaywgdiBpbiBvYmouaXRlbXMoKX0KICAgIGlmIGlzaW5zdGFuY2Uob2JqLCAobGlzdCwgdHVwbGUpKToKICAgICAgICByZXR1cm4gW3BsYWluKHYpIGZvciB2IGluIG9ial0KICAgIGlmIGlzaW5zdGFuY2Uob2JqLCAobnAuZmxvYXRpbmcsIG5wLmludGVnZXIpKToKICAgICAgICByZXR1cm4gb2JqLml0ZW0oKQogICAgaWYgaXNpbnN0YW5jZShvYmosIGZsb2F0KSBhbmQgKG5wLmlzbmFuKG9iaikgb3IgbnAuaXNpbmYob2JqKSk6CiAgICAgICAgcmV0dXJuIE5vbmUKICAgIHJldHVybiBvYmoK").decode("utf-8")
    _mod = _types.ModuleType('chatagent')
    exec(compile(MODULE_SRC, 'chatagent', 'exec'), _mod.__dict__)
    _sys.modules['chatagent'] = _mod
    M = _mod
    def figure(data, layout=None, **kw):
        return go.Figure(data=data, layout=layout or kw)
    return (mo, np, go, M, MODULE_SRC, figure)


@app.cell
def _(mo):
    mo.md(r"""
    # Chat Mode and Agent Mode in Numerical Calculation

    An editable breakdown of the four quantities that a frontier model reported with material error in chat mode, recomputed here by program execution: two standard errors and a root-mean-square error from kinetic fits, an annual saving from a pipe cost comparison, and one flow in a looped pipe network. Edit a value in a cell and re-run; every downstream cell recomputes. Concentrations are in mol/L, times in min, flows in m^3/s, and costs in dollars/yr.
    """)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 1: The four recorded failures

    Two modes of obtaining a number from a language model are compared. In chat mode, the answer is generated as text, token by token, and no program is executed at any point. In agent mode, the model writes a program, the program is executed, and the answer is read from the execution. On 24 October 2026, 26 undergraduate chemical-engineering problems were given to a frontier model (Muse Spark 1.3) under both modes. A requested quantity was classed as materially in error when its relative error exceeded 2 percent, when an integer result was wrong, when a stated uncertainty quantity was in error by more than 50 percent, or when a finite answer was returned for an infeasible specification. Twenty-two problems were solved correctly in full in chat mode. Four contained a materially wrong quantity. This walkthrough recomputes the four failed quantities by execution and places each beside the recorded chat-mode answer.
    """)


@app.cell
def _(M):
    print("Example 1 (kinetics, 41 points): chat SE of n =", M.CHAT_1["se_n"],
          "; chat SE of k =", M.CHAT_1["se_k"])
    print("Example 2 (kinetics, 25 points): chat RMSE =", M.CHAT_2["rmse"],
          "mol/L")
    print("Example 3 (pipe diameters): chat annual saving =",
          M.CHAT_3["saving"], "dollars/yr")
    print("Example 4 (looped network): chat flow in pipe EF =",
          M.CHAT_4["EF"], "m^3/s")


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 2: Example 1: least-squares fit of 41 points

    A batch reactor experiment for the reaction A $\rightarrow$ products records the concentration of A, $C_A$ in mol/L, at time $t$ in min, at 41 times from 0 to 200 min. The rate law is $-\mathrm{d}C_A/\mathrm{d}t = k C_A^{\,n}$, where $k$ is the rate constant, in $(\mathrm{mol/L})^{1-n}\,\mathrm{min}^{-1}$, and $n$ is the reaction order, dimensionless. With initial concentration $C_{A0} = 1.80$ mol/L, the integrated rate law is

    $$C_A(t) = \left( C_{A0}^{\,1-n} + (n-1)\,k\,t \right)^{1/(1-n)}$$

    Both parameters are determined by nonlinear least-squares fitting of all 41 points, minimising the sum of squared residuals between the measured and modelled concentrations. The fit is executed, not estimated: an iterative solver adjusts $k$ and $n$ until the sum of squared residuals is stationary.
    """)


@app.cell
def _(M, figure):
    ex1 = M.example1()
    print("fitted k =", round(ex1["k"], 6), "(mol/L)^(1-n) min^-1")
    print("fitted n =", round(ex1["n"], 5))
    print("chat mode reported k = 0.038 and n = 1.80: acceptable point estimates")
    figure(ex1["fig"]["data"], **ex1["fig"]["layout"])


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 3: Example 1: origin of the standard errors

    The standard error of a fitted parameter measures the precision the data support for that parameter. For a least-squares fit with $N$ points and $p$ parameters, the covariance matrix of the parameters is $s^2 (\mathbf{J}^{\mathsf{T}} \mathbf{J})^{-1}$, where $\mathbf{J}$ is the Jacobian matrix of the model predictions with respect to the parameters, evaluated at all $N$ points, and $s^2$ is the residual variance, the residual sum of squares $\mathrm{SSE}$ divided by $N - p$. The standard error of each parameter is the square root of the corresponding diagonal entry. Every entry of $\mathbf{J}^{\mathsf{T}} \mathbf{J}$ is a sum over all 41 points, and the inverse mixes the two parameters, which are correlated (correlation coefficient 0.51 in this fit). No inspection of the residual scatter yields these numbers; the accumulation either is performed or is not. The chat-mode reply stated that the scatter of the residuals was propagated by judgement, and reported standard errors of 0.03 for $n$ and 0.002 for $k$.
    """)


@app.cell
def _(M, ex1):
    _s2 = ex1["sse"] / (ex1["n_points"] - 2)
    print("SSE =", round(ex1["sse"], 5), "(mol/L)^2 over", ex1["n_points"],
          "points; s^2 =", format(_s2, ".3e"))
    print("computed SE of n =", round(ex1["se_n"], 5),
          "; chat mode reported", M.CHAT_1["se_n"],
          "(factor", round(M.CHAT_1["se_n"] / ex1["se_n"], 1), "too large)")
    print("computed SE of k =", round(ex1["se_k"], 6),
          "; chat mode reported", M.CHAT_1["se_k"],
          "(factor", round(M.CHAT_1["se_k"] / ex1["se_k"], 1), "too large)")
    print("parameter correlation coefficient =", round(ex1["corr_kn"], 2))


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 4: Example 2: the root-mean-square error as an accumulation

    The same experiment at pilot scale gives 25 points over 120 min. The root-mean-square error of a fit, $\mathrm{RMSE} = \sqrt{\mathrm{SSE}/N}$ in mol/L, is the quality figure of the fit itself. It is a sum of squared residuals over every point, divided by the number of points $N$ and square-rooted. The chat-mode reply reported fitted parameters of acceptable accuracy ($n$ in error by 1.3 percent, $k$ by 1.9 percent) and a root-mean-square error of 0.013 mol/L. The value below is accumulated from the 25 residuals of the executed fit.
    """)


@app.cell
def _(M, figure):
    ex2 = M.example2()
    print("SSE =", round(ex2["sse"], 5), "(mol/L)^2 over", ex2["n_points"],
          "points")
    print("computed RMSE = sqrt(SSE/N) =", round(ex2["rmse"], 5), "mol/L")
    print("chat mode reported", M.CHAT_2["rmse"], "mol/L (",
          round(100 * (M.CHAT_2["rmse"] / ex2["rmse"] - 1)), "percent too large)")
    figure(ex2["fig"]["data"], **ex2["fig"]["layout"])


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 5: Example 3: annualised costs at full precision

    Water at 20 °C (density $\rho = 998$ kg/m$^3$, dynamic viscosity $\mu = 1.002 \times 10^{-3}$ Pa·s) is pumped at flow rate $Q = 0.110$ m$^3$/s through a horizontal line of length $L = 9000$ m. Two inside diameters are compared, $D = 0.28$ m and $D = 0.30$ m, both with absolute roughness $\varepsilon = 0.045$ mm. The Darcy friction factor $f$, dimensionless, follows the Colebrook equation in the Reynolds number $\mathrm{Re} = \rho v D / \mu$, where $v$ is the mean velocity in m/s; the pressure drop is $\Delta P = f (L/D)\, \rho v^2 / 2$ in Pa. Pumping power follows from $Q \Delta P$ divided by the combined efficiency 0.74; electricity costs 0.14 dollars per kWh over 8200 h per year. The installed cost is $2275\, D^{1.55}$ dollars per metre, annualised by the capital recovery factor 0.12 per year. The executed calculation carries full precision through every step.
    """)


@app.cell
def _(M, figure):
    ex3 = M.example3()
    for _d in ("0.28", "0.3"):
        _c = ex3["costs"][_d]
        print("D =", _d, "m: pressure drop", round(_c["dp_kpa"], 2), "kPa,",
              "power", round(_c["power_kw"], 3), "kW,",
              "electricity", round(_c["energy"], 2), "dollars/yr,",
              "capital", round(_c["capital"], 2), "dollars/yr,",
              "total", round(_c["total"], 2), "dollars/yr")
    print("annual saving of D = 0.28 m =", round(ex3["saving"], 2),
          "dollars/yr; chat mode reported approximately",
          M.CHAT_3["saving"], "dollars/yr")
    figure(ex3["fig"]["data"], **ex3["fig"]["layout"])


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 6: Example 3: rounding before differencing

    The saving is the difference of two totals of about 473,000 dollars/yr and is itself 0.034 percent of either total. A difference of near-equal quantities inherits the absolute error of its terms, not their relative error: rounding each total to the nearest $u$ dollars/yr admits an absolute error of up to $u$ in the difference, which is a relative error of up to $u / 161.08$ in the saving. The sweep below rounds the two executed totals at units from 0.01 to 1000 dollars/yr and differences the rounded values. At the chat-mode rounding unit of 100 dollars/yr, the difference of the rounded executed totals is 200 dollars/yr, an error of 24 percent; the chat-mode reply stated approximately 140 dollars/yr, which matches neither the exact saving nor the difference of its own stated totals (473,300 $-$ 473,200 $=$ 100 dollars/yr).

    The same amplification applies to the inputs. The last lines below change one input at a time by a modest amount and recompute the saving: it changes by thousands of dollars per year, and in three of the four cases $D = 0.30$ m becomes the cheaper diameter. The saving at the stated inputs is a test of arithmetic; for the design decision, the two diameters cost the same within the accuracy of the inputs.
    """)


@app.cell
def _(M, figure):
    sweep = M.rounding_sweep()
    for _r in sweep["rows"]:
        print("unit", format(_r["unit"], "7.2f"), "dollars/yr: rounded totals",
              format(_r["total_028"], ",.0f"), "and",
              format(_r["total_030"], ",.0f"), "; difference",
              format(_r["difference"], ",.0f"), "dollars/yr; error",
              format(100 * _r["rel_error"], "+.1f"), "percent")
    for _r in M.saving_sensitivity():
        print(_r["label"], ": saving of D = 0.28 m =",
              format(_r["saving"], ",.2f"), "dollars/yr")
    figure(sweep["fig"]["data"], **sweep["fig"]["layout"])


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 7: Example 4: solution of the looped network

    Water (properties as in Example 3) enters a looped pipe network at node A at 0.300 m$^3$/s. Demands (outflows) in m$^3$/s are: B 0.050, C 0.080, D 0.070, E 0.050, F 0.050. The pipes, with the flow direction taken as positive in each case, are A$\rightarrow$B (length 240 m, diameter 0.30 m), B$\rightarrow$C (180 m, 0.25 m), C$\rightarrow$D (220 m, 0.28 m), D$\rightarrow$A (260 m, 0.30 m), C$\rightarrow$E (150 m, 0.20 m), E$\rightarrow$F (170 m, 0.20 m), F$\rightarrow$D (190 m, 0.22 m), all with absolute roughness $\varepsilon = 0.045$ mm. The head loss in a pipe is $h = f (L/D)\, v^2 / (2g)$, with $g = 9.81$ m/s$^2$ and $f$ from the Colebrook equation. Continuity at the nodes reduces the seven unknown flows to two loop corrections; the two loop equations (the signed head losses around each loop sum to zero) are solved by a Newton-type method. The loop residuals, printed below, are the verification. The same equations evaluated at the chat-mode flows leave a residual of about 0.08 m in the loop through CE, EF and FD: checking a chat answer this way is cheaper than solving the network, but it is still a calculation that has to be executed.
    """)


@app.cell
def _(M, figure):
    ex4 = M.example4()
    for _nm in ("AB", "BC", "CD", "DA", "CE", "EF", "FD"):
        print("pipe", _nm, ": computed flow", format(ex4["flows"][_nm], "+.5f"),
              "m^3/s; chat mode", format(M.CHAT_4[_nm], "+.3f"), "m^3/s")
    print("total head at D =", round(ex4["heads"]["D"], 3), "m; at F =",
          round(ex4["heads"]["F"], 3), "m")
    print("loop residuals (m):", [format(v, ".1e") for v in
          ex4["loop_residuals"]])
    print("loop residuals of the chat-mode flows (m):",
          [format(v, "+.4f") for v in ex4["chat_loop_residuals"]])
    figure(ex4["fig"]["data"], **ex4["fig"]["layout"])


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 8: Example 4: the remainder at node E

    Node E receives flow only from pipe CE and discharges its demand of 0.050 m$^3$/s and the flow in pipe EF. Continuity at node E therefore fixes the EF flow as a difference: $Q_{EF} = Q_{CE} - 0.050$ m$^3$/s. With $Q_{CE} = 0.04437$ m$^3$/s, the EF flow is $-0.00563$ m$^3$/s, the negative sign denoting flow from F toward E. The chat-mode Hardy–Cross iteration was accurate in absolute terms everywhere, and its node balance at E is exact ($-0.005 = 0.045 - 0.050$). Its error is in the CE flow, 0.045 against 0.04437 m$^3$/s (1.4 percent, within the 2 percent criterion); the same absolute error of 0.00063 m$^3$/s is 11 percent of the EF remainder. A quantity defined as the difference of two near-equal quantities inherits the absolute error of its parents, not their relative error — the same structure as the annual saving of Example 3, at the scale of a single node.
    """)


@app.cell
def _(M, ex4):
    node_e = ex4["node_e"]
    print("CE inflow to node E =", round(node_e["ce_inflow"], 5), "m^3/s")
    print("E demand =", node_e["demand"], "m^3/s")
    print("EF flow = difference =", round(node_e["ef_flow"], 5), "m^3/s")
    _err = abs(M.CHAT_4["EF"] - node_e["ef_flow"])
    print("chat mode reported", M.CHAT_4["EF"], "m^3/s: absolute error",
          round(_err, 5), "m^3/s, relative error",
          round(100 * _err / abs(node_e["ef_flow"])), "percent")


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 9: Anchor values and verification

    The executed values are asserted against the independently verified record of the screening (each agent-mode result was verified by a second solver, an analytic identity, or a residual evaluation before the record was fixed). A failed assertion in this cell indicates drift between this walkthrough and the record. The four chat-mode failures share one structure: each failed quantity is an accumulation over all terms of a sum, a difference of near-equal quantities, or a remainder of near-cancelling quantities — and a stated uncertainty, which is an accumulation by definition. Quantities reached by iteration were accurate in chat mode throughout the screening; precision was lost at the points where exact accumulation or exact subtraction was the whole of the calculation. Chat mode solved 22 of the 26 problems correctly, but a reply does not mark which of its numbers are wrong, and checking them requires execution: for numerical work, chat mode is still not as good as agent mode.
    """)


@app.cell
def _(ex1, ex2, ex3, ex4):
    assert abs(ex1["se_n"] - 0.0104) < 2e-4
    assert abs(ex1["se_k"] - 0.000217) < 3e-6
    assert abs(ex2["rmse"] - 0.009345) < 2e-5
    assert abs(ex3["saving"] - 161.08) < 0.05
    assert abs(ex4["flows"]["EF"] - (-0.00563)) < 3e-5
    assert max(abs(v) for v in ex4["loop_residuals"]) < 1e-10
    print("all anchor values reproduced: standard errors, root-mean-square",
          "error, annual saving, EF flow, loop residuals")


if __name__ == "__main__":
    app.run()
