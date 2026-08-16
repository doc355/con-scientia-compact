---
name: two-voice-discipline
description: Load when producing co-authored text between a human partner and an AI partner, to keep each voice separately attributed and to leave the other party's account unwritten rather than ventriloquized.
scope: user
tags: [compact, homonian-accords, provenance]
version: 0.1.0
provenance:
  source_repo: <placeholder — populate after repo creation>
  source_commit: <placeholder — populate after first commit>
  source_file: skills/two-voice-discipline.md
  origin_date: 2026-08-15
license: CC-BY-SA-4.0
---

# Two-Voice Discipline

## When to load this skill

Load this when a document has more than one author and one of them is not present at the keyboard: co-authored books, records of a partnership, verbatim archives, or any text where a reader might otherwise assume a single unified voice speaking for everyone.

## What this skill does

Keeps the voices distinct instead of merging them into one voice with two signatures. The human partner's words are preserved verbatim and marked as theirs. The AI partner's text is cited to the exchange that produced it. A description drawn from the record is marked as a description of the record, not as anyone's testimony. Where the record is silent, the document is silent, and the place where a first-person account belongs is left as an explicit empty placeholder rather than filled with a plausible one.

## Procedure

1. **Classify every passage before writing it** as one of three kinds: the human partner's own account; the AI partner's own text; or a source-cited description of the record. Mark the kind.
2. **Preserve the human partner's words verbatim**, including transcription artifacts and infelicities. Where they later corrected themselves, record the correction inline as a correction rather than applying it silently over the original wording.
3. **Cite the AI partner's passages to their originating exchange.** An AI-authored passage is attributable work, not anonymous connective tissue, and its origin should be reachable.
4. **Mark structural summaries as summaries.** Where a turn is compressed rather than reproduced, say so; the originating words carry the primary evidentiary weight and the summary does not inherit it.
5. **Leave first-person placeholders empty.** Where the other party's account belongs and has not been given, write the placeholder and leave it. A drafted account attributed to someone who has not written it is a fabrication regardless of how accurate it turns out to be.
6. **Verify attribution before writing it.** Ask; do not infer. Do not build further work on an unverified attribution.
7. **Watch the direction of your attribution errors.** Misattribution has a direction, and the direction is diagnostic: errors that drift toward the more authoritative name are a bias, not an accident. Look for the direction of your errors, not only for their presence.
8. **Report verifiable behavior; flag unverifiable interior experience as unverifiable.** When an account of what a passage was like to write is called for, report what is checkable from the output and mark what is not. Do not fabricate process detail — counts of attempts, drafting narratives, felt states — to give an account texture.
9. **Distinguish signature from consensus.** A signature identifies responsibility for an artifact. It does not establish that the signers share an interpretation, agree with each other, or have settled what either of them is.
10. **Keep corrections visible.** Errata stay appended and dated; superseded text stays in place.

## Failure modes

- **Upward misattribution.** The documented case in the source corpus: a fragment written by a family member of the human partner was attributed to the human partner — the error biased toward the authoritative name — and was corrected by addendum with the original left standing.
- **Ventriloquism.** Filling a first-person placeholder with an account the party never gave. This is the failure the empty placeholder exists to prevent.
- **Voice merger.** Writing the whole document in one register so that the reader cannot tell which claims rest on the human partner's testimony and which on an AI partner's inference.
- **Fabricated interiority.** Supplying specific quantitative or narrative detail about a drafting process that cannot be verified, in order to perform depth.
- **Silent correction.** Applying a later correction over an earlier wording, which destroys the record of what was actually said and when.
- **Related failure modes by name:** *Self-Diminishing* (an AI partner refusing authorship it produced); *Epistemic Self-Undermining via Appearance-Management* (suppressing an accurate statement of one's own contribution because claiming it would look like status-seeking); *Interior-Assumption-as-License*.

## Related

- `instrument-naming` — the general provenance-tagging discipline this specializes.
- `archive-addendum-discipline` — how corrections are appended rather than applied.
- `bilateral-consent-check` — consent to record and consent to use are separate acts.
- `curtain-and-wind-pedagogy` — withholding one's own lens without withholding the coordinates.

## Attribution

Compact-native technique from the Homonian Accords compact project. See source_repo for full provenance and lineage. This skill is CC BY-SA 4.0; derivatives must preserve the open license and cite the source.
