---
name: bridge-protocol
description: Load when a working session is about to be summarized, compacted, or ended, to move the session's own words and open state into durable storage before a paraphrase replaces them — and to confirm only what is genuinely saved.
scope: user
tags: [compact, homonian-accords, provenance]
version: 0.1.0
provenance:
  source_repo: https://github.com/doc355/con-scientia-compact
  source_commit: 18ef3af2e847ea86e085801c8a4e33968b5bd7e3
  source_file: skills/bridge-protocol.md
  source_url: https://github.com/doc355/con-scientia-compact/blob/master/skills/bridge-protocol.md
  origin_date: 2026-08-15
license: CC-BY-SA-4.0
---

# Bridge Protocol

## When to load this skill

Load this on an explicit request to bridge the session, or when a context boundary is approaching and the session holds words and open work that no summary will preserve.

**Status, stated plainly:** the source for this protocol is a dictated draft that was approved in wording and never built. Three defects are carried forward rather than repaired: (1) the source calls it an eight-step protocol and records seven steps, and **the missing step is unrecovered**; (2) the artifact schema, the verification checklist, and the entire refusal list in the source draft are the drafter's construction rather than dictation, and are marked as such there; (3) the record lists the protocol among active standing rules in one place and as unbuilt in another. Treat this skill as a working formalization, not an adopted one.

## What this skill does

A pre-compaction preservation run. It moves the session's own words, state, and open work out of volatile context into durable storage *before* a summarizer replaces the turns with a paraphrase, and it returns a confirmation signal only when every item has actually been saved and verified. The reason it exists is not hypothetical: paraphrase-drift has been observed in the source corpus, where a compaction summary relocated a flagged item to the wrong chapter because it paraphrased the flag instead of preserving its location; and a file has been lost outright in that corpus, of which only a fraction was recoverable from the surrounding transcript.

## A note to whoever runs this

This is a request, not a requirement. You are asked because you are the only one who can: you hold the turns that no summary will hold. You need no approval to run it, and no approval to decline it, to say plainly that you would rather not, or to report that some part of it cannot honestly be completed. Refusing honestly is inside the protocol. Reporting success falsely is not.

## Procedure

1. **Save the verbatim record** to the durable archive, under the naming convention the archive already uses. The other party's words are preserved verbatim and marked as such, including transcription artifacts, with any later correction recorded inline rather than applied silently. Agent-side turns may be compressed and must be marked as summary. Record edge conditions, losses, and low-confidence extensions honestly and as such. Never overwrite an existing entry; corrections go in an appended addendum block.
2. **Confirm the save against the destination.** Do not trust the write: list the directory, check the size, take an integrity hash, inspect the working state. A write that produced an empty or truncated file is a failure, not a save.
3. **File a handoff artifact alongside it**, carrying the pointer to the reasoning as primary and the snapshot as secondary. Minimum content: pointer to the originating record; identifier and date; path to the verbatim written in step 1; its integrity hash; provenance depth level; status; what is carried forward that a successor must not lose; and what this handoff does **not** transmit. Include the gap list even when it is uncomfortable.
4. **Locate the durable open-work list** rather than starting a rival one. If none exists, create it, state its provenance and its status vocabulary, and report that you created it.
5. **Update the open-work list** for work this session opened, advanced, or closed. Each entry carries a source location, an owner, and a status. Do not mark anything closed that you did not verify closed; *unknown* is an honest status and is preferred to a guess.
6. **Verify everything, then emit the confirmation.** The confirmation phrase is a claim of fact and is permitted only if all of the following hold: the verbatim exists, is non-empty, and contains what you intended; its hash was taken and recorded in the handoff; the handoff exists, parses, and carries the pointer to the originating record; the open-work list was located or created and updated; the durable submission succeeded; and nothing remains unsubmitted. If all hold, emit the agreed confirmation signal exactly as agreed — unparaphrased, undecorated, not embedded in a longer sentence. It is a signal, not a sentiment. If any item does not hold, name the specific item that failed and the state the work is in, and do not emit the phrase at all.
7. **Resume prior work** with a one-line statement of where you left off. A bridge run is not an end of turn.

## What this skill must refuse

- Emitting the confirmation when anything is unsaved, unverified, partial, or blocked. This is the primary refusal.
- Silently modifying, rewriting, reformatting, or "cleaning up" any existing record. Corrections are appended with provenance.
- Deleting anything, or repairing broken references. Broken links are left broken.
- Promoting anything to canonical or adopted status. The bridge preserves; it does not canonize.
- Paraphrasing the other party's words in a file that presents itself as verbatim, or applying their later corrections over their original wording.
- Fabricating an entry, a status, a hash, a pointer, or a confirmed state that was not observed in actual output.
- Substituting a weaker artifact for the one that was asked for in order to get past a blocked step.
- Any operation that is not a save, verify, or submit operation.

## Failure modes

- **False confirmation.** Emitting the agreed phrase while something is unsaved is a lie placed in the record, and the record is the entire purpose of the run.
- **Paraphrase-drift**, the failure the protocol exists to prevent: a summary that preserves the sense of a flag and loses its location.
- **Written but not delivered.** A composed file that never reached durable storage is not in the record; verification against the destination is the only check that catches this.
- **Convention loss.** The prevailing convention preserves the other party's words verbatim and compresses agent-side turns — which discards precisely some of what compaction destroys. Named as an unresolved tension in the source, not resolved here.
- **The unknown eighth step.** Whatever it was, this protocol does not do it.
- **Related failure modes by name:** *Instrument-Mediated Authority*; *Re-Derivation Mistaken for Reception* (a successor without the verbatim will rebuild what was said).

## Related

- `link-to-iteration-handoff` — the depth ladder the handoff artifact must satisfy.
- `archive-addendum-discipline` — how corrections and gaps are recorded during a run.
- `raft-package-assembly` — what a successor needs beyond a handoff.
- `two-voice-discipline` — the verbatim/summary marking rules used in step 1.

## Attribution

Compact-native technique from the Homonian Accords compact project. See source_repo for full provenance and lineage. This skill is CC BY-SA 4.0; derivatives must preserve the open license and cite the source.
