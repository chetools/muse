#!/usr/bin/env python3
"""One-off migration + probe for the 2.4.0 duration_stats table.

Applies the CREATE TABLE from schema.sql to the live hw-grading D1
database through the Cloudflare API (registered custom.cloudflare
credential, surrogate flow, same as deploy.py), then optionally runs
one extra SQL statement given on the command line (used to remove
the calibration-test rows after the live smoke test). Prints only
status/result metadata — never any credential.
"""
import json, sys, urllib.request, urllib.error
sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import add_surrogate_to_request, read_response_body

ACCOUNT = "8d4f9c220c09468e237d76c25678d87d"
BASE = "https://api.cloudflare.com/client/v4"

CREATE_SQL = (
    "CREATE TABLE IF NOT EXISTS duration_stats ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " created_at TEXT, pkg TEXT, context TEXT,"
    " audio_s REAL, video_s REAL, diff_s REAL, abs_diff_s REAL)"
)


def call(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, method=method, data=data)
    req.add_header("Accept", "application/json")
    if data:
        req.add_header("Content-Type", "application/json")
    add_surrogate_to_request(req, "custom.cloudflare",
                             allowed_hosts=["api.cloudflare.com"])
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = read_response_body(resp)
            return resp.status, json.loads(raw.decode()) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw.decode()) if raw else {}
        except Exception:
            return e.code, {"raw": raw.decode(errors="replace")}


def main():
    status, data = call("GET", f"/accounts/{ACCOUNT}/d1/database?name=hw-grading")
    if status != 200 or not data.get("result"):
        print("database lookup failed:", status, data.get("errors"))
        sys.exit(1)
    dbid = data["result"][0]["uuid"]
    print("database:", data["result"][0].get("name"), dbid)
    sql = sys.argv[1] if len(sys.argv) > 1 else CREATE_SQL
    status, data = call("POST", f"/accounts/{ACCOUNT}/d1/database/{dbid}/query",
                        {"sql": sql})
    print("query status:", status, "success:", data.get("success"),
          "errors:", data.get("errors"))
    if status != 200 or not data.get("success"):
        sys.exit(1)
    for r in data.get("result") or []:
        print("result rows:", len(r.get("results") or []),
              "meta:", {k: (r.get("meta") or {}).get(k)
                        for k in ("changes", "rows_read", "rows_written")})
        for row in (r.get("results") or [])[:5]:
            print("row:", row)


if __name__ == "__main__":
    main()
