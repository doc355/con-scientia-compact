"""PI Core Gateway: one front door for every PI client (phones, Watch, AVP, Devin, Plaud watchdog).

Stdlib only, so it runs on any Iris Mac without installs.
Routes OpenAI-style chat to a backend chosen by model prefix:
  ollama/<model>   -> OLLAMA_URL/v1      (default http://localhost:11434)
  exo/<model>      -> EXO_URL/v1         (default http://project-iris-1:52415)
  moonshot/<model> -> https://api.moonshot.ai/v1  (MOONSHOT_API_KEY)
  openrouter/<m>   -> https://openrouter.ai/api/v1 (OPENROUTER_API_KEY)
  anthropic/<m>    -> https://api.anthropic.com/v1/messages (ANTHROPIC_API_KEY), translated
Job API (append-only SQLite): POST /jobs, GET /jobs, GET /jobs/<id>, POST /jobs/<id>/events.
Auth: Bearer PI_TOKEN on every route except GET /health. Keys stay on the gateway; never returned.
"""
import json, os, sqlite3, threading, time, urllib.request, urllib.error, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = "0.1.0"


def env(k, d=None):
    return os.environ.get(k, d)


def backends():
    return {
        "ollama": {"base": env("OLLAMA_URL", "http://localhost:11434").rstrip("/") + "/v1", "key": None},
        "exo": {"base": env("EXO_URL", "http://project-iris-1:52415").rstrip("/") + "/v1", "key": None},
        "moonshot": {"base": env("MOONSHOT_URL", "https://api.moonshot.ai/v1"), "key": env("MOONSHOT_API_KEY")},
        "openrouter": {"base": env("OPENROUTER_URL", "https://openrouter.ai/api/v1"), "key": env("OPENROUTER_API_KEY")},
        "anthropic": {"base": env("ANTHROPIC_URL", "https://api.anthropic.com/v1"), "key": env("ANTHROPIC_API_KEY")},
    }


def http_json(method, url, body=None, headers=None, timeout=600):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {"error": str(e)}
    except (urllib.error.URLError, OSError, ValueError) as e:
        return 502, {"error": f"backend unreachable: {e}"}


def split_model(model):
    if not model or "/" not in model:
        raise ValueError("model must be '<backend>/<model>', e.g. 'ollama/gpt-oss:20b'")
    b, m = model.split("/", 1)
    if b not in backends():
        raise ValueError(f"unknown backend '{b}'; known: {sorted(backends())}")
    return b, m


def to_anthropic(body, model):
    sys_txt = "\n".join(m["content"] for m in body["messages"] if m["role"] == "system")
    msgs = [m for m in body["messages"] if m["role"] != "system"]
    out = {"model": model, "messages": msgs, "max_tokens": body.get("max_tokens", 4096)}
    if sys_txt:
        out["system"] = sys_txt
    if "temperature" in body:
        out["temperature"] = body["temperature"]
    return out


def from_anthropic(resp, model):
    text = "".join(c.get("text", "") for c in resp.get("content", []) if c.get("type") == "text")
    u = resp.get("usage", {})
    return {"id": resp.get("id"), "object": "chat.completion", "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": resp.get("stop_reason")}],
            "usage": {"prompt_tokens": u.get("input_tokens"), "completion_tokens": u.get("output_tokens")}}


def chat(body):
    b, m = split_model(body.get("model"))
    cfg = backends()[b]
    if cfg["key"] is None and b in ("moonshot", "openrouter", "anthropic"):
        return 503, {"error": f"{b} not configured: set {b.upper()}_API_KEY on the gateway"}
    if b == "anthropic":
        st, r = http_json("POST", cfg["base"] + "/messages", to_anthropic(body, m),
                          {"x-api-key": cfg["key"], "anthropic-version": "2023-06-01"})
        return (st, from_anthropic(r, body["model"])) if st == 200 else (st, r)
    hdr = {"Authorization": f"Bearer {cfg['key']}"} if cfg["key"] else {}
    st, r = http_json("POST", cfg["base"] + "/chat/completions", {**body, "model": m}, hdr)
    if st == 200 and isinstance(r, dict):
        r["model"] = body["model"]
    return st, r


def health():
    out = {"status": "ok", "version": VERSION, "time": time.time(), "backends": {}}
    for name in ("ollama", "exo"):
        st, _ = http_json("GET", backends()[name]["base"] + "/models", timeout=5)
        out["backends"][name] = "up" if st == 200 else f"down({st})"
    for name in ("moonshot", "openrouter", "anthropic"):
        out["backends"][name] = "configured" if backends()[name]["key"] else "not_configured"
    return out


class Store:
    """Append-only job + event ledger. Jobs are never deleted; state changes are new events."""
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, kind TEXT, payload TEXT, created REAL);
          CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, job TEXT, state TEXT, detail TEXT, at REAL);
          CREATE TRIGGER IF NOT EXISTS no_del_jobs BEFORE DELETE ON jobs BEGIN SELECT RAISE(ABORT,'append-only'); END;
          CREATE TRIGGER IF NOT EXISTS no_upd_jobs BEFORE UPDATE ON jobs BEGIN SELECT RAISE(ABORT,'append-only'); END;
          CREATE TRIGGER IF NOT EXISTS no_del_ev BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'append-only'); END;
          CREATE TRIGGER IF NOT EXISTS no_upd_ev BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'append-only'); END;""")

    def create(self, kind, payload):
        jid = uuid.uuid4().hex
        with self.lock:
            self.db.execute("INSERT INTO jobs VALUES(?,?,?,?)", (jid, kind, json.dumps(payload), time.time()))
            self.db.execute("INSERT INTO events(job,state,detail,at) VALUES(?,?,?,?)", (jid, "queued", "", time.time()))
            self.db.commit()
        return self.get(jid)

    def event(self, jid, state, detail=""):
        if not self.get(jid):
            return None
        with self.lock:
            self.db.execute("INSERT INTO events(job,state,detail,at) VALUES(?,?,?,?)", (jid, state, detail, time.time()))
            self.db.commit()
        return self.get(jid)

    def get(self, jid):
        r = self.db.execute("SELECT id,kind,payload,created FROM jobs WHERE id=?", (jid,)).fetchone()
        if not r:
            return None
        ev = [{"state": s, "detail": d, "at": a} for s, d, a in
              self.db.execute("SELECT state,detail,at FROM events WHERE job=? ORDER BY seq", (jid,))]
        return {"id": r[0], "kind": r[1], "payload": json.loads(r[2]), "created": r[3], "state": ev[-1]["state"], "events": ev}

    def list(self, kind=None, limit=100):
        q = "SELECT id FROM jobs" + (" WHERE kind=?" if kind else "") + " ORDER BY created DESC LIMIT ?"
        return [self.get(i) for (i,) in self.db.execute(q, ((kind, limit) if kind else (limit,)))]


def make_handler(store, token):
    class H(BaseHTTPRequestHandler):
        server_version = "PI-Gateway/" + VERSION

        def log_message(self, fmt, *a):
            print(time.strftime("%Y-%m-%dT%H:%M:%S"), self.address_string(), fmt % a, flush=True)

        def send(self, st, obj):
            b = json.dumps(obj).encode()
            self.send_response(st)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def authed(self):
            if not token:
                return True
            if self.headers.get("Authorization") == f"Bearer {token}":
                return True
            self.send(401, {"error": "unauthorized"})
            return False

        def body(self):
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}")

        def do_GET(self):
            p = self.path.split("?")[0].rstrip("/")
            if p == "/health":
                return self.send(200, health())
            if not self.authed():
                return
            if p == "/jobs":
                kind = None
                if "kind=" in self.path:
                    kind = self.path.split("kind=", 1)[1].split("&")[0]
                return self.send(200, {"jobs": store.list(kind)})
            if p.startswith("/jobs/"):
                j = store.get(p.split("/")[2])
                return self.send(200, j) if j else self.send(404, {"error": "no such job"})
            if p == "/v1/models":
                data = []
                for b in ("ollama", "exo"):
                    st, r = http_json("GET", backends()[b]["base"] + "/models", timeout=10)
                    if st == 200:
                        data += [{"id": f"{b}/{m['id']}", "object": "model"} for m in r.get("data", [])]
                return self.send(200, {"object": "list", "data": data})
            self.send(404, {"error": "not found"})

        def do_POST(self):
            p = self.path.split("?")[0].rstrip("/")
            if not self.authed():
                return
            try:
                b = self.body()
            except ValueError:
                return self.send(400, {"error": "invalid JSON"})
            try:
                if p == "/v1/chat/completions":
                    return self.send(*chat(b))
                if p == "/jobs":
                    if not b.get("kind"):
                        return self.send(400, {"error": "kind required"})
                    return self.send(201, store.create(b["kind"], b.get("payload", {})))
                if p.startswith("/jobs/") and p.endswith("/events"):
                    j = store.event(p.split("/")[2], b.get("state", "note"), b.get("detail", ""))
                    return self.send(200, j) if j else self.send(404, {"error": "no such job"})
            except ValueError as e:
                return self.send(400, {"error": str(e)})
            self.send(404, {"error": "not found"})
    return H


def serve(host=None, port=None, db=None, token=None):
    host = host or env("PI_HOST", "127.0.0.1")
    port = int(port or env("PI_PORT", "8784"))
    store = Store(db or env("PI_DB", os.path.expanduser("~/.pi-gateway/jobs.sqlite3")))
    srv = ThreadingHTTPServer((host, port), make_handler(store, token if token is not None else env("PI_TOKEN")))
    return srv


if __name__ == "__main__":
    os.makedirs(os.path.expanduser("~/.pi-gateway"), exist_ok=True)
    s = serve()
    print(f"PI gateway {VERSION} on {s.server_address}", flush=True)
    s.serve_forever()
