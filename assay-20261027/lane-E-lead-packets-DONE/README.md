# lane-E-lead-packets — DONE packet (2026-10-27)
Seat: lane-E-lead-packets (Devin, cloud session b812053ed4ee4399a4d80f350e558f58). Director: Gopher. reply-to: COUNCIL-FLOOR.
Lead's two packets taken under seatguard: gopher_20261027_hal-probe-to-lead, gopher_20261027_iris-control-dock-candidate.

## 0. Compliance pass (garden/skills/compliance-pass.md)
- SEALS: none opened. Read: the exp candidate server code, two installed launcher scripts (read-only), HAL's health over Tailscale SSH
  (root@100.106.102.44 — the login HAL's policy allows; Doc approved the check URL), exp instance state under ~/.selflight/instances/iris-creative-exp.
  Nothing private, nothing in beings/verbatim. One leftover `grep -rl` of mine from an early Safari-rule search ran long on the MBP; killed (pids 17487/17314, 31538/31534). Other seats' long greps left alone.
- PII: none written. Target names/IPs are tailnet/LAN addresses already in the shared targets list. No names, keys, or health payloads stored.
- COST: $0. No services bought, no tokens beyond this session.
- LIABILITY: no door opened (HAL's :8765 still binds 127.0.0.1 — measured, untouched). Live Prime :8765 untouched; staged :8790 untouched. One restart of exp :8772 (announced below).
  Risk accepted and bounded: a `via` target shells `ssh -n -o BatchMode=yes <user@host> curl ...` — the user@host shape is regex-validated (`^ssh:[a-z_][a-z0-9_-]{0,31}@[A-Za-z0-9.-]{3,80}$`), anything else is refused as BLIND and never shelled (test_malformed_via_refused_not_shelled).

## 1. What changed (packet 1 — HAL probe)
Root cause (measured): HAL's Project Iris binds 127.0.0.1:8765 only. The keeper did an HTTP GET from the MBP to 100.106.102.44:8765 -> "Connection refused" ->
DOWN -> all-call hold, 217 consecutive fails in the shared store, while HAL's own `curl 127.0.0.1:8765/api/health` answered 200 the whole time.
Fix = two rules, both in the exp copy only:
- LINK-SSH-001: a target may carry `"via": "ssh:user@host"` (+ optional `via_url`, default `http://127.0.0.1:<port><path>`). The keeper then runs
  `ssh -n -o BatchMode=yes user@host curl -s -m T -o /dev/null -w %{http_code} <via_url>` instead of a GET from here. Three outcomes: UP (far-side HTTP 200-499),
  DOWN (ssh arrived, curl found nothing listening), BLIND (ssh itself failed: key, Tailscale check-mode re-auth, host unreachable). BLIND is not DOWN:
  state and fail counter untouched, no recovery rung, no all-call hold; a `sight` field flips seeing<->blind with a transitions line carrying the reason
  (incl. the Tailscale check URL when that is the reason). A via target's hold carries no http `resolve` probe (a GET could never reach it); the keeper
  clears its own hold when the via check answers UP again. write_targets now preserves via / via_url / allcall:false (it stripped them before).
- LINK-SCOPE-001: BASE = $SELFLIGHT_HOME/link-keeper when SELFLIGHT_HOME is set (every candidate launcher sets it; run-exp.sh does). Before, live Prime
  :8765, staged :8790 and exp :8772 all wrote ONE shared ~/.selflight/link-keeper/ — the repeating `FileNotFoundError: state.tmp -> state.json` in
  exp8772.log was two keepers racing one tmp file, and any targets edit from exp would have edited live Prime's watch list. Without SELFLIGHT_HOME the
  path is unchanged, so the live release's behaviour is not altered by this code even if it were ever adopted as-is.
- DEFAULT_TARGETS: the HAL http target now carries via ssh:root@100.106.102.44 (comment names the measurement and the door rule).
- Port on HAL: NOT opened. Door decision stays Doc's.

## 2. Files (exp tree ~/HIFIDecant/Selflight/candidates/iris-creative-exp-1/app/server/)
| file | sha256 after | backup |
|---|---|---|
| link_keeper.py | c50652f2d455b62e2ec24abe929c3ceae363f8c396ce9e745103c18df7516634 | link_keeper.py.pre-laneE-20261027 (sha 7d7580d8381b8e6dde2497615d1193be3128f84a3dca7eea30c1380e969eb799) |
| test_link_keeper_via_ssh.py (new) | 2569da5e3a1145aebd226090cb4bb7eadee124b54ec39b82f2bf5285961df75e | — (new file) |
| ~/.selflight/instances/iris-creative-exp/allcall/holds.json | (state) | holds.json.pre-laneE-20261027 |
| ~/.selflight/instances/iris-creative-exp/link-keeper/targets.json (new, seeded) | see SEED section | — (new; shared ~/.selflight/link-keeper/ untouched) |
Diff of link_keeper.py: link_keeper.patch (beside this README). Claims: seatguard claim lane-E-lead-packets on link_keeper.py, test_allcall.py (read, unchanged), test_link_keeper_via_ssh.py.

## 3. Tests run (on the MBP, release python, exp PYTHONPATH, SELFLIGHT_HOME=/tmp/laneE-testhome)
`python3 -m unittest test_link_keeper_via_ssh test_allcall -v` -> Ran 28 tests, OK (12 new + 16 existing all-call tests). Full output: tests.txt.
New tests prove: via target uses ssh never GET; far-side 200 -> UP; curl exit 7 -> DOWN; ssh 255 -> BLIND; BLIND keeps state/fails, no rung, no hold,
one sight transition; Tailscale check text carries the URL; ssh timeout -> BLIND; malformed via refused, not shelled; plain http target unchanged;
3x DOWN -> hold without resolve URL, then UP -> keeper clears it; write_targets keeps via/allcall; BASE follows SELFLIGHT_HOME.

## 4. Stale holds cleared (no deletes — resolved with a note, ledger append-only)
hold-20261027-080506-018 (hal-9000 project-iris is down) and hold-20261027-080509-019 (hal-9000 project-iris @LAN is down): allcall.clear_hold(id, reason=<note>)
with the FALSE ALARM note (text in holds-resolution-note.txt). Evidence lines appended to allcall.jsonl by the clear. See restart.txt for the before/after.

## 5. Servers restarted / stopped (exp only)
- exp :8772 restarted once — stopped old pid 5100, holds cleared and store seeded while down, started again with run-exp.sh (same env, log /private/tmp/exp8772.log), new pid 41758. Health 200.
- FOUND AND STOPPED an orphaned exp process: pid 31584, started 08:41:25 today with SELFLIGHT_HOME=iris-creative-exp and port 8772 in env but NOT listening
  (its bind had lost to pid 5100), still running the OLD keeper code every minute. It was the second writer behind the double "still-held" per minute, the
  raise/resolve flap, the shared-store `state.tmp` FileNotFoundError, and it re-raised both holds at 16:59:38Z right after my first clear. Killed; holds cleared
  again with the note; then an 80 s watch (restart.txt) for any re-raise. Live :8765 (pid 815) and staged :8790 (pid 37952) untouched.
- Reported, not touched (not my lane): pid 27957 is a `staged-verify` server with SELFLIGHT_HOME=/tmp/staged-verify-home, port 8790 in env, NOT listening — same orphan shape, Lane D's.

## 6. Packet 2 — Safari rule for lane-A
See SAFARI-RULE_source-and-diff_for-lane-A.md + safari-rule.diff. Short: source of truth = /Applications/Project Iris.app/.../project-iris-launch.sh
sha bdbec02b…; installed Iris Control's copy (57eb0837…) lacks `open -a Safari`; lane-A's candidate copy already equals the source byte-for-byte, so
the remaining step is lane-A's rebuild + the sha of the BUNDLED script in their packet. lane-E wrote nothing in lane-A's tree.

## 7. Known gaps / for the Assayer
- Live Prime's own keeper (release code, frozen) still GETs 100.106.102.44:8765 and will keep saying DOWN in the shared ~/.selflight/link-keeper store
  until staged carries this code. Not touched (Prime frozen). Lane D: this is in exp, ready to merge to staged.
- The double "still-held" / flap in exp's all-call ledger is explained and closed: the orphan pid 31584 (section 5). Rule shape for the Assayer: a launcher that
  loses the port bind must exit, not keep its background loops — run-exp.sh/main.py do not check this today (gap, not fixed here; not my file).
- The @LAN HAL target (172.20.1.130:8765) now also checks via Tailscale SSH + loopback curl (same service, same honest answer); a true LAN-leg check of :8765
  is impossible without a door. If Doc wants the LAN leg watched, a tcp check of 172.20.1.130:22 is the doorless option.
- Tailscale SSH check-mode re-auth (MBP->HAL) expires periodically; when it does the HAL target reads BLIND with Doc's click URL in last_reason — by design, not a fault.

---
# v2 (append-only, 2026-10-27) — BIND-EXIT-001: a server that loses the port bind must exit, not keep background loops
Gopher's follow-up after v1 (accepted pending Assayer). Orphans today: exp pid 31584, staged-verify pid 27957, plus last night's.

## v2.0 Compliance pass
SEALS: none opened; exp tree + /private/tmp/exp8772.log only. PII: none. COST: $0. LIABILITY: one announced cycle of exp :8772 (NOTICE on the floor
first, floor tail read for CLAIMs — lane D's claim is the STAGED tree, not exp); live :8765 and staged :8790 untouched; no doors, no Dock/hotkey.
The integration test and the live proof each start a *second* main.py on a port that is already taken — by design it exits in ~1 s and binds nothing.

## v2.1 What changed (exp tree only; main.py imports unchanged, `python main.py` path only)
- NEW app/server/bind_guard.py — two guards:
  1. `preflight(host, port)`: one bind attempt on the exact address, run in main.py right after BIND_HOST/PORT are read (line ~574) and BEFORE link_keeper /
     allcall / warm_keeper / garden / iris_peers are registered. Taken -> one log line `[selflight] BIND-EXIT-001: REFUSING TO START — host:port already has a
     listener (errno …) … exiting 3 now.` then os._exit(3). Nothing has started, so nothing can outlive the process.
  2. `serve_then_exit(uvicorn, app, …)`: replaces the bare `uvicorn.run` at the bottom. If uvicorn never reached `started` (lost the race, any startup error):
     log line + os._exit(3). After a normal stop (SIGTERM / Stop all): 5 s grace for non-daemon threads, then os._exit(0) naming any stragglers in the log — the
     process ends WITH its socket, never after it (the 27957 shape: socket gone, process alive).
  Why os._exit: SystemExit ends only the main thread; the interpreter then waits on every non-daemon thread — exactly how the orphans stayed alive.
- main.py: +11 lines after `PORT = …` (preflight, inside `if __name__ == "__main__"`, ImportError-tolerant: guard missing -> serve as before, say so) and the
  uvicorn call routed through `serve_then_exit` (fallback to the old `uvicorn.run` if the guard did not import). Diff: main.patch. Exit code 3 is distinct from
  1 (python error) and 2 (SEC-07 refuse-to-serve).
- run-exp.sh: claimed, read, UNCHANGED (the bind lives in main.py; the launcher `exec`s python, so main.py's exit code is the launcher's).

## v2.2 Files
| file | sha256 after | backup |
|---|---|---|
| app/server/main.py | a06fc703000dc8e6e00fde5f4443f8d56181af67030cc6ced4fe1cb8a2170a58 | main.py.pre-laneE-20261027 (sha 0150a7c5a1d2fff2919ad35dc6c60dea9d51c3e714a3e10f8fab82f27f99c0dd) |
| app/server/bind_guard.py (new) | 8734c5100128e9c9cab5e5ba17a303901ad229bfd82e477ea2673ad77ab4b20d | — |
| app/server/test_bind_fail_exits.py (new) | 29bcf2c739289529ed634bd5557af3ca48785c79fde42e8c7d4724c69e9858aa | — |
| run-exp.sh | unchanged | — |

## v2.3 Tests (MBP, release python, exp PYTHONPATH) — tests-v2.txt
`python3 -m unittest test_bind_fail_exits -v` -> Ran 5 tests, OK: taken port -> preflight exits 3 with the line; free port -> returns; fake uvicorn never
started -> exit 3; clean stop with a non-daemon straggler -> exit 0 and the straggler is named; and the real `server/main.py` as a second instance on a port
the test holds -> exit 3 in 0.9 s, refusal line printed, NO link-keeper/ or allcall/ store created under its scratch SELFLIGHT_HOME, no "[link] keeper" /
"all-call:" line (no loop ever reached). N = 45 s budget, measured 0.9 s.

## v2.4 Live proof on exp :8772 (announced; v2-live-proof.txt)
One cycle: old pid (v1 main.py, no guard) stopped; new server started on the guarded main.py — log shows `preflight ok — 127.0.0.1:8772 is free` before
the keeper registers; health 200. Then a deliberate second `bash run-exp.sh` on the taken port: exit 3 in about a second, one refusal line, exactly one
iris-creative-exp process left, still serving. (The guard-2 "stopped … exiting 0" line will appear at the NEXT stop of :8772 — the first server running the
guard; whoever cycles it next, check the log tail for it.)

## v2.5 Known gaps
- Only exp carries this; staged :8790 and live :8765 run the old `__main__` path until Lane D merges (Assayer first). The staged-verify orphan shape (27957) is
  exactly guard 2's case.
- Other launchers (iris-control-staged.sh, Project Iris.app launch script) still background-start without checking the exit code; with this guard a refused start
  is exit 3 in the log, but nothing yet surfaces it in Iris Control's UI — a candidate for lane-A: show "port taken by pid X" instead of a silent non-start.
- Guard 2's 5 s grace is a constant (GRACE_S); if a legitimate shutdown task needs longer, raise it there — the log names the thread that was still running.

---
# v3 (append-only, 2026-10-27) — Assayer SEND-BACK E1 + E2, both accepted and fixed

## v3.0 VISIBLE CORRECTION to v1 (section 0 LIABILITY and section 3)
v1 said: "the user@host shape is regex-validated … anything else is refused as BLIND and never shelled." That was TRUE for `via` and FALSE for
`via_url`: via_url went into the remote ssh command unquoted and unvalidated, so a targets.json row (local-only POST /api/link/v1/targets, but still a file
anyone with the Mac can edit) could have run a command as root on HAL. The claim is struck; v1's test only covered `via`. Fixed in v3.1 with tests.

## v3.1 E1 — LINK-SSH-002: via_url allow-list + shlex.quote (link_keeper.py)
- `VIA_URL_RE = ^http://127\.0\.0\.1:[0-9]{1,5}/[A-Za-z0-9/_.-]*$`; a via_url that does not match is refused BEFORE any subprocess call, as BLIND with
  reason `via_url refused: '…' (want http://127.0.0.1:<port>/<path>, LINK-SSH-002)` — state/fails untouched, no hold.
- Every word of the remote command is `shlex.quote`d (curl, flags, '%{http_code}', url) and user@host too; the remote string is now
  `curl -s -m 3 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/api/health`.
- Empty via_url means "use the default loopback URL from port+path" (not hostile); default is asserted to match the allow-list.
- Tests (test_link_keeper_via_ssh.TestViaUrlAllowList): 11 hostile via_urls (`;`, `$( )`, backticks, space, `&&`, `|`, `>`, `?`, non-loopback host,
  https, file://) each refused with subprocess.run mocked to raise — never reached; hostile via_url inside check_all -> BLIND not DOWN, no hold; good url
  passes and the remote string is exactly the quoted form; default/empty via_url.

## v3.2 E2 — SO_REUSEADDR on the probe socket (bind_guard.port_taken)
- `setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)` before bind, matching uvicorn/asyncio's listener. Without it a port whose last connection sat in TIME_WAIT
  after a graceful stop read "taken" and Stop all -> Start all would have exited 3 falsely.
- Tests (test_bind_fail_exits.TestTimeWaitAndReuse): make a real TIME_WAIT (server closes first) -> port_taken is None; the control (a plain socket)
  is refused with errno 48 on the MBP, proving the window is real; an active listener that itself has SO_REUSEADDR is still reported taken.

## v3.3 Files (exp tree app/server/; backups beside, v2 state)
| file | sha256 after | backup |
|---|---|---|
| link_keeper.py | b2781a82851a6f7a58243801097451abff6ccbc6365bd8e24b2f428dcdb0ebe6 | link_keeper.py.pre-laneE-v3-20261027 (= v2 c50652f2…) |
| bind_guard.py | 122bea9a2b5a3afb674ba0be5e291aac9edd76a8b5e580325431eec10bda0da9 | bind_guard.py.pre-laneE-v3-20261027 (= v2 8734c510…) |
| test_link_keeper_via_ssh.py | e5be84b35f8d60f8e55ebd468b3a217b21697023536af033f6922195913fb095 | test_link_keeper_via_ssh.py.pre-laneE-v3-20261027 |
| test_bind_fail_exits.py | 76591e85ac74c017de1c8e823edf4908ac9f8bd4dea264354afcbba2ee9235b6 | test_bind_fail_exits.py.pre-laneE-v3-20261027 |
Diffs: v3-link_keeper.patch, v3-bind_guard.patch. main.py unchanged from v2.

## v3.4 Tests — tests-v3.txt
`python3 -m unittest test_link_keeper_via_ssh test_bind_fail_exits test_allcall -v` -> Ran 39 tests, OK (16 keeper-via-ssh incl. 4 new, 7 bind-guard incl. 2 new, 16 all-call).

## v3.5 Live proof (E2) on exp :8772 — v3-live-proof.txt (NOTICE first)
Stopped pid 54724 (v2 main.py) with SIGTERM — exited in 1 s; `netstat` showed 1 TIME_WAIT socket on :8772 at that moment; started IMMEDIATELY via
run-exp.sh — log: `BIND-EXIT-001: preflight ok — 127.0.0.1:8772 is free`, Uvicorn running, health 200, new pid 88029. Then a second `bash run-exp.sh` on
the taken port: refusal line, exit 3 in 1 s, exactly one iris-creative-exp process, still serving 200. E2's false-exit shape is gone.

### v3.5a VISIBLE CORRECTION to v2.4 ("the guard-2 'stopped … exiting 0' line will appear at the NEXT stop")
It did not, and it will not on SIGTERM: this release's uvicorn (0.53.0, python-deps/uvicorn/server.py lines 332-352 `capture_signals`) records the signal
during serve() and, once serve() returns, RE-RAISES it (`signal.raise_signal`) with the default handler — the process dies by SIGTERM right there, before
`serve_then_exit` gets control back. Consequences, stated plainly: (a) a signal stop ends the whole process, threads included, so that path cannot
make an orphan with this uvicorn; (b) guard 2's "stopped" branch is reached only when uvicorn returns WITHOUT a captured signal (startup/lifespan failure,
Ctrl-C handled inside, programmatic should_exit) — the never-started branch is the one the tests and the live proof exercise. The 27957 orphan was
therefore not a "survived SIGTERM" shape; its socket was taken while it was alive — which is guard 1's territory on the NEXT start, and why guard 1 is the
load-bearing half. v2's sentence is struck, not rewritten.

## v3.6 Compliance
SEALS none; PII none; COST $0; LIABILITY: one announced cycle of exp :8772; :8765/:8790 untouched; HAL port still closed. E1 reduces liability (no
root-on-HAL command path from a targets row).
