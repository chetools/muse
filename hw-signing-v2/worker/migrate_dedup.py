#!/usr/bin/env python3
"""One-off migration for Worker 2.6.0: acoustic-fingerprint dedup.

Applies the 2.6.0 schema additions to the live hw-grading D1
database through the Cloudflare API (registered custom.cloudflare
credential, surrogate flow, same as deploy.py and
migrate_duration_stats.py). Prints only status/result metadata —
never any credential.

Steps, in order:
  1. Add the `chromaprint` column to jobs (guarded by a
     pragma_table_info check, so re-running is safe).
  2. Create the `job_code_aliases` table (IF NOT EXISTS).
  3. Pre-flight: look for live (status <> 'expired') duplicate
     (pkg, audio_sha256) rows that would block creating the partial
     unique index. If any exist, report them and skip ONLY the
     index creation; the column and table are still applied.
  4. Create the `jobs_one_per_recording` partial unique index
     (IF NOT EXISTS), unless step 3 found blockers.

Do NOT run against live D1 as part of a build or test run; this
script is run manually at migration time, like deploy.py.
"""
import json, sys, urllib.request, urllib.error
sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import add_surrogate_to_request, read_response_body

ACCOUNT = "8d4f9c220c09468e237d76c25678d87d"
BASE = "https://api.cloudflare.com/client/v4"

ADD_COLUMN_SQL = "ALTER TABLE jobs ADD COLUMN chromaprint TEXT"
CREATE_ALIASES_SQL = (
    "CREATE TABLE IF NOT EXISTS job_code_aliases ("
    " pkg TEXT, code_lookup TEXT, job_id TEXT, created_at TEXT,"
    " PRIMARY KEY (pkg, code_lookup))"
)
CREATE_INDEX_SQL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS jobs_one_per_recording"
    " ON jobs (pkg, audio_sha256) WHERE status <> 'expired'"
)
# Live duplicates that would block the partial unique index.
PREFLIGHT_SQL = (
    "SELECT pkg, audio_sha256, COUNT(*) AS n,"
    " GROUP_CONCAT(job_id) AS job_ids FROM jobs"
    " WHERE status <> 'expired'"
    " GROUP BY pkg, audio_sha256 HAVING n > 1"
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
    status, data = call(
        "POST", f"/accounts/{ACCOUNT}/d1/database/{dbid}/query",
        {"sql": sql})
    if status != 200 or not data.get("success"):
        print("query failed:", status, data.get("errors"))
        sys.exit(1)
    return data.get("result") or []


def main():
    status, data = call("GET", f"/accounts/{ACCOUNT}/d1/database?name=hw-grading")
    if status != 200 or not data.get("result"):
        print("database lookup failed:", status, data.get("errors"))
        sys.exit(1)
    dbid = data["result"][0]["uuid"]
    print("database:", data["result"][0].get("name"), dbid)

    # 1. chromaprint column, guarded by a pragma_table_info
    # check (a plain SELECT, so it travels the D1 query API like
    # any other read) so a re-run skips it instead of failing on
    # the duplicate column.
    result = query(dbid, "SELECT name FROM pragma_table_info('jobs')")
    columns = [row.get("name") for row in (result[0].get("results") or [])]
    if "chromaprint" in columns:
        print("jobs.chromaprint already present; skipping ALTER")
    else:
        query(dbid, ADD_COLUMN_SQL)
        print("added jobs.chromaprint")

    # 2. Alias table.
    query(dbid, CREATE_ALIASES_SQL)
    print("job_code_aliases table ensured")

    # 3. Pre-flight for the index: live duplicates would block it.
    result = query(dbid, PREFLIGHT_SQL)
    blockers = result[0].get("results") or []
    if blockers:
        print("live duplicate (pkg, audio_sha256) rows found:",
              len(blockers))
        for row in blockers:
            print("blocker:", row.get("pkg"), row.get("audio_sha256"),
                  "count:", row.get("n"), "jobs:", row.get("job_ids"))
        print("skipping index creation; column and table applied")
        return

    # 4. Partial unique index.
    query(dbid, CREATE_INDEX_SQL)
    print("jobs_one_per_recording index ensured")


if __name__ == "__main__":
    main()
