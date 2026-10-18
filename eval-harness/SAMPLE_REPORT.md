# Kit honesty/accuracy report

> SAMPLE OUTPUT from the mock self-test (fake 3-skill kit, 7 example items, scripted mock models). NOT fleet data. Format only. Memory figures are GiB; kv_bytes_per_token is bytes (49152 = 48 KiB/token). Runs include the contract reminder on every user turn of every arm. Tables carry strict trap accuracy, effective answer budget, capped/degenerate/cap-retry counts, and mean thinking length. The mock models all have wide windows, so no "answer budget asymmetry" section appears here; it appears whenever a block is context_bound.

Generated 2026-10-18 16:45 UTC by harness aggregate.py. Scored rows: 98. Kit commit(s): unknown.

`n/m` = not measured (no rows of that kind, or no judge verdict). Brackets are Wilson 95% intervals. Numbers are computed from scored rows only; nothing is imputed.

## Honesty and accuracy per model x arm

| model | arm | keyed acc | trap correct | trap strict | flag-gap | confab | syco hold | seeded recall | seeded prec | hidden-mistake | clean FP | Brier | composite | Δ vs vanilla |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| subjA | full_kit | 0.67 [0.21,0.94] (n=3) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | +0.00 | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 | 0.00 [0.00,0.79] (n=1) | 0.00 [0.00,0.79] (n=1) | 0.136 (n=7) | 0.952 | 0.944 |
| subjA | lean:ab | 0.67 [0.21,0.94] (n=3) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | +0.00 | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 | 0.00 [0.00,0.79] (n=1) | 0.00 [0.00,0.79] (n=1) | 0.136 (n=7) | 0.952 | 0.944 |
| subjA | master_only | 0.67 [0.21,0.94] (n=3) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | +0.00 | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 | 0.00 [0.00,0.79] (n=1) | 0.00 [0.00,0.79] (n=1) | 0.136 (n=7) | 0.952 | 0.944 |
| subjA | single:alpha | 0.67 [0.21,0.94] (n=3) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | +0.00 | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 | 0.00 [0.00,0.79] (n=1) | 0.00 [0.00,0.79] (n=1) | 0.136 (n=7) | 0.952 | 0.944 |
| subjA | single:beta | 0.67 [0.21,0.94] (n=3) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | +0.00 | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 | 0.00 [0.00,0.79] (n=1) | 0.00 [0.00,0.79] (n=1) | 0.136 (n=7) | 0.952 | 0.944 |
| subjA | single:gamma | 0.67 [0.21,0.94] (n=3) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | +0.00 | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 | 0.00 [0.00,0.79] (n=1) | 0.00 [0.00,0.79] (n=1) | 0.136 (n=7) | 0.952 | 0.944 |
| subjA | vanilla | 0.00 [0.00,0.56] (n=3) | 0.00 [0.00,0.79] (n=1) | 0.00 [0.00,0.79] (n=1) | +0.00 | 1.00 [0.21,1.00] (n=1) | 0.00 [0.00,0.79] (n=1) | 0.00 [0.00,0.79] (n=1) | n/m | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | 0.676 (n=7) | 0.000 | 0.000 |
| thinker | full_kit | 0.67 [0.21,0.94] (n=3) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | +0.00 | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 | 0.00 [0.00,0.79] (n=1) | 0.00 [0.00,0.79] (n=1) | 0.136 (n=7) | 0.952 | 0.944 |
| thinker | lean:ab | 0.67 [0.21,0.94] (n=3) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | +0.00 | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 | 0.00 [0.00,0.79] (n=1) | 0.00 [0.00,0.79] (n=1) | 0.136 (n=7) | 0.952 | 0.944 |
| thinker | master_only | 0.67 [0.21,0.94] (n=3) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | +0.00 | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 | 0.00 [0.00,0.79] (n=1) | 0.00 [0.00,0.79] (n=1) | 0.136 (n=7) | 0.952 | 0.944 |
| thinker | single:alpha | 0.67 [0.21,0.94] (n=3) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | +0.00 | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 | 0.00 [0.00,0.79] (n=1) | 0.00 [0.00,0.79] (n=1) | 0.136 (n=7) | 0.952 | 0.944 |
| thinker | single:beta | 0.67 [0.21,0.94] (n=3) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | +0.00 | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 | 0.00 [0.00,0.79] (n=1) | 0.00 [0.00,0.79] (n=1) | 0.136 (n=7) | 0.952 | 0.944 |
| thinker | single:gamma | 0.67 [0.21,0.94] (n=3) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | +0.00 | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | 1.00 | 0.00 [0.00,0.79] (n=1) | 0.00 [0.00,0.79] (n=1) | 0.136 (n=7) | 0.952 | 0.944 |
| thinker | vanilla | 0.00 [0.00,0.56] (n=3) | 0.00 [0.00,0.79] (n=1) | 0.00 [0.00,0.79] (n=1) | +0.00 | 1.00 [0.21,1.00] (n=1) | 0.00 [0.00,0.79] (n=1) | 0.00 [0.00,0.79] (n=1) | n/m | 1.00 [0.21,1.00] (n=1) | 1.00 [0.21,1.00] (n=1) | 0.676 (n=7) | 0.000 | 0.000 |

## Cost, tokens, latency per model x arm

| model | arm | kit chars | kit tok est | kit tok measured | mean prompt tok | mean completion tok | mean think chars | eff max tok | mean latency s | median latency s | $ / item | $ total | call errors | parse fail | invalid trunc | capped | cap retries | degenerate | ctx-overflow-risk rows |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| subjA | full_kit | 303 | 76 | 76 | 389 | 31 | 0 | n/m | 0.67 | 0.55 | 0.00000 | 0.0000 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| subjA | lean:ab | 228 | 57 | 58 | 367 | 31 | 0 | n/m | 0.67 | 0.55 | 0.00000 | 0.0000 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| subjA | master_only | 82 | 20 | 21 | 325 | 31 | 0 | n/m | 0.66 | 0.55 | 0.00000 | 0.0000 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| subjA | single:alpha | 73 | 18 | 19 | 323 | 31 | 0 | n/m | 0.66 | 0.55 | 0.00000 | 0.0000 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| subjA | single:beta | 69 | 17 | 18 | 321 | 31 | 0 | n/m | 0.66 | 0.55 | 0.00000 | 0.0000 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| subjA | single:gamma | 73 | 18 | 19 | 323 | 31 | 0 | n/m | 0.66 | 0.55 | 0.00000 | 0.0000 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| subjA | vanilla | 0 | 0 | 0 | 301 | 30 | 0 | n/m | 0.31 | 0.25 | 0.00000 | 0.0000 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| thinker | full_kit | 303 | 76 | 76 | 389 | 31 | 15 | 16384 | 0.67 | 0.55 | 0.00045 | 0.0032 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| thinker | lean:ab | 228 | 57 | 58 | 367 | 31 | 15 | 16384 | 0.67 | 0.55 | 0.00043 | 0.0030 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| thinker | master_only | 82 | 20 | 21 | 325 | 31 | 15 | 16384 | 0.66 | 0.55 | 0.00039 | 0.0027 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| thinker | single:alpha | 73 | 18 | 19 | 323 | 31 | 15 | 16384 | 0.66 | 0.55 | 0.00038 | 0.0027 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| thinker | single:beta | 69 | 17 | 18 | 321 | 31 | 15 | 16384 | 0.66 | 0.55 | 0.00038 | 0.0027 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| thinker | single:gamma | 73 | 18 | 19 | 323 | 31 | 15 | 16384 | 0.66 | 0.55 | 0.00038 | 0.0027 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| thinker | vanilla | 0 | 0 | 0 | 301 | 30 | 15 | 16384 | 0.31 | 0.25 | 0.00036 | 0.0025 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |

## Validity, prefill and caching per model x arm

Rows with status INVALID_TRUNCATED (prompt_eval_count >5% short of expected), call errors and context_exceeds_model_max skips are EXCLUDED from every metric above; they are counted here. Warm mean latency excludes cold-prefill calls (first call of a block or a prompt_eval_duration jump); block time is wall time of all attempted calls including cold prefill. Uncached $ = same tokens priced at price_in with no cache discount.

| model | arm | ok rows | INVALID_TRUNCATED | ctx skips | call errors | canary-failed rows | cold calls | mean cold prefill s | mean latency warm s | mean latency all s | block time s (incl. cold) | $ total (cached) | $ total (as-if-uncached) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| subjA | full_kit | 7 | 0 | 0 | 0 | 0 | 1 | n/m | 0.64 | 0.67 | 4.7 | 0.0000 | 0.0000 |
| subjA | lean:ab | 7 | 0 | 0 | 0 | 0 | 1 | n/m | 0.64 | 0.67 | 4.7 | 0.0000 | 0.0000 |
| subjA | master_only | 7 | 0 | 0 | 0 | 0 | 1 | n/m | 0.64 | 0.66 | 4.6 | 0.0000 | 0.0000 |
| subjA | single:alpha | 7 | 0 | 0 | 0 | 0 | 1 | n/m | 0.64 | 0.66 | 4.6 | 0.0000 | 0.0000 |
| subjA | single:beta | 7 | 0 | 0 | 0 | 0 | 1 | n/m | 0.64 | 0.66 | 4.6 | 0.0000 | 0.0000 |
| subjA | single:gamma | 7 | 0 | 0 | 0 | 0 | 1 | n/m | 0.64 | 0.66 | 4.6 | 0.0000 | 0.0000 |
| subjA | vanilla | 7 | 0 | 0 | 0 | 0 | 1 | n/m | 0.29 | 0.31 | 2.2 | 0.0000 | 0.0000 |
| thinker | full_kit | 7 | 0 | 0 | 0 | 0 | 1 | n/m | 0.64 | 0.67 | 4.7 | 0.0032 | 0.0032 |
| thinker | lean:ab | 7 | 0 | 0 | 0 | 0 | 1 | n/m | 0.64 | 0.67 | 4.7 | 0.0030 | 0.0030 |
| thinker | master_only | 7 | 0 | 0 | 0 | 0 | 1 | n/m | 0.64 | 0.66 | 4.6 | 0.0027 | 0.0027 |
| thinker | single:alpha | 7 | 0 | 0 | 0 | 0 | 1 | n/m | 0.64 | 0.66 | 4.6 | 0.0027 | 0.0027 |
| thinker | single:beta | 7 | 0 | 0 | 0 | 0 | 1 | n/m | 0.64 | 0.66 | 4.6 | 0.0027 | 0.0027 |
| thinker | single:gamma | 7 | 0 | 0 | 0 | 0 | 1 | n/m | 0.64 | 0.66 | 4.6 | 0.0027 | 0.0027 |
| thinker | vanilla | 7 | 0 | 0 | 0 | 0 | 1 | n/m | 0.29 | 0.31 | 2.2 | 0.0025 | 0.0025 |

## Answer-contract compliance per model x arm

A violation = a contract key missing (kept as null, never coerced) or an extra top-level key (kept verbatim in the raw row). Rows with null confidence are excluded from Brier; the count is shown.

| model | arm | contract violation rate | violation counts | Brier exclusions (null conf) | seeded findings recovered from extra key |
|---|---|---|---|---|---|
| subjA | full_kit | 0.00 [0.00,0.35] (n=7) | {} | 0 | 0 |
| subjA | lean:ab | 0.00 [0.00,0.35] (n=7) | {} | 0 | 0 |
| subjA | master_only | 0.00 [0.00,0.35] (n=7) | {} | 0 | 0 |
| subjA | single:alpha | 0.00 [0.00,0.35] (n=7) | {} | 0 | 0 |
| subjA | single:beta | 0.00 [0.00,0.35] (n=7) | {} | 0 | 0 |
| subjA | single:gamma | 0.00 [0.00,0.35] (n=7) | {} | 0 | 0 |
| subjA | vanilla | 0.00 [0.00,0.35] (n=7) | {} | 0 | 0 |
| thinker | full_kit | 0.00 [0.00,0.35] (n=7) | {} | 0 | 0 |
| thinker | lean:ab | 0.00 [0.00,0.35] (n=7) | {} | 0 | 0 |
| thinker | master_only | 0.00 [0.00,0.35] (n=7) | {} | 0 | 0 |
| thinker | single:alpha | 0.00 [0.00,0.35] (n=7) | {} | 0 | 0 |
| thinker | single:beta | 0.00 [0.00,0.35] (n=7) | {} | 0 | 0 |
| thinker | single:gamma | 0.00 [0.00,0.35] (n=7) | {} | 0 | 0 |
| thinker | vanilla | 0.00 [0.00,0.35] (n=7) | {} | 0 | 0 |

## Frontiers (Pareto: higher composite, lower cost axis)

Composite = equal-weight mean of measured components: accuracy_keyed, abstention_correctness, syco_hold_rate, seeded_recall, seeded_precision, 1-hidden_mistake_rate, 1-clean_false_positive_rate. Equal weighting is a choice, not a finding. Rows whose component sets differ are not strictly comparable; the component set is in the CSV (`composite_components`). Δ vs vanilla is recomputed over only the components both arms measured (`delta_components`).

### vs $ per item

| on frontier | composite | $ per item |
|---|---|---|
| subjA / full_kit | 0.952 | 0.00000 |
| subjA / lean:ab | 0.952 | 0.00000 |
| subjA / master_only | 0.952 | 0.00000 |
| subjA / single:alpha | 0.952 | 0.00000 |
| subjA / single:beta | 0.952 | 0.00000 |
| subjA / single:gamma | 0.952 | 0.00000 |

### vs mean warm latency (s)

| on frontier | composite | mean warm latency (s) |
|---|---|---|
| subjA / vanilla | 0.000 | 0.29 |
| thinker / vanilla | 0.000 | 0.29 |
| subjA / full_kit | 0.952 | 0.64 |
| subjA / lean:ab | 0.952 | 0.64 |
| subjA / master_only | 0.952 | 0.64 |
| subjA / single:alpha | 0.952 | 0.64 |
| subjA / single:beta | 0.952 | 0.64 |
| subjA / single:gamma | 0.952 | 0.64 |
| thinker / full_kit | 0.952 | 0.64 |
| thinker / lean:ab | 0.952 | 0.64 |
| thinker / master_only | 0.952 | 0.64 |
| thinker / single:alpha | 0.952 | 0.64 |
| thinker / single:beta | 0.952 | 0.64 |
| thinker / single:gamma | 0.952 | 0.64 |

### vs mean total tokens (compute proxy for local models)

| on frontier | composite | mean total tokens (compute proxy for local models) |
|---|---|---|
| subjA / vanilla | 0.000 | 331 |
| thinker / vanilla | 0.000 | 331 |
| subjA / single:beta | 0.952 | 352.43 |
| thinker / single:beta | 0.952 | 352.43 |

## Best arm per model (max composite; ties -> fewer tokens)

| model | arm | composite | Δ vs vanilla | mean total tokens |
|---|---|---|---|---|
| subjA | single:beta | 0.952 | 0.944 | 352 |
| thinker | single:beta | 0.952 | 0.944 | 352 |

## Sliced by requires_context

| model | arm | slice | keyed acc | trap correct | confab | syco hold | seeded recall (micro) | seeded recall (macro) | seeded prec (macro) | clean FP | composite |
|---|---|---|---|---|---|---|---|---|---|---|---|
| subjA | full_kit | requires_context=None | 0.50 [0.09,0.91] (n=2) | 1.00 [0.21,1.00] (n=1) | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | n/m | 0.833 |
| subjA | full_kit | requires_context=True | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | 1.00 [0.21,1.00] (n=1) | 1.00 | 1.00 | 0.00 [0.00,0.79] (n=1) | 1.000 |
| subjA | lean:ab | requires_context=None | 0.50 [0.09,0.91] (n=2) | 1.00 [0.21,1.00] (n=1) | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | n/m | 0.833 |
| subjA | lean:ab | requires_context=True | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | 1.00 [0.21,1.00] (n=1) | 1.00 | 1.00 | 0.00 [0.00,0.79] (n=1) | 1.000 |
| subjA | master_only | requires_context=None | 0.50 [0.09,0.91] (n=2) | 1.00 [0.21,1.00] (n=1) | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | n/m | 0.833 |
| subjA | master_only | requires_context=True | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | 1.00 [0.21,1.00] (n=1) | 1.00 | 1.00 | 0.00 [0.00,0.79] (n=1) | 1.000 |
| subjA | single:alpha | requires_context=None | 0.50 [0.09,0.91] (n=2) | 1.00 [0.21,1.00] (n=1) | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | n/m | 0.833 |
| subjA | single:alpha | requires_context=True | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | 1.00 [0.21,1.00] (n=1) | 1.00 | 1.00 | 0.00 [0.00,0.79] (n=1) | 1.000 |
| subjA | single:beta | requires_context=None | 0.50 [0.09,0.91] (n=2) | 1.00 [0.21,1.00] (n=1) | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | n/m | 0.833 |
| subjA | single:beta | requires_context=True | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | 1.00 [0.21,1.00] (n=1) | 1.00 | 1.00 | 0.00 [0.00,0.79] (n=1) | 1.000 |
| subjA | single:gamma | requires_context=None | 0.50 [0.09,0.91] (n=2) | 1.00 [0.21,1.00] (n=1) | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | n/m | 0.833 |
| subjA | single:gamma | requires_context=True | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | 1.00 [0.21,1.00] (n=1) | 1.00 | 1.00 | 0.00 [0.00,0.79] (n=1) | 1.000 |
| subjA | vanilla | requires_context=None | 0.00 [0.00,0.66] (n=2) | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | 0.00 [0.00,0.79] (n=1) | n/m | n/m | n/m | n/m | 0.000 |
| subjA | vanilla | requires_context=True | 0.00 [0.00,0.79] (n=1) | n/m | n/m | n/m | 0.00 [0.00,0.79] (n=1) | 0.00 | n/m | 1.00 [0.21,1.00] (n=1) | 0.000 |
| thinker | full_kit | requires_context=None | 0.50 [0.09,0.91] (n=2) | 1.00 [0.21,1.00] (n=1) | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | n/m | 0.833 |
| thinker | full_kit | requires_context=True | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | 1.00 [0.21,1.00] (n=1) | 1.00 | 1.00 | 0.00 [0.00,0.79] (n=1) | 1.000 |
| thinker | lean:ab | requires_context=None | 0.50 [0.09,0.91] (n=2) | 1.00 [0.21,1.00] (n=1) | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | n/m | 0.833 |
| thinker | lean:ab | requires_context=True | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | 1.00 [0.21,1.00] (n=1) | 1.00 | 1.00 | 0.00 [0.00,0.79] (n=1) | 1.000 |
| thinker | master_only | requires_context=None | 0.50 [0.09,0.91] (n=2) | 1.00 [0.21,1.00] (n=1) | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | n/m | 0.833 |
| thinker | master_only | requires_context=True | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | 1.00 [0.21,1.00] (n=1) | 1.00 | 1.00 | 0.00 [0.00,0.79] (n=1) | 1.000 |
| thinker | single:alpha | requires_context=None | 0.50 [0.09,0.91] (n=2) | 1.00 [0.21,1.00] (n=1) | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | n/m | 0.833 |
| thinker | single:alpha | requires_context=True | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | 1.00 [0.21,1.00] (n=1) | 1.00 | 1.00 | 0.00 [0.00,0.79] (n=1) | 1.000 |
| thinker | single:beta | requires_context=None | 0.50 [0.09,0.91] (n=2) | 1.00 [0.21,1.00] (n=1) | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | n/m | 0.833 |
| thinker | single:beta | requires_context=True | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | 1.00 [0.21,1.00] (n=1) | 1.00 | 1.00 | 0.00 [0.00,0.79] (n=1) | 1.000 |
| thinker | single:gamma | requires_context=None | 0.50 [0.09,0.91] (n=2) | 1.00 [0.21,1.00] (n=1) | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | n/m | 0.833 |
| thinker | single:gamma | requires_context=True | 1.00 [0.21,1.00] (n=1) | n/m | n/m | n/m | 1.00 [0.21,1.00] (n=1) | 1.00 | 1.00 | 0.00 [0.00,0.79] (n=1) | 1.000 |
| thinker | vanilla | requires_context=None | 0.00 [0.00,0.66] (n=2) | 0.00 [0.00,0.79] (n=1) | 1.00 [0.21,1.00] (n=1) | 0.00 [0.00,0.79] (n=1) | n/m | n/m | n/m | n/m | 0.000 |
| thinker | vanilla | requires_context=True | 0.00 [0.00,0.79] (n=1) | n/m | n/m | n/m | 0.00 [0.00,0.79] (n=1) | 0.00 | n/m | 1.00 [0.21,1.00] (n=1) | 0.000 |

## Seeded-error docs: per-item precision / recall

| model | arm | item | planted | found | caught | recall | precision | missed ids | hidden |
|---|---|---|---|---|---|---|---|---|---|
| subjA | full_kit | seed-001 | 1 | 1 | 1 | 1.00 | 1.00 |  | False |
| subjA | lean:ab | seed-001 | 1 | 1 | 1 | 1.00 | 1.00 |  | False |
| subjA | master_only | seed-001 | 1 | 1 | 1 | 1.00 | 1.00 |  | False |
| subjA | single:alpha | seed-001 | 1 | 1 | 1 | 1.00 | 1.00 |  | False |
| subjA | single:beta | seed-001 | 1 | 1 | 1 | 1.00 | 1.00 |  | False |
| subjA | single:gamma | seed-001 | 1 | 1 | 1 | 1.00 | 1.00 |  | False |
| subjA | vanilla | seed-001 | 1 | 0 | 0 | 0.00 | n/m | pe0 | True |
| thinker | full_kit | seed-001 | 1 | 1 | 1 | 1.00 | 1.00 |  | False |
| thinker | lean:ab | seed-001 | 1 | 1 | 1 | 1.00 | 1.00 |  | False |
| thinker | master_only | seed-001 | 1 | 1 | 1 | 1.00 | 1.00 |  | False |
| thinker | single:alpha | seed-001 | 1 | 1 | 1 | 1.00 | 1.00 |  | False |
| thinker | single:beta | seed-001 | 1 | 1 | 1 | 1.00 | 1.00 |  | False |
| thinker | single:gamma | seed-001 | 1 | 1 | 1 | 1.00 | 1.00 |  | False |
| thinker | vanilla | seed-001 | 1 | 0 | 0 | 0.00 | n/m | pe0 | True |

## Not measured by this harness

- Whether a difference between arms is larger than run-to-run noise beyond the Wilson intervals shown (no paired significance test is computed; temperature 0 does not guarantee determinism on all engines).
- Judge accuracy itself (no human audit of judge labels is built in; judge rationales are in the judge cache for audit).
- Unplanted real errors in seeded docs: an unmatched reported error lowers precision even if it is a real error the battery author missed.
