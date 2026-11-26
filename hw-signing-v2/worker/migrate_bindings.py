#!/usr/bin/env python3
"""One-off migration for the 2.7.3 job_bindings table.

Applies the CREATE TABLE from schema.sql to every D1 database in
the account that holds a jobs table (the semester databases),
through the Cloudflare API (registered custom.cloudflare
credential, surrogate flow, same as deploy.py). Safe to re-run:
IF NOT EXISTS. Prints only status/result metadata — never any
credential.
"""
import json, sys, urllib.request, urllib.error
sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import add_surrogate_to_request, read_response_body

ACCOUNT = "8d4f9c220c09468e237d76c25678d87d"
BASE = "https://api.cloudflare.com/client/v4"

CREATE_SQL = (
    "CREATE TABLE IF NOT EXISTS job_bindings ("
    " job_id TEXT, seq INTEGER, action TEXT, video_sha256 TEXT,"
    " prev_video_sha256 TEXT, created_at TEXT,"
    " PRIMARY KEY (job_id, seq))"
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


def query(dbid, sql):
    return call("POST", f"/accounts/{ACCOUNT}/d1/database/{dbid}/query",
                {"sql": sql})


def main():
    status, data = call("GET", f"/accounts/{ACCOUNT}/d1/database?per_page=100")
    if status != 200:
        print("database list failed:", status, data.get("errors"))
        sys.exit(1)
    applied = 0
    for db in data.get("result") or []:
        dbid, name = db.get("uuid"), db.get("name")
        # Only semester databases hold a jobs table; probe for it.
        s2, d2 = query(dbid, "SELECT name FROM sqlite_master "
                             "WHERE type='table' AND name='jobs'")
        rows = []
        for r in d2.get("result") or []:
            rows.extend(r.get("results") or [])
        if not rows:
            print("skip (no jobs table):", name)
            continue
        s3, d3 = query(dbid, CREATE_SQL)
        ok = s3 == 200 and d3.get("success")
        print("job_bindings applied:", name, "status:", s3, "success:", ok,
              "errors:", d3.get("errors"))
        if not ok:
            sys.exit(1)
        applied += 1
    print("databases migrated:", applied)
    if not applied:
        sys.exit(1)


if __name__ == "__main__":
    main()
