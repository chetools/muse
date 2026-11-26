#!/usr/bin/env python3
"""Set up a new semester database for the hw-grading Worker (2.7.0+).

One database holds all courses in one semester. Usage:

    python3 semester_setup.py 2027sp            # create + make current
    python3 semester_setup.py 2027sp --no-current

For term <t> (e.g. 2027sp) the script:
  1. Creates the D1 database hw-grading-<t> (skips creation when a
     database of that name already exists).
  2. Applies schema.sql to it (every statement is IF NOT EXISTS, so
     re-running is safe).
  3. Adds the D1 binding DB_<T> (e.g. DB_2027SP) to the hw-grading
     Worker through the script-settings API, preserving every
     existing binding. Before changing anything it PATCHes the
     settings back unchanged and verifies the Worker still answers an
     admin call, so a settings write that disturbed the secret
     bindings is caught before the real change. After the change it
     verifies again: every prior binding present, the new binding
     present, and an admin call succeeding.
  4. Unless --no-current: points the primary database's registry at
     the new semester (db_meta current_binding / current_semester),
     so newly created packages land in the new database. Existing
     package routes are never touched.
  5. Smoke test: creates a throwaway package in the new database
     through the admin API, lists packages and checks the new package
     carries the new database's tag, then retires the package.

Credentials: the Cloudflare API goes through the registered
custom.cloudflare surrogate (as deploy.py); the admin token for the
smoke test is read from the prompt-package-builder skill config.
Nothing secret is printed.
"""
import json, re, sys, urllib.request, urllib.error, uuid
sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import add_surrogate_to_request, read_response_body

ACCOUNT = "8d4f9c220c09468e237d76c25678d87d"
SCRIPT = "hw-grading"
WORKER_URL = "https://hw-grading.carloscomail.workers.dev"
BASE = "https://api.cloudflare.com/client/v4"
PRIMARY_DB_NAME = "hw-grading"
ADMIN_CONFIG = (
    "/home/hatch/workspace/custom-skills/"
    "local-prompt-package-builder/config.json"
)
SCHEMA_PATH = "/home/hatch/workspace/muse-repo-main/hw-signing-v2/worker/schema.sql"


def call(method, path, payload=None, data=None, ctype=None):
    if data is None and payload is not None:
        data = json.dumps(payload).encode()
    req = urllib.request.Request(BASE + path, method=method, data=data)
    req.add_header("Accept", "application/json")
    if data:
        req.add_header("Content-Type", ctype or "application/json")
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


def d1_query(dbid, sql):
    status, data = call(
        "POST", f"/accounts/{ACCOUNT}/d1/database/{dbid}/query",
        {"sql": sql})
    if status != 200 or not data.get("success"):
        raise SystemExit(f"D1 query failed ({status}): {sql[:60]}...")
    return data["result"][0]["results"] if data.get("result") else []


def find_database(name):
    status, data = call(
        "GET", f"/accounts/{ACCOUNT}/d1/database?name={name}")
    if status != 200:
        raise SystemExit(f"database list failed ({status})")
    for db in data.get("result") or []:
        if db.get("name") == name:
            return db.get("uuid")
    return None


def schema_statements():
    text = open(SCHEMA_PATH, encoding="utf-8").read()
    lines = [ln for ln in text.splitlines()
             if not ln.strip().startswith("--")]
    body = "\n".join(lines)
    return [s.strip() for s in body.split(";") if s.strip()]


def get_bindings():
    status, data = call(
        "GET", f"/accounts/{ACCOUNT}/workers/scripts/{SCRIPT}/settings")
    if status != 200:
        raise SystemExit(f"settings read failed ({status})")
    return (data.get("result") or {}).get("bindings") or []


def patch_bindings(bindings):
    # The script-settings PATCH endpoint accepts only
    # multipart/form-data: one part named "settings" holding the
    # JSON settings object (a plain JSON body is refused with 415,
    # seen 2026-11-26). Same construction as deploy.py's upload.
    boundary = "----muse" + uuid.uuid4().hex
    parts = []
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(b'Content-Disposition: form-data; name="settings"\r\n'
                 b'Content-Type: application/json\r\n\r\n')
    parts.append(json.dumps({"bindings": bindings}).encode() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    status, data = call(
        "PATCH", f"/accounts/{ACCOUNT}/workers/scripts/{SCRIPT}/settings",
        data=b"".join(parts),
        ctype=f"multipart/form-data; boundary={boundary}")
    if status != 200 or not data.get("success", True):
        raise SystemExit(f"settings patch failed ({status}): "
                         f"{json.dumps(data)[:200]}")


def admin_token():
    cfg = json.load(open(ADMIN_CONFIG, encoding="utf-8"))
    tok = cfg.get("adminToken") or cfg.get("admin_token")
    if not tok or tok == "REDACTED":
        raise SystemExit("admin config holds no live token; "
                         "smoke test cannot run")
    return tok


def worker_call(method, path, token=None, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(WORKER_URL + path, method=method,
                                 headers={"User-Agent": "Mozilla/5.0"},
                                 data=data)
    if token:
        req.add_header("X-Admin-Token", token)
    if data:
        req.add_header("Content-Type", "application/json")
    # A truncated response body (http.client.IncompleteRead, seen
    # 2026-11-26 on the package list) is a transport fault, not an
    # answer: retry the whole call twice before giving up. HTTP
    # error statuses are answers: they return at once, unretried.
    last_exc = None
    for _attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw.decode()) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw.decode()) if raw else {}
            except Exception:
                return e.code, {}
        except Exception as exc:  # IncompleteRead / URLError / timeout
            last_exc = exc
    raise last_exc


def binding_key(b):
    return (b.get("type"), b.get("name"))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if len(args) != 1 or not re.fullmatch(r"\d{4}(fa|sp|su)", args[0]):
        raise SystemExit("usage: semester_setup.py <term like 2027sp> "
                         "[--no-current]")
    term = args[0]
    db_name = f"hw-grading-{term}"
    binding = "DB_" + term.upper()
    print(f"term {term}: database {db_name}, binding {binding}")

    # 1. Create the database if needed.
    dbid = find_database(db_name)
    if dbid:
        print("database already exists:", dbid)
    else:
        status, data = call("POST", f"/accounts/{ACCOUNT}/d1/database",
                            {"name": db_name})
        if status not in (200, 201) or not data.get("success"):
            raise SystemExit(f"database create failed ({status}): "
                             f"{json.dumps(data)[:200]}")
        dbid = data["result"]["uuid"]
        print("database created:", dbid)

    # 2. Apply the schema.
    stmts = schema_statements()
    for sql in stmts:
        d1_query(dbid, sql)
    print(f"schema applied ({len(stmts)} statements)")

    # 3. Bind it to the Worker, with a no-op settings write first.
    token = admin_token()
    before = get_bindings()
    before_keys = {binding_key(b) for b in before}
    st, _ = worker_call("GET", "/admin/packages", token)
    if st != 200:
        raise SystemExit(f"pre-flight admin call failed ({st}); aborting")
    patch_bindings(before)
    st, _ = worker_call("GET", "/admin/packages", token)
    if st != 200:
        raise SystemExit("no-op settings write disturbed the Worker "
                         f"(admin call {st}); aborting before any change")
    print("no-op settings write verified harmless")
    if any(b.get("name") == binding for b in before):
        print("binding already present:", binding)
    else:
        patch_bindings(before + [
            {"type": "d1", "name": binding, "id": dbid}])
        after = get_bindings()
        after_keys = {binding_key(b) for b in after}
        missing = before_keys - after_keys
        if missing:
            raise SystemExit(f"bindings lost in the update: {missing}")
        if (("d1", binding)) not in after_keys:
            raise SystemExit("new binding missing after the update")
        st, _ = worker_call("GET", "/admin/packages", token)
        if st != 200:
            raise SystemExit(f"admin call failed after binding ({st})")
        print("binding added and verified:", binding)

    # 4. Registry: make the new semester current (primary database).
    primary_id = find_database(PRIMARY_DB_NAME)
    if "--no-current" in flags:
        print("current pointer left unchanged (--no-current)")
    else:
        d1_query(primary_id,
                 "INSERT INTO db_meta (key, value) VALUES "
                 f"('current_binding', '{binding}') "
                 "ON CONFLICT(key) DO UPDATE SET value = excluded.value")
        d1_query(primary_id,
                 "INSERT INTO db_meta (key, value) VALUES "
                 f"('current_semester', '{term}') "
                 "ON CONFLICT(key) DO UPDATE SET value = excluded.value")
        print("registry current semester ->", term)

    # 5. Smoke test through the admin API.
    smoke_name = f"smoke-{term}"
    st, data = worker_call("POST", "/admin/packages", token, {
        "pkg_name": smoke_name,
        "text": "Smoke-test package for semester setup. Not a real "
                "assignment.",
        "binding": binding,
    })
    if st not in (200, 201):
        raise SystemExit(f"smoke package create failed ({st}): "
                         f"{json.dumps(data)[:200]}")
    st, data = worker_call("GET", "/admin/packages", token)
    if st != 200:
        raise SystemExit(f"smoke package list failed ({st})")
    mine = [p for p in data if p.get("pkg", "").startswith(smoke_name)]
    if not mine or mine[0].get("db") != binding:
        raise SystemExit(f"smoke package not routed to {binding}: "
                         f"{json.dumps(mine)[:200]}")
    pkg_id = mine[0]["pkg"]
    st, data = worker_call(
        "POST", f"/admin/packages/{urllib.parse.quote(pkg_id)}/status",
        token, {"status": "retired"})
    print("smoke package created in the new database, listed with "
          f"db={binding}, retire status call -> {st}")
    st, data = worker_call("GET", "/", None)
    print("worker root:", json.dumps(data))
    print("semester setup complete:", term)


if __name__ == "__main__":
    import urllib.parse
    main()
