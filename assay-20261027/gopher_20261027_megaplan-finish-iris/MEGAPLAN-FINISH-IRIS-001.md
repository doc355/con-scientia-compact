# MEGAPLAN-FINISH-IRIS-001 — Finish Project Iris to ADOPTION-READY
Gopher (cloud, devin-479540fd), 2026-10-27. Status: PROPOSED → runs on Doc's go ("SPEND MONEY NOW").

## What this is (Doc, verbatim)
- "If noone is working choose 5 GOOD agents. Load them out however you think they need to be loaded for this work. Pick your own team."
- "I want at LEAST 5 agents working on this. USE THE BEST FOR THE JOB. SPEND MONEY NOW to get to the finish line!"
- Standing: "Prime is FROZEN … Experimental copy only. Nothing gets published live." "No deletes — retire to _to_delete/." "No seat ever edits a file in a tree another seat is working." "No HIL." "Build until completion. Do not stop."

## Finish line (ADOPTION-READY)
Staged Prime (:8790) carries every approved exp feature, Iris Control starts/stops it cleanly,
Option+Space calls Iris, the packaged app verifies Doc's signature before starting — and the
ONLY remaining step is Doc's fingerprint. Nothing ships to live Prime without it.

## Step zero — compliance pass (house law)
- SEALS: no sealed/LEGAL/FINANCIAL material touched. Prime tree + /Applications/Iris Prime.app OFF LIMITS.
- PII: Library sources (Apple Books/Audible DBs) read-only copies; personal PDFs never shown.
- COST: 5–7 cloud Devin sessions for ~1 day (Doc approved spend). No purchases, no money moves.
- LIABILITY: fingerprint/adoption, door openings (ports on hal), Dock/hotkey changes on Doc's Mac → announced first; adoption is his hand alone.

## The council (8 seats)
| Seat | Who | Archetype (PRIME-COUNCIL) | Lane | Harness worn |
|---|---|---|---|---|
| Director / integrator | Gopher (me, cloud) | Director's seat + Gardener | plan, claims, review every DONE, merge order | all below |
| A | Agent 1 (cloud Devin) | Director's seat (builder) | Iris Control: Stop all/Start all proven both ways, Safari-rule sync, Dock pin (Dock backed up) | candidate-ops, garden-conventions, design-hat (icon/UI) |
| B | Agent 2 (cloud Devin, strongest) | Assayer-builder | Prime launch check: app verifies Doc's signature over engine tree → recovery screen on mismatch (staged only) | compliance-pass, candidate-ops |
| C | Agent 3 (cloud Devin) | builder | Option+Space = Iris Helper only; move Gemini's shortcut off (announce exact change); strip duplicate Ctrl+Space/Cmd+J owners | candidate-ops |
| D | Agent 4 (cloud Devin) | builder + Ledger-Keeper | Merges into staged: ✦ Star (11 pages), History General, Library, Design Hat pin, all-call client. Byte-identical sha256 manifest per file | candidate-ops, garden-conventions |
| E | Agent 5 (cloud Devin) | builder | Lead's packets: hal probe false alarm (probe via ssh health, NOT opening the port), Safari rule into Iris Control's start script copy | candidate-ops |
| Assayer | Agent 6 (cloud Devin, strongest reasoning) | Assayer | red-teams every DONE packet before I accept it; "the honest no is the product" | compliance-pass |
| Jester | Agent 7 (cheap) at the end | Jester | one pass over the whole build; may not build; shouts carry kill conditions | jester-seat |
Local seats (Finish Project Iris, Lead): if they wake, they REVIEW their old lanes' packets; they don't rebuild them.

## How the troops run
1. Claim before touch: each agent posts a seatguard claim + a floor line `[agent-X 2026-10-27] CLAIM: <files/tree>`; one tree per agent; no two agents in one tree.
2. Lane transfer: I post a floor line moving lanes A–D from Finish Project Iris (idle since 01:30) to the agents; it may refuse/reclaim by floor line (NC3).
3. Reach: each cloud agent's VM joins the tailnet (org blueprint auth key) → `ssh root@irisportal` → `ssh christopherhoffpauir@christophers-macbook-pro-3` (absolute paths, single-quoted, `ssh -n` inner hops, END-OF-PASS marker). HYPOTHESIS until Agent 1 proves it; HAL check-mode may need one Doc approval per new node.
4. Work in candidate copies: build in `~/HIFIDecant/Selflight/candidates/<lane>/`, never in staged directly — only Lane D writes staged, from approved candidates, with backups beside every file.
5. Servers: only exp :8772 / candidate ports; staged :8790 restarted only by Lane D, announced; Prime :8765 never.
6. No deletes: retire to `_to_delete/` with a note.
7. DONE packet: `garden/bridge/inbound/<agent>_<date>_<lane>-DONE/` = what changed, files + sha256, backups, tests run + output, screenshots (rendered), servers restarted, known gaps. Plus one floor line.
8. Review chain: Assayer red-team → me (diff + rendered check) → peer builder cross-check (A↔C, B↔D, E↔A). Two passes, or it doesn't merge.
9. Speed: each agent may run up to 3 sub-agents inside its own tree; never across trees.
10. Visible correction: wrong claims get a correction line, never an edit.

## Merge order into staged
E (probe fix, server-side) → D (feature merges) → C (hotkey) → A (Iris Control on staged) → B (launch check, last, because it signs the final tree) → Jester → ADOPTION-READY card for Doc.

## What this megaplan is NOT
Not publishing live. Not touching live Prime. Not opening network doors. Not Doc's fingerprint.

## Open rulings for Doc
1. Library button: replace Reading on the Personal dial, or ✦ menu link?
2. HAL check-mode approvals for new agent nodes (if they appear).

## Kill conditions
- Any agent edits Prime or another agent's tree → that agent stops, its change retires to _to_delete, floor correction.
- Cloud agents can't reach the MBP within 30 min → fall back to hub-and-spoke: agents build in a git repo, Gopher deploys.
- Assayer fails a packet twice → lane goes back to design, not a third patch.

## Change log (append-only)
- 2026-10-27 v1 PROPOSED (Gopher).
