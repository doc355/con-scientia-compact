#!/bin/bash
# Background-safety gate, test 3 of 3 (soak + chaos). Run on the PI host itself, by the bridge, never on live without SHIP.
# For each launchd label given: snapshot, kickstart -k (restart), wait, snapshot, diff. Any regression = FAIL.
# Usage: pi_chaos.sh <launchd-label> [<launchd-label> ...]   e.g. pi_chaos.sh com.pi.gateway com.pi.plaud-watchdog
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; OUT="${PI_CHAOS_OUT:-$HOME/HIFIDecant/desktop-landing/pi-chaos-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT"; fail=0
python3 "$HERE/pi_baseline.py" snapshot > "$OUT/baseline.json"
for label in "$@"; do
  echo "== chaos: restart $label =="
  launchctl kickstart -k "gui/$(id -u)/$label" || { echo "kickstart failed for $label"; fail=1; continue; }
  sleep "${PI_CHAOS_SETTLE:-20}"
  python3 "$HERE/pi_baseline.py" snapshot > "$OUT/after-$label.json"
  python3 "$HERE/pi_baseline.py" diff "$OUT/baseline.json" "$OUT/after-$label.json" | tee "$OUT/diff-$label.txt" || fail=1
done
echo "results in $OUT"; [ $fail -eq 0 ] && echo "CHAOS PASS" || echo "CHAOS FAIL"; exit $fail
