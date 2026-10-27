#!/bin/bash
# rollback.sh — OPTSPACE-001 rollback (lane-C-option-space, 2026-10-27). Safe to run any time; it never touches live Prime.
# 1) restores the STAGED app.asar from the backup made at install time (if one exists)
# 2) prints the hand steps that undo the app-side hotkey changes (they live in app settings UIs, not files)
set -u
STAGED="/Applications/Iris Prime (Staged).app/Contents/Resources/app.asar"
echo "== Iris staged asar =="
BK=$(ls -t "$STAGED".pre-optspace-* 2>/dev/null | head -1)
if [ -n "$BK" ]; then
  echo "restoring $BK -> $STAGED"; cp "$STAGED" "$STAGED.rolledback-$(date +%Y%m%d-%H%M%S)"; cp "$BK" "$STAGED"; shasum -a 256 "$STAGED"
  echo "expected original sha256 f53d014ab8f91c113bbde12b89a591a42678e4fdfcb85db68af75fca44892e39"
  echo "restart the Staged app (not :8765 / not Iris Prime.app) for it to take effect"
else
  echo "no $STAGED.pre-optspace-* backup found -> staged asar was never changed; nothing to restore"
fi
echo
echo "== hand steps (in-app settings; no file to flip) =="
echo "Gemini:  open 'gemini://settings/speak-to-window' -> 'Always call Gemini' -> set back to Option+Space"
echo "Claude:  Claude -> Settings -> General -> Quick entry -> set back to Option+Space (only if it was changed)"
echo "Siri:    System Settings -> Apple Intelligence & Siri -> Keyboard shortcut -> set back to what it read before (default: Hold Fn/Globe)"
echo
echo "== current values for the record =="
defaults read com.apple.Siri HotkeyTag 2>&1 | sed 's/^/Siri HotkeyTag: /'
defaults read com.google.GeminiMacOS loginItemEnabled 2>&1 | sed 's/^/Gemini loginItemEnabled: /'
defaults export com.apple.symbolichotkeys - | plutil -extract AppleSymbolicHotKeys.60.enabled raw - 2>&1 | sed 's/^/symbolichotkeys 60 (Ctrl+Space) enabled: /'
echo END-OF-ROLLBACK
