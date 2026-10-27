# prime-launch-check-1 — LAUNCH-CHECK-001 (lane-B-prime-launch-check, 2026-10-27)

**What it is.** The packaged Iris Prime shell (Electron `main.js`) now asks one question before it
spawns the engine: *does a stored, re-verifiable Touch ID signature cover the engine tree exactly as
it sits on disk right now?* If yes, the engine starts as before. If no, the engine is **never spawned**
and the recovery window says why — and, when it can, names the changed / added / removed files.

**Status: CANDIDATE — not installed anywhere.** Nothing in `/Applications` was written. Lane D installs
this LAST (it signs the final staged tree); Doc enrols and signs by his own hand. Prime (:8765,
`/Applications/Iris Prime.app`, releases/20260922-01) was not read for writing, not touched.

## Reuse, not reinvention (PRIME-SIGN-001)
The signing format and verifier are `server/prime_sign.py` (identical in `candidates/iris-rooms-exp-1/app`
and the staged app — `diff` says IDENTICAL):
- manifest = sorted `sha256  relpath` lines over the app tree (skips `__pycache__`, `_to_delete`, `.git`,
  `node_modules`, `.DS_Store`, `*.pyc`, anything with `.pre-`); **digest = sha256(manifest text)**.
- challenge = sha256(`IRIS-PRIME-SIGN-v1|<purpose>|<name>|<digest>|<nonce>`), signed by Doc's platform
  passkey (WebAuthn, rpId `localhost`, user-verification required), full assertion kept in
  `<SELFLIGHT_HOME>/prime-sign/signatures.jsonl`; keys in `prime-sign/keys.json` (first key = root; others
  only count when vouched for by an `add-key` signature).
- `shell/launch_check.py` carries prime_sign.py's P-256 / CBOR / manifest / assertion code **byte-for-byte**
  (`tests/test_launch_check.py::TestReuse` fails if the two drift) and ports `Signer.trusted` + `Signer.check`
  as read-only functions. Stdlib only; the shell pipes it to the bundled `python3 -I -` so nothing from the
  not-yet-verified tree is imported while that tree is judged.

Signature subject: purpose `promote`, name **`iris-prime-staged`**, app_dir = `…/Contents/Resources/engine/app`,
store = the app's own `SELFLIGHT_HOME` (`candidates/_staged-home/prime-staged-userdata/selflight-instance`).

## Files
| path | role |
|---|---|
| `shell/launch_check.py` | the verifier (exit 0 intact · 10 unsigned · 11 tampered · 12 no key · 13 bad signature · 2 could-not-run). JSON verdict on stdout; one append-only `launch_check` line in `prime-sign/ledger.jsonl`; writes nothing else. |
| `shell/launch_check.js` | node side: spawns the verifier, exit code and JSON must agree, any failure to run = refuse (never pass); plain-words `recoveryWords()`. |
| `shell/main.js` | the staged `app.asar` main.js + the gate (`launchCheckGate()` runs in `boot()` before `startEngine()`); verdict in the log, the tray, IPC `engine-state.launchCheck`, and the Help menu says the truth. `patch/main.js.patch` is the diff against `ref/main.js.asar-20261027`. |
| `shell/recovery.html` | existing recovery screen + a "Signature check" pane (verdict, tree, file count, digest now / signed, when, changed/added/removed lists, Copy details). `patch/recovery.html.patch`. |
| `shell/preload.js`, `shell/package.json` | unchanged copies, so `build/app.asar` is complete. |
| `build/app.asar` | the six files packed (header sha256 printed by `tools/pack_asar.py header-sha256`). |
| `tools/prime_launch_sign.py` | **Doc's enrol + sign page** (loopback only): `prime_sign.register()` on a tiny FastAPI app with name `iris-prime-staged` → the bundle's engine tree, SELFLIGHT_HOME = the app's home. Saves the manifest text at `prime-sign/manifests/<digest>.txt` after a sign so refusals can name files. `/` shows what he is about to sign and whether the launch check would pass right now. |
| `tools/pack_asar.py` | stdlib asar list/extract/pack/header-sha256 (round-trips the staged `app.asar` byte-identically; the header sha256 is exactly the `ElectronAsarIntegrity` value in Info.plist). |
| `tools/install-into-staged.sh` | **lane D's** install step: backs up `app.asar` + `Info.plist` as `*.pre-laneB-20261027`, packs, updates the integrity hash, ad-hoc re-signs; refuses any path that is not `… (Staged).app`. Not run by lane B. |
| `tests/test_launch_check.py` | 18 tests, stdlib unittest. A fake Touch ID (P-256 signing written in the test) signs temp trees. |
| `tests/test_shell.js` | 10 node checks of `launch_check.js` + `main.js` wiring. |
| `tests/run.sh` | runs everything with the bundled python 3.12 and `/opt/homebrew/bin/node`. |
| `ref/` | pristine copies (with sha256 in the DONE packet) of what was patched. |
| `screenshots/` | rendered recovery screens: tampered, unsigned, plain engine failure. |

## Behaviour (tested)
| tree | signature | result |
|---|---|---|
| intact, signed | re-verifies | **starts** (exit 0) |
| one byte changed / file added / file removed | digest ≠ signed | **refuse** + recovery screen naming `changed` / `added` / `removed` (exit 11) |
| never signed (or signed under another name) | none | **refuse** (exit 10) |
| no key enrolled | — | **refuse** (exit 12) |
| signed by a key not enrolled / hand-added to keys.json / record edited / UV flag missing | does not re-verify | **refuse** (exit 13) |
| verifier missing, interpreter missing, timeout, JSON says ok but exit ≠ 0 | — | **refuse** (code 2 / exit) — a missing error is not a pass |
| engine re-signed after a change | latest good record | **starts** |

Real staged tree (read-only dry run, 2026-10-27): 416 files hashed, digest `fe47c513…799a`, 0.41 s wall,
verdict 12 (no key enrolled) — as expected, nobody has enrolled on that home yet.

## How Doc signs (his hand; prepared, never done for him)
1. Lane D installs (`tools/install-into-staged.sh`) after every other merge.
2. Someone with the floor runs, on the MBP:
   `"/Applications/Iris Prime (Staged).app/Contents/Resources/engine/python/bin/python3" tools/prime_launch_sign.py --app-dir "/Applications/Iris Prime (Staged).app/Contents/Resources/engine/app" --home "$HOME/HIFIDecant/Selflight/candidates/_staged-home/prime-staged-userdata/selflight-instance" --port 8796`
   then `open http://localhost:8796/` (Safari/Chrome on the MBP; WebAuthn needs the localhost origin).
3. Doc: **Enrol Touch ID** (once per Mac), check the file count + digest, **Sign with Touch ID**. The page then
   shows "Launch check right now: PASS". Stop the sign server (Ctrl-C). Launch the staged app.
4. Any later change to `engine/app` → the app refuses and shows the files; re-sign the same way.

## Compliance pass (step zero)
- **SEALS** — none touched. No sealed/LEGAL/FINANCIAL material read. Prime trees untouched. Staged bundle read only (two files copied out as references).
- **PII** — none moves. Keys are *public* keys + assertions, kept on the Mac in the app's own home; nothing leaves the device; the only new store write is an append-only ledger line per launch.
- **COST** — one cloud Devin session (this one); ~0.4 s added per app launch; no purchases.
- **LIABILITY** — the signature is Doc's hand alone (WebAuthn user-verification required; nothing here can sign). The check refuses rather than guesses. Dev bypass exists only when the app is *not packaged* and `IRIS_SKIP_LAUNCH_CHECK=1` is set, and it writes itself into the log.

## Known gaps (honest)
- **Scope = `engine/app`** (what PRIME-SIGN-001 already signs). `engine/python` (60 MB) and `engine/python-deps` (208 MB) are not in the digest — hashing them each launch is ~seconds; they are covered by Apple's code signature of the bundle instead. Extending `manifest()` to them is a one-line scope change if wanted.
- **Trust root lives beside the data.** `keys.json` sits in the app's SELFLIGHT_HOME; a root-level actor on the Mac who can rewrite the engine tree can also rewrite keys.json. This gate is against accidental / unauthorised tree changes by seats, not against root. Pinning Doc's root-key fingerprint into the asar at install time would close that; proposed, not built.
- `prime_sign.register()` resolves a name through `release_gate` candidates first; a release candidate literally named `iris-prime-staged` would shadow the bundle path. None exists.
- Electron-in-the-loop test (real app showing the recovery window) was not run: that requires installing into the staged bundle, which is lane D's step. The shell logic is covered by `tests/test_shell.js`; the screen is rendered in `screenshots/`.
- The staged bundle is ad-hoc signed today; `install-into-staged.sh` re-signs ad hoc. If Doc later signs with his Developer ID, that step must use his identity.

## v2 (2026-10-27, Gopher send-back — append-only)
1. **Missing home refuses, never crashes, creates nothing.** `launch_check.py` exit **15** when `SELFLIGHT_HOME` is not a directory (it used to let `Store()` mkdir it). Tests: missing dir, home-is-a-file → 15, nothing created. Recovery words: "Iris cannot find its home folder."
2. **Root-fingerprint pin.** `tools/install-into-staged.sh [APP] [HOME]` now writes `launch_check_pin.json` into the asar: `{home}` always (so engine, verifier and Doc's sign page read ONE prime-sign store — `main.js selflightHome()` honours it), plus `{root_fingerprint}` when `HOME/prime-sign/keys.json` already holds Doc's root key. `launch_check.js` passes `--pin`; `launch_check.py` exit **14** if keys.json's root fingerprint differs from the pin — even when a signature re-verifies (a swapped root + re-sign is exactly what the pin catches; test `test_pin_mismatch_after_keys_json_replaced` proves the gap without the pin and the refusal with it). Pin absent → unchanged; pin present but no key → still 12. Install order: install (unpinned) → Doc enrols + signs → run install again → pinned (second backup stamped `.pre-laneB-20261027-pin-<time>`, never overwriting the first).
3. **Staged home.** Lane A has not yet posted the persistent path (the :8790 verify server still runs with `/tmp/staged-verify-home`; the *packaged* app's home is Electron userData → `candidates/_staged-home/prime-staged-userdata/selflight-instance`, which is the install script's default HOME). When Lane A posts the path, lane D passes it as the HOME argument; nothing else changes.
Tests now: 25 python + 15 node. New screens: `screenshots/recovery-pin-mismatch.png`, `recovery-home-missing.png`.

## v3 (2026-10-27, Assayer integration finding via Gopher — append-only; lane B owns the combined main.js)
- `shell/main.js` is now the **combined shell**: lane C's OPTSPACE-001 (`candidates/option-space-1/main.js`, sha f9d8b51e…) 3-way-merged (`git merge-file`, base = staged asar main.js da3d56d4…) onto LAUNCH-CHECK-001. Clean merge, no conflicts. One integration edit, marked in the source: Option+Space's `openMainWindow` only opens the main window when `engineState === 'running'`; while the launch check has refused it focuses the recovery window instead of opening a window onto a dead port.
- Carried from lane C verbatim: `shell/hotkey.js` (55ffbf05…), `shell/preload.js` (7c027dc1…); their tests as `tests/hotkey.test.js` (only change: path roots → `shell/`, `patch/`), their client patch as `patch/iris-assistant.optspace.patch` (bf9261e5…, still lane D's to apply in the staged client). Lane C's `package.json` (82854c9a…, adds electron-builder scripts) is NOT shipped — the bundle's minimal `package.json` stays; kept for reference in `ref/laneC/`.
- `tools/install-into-staged.sh` refuses (exit 3, clear message) to pack a main.js lacking the `LAUNCH-CHECK-001` or `OPTSPACE-001` marker or either `require`; `--check-markers <file>` runs that check alone. `hotkey.js` added to the pack list.
- Patches: `patch/main.js.combined.patch` (= `patch/main.js.patch`, base→combined), `patch/preload.js.patch`.
- **Combined main.js sha256: cab9c429b3c6df9212534f7ea53391ac5402032e903d6a4c8c9d916b102ccb6c** (also in SHA256SUMS).
- Backups of every file changed in v3: `backups/v3-20261027/` (`*.pre-laneB-v3-20261027`).
