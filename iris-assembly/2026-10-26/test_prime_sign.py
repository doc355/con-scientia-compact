import sys, types, os, json, hashlib, tempfile, time, secrets, struct
try: import fastapi  # noqa
except ImportError:
    f = types.ModuleType("fastapi"); f.Request = object; r = types.ModuleType("fastapi.responses")
    r.JSONResponse = r.HTMLResponse = object; sys.modules["fastapi"] = f; sys.modules["fastapi.responses"] = r
import prime_sign as ps
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

def cbor(o):
    def head(mt, n):
        if n < 24: return bytes([mt << 5 | n])
        for ai, ln in ((24, 1), (25, 2), (26, 4), (27, 8)):
            if n < 1 << (8 * ln): return bytes([mt << 5 | ai]) + n.to_bytes(ln, "big")
    if isinstance(o, bool): return bytes([0xf5 if o else 0xf4])
    if isinstance(o, int): return head(0, o) if o >= 0 else head(1, -1 - o)
    if isinstance(o, bytes): return head(2, len(o)) + o
    if isinstance(o, str): b = o.encode(); return head(3, len(b)) + b
    if isinstance(o, list): return head(4, len(o)) + b"".join(cbor(x) for x in o)
    if isinstance(o, dict): return head(5, len(o)) + b"".join(cbor(k) + cbor(v) for k, v in o.items())

class Authenticator:   # software stand-in for Touch ID
    def __init__(s, origin="http://localhost:8773", rp="localhost", uv=True):
        s.k = ec.generate_private_key(ec.SECP256R1()); s.cid = secrets.token_bytes(16); s.n = 0; s.origin, s.rp, s.uv = origin, rp, uv
    def flags(s, extra=0): return (0x01 | (0x04 if s.uv else 0) | extra)
    def create(s, opts):
        pn = s.k.public_key().public_numbers()
        cose = {1: 2, 3: -7, -1: 1, -2: pn.x.to_bytes(32, "big"), -3: pn.y.to_bytes(32, "big")}
        ad = hashlib.sha256(s.rp.encode()).digest() + bytes([s.flags(0x40)]) + (0).to_bytes(4, "big") + b"\0" * 16 + len(s.cid).to_bytes(2, "big") + s.cid + cbor(cose)
        cd = json.dumps({"type": "webauthn.create", "challenge": opts["publicKey"]["challenge"], "origin": s.origin}).encode()
        return {"clientDataJSON": ps.b64u(cd), "attestationObject": ps.b64u(cbor({"fmt": "none", "attStmt": {}, "authData": ad}))}
    def get(s, opts, nonce):
        s.n += 1
        ad = hashlib.sha256(s.rp.encode()).digest() + bytes([s.flags()]) + s.n.to_bytes(4, "big")
        cd = json.dumps({"type": "webauthn.get", "challenge": opts["publicKey"]["challenge"], "origin": s.origin}).encode()
        sig = s.k.sign(ad + hashlib.sha256(cd).digest(), ec.ECDSA(hashes.SHA256()))
        return {"nonce": nonce, "credentialId": ps.b64u(s.cid), "authenticatorData": ps.b64u(ad), "clientDataJSON": ps.b64u(cd), "signature": ps.b64u(sig)}

ok = 0
def t(name, cond):
    global ok; print(("PASS " if cond else "FAIL ") + name); ok += bool(cond)
    if not cond: sys.exit(1)
def raises(fn):
    try: fn(); return None
    except ValueError as e: return str(e)

# 1. pure-python P-256 vs cryptography
k = ec.generate_private_key(ec.SECP256R1()); pn = k.public_key().public_numbers(); good = bad = 0; t0 = time.time()
for i in range(40):
    m = secrets.token_bytes(50); s = k.sign(m, ec.ECDSA(hashes.SHA256()))
    good += ps.p256_verify(pn.x, pn.y, m, s); bad += ps.p256_verify(pn.x, pn.y, m + b"x", s)
t("p256: 40/40 genuine verify, 0/40 altered", good == 40 and bad == 0); print(f"     {(time.time()-t0)/80*1000:.1f} ms per verify")
k2 = ec.generate_private_key(ec.SECP256R1()).public_key().public_numbers()
t("p256: other key refused", not ps.p256_verify(k2.x, k2.y, m, s))
t("p256: off-curve key refused", not ps.p256_verify(pn.x, (pn.y + 1) % ps._P, m, s))

home = tempfile.mkdtemp(); app = tempfile.mkdtemp(); os.makedirs(f"{app}/server/__pycache__")
open(f"{app}/server/main.py", "w").write("print('prime')\n"); open(f"{app}/server/__pycache__/x.pyc", "wb").write(b"junk")
S = ps.Signer(ps.Path(home)); A = Authenticator()
t("sign before enrol refused", "error" in S.sign_begin("promote", "rooms", app))
t("check before enrol: no", not S.check("promote", "rooms", app)["ok"])
# 2. enrol
bad_o = Authenticator(origin="http://evil.example"); o = S.enroll_begin()
t("enrol from wrong origin refused", "origin" in (raises(lambda: S.enroll_finish(bad_o.create(o))) or ""))
o = S.enroll_begin(); r = S.enroll_finish(A.create(o)); t("enrol ok", r["ok"])
# PRIME-SIGN-001 expectation, superseded by PRIME-SIGN-002 (kept visible):
# t("second enrol refused", "error" in S.enroll_begin())
t("second enrol is a proposal needing an existing key", S.enroll_begin().get("second_key") is True); S.s.pending.pop("enroll", None)
t("keys file is 0600", oct(os.stat(S.s.keys_f).st_mode & 0o777) == "0o600")
# 3. sign + check
t("unsigned build: promote check refuses", "not signed" in S.check("promote", "rooms", app)["why"])
o = S.sign_begin("promote", "rooms", app); t("manifest skips __pycache__", o["files"] == 1)
r = S.sign_finish(A.get(o, o["nonce"])); t("signed", r["ok"])
c = S.check("promote", "rooms", app); t("check ok after signing", c["ok"])
t("signature for 'rooms' doesn't cover 'other'", not S.check("promote", "other", app)["ok"])
# 4. attacks
o = S.sign_begin("promote", "rooms", app); a = A.get(o, o["nonce"]); sig = bytearray(ps.unb64u(a["signature"])); sig[-1] ^= 1; a["signature"] = ps.b64u(bytes(sig))
t("tampered signature refused", "verify" in (raises(lambda: S.sign_finish(a)) or ""))
o = S.sign_begin("promote", "rooms", app); a = A.get(o, o["nonce"]); S.sign_finish(a)
t("replayed assertion refused", raises(lambda: S.sign_finish(a)) is not None)
o = S.sign_begin("promote", "rooms", app); A.uv = False; a = A.get(o, o["nonce"]); A.uv = True
t("no Touch ID (UV flag off) refused", "not verified" in (raises(lambda: S.sign_finish(a)) or ""))
o = S.sign_begin("promote", "rooms", app); A.n = 0; a = A.get(o, o["nonce"])
t("counter going backwards refused", "counter" in (raises(lambda: S.sign_finish(a)) or "")); A.n = 50
o = S.sign_begin("promote", "rooms", app); open(f"{app}/server/main.py", "a").write("#x\n"); a = A.get(o, o["nonce"])
t("build changed mid-signing refused", "changed" in (raises(lambda: S.sign_finish(a)) or ""))
t("one changed byte after signing -> check refuses", "changed since" in S.check("promote", "rooms", app)["why"])
open(f"{app}/server/main.py", "w").write("print('prime')\n"); t("byte put back -> check ok again", S.check("promote", "rooms", app)["ok"])
other = Authenticator(); o = S.sign_begin("promote", "rooms", app); a = other.get(o, o["nonce"]); a["credentialId"] = ps.b64u(A.cid)
t("a different key posing as Doc's refused", "verify" in (raises(lambda: S.sign_finish(a)) or ""))
# forged record written straight into signatures.jsonl with a different key
os.remove(f"{app}/server/main.py"); open(f"{app}/server/evil.py", "w").write("steal()\n")
d = ps.manifest(app)["digest"]; nonce = "f" * 32; opts = {"publicKey": {"challenge": ps.b64u(ps.challenge_for("promote", "rooms", d, nonce))}}
fa = other.get(opts, nonce); S.s.add_sig({"purpose": "promote", "name": "rooms", "digest": d, "files": 1, "nonce": nonce, "cred_id": ps.b64u(A.cid), "key_fingerprint": "x", "utc": "x",
     "assertion": {k: fa[k] for k in ("authenticatorData", "clientDataJSON", "signature")}})
t("forged signature record pasted into the file is ignored", not S.check("promote", "rooms", app)["ok"])
print(f"{ok} checks passed")
