"""Devin as a callable cloud agent inside PI.

PI (or anything holding the gateway) can start a Devin session, message it, and read its status/result.
Uses the Devin public API v1 (https://docs.devin.ai/api-reference): POST /v1/sessions, GET /v1/session/{id},
POST /v1/session/{id}/message. Key: DEVIN_API_KEY on the PI host only, never sent to clients.
Every call is appended to an append-only JSONL ledger (PI_DEVIN_LEDGER) with the key never written.
Cost guard: max_acu_limit is always sent (default PI_DEVIN_MAX_ACU=10).

CLI:  pi_devin.py start "<prompt>" [--title T]  |  status <session_id>  |  message <session_id> "<text>"
"""
import json, os, sys, time, urllib.error, urllib.request

API = os.environ.get("DEVIN_API_URL", "https://api.devin.ai/v1")
LEDGER = os.path.expanduser(os.environ.get("PI_DEVIN_LEDGER", "~/.pi-gateway/devin-ledger.jsonl"))
PREAMBLE = ("You were started by Project Iris (PI) for Christopher Hoffpauir. Rules: truth over polish, append-only ledgers, "
            "no deletes (retire to _to_delete/), no PII off device, no money moves, nothing goes live without Christopher's word SHIP. "
            "Deliver work on a git branch, never main.\n\nTASK:\n")


def _key():
    k = os.environ.get("DEVIN_API_KEY")
    if not k:
        raise RuntimeError("DEVIN_API_KEY not set on this PI host")
    return k


def _log(op, req, status, resp):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a") as f:
        f.write(json.dumps({"at": time.time(), "op": op, "request": req, "status": status, "response": resp}) + "\n")


def _call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            st, out = r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        st, out = e.code, {"error": (e.read() or b"").decode()[:500]}
    except (urllib.error.URLError, OSError) as e:
        st, out = 502, {"error": f"Devin API unreachable: {e}"}
    _log(f"{method} {path}", body, st, out)
    return st, out


def start(prompt, title=None, max_acu=None):
    body = {"prompt": PREAMBLE + prompt, "max_acu_limit": int(max_acu or os.environ.get("PI_DEVIN_MAX_ACU", "10"))}
    if title:
        body["title"] = title
    return _call("POST", "/sessions", body)


def status(session_id):
    return _call("GET", f"/session/{session_id}")


def message(session_id, text):
    return _call("POST", f"/session/{session_id}/message", {"message": text})


if __name__ == "__main__":
    a = sys.argv[1:]
    try:
        if a[:1] == ["start"] and len(a) >= 2:
            t = a[a.index("--title") + 1] if "--title" in a else None
            st, out = start(a[1], t)
        elif a[:1] == ["status"] and len(a) == 2:
            st, out = status(a[1])
        elif a[:1] == ["message"] and len(a) == 3:
            st, out = message(a[1], a[2])
        else:
            print(__doc__); sys.exit(2)
    except RuntimeError as e:
        print(json.dumps({"error": str(e)})); sys.exit(1)
    print(json.dumps(out, indent=1)); sys.exit(0 if st < 300 else 1)
