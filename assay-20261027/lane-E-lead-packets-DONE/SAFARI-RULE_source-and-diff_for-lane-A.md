# Safari rule (SAFARI-KEYCHAIN-001) — verified source + diff for lane-A (Iris Control)
From: lane-E-lead-packets, 2026-10-27. Packet: gopher_20261027_iris-control-dock-candidate. reply-to: COUNCIL-FLOOR.

## What the rule is
Project Iris must open its page in SAFARI (keychain / passkey / fingerprint lives there), never the default browser.
The place it lives is the launcher script bundled in each app: Contents/Resources/project-iris-launch.sh.

## Verified source (muster = the live, working app; read-only, nothing touched)
- /Applications/Project Iris.app/Contents/Resources/project-iris-launch.sh
  sha256 bdbec02bd5c29d22966ca18b2bee1f5dbe8286116b55ee6acafc089932c8b324   <- THE SOURCE OF TRUTH
- /Applications/Iris Control.app/Contents/Resources/project-iris-launch.sh (the installed Iris Control, pre-fix)
  sha256 57eb08372253b41f33a1502fb33eefca24f6445bc0155f9d6653b3183a1188f5   <- the GAP (opens with plain `open`, default browser)

## The diff (Iris Control installed -> Project Iris source). Apply = make Iris Control's copy identical to the source.
The only functional difference is the open line; the rest is the comment block that names the rule:
    -open "$URL"
    +open -a Safari "$URL"     # SAFARI-KEYCHAIN-001: keychain/passkey/fingerprint live in Safari; never the default browser
(full `diff -u` of the two installed files is in lane-E's DONE packet: safari-rule.diff)

## State of lane-A's tree at the time of this check (measured 2026-10-27, read-only)
- ~/HIFIDecant/Selflight/candidates/iris-control-1/project-iris-launch.sh
  sha256 bdbec02bd5c29d22966ca18b2bee1f5dbe8286116b55ee6acafc089932c8b324  == Project Iris source, byte-identical.
  So lane-A has ALREADY synced the source into the candidate. Nothing for lane-E to patch in lane-A's tree (and lane-E would not: seatguard).

## Gate for lane-A's DONE (so Gopher/Assayer can check it in one line)
    shasum -a 256 "/Applications/Project Iris.app/Contents/Resources/project-iris-launch.sh" \
                  "<candidate build>/Iris Control.app/Contents/Resources/project-iris-launch.sh"
Both lines must read bdbec02b...; build.sh copies the script into the bundle, so a rebuild after the sync is the only step left,
then the sha of the BUNDLED copy (not just the tree copy) goes in lane-A's packet. Installed /Applications/Iris Control.app stays as is
until Gopher clears a replace (Dock/app changes on Doc's Mac = Gopher's clearance).

## Compliance (lane-E's part of this packet)
SEALS: none opened; read-only sha/diff of two installed scripts. PII: none (script has no names/keys). COST: $0.
LIABILITY: none — no file written outside lane-E's own packet folder; lane-A's tree untouched.
