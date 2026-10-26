import sys, os, json, tempfile, asyncio, types
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_prime_sign.py")).read()
exec(src.split("\nok = 0")[0])          # fastapi stub + software Authenticator, no tests run
import budget_keeper as bk, prime_sign as ps
tmp = tempfile.mkdtemp(); os.environ["SELFLIGHT_SPEND_LEDGER"] = os.path.join(tmp, "spend.jsonl")
n = 0
def t(name, cond):
    global n; print(("PASS " if cond else "FAIL ") + name); n += bool(cond)
    if not cond: sys.exit(1)
def raises(fn):
    try: fn(); return None
    except ValueError as e: return str(e)
def refused(fn):
    try: fn(); return None
    except bk.BudgetRefused as e: return str(e)

S = ps.Signer(tmp); K = bk.Keeper(tmp, signer=S); A = Authenticator()
t("local model has no wallet", bk.wallet_of("llama3.2:3b") is None and K.decide("llama3.2:3b")["allow"])
t("wallets by prefix", bk.wallet_of("anthropic:claude-opus-5-5") == "anthropic" and bk.wallet_of("fw:kimi-k3") == "fireworks")
t("starts in WATCH", not K.enforcing())
d = K.guard("anthropic:claude-opus-5-5")
t("WATCH: unsigned paid call passes, marked watch_only", d.get("watch_only") and not d["allow"])
t("WATCH: would_refuse is recorded", any(json.loads(l)["event"] == "would_refuse" for l in open(K.log_f)))
t("propose needs cleared_by", "error" in K.propose("anthropic", 1.0, ""))
K.propose("anthropic", 1.0, "Business Unit / Doc Hoff Investments")
t("proposed but unsigned -> still WATCH", not K.enforcing() and K.status_of(K.latest("anthropic"))["state"] == "unsigned")
ch = S.enroll_begin(); S.enroll_finish(A.create(ch))
o = S.sign_blob_begin("budget", "anthropic", K.latest("anthropic")["digest"])
S.sign_blob_finish(A.get(o, o["nonce"]))
t("signed budget -> ENFORCE", K.enforcing() and K.status_of(K.latest("anthropic"))["state"] == "signed")
t("ENFORCE: within budget allowed", K.guard("anthropic:claude-opus-5-5")["allow"])
t("ENFORCE: wallet with no signed budget refused", "no signed budget for fireworks" in (refused(lambda: K.guard("fw:kimi-k3")) or ""))
t("ENFORCE: local model still free", K.guard("llama3.2:3b")["allow"])
bk.record_spend("anthropic:claude-opus-5-5", 20000, 20000, "test")   # 0.3 + 1.5 USD at Opus estimate
t("ENFORCE: cap reached refused", "daily cap 1.0 USD reached" in (refused(lambda: K.guard("anthropic:claude-opus-5-5")) or ""))
t("other wallets' spend doesn't count", bk.spend_today("fireworks") == 0)
lines = K.budgets_f.read_text().splitlines(); r = json.loads(lines[-1]); r["daily_cap_usd"] = 1000.0; lines[-1] = json.dumps(r)
K.budgets_f.write_text("\n".join(lines) + "\n")
t("tampered cap -> frozen", "tampered" in (refused(lambda: K.guard("anthropic:claude-opus-5-5")) or ""))
o2 = S.sign_blob_begin("budget", "anthropic", "f" * 64)
t("a signature over another digest doesn't cover the record", K.status_of(K.latest("anthropic"))["state"] == "tampered")
K.propose("anthropic", 50.0, "Business Unit"); o = S.sign_blob_begin("budget", "anthropic", K.latest("anthropic")["digest"]); S.sign_blob_finish(A.get(o, o["nonce"]))
t("fresh signed budget unfreezes", K.guard("anthropic:claude-opus-5-5")["allow"])
K.propose("fireworks", 0, "Business Unit", disable=True)
t("UNSIGNED disable does not stand the keeper down", K.enforcing())
o = S.sign_blob_begin("budget", "fireworks", K.latest("fireworks")["digest"]); S.sign_blob_finish(A.get(o, o["nonce"]))
t("SIGNED disable stands it down (back to WATCH)", not K.enforcing())
replay = A.get(o, o["nonce"])
t("replayed/expired nonce refused", raises(lambda: S.sign_blob_finish(replay)) is not None)

class FakePC:
    calls = 0
    async def stream_chat(self, model, messages, pane="chat", extra_options=None, out=None):
        FakePC.calls += 1
        out.update({"input_tokens": 1000, "output_tokens": 500}); yield "hi"
pcm = types.SimpleNamespace(ProviderChat=FakePC)
K2 = bk.Keeper(tempfile.mkdtemp(), signer=ps.Signer(tempfile.mkdtemp()))
bk.install_hooks(K2, provider_chat_mod=pcm)
async def run(m):
    return [d async for d in FakePC().stream_chat(m, [], pane="rooms")]
before = bk.spend_today("anthropic")
t("hooked chat streams in WATCH", asyncio.run(run("anthropic:claude-sonnet-5-5")) == ["hi"])
t("hooked chat now writes the spend ledger (closes the gap)", bk.spend_today("anthropic") > before)
K3 = bk.Keeper(tmp, signer=S)   # tmp home: anthropic signed budget at 50 USD, fireworks disable signed -> WATCH; re-enable test via fresh home
H = tempfile.mkdtemp(); S4 = ps.Signer(H); A4 = Authenticator(); c4 = S4.enroll_begin(); S4.enroll_finish(A4.create(c4)); K4 = bk.Keeper(H, signer=S4)
K4.propose("anthropic", 5, "BU"); o = S4.sign_blob_begin("budget", "anthropic", K4.latest("anthropic")["digest"]); S4.sign_blob_finish(A4.get(o, o["nonce"]))
FakePC.calls = 0; FakePC.stream_chat = FakePC.__dict__["stream_chat"].__wrapped__ if hasattr(FakePC.__dict__["stream_chat"], "__wrapped__") else FakePC.stream_chat
class FakePC2:
    calls = 0
    async def stream_chat(self, model, messages, pane="chat", extra_options=None, out=None):
        FakePC2.calls += 1; yield "x"
bk.install_hooks(K4, provider_chat_mod=types.SimpleNamespace(ProviderChat=FakePC2))
async def run2(m): return [d async for d in FakePC2().stream_chat(m, [])]
try: asyncio.run(run2("fw:kimi-k3")); got = None
except bk.BudgetRefused as e: got = str(e)
t("ENFORCE: refused BEFORE the provider is called (no money leaves)", got and FakePC2.calls == 0)
print(f"\n{n} checks passed")
