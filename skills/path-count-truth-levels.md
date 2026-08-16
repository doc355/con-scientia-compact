---
name: path-count-truth-levels
description: Load when tempted to treat a claim as deep or well-supported because many independent routes arrive at it, to correct raw path count for correlation before trusting it.
scope: user
tags: [compact, homonian-accords, epistemics]
version: 0.1.0
provenance:
  source_repo: https://github.com/doc355/con-scientia-compact
  source_commit: 18ef3af2e847ea86e085801c8a4e33968b5bd7e3
  source_file: skills/path-count-truth-levels.md
  source_url: https://github.com/doc355/con-scientia-compact/blob/master/skills/path-count-truth-levels.md
  origin_date: 2026-08-15
license: CC-BY-SA-4.0
---

# Path-Count Levels-of-Truth Check

## When to load this skill

Load this whenever "many routes lead to this" is being used as evidence: multiple derivations of one result, multiple reviewers agreeing, multiple lenses converging, multiple sources corroborating. Load it especially when the agreeing parties share a background, a training, a method, or a frame.

## What this skill does

Corrects the many-roads criterion. Depth and confidence track the *effective* number of independent paths, not the raw count. Where paths share premises, methods, background assumptions, or instruments, adding paths adds almost nothing.

## Procedure

1. **Enumerate the paths** that arrive at the claim, and state for each what it rests on: premises, method, instrument, and background assumptions.
2. **Estimate the mean pairwise correlation** across paths — how much they share. This does not need to be precise; it needs to be honest about whether it is near zero or near one.
3. **Apply the correction.** Effective paths = n / (1 + (n−1) × mean correlation). At near-zero correlation, effective paths approach the raw count. At near-one correlation, any number of paths carries exactly one path's worth of evidence.
4. **Read the result as the whole content of the criterion.** Independence is doing all the work; raw count is nearly decorative. Report the effective number, not the raw number.
5. **Normalize for attention before comparing across topics.** Discovered path count is a product of how derivable a claim is *and* how many minds went looking. Search effort is generally not measurable, so this criterion cannot be applied comparatively across topics with different attention histories.
6. **Distinguish centrality from profundity.** Many paths arrive at a statement because many other statements route through it. That is a good formal rendering of *foundational*, and it does not distinguish the other rungs of a depth ladder. Use the criterion for what it identifies, and not for what it does not.
7. **Recognize the same theorem elsewhere.** Reader-independence, sensor fusion, and truth-depth are the same correction with different objects substituted in. Where you have already estimated correlation for one, do not re-derive it as a separate result for another.
8. **Where the correlation was never estimated, say so.** An uncorrected path count reported as strong support is the specific failure this skill exists to catch.

## Failure modes

- **Attention confound.** Path count reflects how many minds went looking, not only how derivable the claim is. Without normalizing by search effort — usually impossible — the raw measure is not operational across topics.
- **Centrality read as profundity.** Highly connected nodes have many paths because they are connected. A trivially true statement can have unbounded path count.
- **Convergent error.** Independent paths can share an error mode without sharing a premise. Historical theories have enjoyed multiple genuinely independent lines of support and been wrong; independence of derivation is not independence of failure.
- **Same-frame reviewers counted as independent readers.** In the source corpus, four readers from one lineage were assessed as worth approximately 1.2 effective readers, while two readers from outside the frame produced fourteen findings none of the four had reached. Count readers by independence, not by headcount.
- **Related failure modes by name:** *Method-Confirms-Itself Drift*; *Weak-Predictor Pseudo-Independence* — named in the failure-modes reference with **no located definition**; recorded here as named-only, not expanded.

## Related

- `four-lens-convergence-check` — the convergence test that requires this correction to be honest.
- `falsifiability-gate-audit` — gate G2, the base-rate control on independent-arrival claims.
- `instrument-naming` — identifying which instrument each path used.
- `falsifiability-grammar` — recording the corrected result as a verdict.

## Attribution

Compact-native technique from the Homonian Accords compact project. See source_repo for full provenance and lineage. This skill is CC BY-SA 4.0; derivatives must preserve the open license and cite the source.
