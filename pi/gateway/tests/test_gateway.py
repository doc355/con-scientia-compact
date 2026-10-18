import json, os, sys, sqlite3, tempfile, threading, unittest, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pi_gateway as g


class FakeBackend(BaseHTTPRequestHandler):
    seen = []
    def log_message(self, *a): pass
    def _send(self, obj):
        b = json.dumps(obj).encode(); self.send_response(200)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        self._send({"data": [{"id": "m1"}]})
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeBackend.seen.append((self.path, dict(self.headers), body))
        if self.path.endswith("/messages"):
            return self._send({"id": "a1", "content": [{"type": "text", "text": "hi"}], "stop_reason": "end_turn",
                               "usage": {"input_tokens": 3, "output_tokens": 1}})
        self._send({"id": "c1", "model": body["model"], "choices": [{"message": {"role": "assistant", "content": "ok"}}]})


def start(handler):
    s = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake = start(FakeBackend)
        base = f"http://127.0.0.1:{cls.fake.server_address[1]}"
        os.environ.update(OLLAMA_URL=base, EXO_URL=base, ANTHROPIC_URL=base + "/v1", ANTHROPIC_API_KEY="sk-test")
        os.environ.pop("MOONSHOT_API_KEY", None)
        cls.tmp = tempfile.mkdtemp()
        cls.gw = g.serve("127.0.0.1", 0, os.path.join(cls.tmp, "j.db"), token="tok")
        threading.Thread(target=cls.gw.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.gw.server_address[1]}"

    def call(self, method, path, body=None, auth=True):
        h = {"Content-Type": "application/json"}
        if auth: h["Authorization"] = "Bearer tok"
        req = urllib.request.Request(self.url + path, data=json.dumps(body).encode() if body is not None else None, method=method, headers=h)
        try:
            with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e: return e.code, json.loads(e.read())

    def test_health_no_auth(self):
        st, r = self.call("GET", "/health", auth=False)
        self.assertEqual(st, 200); self.assertEqual(r["backends"]["ollama"], "up")
        self.assertEqual(r["backends"]["moonshot"], "not_configured")
        self.assertNotIn("sk-test", json.dumps(r))

    def test_auth_required(self):
        self.assertEqual(self.call("GET", "/jobs", auth=False)[0], 401)

    def test_route_ollama_strips_prefix(self):
        st, r = self.call("POST", "/v1/chat/completions", {"model": "ollama/gpt-oss:20b", "messages": [{"role": "user", "content": "x"}]})
        self.assertEqual(st, 200); self.assertEqual(r["model"], "ollama/gpt-oss:20b")
        self.assertEqual(FakeBackend.seen[-1][2]["model"], "gpt-oss:20b")

    def test_anthropic_translation(self):
        st, r = self.call("POST", "/v1/chat/completions", {"model": "anthropic/claude-x", "messages": [
            {"role": "system", "content": "S"}, {"role": "user", "content": "u"}]})
        self.assertEqual(st, 200); self.assertEqual(r["choices"][0]["message"]["content"], "hi")
        path, hdr, body = FakeBackend.seen[-1]
        self.assertEqual(body["system"], "S"); self.assertEqual(body["messages"], [{"role": "user", "content": "u"}])

    def test_unconfigured_cloud_503(self):
        st, r = self.call("POST", "/v1/chat/completions", {"model": "moonshot/kimi-k2", "messages": []})
        self.assertEqual(st, 503)

    def test_bad_model_400(self):
        self.assertEqual(self.call("POST", "/v1/chat/completions", {"model": "nope", "messages": []})[0], 400)
        self.assertEqual(self.call("POST", "/v1/chat/completions", {"model": "zzz/x", "messages": []})[0], 400)

    def test_models_aggregated(self):
        st, r = self.call("GET", "/v1/models")
        self.assertIn("ollama/m1", [m["id"] for m in r["data"]]); self.assertIn("exo/m1", [m["id"] for m in r["data"]])

    def test_jobs_append_only(self):
        st, j = self.call("POST", "/jobs", {"kind": "plaud", "payload": {"id": "r1"}})
        self.assertEqual(st, 201); self.assertEqual(j["state"], "queued")
        st, j2 = self.call("POST", f"/jobs/{j['id']}/events", {"state": "done", "detail": "ok"})
        self.assertEqual(j2["state"], "done"); self.assertEqual(len(j2["events"]), 2)
        db = sqlite3.connect(os.path.join(self.tmp, "j.db"))
        with self.assertRaises(sqlite3.DatabaseError): db.execute("DELETE FROM jobs"); db.commit()
        with self.assertRaises(sqlite3.DatabaseError): db.execute("UPDATE events SET state='x'"); db.commit()
        self.assertEqual(self.call("GET", "/jobs?kind=plaud")[1]["jobs"][0]["id"], j["id"])
        self.assertEqual(self.call("GET", "/jobs/nope")[0], 404)

    def test_unreachable_backend_502(self):
        old = os.environ["EXO_URL"]; os.environ["EXO_URL"] = "http://127.0.0.1:1"
        try:
            self.assertEqual(self.call("POST", "/v1/chat/completions", {"model": "exo/q", "messages": []})[0], 502)
        finally:
            os.environ["EXO_URL"] = old


if __name__ == "__main__":
    unittest.main()
