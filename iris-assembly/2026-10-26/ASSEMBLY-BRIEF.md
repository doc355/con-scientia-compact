# IRIS ASSEMBLY BRIEF — one great big machine
2026-10-26 · written by the Rooms integrator seat (Devin, cloud) · append-only: add, never erase.
Read this whole page before touching anything. Doc's word outranks this page.

## The law (Doc, standing)
1. **Prime Build Directive.** Any change to Iris Prime: freeze a copy of Prime as it is → build in an EXPERIMENTAL copy → when the feature works, add it to a STAGED copy of Prime → test there until adopted → **Doc's fingerprint** → the frozen Prime becomes the new Prime. Nothing reaches Prime without his fingerprint.
2. **Never patch the installed, signed macOS app bundle in place. Never publish live without Doc's yes.**
3. **No deletes — retire to `_to_delete/`.** Notes are append-only; corrections stay visible (Wrong Ideas Ledger spirit). Grade claims CERTIFIED / PROPOSED / UNVERIFIED and state kill conditions.
4. **The Style Guide (24 Oct PDF) is the Law of the build.** Style catalog = "inspired by" palettes/linework/materials only — no copied characters or logos.
5. **Only Research (the Forge) has non-armoured beings.** The armour is worn by the room. The assistant is always armoured.
6. **HiFi is per unit and belongs to the person holding it.** HiFi off = never joins, never reachable.
7. No copying Doc's beings/history into a packaged app without his explicit A/B choice.
8. Transparency: announce before opening anything private; no output-hiding flags without saying why.

## Where things are (MBP)
- Experimental copy: `~/HIFIDecant/Selflight/candidates/iris-rooms-exp-1/` → serves **8773** (`/rooms`). Instance home `~/.selflight/instances/iris-rooms-exp/`.
- Exp Prime: 8772 · Live Prime app: the packaged Iris Prime (untouched tonight).
- Integrator sources + tests: `~/devin-bridge/rooms-ship/` (copies) · ledger: `WORKNOTES.md` (joint/reskin).
- Release gate: `app/server/release_gate.py` (promote is wrapped by the fingerprint lock).

## What is in the machine (8773), with proof
| Piece | File(s) | Proof | Grade |
|---|---|---|---|
| Iris Connect API (`/connect/v1` public, `/ascended/v1` household), grants, receipts, never-exposed list | `connect_gateway.py` | 15/15 live HTTP checks | CERTIFIED on one Mac |
| Household garden: HMAC beacon 239.255.73.77:47377, auto-pair, HiFi on/off, leave/retire | `garden.py` | two live instances (8773+8774) | CERTIFIED on one Mac; cross-machine PENDING (garden door) |
| Councils across the garden (`garden:<unit>/<model>` seats; away = recorded no-answer; no paid models on others' units) | `garden.py` | live 3-seat council | CERTIFIED on one Mac |
| Prime fingerprint lock (PRIME-SIGN-001): sign manifest with Touch ID; promote refuses unsigned/changed | `prime_sign.py` | 23 math checks, real-Chrome virtual authenticator, real promote path 5 cases | CERTIFIED w/ stand-in; Doc's real finger UNVERIFIED |
| Second key (PRIME-SIGN-002): new key needs a touch from an existing key; hand-written keys don't count | `prime_sign.py` | 10 checks | CERTIFIED w/ stand-in |
| Budget keeper (BUDGET-KEEPER-001), WATCH until first signed budget; per-wallet caps from one spend ledger; chat/council/Devin/bridge hooked | `budget_keeper.py` | 22 checks + live route checks | CERTIFIED w/ stand-in; WATCH live |
| Rooms UI: writing desk, floating writing pad, curio cabinet, quill/ink pot, owl, 428 styles, room AI tools (undoable), room-worn armour, always-armoured assistant, being per head | Rooms front end | live page loads, no script errors | CERTIFIED on 8773 |

## Lanes (wake order)
- **Council of Builders — RED TEAM.** Try to break `budget_keeper.py` and `prime_sign.py` (both lock money/Prime). Goal: a paid call that slips past ENFORCE, a way back to WATCH without a signature, a key that counts without vouching, a promote without a fingerprint. Write findings to `~/devin-bridge/council/redteam-<seat>.md`; do NOT patch, the integrator fixes. Known/declared gaps (don't re-report, try to go further): deleting `prime-sign/signatures.jsonl` returns the keeper to WATCH (same trust boundary as the lock; closed by task 132 launch check); `cleared_by` is self-reported.
- **Shard Builder** — Phone (calls+texts in one) + iPhone Mirroring curio, in the exp copy only. Later: Vision Pro shard (own unit, Optic ID as its own root key).
- **Gopher + Shardwright** — audit 8773 against the Style Guide and IRIS-API-001; list deviations, don't fix Prime.
- **Integrator (me)** — after red-team fixes: freeze current Prime → staged copy of Prime carrying the 8773 work → test → hand Doc the fingerprint step.

## Waiting on Doc only
1. Enrol Touch ID at `http://localhost:8773/prime-sign` (localhost, not 127.0.0.1) — a 30-second test; locks nothing yet.
2. Free Option-Space in Gemini's settings (Iris hotkey patch staged).
3. Family photos source (Apple Photos album or folder).
4. Yes/no: open the narrow "garden door" (`/garden/v1/pair` + `/ascended/v1` on LAN/tailnet only).
5. Lost-only-key policy: spare security key in a safe / paper code / re-install from frozen copy.
6. Go for council red team.

## Next builds (not started)
Prime launch check (132) · treasury rules for trades (107) · Iris runner on MLX (135) · EXO-style shared models with per-unit "lend" switches, Thunderbolt preferred (136) · photo frame (123).

## ADDENDUM 2026-10-26 (append-only) — products and the launcher cleanup
- PRODUCTS ARE NEVER RETIRED. Iris Dental, Iris Vet, Iris Teacher, Iris GBM, Paradox, and every expert-head unit are products Doc will show and sell. Doc: "All of the individual expert heads, I'm going to sell as individual units. So we need to have one of each of those." -> SHARD BUILDER's lane: one installable product app per expert head. Integrator does not touch them.
- Launcher cleanup (Doc's yes): the seven Iris launchers (Project Iris, Start All, Kill All, Restart, Console, Selflight Local, Selflight MASTER, + Chrome "IRIS" web app on dead :8765) are being replaced by ONE app, Iris Control (moving-eye Dock icon), and retired to /Applications/_to_delete/ only AFTER Iris Control's start/stop are proven. Iris Prime and all non-Iris apps untouched.
- "Selflight" = old internal name of the engine (folders, ~/.selflight, launchd label). Not renamed now; on-screen name is Iris.
- CORRECTION 2026-10-26 (append-only): "Paradox" in the PRODUCTS line above is a dictation error for "products" — Doc said "Products as well." There is no Paradox head or app. The product rule stands: every expert head becomes its own sellable product unit (Shard Builder). Products on the MBP today: Iris Dental, Iris Vet, Iris Teacher, Iris GBM.
