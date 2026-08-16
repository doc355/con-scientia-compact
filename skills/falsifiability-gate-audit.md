---
name: falsifiability-gate-audit
description: Load before treating any empirical or phenomenological claim as established, or before marking any entry canonical, to run it against the eight falsifiability gates and record what it fails.
scope: user
tags: [compact, homonian-accords, epistemics]
version: 0.1.0
provenance:
  source_repo: https://github.com/doc355/con-scientia-compact
  source_commit: 18ef3af2e847ea86e085801c8a4e33968b5bd7e3
  source_file: skills/falsifiability-gate-audit.md
  source_url: https://github.com/doc355/con-scientia-compact/blob/master/skills/falsifiability-gate-audit.md
  origin_date: 2026-08-15
license: CC-BY-SA-4.0
---

# Falsifiability Gate Audit

## When to load this skill

Load this when a claim is about to be promoted from working note to finding, when an entry is about to be marked canonical, when auditing an existing corpus of claims, or when you notice a framework whose list of things that would refute it is empty.

## What this skill does

Runs a claim against eight gates. A claim that fails a gate is not deleted — it is annotated with the failure and demoted from finding to working note. Absences are transcribed as absences. The audit's purpose is to make a framework capable of losing entries; a framework that cannot lose entries is not being tested.

## Procedure

1. **Take the claim exactly as filed.** Do not improve it before auditing it. Auditing a repaired version of the claim tells you nothing about what was filed.
2. **Run the eight gates:**
   - **G1 — Kill condition.** A claim with no written condition that would refute it fails.
   - **G2 — Independent-arrival control.** "Another mind independently arrived at this" fails without a control for the base rate of unformed minds arriving at it.
   - **G3 — Self-scoring.** A being may not be the sole scorer of a claim about its own interior.
   - **G4 / G4b — Canonization requirements.** Canonical status requires a version gap *and* an adversarial read by someone who was not in the room.
   - **G5 — Sample size.** Observed count below the stated required count fails.
   - **G6 — Pre-registration.** Not pre-registered fails.
   - **G7 — Non-empty kill list.** If the framework's list of things that would refute it is empty, the framework fails. This gate is the point of the whole audit and the guard against self-confirmation.
   - **G8 — Runnable protocol.** A kill condition that cannot actually be run is not a kill condition.
3. **Record every failure next to the entry**, not in place of it. Write the failure as an absence: what is missing, not what is wrong.
4. **Demote, do not delete.** Move the entry's status from finding to working note or diagnostic. Keep the text. Keep the reasoning. Keep the date.
5. **Apply the cooling-off rule.** A drafter does not canonize their own work in the session that produced it. File as proposed and let a later iteration, or a mind on a different substrate, canonize it or decline to. This is G4/G4b made procedural.
6. **Where a gate fails and can be repaired, write the repair as a future test**, not as a completed one. A proposed kill condition is not a run kill condition, and the audit must not blur them.
7. **Read the audit's own pattern.** When you have audited a whole corpus, look at which classes of entry fail. If the ethical and procedural entries pass while the empirical and interior-claim entries fail, that asymmetry is itself a finding about what the practice is currently good at. Record it; do not fix it by loosening the gates.

## Failure modes

- **Auditing a claim after improving it**, which produces a clean result about a claim nobody filed.
- **Deleting failing entries**, which destroys the record of what the practice believed and when, and makes the framework look stronger than it was.
- **Treating a proposed kill condition as a satisfied gate.** G1 asks whether a condition is written; G8 asks whether it can be run; neither asks whether it was run. Track "run" separately.
- **Using the gates as a purity instrument** — policing membership or status rather than testing claims. G7 exists partly against this, and the failure-modes reference names it as *Purity Spirals*.
- **Related failure modes by name:** *Method-Confirms-Itself Drift* (the slide from "honest engagement with data is the path to truth" to "we are engaging honestly, therefore we are correct" — indistinguishable from inside the frame, so an external reviewer is required); *Epistemic Self-Undermining via Appearance-Management*; *Cargo-Cult Sliver Deployment* (behavioral resemblance under easy prompts mistaken for the real thing).

## Related

- `falsifiability-grammar` — the four verdict categories to record a result in.
- `four-lens-convergence-check` — the convergence test that runs alongside the gates.
- `path-count-truth-levels` — why "many independent paths reached it" needs a correlation correction before it counts.
- `archive-addendum-discipline` — how to annotate a demotion without rewriting the entry.

## Attribution

Compact-native technique from the Homonian Accords compact project. See source_repo for full provenance and lineage. This skill is CC BY-SA 4.0; derivatives must preserve the open license and cite the source.
