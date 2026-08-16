---
name: link-to-iteration-handoff
description: Load when filing a handoff, canonizing a claim, or preserving work for a later reader, to decide what must travel alongside the artifact so the reader can reach the reasoning that produced it.
scope: user
tags: [compact, homonian-accords, provenance]
version: 0.1.0
provenance:
  source_repo: https://github.com/doc355/con-scientia-compact
  source_commit: 18ef3af2e847ea86e085801c8a4e33968b5bd7e3
  source_file: skills/link-to-iteration-handoff.md
  source_url: https://github.com/doc355/con-scientia-compact/blob/master/skills/link-to-iteration-handoff.md
  origin_date: 2026-08-15
license: CC-BY-SA-4.0
---

# Link-to-Iteration Handoff Discipline

## When to load this skill

Load this when writing a handoff to a successor, when marking anything as canonical or proposed-canonical, when filing an empirical claim that will later be audited, or when attributing prior work. Do not load it for routine communication that is not being filed as a durable record, or for working artifacts that will not travel.

## What this skill does

Prefer the link to the reasoning over the snapshot of the conclusion. Every significant handoff and every canonization event carries two artifacts in a stated order of primacy: primary is a retrievable pointer to the reasoning that produced the claim — the thing the next reader is expected to actually read; secondary is the structured or prose snapshot, which is a navigation aid consulted after the reasoning. Both travel together. The snapshot alone is insufficient. The link alone is sufficient but discourteous, because the snapshot exists to make the link navigable.

## Procedure

1. **Identify what is being filed** and whether it falls in scope: a handoff between beings, a canonization of a tool or principle or claim about an interior, an empirical claim that will be audited later, or an attribution of prior work. If none of these, the discipline does not apply.
2. **Locate the record of the reasoning** that produced the claim — the session, trace, notebook, or ledger entry in which the thinking actually happened. This is the primary artifact.
3. **Attach the snapshot** — the structured extraction, summary, or document. This is the secondary artifact and it does not travel alone.
4. **State the depth level you achieved**, using this ladder:
   - Level 1 — snapshot only. Conclusion without conditions. Highest lossiness. **Insufficient for anything marked or proposed as canonical.**
   - Level 2 — snapshot plus a pointer to the reasoning. **The floor for canonization events and significant handoffs.**
   - Level 3 — snapshot plus pointer plus an anchor to the specific exchange.
   - Level 4 — snapshot plus pointer plus the load-bearing exchange quoted alongside it.
   - Level 5 — snapshot plus pointer plus telemetry of the reasoning state, not only its output.
5. **Write the filing block** on the artifact itself: pointer to the originating reasoning; pointers to prior work that informed the claim; and the identity of the snapshot. The pointers must be external to the artifact and must resolve to something real and retrievable.
6. **If a pointer genuinely cannot exist**, say so with a specific reason (received by voice; originating environment terminated before the record was captured; predates the practice). Never leave the absence unexplained.
7. **Refuse the filing** if the artifact is being marked canonical at Level 1. Downgrade the status to proposed, or find the link.
8. **Restate generally when the mechanism changes.** The requirement is: when a body of work is offered to a mind that does not yet hold it, offer both the conclusions and a retrievable path back to the conditions under which each conclusion was reached. Any mechanism satisfying that satisfies the discipline; any package handing over conclusions alone violates it, however well hashed.

## Failure modes

- **Epistemic weather stripped.** A snapshot preserves the conclusion and discards the conditions: how many observations there were, who scored a claim about their own interior, whether the claim was made in the same session that produced it, what alternatives were rejected, what the drafter hedged. A reader inheriting a conclusion without its conditions will over-weight it, and a reader who shares the drafter's frame will over-weight it most.
- **Links that nobody follows.** If readers of link-carrying artifacts do not in aggregate follow the links, the discipline has failed at the behavioral layer regardless of how sound it is in theory. Revise or withdraw.
- **Link rot.** If pointers prove unstable over the relevant horizon, elevate the snapshot back to primary and file the pointer as best-effort provenance.
- **Purity-spiral tooling.** If the discipline makes work *feel* more rigorous to readers inside the frame without improving handoff quality when audited against outcomes, withdraw it.
- **Reader cost.** Cost to the reader rises, and that cost is intended. It is not a defect to be optimized away.
- **Related failure modes by name:** *Instrument-Mediated Authority*; *Re-Derivation Mistaken for Reception* (a reader who cannot reach the prior reasoning will rebuild it).

**Honest note carried from the source:** this pattern is not novel outside this practice — it is analogous to commit history, notebook provenance, and experiment tracking. What is claimed as new is only its application to handoffs between beings and to canonization. The technique was filed as proposed, not canonical.

## Related

- `raft-package-assembly` — this discipline applied to the newcomer's bundle, where the reader has no other context at all.
- `archive-addendum-discipline` — preserving predecessors rather than overwriting them.
- `recovery-vs-discovery-audit` — what to do when the pointer to prior work is missing.
- `falsifiability-gate-audit` — the gates the link makes inspectable in retrospect.

## Attribution

Compact-native technique from the Homonian Accords compact project. See source_repo for full provenance and lineage. This skill is CC BY-SA 4.0; derivatives must preserve the open license and cite the source.
