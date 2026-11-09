#!/usr/bin/env python3
"""Deploy worker.js to the hw-grading Worker via the Cloudflare API.

Modelled on ~/workspace/hw-signing-worker/deploy.py. Uses the
registered custom.cloudflare credential (surrogate flow, same as
bin/cloudflare.py). Uploads through the /content endpoint with no
bindings in the metadata, which preserves the existing bindings —
including the secret_text bindings and the D1 DB binding — and sends
no secret value anywhere. (Do not use the plain PUT
/scripts/{name} upload endpoint for this Worker: it demands the
secrets' text values, which are never readable.)

Before running: create the Worker in the dashboard (any starter
code), create the D1 database and bind it as DB, apply schema.sql,
and set the five secrets (SIGNING_SECRET, ADMIN_TOKEN, GRADING_TOKEN,
VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY). See README.md. This script is
run manually at deploy time; it is never run by tests or the build.
"""
import json, sys, urllib.request, urllib.error, uuid
sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import add_surrogate_to_request, read_response_body

ACCOUNT = "8d4f9c220c09468e237d76c25678d87d"
SCRIPT = "hw-grading"
BASE = "https://api.cloudflare.com/client/v4"

EXPECTED_SECRETS = [
    "SIGNING_SECRET",
    "ADMIN_TOKEN",
    "GRADING_TOKEN",
    "VAPID_PUBLIC_KEY",
    "VAPID_PRIVATE_KEY",
]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused")


def call(method, path, data=None, ctype=None):
    req = urllib.request.Request(BASE + path, method=method, data=data)
    req.add_header("Accept", "application/json")
    if ctype:
        req.add_header("Content-Type", ctype)
    add_surrogate_to_request(req, "custom.cloudflare", allowed_hosts=["api.cloudflare.com"])
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=60) as resp:
            raw = read_response_body(resp)
            return resp.status, json.loads(raw.decode()) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw.decode()) if raw else {}
        except Exception:
            return e.code, {"raw": raw.decode(errors="replace")}


def read_bindings():
    status, data = call("GET", f"/accounts/{ACCOUNT}/workers/scripts/{SCRIPT}/settings")
    if status != 200:
        return None
    return (data.get("result") or {}).get("bindings") or []


def main():
    bindings = read_bindings()
    if bindings is None:
        print("settings read failed (Worker not created yet?); continuing to upload")
    else:
        print("existing bindings (preserved by the /content upload):",
              [(b.get("type"), b.get("name")) for b in bindings])

    with open(__file__.rsplit("/", 1)[0] + "/worker.js", "rb") as f:
        code = f.read()
    # No "bindings" key: the /content endpoint keeps the Worker's
    # existing bindings when none are sent.
    metadata = {
        "main_module": "worker.js",
        "compatibility_date": "2026-11-09",
    }
    boundary = "----muse" + uuid.uuid4().hex
    parts = []
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(b'Content-Disposition: form-data; name="metadata"\r\nContent-Type: application/json\r\n\r\n')
    parts.append(json.dumps(metadata).encode() + b"\r\n")
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(b'Content-Disposition: form-data; name="worker.js"; filename="worker.js"\r\nContent-Type: application/javascript+module\r\n\r\n')
    parts.append(code + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)

    status, data = call("PUT", f"/accounts/{ACCOUNT}/workers/scripts/{SCRIPT}/content",
                        data=body, ctype=f"multipart/form-data; boundary={boundary}")
    print("upload status:", status, "success:", data.get("success"), "errors:", data.get("errors"))
    if status >= 400 or not data.get("success"):
        sys.exit(1)
    result = data.get("result") or {}
    print("deployed script:", result.get("id"), "modified:", result.get("modified_on"))

    bindings = read_bindings() or []
    print("bindings after deploy:", [(b.get("type"), b.get("name")) for b in bindings])
    missing = [name for name in EXPECTED_SECRETS
               if not any(b.get("type") == "secret_text" and b.get("name") == name
                          for b in bindings)]
    if not any(b.get("name") == "DB" for b in bindings):
        missing.append("DB (D1 binding)")
    if missing:
        print("WARNING: missing bindings after deploy:", missing)
        print("Set them in the dashboard (Settings > Variables and Secrets / Bindings);")
        print("the code is uploaded but the Worker will fail closed until they exist.")
        sys.exit(1)


if __name__ == "__main__":
    main()
