"""Background-safety gate, test 1 of 3: snapshot every background function, then diff against a saved baseline.

  python3 pi_baseline.py snapshot > before.json     # before any install
  python3 pi_baseline.py snapshot > after.json      # after
  python3 pi_baseline.py diff before.json after.json   # exit 1 on any regression

Read-only probes only. Targets come from env (defaults are Doc's tailnet).
"""
import json, os, shutil, socket, subprocess, sys, time, urllib.request

T = {
    "ollama": os.environ.get("OLLAMA_URL", "http://christophers-macbook-pro-3:11434"),
    "exo": os.environ.get("EXO_URL", "http://project-iris-1:52415"),
    "selflight": os.environ.get("SELFLIGHT_URL", "http://localhost:8765"),
    "gateway": os.environ.get("PI_GATEWAY_URL", "http://localhost:8784"),
}
PEERS = [p for p in os.environ.get("PI_PEERS", "project-iris-1,project-iris-2-8,christophers-macbook-pro-3").split(",") if p]


def get(url, timeout=8):
    t = time.time()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read()
            return {"ok": r.status == 200, "status": r.status, "ms": round((time.time() - t) * 1000), "body": body}
    except Exception as e:
        return {"ok": False, "status": None, "ms": round((time.time() - t) * 1000), "error": type(e).__name__ + ": " + str(e)[:120]}


def probe_tailscale():
    if not shutil.which("tailscale"):
        return {"ok": None, "note": "tailscale CLI not on this host"}
    try:
        d = json.loads(subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=10).stdout)
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}
    online = {(p.get("DNSName") or "").split(".")[0]: p.get("Online", False) for p in (d.get("Peer") or {}).values()}
    return {"ok": d.get("BackendState") == "Running" and d["Self"].get("Online", False),
            "backend": d.get("BackendState"), "peers": {p: online.get(p, False) for p in PEERS}}


def probe_json(name, path, summarize):
    r = get(T[name] + path)
    out = {k: v for k, v in r.items() if k != "body"}
    if r["ok"]:
        try:
            out.update(summarize(json.loads(r["body"])))
        except Exception as e:
            out.update(ok=False, error="bad JSON: " + str(e)[:80])
    return out


def probe_port(host, port):
    try:
        with socket.create_connection((host, port), timeout=3):
            return True
    except OSError:
        return False


def snapshot():
    s = {"taken": time.time(), "host": socket.gethostname(), "checks": {}}
    c = s["checks"]
    c["tailscale"] = probe_tailscale()
    c["ollama"] = probe_json("ollama", "/api/tags", lambda d: {"models": sorted(m["name"] for m in d["models"])})
    c["exo"] = probe_json("exo", "/state", lambda d: {"nodes": len(d.get("nodeMemory") or {}), "instances": len(d.get("instances") or {})})
    c["selflight"] = probe_json("selflight", "/api/health", lambda d: {"health": d if len(json.dumps(d)) < 400 else "large"})
    c["gateway"] = probe_json("gateway", "/health", lambda d: {"backends": d.get("backends")})
    c["listening"] = {f"{h}:{p}": probe_port(h, p) for h, p in
                      [("localhost", 8765), ("localhost", 8784)]}
    try:
        out = subprocess.run(["vm_stat"] if sys.platform == "darwin" else ["free", "-m"], capture_output=True, text=True, timeout=5).stdout
        c["memory_raw"] = {"ok": True, "text": out[:600]}
    except Exception as e:
        c["memory_raw"] = {"ok": None, "error": str(e)[:80]}
    return s


def diff(before, after):
    regressions, notes = [], []
    for k, b in before["checks"].items():
        a = after["checks"].get(k)
        if a is None:
            regressions.append(f"{k}: check missing after change"); continue
        if k == "listening":
            for port, was in b.items():
                if was and not a.get(port):
                    regressions.append(f"listening {port}: was up, now down")
            continue
        if b.get("ok") is True and a.get("ok") is not True:
            regressions.append(f"{k}: was ok, now {a.get('error') or a.get('status')}")
        if k == "tailscale" and b.get("peers"):
            for p, was in b["peers"].items():
                if was and not a.get("peers", {}).get(p):
                    regressions.append(f"tailscale peer {p}: was online, now offline")
        if k == "ollama" and b.get("models"):
            lost = set(b["models"]) - set(a.get("models") or [])
            if lost:
                regressions.append(f"ollama models disappeared: {sorted(lost)}")
        if b.get("ms") and a.get("ms") and a["ms"] > max(5 * b["ms"], b["ms"] + 2000):
            notes.append(f"{k}: latency {b['ms']}ms -> {a['ms']}ms (warning, not a failure)")
    return regressions, notes


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "snapshot":
        print(json.dumps(snapshot(), indent=1, default=str))
    elif len(sys.argv) == 4 and sys.argv[1] == "diff":
        reg, notes = diff(json.load(open(sys.argv[2])), json.load(open(sys.argv[3])))
        for n in notes: print("NOTE", n)
        for r in reg: print("REGRESSION", r)
        print("PASS: no background regressions" if not reg else f"FAIL: {len(reg)} regression(s)")
        sys.exit(1 if reg else 0)
    else:
        print(__doc__); sys.exit(2)
