# /// script
# requires-python = ">=3.10"
# dependencies = ["marimo", "numpy", "plotly"]
# ///
"""Editable MoLab notebook generated from walkthrough.py CELLS.

Do not edit by hand; regenerate with make_molab.py.
"""
import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")

@app.cell
def _():
    import marimo as mo
    import numpy as np, base64
    import plotly.graph_objects as go
    import sys as _sys, types as _types
    MODEL_SRC = base64.b64decode("IiIiUmVmZXJlbmNlIG1vZGVsIGZvciB0aGUgamFja2V0ZWQtQ1NUUiBkaWdpdGFsLXR3aW4gZGVtby4KClR3byBzdHJpY3RseSBzZXBhcmF0ZWQgcGFydHM6CgpQTEFOVCAtLSB0aGUgInJlYWwiIHByb2Nlc3MuIE93bnMgdGhlIGhpZGRlbiB0cnVlIHBhcmFtZXRlcnMuIFB1Ymxpc2hlcyBhCnNlbnNvciBkYXRhIHN0cmVhbSAoVCwgVF9qLCBGLCBUMCBldmVyeSBkdF9wdWIgc2Vjb25kcyB3aXRoIG5vaXNlOyBDX0EgYXMKb2NjYXNpb25hbCBkZWxheWVkIGxhYiBzYW1wbGVzKS4gTm90aGluZyBvdXRzaWRlIHRoaXMgbW9kdWxlIG1heSByZWFkIHRoZQpwbGFudCdzIGludGVybmFsIHN0YXRlIG9yIHBhcmFtZXRlcnM7IHRoZSB0d2luIHJlY2VpdmVzIG9ubHkgdGhlIHN0cmVhbS4KClRXSU4gLS0gYW4gZXh0ZW5kZWQgS2FsbWFuIGZpbHRlciB3aXRoIGF1Z21lbnRlZCBzdGF0ZSBbQ19BLCBULCBUX2osIFVBXS4KSXQga25vd3MgdGhlIG1vZGVsIHN0cnVjdHVyZSwgdGhlIG5vbWluYWwgKHdyb25nKSBwYXJhbWV0ZXJzLCBhbmQgdGhlCnB1Ymxpc2hlZCBjb250cm9sbGVyIHNldHRpbmdzLiBJdCBuZXZlciBzZWVzIHRoZSBwbGFudCdzIHRydWUgcGFyYW1ldGVycy4KIiIiCgppbXBvcnQgbWF0aAoKaW1wb3J0IG51bXB5IGFzIG5wCgojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQojIFBMQU5UOiBoaWRkZW4gdHJ1ZSBwYXJhbWV0ZXJzIChuZXZlciB2aXNpYmxlIHRvIHRoZSB0d2luKQojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQpQTEFOVF9QID0gZGljdCgKICAgIFY9MS4wLCAgICAgICAgICAgICMgTCwgcmVhY3RvciB2b2x1bWUKICAgIEY9MS4wIC8gNjAwLjAsICAgICMgTC9zLCBmZWVkIGZsb3cKICAgIENfQTA9OC4wLCAgICAgICAgICMgbW9sL0wsIGZlZWQgY29uY2VudHJhdGlvbgogICAgVDA9MzAwLjAsICAgICAgICAgIyBLLCBmZWVkIHRlbXBlcmF0dXJlCiAgICBrMD0zLjBlNywgICAgICAgICAjIDEvcywgQXJyaGVuaXVzIHByZS1leHBvbmVudGlhbCAoaGlkZGVuKQogICAgRWFSPTgwMDAuMCwgICAgICAgIyBLLCBFX2EgLyBSIChoaWRkZW4pCiAgICBkSG5lZz04LjBlNCwgICAgICAjIEovbW9sLCAtRGVsdGFICiAgICByaG9DcD00MDAwLjAsICAgICAjIEovKEwgSyksIHByb2Nlc3Mtc2lkZSB2b2x1bWV0cmljIGhlYXQgY2FwYWNpdHkKICAgIHJob0NwX2o9NDAwMC4wLCAgICMgSi8oTCBLKSwgamFja2V0LXNpZGUgdm9sdW1ldHJpYyBoZWF0IGNhcGFjaXR5CiAgICBWaj0wLjIsICAgICAgICAgICAjIEwsIGphY2tldCB2b2x1bWUKICAgIFRqaW49MzAwLjAsICAgICAgICMgSywgY29vbGFudCBpbmxldCB0ZW1wZXJhdHVyZQogICAgVUEwPTE2LjAsICAgICAgICAgIyBKLyhzIEspLCBjbGVhbiBvdmVyYWxsIGNvZWZmaWNpZW50OyBmb3VscyBkb3dud2FyZAogICAgdGF1X2ZvdWw9Ni4wICogMzYwMC4wLCAgIyBzLCBmb3VsaW5nIHRpbWUgY29uc3RhbnQKKQoKIyBQdWJsaXNoZWQgY29udHJvbGxlciBzZXR0aW5ncyAoa25vd24gdG8gdGhlIHR3aW47IHBhcnQgb2YgcGxhbnQgZG9jdW1lbnRhdGlvbikKQ1RSTCA9IGRpY3QoCiAgICBUX3NwPTM3MC4wLCAgICAgICAjIEssIHRlbXBlcmF0dXJlIHNldHBvaW50CiAgICBGal9taW49MC4wMDA1LCAgICAjIEwvcwogICAgRmpfbWF4PTAuMDA4LCAgICAgIyBML3MKICAgIEZqX2JpYXM9MC4wMDMsICAgICMgTC9zCiAgICBLYz0xLjBlLTQsICAgICAgICAjIEwvKHMgSyksIHByb3BvcnRpb25hbCBnYWluIChyZXZlcnNlLWFjdGluZykKICAgIHRhdUk9MzAwLjAsICAgICAgICMgcywgaW50ZWdyYWwgdGltZQopCgojIFR3aW4ncyBub21pbmFsICh3cm9uZyBidXQgcmVhc29uYWJsZSkgcGFyYW1ldGVycwpUV0lOX1AgPSBkaWN0KAogICAgazA9Mi44NWU3LCAgICAgICAgIyAtNSUgdnMgdHJ1dGgKICAgIEVhUj03OTYwLjAsICAgICAgICMgLTAuNSUgdnMgdHJ1dGgKICAgIGRIbmVnPTcuODRlNCwgICAgICMgLTIlIHZzIHRydXRoCiAgICByaG9DcD00MDAwLjAsCiAgICByaG9DcF9qPTQwMDAuMCwKICAgIFY9MS4wLAogICAgVmo9MC4yLAogICAgQ19BMD04LjAsICAgICAgICAgIyBwdWJsaXNoZWQgZmVlZCBjb25jZW50cmF0aW9uCiAgICBUamluPTMwMC4wLCAgICAgICAjIHB1Ymxpc2hlZCBjb29sYW50IGlubGV0IHRlbXBlcmF0dXJlCiAgICBVQV9pbml0PTE2LjAsICAgICAjIGNsZWFuIHZhbHVlIGFzc3VtZWQga25vd247IGZvdWxpbmcgcmF0ZSB1bmtub3duCikKCgpkZWYga19vZl9UKFQsIGswLCBFYVIpOgogICAgcmV0dXJuIGswICogbnAuZXhwKG5wLmNsaXAoLUVhUiAvIG5wLm1heGltdW0oVCwgMS4wKSwgLTcwMC4wLCAwLjApKQoKCmRlZiBfc29sdmVfaXZwKGZ1biwgdF9zcGFuLCB5MCwgcnRvbD0xZS02LCBhdG9sPTFlLTkpOgogICAgIiIiQWRhcHRpdmUgZXhwbGljaXQgUnVuZ2UtS3V0dGEgT0RFIHNvbHZlciwgc29sdmVfaXZwLWxpa2UgaW50ZXJmYWNlLgoKICAgIGZ1bih0LCB5KSB0YWtlcyBhIHNlcXVlbmNlIG9mIGZsb2F0cyBhbmQgcmV0dXJucyBhIHNlcXVlbmNlIG9mCiAgICBkZXJpdmF0aXZlcy4gUmV0dXJucyBhIG5hbWVzcGFjZSB3aXRoIC50IGFuZCAueSBzaGFwZWQgKG4sIDIpIChpbml0aWFsCiAgICBhbmQgZmluYWwgc3RhdGVzKSwgc28gY2FsbCBzaXRlcyBrZWVwIHJlYWRpbmcgc29sLnlbOiwgLTFdLgogICAgSW50ZXJuYWwgdXNlIG9ubHkuCiAgICAiIiIKICAgIGZyb20gdHlwZXMgaW1wb3J0IFNpbXBsZU5hbWVzcGFjZQogICAgdDAsIHQxID0gZmxvYXQodF9zcGFuWzBdKSwgZmxvYXQodF9zcGFuWzFdKQogICAgeSA9IFtmbG9hdCh2KSBmb3IgdiBpbiB5MF0KICAgIG4gPSBsZW4oeSkKCiAgICBkZWYgcm1zKHMpOgogICAgICAgIHJldHVybiBtYXRoLnNxcnQoc3VtKHYgKiB2IGZvciB2IGluIHMpIC8gbikKCiAgICBmMCA9IGZ1bih0MCwgeSkKICAgIHMwID0gW2F0b2wgKyBydG9sICogYWJzKHYpIGZvciB2IGluIHldCiAgICBkMCA9IHJtcyhbYSAvIGIgZm9yIGEsIGIgaW4gemlwKHksIHMwKV0pCiAgICBkMSA9IHJtcyhbYSAvIGIgZm9yIGEsIGIgaW4gemlwKGYwLCBzMCldKQogICAgaCA9IDFlLTYgaWYgbWF4KGQwLCBkMSkgPCAxZS01IGVsc2UgMC4wMSAqIGQwIC8gZDEKICAgIGYxID0gZnVuKHQwICsgaCwgW3lbaV0gKyBoICogZjBbaV0gZm9yIGkgaW4gcmFuZ2UobildKQogICAgZDIgPSBybXMoWyhhIC0gYikgLyAoaCAqIGMpIGZvciBhLCBiLCBjIGluIHppcChmMSwgZjAsIHMwKV0pCiAgICBkbSA9IG1heChkMCwgZDEsIGQyKQogICAgaCA9IG1pbigxMDAuMCAqIGgsICgwLjAxIC8gZG0pICoqIDAuMiBpZiBkbSA+PSAxZS0xNSBlbHNlIG1heCgxZS02LCBoICogMWUtMykpCiAgICBoID0gbWluKGgsIHQxIC0gdDApCgogICAgdCwgazEgPSB0MCwgW2Zsb2F0KHYpIGZvciB2IGluIGYwXQogICAgZm9yIF8gaW4gcmFuZ2UoMTAwMDAwKToKICAgICAgICBpZiB0ID49IHQxOgogICAgICAgICAgICBicmVhawogICAgICAgIGggPSBtaW4oaCwgdDEgLSB0KQogICAgICAgIGsyID0gZnVuKHQgKyBoIC8gNSwKICAgICAgICAgICAgICAgICBbeVtpXSArIGggKiAoazFbaV0gLyA1KSBmb3IgaSBpbiByYW5nZShuKV0pCiAgICAgICAgazMgPSBmdW4odCArIGggKiAzIC8gMTAsCiAgICAgICAgICAgICAgICAgW3lbaV0gKyBoICogKDMgLyA0MCAqIGsxW2ldICsgOSAvIDQwICogazJbaV0pIGZvciBpIGluIHJhbmdlKG4pXSkKICAgICAgICBrNCA9IGZ1bih0ICsgaCAqIDQgLyA1LAogICAgICAgICAgICAgICAgIFt5W2ldICsgaCAqICg0NCAvIDQ1ICogazFbaV0gLSA1NiAvIDE1ICogazJbaV0gKyAzMiAvIDkgKiBrM1tpXSkKICAgICAgICAgICAgICAgICAgZm9yIGkgaW4gcmFuZ2UobildKQogICAgICAgIGs1ID0gZnVuKHQgKyBoICogOCAvIDksCiAgICAgICAgICAgICAgICAgW3lbaV0gKyBoICogKDE5MzcyIC8gNjU2MSAqIGsxW2ldIC0gMjUzNjAgLyAyMTg3ICogazJbaV0KICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgKyA2NDQ0OCAvIDY1NjEgKiBrM1tpXSAtIDIxMiAvIDcyOSAqIGs0W2ldKQogICAgICAgICAgICAgICAgICBmb3IgaSBpbiByYW5nZShuKV0pCiAgICAgICAgazYgPSBmdW4odCArIGgsCiAgICAgICAgICAgICAgICAgW3lbaV0gKyBoICogKDkwMTcgLyAzMTY4ICogazFbaV0gLSAzNTUgLyAzMyAqIGsyW2ldCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICsgNDY3MzIgLyA1MjQ3ICogazNbaV0gKyA0OSAvIDE3NiAqIGs0W2ldCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIC0gNTEwMyAvIDE4NjU2ICogazVbaV0pIGZvciBpIGluIHJhbmdlKG4pXSkKICAgICAgICB5biA9IFt5W2ldICsgaCAqICgzNSAvIDM4NCAqIGsxW2ldICsgNTAwIC8gMTExMyAqIGszW2ldICsgMTI1IC8gMTkyICogazRbaV0KICAgICAgICAgICAgICAgICAgICAgICAgICAtIDIxODcgLyA2Nzg0ICogazVbaV0gKyAxMSAvIDg0ICogazZbaV0pIGZvciBpIGluIHJhbmdlKG4pXQogICAgICAgIGs3ID0gZnVuKHQgKyBoLCB5bikKICAgICAgICBlbm9ybSA9IHJtcyhbaCAqICg3MSAvIDU3NjAwICogazFbaV0gLSA3MSAvIDE2Njk1ICogazNbaV0KICAgICAgICAgICAgICAgICAgICAgICAgICArIDcxIC8gMTkyMCAqIGs0W2ldIC0gMTcyNTMgLyAzMzkyMDAgKiBrNVtpXQogICAgICAgICAgICAgICAgICAgICAgICAgICsgMjIgLyA1MjUgKiBrNltpXSAtIGs3W2ldIC8gNDApCiAgICAgICAgICAgICAgICAgICAgIC8gKGF0b2wgKyBydG9sICogbWF4KGFicyh5W2ldKSwgYWJzKHluW2ldKSkpCiAgICAgICAgICAgICAgICAgICAgIGZvciBpIGluIHJhbmdlKG4pXSkKICAgICAgICBpZiBlbm9ybSA8PSAxLjA6CiAgICAgICAgICAgIHQsIHksIGsxID0gdCArIGgsIHluLCBbZmxvYXQodikgZm9yIHYgaW4gazddCiAgICAgICAgZmFjID0gMC45ICogZW5vcm0gKiogKC0wLjIpIGlmIGVub3JtID4gMCBlbHNlIDUuMAogICAgICAgIGggPSBoICogbWluKDUuMCwgbWF4KDAuMiwgZmFjKSkgaWYgZW5vcm0gPD0gMS4wIGVsc2UgaCAqIG1heCgwLjEsIGZhYykKICAgIGlmIHQgPCB0MToKICAgICAgICByYWlzZSBSdW50aW1lRXJyb3IoIl9zb2x2ZV9pdnAgZGlkIG5vdCBjb252ZXJnZSIpCiAgICByZXR1cm4gU2ltcGxlTmFtZXNwYWNlKHQ9bnAuYXJyYXkoW3QwLCB0MV0pLAogICAgICAgICAgICAgICAgICAgICAgICAgICB5PW5wLmNvbHVtbl9zdGFjayhbbnAuYXNhcnJheSh5MCwgZHR5cGU9ZmxvYXQpLCB5XSkpCgoKIyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KIyBTdGVhZHktc3RhdGUgYW5hbHlzaXMgaGVscGVycyAocHVibGljOyB1c2VkIGJ5IHRoZSB3YWxrdGhyb3VnaCBhbmQgU2NlbmUgNCkKIyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KZGVmIHFzc19qYWNrZXRfVChULCBVQSwgRmosIHApOgogICAgIiIiUXVhc2ktc3RlYWR5IGphY2tldCB0ZW1wZXJhdHVyZSBmcm9tIHRoZSBqYWNrZXQgZW5lcmd5IGJhbGFuY2UuIiIiCiAgICBhID0gRmoKICAgIGIgPSBVQSAvIHBbInJob0NwX2oiXQogICAgcmV0dXJuIChhICogcFsiVGppbiJdICsgYiAqIFQpIC8gKGEgKyBiKQoKCmRlZiBoZWF0X3Jlc2lkdWFsKFQsIFVBLCBGaiwgcCk6CiAgICAiIiJTdGVhZHktc3RhdGUgcmVhY3RvciBlbmVyZ3kgcmVzaWR1YWw7IGl0cyByb290cyBhcmUgc3RlYWR5IHN0YXRlcy4iIiIKICAgIHRhdSA9IHBbIlYiXSAvIHBbIkYiXQogICAgayA9IGtfb2ZfVChULCBwWyJrMCJdLCBwWyJFYVIiXSkKICAgIENfQSA9IHBbIkNfQTAiXSAvICgxLjAgKyBrICogdGF1KQogICAgVF9qID0gcXNzX2phY2tldF9UKFQsIFVBLCBGaiwgcCkKICAgIHJldHVybiAoKHBbIkYiXSAvIHBbIlYiXSkgKiAocFsiVDAiXSAtIFQpCiAgICAgICAgICAgICsgKHBbImRIbmVnIl0gLyBwWyJyaG9DcCJdKSAqIGsgKiBDX0EKICAgICAgICAgICAgLSAoVUEgLyAocFsiViJdICogcFsicmhvQ3AiXSkpICogKFQgLSBUX2opKQoKCmRlZiBmaW5kX1Rfcm9vdHMoVUEsIEZqLCBwLCBUX2xvPTMwMC4wLCBUX2hpPTY1MC4wLCBuPTIwMDApOgogICAgIiIiUm9idXN0IHN0ZWFkeS1zdGF0ZSB0ZW1wZXJhdHVyZXMgdmlhIHJlc2lkdWFsIHNpZ24tY2hhbmdlIHNjYW4uIiIiCiAgICBUcyA9IG5wLmxpbnNwYWNlKFRfbG8sIFRfaGksIG4pCiAgICBSID0gbnAuYXJyYXkoW2hlYXRfcmVzaWR1YWwoVCwgVUEsIEZqLCBwKSBmb3IgVCBpbiBUc10pCiAgICByb290cyA9IFtdCiAgICBmb3IgaSBpbiByYW5nZShuIC0gMSk6CiAgICAgICAgaWYgUltpXSA9PSAwLjA6CiAgICAgICAgICAgIHJvb3RzLmFwcGVuZChUc1tpXSkKICAgICAgICBlbGlmIFJbaV0gKiBSW2kgKyAxXSA8IDAuMDoKICAgICAgICAgICAgYSwgYiA9IFRzW2ldLCBUc1tpICsgMV0KICAgICAgICAgICAgZm9yIF8gaW4gcmFuZ2UoNTApOgogICAgICAgICAgICAgICAgbSA9IDAuNSAqIChhICsgYikKICAgICAgICAgICAgICAgIGlmIGhlYXRfcmVzaWR1YWwoYSwgVUEsIEZqLCBwKSAqIGhlYXRfcmVzaWR1YWwobSwgVUEsIEZqLCBwKSA8PSAwOgogICAgICAgICAgICAgICAgICAgIGIgPSBtCiAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAgIGEgPSBtCiAgICAgICAgICAgIHJvb3RzLmFwcGVuZCgwLjUgKiAoYSArIGIpKQogICAgcmV0dXJuIG5wLmFycmF5KHJvb3RzKQoKCmRlZiBmdWxsX3N0YXRlKFQsIFVBLCBGaiwgcCk6CiAgICAiIiJMaWZ0IGEgc3RlYWR5LXN0YXRlIHRlbXBlcmF0dXJlIHRvIFtDX0EsIFQsIFRfal0uIiIiCiAgICB0YXUgPSBwWyJWIl0gLyBwWyJGIl0KICAgIGsgPSBrX29mX1QoVCwgcFsiazAiXSwgcFsiRWFSIl0pCiAgICBDX0EgPSBwWyJDX0EwIl0gLyAoMS4wICsgayAqIHRhdSkKICAgIHJldHVybiBucC5hcnJheShbQ19BLCBULCBxc3NfamFja2V0X1QoVCwgVUEsIEZqLCBwKV0pCgoKZGVmIHVhX29mX3QodCwgcCk6CiAgICByZXR1cm4gcFsiVUEwIl0gKiBucC5leHAoLXQgLyBwWyJ0YXVfZm91bCJdKQoKCmRlZiBjb250cm9sbGVyKFRfbWVhcywgSSwgYyk6CiAgICAiIiJSZXZlcnNlLWFjdGluZyBQSTogaG90IC0+IG1vcmUgY29vbGFudC4gUmV0dXJucyAoRmosIGVycm9yKS4iIiIKICAgIGUgPSBUX21lYXMgLSBjWyJUX3NwIl0KICAgIHUgPSBjWyJGal9iaWFzIl0gKyBjWyJLYyJdICogKGUgKyBJIC8gY1sidGF1SSJdKQogICAgcmV0dXJuIGZsb2F0KG5wLmNsaXAodSwgY1siRmpfbWluIl0sIGNbIkZqX21heCJdKSksIGUKCgpkZWYgcGxhbnRfcmhzKHQsIHgsIHAsIGMsIFRfbWVhcyk6CiAgICAiIiJ4ID0gW0NfQSwgVCwgVF9qLCBJXS4gUmV0dXJucyAoZHhkdCwgRmosIFVBKS4iIiIKICAgIENfQSwgVCwgVF9qLCBJID0geAogICAgVUEgPSB1YV9vZl90KHQsIHApCiAgICBGaiwgZSA9IGNvbnRyb2xsZXIoVF9tZWFzLCBJLCBjKQogICAgaWYgKEZqIDw9IGNbIkZqX21pbiJdIGFuZCBlIDwgMCkgb3IgKEZqID49IGNbIkZqX21heCJdIGFuZCBlID4gMCk6CiAgICAgICAgZEkgPSAwLjAgICMgYW50aS13aW5kdXAKICAgIGVsc2U6CiAgICAgICAgZEkgPSBlCiAgICBrID0ga19vZl9UKFQsIHBbImswIl0sIHBbIkVhUiJdKQogICAgZENfQSA9IChwWyJGIl0gLyBwWyJWIl0pICogKHBbIkNfQTAiXSAtIENfQSkgLSBrICogQ19BCiAgICBkVCA9ICgocFsiRiJdIC8gcFsiViJdKSAqIChwWyJUMCJdIC0gVCkKICAgICAgICAgICsgKHBbImRIbmVnIl0gLyBwWyJyaG9DcCJdKSAqIGsgKiBDX0EKICAgICAgICAgIC0gKFVBIC8gKHBbIlYiXSAqIHBbInJob0NwIl0pKSAqIChUIC0gVF9qKSkKICAgIGRUX2ogPSAoKEZqIC8gcFsiVmoiXSkgKiAocFsiVGppbiJdIC0gVF9qKQogICAgICAgICAgICArIChVQSAvIChwWyJWaiJdICogcFsicmhvQ3BfaiJdKSkgKiAoVCAtIFRfaikpCiAgICByZXR1cm4gbnAuYXJyYXkoW2RDX0EsIGRULCBkVF9qLCBkSV0pLCBGaiwgVUEKCgpkZWYgX3BsYW50X3Joc19zKHQsIHgsIHAsIGMsIFRfbWVhcyk6CiAgICAiIiJTY2FsYXItZmxvYXQgZHVwbGljYXRlIG9mIHBsYW50X3JocydzIHN0YXRlIGRlcml2YXRpdmVzLgoKICAgIFNhbWUgcGh5c2ljcyBhcyBwbGFudF9yaHMgKGtlcHQgaW4gc3luYyBieSB0ZXN0X3NjYWxhcl9yaHNfcGFyaXR5KTsKICAgIHBsYWluIGZsb2F0cyBrZWVwIHRoZSBob3QgaW50ZWdyYXRpb24gbG9vcCBmYXN0LgogICAgIiIiCiAgICBDX0EsIFQsIFRfaiwgSSA9IHhbMF0sIHhbMV0sIHhbMl0sIHhbM10KICAgIFVBID0gcFsiVUEwIl0gKiBtYXRoLmV4cCgtdCAvIHBbInRhdV9mb3VsIl0pCiAgICBlID0gVF9tZWFzIC0gY1siVF9zcCJdCiAgICB1ID0gY1siRmpfYmlhcyJdICsgY1siS2MiXSAqIChlICsgSSAvIGNbInRhdUkiXSkKICAgIEZqID0gdSBpZiBjWyJGal9taW4iXSA8IHUgPCBjWyJGal9tYXgiXSBlbHNlIChjWyJGal9taW4iXSBpZiB1IDw9IGNbIkZqX21pbiJdIGVsc2UgY1siRmpfbWF4Il0pCiAgICBkSSA9IDAuMCBpZiAoRmogPD0gY1siRmpfbWluIl0gYW5kIGUgPCAwKSBvciAoRmogPj0gY1siRmpfbWF4Il0gYW5kIGUgPiAwKSBlbHNlIGUKICAgIGV4ID0gLXBbIkVhUiJdIC8gVCBpZiBUID4gMS4wIGVsc2UgLXBbIkVhUiJdCiAgICBpZiBleCA8IC03MDAuMDoKICAgICAgICBleCA9IC03MDAuMAogICAgayA9IHBbImswIl0gKiBtYXRoLmV4cChleCkKICAgIEZWID0gcFsiRiJdIC8gcFsiViJdCiAgICBkQ19BID0gRlYgKiAocFsiQ19BMCJdIC0gQ19BKSAtIGsgKiBDX0EKICAgIGRUID0gKEZWICogKHBbIlQwIl0gLSBUKSArIChwWyJkSG5lZyJdIC8gcFsicmhvQ3AiXSkgKiBrICogQ19BCiAgICAgICAgICAtIChVQSAvIChwWyJWIl0gKiBwWyJyaG9DcCJdKSkgKiAoVCAtIFRfaikpCiAgICBkVF9qID0gKChGaiAvIHBbIlZqIl0pICogKHBbIlRqaW4iXSAtIFRfaikKICAgICAgICAgICAgKyAoVUEgLyAocFsiVmoiXSAqIHBbInJob0NwX2oiXSkpICogKFQgLSBUX2opKQogICAgcmV0dXJuIChkQ19BLCBkVCwgZFRfaiwgZEkpCgoKY2xhc3MgUGxhbnQ6CiAgICAiIiJUaGUgaGlkZGVuIHByb2Nlc3MuIE9ubHkgYHN0cmVhbWAgZGF0YSBsZWF2ZXMgdGhpcyBvYmplY3QuIiIiCgogICAgZGVmIF9faW5pdF9fKHNlbGYsIHA9Tm9uZSwgYz1Ob25lLCBzZWVkPTAsCiAgICAgICAgICAgICAgICAgc2lnbWFfVD0wLjMsIHNpZ21hX1RqPTAuMywgc2lnbWFfRj0xZS02LCBzaWdtYV9UMD0wLjIsCiAgICAgICAgICAgICAgICAgbGFiX2ludGVydmFsPTEyMDAuMCwgbGFiX2RlbGF5PTYwMC4wLCBzaWdtYV9sYWI9MC4wNSk6CiAgICAgICAgc2VsZi5wID0gZGljdChQTEFOVF9QIGlmIHAgaXMgTm9uZSBlbHNlIHApCiAgICAgICAgc2VsZi5jID0gZGljdChDVFJMIGlmIGMgaXMgTm9uZSBlbHNlIGMpCiAgICAgICAgc2VsZi5ybmcgPSBucC5yYW5kb20uZGVmYXVsdF9ybmcoc2VlZCkKICAgICAgICBzZWxmLnNpZ21hX1QgPSBzaWdtYV9UCiAgICAgICAgc2VsZi5zaWdtYV9UaiA9IHNpZ21hX1RqCiAgICAgICAgc2VsZi5zaWdtYV9GID0gc2lnbWFfRgogICAgICAgIHNlbGYuc2lnbWFfVDAgPSBzaWdtYV9UMAogICAgICAgIHNlbGYubGFiX2ludGVydmFsID0gbGFiX2ludGVydmFsCiAgICAgICAgc2VsZi5sYWJfZGVsYXkgPSBsYWJfZGVsYXkKICAgICAgICBzZWxmLnNpZ21hX2xhYiA9IHNpZ21hX2xhYgogICAgICAgIHNlbGYuc2Vuc29yX2JpYXNfVCA9IDAuMAogICAgICAgIHNlbGYuZmVlZF9UX3N0ZXAgPSAwLjAKICAgICAgICAjIHNldHRsZSBuZWFyIHRoZSBpZ25pdGVkIGJyYW5jaCB1bmRlciBjb250cm9sIGJlZm9yZSB0ID0gMAogICAgICAgIHggPSBucC5hcnJheShbMC43NzIsIDM3NC4wLCAzMzUuMCwgMC4wXSkKICAgICAgICBzb2wgPSBfc29sdmVfaXZwKGxhbWJkYSB0LCB4eDogX3BsYW50X3Joc19zKHQsIHh4LCBzZWxmLnAsIHNlbGYuYywgeHhbMV0pLAogICAgICAgICAgICAgICAgICAgICAgICAgKDAsIDM2MDAuMCksIHgsIHJ0b2w9MWUtOCwgYXRvbD0xZS0xMCkKICAgICAgICBzZWxmLnggPSBzb2wueVs6LCAtMV0KICAgICAgICBzZWxmLnQgPSAwLjAKICAgICAgICBzZWxmLl9sYWJfcXVldWUgPSBbXSAgIyAoZGVsaXZlcl9hdCwgdmFsdWUpIHBlbmRpbmcgbGFiIHJlc3VsdHMKICAgICAgICBzZWxmLl9uZXh0X2xhYiA9IDAuMAoKICAgIGRlZiBzdGVwKHNlbGYsIGR0KToKICAgICAgICAiIiJBZHZhbmNlIGR0IHNlY29uZHM7IHJldHVybiBvbmUgcHVibGlzaGVkIHNhbXBsZSBkaWN0LiIiIgogICAgICAgIHAsIGMgPSBzZWxmLnAsIHNlbGYuYwogICAgICAgIFRfcHViID0gc2VsZi54WzFdICsgc2VsZi5ybmcubm9ybWFsKDAsIHNlbGYuc2lnbWFfVCkgKyBzZWxmLnNlbnNvcl9iaWFzX1QKICAgICAgICBzb2wgPSBfc29sdmVfaXZwKAogICAgICAgICAgICBsYW1iZGEgdHQsIHh4OiBfcGxhbnRfcmhzX3ModHQsIHh4LCBwLCBjLCBUX3B1YiksCiAgICAgICAgICAgIChzZWxmLnQsIHNlbGYudCArIGR0KSwgc2VsZi54LCBydG9sPTFlLTgsIGF0b2w9MWUtMTApCiAgICAgICAgc2VsZi54ID0gc29sLnlbOiwgLTFdCiAgICAgICAgc2VsZi50ICs9IGR0CiAgICAgICAgXywgRmosIFVBID0gcGxhbnRfcmhzKHNlbGYudCwgc2VsZi54LCBwLCBjLCBUX3B1YikKICAgICAgICAjIHNjaGVkdWxlIGxhYiBzYW1wbGVzIChzYW1wbGVkIG5vdywgZGVsaXZlcmVkIGFmdGVyIHRoZSBkZWxheSkKICAgICAgICBpZiBzZWxmLnQgPj0gc2VsZi5fbmV4dF9sYWI6CiAgICAgICAgICAgIHNlbGYuX2xhYl9xdWV1ZS5hcHBlbmQoCiAgICAgICAgICAgICAgICAoc2VsZi50ICsgc2VsZi5sYWJfZGVsYXksCiAgICAgICAgICAgICAgICAgc2VsZi54WzBdICsgc2VsZi5ybmcubm9ybWFsKDAsIHNlbGYuc2lnbWFfbGFiKSkpCiAgICAgICAgICAgIHNlbGYuX25leHRfbGFiICs9IHNlbGYubGFiX2ludGVydmFsCiAgICAgICAgc2FtcGxlID0gZGljdCgKICAgICAgICAgICAgdD1zZWxmLnQsCiAgICAgICAgICAgIFQ9VF9wdWIsCiAgICAgICAgICAgIFRfaj1zZWxmLnhbMl0gKyBzZWxmLnJuZy5ub3JtYWwoMCwgc2VsZi5zaWdtYV9UaiksCiAgICAgICAgICAgIEY9cFsiRiJdICsgc2VsZi5ybmcubm9ybWFsKDAsIHNlbGYuc2lnbWFfRiksCiAgICAgICAgICAgIFQwPXBbIlQwIl0gKyBzZWxmLmZlZWRfVF9zdGVwICsgc2VsZi5ybmcubm9ybWFsKDAsIHNlbGYuc2lnbWFfVDApLAogICAgICAgICAgICBGaj1GaiwKICAgICAgICApCiAgICAgICAgbGFicyA9IFt2IGZvciAodGQsIHYpIGluIHNlbGYuX2xhYl9xdWV1ZSBpZiB0ZCA8PSBzZWxmLnRdCiAgICAgICAgc2VsZi5fbGFiX3F1ZXVlID0gWyh0ZCwgdikgZm9yICh0ZCwgdikgaW4gc2VsZi5fbGFiX3F1ZXVlIGlmIHRkID4gc2VsZi50XQogICAgICAgIGlmIGxhYnM6CiAgICAgICAgICAgIHNhbXBsZVsibGFiX0NfQSJdID0gbGFic1stMV0KICAgICAgICAgICAgc2FtcGxlWyJsYWJfdF9zYW1wbGUiXSA9IHNlbGYudCAtIHNlbGYubGFiX2RlbGF5CiAgICAgICAgIyBoaWRkZW4gdHJ1dGgsIGZvciBzY29yaW5nIG9ubHkgLS0gbmV2ZXIgZ2l2ZW4gdG8gdGhlIHR3aW4KICAgICAgICBzYW1wbGVbIl90cnVlIl0gPSBkaWN0KENfQT1zZWxmLnhbMF0sIFQ9c2VsZi54WzFdLCBUX2o9c2VsZi54WzJdLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgVUE9VUEpCiAgICAgICAgcmV0dXJuIHNhbXBsZQoKCmRlZiB0d2luX3Jocyh4YSwgRmosIEYsIFQwLCB0cCk6CiAgICAiIiJUd2luJ3MgbW9kZWwgb2YgdGhlIGF1Z21lbnRlZCBzdGF0ZSBbQ19BLCBULCBUX2osIFVBXS4iIiIKICAgIENfQSwgVCwgVF9qLCBVQSA9IHhhCiAgICBrID0ga19vZl9UKFQsIHRwWyJrMCJdLCB0cFsiRWFSIl0pCiAgICBkQ19BID0gKEYgLyB0cFsiViJdKSAqICh0cFsiQ19BMCJdIC0gQ19BKSAtIGsgKiBDX0EgICAjIENfQTAgcHVibGlzaGVkCiAgICBkVCA9ICgoRiAvIHRwWyJWIl0pICogKFQwIC0gVCkKICAgICAgICAgICsgKHRwWyJkSG5lZyJdIC8gdHBbInJob0NwIl0pICogayAqIENfQQogICAgICAgICAgLSAoVUEgLyAodHBbIlYiXSAqIHRwWyJyaG9DcCJdKSkgKiAoVCAtIFRfaikpCiAgICBkVF9qID0gKChGaiAvIHRwWyJWaiJdKSAqICh0cFsiVGppbiJdIC0gVF9qKSAgICAgICAgICAjIFRqaW4gcHVibGlzaGVkCiAgICAgICAgICAgICsgKFVBIC8gKHRwWyJWaiJdICogdHBbInJob0NwX2oiXSkpICogKFQgLSBUX2opKQogICAgcmV0dXJuIG5wLmFycmF5KFtkQ19BLCBkVCwgZFRfaiwgMC4wXSkKCgpkZWYgX3R3aW5fcmhzX3MoeGEsIEZqLCBGLCBUMCwgdHApOgogICAgIiIiU2NhbGFyLWZsb2F0IGR1cGxpY2F0ZSBvZiB0d2luX3Jocy4KCiAgICBTYW1lIHBoeXNpY3MgYXMgdHdpbl9yaHMgKGtlcHQgaW4gc3luYyBieSB0ZXN0X3NjYWxhcl9yaHNfcGFyaXR5KTsKICAgIHBsYWluIGZsb2F0cyBrZWVwIHRoZSBob3QgaW50ZWdyYXRpb24gbG9vcCBmYXN0LgogICAgIiIiCiAgICBDX0EsIFQsIFRfaiwgVUEgPSB4YVswXSwgeGFbMV0sIHhhWzJdLCB4YVszXQogICAgZXggPSAtdHBbIkVhUiJdIC8gVCBpZiBUID4gMS4wIGVsc2UgLXRwWyJFYVIiXQogICAgaWYgZXggPCAtNzAwLjA6CiAgICAgICAgZXggPSAtNzAwLjAKICAgIGsgPSB0cFsiazAiXSAqIG1hdGguZXhwKGV4KQogICAgRlYgPSBGIC8gdHBbIlYiXQogICAgZENfQSA9IEZWICogKHRwWyJDX0EwIl0gLSBDX0EpIC0gayAqIENfQQogICAgZFQgPSAoRlYgKiAoVDAgLSBUKSArICh0cFsiZEhuZWciXSAvIHRwWyJyaG9DcCJdKSAqIGsgKiBDX0EKICAgICAgICAgIC0gKFVBIC8gKHRwWyJWIl0gKiB0cFsicmhvQ3AiXSkpICogKFQgLSBUX2opKQogICAgZFRfaiA9ICgoRmogLyB0cFsiVmoiXSkgKiAodHBbIlRqaW4iXSAtIFRfaikKICAgICAgICAgICAgKyAoVUEgLyAodHBbIlZqIl0gKiB0cFsicmhvQ3BfaiJdKSkgKiAoVCAtIFRfaikpCiAgICByZXR1cm4gKGRDX0EsIGRULCBkVF9qLCAwLjApCgoKZGVmIHR3aW5famFjKHhhLCBGaiwgRiwgVDAsIHRwKToKICAgICIiIkV4YWN0IEphY29iaWFuIG9mIHR3aW5fcmhzIHdpdGggcmVzcGVjdCB0byB4YSA9IFtDX0EsIFQsIFRfaiwgVUFdLiIiIgogICAgQ19BLCBULCBUX2osIFVBID0geGEKICAgIGsgPSBrX29mX1QoVCwgdHBbImswIl0sIHRwWyJFYVIiXSkKICAgIGRrX2RUID0gayAqIHRwWyJFYVIiXSAvIChUICogVCkKICAgIEZfViA9IEYgLyB0cFsiViJdCiAgICBhID0gdHBbImRIbmVnIl0gLyB0cFsicmhvQ3AiXQogICAgYiA9IFVBIC8gKHRwWyJWIl0gKiB0cFsicmhvQ3AiXSkKICAgIGNjID0gVUEgLyAodHBbIlZqIl0gKiB0cFsicmhvQ3BfaiJdKQogICAgSiA9IG5wLnplcm9zKCg0LCA0KSkKICAgIEpbMCwgMF0gPSAtRl9WIC0gawogICAgSlswLCAxXSA9IC1DX0EgKiBka19kVAogICAgSlsxLCAwXSA9IGEgKiBrCiAgICBKWzEsIDFdID0gLUZfViArIGEgKiBDX0EgKiBka19kVCAtIGIKICAgIEpbMSwgMl0gPSBiCiAgICBKWzEsIDNdID0gLShUIC0gVF9qKSAvICh0cFsiViJdICogdHBbInJob0NwIl0pCiAgICBKWzIsIDFdID0gY2MKICAgIEpbMiwgMl0gPSAtRmogLyB0cFsiVmoiXSAtIGNjCiAgICBKWzIsIDNdID0gKFQgLSBUX2opIC8gKHRwWyJWaiJdICogdHBbInJob0NwX2oiXSkKICAgIHJldHVybiBKCgoKY2xhc3MgVHdpbkVLRjoKICAgICIiIlRoZSBkaWdpdGFsIHR3aW46IEVLRiBvbiBbQ19BLCBULCBUX2osIFVBXSBmZWQgb25seSBieSB0aGUgZGF0YSBzdHJlYW0uIiIiCgogICAgZGVmIF9faW5pdF9fKHNlbGYsIHRwPU5vbmUsIGM9Tm9uZSwgZHQ9MTAuMCwKICAgICAgICAgICAgICAgICBzaWdtYV9UPTAuMywgc2lnbWFfVGo9MC4zLCBzaWdtYV9sYWI9MC4wNSwKICAgICAgICAgICAgICAgICBxX1VBPTEuMGUtNSwgbGFiX2RlbGF5PTYwMC4wKToKICAgICAgICBzZWxmLnRwID0gZGljdChUV0lOX1AgaWYgdHAgaXMgTm9uZSBlbHNlIHRwKQogICAgICAgIHNlbGYuYyA9IGRpY3QoQ1RSTCBpZiBjIGlzIE5vbmUgZWxzZSBjKQogICAgICAgIHNlbGYuZHQgPSBkdAogICAgICAgIHNlbGYubGFiX2RlbGF5ID0gbGFiX2RlbGF5CiAgICAgICAgIyBzdGF0ZTogc3RhcnQgYXQgbm9taW5hbCBjbGVhbiBzdGVhZHkgc3RhdGUgZ3Vlc3MKICAgICAgICBzZWxmLnggPSBucC5hcnJheShbMS4wLCAzNjguMCwgMzM1LjAsIHNlbGYudHBbIlVBX2luaXQiXV0pCiAgICAgICAgc2VsZi5QbSA9IG5wLmRpYWcoWzAuNSoqMiwgMy4wKioyLCAzLjAqKjIsIDMuMCoqMl0pCiAgICAgICAgc2VsZi5SID0gbnAuZGlhZyhbc2lnbWFfVCoqMiwgc2lnbWFfVGoqKjJdKQogICAgICAgIHNlbGYuUl9sYWIgPSBucC5hcnJheShbW3NpZ21hX2xhYioqMl1dKQogICAgICAgIHEgPSBucC5kaWFnKFsxZS02LCAxZS00LCAxZS00LCBxX1VBXSkgKiBkdAogICAgICAgIHNlbGYuUSA9IHEKICAgICAgICBzZWxmLklfY3RybCA9IDAuMAogICAgICAgIHNlbGYuaGlzdCA9IFtdICAjICh0LCB4LCBQbSwgRmosIEYsIFQwKSByaW5nIGJ1ZmZlciBmb3IgbGFiIHJlcHJvY2Vzc2luZwogICAgICAgIHNlbGYucmVzaWRfVCA9IFtdCiAgICAgICAgc2VsZi5yZXNpZF9UaiA9IFtdCiAgICAgICAgc2VsZi5sYWJfaW5ub3YgPSBbXSAgIyAodF9kZWxpdmVyLCBpbm5vdmF0aW9uLCBzdGQpIHBlciBsYWIgc2FtcGxlCgogICAgZGVmIF9wcmVkaWN0KHNlbGYsIHgsIFBtLCBGaiwgRiwgVDApOgogICAgICAgIHNvbCA9IF9zb2x2ZV9pdnAobGFtYmRhIHQsIHhhOiBfdHdpbl9yaHNfcyh4YSwgRmosIEYsIFQwLCBzZWxmLnRwKSwKICAgICAgICAgICAgICAgICAgICAgICAgICgwLCBzZWxmLmR0KSwgeCwgcnRvbD0xZS02LCBhdG9sPTFlLTgpCiAgICAgICAgeHAgPSBzb2wueVs6LCAtMV0KICAgICAgICBKID0gdHdpbl9qYWMoeHAsIEZqLCBGLCBUMCwgc2VsZi50cCkgICAjIGxpbmVhcml6ZSBhdCB0aGUgcHJlZGljdGlvbgogICAgICAgICMgZGlzY3JldGUgdHJhbnNpdGlvbjogRXVsZXIgaXMgYWNjdXJhdGUgaGVyZSAofEp8KmR0IH4gMWUtMikgYW5kCiAgICAgICAgIyBmYXIgY2hlYXBlciB0aGFuIGV4cG07IHZlcmlmaWVkIGFnYWluc3QgZXhwbSBpbiBhbmFseXNpcy9iZW5jaC5weQogICAgICAgIFBoaSA9IG5wLmV5ZSg0KSArIEogKiBzZWxmLmR0CiAgICAgICAgUHAgPSBQaGkgQCBQbSBAIFBoaS5UICsgc2VsZi5RCiAgICAgICAgcmV0dXJuIHhwLCBQcAoKICAgIGRlZiBfdXBkYXRlX1Qoc2VsZiwgeHAsIFBwLCB5KToKICAgICAgICBIID0gbnAuYXJyYXkoW1swLiwgMS4sIDAuLCAwLl0sIFswLiwgMC4sIDEuLCAwLl1dKQogICAgICAgIHIgPSB5IC0gSCBAIHhwCiAgICAgICAgUyA9IEggQCBQcCBAIEguVCArIHNlbGYuUgogICAgICAgIEsgPSBQcCBAIEguVCBAIG5wLmxpbmFsZy5pbnYoUykKICAgICAgICByZXR1cm4geHAgKyBLIEAgciwgKG5wLmV5ZSg0KSAtIEsgQCBIKSBAIFBwLCByCgogICAgZGVmIF91cGRhdGVfbGFiKHNlbGYsIHhwLCBQcCwgY19tZWFzKToKICAgICAgICBIID0gbnAuYXJyYXkoW1sxLiwgMC4sIDAuLCAwLl1dKQogICAgICAgIHIgPSBucC5hcnJheShbY19tZWFzXSkgLSBIIEAgeHAKICAgICAgICBTID0gSCBAIFBwIEAgSC5UICsgc2VsZi5SX2xhYgogICAgICAgIEsgPSBQcCBAIEguVCBAIG5wLmxpbmFsZy5pbnYoUykKICAgICAgICByZXR1cm4geHAgKyBLIEAgciwgKG5wLmV5ZSg0KSAtIEsgQCBIKSBAIFBwCgogICAgZGVmIHN0ZXAoc2VsZiwgc2FtcGxlKToKICAgICAgICAiIiJDb25zdW1lIG9uZSBwdWJsaXNoZWQgc2FtcGxlOyByZXR1cm4gdGhlIHR3aW4ncyBzdGF0ZSBlc3RpbWF0ZS4iIiIKICAgICAgICBkdCwgdHAsIGMgPSBzZWxmLmR0LCBzZWxmLnRwLCBzZWxmLmMKICAgICAgICAjIHRoZSB0d2luIHJ1bnMgdGhlIHB1Ymxpc2hlZCBjb250cm9sbGVyIG9uIHRoZSBwdWJsaXNoZWQgbWVhc3VyZW1lbnQKICAgICAgICBGaiwgZSA9IGNvbnRyb2xsZXIoc2FtcGxlWyJUIl0sIHNlbGYuSV9jdHJsLCBjKQogICAgICAgIGlmIChGaiA8PSBjWyJGal9taW4iXSBhbmQgZSA8IDApIG9yIChGaiA+PSBjWyJGal9tYXgiXSBhbmQgZSA+IDApOgogICAgICAgICAgICBwYXNzCiAgICAgICAgZWxzZToKICAgICAgICAgICAgc2VsZi5JX2N0cmwgKz0gZSAqIGR0CiAgICAgICAgeHAsIFBwID0gc2VsZi5fcHJlZGljdChzZWxmLngsIHNlbGYuUG0sIEZqLCBzYW1wbGVbIkYiXSwgc2FtcGxlWyJUMCJdKQogICAgICAgIHkgPSBucC5hcnJheShbc2FtcGxlWyJUIl0sIHNhbXBsZVsiVF9qIl1dKQogICAgICAgIHgsIFBtLCByID0gc2VsZi5fdXBkYXRlX1QoeHAsIFBwLCB5KQogICAgICAgIHNlbGYucmVzaWRfVC5hcHBlbmQoclswXSkKICAgICAgICBzZWxmLnJlc2lkX1RqLmFwcGVuZChyWzFdKQogICAgICAgIGlmICJsYWJfQ19BIiBpbiBzYW1wbGU6CiAgICAgICAgICAgIHgsIFBtID0gc2VsZi5fcmVwcm9jZXNzX2xhYih4LCBQbSwgRmosIHNhbXBsZSkKICAgICAgICBzZWxmLngsIHNlbGYuUG0gPSB4LCBQbQogICAgICAgIHNlbGYuaGlzdC5hcHBlbmQoZGljdCh0PXNhbXBsZVsidCJdLCB4PXguY29weSgpLCBQbT1QbS5jb3B5KCksCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIEZqPUZqLCBGPXNhbXBsZVsiRiJdLCBUMD1zYW1wbGVbIlQwIl0sIHk9eS5jb3B5KCkpKQogICAgICAgICMga2VlcCA0MCBtaW4gb2YgaGlzdG9yeSAoY292ZXJzIHRoZSBsYWIgZGVsYXkpCiAgICAgICAgd2hpbGUgc2VsZi5oaXN0IGFuZCBzZWxmLmhpc3RbMF1bInQiXSA8IHNhbXBsZVsidCJdIC0gMjQwMC4wOgogICAgICAgICAgICBzZWxmLmhpc3QucG9wKDApCiAgICAgICAgcmV0dXJuIGRpY3QoQ19BPXhbMF0sIFQ9eFsxXSwgVF9qPXhbMl0sIFVBPXhbM10sCiAgICAgICAgICAgICAgICAgICAgcmVzaWRfVD1yWzBdLCByZXNpZF9Uaj1yWzFdLCBGaj1GaikKCiAgICBkZWYgX3JlcHJvY2Vzc19sYWIoc2VsZiwgeF9ub3csIFBtX25vdywgRmpfbm93LCBzYW1wbGUpOgogICAgICAgICIiIkV4YWN0IGZpeGVkLWxhZyByZXByb2Nlc3Npbmc6IGFwcGx5IHRoZSBkZWxheWVkIGxhYiBzYW1wbGUgYXQgaXRzCiAgICAgICAgc2FtcGxlIHRpbWUsIHRoZW4gcmUtcnVuIHByZWRpY3QgKyBUL1RfaiB1cGRhdGVzIGZvcndhcmQuIiIiCiAgICAgICAgdF9zID0gc2FtcGxlWyJsYWJfdF9zYW1wbGUiXQogICAgICAgIGlkeCA9IG5leHQoKGkgZm9yIGksIGggaW4gZW51bWVyYXRlKHNlbGYuaGlzdCkgaWYgaFsidCJdID49IHRfcyksIE5vbmUpCiAgICAgICAgaWYgaWR4IGlzIE5vbmU6ICAjIHNhbXBsZSBvbGRlciB0aGFuIGhpc3Rvcnk6IGFwcGx5IG5vdywgZmxhZ2dlZCBsYXRlCiAgICAgICAgICAgIHJldHVybiBzZWxmLl91cGRhdGVfbGFiKHhfbm93LCBQbV9ub3csIHNhbXBsZVsibGFiX0NfQSJdKQogICAgICAgIGggPSBzZWxmLmhpc3RbaWR4XQogICAgICAgICMgcmVjb3JkIHRoZSBsYWIgaW5ub3ZhdGlvbiBCRUZPUkUgdGhlIHVwZGF0ZTogdGhlIGluZGVwZW5kZW50IGNoZWNrCiAgICAgICAgIyB1c2VkIGZvciBmYXVsdCBkZXRlY3Rpb24gKHRoZSB1cGRhdGUgaXRzZWxmIHdvdWxkIGhpZGUgaXQpCiAgICAgICAgaW5ub3YgPSBmbG9hdChzYW1wbGVbImxhYl9DX0EiXSAtIGhbIngiXVswXSkKICAgICAgICBpbm5vdl9zdGQgPSBmbG9hdChucC5zcXJ0KGhbIlBtIl1bMCwgMF0gKyBzZWxmLlJfbGFiWzAsIDBdKSkKICAgICAgICBzZWxmLmxhYl9pbm5vdi5hcHBlbmQoKHNhbXBsZVsidCJdLCBpbm5vdiwgaW5ub3Zfc3RkKSkKICAgICAgICB4LCBQbSA9IHNlbGYuX3VwZGF0ZV9sYWIoaFsieCJdLCBoWyJQbSJdLCBzYW1wbGVbImxhYl9DX0EiXSkKICAgICAgICBzZWxmLmhpc3RbaWR4XSA9IGRpY3QoaCwgeD14LmNvcHkoKSwgUG09UG0uY29weSgpKQogICAgICAgIGZvciBqIGluIHJhbmdlKGlkeCArIDEsIGxlbihzZWxmLmhpc3QpKToKICAgICAgICAgICAgaGogPSBzZWxmLmhpc3Rbal0KICAgICAgICAgICAgeHAsIFBwID0gc2VsZi5fcHJlZGljdCh4LCBQbSwgaGpbIkZqIl0sIGhqWyJGIl0sIGhqWyJUMCJdKQogICAgICAgICAgICB4LCBQbSwgXyA9IHNlbGYuX3VwZGF0ZV9UKHhwLCBQcCwgaGpbInkiXSkKICAgICAgICAgICAgc2VsZi5oaXN0W2pdID0gZGljdChoaiwgeD14LmNvcHkoKSwgUG09UG0uY29weSgpKQogICAgICAgIHhwLCBQcCA9IHNlbGYuX3ByZWRpY3QoeCwgUG0sIEZqX25vdywgc2FtcGxlWyJGIl0sIHNhbXBsZVsiVDAiXSkKICAgICAgICByZXR1cm4gc2VsZi5fdXBkYXRlX2xhYih4cCwgUHAsIHNhbXBsZVsibGFiX0NfQSJdKQo=").decode("utf-8")
    _mod = _types.ModuleType('cstr_model')
    exec(compile(MODEL_SRC, "cstr_model.py", "exec"), _mod.__dict__)
    _sys.modules["cstr_model"] = _mod
    import cstr_model as M
    def figure(data, layout=None, **kw):
        return go.Figure(data=data, layout=layout or kw)
    return (mo, np, go, M, MODEL_SRC, figure)


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 1: The plant: a jacketed exothermic CSTR

    The plant is a jacketed continuous stirred-tank reactor. Reactant $A$
    (concentration $C_A$, in mol L$^{-1}$) converts to $B$ by a first-order
    reaction with Arrhenius kinetics; the heat released warms the reactor
    (temperature $T$, in K) and is removed through the wall to a cooling jacket
    (temperature $T_j$, in K). A published proportional-integral controller
    holds $T$ at its setpoint $T_{sp}$ by manipulating the coolant flow $F_j$.
    The jacket slowly fouls: the overall conductance $UA$ (in J s$^{-1}$ K$^{-1}$)
    decays exponentially with time constant $\tau_f$. The true kinetic
    parameters are hidden from the twin.
    """)


@app.cell
def _(M):
    print('hidden plant parameters (never visible to the twin):')
    for _k in ['k0', 'EaR', 'UA0', 'tau_foul']:
        print(f'  {_k} = {M.PLANT_P[_k]}')
    print('published controller settings (known to the twin):')
    for _k in ['T_sp', 'Fj_max', 'Kc', 'tauI']:
        print(f'  {_k} = {M.CTRL[_k]}')
    print('twin nominal parameters (wrong but reasonable):')
    for _k in ['k0', 'EaR', 'dHneg']:
        _err = 100 * (M.TWIN_P[_k] - M.PLANT_P[_k]) / M.PLANT_P[_k]
        print(f'  {_k} = {M.TWIN_P[_k]}  ({_err:+.1f}% error)')


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 2: Steady states: the reactor can ignite

    At fixed coolant flow the steady-state heat balance has up to three roots:
    an extinguished branch (low $T$), an unstable middle branch, and an ignited
    branch (high $T$). Fouling moves the operating point along the ignited
    branch toward higher temperature. The scan below uses the plant's true
    parameters at a representative coolant flow; the twin never sees this curve.
    """)


@app.cell
def _(M, go, np):
    _ua_vals = np.linspace(2.0, 24.0, 45)
    _Fj_rep = 0.2 / 60.0
    _branches = [M.find_T_roots(ua, _Fj_rep, M.PLANT_P) for ua in _ua_vals]
    _b0 = [b[0] if len(b) > 0 else np.nan for b in _branches]
    _b1 = [b[1] if len(b) > 1 else np.nan for b in _branches]
    _b2 = [b[2] if len(b) > 2 else np.nan for b in _branches]
    _fig0 = go.Figure(data=[dict(x=_ua_vals.tolist(), y=np.array(_b0).tolist(), mode='lines', name='extinguished branch'), dict(x=_ua_vals.tolist(), y=np.array(_b1).tolist(), mode='lines', name='middle branch (unstable)', line=dict(dash='dash')), dict(x=_ua_vals.tolist(), y=np.array(_b2).tolist(), mode='lines', name='ignited branch')], layout=dict(title='Steady-state reactor temperature vs jacket conductance', xaxis=dict(title='UA [J s-1 K-1]'), yaxis=dict(title='T [K]'), legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'), margin=dict(r=150)))
    print(f'multiplicity (3 branches) for UA in [{_ua_vals[[len(b) >= 3 for b in _branches]].min():.0f}, {_ua_vals[[len(b) >= 3 for b in _branches]].max():.0f}] J s-1 K-1')
    _fig0



@app.cell
def _(mo):
    mo.md(r"""
    ## Step 3: The data stream

    The plant publishes reactor temperature $T$, jacket temperature $T_j$,
    feed flow $F$, and feed temperature $T_0$ every $\Delta t = 10$ s with
    measurement noise. Concentration $C_A$ arrives only as an occasional
    delayed laboratory sample (every 20 min, 10 min late), mirroring plant
    practice. The twin receives this stream and nothing else: the driver
    deletes the hidden-truth channel before each sample reaches the twin.
    """)


@app.cell
def _(M):
    _plant = M.Plant(seed=7)
    for _ in range(3):
        _s = _plant.step(10.0)
        _pub = {k: v for k, v in _s.items() if not k.startswith('_')}
        print({k: round(v, 3) if isinstance(v, float) else v for k, v in _pub.items()})
    print('keys withheld from the twin:', [k for k in _s if k.startswith('_')])


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 4: The twin: extended Kalman filter

    The twin's state vector is $x = [C_A\;\; T\;\; T_j\;\; UA]^{\mathsf{T}}$:
    the three process states plus the drifting conductance, modelled as a
    random walk. Each step predicts by integrating the nominal model, then
    corrects with the $T$ and $T_j$ measurements. Delayed lab samples are
    applied at their sample time with exact fixed-lag reprocessing of the
    stored history. The twin's copy of the published controller supplies the
    coolant flow from the measured temperature, exactly as the plant does.
    """)


@app.cell
def _(M, np):
    _twin = M.TwinEKF(dt=10.0)
    print('twin state:', ['C_A', 'T', 'T_j', 'UA'])
    print('initial estimate:', np.round(_twin.x, 3))
    print('measurement noise R: sigma_T = 0.3 K, sigma_Tj = 0.3 K')
    print('lab noise: sigma_lab = 0.05 mol L-1, delay 600 s')


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 5: Scene 1: a simulation is not a twin until data flows in

    An open-loop copy of the model (nominal parameters, $UA$ frozen at its
    clean value, no measurement feedback) runs next to the twin. As the jacket
    fouls, the copy's temperature and concentration predictions drift far from
    the plant, while the twin's estimates stay locked on. The numbers below
    come from a 6 h closed-loop run; the App tab reproduces them live.
    """)


@app.cell
def _(M, go, mo, np):
    _DT, _H = (10.0, 6.0)
    _plant = M.Plant(seed=7)
    _twin = M.TwinEKF(dt=_DT)
    _x_m = np.array([1.0, 368.0, 335.0, M.TWIN_P['UA_init']])
    _I_m = 0.0
    _n = int(_H * 3600 / _DT)
    _t, _ua_t, _ua_e, _ca_t, _ca_e, _ca_m, _Tms, _T_e = ([], [], [], [], [], [], [], [])
    for _ in range(_n):
        _s = _plant.step(_DT)
        _pub = {k: v for k, v in _s.items() if not k.startswith('_')}
        _est = _twin.step(_pub)
        _Fj_m, _e_m = M.controller(_pub['T'], _I_m, M.CTRL)
        if not (_Fj_m <= M.CTRL['Fj_min'] and _e_m < 0 or (_Fj_m >= M.CTRL['Fj_max'] and _e_m > 0)):
            _I_m += _e_m * _DT
        _sol = M._solve_ivp(lambda tt, xa: M._twin_rhs_s((xa[0], xa[1], xa[2], 16.0), _Fj_m, _pub['F'], _pub['T0'], M.TWIN_P)[:3], (0, _DT), _x_m[:3], rtol=1e-06, atol=1e-08)
        _x_m[:3] = _sol.y[:, -1]
        _tr = _s['_true']
        _t.append(_s['t'] / 3600.0)
        _ua_t.append(_tr['UA'])
        _ua_e.append(_est['UA'])
        _ca_t.append(_tr['C_A'])
        _ca_e.append(_est['C_A'])
        _ca_m.append(_x_m[0])
        _Tms.append(_pub['T'])
        _T_e.append(_est['T'])
    _b = int(1800 / _DT)
    _ua_rmse = float(np.sqrt(np.mean((np.array(_ua_e[_b:]) - np.array(_ua_t[_b:])) ** 2)))
    _ca_rmse = float(np.sqrt(np.mean((np.array(_ca_e[_b:]) - np.array(_ca_t[_b:])) ** 2)))
    _ca_rmse_m = float(np.sqrt(np.mean((np.array(_ca_m[_b:]) - np.array(_ca_t[_b:])) ** 2)))
    print(f'twin  UA  RMSE: {_ua_rmse:.3f} J s-1 K-1')
    print(f'twin  C_A RMSE: {_ca_rmse:.4f} mol L-1')
    print(f'model C_A RMSE: {_ca_rmse_m:.4f} mol L-1  (frozen UA, no feedback)')
    _fig0 = go.Figure(data=[dict(x=_t, y=_ua_t, mode='lines', name='UA true (hidden)'), dict(x=_t, y=_ua_e, mode='lines', name='UA twin estimate')], layout=dict(title='Fouling tracked by the twin', xaxis=dict(title='time [h]'), yaxis=dict(title='UA [J s-1 K-1]'), legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'), margin=dict(r=150)))
    _fig1 = go.Figure(data=[dict(x=_t, y=_ca_t, mode='lines', name='C_A true (hidden)'), dict(x=_t, y=_ca_e, mode='lines', name='C_A twin (soft sensor)'), dict(x=_t, y=_ca_m, mode='lines', name='C_A open-loop model', line=dict(dash='dash'))], layout=dict(title='Soft sensor vs open-loop model', xaxis=dict(title='time [h]'), yaxis=dict(title='C_A [mol L-1]'), legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'), margin=dict(r=170)))
    mo.vstack([_fig0, _fig1])



@app.cell
def _(mo):
    mo.md(r"""
    ## Step 6: Identifiability: why the lab samples matter

    From temperature data alone, $UA$ and the pre-exponential factor $k_0$
    are hard to separate: their steady-state sensitivity vectors in the
    $[T\;\; T_j]$ measurement space point in nearly opposite, nearly
    collinear directions (cosine $-0.86$). A laboratory $C_A$ sample breaks
    the symmetry, because $C_A$ responds to the two parameters with a
    markedly different sensitivity ratio. The twin therefore sharpens its
    $UA$ estimate each time a lab result arrives.
    """)


@app.cell
def _(M, np):
    _UA0, _Fj_rep = (12.0, 0.2 / 60.0)
    _p = M.PLANT_P
    _roots = M.find_T_roots(_UA0, _Fj_rep, _p)
    _T_op = _roots[np.argmin(np.abs(_roots - 374.0))]

    def _branch(par, rel):
        if par == 'UA':
            ua2 = _UA0 * (1.0 + rel)
            r = M.find_T_roots(ua2, _Fj_rep, _p)
            T2 = r[np.argmin(np.abs(r - _T_op))]
            return (M.full_state(T2, ua2, _Fj_rep, _p) - M.full_state(_T_op, _UA0, _Fj_rep, _p)) / (_UA0 * rel)
        p2 = dict(_p, **{par: _p[par] * (1.0 + rel)})
        r = M.find_T_roots(_UA0, _Fj_rep, p2)
        T2 = r[np.argmin(np.abs(r - _T_op))]
        return (M.full_state(T2, _UA0, _Fj_rep, p2) - M.full_state(_T_op, _UA0, _Fj_rep, _p)) / (_p[par] * rel)
    _s_ua, _s_k0 = (_branch('UA', 0.0001), _branch('k0', 0.0001))
    _v_ua, _v_k0 = (_s_ua[1:] * _UA0, _s_k0[1:] * _p['k0'])
    _cosang = float(_v_ua @ _v_k0 / (np.linalg.norm(_v_ua) * np.linalg.norm(_v_k0)))
    print(f'd[T,Tj]/d(ln UA) = [{_v_ua[0]:+.2f}, {_v_ua[1]:+.2f}] K')
    print(f'd[T,Tj]/d(ln k0) = [{_v_k0[0]:+.2f}, {_v_k0[1]:+.2f}] K')
    print(f'cosine(UA, k0) in temperature space: {_cosang:+.3f}')
    print(f'dC_A/d(ln UA) = {_s_ua[0] * _UA0:+.3f} mol L-1, dC_A/d(ln k0) = {_s_k0[0] * _p['k0']:+.3f} mol L-1')
    print('-> opposite signs and different ratios: the lab sample separates them')


@app.cell
def _(mo):
    mo.md(r"""
    ## Step 7: Forecast: when cooling capacity runs out

    The twin fits its recent $UA$ estimates to an exponential decay, projects
    $UA(t)$ forward, and simulates its own model under the published controller.
    The forecast time is the first instant at which the required coolant flow
    reaches $F_{j,max}$: beyond it the setpoint can no longer be held. The
    page reports this as the latest recommended jacket-cleaning date.
    """)


@app.cell
def _(M, go, np):
    _DT = 10.0
    _plant = M.Plant(seed=11)
    _twin = M.TwinEKF(dt=_DT)
    _n = int(4 * 3600 / _DT)
    _hist_t, _hist_ua = ([], [])
    for _ in range(_n):
        _s = _plant.step(_DT)
        _pub = {k: v for k, v in _s.items() if not k.startswith('_')}
        _est = _twin.step(_pub)
        _hist_t.append(_s['t'])
        _hist_ua.append(_est['UA'])
    _hist_t, _hist_ua = (np.array(_hist_t), np.array(_hist_ua))
    _use = _hist_t > 3600.0
    _ln = np.log(np.maximum(_hist_ua[_use], 1e-06))
    _slope, _intercept = np.polyfit(_hist_t[_use], _ln, 1)
    _t_now = _hist_t[-1]
    _t_grid = np.linspace(_t_now, _t_now + 12 * 3600.0, 200)
    _ua_proj = np.exp(_intercept + _slope * _t_grid)
    _xa = _twin.x.copy()
    _I = _twin.I_ctrl
    _sat_time = None
    for _tg, _ua in zip(_t_grid, _ua_proj):
        _xa[3] = _ua
        _Fj, _e = M.controller(_xa[1], _I, M.CTRL)
        if _Fj >= M.CTRL['Fj_max'] - 1e-09 and _sat_time is None:
            _sat_time = _tg
        if not (_Fj <= M.CTRL['Fj_min'] and _e < 0 or (_Fj >= M.CTRL['Fj_max'] and _e > 0)):
            _I += _e * (_t_grid[1] - _t_grid[0])
        _sol = M._solve_ivp(lambda tt, xx: M._twin_rhs_s(xx, _Fj, M.PLANT_P['F'], M.PLANT_P['T0'], M.TWIN_P), (0, _t_grid[1] - _t_grid[0]), _xa, rtol=1e-06, atol=1e-08)
        _xa = _sol.y[:, -1]
    print(f'fitted fouling rate: {_slope * 3600:.4f} h-1 (true {-1 / (M.PLANT_P['tau_foul'] / 3600):.4f} h-1)')
    print(f'forecast: coolant saturates {(_sat_time - _t_now) / 3600:.1f} h after now (t = {_sat_time / 3600:.1f} h)')
    _fig0 = go.Figure(data=[dict(x=(_hist_t / 3600.0).tolist(), y=_hist_ua.tolist(), mode='lines', name='UA twin estimate'), dict(x=(_t_grid / 3600.0).tolist(), y=_ua_proj.tolist(), mode='lines', name='UA forecast', line=dict(dash='dash'))], layout=dict(title='Fouling trend and forecast', xaxis=dict(title='time [h]'), yaxis=dict(title='UA [J s-1 K-1]'), legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'), margin=dict(r=150)))
    _fig0



@app.cell
def _(mo):
    mo.md(r"""
    ## Step 8: Fault detection: the filter hides the fault; the lab catches it

    A temperature-sensor bias of $+5$ K is injected halfway through a 6 h run.
    The filter absorbs the bias into biased $UA$ and $C_A$ estimates, so the
    fast temperature innovations stay deceptively quiet -- naive residual
    gating misses the fault. The delayed lab analyses are independent: when
    two consecutive lab samples disagree with the physics-based $C_A$
    prediction by more than three standard deviations each, the twin flags a
    sensor fault instead of mis-attributing the bias to faster fouling.
    """)


@app.cell
def _(M, go, np):
    _DT = 10.0
    _plant = M.Plant(seed=21)
    _twin = M.TwinEKF(dt=_DT)
    _n = int(6 * 3600 / _DT)
    for _i in range(_n):
        if _i == _n // 3:
            _plant.sensor_bias_T = 5.0
        _s = _plant.step(_DT)
        _pub = {k: v for k, v in _s.items() if not k.startswith('_')}
        _twin.step(_pub)
    _li = [(t, iv, sd) for t, iv, sd in _twin.lab_innov if t / 3600.0 >= 0.6]
    _det_t = None
    for _j in range(1, len(_li)):
        if abs(_li[_j][1]) > 3 * _li[_j][2] and abs(_li[_j - 1][1]) > 3 * _li[_j - 1][2]:
            _det_t = _li[_j][0] / 3600.0
            break
    print(f'fault injected at t = 2.0 h; flagged at t = {_det_t:.2f} h' if _det_t else 'fault NOT detected')
    print(f'fast-innovation mean after fault: {np.array(_twin.resid_T[_n // 3:]).mean():+.3f} K  (filter absorbed it)')
    _lt = [t / 3600.0 for t, iv, sd in _li]
    _liv = [iv for t, iv, sd in _li]
    _band = [3 * sd for t, iv, sd in _li]
    _fig0 = go.Figure(data=[dict(x=_lt, y=_liv, mode='markers', name='lab innovation', marker=dict(size=8)), dict(x=_lt, y=_band, mode='lines', name='+3 sigma', line=dict(dash='dash', color='red')), dict(x=_lt, y=[-b for b in _band], mode='lines', name='-3 sigma', line=dict(dash='dash', color='red'))], layout=dict(title='Lab C_A innovations under a +5 K sensor bias', xaxis=dict(title='time [h]'), yaxis=dict(title='innovation [mol L-1]'), legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'), margin=dict(r=150)))
    _fig0



@app.cell
def _(mo):
    mo.md(r"""
    ## Step 9: What the twin may and may not see

    The honesty architecture is enforced in code, not by convention. The plant
    object owns the hidden parameters and the true state; its `step` method
    returns a published sample plus a `_true` channel used only for scoring.
    The driver strips every key starting with `_` before the twin's `step`
    sees the sample, and a static test asserts that the twin's source contains
    no reference to the plant's parameter dictionary, its fouling function, or
    the truth channel. Scenes 1--5 are therefore a digital shadow in the sense
    of Kritzinger et al. (2018): data flows from the plant to the twin only.
    Scene 6 closes the loop -- the twin writes an adjusted setpoint back --
    which is what makes it a twin in that taxonomy.
    """)


@app.cell
def _(MODEL_SRC):
    _src = MODEL_SRC
    _twin_src = _src[_src.index('class TwinEKF'):]
    _forbidden = ['PLANT_P', 'ua_of_t', '_true', 'plant_rhs', 'sensor_bias_T']
    print('forbidden tokens in twin source:', [tok for tok in _forbidden if tok in _twin_src] or 'none')
    _sample_keys = ['t', 'T', 'T_j', 'F', 'T0', 'Fj']
    print('twin receives per sample:', _sample_keys)
    print('twin never receives: C_A (except delayed lab), UA, k0, E_a')


if __name__ == "__main__":
    app.run()

