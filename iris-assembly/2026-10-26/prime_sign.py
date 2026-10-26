"""PRIME-SIGN-001 — Doc's Touch ID (WebAuthn passkey) signature over a build's checksum list.

Rule (Doc, 2026-10-26): any change to Iris Prime itself must be locked in with his biometric.
- Enrol: Doc's platform passkey (Touch ID) is registered once, on this Mac (loopback only).
- Sign: a candidate's app tree -> sorted sha256 manifest -> digest; Doc's passkey signs a challenge
  bound to (purpose, name, digest). The full assertion is kept, so anyone can re-verify it later.
- Promote: release_gate.Gate.promote refuses unless a stored signature re-verifies AND the tree's
  digest today equals the signed digest (one changed byte = refused).
Pure stdlib (P-256 ECDSA verify, minimal CBOR): the bundled Python has no `cryptography`.
Verification only; no secret ever lives here. Append-only records under SELFLIGHT_HOME/prime-sign/.
"""
import base64, hashlib, json, os, secrets, threading, time
from pathlib import Path
from fastapi import Request
from fastapi.responses import JSONResponse, HTMLResponse

SHIP = "PRIME-SIGN-001"
RP_ID = "localhost"
EXCLUDE_DIRS = {"__pycache__", "_to_delete", ".git", "node_modules"}

# ---------------- P-256 ECDSA verify (FIPS 186-4), stdlib only ----------------
_P = 0xffffffff00000001000000000000000000000000ffffffffffffffffffffffff
_A = _P - 3
_B = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b
_N = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551
_G = (0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296,
      0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5)

def _on_curve(Q):
    x, y = Q
    return 0 <= x < _P and 0 <= y < _P and (y * y - (x * x * x + _A * x + _B)) % _P == 0

def _jadd(P1, P2):   # Jacobian add (handles doubling/infinity)
    if P1[2] == 0: return P2
    if P2[2] == 0: return P1
    X1, Y1, Z1 = P1; X2, Y2, Z2 = P2
    Z1Z1, Z2Z2 = Z1 * Z1 % _P, Z2 * Z2 % _P
    U1, U2 = X1 * Z2Z2 % _P, X2 * Z1Z1 % _P
    S1, S2 = Y1 * Z2 * Z2Z2 % _P, Y2 * Z1 * Z1Z1 % _P
    if U1 == U2:
        if S1 != S2: return (1, 1, 0)
        return _jdbl(P1)
    H = (U2 - U1) % _P; R = (S2 - S1) % _P
    H2 = H * H % _P; H3 = H * H2 % _P; U1H2 = U1 * H2 % _P
    X3 = (R * R - H3 - 2 * U1H2) % _P
    Y3 = (R * (U1H2 - X3) - S1 * H3) % _P
    return (X3, Y3, H * Z1 * Z2 % _P)

def _jdbl(P1):
    X, Y, Z = P1
    if Z == 0 or Y == 0: return (1, 1, 0)
    YY = Y * Y % _P; S = 4 * X * YY % _P
    ZZ = Z * Z % _P; M = 3 * (X - ZZ) * (X + ZZ) % _P   # a = -3
    X3 = (M * M - 2 * S) % _P
    Y3 = (M * (S - X3) - 8 * YY * YY) % _P
    return (X3, Y3, 2 * Y * Z % _P)

def _shamir(u1, Pt1, u2, Pt2):
    J1, J2 = (Pt1[0], Pt1[1], 1), (Pt2[0], Pt2[1], 1)
    J12 = _jadd(J1, J2); R = (1, 1, 0)
    for i in range(max(u1.bit_length(), u2.bit_length()) - 1, -1, -1):
        R = _jdbl(R); b1, b2 = (u1 >> i) & 1, (u2 >> i) & 1
        if b1 and b2: R = _jadd(R, J12)
        elif b1: R = _jadd(R, J1)
        elif b2: R = _jadd(R, J2)
    if R[2] == 0: return None
    zi = pow(R[2], -1, _P); return (R[0] * zi * zi % _P, R[1] * zi * zi * zi % _P)

def _der_sig(sig: bytes):
    if len(sig) < 8 or sig[0] != 0x30 or sig[1] != len(sig) - 2: raise ValueError("bad DER signature")
    i = 2; out = []
    for _ in range(2):
        if sig[i] != 0x02: raise ValueError("bad DER integer")
        ln = sig[i + 1]; out.append(int.from_bytes(sig[i + 2:i + 2 + ln], "big")); i += 2 + ln
    if i != len(sig): raise ValueError("trailing bytes in signature")
    return out

def p256_verify(x: int, y: int, msg: bytes, der_sig: bytes) -> bool:
    try: r, s = _der_sig(der_sig)
    except Exception: return False
    Q = (x, y)
    if not _on_curve(Q) or not (1 <= r < _N and 1 <= s < _N): return False
    e = int.from_bytes(hashlib.sha256(msg).digest(), "big")
    w = pow(s, -1, _N)
    X = _shamir(e * w % _N, _G, r * w % _N, Q)
    return X is not None and X[0] % _N == r

# ---------------- minimal CBOR (what WebAuthn needs) ----------------
def cbor_decode(b: bytes, i: int = 0):
    ib = b[i]; mt, ai = ib >> 5, ib & 31; i += 1
    if ai < 24: val = ai
    elif ai in (24, 25, 26, 27):
        n = 1 << (ai - 24); val = int.from_bytes(b[i:i + n], "big"); i += n
    else: raise ValueError("indefinite CBOR not supported")
    if mt == 0: return val, i
    if mt == 1: return -1 - val, i
    if mt == 2: return bytes(b[i:i + val]), i + val
    if mt == 3: return b[i:i + val].decode(), i + val
    if mt == 4:
        out = []
        for _ in range(val): v, i = cbor_decode(b, i); out.append(v)
        return out, i
    if mt == 5:
        out = {}
        for _ in range(val):
            k, i = cbor_decode(b, i); v, i = cbor_decode(b, i); out[k] = v
        return out, i
    if mt == 7: return {20: False, 21: True, 22: None}.get(val), i
    raise ValueError(f"CBOR major type {mt} not supported")

def b64u(b: bytes) -> str: return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def unb64u(s: str) -> bytes: return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

def parse_auth_data(ad: bytes) -> dict:
    if len(ad) < 37: raise ValueError("authenticatorData too short")
    out = {"rp_id_hash": ad[:32], "flags": ad[32], "sign_count": int.from_bytes(ad[33:37], "big")}
    if ad[32] & 0x40:
        cl = int.from_bytes(ad[53:55], "big"); out["cred_id"] = ad[55:55 + cl]
        cose, _ = cbor_decode(ad, 55 + cl); out["cose"] = cose
    return out

# ---------------- manifest ----------------
def manifest(app_dir) -> dict:
    root = Path(app_dir); lines = []
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in EXCLUDE_DIRS and ".pre-" not in d)
        for fn in sorted(fns):
            if fn == ".DS_Store" or ".pre-" in fn or fn.endswith(".pyc"): continue
            p = Path(dp) / fn
            if p.is_symlink(): lines.append(f"symlink:{os.readlink(p)}  {p.relative_to(root).as_posix()}"); continue
            h = hashlib.sha256()
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
            lines.append(f"{h.hexdigest()}  {p.relative_to(root).as_posix()}")
    lines.sort(key=lambda l: l.split("  ", 1)[1])
    text = "\n".join(lines) + "\n"
    return {"files": len(lines), "digest": hashlib.sha256(text.encode()).hexdigest(), "text": text}

def challenge_for(purpose: str, name: str, digest: str, nonce: str) -> bytes:
    return hashlib.sha256(f"IRIS-PRIME-SIGN-v1|{purpose}|{name}|{digest}|{nonce}".encode()).digest()

# ---------------- store ----------------
class Store:
    def __init__(self, home: Path):
        self.dir = Path(home) / "prime-sign"; self.dir.mkdir(parents=True, exist_ok=True)
        self.keys_f, self.sigs_f, self.log_f = self.dir / "keys.json", self.dir / "signatures.jsonl", self.dir / "ledger.jsonl"
        self.lock = threading.Lock(); self.pending = {}
    def keys(self) -> list:
        try: return json.loads(self.keys_f.read_text())
        except Exception: return []
    def save_keys(self, ks):
        tmp = self.keys_f.with_suffix(".tmp"); tmp.write_text(json.dumps(ks, indent=1)); os.chmod(tmp, 0o600); tmp.replace(self.keys_f)
    def log(self, **kw):
        kw["utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(self.log_f, "a") as f: f.write(json.dumps(kw) + "\n")
    def add_sig(self, rec):
        with open(self.sigs_f, "a") as f: f.write(json.dumps(rec) + "\n")
    def sigs(self) -> list:
        try: return [json.loads(l) for l in self.sigs_f.read_text().splitlines() if l.strip()]
        except Exception: return []

def _origin_ok(origin: str) -> bool:
    try:
        from urllib.parse import urlparse
        u = urlparse(origin); return u.hostname == RP_ID and u.scheme in ("http", "https")
    except Exception: return False

def _client_data(cdj_b64: str, typ: str, challenge: bytes):
    raw = unb64u(cdj_b64); cd = json.loads(raw)
    if cd.get("type") != typ: raise ValueError(f"clientData type is {cd.get('type')}, wanted {typ}")
    if cd.get("challenge") != b64u(challenge): raise ValueError("challenge mismatch")
    if not _origin_ok(cd.get("origin", "")): raise ValueError(f"origin {cd.get('origin')} not allowed")
    return raw

def verify_assertion(key: dict, challenge: bytes, a: dict, check_count: bool = True) -> dict:
    """Raises ValueError on any failure; returns parsed authData. `a` = {authenticatorData, clientDataJSON, signature} (b64url)."""
    raw_cd = _client_data(a["clientDataJSON"], "webauthn.get", challenge)
    ad_b = unb64u(a["authenticatorData"]); ad = parse_auth_data(ad_b)
    if ad["rp_id_hash"] != hashlib.sha256(RP_ID.encode()).digest(): raise ValueError("rpId hash mismatch")
    if not ad["flags"] & 0x01: raise ValueError("user not present")
    if not ad["flags"] & 0x04: raise ValueError("user not verified (Touch ID required)")
    if not p256_verify(int(key["x"], 16), int(key["y"], 16), ad_b + hashlib.sha256(raw_cd).digest(), unb64u(a["signature"])):
        raise ValueError("signature does not verify")
    if check_count and (ad["sign_count"] or key.get("sign_count")) and ad["sign_count"] <= key.get("sign_count", 0):
        raise ValueError("signature counter went backwards (cloned key?)")
    return ad

class Signer:
    def __init__(self, home: Path): self.s = Store(home)

    # ---- keys: one root, every later key vouched for by an already-trusted key ----
    @staticmethod
    def key_digest(k: dict) -> str:
        return hashlib.sha256(f"{k['cred_id']}|{k['x']}|{k['y']}".encode()).hexdigest()

    def _rec_ok(self, rec: dict, k: dict) -> bool:
        try:
            verify_assertion(k, challenge_for(rec["purpose"], rec["name"], rec["digest"], rec["nonce"]), rec["assertion"], check_count=False)
            return True
        except (ValueError, KeyError):
            return False

    def trusted(self) -> list:
        """Keys that count. The first enrolled key is the root; any other key counts only
        if an 'add-key' signature over exactly that key re-verifies against a key that
        already counts. A key written into keys.json by hand counts for nothing."""
        ks = self.s.keys()
        if not ks: return []
        trusted = [ks[0]]; rest = ks[1:]; adds = [r for r in self.s.sigs() if r.get("purpose") == "add-key"]
        grew = True
        while grew and rest:
            grew = False
            for k in list(rest):
                by = {t["cred_id"]: t for t in trusted}
                if any(r.get("name") == k["fingerprint"] and r.get("digest") == self.key_digest(k)
                       and r.get("cred_id") in by and self._rec_ok(r, by[r["cred_id"]]) for r in adds):
                    trusted.append(k); rest.remove(k); grew = True
        return trusted

    def enroll_begin(self) -> dict:
        ks = self.s.keys()
        ch = secrets.token_bytes(32); self.s.pending["enroll"] = (ch, time.time())
        sel = {"userVerification": "required", "residentKey": "preferred"}
        if not ks: sel["authenticatorAttachment"] = "platform"     # the root is this Mac's Touch ID
        return {"second_key": bool(ks),
                "publicKey": {"challenge": b64u(ch), "rp": {"id": RP_ID, "name": "Iris Prime"},
                "user": {"id": b64u(b"doc"), "name": "Doc", "displayName": "Christopher Hoffpauir"},
                "pubKeyCredParams": [{"type": "public-key", "alg": -7}], "timeout": 120000, "attestation": "none",
                "excludeCredentials": [{"type": "public-key", "id": k["cred_id"]} for k in ks],
                "authenticatorSelection": sel}}

    def enroll_finish(self, b: dict) -> dict:
        ch, t = self.s.pending.pop("enroll", (None, 0))
        if not ch or time.time() - t > 300: raise ValueError("no enrolment in progress (or it expired)")
        _client_data(b["clientDataJSON"], "webauthn.create", ch)
        att, _ = cbor_decode(unb64u(b["attestationObject"])); ad = parse_auth_data(att["authData"])
        if ad["rp_id_hash"] != hashlib.sha256(RP_ID.encode()).digest(): raise ValueError("rpId hash mismatch")
        if not ad["flags"] & 0x04: raise ValueError("user not verified (Touch ID required)")
        c = ad.get("cose") or {}
        if c.get(1) != 2 or c.get(3) != -7 or c.get(-1) != 1: raise ValueError("key must be EC2 / ES256 / P-256")
        x, y = int.from_bytes(c[-2], "big"), int.from_bytes(c[-3], "big")
        if not _on_curve((x, y)): raise ValueError("public key not on P-256")
        key = {"cred_id": b64u(ad["cred_id"]), "x": f"{x:064x}", "y": f"{y:064x}", "sign_count": ad["sign_count"],
               "enrolled": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "fmt": att.get("fmt"),
               "fingerprint": hashlib.sha256(bytes.fromhex(f"{x:064x}{y:064x}")).hexdigest()[:16]}
        ks = self.s.keys()
        if not ks:
            key["root"] = True
            self.s.save_keys([key]); self.s.log(event="enrolled", fingerprint=key["fingerprint"], root=True)
            return {"ok": True, "fingerprint": key["fingerprint"]}
        if any(k["cred_id"] == key["cred_id"] for k in ks): raise ValueError("that key is already enrolled")
        self.s.pending["newkey"] = (key, time.time())
        self.s.log(event="second_key_proposed", fingerprint=key["fingerprint"])
        return {"ok": False, "needs_approval": True, "fingerprint": key["fingerprint"],
                "approve": self.sign_blob_begin("add-key", key["fingerprint"], self.key_digest(key))}

    def approve_finish(self, b: dict) -> dict:
        """The touch from an EXISTING key that lets the proposed key in."""
        nk, t = self.s.pending.get("newkey", (None, 0))
        if not nk or time.time() - t > 300: raise ValueError("no new key waiting for approval (or it expired)")
        if b.get("credentialId") == nk["cred_id"]: raise ValueError("a new key cannot approve itself")
        r = self.sign_blob_finish(b)
        if r.get("digest") != self.key_digest(nk): raise ValueError("that approval was for something else")
        self.s.pending.pop("newkey", None)
        ks = self.s.keys(); nk["added_by"] = next(k["fingerprint"] for k in ks if k["cred_id"] == b["credentialId"])
        self.s.save_keys(ks + [nk]); self.s.log(event="second_key_added", fingerprint=nk["fingerprint"], added_by=nk["added_by"])
        if nk["fingerprint"] not in [k["fingerprint"] for k in self.trusted()]: raise ValueError("internal: approved key failed the trust check")
        return {"ok": True, "fingerprint": nk["fingerprint"], "added_by": nk["added_by"]}

    def sign_begin(self, purpose: str, name: str, app_dir) -> dict:
        ks = self.trusted()
        if not ks: return {"error": "no key enrolled yet"}
        m = manifest(app_dir); nonce = secrets.token_hex(16); ch = challenge_for(purpose, name, m["digest"], nonce)
        self.s.pending[("sign", nonce)] = (purpose, name, str(app_dir), m["digest"], m["files"], time.time())
        return {"nonce": nonce, "digest": m["digest"], "files": m["files"],
                "publicKey": {"challenge": b64u(ch), "rpId": RP_ID, "timeout": 120000, "userVerification": "required",
                              "allowCredentials": [{"type": "public-key", "id": k["cred_id"]} for k in ks]}}

    def sign_finish(self, b: dict) -> dict:
        p = self.s.pending.pop(("sign", b.get("nonce")), None)
        if not p or time.time() - p[5] > 300: raise ValueError("no signing in progress for that nonce (or it expired)")
        purpose, name, app_dir, digest, files, _ = p
        ks = self.s.keys(); tr = {k["cred_id"] for k in self.trusted()}
        key = next((k for k in ks if k["cred_id"] == b.get("credentialId") and k["cred_id"] in tr), None)
        if not key: raise ValueError("unknown or untrusted key")
        if manifest(app_dir)["digest"] != digest: raise ValueError("the build changed while you were signing; sign again")
        ad = verify_assertion(key, challenge_for(purpose, name, digest, b["nonce"]), b)
        key["sign_count"] = ad["sign_count"]; self.s.save_keys(ks)
        rec = {"purpose": purpose, "name": name, "digest": digest, "files": files, "nonce": b["nonce"], "cred_id": key["cred_id"],
               "key_fingerprint": key["fingerprint"], "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "assertion": {k: b[k] for k in ("authenticatorData", "clientDataJSON", "signature")}}
        self.s.add_sig(rec); self.s.log(event="signed", purpose=purpose, name=name, digest=digest, files=files)
        return {"ok": True, "digest": digest, "files": files}

    # ---- generic blob signing (PRIME-SIGN-001 shared with budget keeper) ----
    def sign_blob_begin(self, purpose: str, name: str, digest: str) -> dict:
        ks = self.trusted()
        if not ks: return {"error": "no key enrolled yet"}
        nonce = secrets.token_hex(16); ch = challenge_for(purpose, name, digest, nonce)
        self.s.pending[("blob", nonce)] = (purpose, name, digest, time.time())
        return {"nonce": nonce, "digest": digest,
                "publicKey": {"challenge": b64u(ch), "rpId": RP_ID, "timeout": 120000, "userVerification": "required",
                              "allowCredentials": [{"type": "public-key", "id": k["cred_id"]} for k in ks]}}

    def sign_blob_finish(self, b: dict) -> dict:
        p = self.s.pending.pop(("blob", b.get("nonce")), None)
        if not p or time.time() - p[3] > 300: raise ValueError("no signing in progress for that nonce (or it expired)")
        purpose, name, digest, _ = p
        ks = self.s.keys(); tr = {k["cred_id"] for k in self.trusted()}
        key = next((k for k in ks if k["cred_id"] == b.get("credentialId") and k["cred_id"] in tr), None)
        if not key: raise ValueError("unknown or untrusted key")
        ad = verify_assertion(key, challenge_for(purpose, name, digest, b["nonce"]), b)
        key["sign_count"] = ad["sign_count"]; self.s.save_keys(ks)
        rec = {"purpose": purpose, "name": name, "digest": digest, "nonce": b["nonce"], "cred_id": key["cred_id"],
               "key_fingerprint": key["fingerprint"], "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "assertion": {k: b[k] for k in ("authenticatorData", "clientDataJSON", "signature")}}
        self.s.add_sig(rec); self.s.log(event="signed_blob", purpose=purpose, name=name, digest=digest)
        return {"ok": True, "digest": digest}

    def check_blob(self, purpose: str, name: str, digest: str) -> dict:
        """Does a stored, re-verifiable signature cover exactly this digest right now?"""
        ks = {k["cred_id"]: k for k in self.trusted()}
        if not ks: return {"ok": False, "why": "no key enrolled"}
        seen = False
        for rec in reversed(self.s.sigs()):
            if rec.get("purpose") != purpose or rec.get("name") != name: continue
            seen = True
            if rec.get("digest") != digest: continue
            k = ks.get(rec.get("cred_id"))
            if not k: continue
            try: verify_assertion(k, challenge_for(purpose, name, digest, rec["nonce"]), rec["assertion"], check_count=False)
            except ValueError: continue
            return {"ok": True, "digest": digest, "signed_utc": rec["utc"], "key_fingerprint": k["fingerprint"]}
        return {"ok": False, "digest": digest, "why": "signed, but the record has changed since" if seen else "not signed by Doc's fingerprint"}

    def check(self, purpose: str, name: str, app_dir) -> dict:
        """Does a stored, re-verifiable signature cover this exact tree right now?"""
        ks = {k["cred_id"]: k for k in self.trusted()}
        if not ks: return {"ok": False, "why": "no key enrolled"}
        d = manifest(app_dir)["digest"]; seen = False
        for rec in reversed(self.s.sigs()):
            if rec.get("purpose") != purpose or rec.get("name") != name: continue
            seen = True
            if rec.get("digest") != d: continue
            k = ks.get(rec.get("cred_id"))
            if not k: continue
            try: verify_assertion(k, challenge_for(purpose, name, d, rec["nonce"]), rec["assertion"], check_count=False)
            except ValueError: continue
            return {"ok": True, "digest": d, "signed_utc": rec["utc"], "key_fingerprint": k["fingerprint"]}
        return {"ok": False, "digest": d, "why": "signed, but the build has changed since" if seen else "Doc's fingerprint has not signed this build"}

PAGE = """<!doctype html><meta charset=utf-8><title>Iris Prime · fingerprint</title>
<style>body{font:15px -apple-system,system-ui;background:#0d1117;color:#e6edf3;max-width:640px;margin:40px auto;padding:0 16px}
button{font:inherit;padding:8px 16px;border-radius:8px;border:1px solid #3fb6c6;background:#10262b;color:#e6edf3;cursor:pointer;margin:4px 0}
input{font:inherit;padding:6px;border-radius:6px;border:1px solid #30363d;background:#161b22;color:#e6edf3}pre{white-space:pre-wrap;background:#161b22;padding:10px;border-radius:8px}</style>
<h2>Iris Prime · fingerprint</h2><p>Your Touch ID locks a build in. Open this page at <b>localhost</b> on this Mac.</p>
<div id=st>…</div><p><button id=en>Enrol Touch ID</button> <small>(a second key, e.g. a security key or your iPhone, must be approved with a key you already have)</small></p>
<p>Candidate <input id=nm placeholder="candidate name"> <button id=sg>Sign this build</button></p><pre id=out></pre>
<script>
const B=s=>Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/')+'==='.slice((s.length+3)%4)),c=>c.charCodeAt(0));
const U=b=>btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,'');
const out=t=>document.getElementById('out').textContent=typeof t=='string'?t:JSON.stringify(t,null,1);
const J=(u,b)=>fetch(u,{method:b?'POST':'GET',headers:{'content-type':'application/json'},body:b?JSON.stringify(b):undefined}).then(r=>r.json());
J('/api/prime-sign/v1/status').then(s=>document.getElementById('st').textContent=s.enrolled?('Key enrolled · '+s.fingerprint):'No key enrolled yet');
const guard=f=>async()=>{try{await f()}catch(e){out('refused: '+(e&&e.message||e))}};
en.onclick=guard(async()=>{const o=await J('/api/prime-sign/v1/enroll/begin',{});if(o.error)return out(o.error);const p=o.publicKey;
 p.challenge=B(p.challenge);p.user.id=B(p.user.id);const c=await navigator.credentials.create({publicKey:p});
 let r=await J('/api/prime-sign/v1/enroll/finish',{clientDataJSON:U(c.response.clientDataJSON),attestationObject:U(c.response.attestationObject)});
 if(r.needs_approval){out('New key '+r.fingerprint+' — now touch a key you ALREADY have to let it in');const o2=r.approve,q=o2.publicKey;q.challenge=B(q.challenge);q.allowCredentials.forEach(c=>c.id=B(c.id));
  const a=await navigator.credentials.get({publicKey:q});r=await J('/api/prime-sign/v1/enroll/approve',{nonce:o2.nonce,credentialId:U(a.rawId),authenticatorData:U(a.response.authenticatorData),clientDataJSON:U(a.response.clientDataJSON),signature:U(a.response.signature)});}
 out(r);});
sg.onclick=guard(async()=>{const o=await J('/api/prime-sign/v1/sign/begin',{name:nm.value});if(o.error)return out(o.error);out('Signing '+o.files+' files, digest '+o.digest);
 const p=o.publicKey;p.challenge=B(p.challenge);p.allowCredentials.forEach(c=>c.id=B(c.id));const a=await navigator.credentials.get({publicKey:p});
 out(await J('/api/prime-sign/v1/sign/finish',{nonce:o.nonce,credentialId:U(a.rawId),authenticatorData:U(a.response.authenticatorData),clientDataJSON:U(a.response.clientDataJSON),signature:U(a.response.signature)}));});
</script>"""

def register(app, home=None, candidate_dir=None):
    home = Path(home or os.environ.get("SELFLIGHT_HOME", str(Path.home() / ".selflight")))
    S = Signer(home)
    def loopback(req): return (req.client.host if req.client else "") in ("127.0.0.1", "::1", "localhost")
    def deny(code, msg): return JSONResponse({"ship": SHIP, "error": msg}, status_code=code)
    def app_dir_of(name):
        try:
            import release_gate as rg
            c = rg._read().get(name)
            if c and c.get("app_dir"): return Path(c["app_dir"])
        except Exception: pass
        if candidate_dir: return Path(candidate_dir(name)) if callable(candidate_dir) else Path(candidate_dir) / name / "app"
        return None

    @app.get("/prime-sign")
    async def page(req: Request):
        if not loopback(req): return deny(403, "this Mac only")
        return HTMLResponse(PAGE)
    @app.get("/api/prime-sign/v1/status")
    async def status(req: Request):
        if not loopback(req): return deny(403, "this Mac only")
        ks = S.s.keys()
        tr = S.trusted()
        return {"ship": SHIP, "enrolled": bool(ks), "fingerprint": ks[0]["fingerprint"] if ks else None,
                "keys": [{"fingerprint": k["fingerprint"], "root": k is ks[0], "added_by": k.get("added_by"), "trusted": k in tr} for k in ks],
                "signatures": [{k: r[k] for k in ("purpose", "name", "digest", "files", "utc")} for r in S.s.sigs()[-10:]]}
    @app.post("/api/prime-sign/v1/enroll/begin")
    async def eb(req: Request):
        if not loopback(req): return deny(403, "this Mac only")
        return S.enroll_begin()
    @app.post("/api/prime-sign/v1/enroll/finish")
    async def ef(req: Request):
        if not loopback(req): return deny(403, "this Mac only")
        try: return S.enroll_finish(await req.json())
        except (ValueError, KeyError) as e: S.s.log(event="enroll_refused", why=str(e)); return deny(400, str(e))
    @app.post("/api/prime-sign/v1/enroll/approve")
    async def ea(req: Request):
        if not loopback(req): return deny(403, "this Mac only")
        try: return S.approve_finish(await req.json())
        except (ValueError, KeyError) as e: S.s.log(event="approve_refused", why=str(e)); return deny(400, str(e))
    @app.post("/api/prime-sign/v1/sign/begin")
    async def sb(req: Request):
        if not loopback(req): return deny(403, "this Mac only")
        b = await req.json(); name = str(b.get("name", "")).strip().lower(); d = app_dir_of(name)
        if not d or not d.is_dir(): return deny(404, f"no candidate {name!r}")
        return S.sign_begin("promote", name, d)
    @app.post("/api/prime-sign/v1/sign/finish")
    async def sf(req: Request):
        if not loopback(req): return deny(403, "this Mac only")
        try: return S.sign_finish(await req.json())
        except (ValueError, KeyError) as e: S.s.log(event="sign_refused", why=str(e)); return deny(400, str(e))
    @app.get("/api/prime-sign/v1/check")
    async def ck(req: Request, name: str):
        if not loopback(req): return deny(403, "this Mac only")
        d = app_dir_of(name.strip().lower())
        if not d or not d.is_dir(): return deny(404, f"no candidate {name!r}")
        return S.check("promote", name.strip().lower(), d)

    hooked = "promote not hooked"
    try:
        import release_gate as rg
        orig = rg.Gate.promote
        if not getattr(orig, "_prime_sign", False):
            def promote(self, name, confirm, local, dry_run=False):
                d = app_dir_of(name); c = S.check("promote", name, d) if d and d.is_dir() else {"ok": False, "why": f"no candidate {name}"}
                if not c["ok"]:
                    S.s.log(event="promote_refused", name=name, why=c["why"], dry_run=dry_run)
                    rg._led(kind="promote", name=name, refused=f"PRIME-LOCK: {c['why']}")
                    return 403, {"ok": False, "refused": f"PRIME-LOCK: {c['why']}", "signature": c}
                code, res = orig(self, name, confirm, local, dry_run)
                if isinstance(res, dict): res["signature"] = c
                return code, res
            promote._prime_sign = True; rg.Gate.promote = promote; hooked = "promote requires Doc's fingerprint"
    except Exception as e: hooked = f"promote not hooked ({e})"
    return f"Prime sign: {hooked}; page /prime-sign ({SHIP})"
