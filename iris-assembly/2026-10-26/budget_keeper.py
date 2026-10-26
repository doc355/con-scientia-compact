# budget_keeper.py — BUDGET-KEEPER-001 (Rooms experimental copy only)
#
# Doc's rule (task 107): "Budgets are cleared by the business unit and signed by
# Doc's fingerprint; the keeper re-verifies the signature before every spend or
# trade; tampered/unsigned -> freeze." This is the plain-code keeper that sits in
# front of every PAID model call and enforces that.
#
# WATCH vs ENFORCE. It ships in WATCH: it records exactly what it WOULD refuse and
# changes nothing, because Doc has not enrolled/signed yet and enforcing now would
# turn off every paid model. It flips to ENFORCE the moment a signed budget exists.
# Turning enforcement back OFF needs a signed record (his fingerprint) — never a flag.
#
# It shares the Prime fingerprint (prime_sign.Signer): a budget record is signed with
# the SAME passkey as a Prime build, via sign_blob/check_blob. No second key, no
# second lock.
#
# The cap is PER WALLET and counted from the ONE shared spend ledger
# (~/.selflight/spend.jsonl), which both the chat pane (via this keeper) and the
# foreman bridge write to — so the cap finally covers every paid path, not just the
# bridge.
from __future__ import annotations
import hashlib, json, os, threading, time
from pathlib import Path
try:   # module level: FastAPI resolves string annotations against module globals
    from fastapi import Request
    from fastapi.responses import HTMLResponse, JSONResponse
    _Rq = Request  # from fastapi import Request as _Rq (marker)
except ImportError:
    Request = HTMLResponse = JSONResponse = object

SHIP = "BUDGET-KEEPER-001"
# model-string prefix -> wallet name. A wallet is a place money leaves from.
WALLET_PREFIX = {"anthropic:": "anthropic", "fw:": "fireworks", "openai:": "openai",
                 "pplx:": "perplexity", "perplexity:": "perplexity", "gemini:": "google",
                 "google:": "google", "xai:": "xai", "devin:": "devin"}


def _utc() -> str: return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def wallet_of(model: str) -> str | None:
    """Which wallet a model spends from, or None for a $0 local model."""
    m = model or ""
    for pre, w in WALLET_PREFIX.items():
        if m.startswith(pre): return w
    try:
        import provider_chat as pc
        if pc.is_provider_unit(m):
            # a declared provider unit without one of the known prefixes
            return (m.split(":", 1)[0] or "other")
    except Exception:
        pass
    try:
        import free_cloud as fc
        if m.split("@", 1)[0].split(":", 1)[0] in getattr(fc, "CLOUD_ALIASES", ()):
            return "fireworks"   # the iris-ola alias is a fw:kimi-k3 backend
    except Exception:
        pass
    return None


# ---- spend ledger (shared with ollama_bridge) ----
def _spend_path() -> Path:
    return Path(os.environ.get("SELFLIGHT_SPEND_LEDGER", os.path.expanduser("~/.selflight/spend.jsonl")))


def spend_today(wallet: str | None = None) -> float:
    """USD spent today, from the one shared ledger. Keyed by wallet when given."""
    day = _utc()[:10]; total = 0.0
    try:
        for ln in open(_spend_path()):
            try:
                r = json.loads(ln)
                if not r.get("t", "").startswith(day): continue
                if wallet and wallet_of(str(r.get("model", ""))) != wallet: continue
                total += float(r.get("usd_est", 0) or 0)
            except Exception: pass
    except FileNotFoundError: pass
    return round(total, 5)


def _price(model: str):
    try:
        import ollama_bridge as ob
        return ob._price(model)
    except Exception:
        return (15.0, 75.0)   # conservative default (Opus-tier), never zero


def record_spend(model: str, tin: int, tout: int, caller: str, note: str = "") -> float:
    """Write one spend line in the shared ledger's shape (for paths that don't already)."""
    pin, pout = _price(model); usd = tin / 1e6 * pin + tout / 1e6 * pout
    p = _spend_path(); p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as h:
        h.write(json.dumps({"t": _utc(), "model": model, "in": tin, "out": tout,
                            "usd_est": round(usd, 5), "caller": caller, "note": note,
                            "by": "budget_keeper"}) + "\n")
    return usd


class BudgetRefused(RuntimeError):
    pass


def _rec_digest(rec: dict) -> str:
    sign = {k: rec[k] for k in ("wallet", "daily_cap_usd", "per_tx_cap_usd", "cleared_by", "created_utc", "disable")}
    return hashlib.sha256(json.dumps(sign, sort_keys=True).encode()).hexdigest()


class Keeper:
    PURPOSE = "budget"

    def __init__(self, home: Path, signer=None):
        self.home = Path(home); self.dir = self.home / "budget-keeper"; self.dir.mkdir(parents=True, exist_ok=True)
        self.budgets_f = self.dir / "budgets.jsonl"; self.log_f = self.dir / "ledger.jsonl"
        self.lock = threading.Lock()
        self.signer = signer

    def _signer(self):
        if self.signer: return self.signer
        import prime_sign as ps
        self.signer = ps.Signer(self.home); return self.signer

    def log(self, **kw):
        kw["utc"] = _utc()
        with open(self.log_f, "a") as f: f.write(json.dumps(kw) + "\n")

    def _all(self) -> list:
        try: return [json.loads(l) for l in self.budgets_f.read_text().splitlines() if l.strip()]
        except Exception: return []

    def latest(self, wallet: str) -> dict | None:
        for r in reversed(self._all()):
            if r.get("wallet") == wallet: return r
        return None

    def propose(self, wallet: str, daily_cap_usd: float, cleared_by: str,
                per_tx_cap_usd: float = 0.0, note: str = "", disable: bool = False) -> dict:
        """Business-unit clearance + a budget to be signed. cleared_by is SELF-REPORTED
        here: the real business-unit approval flow is not built yet, and the record says so."""
        if not cleared_by or not str(cleared_by).strip():
            return {"error": "cleared_by is required (which business unit cleared this budget)"}
        rec = {"ship": SHIP, "wallet": wallet, "daily_cap_usd": float(daily_cap_usd),
               "per_tx_cap_usd": float(per_tx_cap_usd), "cleared_by": str(cleared_by).strip(),
               "clearance_note": "SELF-REPORTED; business-unit approval flow not yet built",
               "disable": bool(disable), "created_utc": _utc()}
        rec["digest"] = _rec_digest(rec)
        with self.lock, open(self.budgets_f, "a") as f: f.write(json.dumps(rec) + "\n")
        self.log(event="proposed", wallet=wallet, cap=daily_cap_usd, cleared_by=cleared_by, disable=disable, digest=rec["digest"])
        return {"ok": True, "record": rec}

    def status_of(self, rec: dict | None) -> dict:
        if not rec: return {"state": "none", "why": "no budget proposed for this wallet"}
        if _rec_digest(rec) != rec.get("digest"):
            return {"state": "tampered", "why": "the budget record on disk was altered after it was written"}
        chk = self._signer().check_blob(self.PURPOSE, rec["wallet"], rec["digest"])
        if chk.get("ok"):
            return {"state": "disabled" if rec.get("disable") else "signed",
                    "signed_utc": chk.get("signed_utc"), "fingerprint": chk.get("key_fingerprint")}
        return {"state": "unsigned", "why": chk.get("why")}

    def enforcing(self) -> bool:
        """STICKY. Keyed on Doc's signatures, not on the (editable) budget records:
        once any budget signature re-verifies, the keeper enforces, and it returns to
        WATCH only if the LATEST valid budget signature covers an intact 'disable'
        record. Tampering with or deleting a budget record can never drop it to WATCH."""
        S = self._signer()
        intact = {r.get("digest"): r for r in self._all() if _rec_digest(r) == r.get("digest")}
        last = None
        for sig in S.s.sigs():
            if sig.get("purpose") != self.PURPOSE: continue
            if S.check_blob(self.PURPOSE, sig.get("name"), sig.get("digest")).get("ok"): last = sig
        if not last: return False
        r = intact.get(last["digest"])
        return not (r and r.get("disable"))

    def decide(self, model: str) -> dict:
        """What the keeper thinks of a paid call, independent of watch/enforce."""
        w = wallet_of(model)
        if not w: return {"wallet": None, "allow": True, "why": "local model, no wallet"}
        rec = self.latest(w); st = self.status_of(rec)
        if st["state"] == "tampered":
            return {"wallet": w, "allow": False, "freeze": True, "why": f"budget for {w} was tampered with — frozen"}
        if st["state"] in ("none", "unsigned"):
            return {"wallet": w, "allow": False, "why": f"no signed budget for {w} ({st.get('why')})"}
        if st["state"] == "disabled":
            return {"wallet": w, "allow": True, "why": f"keeper stood down for {w} by a signed record"}
        cap = float(rec["daily_cap_usd"]); spent = spend_today(w)
        if cap and spent >= cap:
            return {"wallet": w, "allow": False, "why": f"{w} daily cap {cap} USD reached (spent {spent})", "cap": cap, "spent": spent}
        return {"wallet": w, "allow": True, "why": f"{w} within budget (spent {spent} of {cap} USD)", "cap": cap, "spent": spent}

    def guard(self, model: str, caller: str = "chat") -> dict:
        """Called before every paid call. In ENFORCE, raises BudgetRefused on a no.
        In WATCH, never raises — it records would_refuse and lets the call through."""
        d = self.decide(model); enforce = self.enforcing()
        if d["allow"]:
            self.log(event="allow", model=model, wallet=d["wallet"], caller=caller, enforce=enforce, why=d["why"])
            return d
        kind = "refused" if enforce else "would_refuse"
        self.log(event=kind, model=model, wallet=d["wallet"], caller=caller, why=d["why"], freeze=d.get("freeze", False))
        if enforce:
            raise BudgetRefused(f"BUDGET-KEEPER: {d['why']}")
        d["watch_only"] = True
        return d


KEEPER: "Keeper | None" = None


def keeper_says(model: str, caller: str) -> str | None:
    """For call sites that fall back instead of raising (the foreman bridge).
    Returns a refusal reason, or None to proceed. A keeper bug fails CLOSED only
    while enforcing; in WATCH it is logged and the call proceeds."""
    k = KEEPER
    if not k: return None
    try:
        k.guard(model, caller=caller); return None
    except BudgetRefused as e:
        return str(e)
    except Exception as e:
        try: enforcing = k.enforcing()
        except Exception: enforcing = True
        try: k.log(event="keeper_error", model=model, caller=caller, error=repr(e)[:300], enforce=enforcing)
        except Exception: pass
        return f"BUDGET-KEEPER error, refusing while enforcing: {e}" if enforcing else None


def install_hooks(k: Keeper, provider_chat_mod=None, devin_mod=None) -> list:
    done = []
    if provider_chat_mod is not None and not getattr(provider_chat_mod.ProviderChat.stream_chat, "_keeper", False):
        orig = provider_chat_mod.ProviderChat.stream_chat

        async def stream_chat(self, model, messages, pane="chat", extra_options=None, out=None):
            k.guard(model, caller=f"chat:{pane}")          # raises BudgetRefused only when enforcing
            o = out if out is not None else {}
            async for d in orig(self, model, messages, pane=pane, extra_options=extra_options, out=o):
                yield d
            w = wallet_of(model)
            if w and w != "devin":
                tin, tout = int(o.get("input_tokens") or 0), int(o.get("output_tokens") or 0)
                cr, cw = int(o.get("cache_read_input_tokens") or 0), int(o.get("cache_creation_input_tokens") or 0)
                note = "" if (tin or tout) else "provider reported no token counts"
                record_spend(model, tin + cw + cr // 10, tout, caller=f"chat:{pane}", note=note)
        stream_chat._keeper = True
        provider_chat_mod.ProviderChat.stream_chat = stream_chat
        done.append("provider_chat.stream_chat")
    if devin_mod is not None and not getattr(devin_mod.answer, "_keeper", False):
        orig_a = devin_mod.answer

        async def answer(unit, messages, key=None):
            k.guard(unit, caller="devin")
            return await orig_a(unit, messages, key=key)
        answer._keeper = True
        devin_mod.answer = answer
        done.append("devin_adapter.answer")
    return done


PAGE = """<!doctype html><meta charset=utf-8><title>Iris · budget keeper</title>
<style>body{font:15px -apple-system,system-ui;background:#0c1116;color:#dfe7ee;max-width:760px;margin:40px auto;padding:0 20px}
h1{font-weight:500;color:#7fd1d8}button{background:#1d6f78;color:#fff;border:0;border-radius:8px;padding:8px 14px;margin:4px 0;cursor:pointer}
input{background:#161e26;color:#dfe7ee;border:1px solid #2a3a48;border-radius:6px;padding:6px;margin:2px}pre{background:#111821;padding:12px;border-radius:8px;white-space:pre-wrap}</style>
<h1>Budget keeper</h1><p id=mode></p>
<p>Clear a daily budget for a wallet, then sign it with Touch ID. The first signed budget switches the keeper from WATCH to ENFORCE.</p>
<div><input id=w placeholder="wallet (anthropic, fireworks, openai, devin…)"><input id=c type=number step=0.5 placeholder="USD per day"><input id=by placeholder="cleared by (business unit)">
<button onclick=prop()>Propose</button></div><pre id=out></pre>
<script>
const b64u=b=>btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,'');
const unb=s=>Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/')+'==='.slice((s.length+3)%4)),c=>c.charCodeAt(0));
const J=(u,b)=>fetch(u,{method:b?'POST':'GET',headers:{'content-type':'application/json'},body:b?JSON.stringify(b):undefined}).then(r=>r.json());
async function load(){const s=await J('/api/budget/v1/status');mode.textContent='Mode: '+s.mode.toUpperCase()+(s.mode=='watch'?' (records what it would refuse; changes nothing)':'');
 out.textContent=JSON.stringify(s.wallets,null,1);}
async function prop(){const r=await J('/api/budget/v1/propose',{wallet:w.value,daily_cap_usd:+c.value,cleared_by:by.value});
 if(r.error){out.textContent=r.error;return;} await sign(r.record.wallet);}
async function sign(wallet){try{const o=await J('/api/budget/v1/sign/begin',{wallet});if(o.error){out.textContent=o.error;return;}
 const pk=o.publicKey;pk.challenge=unb(pk.challenge);pk.allowCredentials=pk.allowCredentials.map(c=>({...c,id:unb(c.id)}));
 const a=await navigator.credentials.get({publicKey:pk});
 const r=await J('/api/budget/v1/sign/finish',{nonce:o.nonce,credentialId:b64u(a.rawId),authenticatorData:b64u(a.response.authenticatorData),clientDataJSON:b64u(a.response.clientDataJSON),signature:b64u(a.response.signature)});
 out.textContent=JSON.stringify(r,null,1);load();}catch(e){out.textContent='refused: '+e.message;}}
load();</script>"""


def register(app, home=None):
    global KEEPER
    home = Path(home or os.environ.get("SELFLIGHT_HOME", str(Path.home() / ".selflight")))
    k = KEEPER = Keeper(home)
    hooked = []
    try:
        import provider_chat, devin_adapter
        hooked = install_hooks(k, provider_chat, devin_adapter)
    except Exception as e:
        k.log(event="hook_error", error=repr(e)[:300])

    def his_hand(req):
        host = req.client.host if req.client else ""
        unit = req.headers.get("x-iris-unit") == "1" or bool(req.headers.get("x-iris-caller")) or req.headers.get("x-from", "").lower().startswith("iris")
        return host in ("127.0.0.1", "::1", "localhost") and not unit

    def deny(code, msg): return JSONResponse({"ship": SHIP, "error": msg}, status_code=code)

    @app.get("/budget")
    async def page(req: Request):
        if not his_hand(req): return deny(403, "this Mac only, by hand")
        return HTMLResponse(PAGE)

    @app.get("/api/budget/v1/status")
    async def status(req: Request):
        if not his_hand(req): return deny(403, "this Mac only, by hand")
        ws = sorted({r.get("wallet") for r in k._all()} | {"anthropic", "fireworks"})
        rows = {}
        for w in ws:
            rec = k.latest(w); st = k.status_of(rec)
            rows[w] = {**st, "daily_cap_usd": (rec or {}).get("daily_cap_usd"), "cleared_by": (rec or {}).get("cleared_by"),
                       "spent_today_usd": spend_today(w)}
        tail = []
        try: tail = [json.loads(l) for l in k.log_f.read_text().splitlines()[-15:]]
        except Exception: pass
        return {"ship": SHIP, "mode": "enforce" if k.enforcing() else "watch", "wallets": rows, "hooked": hooked, "recent": tail}

    @app.post("/api/budget/v1/propose")
    async def propose(req: Request):
        if not his_hand(req): return deny(403, "this Mac only, by hand")
        b = await req.json()
        w = str(b.get("wallet") or "").strip().lower()
        if w not in set(WALLET_PREFIX.values()): return deny(400, f"unknown wallet {w!r}; one of {sorted(set(WALLET_PREFIX.values()))}")
        try: cap = float(b.get("daily_cap_usd"))
        except Exception: return deny(400, "daily_cap_usd must be a number")
        if cap < 0: return deny(400, "daily_cap_usd must be >= 0")
        r = k.propose(w, cap, b.get("cleared_by", ""), float(b.get("per_tx_cap_usd") or 0), str(b.get("note") or ""), bool(b.get("disable")))
        return r if r.get("ok") else deny(400, r["error"])

    @app.post("/api/budget/v1/sign/begin")
    async def sign_begin(req: Request):
        if not his_hand(req): return deny(403, "this Mac only, by hand")
        w = str((await req.json()).get("wallet") or "")
        rec = k.latest(w)
        if not rec: return deny(404, "no budget proposed for that wallet")
        if k.status_of(rec)["state"] == "tampered": return deny(409, "that record was altered on disk; propose a fresh one")
        return k._signer().sign_blob_begin(Keeper.PURPOSE, w, rec["digest"])

    @app.post("/api/budget/v1/sign/finish")
    async def sign_finish(req: Request):
        if not his_hand(req): return deny(403, "this Mac only, by hand")
        try:
            r = k._signer().sign_blob_finish(await req.json())
        except ValueError as e:
            k.log(event="sign_refused", why=str(e)); return deny(400, str(e))
        k.log(event="signed", digest=r.get("digest"), mode_now="enforce" if k.enforcing() else "watch")
        return {**r, "mode": "enforce" if k.enforcing() else "watch"}

    return f"Budget keeper: {'ENFORCE' if k.enforcing() else 'WATCH'}; hooks {', '.join(hooked) or 'none'}; page /budget ({SHIP})"
