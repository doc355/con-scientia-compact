"""Plaud -> PI watchdog. Polls the official Plaud CLI, pulls new recordings, signals the PI gateway.

Per new recording id: transcript (.txt), summary (.md), audio (.mp3, downloaded immediately: links expire in 24h),
then POST /jobs {kind:"plaud", payload:{id, files}} to the gateway; if the gateway is down, drop signals/<id>.ready.
Idempotent: seen ids live in SQLite; failures are retried on the next poll with backoff, never marked seen.
Command names come from env so they can be corrected without code changes once tested against the real CLI:
  PLAUD_LIST_CMD   default "plaud recent --json"
  PLAUD_TX_CMD     default "plaud transcript {id} -o {out}"
  PLAUD_SUM_CMD    default "plaud summary {id} -o {out}"
  PLAUD_AUDIO_CMD  default "plaud audio {id} --json"   (must print JSON with a "url" field)
"""
import json, os, shlex, sqlite3, subprocess, sys, time, urllib.request

ROOT = os.path.expanduser(os.environ.get("PLAUD_ROOT", "~/HIFIDecant/plaud"))
GW = os.environ.get("PI_GATEWAY_URL", "http://localhost:8784")
TOKEN = os.environ.get("PI_TOKEN", "")
CMD = {k: os.environ.get(f"PLAUD_{k}_CMD", d) for k, d in
       {"LIST": "plaud recent --json", "TX": "plaud transcript {id} -o {out}",
        "SUM": "plaud summary {id} -o {out}", "AUDIO": "plaud audio {id} --json"}.items()}


def run(cmd):
    p = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=300)
    if p.returncode != 0:
        raise RuntimeError(f"{cmd!r} exit {p.returncode}: {p.stderr.strip()[:200]}")
    return p.stdout


def ids_from(listing):
    d = json.loads(listing)
    items = d if isinstance(d, list) else d.get("files") or d.get("data") or d.get("items") or []
    return [str(i.get("id") or i.get("file_id")) for i in items if (i.get("id") or i.get("file_id"))]


class Seen:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS seen(id TEXT PRIMARY KEY, at REAL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS attempts(id TEXT, at REAL, error TEXT)")

    def has(self, i):
        return self.db.execute("SELECT 1 FROM seen WHERE id=?", (i,)).fetchone() is not None

    def fails(self, i):
        return self.db.execute("SELECT COUNT(*), MAX(at) FROM attempts WHERE id=?", (i,)).fetchone()

    def mark(self, i):
        self.db.execute("INSERT OR IGNORE INTO seen VALUES(?,?)", (i, time.time())); self.db.commit()

    def fail(self, i, err):
        self.db.execute("INSERT INTO attempts VALUES(?,?,?)", (i, time.time(), err[:300])); self.db.commit()


def download(url, dest):
    with urllib.request.urlopen(url, timeout=300) as r, open(dest + ".part", "wb") as f:
        while chunk := r.read(1 << 16):
            f.write(chunk)
    os.replace(dest + ".part", dest)


def signal(rid, files):
    body = json.dumps({"kind": "plaud", "payload": {"id": rid, "files": files}}).encode()
    req = urllib.request.Request(GW + "/jobs", data=body, method="POST",
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return "gateway:" + json.loads(r.read())["id"]
    except Exception as e:
        os.makedirs(os.path.join(ROOT, "signals"), exist_ok=True)
        with open(os.path.join(ROOT, "signals", f"{rid}.ready"), "w") as f:
            json.dump({"id": rid, "files": files, "gateway_error": str(e)[:200]}, f)
        return "file:" + rid


def poll_once(seen, log=print):
    inbox = os.path.join(ROOT, "inbox"); os.makedirs(inbox, exist_ok=True)
    done = []
    for rid in ids_from(run(CMD["LIST"])):
        if seen.has(rid):
            continue
        n, last = seen.fails(rid)
        if n and time.time() - (last or 0) < min(3600, 60 * 2 ** n):
            continue
        try:
            tx, sm, au = (os.path.join(inbox, f"{rid}{e}") for e in (".txt", ".md", ".mp3"))
            run(CMD["TX"].format(id=rid, out=tx)); run(CMD["SUM"].format(id=rid, out=sm))
            download(json.loads(run(CMD["AUDIO"].format(id=rid)))["url"], au)
            via = signal(rid, {"transcript": tx, "summary": sm, "audio": au})
            seen.mark(rid); done.append(rid); log(f"new {rid} -> {via}")
        except Exception as e:
            seen.fail(rid, str(e)); log(f"FAILED {rid}: {e}")
    return done


if __name__ == "__main__":
    os.makedirs(ROOT, exist_ok=True)
    s = Seen(os.path.join(ROOT, "seen.sqlite3"))
    every = int(os.environ.get("PLAUD_POLL_SECONDS", "300"))
    while True:
        try:
            poll_once(s, lambda m: print(time.strftime("%FT%T"), m, flush=True))
        except Exception as e:
            print(time.strftime("%FT%T"), "poll error:", e, flush=True)
        if "--once" in sys.argv:
            break
        time.sleep(every)
