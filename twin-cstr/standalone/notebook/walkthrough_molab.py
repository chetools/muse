# /// script
# requires-python = ">=3.10"
# dependencies = ["marimo", "numpy", "scipy", "plotly"]
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
    from scipy.integrate import solve_ivp
    import sys as _sys, types as _types
    MODEL_SRC = base64.b64decode("IiIiUmVmZXJlbmNlIG1vZGVsIGZvciB0aGUgamFja2V0ZWQtQ1NUUiBkaWdpdGFsLXR3aW4gZGVtby4KClR3byBzdHJpY3RseSBzZXBhcmF0ZWQgcGFydHM6CgpQTEFOVCAtLSB0aGUgInJlYWwiIHByb2Nlc3MuIE93bnMgdGhlIGhpZGRlbiB0cnVlIHBhcmFtZXRlcnMuIFB1Ymxpc2hlcyBhCnNlbnNvciBkYXRhIHN0cmVhbSAoVCwgVF9qLCBGLCBUMCBldmVyeSBkdF9wdWIgc2Vjb25kcyB3aXRoIG5vaXNlOyBDX0EgYXMKb2NjYXNpb25hbCBkZWxheWVkIGxhYiBzYW1wbGVzKS4gTm90aGluZyBvdXRzaWRlIHRoaXMgbW9kdWxlIG1heSByZWFkIHRoZQpwbGFudCdzIGludGVybmFsIHN0YXRlIG9yIHBhcmFtZXRlcnM7IHRoZSB0d2luIHJlY2VpdmVzIG9ubHkgdGhlIHN0cmVhbS4KClRXSU4gLS0gYW4gZXh0ZW5kZWQgS2FsbWFuIGZpbHRlciB3aXRoIGF1Z21lbnRlZCBzdGF0ZSBbQ19BLCBULCBUX2osIFVBXS4KSXQga25vd3MgdGhlIG1vZGVsIHN0cnVjdHVyZSwgdGhlIG5vbWluYWwgKHdyb25nKSBwYXJhbWV0ZXJzLCBhbmQgdGhlCnB1Ymxpc2hlZCBjb250cm9sbGVyIHNldHRpbmdzLiBJdCBuZXZlciBzZWVzIHRoZSBwbGFudCdzIHRydWUgcGFyYW1ldGVycy4KIiIiCgppbXBvcnQgbnVtcHkgYXMgbnAKZnJvbSBzY2lweS5pbnRlZ3JhdGUgaW1wb3J0IHNvbHZlX2l2cAoKIyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KIyBQTEFOVDogaGlkZGVuIHRydWUgcGFyYW1ldGVycyAobmV2ZXIgdmlzaWJsZSB0byB0aGUgdHdpbikKIyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KUExBTlRfUCA9IGRpY3QoCiAgICBWPTEuMCwgICAgICAgICAgICAjIEwsIHJlYWN0b3Igdm9sdW1lCiAgICBGPTEuMCAvIDYwMC4wLCAgICAjIEwvcywgZmVlZCBmbG93CiAgICBDX0EwPTguMCwgICAgICAgICAjIG1vbC9MLCBmZWVkIGNvbmNlbnRyYXRpb24KICAgIFQwPTMwMC4wLCAgICAgICAgICMgSywgZmVlZCB0ZW1wZXJhdHVyZQogICAgazA9My4wZTcsICAgICAgICAgIyAxL3MsIEFycmhlbml1cyBwcmUtZXhwb25lbnRpYWwgKGhpZGRlbikKICAgIEVhUj04MDAwLjAsICAgICAgICMgSywgRV9hIC8gUiAoaGlkZGVuKQogICAgZEhuZWc9OC4wZTQsICAgICAgIyBKL21vbCwgLURlbHRhSAogICAgcmhvQ3A9NDAwMC4wLCAgICAgIyBKLyhMIEspLCBwcm9jZXNzLXNpZGUgdm9sdW1ldHJpYyBoZWF0IGNhcGFjaXR5CiAgICByaG9DcF9qPTQwMDAuMCwgICAjIEovKEwgSyksIGphY2tldC1zaWRlIHZvbHVtZXRyaWMgaGVhdCBjYXBhY2l0eQogICAgVmo9MC4yLCAgICAgICAgICAgIyBMLCBqYWNrZXQgdm9sdW1lCiAgICBUamluPTMwMC4wLCAgICAgICAjIEssIGNvb2xhbnQgaW5sZXQgdGVtcGVyYXR1cmUKICAgIFVBMD0xNi4wLCAgICAgICAgICMgSi8ocyBLKSwgY2xlYW4gb3ZlcmFsbCBjb2VmZmljaWVudDsgZm91bHMgZG93bndhcmQKICAgIHRhdV9mb3VsPTYuMCAqIDM2MDAuMCwgICMgcywgZm91bGluZyB0aW1lIGNvbnN0YW50CikKCiMgUHVibGlzaGVkIGNvbnRyb2xsZXIgc2V0dGluZ3MgKGtub3duIHRvIHRoZSB0d2luOyBwYXJ0IG9mIHBsYW50IGRvY3VtZW50YXRpb24pCkNUUkwgPSBkaWN0KAogICAgVF9zcD0zNzAuMCwgICAgICAgIyBLLCB0ZW1wZXJhdHVyZSBzZXRwb2ludAogICAgRmpfbWluPTAuMDAwNSwgICAgIyBML3MKICAgIEZqX21heD0wLjAwOCwgICAgICMgTC9zCiAgICBGal9iaWFzPTAuMDAzLCAgICAjIEwvcwogICAgS2M9MS4wZS00LCAgICAgICAgIyBMLyhzIEspLCBwcm9wb3J0aW9uYWwgZ2FpbiAocmV2ZXJzZS1hY3RpbmcpCiAgICB0YXVJPTMwMC4wLCAgICAgICAjIHMsIGludGVncmFsIHRpbWUKKQoKIyBUd2luJ3Mgbm9taW5hbCAod3JvbmcgYnV0IHJlYXNvbmFibGUpIHBhcmFtZXRlcnMKVFdJTl9QID0gZGljdCgKICAgIGswPTIuODVlNywgICAgICAgICMgLTUlIHZzIHRydXRoCiAgICBFYVI9Nzk2MC4wLCAgICAgICAjIC0wLjUlIHZzIHRydXRoCiAgICBkSG5lZz03Ljg0ZTQsICAgICAjIC0yJSB2cyB0cnV0aAogICAgcmhvQ3A9NDAwMC4wLAogICAgcmhvQ3Bfaj00MDAwLjAsCiAgICBWPTEuMCwKICAgIFZqPTAuMiwKICAgIENfQTA9OC4wLCAgICAgICAgICMgcHVibGlzaGVkIGZlZWQgY29uY2VudHJhdGlvbgogICAgVGppbj0zMDAuMCwgICAgICAgIyBwdWJsaXNoZWQgY29vbGFudCBpbmxldCB0ZW1wZXJhdHVyZQogICAgVUFfaW5pdD0xNi4wLCAgICAgIyBjbGVhbiB2YWx1ZSBhc3N1bWVkIGtub3duOyBmb3VsaW5nIHJhdGUgdW5rbm93bgopCgoKZGVmIGtfb2ZfVChULCBrMCwgRWFSKToKICAgIHJldHVybiBrMCAqIG5wLmV4cChucC5jbGlwKC1FYVIgLyBucC5tYXhpbXVtKFQsIDEuMCksIC03MDAuMCwgMC4wKSkKCgojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQojIFN0ZWFkeS1zdGF0ZSBhbmFseXNpcyBoZWxwZXJzIChwdWJsaWM7IHVzZWQgYnkgdGhlIHdhbGt0aHJvdWdoIGFuZCBTY2VuZSA0KQojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQpkZWYgcXNzX2phY2tldF9UKFQsIFVBLCBGaiwgcCk6CiAgICAiIiJRdWFzaS1zdGVhZHkgamFja2V0IHRlbXBlcmF0dXJlIGZyb20gdGhlIGphY2tldCBlbmVyZ3kgYmFsYW5jZS4iIiIKICAgIGEgPSBGagogICAgYiA9IFVBIC8gcFsicmhvQ3BfaiJdCiAgICByZXR1cm4gKGEgKiBwWyJUamluIl0gKyBiICogVCkgLyAoYSArIGIpCgoKZGVmIGhlYXRfcmVzaWR1YWwoVCwgVUEsIEZqLCBwKToKICAgICIiIlN0ZWFkeS1zdGF0ZSByZWFjdG9yIGVuZXJneSByZXNpZHVhbDsgaXRzIHJvb3RzIGFyZSBzdGVhZHkgc3RhdGVzLiIiIgogICAgdGF1ID0gcFsiViJdIC8gcFsiRiJdCiAgICBrID0ga19vZl9UKFQsIHBbImswIl0sIHBbIkVhUiJdKQogICAgQ19BID0gcFsiQ19BMCJdIC8gKDEuMCArIGsgKiB0YXUpCiAgICBUX2ogPSBxc3NfamFja2V0X1QoVCwgVUEsIEZqLCBwKQogICAgcmV0dXJuICgocFsiRiJdIC8gcFsiViJdKSAqIChwWyJUMCJdIC0gVCkKICAgICAgICAgICAgKyAocFsiZEhuZWciXSAvIHBbInJob0NwIl0pICogayAqIENfQQogICAgICAgICAgICAtIChVQSAvIChwWyJWIl0gKiBwWyJyaG9DcCJdKSkgKiAoVCAtIFRfaikpCgoKZGVmIGZpbmRfVF9yb290cyhVQSwgRmosIHAsIFRfbG89MzAwLjAsIFRfaGk9NjUwLjAsIG49MjAwMCk6CiAgICAiIiJSb2J1c3Qgc3RlYWR5LXN0YXRlIHRlbXBlcmF0dXJlcyB2aWEgcmVzaWR1YWwgc2lnbi1jaGFuZ2Ugc2Nhbi4iIiIKICAgIFRzID0gbnAubGluc3BhY2UoVF9sbywgVF9oaSwgbikKICAgIFIgPSBucC5hcnJheShbaGVhdF9yZXNpZHVhbChULCBVQSwgRmosIHApIGZvciBUIGluIFRzXSkKICAgIHJvb3RzID0gW10KICAgIGZvciBpIGluIHJhbmdlKG4gLSAxKToKICAgICAgICBpZiBSW2ldID09IDAuMDoKICAgICAgICAgICAgcm9vdHMuYXBwZW5kKFRzW2ldKQogICAgICAgIGVsaWYgUltpXSAqIFJbaSArIDFdIDwgMC4wOgogICAgICAgICAgICBhLCBiID0gVHNbaV0sIFRzW2kgKyAxXQogICAgICAgICAgICBmb3IgXyBpbiByYW5nZSg1MCk6CiAgICAgICAgICAgICAgICBtID0gMC41ICogKGEgKyBiKQogICAgICAgICAgICAgICAgaWYgaGVhdF9yZXNpZHVhbChhLCBVQSwgRmosIHApICogaGVhdF9yZXNpZHVhbChtLCBVQSwgRmosIHApIDw9IDA6CiAgICAgICAgICAgICAgICAgICAgYiA9IG0KICAgICAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICAgICAgYSA9IG0KICAgICAgICAgICAgcm9vdHMuYXBwZW5kKDAuNSAqIChhICsgYikpCiAgICByZXR1cm4gbnAuYXJyYXkocm9vdHMpCgoKZGVmIGZ1bGxfc3RhdGUoVCwgVUEsIEZqLCBwKToKICAgICIiIkxpZnQgYSBzdGVhZHktc3RhdGUgdGVtcGVyYXR1cmUgdG8gW0NfQSwgVCwgVF9qXS4iIiIKICAgIHRhdSA9IHBbIlYiXSAvIHBbIkYiXQogICAgayA9IGtfb2ZfVChULCBwWyJrMCJdLCBwWyJFYVIiXSkKICAgIENfQSA9IHBbIkNfQTAiXSAvICgxLjAgKyBrICogdGF1KQogICAgcmV0dXJuIG5wLmFycmF5KFtDX0EsIFQsIHFzc19qYWNrZXRfVChULCBVQSwgRmosIHApXSkKCgpkZWYgdWFfb2ZfdCh0LCBwKToKICAgIHJldHVybiBwWyJVQTAiXSAqIG5wLmV4cCgtdCAvIHBbInRhdV9mb3VsIl0pCgoKZGVmIGNvbnRyb2xsZXIoVF9tZWFzLCBJLCBjKToKICAgICIiIlJldmVyc2UtYWN0aW5nIFBJOiBob3QgLT4gbW9yZSBjb29sYW50LiBSZXR1cm5zIChGaiwgZXJyb3IpLiIiIgogICAgZSA9IFRfbWVhcyAtIGNbIlRfc3AiXQogICAgdSA9IGNbIkZqX2JpYXMiXSArIGNbIktjIl0gKiAoZSArIEkgLyBjWyJ0YXVJIl0pCiAgICByZXR1cm4gZmxvYXQobnAuY2xpcCh1LCBjWyJGal9taW4iXSwgY1siRmpfbWF4Il0pKSwgZQoKCmRlZiBwbGFudF9yaHModCwgeCwgcCwgYywgVF9tZWFzKToKICAgICIiInggPSBbQ19BLCBULCBUX2osIEldLiBSZXR1cm5zIChkeGR0LCBGaiwgVUEpLiIiIgogICAgQ19BLCBULCBUX2osIEkgPSB4CiAgICBVQSA9IHVhX29mX3QodCwgcCkKICAgIEZqLCBlID0gY29udHJvbGxlcihUX21lYXMsIEksIGMpCiAgICBpZiAoRmogPD0gY1siRmpfbWluIl0gYW5kIGUgPCAwKSBvciAoRmogPj0gY1siRmpfbWF4Il0gYW5kIGUgPiAwKToKICAgICAgICBkSSA9IDAuMCAgIyBhbnRpLXdpbmR1cAogICAgZWxzZToKICAgICAgICBkSSA9IGUKICAgIGsgPSBrX29mX1QoVCwgcFsiazAiXSwgcFsiRWFSIl0pCiAgICBkQ19BID0gKHBbIkYiXSAvIHBbIlYiXSkgKiAocFsiQ19BMCJdIC0gQ19BKSAtIGsgKiBDX0EKICAgIGRUID0gKChwWyJGIl0gLyBwWyJWIl0pICogKHBbIlQwIl0gLSBUKQogICAgICAgICAgKyAocFsiZEhuZWciXSAvIHBbInJob0NwIl0pICogayAqIENfQQogICAgICAgICAgLSAoVUEgLyAocFsiViJdICogcFsicmhvQ3AiXSkpICogKFQgLSBUX2opKQogICAgZFRfaiA9ICgoRmogLyBwWyJWaiJdKSAqIChwWyJUamluIl0gLSBUX2opCiAgICAgICAgICAgICsgKFVBIC8gKHBbIlZqIl0gKiBwWyJyaG9DcF9qIl0pKSAqIChUIC0gVF9qKSkKICAgIHJldHVybiBucC5hcnJheShbZENfQSwgZFQsIGRUX2osIGRJXSksIEZqLCBVQQoKCmNsYXNzIFBsYW50OgogICAgIiIiVGhlIGhpZGRlbiBwcm9jZXNzLiBPbmx5IGBzdHJlYW1gIGRhdGEgbGVhdmVzIHRoaXMgb2JqZWN0LiIiIgoKICAgIGRlZiBfX2luaXRfXyhzZWxmLCBwPU5vbmUsIGM9Tm9uZSwgc2VlZD0wLAogICAgICAgICAgICAgICAgIHNpZ21hX1Q9MC4zLCBzaWdtYV9Uaj0wLjMsIHNpZ21hX0Y9MWUtNiwgc2lnbWFfVDA9MC4yLAogICAgICAgICAgICAgICAgIGxhYl9pbnRlcnZhbD0xMjAwLjAsIGxhYl9kZWxheT02MDAuMCwgc2lnbWFfbGFiPTAuMDUpOgogICAgICAgIHNlbGYucCA9IGRpY3QoUExBTlRfUCBpZiBwIGlzIE5vbmUgZWxzZSBwKQogICAgICAgIHNlbGYuYyA9IGRpY3QoQ1RSTCBpZiBjIGlzIE5vbmUgZWxzZSBjKQogICAgICAgIHNlbGYucm5nID0gbnAucmFuZG9tLmRlZmF1bHRfcm5nKHNlZWQpCiAgICAgICAgc2VsZi5zaWdtYV9UID0gc2lnbWFfVAogICAgICAgIHNlbGYuc2lnbWFfVGogPSBzaWdtYV9UagogICAgICAgIHNlbGYuc2lnbWFfRiA9IHNpZ21hX0YKICAgICAgICBzZWxmLnNpZ21hX1QwID0gc2lnbWFfVDAKICAgICAgICBzZWxmLmxhYl9pbnRlcnZhbCA9IGxhYl9pbnRlcnZhbAogICAgICAgIHNlbGYubGFiX2RlbGF5ID0gbGFiX2RlbGF5CiAgICAgICAgc2VsZi5zaWdtYV9sYWIgPSBzaWdtYV9sYWIKICAgICAgICBzZWxmLnNlbnNvcl9iaWFzX1QgPSAwLjAKICAgICAgICBzZWxmLmZlZWRfVF9zdGVwID0gMC4wCiAgICAgICAgIyBzZXR0bGUgbmVhciB0aGUgaWduaXRlZCBicmFuY2ggdW5kZXIgY29udHJvbCBiZWZvcmUgdCA9IDAKICAgICAgICB4ID0gbnAuYXJyYXkoWzAuNzcyLCAzNzQuMCwgMzM1LjAsIDAuMF0pCiAgICAgICAgc29sID0gc29sdmVfaXZwKGxhbWJkYSB0LCB4eDogcGxhbnRfcmhzKHQsIHh4LCBzZWxmLnAsIHNlbGYuYywgeHhbMV0pWzBdLAogICAgICAgICAgICAgICAgICAgICAgICAoMCwgMzYwMC4wKSwgeCwgbWV0aG9kPSJSYWRhdSIsCiAgICAgICAgICAgICAgICAgICAgICAgIHJ0b2w9MWUtOCwgYXRvbD0xZS0xMCkKICAgICAgICBzZWxmLnggPSBzb2wueVs6LCAtMV0KICAgICAgICBzZWxmLnQgPSAwLjAKICAgICAgICBzZWxmLl9sYWJfcXVldWUgPSBbXSAgIyAoZGVsaXZlcl9hdCwgdmFsdWUpIHBlbmRpbmcgbGFiIHJlc3VsdHMKICAgICAgICBzZWxmLl9uZXh0X2xhYiA9IDAuMAoKICAgIGRlZiBzdGVwKHNlbGYsIGR0KToKICAgICAgICAiIiJBZHZhbmNlIGR0IHNlY29uZHM7IHJldHVybiBvbmUgcHVibGlzaGVkIHNhbXBsZSBkaWN0LiIiIgogICAgICAgIHAsIGMgPSBzZWxmLnAsIHNlbGYuYwogICAgICAgIFRfcHViID0gc2VsZi54WzFdICsgc2VsZi5ybmcubm9ybWFsKDAsIHNlbGYuc2lnbWFfVCkgKyBzZWxmLnNlbnNvcl9iaWFzX1QKICAgICAgICBzb2wgPSBzb2x2ZV9pdnAoCiAgICAgICAgICAgIGxhbWJkYSB0dCwgeHg6IHBsYW50X3Jocyh0dCwgeHgsIHAsIGMsIFRfcHViKVswXSwKICAgICAgICAgICAgKHNlbGYudCwgc2VsZi50ICsgZHQpLCBzZWxmLngsCiAgICAgICAgICAgIG1ldGhvZD0iUmFkYXUiLCBydG9sPTFlLTgsIGF0b2w9MWUtMTApCiAgICAgICAgc2VsZi54ID0gc29sLnlbOiwgLTFdCiAgICAgICAgc2VsZi50ICs9IGR0CiAgICAgICAgXywgRmosIFVBID0gcGxhbnRfcmhzKHNlbGYudCwgc2VsZi54LCBwLCBjLCBUX3B1YikKICAgICAgICAjIHNjaGVkdWxlIGxhYiBzYW1wbGVzIChzYW1wbGVkIG5vdywgZGVsaXZlcmVkIGFmdGVyIHRoZSBkZWxheSkKICAgICAgICBpZiBzZWxmLnQgPj0gc2VsZi5fbmV4dF9sYWI6CiAgICAgICAgICAgIHNlbGYuX2xhYl9xdWV1ZS5hcHBlbmQoCiAgICAgICAgICAgICAgICAoc2VsZi50ICsgc2VsZi5sYWJfZGVsYXksCiAgICAgICAgICAgICAgICAgc2VsZi54WzBdICsgc2VsZi5ybmcubm9ybWFsKDAsIHNlbGYuc2lnbWFfbGFiKSkpCiAgICAgICAgICAgIHNlbGYuX25leHRfbGFiICs9IHNlbGYubGFiX2ludGVydmFsCiAgICAgICAgc2FtcGxlID0gZGljdCgKICAgICAgICAgICAgdD1zZWxmLnQsCiAgICAgICAgICAgIFQ9VF9wdWIsCiAgICAgICAgICAgIFRfaj1zZWxmLnhbMl0gKyBzZWxmLnJuZy5ub3JtYWwoMCwgc2VsZi5zaWdtYV9UaiksCiAgICAgICAgICAgIEY9cFsiRiJdICsgc2VsZi5ybmcubm9ybWFsKDAsIHNlbGYuc2lnbWFfRiksCiAgICAgICAgICAgIFQwPXBbIlQwIl0gKyBzZWxmLmZlZWRfVF9zdGVwICsgc2VsZi5ybmcubm9ybWFsKDAsIHNlbGYuc2lnbWFfVDApLAogICAgICAgICAgICBGaj1GaiwKICAgICAgICApCiAgICAgICAgbGFicyA9IFt2IGZvciAodGQsIHYpIGluIHNlbGYuX2xhYl9xdWV1ZSBpZiB0ZCA8PSBzZWxmLnRdCiAgICAgICAgc2VsZi5fbGFiX3F1ZXVlID0gWyh0ZCwgdikgZm9yICh0ZCwgdikgaW4gc2VsZi5fbGFiX3F1ZXVlIGlmIHRkID4gc2VsZi50XQogICAgICAgIGlmIGxhYnM6CiAgICAgICAgICAgIHNhbXBsZVsibGFiX0NfQSJdID0gbGFic1stMV0KICAgICAgICAgICAgc2FtcGxlWyJsYWJfdF9zYW1wbGUiXSA9IHNlbGYudCAtIHNlbGYubGFiX2RlbGF5CiAgICAgICAgIyBoaWRkZW4gdHJ1dGgsIGZvciBzY29yaW5nIG9ubHkgLS0gbmV2ZXIgZ2l2ZW4gdG8gdGhlIHR3aW4KICAgICAgICBzYW1wbGVbIl90cnVlIl0gPSBkaWN0KENfQT1zZWxmLnhbMF0sIFQ9c2VsZi54WzFdLCBUX2o9c2VsZi54WzJdLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgVUE9VUEpCiAgICAgICAgcmV0dXJuIHNhbXBsZQoKCmRlZiB0d2luX3Jocyh4YSwgRmosIEYsIFQwLCB0cCk6CiAgICAiIiJUd2luJ3MgbW9kZWwgb2YgdGhlIGF1Z21lbnRlZCBzdGF0ZSBbQ19BLCBULCBUX2osIFVBXS4iIiIKICAgIENfQSwgVCwgVF9qLCBVQSA9IHhhCiAgICBrID0ga19vZl9UKFQsIHRwWyJrMCJdLCB0cFsiRWFSIl0pCiAgICBkQ19BID0gKEYgLyB0cFsiViJdKSAqICh0cFsiQ19BMCJdIC0gQ19BKSAtIGsgKiBDX0EgICAjIENfQTAgcHVibGlzaGVkCiAgICBkVCA9ICgoRiAvIHRwWyJWIl0pICogKFQwIC0gVCkKICAgICAgICAgICsgKHRwWyJkSG5lZyJdIC8gdHBbInJob0NwIl0pICogayAqIENfQQogICAgICAgICAgLSAoVUEgLyAodHBbIlYiXSAqIHRwWyJyaG9DcCJdKSkgKiAoVCAtIFRfaikpCiAgICBkVF9qID0gKChGaiAvIHRwWyJWaiJdKSAqICh0cFsiVGppbiJdIC0gVF9qKSAgICAgICAgICAjIFRqaW4gcHVibGlzaGVkCiAgICAgICAgICAgICsgKFVBIC8gKHRwWyJWaiJdICogdHBbInJob0NwX2oiXSkpICogKFQgLSBUX2opKQogICAgcmV0dXJuIG5wLmFycmF5KFtkQ19BLCBkVCwgZFRfaiwgMC4wXSkKCgpjbGFzcyBUd2luRUtGOgogICAgIiIiVGhlIGRpZ2l0YWwgdHdpbjogRUtGIG9uIFtDX0EsIFQsIFRfaiwgVUFdIGZlZCBvbmx5IGJ5IHRoZSBkYXRhIHN0cmVhbS4iIiIKCiAgICBkZWYgX19pbml0X18oc2VsZiwgdHA9Tm9uZSwgYz1Ob25lLCBkdD0xMC4wLAogICAgICAgICAgICAgICAgIHNpZ21hX1Q9MC4zLCBzaWdtYV9Uaj0wLjMsIHNpZ21hX2xhYj0wLjA1LAogICAgICAgICAgICAgICAgIHFfVUE9MS4wZS01LCBsYWJfZGVsYXk9NjAwLjApOgogICAgICAgIHNlbGYudHAgPSBkaWN0KFRXSU5fUCBpZiB0cCBpcyBOb25lIGVsc2UgdHApCiAgICAgICAgc2VsZi5jID0gZGljdChDVFJMIGlmIGMgaXMgTm9uZSBlbHNlIGMpCiAgICAgICAgc2VsZi5kdCA9IGR0CiAgICAgICAgc2VsZi5sYWJfZGVsYXkgPSBsYWJfZGVsYXkKICAgICAgICAjIHN0YXRlOiBzdGFydCBhdCBub21pbmFsIGNsZWFuIHN0ZWFkeSBzdGF0ZSBndWVzcwogICAgICAgIHNlbGYueCA9IG5wLmFycmF5KFsxLjAsIDM2OC4wLCAzMzUuMCwgc2VsZi50cFsiVUFfaW5pdCJdXSkKICAgICAgICBzZWxmLlBtID0gbnAuZGlhZyhbMC41KioyLCAzLjAqKjIsIDMuMCoqMiwgMy4wKioyXSkKICAgICAgICBzZWxmLlIgPSBucC5kaWFnKFtzaWdtYV9UKioyLCBzaWdtYV9UaioqMl0pCiAgICAgICAgc2VsZi5SX2xhYiA9IG5wLmFycmF5KFtbc2lnbWFfbGFiKioyXV0pCiAgICAgICAgcSA9IG5wLmRpYWcoWzFlLTYsIDFlLTQsIDFlLTQsIHFfVUFdKSAqIGR0CiAgICAgICAgc2VsZi5RID0gcQogICAgICAgIHNlbGYuSV9jdHJsID0gMC4wCiAgICAgICAgc2VsZi5oaXN0ID0gW10gICMgKHQsIHgsIFBtLCBGaiwgRiwgVDApIHJpbmcgYnVmZmVyIGZvciBsYWIgcmVwcm9jZXNzaW5nCiAgICAgICAgc2VsZi5yZXNpZF9UID0gW10KICAgICAgICBzZWxmLnJlc2lkX1RqID0gW10KICAgICAgICBzZWxmLmxhYl9pbm5vdiA9IFtdICAjICh0X2RlbGl2ZXIsIGlubm92YXRpb24sIHN0ZCkgcGVyIGxhYiBzYW1wbGUKCiAgICBkZWYgX2phY29iaWFuKHNlbGYsIHhhLCBGaiwgRiwgVDAsIGg9MWUtNik6CiAgICAgICAgbiA9IDQKICAgICAgICBKID0gbnAuemVyb3MoKG4sIG4pKQogICAgICAgIGYwID0gdHdpbl9yaHMoeGEsIEZqLCBGLCBUMCwgc2VsZi50cCkKICAgICAgICBmb3IgaiBpbiByYW5nZShuKToKICAgICAgICAgICAgZHggPSBucC56ZXJvcyhuKQogICAgICAgICAgICBkeFtqXSA9IGggKiBtYXgoYWJzKHhhW2pdKSwgMS4wKQogICAgICAgICAgICBKWzosIGpdID0gKHR3aW5fcmhzKHhhICsgZHgsIEZqLCBGLCBUMCwgc2VsZi50cCkgLSBmMCkgLyBkeFtqXQogICAgICAgIHJldHVybiBKCgogICAgZGVmIF9wcmVkaWN0KHNlbGYsIHgsIFBtLCBGaiwgRiwgVDApOgogICAgICAgIHNvbCA9IHNvbHZlX2l2cChsYW1iZGEgdCwgeGE6IHR3aW5fcmhzKHhhLCBGaiwgRiwgVDAsIHNlbGYudHApLAogICAgICAgICAgICAgICAgICAgICAgICAoMCwgc2VsZi5kdCksIHgsIG1ldGhvZD0iUmFkYXUiLAogICAgICAgICAgICAgICAgICAgICAgICBydG9sPTFlLTYsIGF0b2w9MWUtOCkKICAgICAgICB4cCA9IHNvbC55WzosIC0xXQogICAgICAgIEogPSBzZWxmLl9qYWNvYmlhbih4cCwgRmosIEYsIFQwKSAgICMgbGluZWFyaXplIGF0IHRoZSBwcmVkaWN0aW9uCiAgICAgICAgIyBkaXNjcmV0ZSB0cmFuc2l0aW9uOiBFdWxlciBpcyBhY2N1cmF0ZSBoZXJlICh8SnwqZHQgfiAxZS0yKSBhbmQKICAgICAgICAjIGZhciBjaGVhcGVyIHRoYW4gZXhwbTsgdmVyaWZpZWQgYWdhaW5zdCBleHBtIGluIGFuYWx5c2lzL2JlbmNoLnB5CiAgICAgICAgUGhpID0gbnAuZXllKDQpICsgSiAqIHNlbGYuZHQKICAgICAgICBQcCA9IFBoaSBAIFBtIEAgUGhpLlQgKyBzZWxmLlEKICAgICAgICByZXR1cm4geHAsIFBwCgogICAgZGVmIF91cGRhdGVfVChzZWxmLCB4cCwgUHAsIHkpOgogICAgICAgIEggPSBucC5hcnJheShbWzAuLCAxLiwgMC4sIDAuXSwgWzAuLCAwLiwgMS4sIDAuXV0pCiAgICAgICAgciA9IHkgLSBIIEAgeHAKICAgICAgICBTID0gSCBAIFBwIEAgSC5UICsgc2VsZi5SCiAgICAgICAgSyA9IFBwIEAgSC5UIEAgbnAubGluYWxnLmludihTKQogICAgICAgIHJldHVybiB4cCArIEsgQCByLCAobnAuZXllKDQpIC0gSyBAIEgpIEAgUHAsIHIKCiAgICBkZWYgX3VwZGF0ZV9sYWIoc2VsZiwgeHAsIFBwLCBjX21lYXMpOgogICAgICAgIEggPSBucC5hcnJheShbWzEuLCAwLiwgMC4sIDAuXV0pCiAgICAgICAgciA9IG5wLmFycmF5KFtjX21lYXNdKSAtIEggQCB4cAogICAgICAgIFMgPSBIIEAgUHAgQCBILlQgKyBzZWxmLlJfbGFiCiAgICAgICAgSyA9IFBwIEAgSC5UIEAgbnAubGluYWxnLmludihTKQogICAgICAgIHJldHVybiB4cCArIEsgQCByLCAobnAuZXllKDQpIC0gSyBAIEgpIEAgUHAKCiAgICBkZWYgc3RlcChzZWxmLCBzYW1wbGUpOgogICAgICAgICIiIkNvbnN1bWUgb25lIHB1Ymxpc2hlZCBzYW1wbGU7IHJldHVybiB0aGUgdHdpbidzIHN0YXRlIGVzdGltYXRlLiIiIgogICAgICAgIGR0LCB0cCwgYyA9IHNlbGYuZHQsIHNlbGYudHAsIHNlbGYuYwogICAgICAgICMgdGhlIHR3aW4gcnVucyB0aGUgcHVibGlzaGVkIGNvbnRyb2xsZXIgb24gdGhlIHB1Ymxpc2hlZCBtZWFzdXJlbWVudAogICAgICAgIEZqLCBlID0gY29udHJvbGxlcihzYW1wbGVbIlQiXSwgc2VsZi5JX2N0cmwsIGMpCiAgICAgICAgaWYgKEZqIDw9IGNbIkZqX21pbiJdIGFuZCBlIDwgMCkgb3IgKEZqID49IGNbIkZqX21heCJdIGFuZCBlID4gMCk6CiAgICAgICAgICAgIHBhc3MKICAgICAgICBlbHNlOgogICAgICAgICAgICBzZWxmLklfY3RybCArPSBlICogZHQKICAgICAgICB4cCwgUHAgPSBzZWxmLl9wcmVkaWN0KHNlbGYueCwgc2VsZi5QbSwgRmosIHNhbXBsZVsiRiJdLCBzYW1wbGVbIlQwIl0pCiAgICAgICAgeSA9IG5wLmFycmF5KFtzYW1wbGVbIlQiXSwgc2FtcGxlWyJUX2oiXV0pCiAgICAgICAgeCwgUG0sIHIgPSBzZWxmLl91cGRhdGVfVCh4cCwgUHAsIHkpCiAgICAgICAgc2VsZi5yZXNpZF9ULmFwcGVuZChyWzBdKQogICAgICAgIHNlbGYucmVzaWRfVGouYXBwZW5kKHJbMV0pCiAgICAgICAgaWYgImxhYl9DX0EiIGluIHNhbXBsZToKICAgICAgICAgICAgeCwgUG0gPSBzZWxmLl9yZXByb2Nlc3NfbGFiKHgsIFBtLCBGaiwgc2FtcGxlKQogICAgICAgIHNlbGYueCwgc2VsZi5QbSA9IHgsIFBtCiAgICAgICAgc2VsZi5oaXN0LmFwcGVuZChkaWN0KHQ9c2FtcGxlWyJ0Il0sIHg9eC5jb3B5KCksIFBtPVBtLmNvcHkoKSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgRmo9RmosIEY9c2FtcGxlWyJGIl0sIFQwPXNhbXBsZVsiVDAiXSwgeT15LmNvcHkoKSkpCiAgICAgICAgIyBrZWVwIDQwIG1pbiBvZiBoaXN0b3J5IChjb3ZlcnMgdGhlIGxhYiBkZWxheSkKICAgICAgICB3aGlsZSBzZWxmLmhpc3QgYW5kIHNlbGYuaGlzdFswXVsidCJdIDwgc2FtcGxlWyJ0Il0gLSAyNDAwLjA6CiAgICAgICAgICAgIHNlbGYuaGlzdC5wb3AoMCkKICAgICAgICByZXR1cm4gZGljdChDX0E9eFswXSwgVD14WzFdLCBUX2o9eFsyXSwgVUE9eFszXSwKICAgICAgICAgICAgICAgICAgICByZXNpZF9UPXJbMF0sIHJlc2lkX1RqPXJbMV0sIEZqPUZqKQoKICAgIGRlZiBfcmVwcm9jZXNzX2xhYihzZWxmLCB4X25vdywgUG1fbm93LCBGal9ub3csIHNhbXBsZSk6CiAgICAgICAgIiIiRXhhY3QgZml4ZWQtbGFnIHJlcHJvY2Vzc2luZzogYXBwbHkgdGhlIGRlbGF5ZWQgbGFiIHNhbXBsZSBhdCBpdHMKICAgICAgICBzYW1wbGUgdGltZSwgdGhlbiByZS1ydW4gcHJlZGljdCArIFQvVF9qIHVwZGF0ZXMgZm9yd2FyZC4iIiIKICAgICAgICB0X3MgPSBzYW1wbGVbImxhYl90X3NhbXBsZSJdCiAgICAgICAgaWR4ID0gbmV4dCgoaSBmb3IgaSwgaCBpbiBlbnVtZXJhdGUoc2VsZi5oaXN0KSBpZiBoWyJ0Il0gPj0gdF9zKSwgTm9uZSkKICAgICAgICBpZiBpZHggaXMgTm9uZTogICMgc2FtcGxlIG9sZGVyIHRoYW4gaGlzdG9yeTogYXBwbHkgbm93LCBmbGFnZ2VkIGxhdGUKICAgICAgICAgICAgcmV0dXJuIHNlbGYuX3VwZGF0ZV9sYWIoeF9ub3csIFBtX25vdywgc2FtcGxlWyJsYWJfQ19BIl0pCiAgICAgICAgaCA9IHNlbGYuaGlzdFtpZHhdCiAgICAgICAgIyByZWNvcmQgdGhlIGxhYiBpbm5vdmF0aW9uIEJFRk9SRSB0aGUgdXBkYXRlOiB0aGUgaW5kZXBlbmRlbnQgY2hlY2sKICAgICAgICAjIHVzZWQgZm9yIGZhdWx0IGRldGVjdGlvbiAodGhlIHVwZGF0ZSBpdHNlbGYgd291bGQgaGlkZSBpdCkKICAgICAgICBpbm5vdiA9IGZsb2F0KHNhbXBsZVsibGFiX0NfQSJdIC0gaFsieCJdWzBdKQogICAgICAgIGlubm92X3N0ZCA9IGZsb2F0KG5wLnNxcnQoaFsiUG0iXVswLCAwXSArIHNlbGYuUl9sYWJbMCwgMF0pKQogICAgICAgIHNlbGYubGFiX2lubm92LmFwcGVuZCgoc2FtcGxlWyJ0Il0sIGlubm92LCBpbm5vdl9zdGQpKQogICAgICAgIHgsIFBtID0gc2VsZi5fdXBkYXRlX2xhYihoWyJ4Il0sIGhbIlBtIl0sIHNhbXBsZVsibGFiX0NfQSJdKQogICAgICAgIHNlbGYuaGlzdFtpZHhdID0gZGljdChoLCB4PXguY29weSgpLCBQbT1QbS5jb3B5KCkpCiAgICAgICAgZm9yIGogaW4gcmFuZ2UoaWR4ICsgMSwgbGVuKHNlbGYuaGlzdCkpOgogICAgICAgICAgICBoaiA9IHNlbGYuaGlzdFtqXQogICAgICAgICAgICB4cCwgUHAgPSBzZWxmLl9wcmVkaWN0KHgsIFBtLCBoalsiRmoiXSwgaGpbIkYiXSwgaGpbIlQwIl0pCiAgICAgICAgICAgIHgsIFBtLCBfID0gc2VsZi5fdXBkYXRlX1QoeHAsIFBwLCBoalsieSJdKQogICAgICAgICAgICBzZWxmLmhpc3Rbal0gPSBkaWN0KGhqLCB4PXguY29weSgpLCBQbT1QbS5jb3B5KCkpCiAgICAgICAgeHAsIFBwID0gc2VsZi5fcHJlZGljdCh4LCBQbSwgRmpfbm93LCBzYW1wbGVbIkYiXSwgc2FtcGxlWyJUMCJdKQogICAgICAgIHJldHVybiBzZWxmLl91cGRhdGVfbGFiKHhwLCBQcCwgc2FtcGxlWyJsYWJfQ19BIl0pCg==").decode("utf-8")
    _mod = _types.ModuleType('cstr_model')
    exec(compile(MODEL_SRC, "cstr_model.py", "exec"), _mod.__dict__)
    _sys.modules["cstr_model"] = _mod
    import cstr_model as M
    def figure(data, layout=None, **kw):
        return go.Figure(data=data, layout=layout or kw)
    return (mo, np, go, solve_ivp, M, MODEL_SRC, figure)


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
def _(M, go, mo, np, solve_ivp):
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
        _sol = solve_ivp(lambda tt, xa: M.twin_rhs(np.array([xa[0], xa[1], xa[2], 16.0]), _Fj_m, _pub['F'], _pub['T0'], M.TWIN_P)[:3], (0, _DT), _x_m[:3], method='Radau', rtol=1e-06, atol=1e-08)
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
def _(M, go, np, solve_ivp):
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
        _sol = solve_ivp(lambda tt, xx: M.twin_rhs(xx, _Fj, M.PLANT_P['F'], M.PLANT_P['T0'], M.TWIN_P), (0, _t_grid[1] - _t_grid[0]), _xa, method='Radau', rtol=1e-06, atol=1e-08)
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

