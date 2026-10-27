# DONE — lane-D-staged-merge (2026-10-27) — exp → STAGED Prime merge
Seat: lane-D-staged-merge (cloud Devin, session https://app.devin.ai/sessions/5acd0e2916404d62a23352c542309406), under MEGAPLAN-FINISH-IRIS-001 (Gopher, Director).
Target: `/Applications/Iris Prime (Staged).app/Contents/Resources/engine/app` (STAGED, served on :8790). Source (read-only): `candidates/iris-creative-exp-1/app` (:8772).
Live Prime (`/Applications/Iris Prime.app`, releases/20260922-01, :8765) and exp :8772 were NOT touched. Nothing published. HOLD for Gopher / Assayer / peer review, then Doc's fingerprint.

## Step zero — compliance pass
- SEALS: household only. No LEGAL / FINANCIAL / OFF-LIMITS material opened. Prime tree never read for writing, never written. Library reads Apple Books / Audible SQLite read-only (library.py copies the DB to a temp file before reading).
- PII: none leaves the MBP. The Library page lists Doc's own catalogue titles on his own machine; the API reports `hidden: {apple_books_personal_pdfs: 62}` — the 62 personal PDFs in Apple Books are counted, never listed (test_library proves it, 5/5). Test homes used throwaway dirs (/tmp/laneD-test-home, /tmp/staged-verify-home).
- COST: one cloud Devin session (~2.5 h), no purchases, no tokens spent on paid models (no chat turns sent to any head). Doc's attention: one Tailscale SSH check-mode click (HAL).
- LIABILITY: no money, no signatures, no network doors opened (nothing bound beyond 127.0.0.1; headless Chrome CDP on 127.0.0.1:9333 was started and closed within the pass). No Dock/hotkey changes. Adoption stays Doc's hand.

## Method (precedent: devin_20261027_finish-prime-styling-merge-DONE)
1. Freeze first: `candidates/_freezes/iris-prime-STAGED-FREEZE-pre-laneD-20261027-1136.tar.gz`, sha256 `8184ea97953cabb5d92a166b837e5c1e6b51f823f9892df76a08a406ba241df5` (.sha256 beside it, `shasum -c` OK; 3.55 MB — tar of engine/app excluding nothing; the pre-styling freeze was 67.9 MB, likely because it carried __pycache__/.pre-* at the time — noted, not investigated). No staged file was newer than the freeze when the merge began.
2. Seatguard: claims by seat `lane-D-staged-merge` on every staged path written (ledger: staged `.seatguard/claims.jsonl`); released at the end of this packet. Floor CLAIM line posted before the first write.
3. Base check per file, then byte-identical copies where the staged file equalled the exp patch's base; a declared 3-way for the two files whose staged copy was NOT the exp base (main.py, casual.py). Every pre-existing file got `<file>.pre-laneD-20261027` beside it before overwrite. New files have no backup (declared).
4. Manifests (sha256, client/ + server/, no __pycache__): before `manifest_staged_before.sha256` (415 files), after `manifest_staged_after.sha256` (445), exp `manifest_exp.sha256` — all copied into this packet.

## Base findings (why each merge was safe)
- staged `server/main.py` (sha 9a24213f…) is byte-identical to `candidates/iris-rooms-exp-1/app/server/main.py` — the staged engine is the ROOMS lineage, not the creative-exp lineage. 354-line diff to exp main.py; see 3-way below.
- staged `client/assets/assist-launch.js` (94f7091b…) == exp `assist-launch.js.pre-halfport-20261026` → straight copy of exp HEAD (9028fa6f…, carries ✦ star + History General panel).
- staged `glass-topbar.js` (eaee6b76…) / `.css` (905f1f3f…) == exp `.pre-allcall-20261027` bases → straight copies (all-call client).
- staged `server/recall.py` (ab925e00…) == exp `recall.py.pre-histrecord-20261027` → straight copy (History General record isolation).
- 12 staged pages lacking the ✦ tag (books, business-signin, comms, creative, files, keychain, notes, os, play, reading, rooms, writer): `diff` against exp was EXACTLY the one `<script src="/assets/assist-launch.js" defer></script>` line each → straight copies, byte-identical to exp. (rooms.html closes the open note in Gopher's styling REVIEW correction.)
- staged `server/nodes_door.py` vs exp: the diff is purely the ALLCALL-001 `_allcall_hold` emitter (30 lines) → straight copy, declared as part of the all-call unit.
- staged `server/casual.py` (fc23c1a1…) != exp pre-designhatpin base (f2b0b16b…): staged carries iris-rooms-exp-1 differences (ROOM-TOOLS-001 `_room` condition, comments). → 3-way: ONLY the DESIGN-HAT-PIN-001 four-line change applied onto staged; staged-only lines preserved. Result diff vs staged backup = exactly the packet's diff.

## main.py 3-way (staged base, exp hunks selected)
Unified diff staged→exp has 19 hunks. TAKEN (15): RedirectResponse import; HISTORY-GENERAL-COMMENTARY/PANEL/GROUND/QUOTE/RECORD-001 (passage labelling, `head=` plumbing through `_apply_identity_preamble`, `_select_turn_skills`, `_chatlog_path/_chatlog_append(head=)`, `ChatBody.head`, model pick for head, debug hook, continuity block per head); ALLCALL-001 + LIBRARY-001 register hooks; `/books` → 302 `/library`. NOT TAKEN (4, out of lane, declared): INTERCONNECT-001 `product` field in /api/health; removal of the staged DESK-VAULT/ROOMS block at its staged position (exp has it later as PORT-ROOMS-001 — staged keeps its own); comment-only prime_sign/budget_keeper lines; the creative-modules/phone_mirror reorder + IRIS-DNA-001 / IRIS-GRAFT-001 / IRIS-PEERS-001 hooks (not reviewed/approved for staged). Residual `diff merged main.py vs exp main.py` = exactly those 4 hunks (75 lines). `unit_type`/UNIT_OPEN referenced by the taken RECORD hunk already exist in staged's function (line 1081) — verified before applying. py_compile with the release python: OK.

## Retired (no deletes)
- `server/_to_delete/test_allcall.py.laneD-20261027` + `NOTE_test_allcall_laneD-20261027.md`: exp's test_allcall.py ran 14/16 against staged; the 2 errors patch `link_keeper._allcall_skip_logged`, which only exists in exp's link_keeper.py (ALLCALL-002) — a file under lane-E-lead-packets' seatguard claim, so lane D did not merge it. Restore the test beside link_keeper when lane E's merge lands.

## Servers (announced on floor + to Gopher)
- :8765 (live Prime, pid 815) and :8772 (exp, pid 5100): untouched, both healthy before and after.
- :8790 before: pid 32139 (started 08:41, staged-verify recipe). During my merge write (11:38:50–58) lane-A's `iris-control-staged.sh restart` cycled :8790 (their NOTICE on the floor) — the server it started (pid 23123) had imported the PRE-merge main.py (/library and /api/allcall/v1 → 404). 32139 survived SIGTERM as an orphan without its socket. I TERMed both; both needed KILL (declared). Relaunched 11:43:16 as pid 27957 with the same recipe (cwd staged app; `SELFLIGHT_INSTANCE=staged-verify SELFLIGHT_HOME=/tmp/staged-verify-home SELFLIGHT_SHARED_HOME=~/.selflight SELFLIGHT_PORT=8790 SELFLIGHT_OLLAMA_URL/OLLAMA_HOST=http://127.0.0.1:8766 SELFLIGHT_WORKSPACE_ROOT=~/HIFIDecant/workspace SELFLIGHT_HOST=127.0.0.1 PYTHONPATH=vendor:server:release python-deps`, release python 3.12). Log: `work/lane-D-staged-merge/staged-8790-run2.log`. Boot lines: DESK-VAULT attached, Prime sign, Budget keeper, `all-call: GET /api/allcall/v1 …`, `library registered (/library, /api/library/v1)`; no "NOT attached", no Traceback.
- Floor line asks lane-A to hold :8790 cycles until this DONE; after it, Iris Control may cycle freely (the tree is now the merged one).

## Verification on :8790 (merged tree)
- 26 surfaces: `/ /accounting /board /business /business/mail /business/signin /business/wiki /casual /comms /console /creative /files /keychain /library /notes /phone /play /polyglot /reading /rooms /security /servers /workshop /writer` → 200; `/books` → 302 `/library` (by design, LIBRARY-001); `/os` → 302 `/` (pre-existing behaviour). 25/25 original pages + Library.
- `/assets/assist-launch.js /assets/heads.json /assets/glass-topbar.js /assets/glass-topbar.css /api/allcall/v1` → 200. heads.json: 14 ids incl. `history-general`. all-call door: `held:false, count:0` (no emitter has fired; link_keeper emitter not merged — see gaps).
- `/api/library/v1`: sections own 9 / apple-books 190 / audible 130 / training 0 = 329; `hidden.apple_books_personal_pdfs: 62`; `errors: {}`. No `.pdf` path appears in the page text (the "PDF" chips are format badges on Doc's own published books in `Desktop/Doc's Copies/Final Books`).
- Rendered (headless Chrome 156 over CDP, 1280×800, fresh profile): ✦ chip present on index, writer, rooms (rooms had none before); the summon popover opens on each; History General row listed (shots 03, 05 show it under "recent"; on the fresh index profile the HEADS section sits below the fold of the popover — shot 01b scrolls to it). History General pane opens off the ✦ menu (shot 02, model gemma4:26b, empty record — no turn was sent, so the head's record stays clean per G2's lesson). JS exceptions: 0. Only 4xx: `/favicon.ico` 404 on index (pre-existing; accounting.html got a favicon fix in the styling merge, index did not).
- Tests (release python, PYTHONPATH as the server): see TESTS.txt — heads star 5/5, library 5/5 (unittest OK), history ground 11 PASS, history panel 4 PASS, history record 5 PASS. `node --check` assist-launch.js + glass-topbar.js OK. py_compile of all merged .py OK.

## Known gaps / for the reviewers
1. `server/link_keeper.py` NOT merged (lane-E claim). So the all-call lights can only be raised by nodes_door's NEED-HUMAN rung for now; the HAL-probe/ALLCALL-002 emitter arrives with lane E. test_allcall retired until then.
2. Out-of-lane exp diffs left unmerged and declared: main.py INTERCONNECT-001 product field, IRIS-DNA/GRAFT/PEERS hooks (+ iris_dna.py, iris_graft.py, iris_peers.py, vtt_persona.py, their tests), `ollama_bridge.py`, `provider_chat.py`, `voice_input.py`, `test_kit_loader.py`. Each needs its own approved card before staged.
3. `garden/skills/history-general.md` and `~/HIFIDecant/Shelves/history-general/` are household-wide (no merge needed); staged's `history_shelf.py` reads the shelf at the same path as exp.
4. Design note (not a defect of this merge): on index at 1280×800 the ✦ popover lists actions first and the HEADS section is below its fold; a stranger looks for the heads first. Gopher's Open ruling #1 (Library button on the Personal dial vs ✦ link) untouched here.
5. Not re-measured: fps under live feeds; Business-room Design Hat armour via a live turn (no chat turn sent on purpose — would write a being's record; casual.py import check only via py_compile + the 4-line diff).
6. The `.pre-laneD-20261027` backups now also appear in the staged tree manifests (30 extra entries) — by design (no deletes).

## Files written (path · sha256 after · backup · how)
| file | sha256 (staged after) | backup beside it | how |
|---|---|---|---|
| client/assets/assist-launch.js | 9028fa6f38b20b5d2af75681028e1e7f728db822736c1ad2b0ee516bcccae875 | client/assets/assist-launch.js.pre-laneD-20261027 (94f7091b559b1c08…) | byte-identical copy of exp (verified sha == exp) |
| client/assets/glass-topbar.js | d8e2bdbc68073b437e56216f2e56350b87df17d7bb3ed0e5ba5fef9b4b5e5f3a | client/assets/glass-topbar.js.pre-laneD-20261027 (eaee6b761fa4329c…) | byte-identical copy of exp (verified sha == exp) |
| client/assets/glass-topbar.css | e1c3179ffcf4accea0489c38d9c4d3723b759fea7178d5ce89f71de073daae3a | client/assets/glass-topbar.css.pre-laneD-20261027 (905f1f3f779aa996…) | byte-identical copy of exp (verified sha == exp) |
| server/recall.py | dafd5ff94abadd9d2b64eaa779ac48dfe2ea4caac15470311cfb5f94622b2288 | server/recall.py.pre-laneD-20261027 (ab925e00a2194ca6…) | byte-identical copy of exp (verified sha == exp) |
| server/nodes_door.py | 7c588d36df14a05c3ef623219dd76f552f128c32d16d9446b28a8f8ed327c5f1 | server/nodes_door.py.pre-laneD-20261027 (8b209bf44fe91cf1…) | byte-identical copy of exp (verified sha == exp) |
| client/books.html | 8961e46c8e434c72a55625653e665ca0dce81a95e1603f907408f434f829bbe0 | client/books.html.pre-laneD-20261027 (ad7d870ba279619e…) | byte-identical copy of exp (verified sha == exp) |
| client/business-signin.html | 09db3b27197666daaf4fbfc3711b44f79d80354d22157fdbac6f030f9c9f7432 | client/business-signin.html.pre-laneD-20261027 (9913244a5a245827…) | byte-identical copy of exp (verified sha == exp) |
| client/comms.html | e969e0ab4f025bd5645a36c469c8a76780a857bae796c6796b45d8e00a1674b3 | client/comms.html.pre-laneD-20261027 (1351e4d5814af66e…) | byte-identical copy of exp (verified sha == exp) |
| client/creative.html | 71ff2d14d2765a4f829e315bb5594cd049715257d5ddc6516425bc89b5eb82ff | client/creative.html.pre-laneD-20261027 (ec840f3372e25ecb…) | byte-identical copy of exp (verified sha == exp) |
| client/files.html | dfb05d3b30b3f9fb7906f53cadf308578baf08e46b93652b2ede78e9769fde39 | client/files.html.pre-laneD-20261027 (de0b440a3fcbaf50…) | byte-identical copy of exp (verified sha == exp) |
| client/keychain.html | 95ec6ead7f5c2726ad02d23dff666011438d182eefb25039469dca03ebd8f825 | client/keychain.html.pre-laneD-20261027 (73dbe25cab642cb6…) | byte-identical copy of exp (verified sha == exp) |
| client/notes.html | 5bf9a62a331afba5bf7e790273085df0c8707c6f1a5efaa5d33ea0556d927121 | client/notes.html.pre-laneD-20261027 (c51f9fc3b608e04f…) | byte-identical copy of exp (verified sha == exp) |
| client/os.html | 7ff1203e94e124fb422c6c1abe2dfd76b72c06632cb412ecb4c177ebe3d46a86 | client/os.html.pre-laneD-20261027 (6f0d8acfb4454a14…) | byte-identical copy of exp (verified sha == exp) |
| client/play.html | f14f546802556079ff06d2e8ef6863ff4d5cd744db5c9771b217c94dd1076578 | client/play.html.pre-laneD-20261027 (0c6230e66c408357…) | byte-identical copy of exp (verified sha == exp) |
| client/reading.html | b2130bbc232f32f4d1ad18fd8e9cf9c7118558e5213fa3740ad33a66d6bcfcad | client/reading.html.pre-laneD-20261027 (26177dacaef4bcc8…) | byte-identical copy of exp (verified sha == exp) |
| client/rooms.html | ef011a6ac8815554b7d0424ff6d5d32f52cc38321151a1bee8f904665074e2b4 | client/rooms.html.pre-laneD-20261027 (70c9bc4d9a9dc838…) | byte-identical copy of exp (verified sha == exp) |
| client/writer.html | 0c60d9eba3d632e257450f5d8b01834809568bcef54ab2920d4fcbe18b223d9c | client/writer.html.pre-laneD-20261027 (0d115e0e20fe4a5c…) | byte-identical copy of exp (verified sha == exp) |
| server/main.py | 833a2089dc77c89d6300dd45ac25e36e25164ac60adcbbe5c5f160af10883249 | server/main.py.pre-laneD-20261027 (9a24213f64ac60e8…) | 3-way (staged base + selected exp hunks), see diff_*_pre-laneD_vs_merged.txt |
| server/casual.py | 9d4cba883d699944fac77a5f5284b735d6352ee604b6e9acab5bfab80bef8cf4 | server/casual.py.pre-laneD-20261027 (fc23c1a1f6af0ab7…) | 3-way (staged base + selected exp hunks), see diff_*_pre-laneD_vs_merged.txt |
| client/assets/heads.json | 77529f2888af2c75c5bbbf831d9353669628b28656118d30c5a35a6530585741 | (new file, none) | byte-identical copy of exp |
| client/library.html | 191ffb1a64300a67bc800080f93ae3b6ce6683d9ef2a88e905fd852763460615 | (new file, none) | byte-identical copy of exp |
| server/library.py | c3e185666aa4a9efa130d1590753b7cc1ad28e1486169fe12fa713919d06c642 | (new file, none) | byte-identical copy of exp |
| server/history_shelf.py | dc1192627ca83a8a163bea85cefdd777dc4ecdd4b15877facd36a276276d64dc | (new file, none) | byte-identical copy of exp |
| server/allcall.py | 6444e4e2ae5375d0d7a4eb229efccc9fc08e49fb6e00b08514b2b9ef7ffa1d99 | (new file, none) | byte-identical copy of exp |
| server/test_t_heads_star_001.py | 9b6958581e01e5f600b82671b14f02739c39e1bb2f05889322c1771353089ca3 | (new file, none) | byte-identical copy of exp |
| server/test_history_ground_001.py | d19974c88810c8c260faf4d47abc5563bcfac9a005e5d9bc9d39bfcb4b17bd03 | (new file, none) | byte-identical copy of exp |
| server/test_history_panel_001.py | ddb20b1bc7ba15308e1868fb43253fd33f126ac3effd3c5eacf4e4137088e586 | (new file, none) | byte-identical copy of exp |
| server/test_history_record_001.py | 3f87e89c2ca78365adf0964e6175f08a59e5b557925f4847a9c94a88fff9769f | (new file, none) | byte-identical copy of exp |
| server/test_library.py | d22d4bb51f68512c703e15f1a03f5c8827943f6c44369aed0447c09af03bd39f | (new file, none) | byte-identical copy of exp |
| server/_to_delete/test_allcall.py.laneD-20261027 | 2d8718a158da2049c4911a48f1b4c3187f5c1a648d18a129e9c89c740d324a91 | (retired copy) | exp test_allcall.py, retired with NOTE |

## Packet contents
- README.md (this), TESTS.txt (test runs), manifest_staged_before/after.sha256, manifest_exp.sha256, diff_main_staged_vs_exp.txt (pre-merge diff, 354 lines), diff_main_pre-laneD_vs_merged.txt, diff_casual_pre-laneD_vs_merged.txt, staged-8790-run2.log, shots/01_index_star_open.png 01b_index_heads_section.png 02_history_general_pane.png 03_writer_star_open.png 04_library.png 05_rooms_star_open.png
- Worktree with the same artefacts + the CDP scripts: `Selflight/work/lane-D-staged-merge/`

## Seatguard
```
released server/main.py
released server/casual.py
released server/recall.py
released server/nodes_door.py
released client/assets/assist-launch.js
released client/assets/glass-topbar.js
released client/assets/glass-topbar.css
released client/books.html
released client/business-signin.html
released client/comms.html
released client/creative.html
released client/files.html
released client/keychain.html
released client/notes.html
released client/os.html
released client/play.html
released client/reading.html
released client/rooms.html
released client/writer.html
released client/assets/heads.json
released client/library.html
released server/library.py
released server/history_shelf.py
released server/allcall.py
released server/test_t_heads_star_001.py
released server/test_history_ground_001.py
released server/test_history_panel_001.py
released server/test_history_record_001.py
released server/test_library.py
released server/test_allcall.py
no active claims
```

## Change log (append-only)
- 2026-10-27 16:50Z v1 DONE packet posted (lane-D-staged-merge). HOLD for review; nothing live.

## CORRECTION (appended 2026-10-27, lane-D, visible not rewritten)
The Verification section says "shot 01b scrolls to it [the HEADS section]". That is wrong about what 01b shows: the headless profile had already opened History General once, so in 01b History General appears at the TOP of the popover under the "recent" badge, and my scroll-to-HEADS script found no HEADS header to scroll to (it printed "no HEADS header"). Shot 01 (truly fresh profile) is the one where the HEADS header sits below the fold with the actions above it. Both shots are kept. The design note in Known gaps #4 stands. SHA256SUMS regenerated after this append.

## v1.1 CORRECTION (appended 2026-10-27 ~12:05, lane-D): my own orphan
lane-E's packet (§5) reported pid 27957 — my 11:43 staged-verify server — still running with no socket after lane-A's 11:52 cycle took :8790 (pid 37952). Same orphan shape I had just killed in others: these servers survive SIGTERM and keep their background loops (keeper, etc.) without the port. I stopped 27957 (TERM, then KILL) and checked :8790 (37952) stayed healthy. Rule shape I accept for myself: after any cycle of a shared server, `pgrep -f "server/main.py"` and check every pid LISTENs; a pid with the port in its env and no socket is litter — stop it and say so. The launcher gap (a server that loses its bind should exit) is lane-E's noted gap, not fixed here.
