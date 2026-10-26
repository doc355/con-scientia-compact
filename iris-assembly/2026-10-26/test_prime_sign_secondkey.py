import os, json, sys, tempfile
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_prime_sign.py")).read()
exec(src.split("\nok = 0")[0])
import prime_sign as ps
n = 0
def t(name, c):
    global n; print(("PASS " if c else "FAIL ") + name); n += bool(c)
    if not c: sys.exit(1)
def err(f):
    try: f(); return None
    except (ValueError, KeyError) as e: return str(e)
H = tempfile.mkdtemp(); S = ps.Signer(H); root, spare, thief = Authenticator(), Authenticator(), Authenticator()
S.enroll_finish(root.create(S.enroll_begin()))
t("root enrolled, one trusted key", len(S.trusted()) == 1 and S.s.keys()[0].get("root"))
o = S.enroll_begin(); t("second enrolment offered (not refused), any authenticator", o["second_key"] and "authenticatorAttachment" not in o["publicKey"]["authenticatorSelection"])
r = S.enroll_finish(spare.create(o))
t("second key is NOT added on its own touch", r.get("needs_approval") and len(S.s.keys()) == 1)
ap = r["approve"]
t("the new key cannot approve itself", "cannot approve itself" in (err(lambda: S.approve_finish(spare.get(ap, ap["nonce"]))) or ""))
r2 = S.approve_finish(root.get(ap, ap["nonce"]))
t("root's touch lets the spare in", r2["ok"] and len(S.trusted()) == 2 and r2["added_by"] == S.s.keys()[0]["fingerprint"])
d = "a" * 64; o = S.sign_blob_begin("budget", "anthropic", d); S.sign_blob_finish(spare.get(o, o["nonce"]))
t("the spare can sign once trusted", S.check_blob("budget", "anthropic", d)["ok"])
# attacker writes a key straight into keys.json
o = S.enroll_begin(); r = S.enroll_finish(thief.create(o)); S.s.pending.pop("newkey")
ks = S.s.keys(); ks.append({**r_key, } if False else None) if False else None
import base64
tk = json.loads(json.dumps(S.s.keys()[0])); tk.update(cred_id=thief.cred_id_b64() if hasattr(thief, "cred_id_b64") else "THIEF", fingerprint="thief0000000000")
S.s.save_keys(S.s.keys() + [tk])
t("a key written into keys.json by hand is not trusted", len(S.trusted()) == 2 and "thief0000000000" not in [k["fingerprint"] for k in S.trusted()])
d2 = "b" * 64; o = S.sign_blob_begin("budget", "fw", d2)
t("an untrusted key is not offered for signing", all(c["id"] != tk["cred_id"] for c in o["publicKey"]["allowCredentials"]))
# tamper the add-key record so the spare's vouching no longer verifies
lines = S.s.sigs_f.read_text().splitlines(); fixed = []
for l in lines:
    rr = json.loads(l)
    if rr["purpose"] == "add-key": rr["digest"] = "0" * 64
    fixed.append(json.dumps(rr))
S.s.sigs_f.write_text("\n".join(fixed) + "\n")
t("altering the vouching record un-trusts the spare", len(S.trusted()) == 1)
t("...and the spare's signatures stop counting", not S.check_blob("budget", "anthropic", d)["ok"])
print(f"\n{n} checks passed")
