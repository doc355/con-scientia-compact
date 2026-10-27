# lane-B-prime-launch-check — DONE packet (2026-10-27)
Builder: lane-B-prime-launch-check (cloud Devin, session ec281a58). Plan: MEGAPLAN-FINISH-IRIS-001, seat B.
Tree: `~/HIFIDecant/Selflight/candidates/prime-launch-check-1/` (claimed via seatguard; every file listed in `.seatguard/claims.jsonl`).

## What changed (one paragraph)
LAUNCH-CHECK-001: the packaged staged Iris Prime shell verifies Doc's Touch ID signature (PRIME-SIGN-001 format,
`server/prime_sign.py`, reused byte-for-byte) over `engine/app` before spawning the engine. Intact signed tree →
starts. Tampered (changed/added/removed file) → engine never spawned, recovery screen names the files. Unsigned /
no key / signature that does not re-verify → refuse. Delivered as a candidate: patched `main.js` + `recovery.html`,
stdlib verifier `launch_check.py`, node glue `launch_check.js`, Doc's enrol+sign page `prime_launch_sign.py`,
stdlib asar packer, lane-D install script, 18 python + 10 node tests, rendered screens. Full design, behaviour
table, signing steps, compliance pass and known gaps: `CANDIDATE-README.md` (copy of the candidate's README).

## NOT done, on purpose
- Nothing installed into `/Applications/Iris Prime (Staged).app` (lane D, LAST — `tools/install-into-staged.sh`).
- Nothing signed. Doc enrols and signs by his own hand (`tools/prime_launch_sign.py`, steps in CANDIDATE-README).
- Prime (:8765, `/Applications/Iris Prime.app`, releases/20260922-01): not touched, not restarted.

## Files + sha256 (computed on the MBP at packet time — see SHA256SUMS beside this file)
See `SHA256SUMS` (every file in `candidates/prime-launch-check-1/`, generated with `shasum -a 256`).

## Backups
No existing file was edited, so no `.pre-` backups were needed. Pristine copies of what the patches apply to are
kept in `candidates/prime-launch-check-1/ref/`:
- `ref/main.js.asar-20261027`      sha256 da3d56d4999879f15a554cde0ccf36ee79d195175b7e88426d9b643dbfd6681e (staged app.asar main.js)
- `ref/recovery.html.asar-20261027` sha256 6e29a8dfa4d2961606d62774da5c07f05579d3805d3862bed294ffa9e96158df
- `ref/preload.js.asar-20261027`   sha256 232e43bd46c3879f14286f98bceee6249e351b90971b1d5cc88fc65fa2bf0b51
- `ref/prime_sign.py.staged-20261027` sha256 5569a9b1c7bc86ec4b8036dbf176cd9a01386b6a41efaa8e9dbfcb536d18ca37 (identical to rooms candidate's)
- staged `app.asar` as read: sha256 f53d014ab8f91c113bbde12b89a591a42678e4fdfcb85db68af75fca44892e39, header sha256 9ba6a850…9198 (= Info.plist ElectronAsarIntegrity).
Lane D's install script makes `app.asar.pre-laneB-20261027` and `Info.plist.pre-laneB-20261027` beside the originals.

## Tests run (outputs attached verbatim)
- `tests/run.sh` on the MBP with the bundled python 3.12.13 and node v26.10.0: 18/18 python, 10/10 node, asar roundtrip → ALL PASS (`tests-output_run-sh_20261027.txt`).
- Real staged tree dry run (read-only, `--no-ledger`): 416 files, digest fe47c513eb7c758345720681b45ed711ce4a22767e78c05cd8b1857d7117799a, 0.41 s, verdict 12 "no Touch ID key enrolled" (expected: nobody has enrolled on that home) (`tests-output_real-tree-dryrun_and_sign-server-smoke_20261027.txt`).
- Sign-server smoke test: loopback 127.0.0.1:8796 for ~8 s against a TEMP home, GET `/` 200, `/api/launch-sign/v1/state` and `/api/prime-sign/v1/status` answered, stopped, port closed. No real home written.
- Asar packer round-trip on the VM: repacked staged app.asar is byte-identical to the original.

## Screenshots (rendered, headless Chrome 860×620)
`recovery-tampered.png`, `recovery-unsigned.png`, `recovery-plain-engine-failure.png` (the existing path, unchanged look).

## Servers
- Restarted: none. Started: `prime_launch_sign.py` on 127.0.0.1:8796 for ~8 s (smoke test), stopped.
- Observed, not mine: staged :8790 changed PID 32139 → 27957 between 16:33Z and 16:43Z (someone else restarted it). :8765 untouched.

## Reads outside my tree (transparency)
Read-only: staged bundle (`Info.plist`, `app.asar`, `engine/app/server/{prime_sign,main,release_gate,budget_keeper}.py`, `run_selflight.sh`, checksums), rooms candidate `app/server/prime_sign.py`, `candidates/_staged-home/…/selflight-instance` listing + `logs/engine.log` tail, `~/.selflight` top-level listing only, GET `/api/prime-sign/v1/status` + `/api/health` on :8790 and :8772, garden skills/rules/megaplan. No private being records opened.

## Compliance pass
SEALS none touched · PII none moves (public keys + assertions stay on the Mac) · COST one cloud session, +0.4 s per launch, no purchases · LIABILITY the signature is Doc's hand alone; the gate refuses rather than guesses; dev bypass only when not packaged and logged. Detail in CANDIDATE-README.

## Known gaps
Scope is `engine/app` only (python/ and python-deps/ ride on Apple's code signature); trust root (`keys.json`) lives in the app's home, so a root-level actor who rewrites the tree could rewrite it too (pin the root fingerprint into the asar — proposed); real-Electron end-to-end run awaits lane D's install; a release candidate literally named `iris-prime-staged` would shadow the bundle path in `prime_sign.register`.

## Correction (kept visible)
My first HAL master SSH connection died when its shell closed (started without setsid), so its Tailscale check URL went dead and a second URL had to be minted. Rule I'm taking: long-lived connections start under `setsid nohup … & disown` the first time.

## v2 (2026-10-27, Gopher send-back; append-only — v1 above stands as written)
Asked: (1) verifier + sign page resolve keys.json from the same persistent staged home; refuse, don't crash, if the home is missing. (2) Root-fingerprint pin written into the asar at install time; refuse on mismatch; absent pin = unchanged.
Done, in my own tree (`candidates/prime-launch-check-1/`), nothing installed, nothing signed:
- **Missing home → refuse code 15**, nothing created (verified on the real staged tree against `/tmp/no-such-home-laneB`: code 15, directory still absent). Home that is a file → 15. `Store()` is no longer reached for a missing home.
- **Pin.** `tools/install-into-staged.sh [APP] [HOME]` writes `launch_check_pin.json` `{home, root_fingerprint?, pinned_utc}` into the asar; `main.js selflightHome()` honours the pinned `home` so engine, verifier and Doc's sign page (`--home`) read ONE `prime-sign/` store; `launch_check.js` passes `--pin`; `launch_check.py` **code 14** if keys.json's root fingerprint ≠ pin, even when a signature re-verifies. Pin absent → unchanged; pin present but no key → 12 (verified on the real tree with a temp home: code 12). Install twice: once unpinned, once after Doc enrols (second backup stamped `-pin-<time>`, first never overwritten).
- **Tests:** 25 python (was 18) + 15 node (was 10) — ALL PASS on the MBP with bundled python 3.12.13 + node 26 (`tests-output_run-sh_v2_20261027.txt`). New: pin match / mismatch / mismatch-after-keys.json-swap (proves the gap without the pin, the refusal with it) / absent / present-without-key; missing home; home-is-file; node pin-file passthrough, unreadable pin file, selflightHome wiring.
- **Screens:** `recovery-pin-mismatch.png`, `recovery-home-missing.png` (rendered).
- **Staged home path:** Lane A has not posted it yet (floor read at 16:50Z: :8790 still `/tmp/staged-verify-home`; Lane A's packet names an `IRIS_STAGED_HOME` override and asks lane D / Gopher to rule). The packaged app's own home is `candidates/_staged-home/prime-staged-userdata/selflight-instance` — the install script's default. When the path is ruled, lane D passes it as HOME; no code changes.
- **Changed files** (each backed up beside it as `*.pre-laneB-v2-20261027`): shell/launch_check.py, shell/launch_check.js, shell/main.js, patch/main.js.patch, tests/test_launch_check.py, tests/test_shell.js, tools/install-into-staged.sh, README.md; tools/pack_asar.py (skips `.pre-` backups when packing — a v2 repack had swept them in; caught and repacked). SHA256SUMS regenerated for the whole tree.
- Servers: none started or restarted in v2.
