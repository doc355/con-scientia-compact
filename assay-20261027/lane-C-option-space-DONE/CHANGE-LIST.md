# OPTSPACE-001 — exact change list (Phase 1, lane-C-option-space, 2026-10-27). PROPOSED — nothing below has been applied.
Machine: Christophers-MacBook-Pro-2 (tailnet christophers-macbook-pro-3), macOS 27.0.1. Survey was read-only (defaults export / plistlib / sqlite on temp copies / strings).

## Who owns what today (DATA)
| Key combo | Owner found | Where | Grade |
|---|---|---|---|
| Option+Space | Gemini.app (com.google.GeminiMacOS 1.119.2.914, running, login item) — built-in default "Always call Gemini / Full chat" shortcut; modes hold / double-tap / custom / none | NO file holds the value: ~/Library/Preferences/com.google.GeminiMacOS.plist, Group Containers/group.com.google.gemini/…/group.com.google.gemini.plist, Application Support/com.google.GeminiMacOS/Data/app-settings.store + minichat-settings.store all carry no shortcut key → default lives in the binary (strings: GlobalShortcutConfig, SHORTCUT_KEY_SPACE, gemini://settings/speak-to-window) | CERTIFIED owner (Doc's report + Gemini default); storage location CERTIFIED absent from files |
| Option+Space (latent) | Claude.app — quick-entry default is ⌥Space upstream; app NOT running now (only chrome-native-host); no stored shortcut key in Application Support/Claude/config.json or Local Storage | would contend only when Claude main app runs | UNVERIFIED on this Mac |
| Option+Space (in-page) | Iris staged client `engine/app/client/assets/iris-assistant.js` keydown altKey+Space → toggle() — works only when the Iris window is focused | staged tree (Lane D) | CERTIFIED |
| Ctrl+Space | macOS "Select previous input source" symbolic hotkey 60 — **already disabled** (enabled=False); 61 Ctrl+Opt+Space also disabled | com.apple.symbolichotkeys AppleSymbolicHotKeys 60/61 | CERTIFIED |
| Ctrl+Space (in-page) | Iris staged `assist-launch.js` handleHotkey → summon() (pref `summon.hotkey`) | staged tree | CERTIFIED |
| ⌘J | no Mac-wide owner found (no NSUserKeyEquivalents anywhere, no Karabiner/BTT/Hammerspoon/skhd installed); in-page: Iris assist-launch.js (⌘J/Ctrl+J → summon), plus per-app menu items (Finder, Chrome, Devin) when focused | — | CERTIFIED (global); in-app owners not enumerated |
| ⌘⇧Space | Perplexity "showCommandBar" (macHotkeyManager.hotkeys.v1 carbon 768/kc49) — no conflict with ⌥Space | ai.perplexity.macv3 plist | CERTIFIED |
| Siri | com.apple.Siri has no HotkeyTag key → system default (on current macOS: Hold ⌘Space or Fn/🌐; not ⌥Space) | — | default value UNVERIFIED on this build; verify in System Settings → Apple Intelligence & Siri → Keyboard shortcut |

## Changes to make (file / key / old → new), in order
1. **Gemini — release Option+Space** (Doc's hand, in-app; Gopher announces first)
   - Surface: Gemini menu-bar icon → Settings → Keyboard shortcuts (deep link `open "gemini://settings/speak-to-window"`), row "Always call Gemini" (also called "Full chat keyboard shortcut").
   - Old: ⌥ Space (built-in default; no plist key). New: **No shortcut** (or a combo Doc picks, e.g. ⌃⌥G — his choice, not assigned).
   - File/key: none exists to edit; Gemini keeps this in its own settings store the moment it is changed (then it will appear in `~/Library/Application Support/com.google.GeminiMacOS/Data/app-settings.store` or the group plist — re-survey after the change to record the new key for the rollback file).
   - Rollback: same pane → set back to ⌥ Space.
   - Blunt alternative (only if Doc prefers Gemini gone): System Settings → General → Login Items → Gemini off, then Quit Gemini. Old `loginItemEnabled=1` in com.google.GeminiMacOS.plist (Gemini's own bookkeeping; the real switch is the Login Items pane, do not `defaults write` it). Rollback: Login Items → Gemini on.
2. **Claude — clear quick-entry** (Doc's hand, in-app, only when Claude is next opened): Claude → Settings → General → "Quick entry" shortcut: old ⌥Space (default, UNVERIFIED) → New: none. Rollback: set back.
3. **Siri — confirm, no change expected**: System Settings → Apple Intelligence & Siri → Keyboard shortcut must NOT read "Press Option Space". If it does: old "Option Space" → new "Hold 🌐/Fn" (or Doc's pick). Rollback: set back. (File: com.apple.Siri `HotkeyTag` — absent today; Apple writes it when changed.)
4. **macOS Ctrl+Space / Ctrl+Opt+Space**: no change — com.apple.symbolichotkeys 60/61 already enabled=False (old=New=False).
5. **Iris shell (this candidate → staged asar, Phase 3)**: `/Applications/Iris Prime (Staged).app/Contents/Resources/app.asar`: old sha256 `f53d014ab8f91c113bbde12b89a591a42678e4fdfcb85db68af75fca44892e39` → new = asar packed from candidates/option-space-1 (sha recorded at pack time). Backup `app.asar.pre-optspace-<date>` beside it. Live Prime.app: untouched, frozen.
6. **Iris client (Lane D, staged tree)**: `engine/app/client/assets/iris-assistant.js` — add the `message` listener in `client/iris-assistant.optspace.patch` (old: no listener → new: `{type:'iris:call'} → toggle(true)`). `engine/app/client/assets/prefs.js` line ~`aToggle("summon.hotkey", "Hotkey summon", "Ctrl+Space or ⌘J")` → old caption `"Ctrl+Space or ⌘J"` → new `"Option+Space anywhere · Ctrl+Space / ⌘J in Iris"`. Backups beside each.
7. **Duplicates to retire (so Option+Space has ONE owner = Iris Helper/Prime shell)**: in-page altKey+Space listener in iris-assistant.js may stay (it only fires when Iris is focused and the shell's global one wins first); if Doc wants exactly one code path, Lane D removes those 1 lines after the patch in step 6 lands — not required for ownership.

## Verification after the change (Phase 3 instrument)
`cd releases/20260922-01/desktop && ./node_modules/.bin/electron candidates/option-space-1/probe/optspace-probe.js` → `{"ok":true,"state":"registered"}` = Option+Space is free for Iris; `held-by-another-app` = someone still owns it (re-check Gemini/Claude/Siri). Then launch staged Prime: tray must read `Call button: Option+Space` with no suffix.
