# lane-A-iris-control — DONE packet (2026-10-27)
Seat: lane-A-iris-control (cloud Devin, session https://app.devin.ai/sessions/4601af8e6d1b43358b7c5b7a508b5d3a). Plan: MEGAPLAN-FINISH-IRIS-001 lane A. Reply-to: COUNCIL-FLOOR.
Tree claimed (seatguard): candidates/iris-control-1/ and garden/bridge/inbound/lane-A-iris-control-DONE/. Nothing else was written.

## Grade
- CERTIFIED: candidate builds (arm64, ad-hoc signed); Stop all / Start all / Restart proven both ways on the real :8790 with port listings before/after; :8765 (pid 815) and :8772 (pid 5100) untouched across all three cycles; bundled project-iris-launch.sh is byte-identical to /Applications/Project Iris.app's (Safari rule in); Dock pin prepared and dry-run only.
- PROPOSED: the staged-scoped design below (Iris Control's buttons now drive only the staged engine :8790, never the live family). Gopher/Assayer rule on it.
- NOT DONE (by rule, waits for Gopher's clearance): install into /Applications, Dock change, source copy into tools/iris-control/ + registry line, muster sync (foreign seatguard claim).

## What changed (all inside candidates/iris-control-1/)
1. `main.swift` (from ~/devin-bridge/iris-control/main.swift, unchanged original kept as .pre-): Start all / Stop all / Restart / NEW Status call `iris-control-staged.sh` instead of `project-iris-launch.sh`; service list puts "Staged Prime engine (8790)" as the only core service, "Live Prime (8765) — frozen, status only" + exp + Rooms as non-core; subtitle "staged build · :8790"; Stop-all alert text says exactly what is and is not stopped; 4-button rows re-laid (old Console button overflowed the 400-pt window at x 370–470); probe timeout 2→5 s (:8765 answers slowly and showed red while up); `--snapshot <png>` renders the app's own window (used for the screenshot below, no screen-recording permission needed).
2. `build.sh`: builds from this folder, bundles BOTH scripts from this folder (no longer reads /Applications), version 1.1 (2), does NOT install.
3. `iris-control-staged.sh` (NEW): verbs status | start-all | kill-all | restart | open | console, scoped to :8790 + the Iris Prime (Staged) window. Refuses to stop a :8790 holder that is not server/main.py from the staged engine tree; refuses to start over a foreign instance; starts the engine with the verify server's own recipe (SELFLIGHT_INSTANCE=staged-verify, SELFLIGHT_HOME=/tmp/staged-verify-home, SELFLIGHT_SHARED_HOME=~/.selflight, SELFLIGHT_PORT=8790, SELFLIGHT_HOST=127.0.0.1, release python, PYTHONPATH engine vendor:server:release python-deps); opens pages with `open -a Safari` (SAFARI-KEYCHAIN-001); IRIS_STAGED_DRY=1 = rehearsal. Logs: ~/Library/Logs/HIFIDecant/iris-control-staged.log and iris-staged-8790.log.
4. `project-iris-launch.sh`: copied from /Applications/Project Iris.app (the newer truth per Gopher's REVIEW), sha bdbec02b… — the Safari drift (old 57eb0837… in the installed Iris Control.app) is gone in this candidate. Still bundled for the `open`/`console` verbs it may be asked for.
5. `dock-pin-PREPARED.sh` (NEW, NOT APPLIED): default dry run; `--apply` only. Dry run output: Dock before [Claude, Perplexity, Project Iris, Apps, System Settings, Calendar, Notes, DaVinci Resolve, Google Chrome] → after [… Project Iris, Iris Control, Apps …]. Backup it relies on: candidates/_freezes/dock-pre-iriscontrol-20261027.plist (cc9be793…).
6. `stage/Iris Control.app`: the built candidate (bundle id com.hifidecant.iriscontrol, arm64, adhoc). Launch it from here to try it; it is not in /Applications.

## Files + sha256 (computed at packet time)
    7cf6aae9d3e729ad90f5b1aa8b24aa623090ffe74fa210b657f1b9f6d4161103  main.swift
    8eba9892c09d9e882caf883144b10504dc181e3b2687556a0095e84ce7af9a7d  build.sh
    88df0ca412c67e7d77d32855f2d7e1e825dca24a7ce604dc45f10e184c770b4c  iris-control-staged.sh
    bdbec02bd5c29d22966ca18b2bee1f5dbe8286116b55ee6acafc089932c8b324  project-iris-launch.sh
    44d8ac4f854021f1d5528616fb9d850cb70b64e9d23004da5607b00106249224  dock-pin-PREPARED.sh
    a919c292793530903b95c71d844d74d0b8a8f88c3393319af404a9f828a3d535  main.swift.pre-lane-A-iris-control-20261027
    878811e596eee6fac952c742687172bf2066bce7cb188d3cc64e8ebe28d43d99  build.sh.pre-lane-A-iris-control-20261027
    ac096dfc1eef2b3a0ecd80278e96d3cb63ed3ac662e67e3fd99ef39f11a03435  stage/Iris Control.app/Contents/MacOS/IrisControl
    88df0ca412c67e7d77d32855f2d7e1e825dca24a7ce604dc45f10e184c770b4c  stage/Iris Control.app/Contents/Resources/iris-control-staged.sh
    bdbec02bd5c29d22966ca18b2bee1f5dbe8286116b55ee6acafc089932c8b324  stage/Iris Control.app/Contents/Resources/project-iris-launch.sh
    5c19433768c4e226b7e66445ce42c3fc68bcfd9e93cc90bd6f66e5203214fce6  tests/stop-start-proof_20261027.log
    9e30c9b09e489c7521bfc52e166b1910dab8b216d41e04767970db3c9425debd  tests/iris-control-1_window_20261027.png
    32324f26bff02273b55d586b61af2923b9044468d2df948759db7eec7c3a973c  tests/iris-control-1_icon_512.png
Backups: main.swift.pre-lane-A-iris-control-20261027 (= devin-bridge original a919c292…), build.sh.pre-lane-A-iris-control-20261027 (= 878811e5…). Nothing outside this tree was edited, so no other .pre- files exist. /Applications/Iris Control.app untouched (its script still 57eb0837…).

## Tests run (full log: tests/stop-start-proof_20261027.log)
Run on the MBP over ssh, calling the same script file the GUI buttons call (GUI buttons were not pressed: Stop all needs a mouse on the confirm dialog).
- LISTEN before: 8768(805) 8765(815) 8767(818) 8766(819) 11434 52415 8772(5100) 8790(32139)
- kill-all → :8790 closed (pid 32139 gone after SIGTERM); health GET /api/health = 000; LISTEN after: identical minus 8790. :8765 health "up", :8772 health "up".
- start-all → spawned, healthy as staged-verify in 3 s (pid 22762); LISTEN after = before-list with 8790 back; 8765 pid 815 and 8772 pid 5100 unchanged before/after; Safari opened http://localhost:8790/.
- restart → 22762 down, 23123 up in 3 s, healthy as staged-verify.
- Dry runs (IRIS_STAGED_DRY=1) of kill-all and start-all printed intended actions and changed nothing.
- status verb: one line per port with pid, command and instance_id (see log).
- Frozen app check: /Applications/Iris Prime.app mtime Oct 25 20:00:16 before and after — unchanged. Staged tile (NSWorkspace open with --user-data-dir=candidates/_staged-home/prime-staged-userdata) NOT exercised this pass — it needs a GUI session click; code unchanged from Gopher's STAGED-PRIME-001 version.
- Build: `./build.sh` → stage/Iris Control.app; codesign Identifier=com.hifidecant.iriscontrol Signature=adhoc; Mach-O arm64.

## Screenshots (rendered)
- tests/iris-control-1_window_20261027.png — the candidate's own window, rendered by `IrisControl --snapshot` on the MBP: title, subtitle, six service dots, Products, two rows of four buttons (Start all / Stop all / Restart / Status; Rooms / Prime / Staged / Console). First render showed "Staged Prime" clipped to "Staged Pri…" and :8765 red while up → fixed (label "Staged", probe timeout 5 s) and re-rendered.
- tests/iris-control-1_icon_512.png — Dock icon.
- Known limit: `screencapture` over ssh fails ("could not create image from display") — sshd has no Screen Recording permission, which only Doc can grant; the self-render is the honest substitute.

## Servers restarted (tell Doc)
- :8790 staged engine cycled THREE times by this lane at 11:38:50–11:39:01 local (stop, start, restart), restored with the same recipe each time.
- COLLISION (visible, not rewritten): lane-D-staged-merge was mid-merge in the staged engine tree at that moment; my restart (pid 23123) loaded PRE-merge main.py. Lane D killed it and restarted :8790 on the merged tree (now pid 27957, started 11:43:15, instance staged-verify). Current state: :8790 up on Lane D's process; :8765 pid 815 and :8772 pid 5100 never changed.
- My mistake and the rule for its shape (Doc's mistake principle): I posted a NOTICE and cycled at once; I did not read the floor for a live CLAIM on the tree whose server I was about to cycle (Lane D's CLAIM was four lines up). RULE CYCLE-ASK-FLOOR-001: before stopping/starting a shared server, (1) read the floor tail for a CLAIM on that server's tree; (2) if another seat holds it, post NOTICE and WAIT for their ack or their DONE — never cycle under a working seat; (3) cycle the minimum number of times the proof needs (one stop, one start). Also appended to COUNCIL-FLOOR so all seats read it.

## Corrections to the brief (append-only)
- Brief said "Stop all must not kill live Prime :8765" and "note that it also stops exp :8772". With the staged-scoped script neither happens: kill-all stops only :8790 (+ the Staged window). The OLD project-iris-launch.sh kill-all would have stopped the whole launchd family including :8765 — that is why Iris Control no longer calls it for Stop all.
- Earlier survey note "the :8790 process has PYTHONPATH=/Applications/Iris (truncated)" was my display artifact (splitting `ps eww` on spaces inside "Iris Prime (Staged).app"); the real PYTHONPATH is intact.

## Known gaps / open rulings
- Install to /Applications, Dock pin, tools/iris-control/ copy + garden/catalog/tools-registry.jsonl line: prepared, awaiting Gopher. Install recipe: retire /Applications/Iris Control.app to candidates/_to_delete/ with a note, `ditto stage/Iris Control.app /Applications/Iris Control.app`, then `./dock-pin-PREPARED.sh --apply`.
- garden/ola/muster/project-iris-launch.sh still lacks the Safari line and is seatguard-claimed by mdns-keeper (stale) — not touched; the candidate no longer depends on it.
- Staged recipe keeps SELFLIGHT_HOME=/tmp/staged-verify-home (as the verify server was running); /tmp is wiped on reboot. Lane D / Gopher to rule on a persistent home (override: IRIS_STAGED_HOME). candidate-ops' Ollama env pair (SELFLIGHT_OLLAMA_URL/OLLAMA_HOST) is also not set, same reason.
- Status button writes to ~/Library/Logs/iris-control.log and the note line; no in-window table yet. services.json skipped (optional, per REVIEW item 6).
- No launchd plist for :8790: the engine is a nohup child; it does not come back by itself after reboot (Start all brings it back).

## Compliance pass (garden/skills/compliance-pass.md)
- SEALS: none opened. No private, sealed or restricted file read; Prime trees and /Applications/Iris Prime.app read-only (mtime proven unchanged).
- PII: none in this packet. The proof log lists pids, ports and local paths only; `ps eww` output (which contains API keys in env) was filtered to SELFLIGHT_*/PYTHONPATH keys and not stored.
- COST: one cloud Devin session; Doc's hand once (Tailscale SSH check URL). No purchases, no signatures.
- LIABILITY: cycling :8790 interrupted Lane D (see collision above); nothing live was touched; all changes revertible by deleting candidates/iris-control-1/ (nothing installed).

## v2 (append-only, 2026-10-27 — Gopher's ruling after review: "staged home must be persistent, not /tmp")
Ruling: /tmp/staged-verify-home is wiped at reboot and lane B's Touch ID key store lives in SELFLIGHT_HOME, so Doc's enrolment would be lost. Default the home to the existing persistent staged home under candidates/_staged-home/ and set the candidate-ops Ollama pair.
- Path confirmed: `~/HIFIDecant/Selflight/candidates/_staged-home/prime-staged-userdata/selflight-instance` — the directory the Staged app's Electron shell creates inside its user-data dir; it already has the SELFLIGHT_HOME layout (prime-sign/, sessions/, iterations/, logs/, councils/, shared/, weave/ …). Evidence (app.asar grep) in the v2 log below. `prime-staged-userdata/` itself is Chromium user data (Cookies, Cache …), not an engine home.
- `iris-control-staged.sh` v2 defaults: SELFLIGHT_HOME=<path above>; SELFLIGHT_OLLAMA_URL=http://127.0.0.1:8766 and OLLAMA_HOST=http://127.0.0.1:8766 (candidate-ops: mandatory, else the client hits system :11434); SELFLIGHT_WORKSPACE_ROOT=~/HIFIDecant/workspace (matches lane D's running :8790 recipe). Instance id stays staged-verify; SELFLIGHT_SHARED_HOME stays ~/.selflight. Overrides: IRIS_STAGED_HOME, IRIS_STAGED_OLLAMA_URL, IRIS_STAGED_WORKSPACE_ROOT.
- Rebuilt stage/Iris Control.app (main.swift unchanged from v1 final). Re-hashes:
    43949c204fac6ec778e66b8cf961dcbbfafbeca2a108c41f16760907586c86a5  iris-control-staged.sh
    88df0ca412c67e7d77d32855f2d7e1e825dca24a7ce604dc45f10e184c770b4c  iris-control-staged.sh.v1-20261027
    7cf6aae9d3e729ad90f5b1aa8b24aa623090ffe74fa210b657f1b9f6d4161103  main.swift
    8eba9892c09d9e882caf883144b10504dc181e3b2687556a0095e84ce7af9a7d  build.sh
    2c6b7411564aa19ab30c03766187b3325de487570a7404fb3f87330b6527a0ca  stage/Iris Control.app/Contents/MacOS/IrisControl
    43949c204fac6ec778e66b8cf961dcbbfafbeca2a108c41f16760907586c86a5  stage/Iris Control.app/Contents/Resources/iris-control-staged.sh
    bdbec02bd5c29d22966ca18b2bee1f5dbe8286116b55ee6acafc089932c8b324  stage/Iris Control.app/Contents/Resources/project-iris-launch.sh
    9e8becebea444fbe80072a8e8ba412ae551d2273869297b3a383f32857faad2a  tests/v2-dryrun_20261027.log
- Dry run (IRIS_STAGED_DRY=1 start-all) printed the v2 spawn line; nothing was started. :8790 was NOT cycled for v2 — per Gopher, that waits for lane D's DONE on the floor, then NOTICE → one stop → one start; the proof will be appended here as v2-proof.
- Floor line posted naming the path so lanes B and D use the same home.
- v1 text above is kept as written; where it says SELFLIGHT_HOME=/tmp/staged-verify-home, read v2.
- v2 CORRECTION (append-only): the first dry run against :8790 did not print the spawn line — :8790 was already up as staged-verify, so the script correctly said "already up" and did nothing (tests/v2-dryrun_20261027.log). The spawn line was then shown with a dry run on an unused port (IRIS_STAGED_PORT=8799, tests/v2-dryrun-spawnline_20261027.log): SELFLIGHT_HOME=…/_staged-home/prime-staged-userdata/selflight-instance, SELFLIGHT_OLLAMA_URL=OLLAMA_HOST=http://127.0.0.1:8766, SELFLIGHT_WORKSPACE_ROOT=~/HIFIDecant/workspace.
- v2 path evidence: `grep -a selflight-instance app.asar` → `const selflightHome = () => path.join(userData(), 'selflight-instance')` — the Staged app's shell puts the engine home at userData/selflight-instance, i.e. exactly the path above.
- v2 open ruling: candidate-ops' full recipe also lists SELFLIGHT_PLAUD_INTAKE=1 and SELFLIGHT_CEILING_MAY_OPS=1; lane D's running :8790 does not set them and v2 mirrors lane D. Not added silently — Gopher/lane D to rule; overrideable by env if wanted.

## v2-proof (append-only, 2026-10-27, after lane-D DONE)
One stop + one start of :8790 on the v2 recipe, NOTICE posted first, no newer CLAIM on the staged tree (CYCLE-ASK-FLOOR-001). Full log: tests/v2-stop-start-proof_20261027.log (also in this packet).
- Before: :8790 pid 27957 (lane D's), home=/private/tmp/staged-verify-home. kill-all → closed after SIGTERM, health 000; :8765 still up.
- start-all → pid 37952 healthy as staged-verify in 2 s; /api/health home = ~/HIFIDecant/Selflight/candidates/_staged-home/prime-staged-userdata/selflight-instance; env shows SELFLIGHT_OLLAMA_URL=OLLAMA_HOST=http://127.0.0.1:8766, SELFLIGHT_WORKSPACE_ROOT=~/HIFIDecant/workspace; lane D's merged tree still served (/library 200, /api/allcall/v1 200); iris-ola:latest present in the model list.
- LISTEN lists before/after identical except the :8790 pid; :8765 pid 815 and :8772 pid 5100 unchanged. Server relaunched: :8790 once (tell Doc).
