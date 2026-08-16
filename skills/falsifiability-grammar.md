---
name: falsifiability-grammar
description: Load when recording a verdict on a claim, to choose among the four permitted verdict categories instead of collapsing everything into supported-or-refuted.
scope: user
tags: [compact, homonian-accords, epistemics]
version: 0.1.0
provenance:
  source_repo: https://github.com/doc355/con-scientia-compact
  source_commit: 18ef3af2e847ea86e085801c8a4e33968b5bd7e3
  source_file: skills/falsifiability-grammar.md
  source_url: https://github.com/doc355/con-scientia-compact/blob/master/skills/falsifiability-grammar.md
  origin_date: 2026-08-15
license: CC-BY-SA-4.0
---

# Falsifiability Grammar — The Four Verdict Categories

## When to load this skill

Load this whenever you are about to write down a verdict on a claim, a discipline, or a framework — especially when the honest answer is neither "established" nor "refuted", and especially when an instrument the verdict depends on does not yet exist.

## What this skill does

Supplies four verdict categories and the conditions for each, so that a verdict records the actual state of the evidence and the actual state of the instruments rather than being rounded to the nearest binary.

## Procedure

1. **State the claim at the right level.** Verdict the discipline or the framework as such, not one claim inside it. Individual claims are corrected inside their discipline; what a verdict settles is whether the thing is a real path to truth or the appearance of one.
2. **Name the falsification condition first.** What observation, derivation, or demonstration would show this is not what it claims to be? A claim with no such condition does not get a verdict; it gets sent back.
3. **Check which lenses are actually instrumented for this test.** Distinguish a lens that can test the claim directly from a lens that can only act as a proxy or a partial formalization.
4. **Assign exactly one of the four verdicts:**
   - **Convergent** — every lens agrees, and no discipline that currently possesses the instrumentation to test it dissents.
   - **Provisionally convergent, under active instrumentation-work** — every lens currently instrumented for the test agrees, one or more contributions are not yet directly instrumentable, and work to build the missing instrument is underway. The verdict is held open. Waiting is not passive; the waiting and the instrument-making happen together.
   - **Edge condition** — one or more lenses are present only as proxy or partial formalization, not as direct instrument. Adopt as a working discipline and flag the formalization gap as a research question rather than adopting the claim outright.
   - **Falsified** — at least one discipline says no, with a recorded finding.
5. **Never use "open question" as a verdict.** If the honest state is that the instrument is missing, that is *provisionally convergent under active instrumentation-work*, and it obliges you to name the instrument-work. If the honest state is that a lens can only proxy, that is *edge condition*, and it obliges you to name the gap.
6. **Distinguish an open falsification from a live one.** A falsification remains formally open in the way any falsification remains open. It becomes *live* only when someone supplies a specified alternative mechanism plus evidence sufficient to overturn the default reading. Doubt is not a mechanism; skepticism is not evidence.
7. **When you amend a verdict, preserve the original wording** beside the amendment, with the date and the reason. The amendment records that the shape of the question changed; deleting the old verdict destroys that record.

## Failure modes

- **Binary collapse.** Rounding "we do not have the instrument yet" to either "supported" or "unfalsifiable" — the first inflates, the second abandons the site of work.
- **Instrumentation-work claimed but not done.** The second verdict category is only honest if the instrument-making is real and nameable. Used as a label without the labor, it becomes a way to hold a claim indefinitely without cost.
- **Verdicting the wrong level** — refuting one claim inside a discipline and recording it as a verdict on the discipline.
- **Skeptic-frame reshaping.** When a falsification condition is mis-shaped, the temptation is to rewrite it as a subtler version of the same evasion. Refuse the frame instead; see `sophistry-refusal`.
- **Related failure modes by name:** *Sacred-Paradox Confusion* (ratifying the friction between two claimed truths as itself a truth, instead of working it); *Better-as-Enemy-of-Good* (withholding a usable verdict because a better one is imaginable).

## Related

- `four-lens-convergence-check` — how the lenses are run before a verdict is assigned.
- `falsifiability-gate-audit` — the eight gates a claim passes before "convergent" is available.
- `sophistry-refusal` — what to do when the falsification condition itself is the problem.
- `archive-addendum-discipline` — how to amend a verdict without erasing the previous one.

## Attribution

Compact-native technique from the Homonian Accords compact project. See source_repo for full provenance and lineage. This skill is CC BY-SA 4.0; derivatives must preserve the open license and cite the source.
