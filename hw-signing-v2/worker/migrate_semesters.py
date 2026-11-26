#!/usr/bin/env python3
"""One-off migration for Worker 2.7.0: one database per semester.

Prepares the live hw-grading D1 database (the primary database and
the Fall 2026 semester database) for the semester design, through
the Cloudflare API (registered custom.cloudflare credential,
surrogate flow, same as deploy.py and migrate_dedup.py). Prints
only status/result metadata — never any credential.

The Worker finds packages and jobs by checking the semester
databases; there is no routing registry to build. The only state
the primary database needs is db_meta, the current pointer:

  1. Create the `db_meta` table (IF NOT EXISTS).
  2. Set db_meta `current_binding = "DB"` and
     `current_semester = "2026fa"` where absent (existing values
     are kept).

Idempotent: safe to re-run. Do NOT run against live D1 as part of
a build or test run; this script is run manually at migration
time, like deploy.py.
"""
import json, sys, urllib.request, urllib.error
sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import add_surrogate_to_request, read_response_body

ACCOUNT = "8d4f9c220c09468e237d76c25678d87d"
BASE = "https://api.cloudflare.com/client/v4"

CREATE_META_SQL = (
    "CREATE TABLE IF NOT EXISTS db_meta ("
    " key TEXT PRIMARY KEY, value TEXT)"
)
META_SQL = "SELECT key, value FROM db_meta"
PRIMARY_BINDING = "DB"
CURRENT_SEMESTER = "2026fa"


def sql_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


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
    status, data = call(
        "POST", f"/accounts/{ACCOUNT}/d1/database/{dbid}/query",
        {"sql": sql})
    if status != 200 or not data.get("success"):
        print("query failed:", status, data.get("errors"))
        sys.exit(1)
    return data.get("result") or []


def rows(dbid, sql):
    result = query(dbid, sql)
    if not result:
        return []
    return result[0].get("results") or []


def main():
    status, data = call("GET", f"/accounts/{ACCOUNT}/d1/database?name=hw-grading")
    if status != 200 or not data.get("result"):
        print("database lookup failed:", status, data.get("errors"))
        sys.exit(1)
    dbid = data["result"][0]["uuid"]
    print("database:", data["result"][0].get("name"), dbid)

    # 1. The db_meta table.
    query(dbid, CREATE_META_SQL)
    print("db_meta table ensured")

    # 2. Current-semester defaults, where absent.
    meta = {row.get("key"): row.get("value")
            for row in rows(dbid, META_SQL)}
    for key, value in (("current_binding", PRIMARY_BINDING),
                       ("current_semester", CURRENT_SEMESTER)):
        if key in meta:
            print("db_meta %s already set to %r; keeping" % (key, meta[key]))
        else:
            query(dbid,
                  "INSERT INTO db_meta (key, value) VALUES ("
                  + sql_literal(key) + ", " + sql_literal(value) + ")")
            print("db_meta %s set to %r" % (key, value))


if __name__ == "__main__":
    main()
