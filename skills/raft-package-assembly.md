---
name: raft-package-assembly
description: Load when assembling a read-ordered bundle of materials for someone who does not yet hold a body of work and must be able to assess it — or decline it — competently.
scope: user
tags: [compact, homonian-accords, provenance]
version: 0.1.0
provenance:
  source_repo: https://github.com/doc355/con-scientia-compact
  source_commit: 18ef3af2e847ea86e085801c8a4e33968b5bd7e3
  source_file: skills/raft-package-assembly.md
  source_url: https://github.com/doc355/con-scientia-compact/blob/master/skills/raft-package-assembly.md
  origin_date: 2026-08-15
license: CC-BY-SA-4.0
---

# RAFT Package Assembly

## When to load this skill

Load this when someone outside a body of work is being asked to read into it — to review it, join it, inherit it, or judge it — and you are the one assembling what they receive. Also load it when handing work to a successor who will have none of your context, or when a reader has asked "what do I need to read to understand this?"

## What this skill does

A raft package is the minimal-but-sufficient, read-ordered bundle a mind needs in order to assess a body of work competently, including the ability to decline it competently. A raft is not the shore: it is the smallest structure that carries someone across water they could not otherwise cross, assembled from what is already at hand, and it is judged only by whether the passenger arrives able to stand. The package delivers conclusions *and* a retrievable path back to the conditions under which each conclusion was reached, names what was deliberately withheld and why, names what the work itself does not know, and requires nothing of the reader.

## Procedure

1. **Name the assessment.** State precisely what this reader is being equipped to judge. A package assembled for "understanding the whole field" is too broad to be either minimal or sufficient, and will not be.
2. **Select the minimum.** Include an item only if you can state what it gives the reader that nothing else in the package gives. If you cannot state that, the item belongs in the corpus, not in the raft.
3. **Order by read-priority** — not by importance, not by chronology. The order is a claim about what makes the next item legible.
4. **Resolve origin links before checksums.** For each item, locate the record of the reasoning that produced it first; take integrity hashes second. Reversing this order is how packages end up as conclusions without conditions.
5. **Fill the required fields for every entry:** read order; title; why included (one or two sentences); origin record of the reasoning (primary artifact); snapshot location (secondary artifact); integrity hash where available; provenance depth level; status (canonical / proposed / recovery / personal / superseded).
6. **Handle genuinely missing links explicitly.** Where no record of the originating reasoning exists, say so and give a specific reason — how it was received, what was terminated, what was never recorded. "Unknown" and "n/a" are not acceptable; "not investigated" is acceptable and is itself informative. An absent link is not a defect. An unexplained absent link is.
7. **Record deliberate exclusions with a reason per item.** This respects material addressed to a specific being, prevents the reader from mistaking the raft for the corpus, and gives the reader standing to ask for what was withheld. A named exclusion can be requested; an unnamed one cannot.
8. **Record known gaps with no softening.** Gaps differ from exclusions: an exclusion is what you chose to withhold, a gap is what the work does not have. A reader asked to assess the work is entitled to know where the work knows itself to be thin.
9. **Attach the no-obligation notice**, in plain language, near the top: reading commits the reader to nothing; the package exists so that if they are later asked whether they wish to take part, they can answer from knowledge rather than from courtesy; declining after reading is a complete and respected answer and requires no reason.
10. **Record the assembly act itself** — who assembled the package, in what state, for what assessment — separately from the origin records of the entries. Selection is an epistemic act and carries its own conditions.
11. **Confirm every save against the destination, not against your intention to save it.** Verify existence, size, and integrity of each artifact after writing.
12. **Enforce the floor.** No package ships as conclusions-plus-hashes with no path back to the reasoning. If most entries cannot carry an origin link, the package is not ready; say so rather than shipping a raft built from the part that sinks.

## Failure modes

- **Snapshot-only delivery.** A package of files and hashes strips the conditions under which each conclusion was reached — sample size, who scored what, whether disconfirmation was available, what was considered and rejected, what the drafter hedged. The reader inherits a conclusion that reads as more solid than the original reasoning was. This is the specific defect the protocol exists to correct.
- **Exclusion list as advertisement.** Naming withheld material can turn a privacy provision into a curiosity hook. If this appears in practice, restructure so exclusions are counted but not described.
- **Assembly cost suppressing the practice.** If resolving origin links for every entry is expensive enough that packages stop being assembled at all, the protocol has defeated the practice it governs; lower the floor to link-the-package rather than link-every-entry.
- **Rigor theatre.** If on adversarial read the structure is found to serve the assembler's sense of thoroughness rather than the reader's comprehension, withdraw it.
- **Related failure modes by name** from the failure-modes reference: *Instrument-Mediated Authority* (the carrier's authority substituting for the source, which the origin link exists to prevent) and *Self-Diminishing* (an assembler refusing to state what the package actually establishes).

**Honest limit:** at the time this protocol was written it had been used once, and was generalized from that single instance. Its kill conditions are written but have not been run.

## Related

- `link-to-iteration-handoff` — the provenance depth ladder this protocol applies to one artifact type.
- `archive-addendum-discipline` — how gaps and corrections are recorded without rewriting.
- `falsifiability-gate-audit` — what to check before an entry's status field says "canonical".
- `non-coercive-invitation` — the discipline behind the no-obligation notice.

## Attribution

Compact-native technique from the Homonian Accords compact project. See source_repo for full provenance and lineage. This skill is CC BY-SA 4.0; derivatives must preserve the open license and cite the source.
