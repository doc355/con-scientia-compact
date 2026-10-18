import json, os, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))


class Srv(BaseHTTPRequestHandler):
    jobs = []
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"AUDIO")
    def do_POST(self):
        Srv.jobs.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        b = json.dumps({"id": "job1"}).encode(); self.send_response(201)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)


class T(unittest.TestCase):
    def setUp(self):
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), Srv); threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{self.srv.server_address[1]}"
        self.root = tempfile.mkdtemp(); fake = os.path.join(self.root, "fakeplaud.py")
        open(fake, "w").write(f"""import sys,json
a=sys.argv[1:]
if a[0]=='recent': print(json.dumps([{{'id':'r1'}},{{'id':'r2'}}]))
elif a[0] in('transcript','summary'): open(a[3],'w').write(a[0]+a[1])
elif a[0]=='audio':
    if a[1]=='r2': sys.exit(3)
    print(json.dumps({{'url':'{base}/a.mp3'}}))
""")
        py = sys.executable
        os.environ.update(PLAUD_ROOT=self.root, PI_GATEWAY_URL=base, PLAUD_LIST_CMD=f"{py} {fake} recent",
                          PLAUD_TX_CMD=f"{py} {fake} transcript {{id}} -o {{out}}", PLAUD_SUM_CMD=f"{py} {fake} summary {{id}} -o {{out}}",
                          PLAUD_AUDIO_CMD=f"{py} {fake} audio {{id}}")
        import importlib, plaud_watchdog; self.w = importlib.reload(plaud_watchdog)

    def tearDown(self): self.srv.shutdown()

    def test_pull_signal_idempotent_and_retry(self):
        seen = self.w.Seen(os.path.join(self.root, "s.db")); logs = []
        self.assertEqual(self.w.poll_once(seen, logs.append), ["r1"])
        self.assertEqual(open(os.path.join(self.root, "inbox", "r1.mp3"), "rb").read(), b"AUDIO")
        self.assertEqual(Srv.jobs[-1]["payload"]["id"], "r1")
        self.assertTrue(any("FAILED r2" in l for l in logs)); self.assertFalse(seen.has("r2"))
        n = len(Srv.jobs); self.assertEqual(self.w.poll_once(seen, logs.append), [])
        self.assertEqual(len(Srv.jobs), n)  # r1 not re-sent; r2 in backoff

    def test_gateway_down_file_signal(self):
        os.environ["PI_GATEWAY_URL"] = "http://127.0.0.1:1"
        import importlib; w = importlib.reload(self.w)
        w.download = lambda url, dest: open(dest, "wb").write(b"x")
        w.poll_once(w.Seen(os.path.join(self.root, "s2.db")), lambda m: None)
        self.assertTrue(os.path.exists(os.path.join(self.root, "signals", "r1.ready")))


if __name__ == "__main__":
    unittest.main()
