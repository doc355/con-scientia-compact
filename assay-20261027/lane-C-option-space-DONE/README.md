# lane-C-option-space — DONE packet (2026-10-27) — OPTSPACE-001: Option+Space = the Iris call button
Status: Phase 1 DONE (survey + exact change list + rollback), Phase 2 DONE (candidate build + 12/12 tests). Nothing applied, nothing live, no system/hotkey setting changed on Doc's Mac. Gemini/Claude/Siri changes are listed for Gopher to announce to Doc (CHANGE-LIST.md §Changes 1–3).

## Compliance pass (garden/skills/compliance-pass.md) — answered before building
- Seals: nothing sealed/private was opened on purpose. Read-only survey touched app preference plists and settings stores (Gemini, Perplexity, Claude, Siri, symbolichotkeys, universalaccess) via temp copies/defaults export. ACCIDENTAL EXPOSURE, reported here: the Perplexity prefs dump showed two third-party service tokens (a soniox temp key marked expired 2026-10-25 and an ai_coustics token) in my VM's command log. Not copied into this packet (survey-raw/ is grep-filtered for api_key/token/secret), not used, not sent anywhere. Rule made for the shape: dump prefs with a key allow-list or filter before display — never cat a whole third-party plist.
- PII: packet contains Doc's home path and machine name only. No contacts, no messages, no biometrics.
- Cost: $0. No purchases, no API spend, no new ports, no network doors.
- Liability: zero changes applied to any hotkey, login item, Gemini, Siri, system pref, live Prime (/Applications/Iris Prime.app untouched; :8765 untouched; no server restarted). Only writes: candidates/option-space-1/ (new tree, seatguard-claimed by this seat), this packet, two append-only lines on COUNCIL-FLOOR.

## What changed (files + sha256) — all NEW files, no pre-existing file edited, so no .pre- backups were needed
candidates/option-space-1/ (source = releases/20260922-01/desktop/, proven byte-identical to the staged app.asar's main.js/preload.js/recovery.html via @electron/asar extractFile):
```
18cecce9cefc7096114fb7e627882f0e6b8e20dd927086e395f8870ccc28042a  ./.seatguard/claims.jsonl
95b1aa075672bccfb6539b5d75ffdde22b0268499829e8746b50cac4acd73217  ./CHANGE-LIST.md
1b08dec5aa295b35804891ae78ec4477ac782c11f03c4d35c5f7e8e8d76e71e5  ./README.md
bf9261e58aaf8ac65e30f1c9d51e97e00bb006c83b326bd1f60cda12da275b32  ./client/iris-assistant.optspace.patch
55ffbf05c56322f585e2a0cc79b141fe7db637fd85b20034270adc307c58f330  ./hotkey.js
f9d8b51e5f3d4a3ec96760d3ba7fb65a86e6e92e9896dc28adeb37e4dd1ab42a  ./main.js
82854c9a9a1970a2cb898266520315c2227b2f064322fe69e0963ee42a6fcf31  ./package.json
7c027dc184e911dcce78b9c4f6c9ae3596abd0a095c7c9754377b72a312d750c  ./preload.js
44ae377fb88007c705e61e3e361372caf222787709b21f3f80fecd00bb53dd0a  ./probe/optspace-probe.js
6e29a8dfa4d2961606d62774da5c07f05579d3805d3862bed294ffa9e96158df  ./recovery.html
9b46ff1e108e05aeea230fc83d11ab618762263bf0614655cbd5fda7efe631d1  ./rollback.sh
0ac2ca1da01ddc3f4b1ac05861d2bbb5eb3d88bc7026f8dd5b9f92bba495f120  ./test/hotkey.test.js
```
Unchanged copies: recovery.html, package.json (same sha as desktop/). Modified vs desktop/: main.js (+6 OPTSPACE-001 blocks: import globalShortcut + ./hotkey; register in whenReady after tray; will-quit unregister; tray label; ipc call-button-state), preload.js (+iris:call forward, +IRIS.callButtonState). New: hotkey.js, test/hotkey.test.js, client/iris-assistant.optspace.patch (for Lane D), probe/optspace-probe.js (Phase-3 instrument, NOT run), README.md, CHANGE-LIST.md, rollback.sh.
Desktop sources for reference: main.js da3d56d4…, preload.js 232e43bd…, recovery.html 6e29a8df…; staged app.asar f53d014a… (== live Prime's asar).

## Tests run (on the MBP, /opt/homebrew/bin/node v26.10.0)
`cd candidates/option-space-1 && node --test test/` → tests 12, pass 12, fail 0 (full output: survey-raw/survey_out_ship.txt). `node --check` main.js/preload.js/hotkey.js → ok.
Not run: Electron launch of the candidate (would briefly register the Mac-wide hotkey and show a Dock icon — needs Gopher's clearance per house rule) and probe/optspace-probe.js (same reason). Both are the Phase-3 instruments.

## Survey result (data; detail in CHANGE-LIST.md)
- Option+Space: owned by Gemini.app (running, login item), built-in default; the value is in NO file/plist/sqlite on this Mac → the change is in Gemini's settings UI (deep link gemini://settings/speak-to-window). Claude.app would contend when launched (default quick-entry ⌥Space, UNVERIFIED locally; not running). Siri: no HotkeyTag override → system default; verify not ⌥Space.
- Ctrl+Space: macOS input-source hotkeys 60/61 already disabled; only in-page Iris (assist-launch.js) uses it. ⌘J: no Mac-wide owner; in-page Iris + per-app menus only. Perplexity uses ⌘⇧Space (no conflict). No Karabiner/BetterTouchTool/Hammerspoon/skhd installed.
- Iris side: staged Electron shell has NO globalShortcut today; client has an in-page ⌥Space listener (window-focused only) and a prefs caption still saying "Ctrl+Space or ⌘J".

## Rollback
rollback.sh (here and in the candidate): restores staged app.asar from app.asar.pre-optspace-* if one exists (none today), prints the hand steps for Gemini/Claude/Siri, records current values. Never touches live Prime.

## Servers restarted: none. Ports opened: none.
## Known gaps / send-back candidates
1. Gemini's post-change key name is unknown until it is changed once (then re-survey app-settings.store/group plist and add the key to rollback.sh).
2. Claude and Siri defaults on THIS Mac are UNVERIFIED (apps not running / no override key); CHANGE-LIST gives the check.
3. Client hook (client/iris-assistant.optspace.patch) + prefs.js caption are Lane D's staged tree — handed over, not applied.
4. No live Electron run of the candidate; the hotkey registration is tested against a fake globalShortcut only. Phase-3 probe exists for the real check.
5. seatguard note: claim on the new dir was recorded before files existed; re-claimed with files after the build (ledger shows both).
