import json, os, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Fake(BaseHTTPRequestHandler):
    seen = []
    def log_message(self, *a): pass
    def _r(self, st, obj):
        b = json.dumps(obj).encode(); self.send_response(st); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Fake.seen.append((self.path, self.headers["Authorization"], body))
        self._r(200, {"session_id": "devin-x", "url": "https://app.devin.ai/sessions/x"} if self.path == "/v1/sessions" else {})
    def do_GET(self):
        ok = self.path in ("/v1/session/devin-x", "/v3/organizations/org-t/sessions/devin-x")
        self._r(200, {"session_id": "devin-x", "status_enum": "working"}) if ok else self._r(404, {})


class T(unittest.TestCase):
    def setUp(self):
        self.s = ThreadingHTTPServer(("127.0.0.1", 0), Fake); threading.Thread(target=self.s.serve_forever, daemon=True).start()
        self.ledger = os.path.join(tempfile.mkdtemp(), "l.jsonl")
        os.environ.update(DEVIN_API_URL=f"http://127.0.0.1:{self.s.server_address[1]}/v1", DEVIN_API_KEY="sk-secret", PI_DEVIN_LEDGER=self.ledger)
        os.environ.pop("DEVIN_ORG_ID", None)
        import importlib, pi_devin; self.d = importlib.reload(pi_devin)
    def tearDown(self): self.s.shutdown()

    def test_v3_paths_when_org_set(self):
        import importlib
        os.environ.update(DEVIN_ORG_ID="org-t", DEVIN_API_URL=f"http://127.0.0.1:{self.s.server_address[1]}/v3/organizations/org-t")
        d = importlib.reload(self.d)
        self.assertEqual(d.status("devin-x")[1]["status_enum"], "working")
        d.message("devin-x", "hi"); self.assertEqual(Fake.seen[-1][0], "/v3/organizations/org-t/sessions/devin-x/messages")
        d.start("x"); self.assertEqual(Fake.seen[-1][0], "/v3/organizations/org-t/sessions")
        os.environ.pop("DEVIN_ORG_ID")

    def test_start_has_guardrails_and_acu_cap(self):
        st, out = self.d.start("build X", "t")
        self.assertEqual(out["session_id"], "devin-x")
        path, auth, body = Fake.seen[-1]
        self.assertEqual(auth, "Bearer sk-secret"); self.assertIn("SHIP", body["prompt"]); self.assertEqual(body["max_acu_limit"], 10)

    def test_status_message_and_ledger_has_no_key(self):
        self.assertEqual(self.d.status("devin-x")[1]["status_enum"], "working")
        self.assertEqual(self.d.message("devin-x", "hi")[0], 200)
        txt = open(self.ledger).read(); self.assertNotIn("sk-secret", txt); self.assertEqual(len(txt.strip().splitlines()), 2)

    def test_missing_key(self):
        os.environ.pop("DEVIN_API_KEY")
        with self.assertRaises(RuntimeError): self.d.start("x")


if __name__ == "__main__":
    unittest.main()
