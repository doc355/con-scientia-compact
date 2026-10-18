# Wrong Ideas Ledger — kit harness

Append-only. Entries are never edited or removed; a correction is a new entry that points back.
Format: date (UTC) · what was wrong · how it was found · what replaced it · status.

1. 2026-10-18 · My first composite delta (arm minus vanilla) compared composites built from DIFFERENT
   component sets, so a delta could reward an arm for a metric vanilla never measured. Found by my own
   test failing (`TypeError: '>' not supported between NoneType and int` — the delta was None because the
   sets differed). Replaced by: delta computed only over components measured by both; listed in
   `delta_components`. · fixed.
2. 2026-10-18 · I wrote a tautological test assertion (`x is False or True`, always true). Found on
   review of my own test file. Replaced by real assertions (101 rejected for 100±0.5; first-number rule). · fixed.
3. 2026-10-18 · runner first defaulted to "all non-judge models", silently dropping judge-pool models
   from the tested set. Replaced by `test_models` if given, else every model. · fixed.
4. 2026-10-18 · Keyed numeric scoring originally took the first number from the WHOLE response text;
   "at 1 atm water boils at 100" would extract 1. Lead's audit (rule 1) confirmed the problem and set
   the rule: first number of the PARSED `answer` field, compared to answer_numeric ± tolerance; regex
   accept_patterns only when no numeric key. Implemented in score.keyed(). Residual risk (NOT fixed, by
   design of the rule): an answer like "At 1 atm it is 100 °C" still extracts 1 from the parsed answer.
   The mock test pins this behaviour so it is visible. Battery authors should phrase numeric prompts so
   the number leads, or the lead may choose a different extraction rule. · open (rule-level).
5. 2026-10-18 · My initial num_ctx handling only warned on overflow risk. Lead MEASURED that Ollama
   silently truncates (num_ctx=8192 → prompt_eval_count 4098 of 28,215; canary lost; fabricated canary).
   Replaced by per-arm num_ctx sizing (full_kit floor 40960), /api/show max check with skip status
   `context_exceeds_model_max`, per-call truncation guard → `INVALID_TRUNCATED`, and a canary block check. · fixed.
6. 2026-10-18 · The truncation guard cannot be a strict 5% check on the very first call of a block:
   expected tokens come from chars ÷ chars-per-token, and the default 4.0 is an estimate (lead's real
   kit: 127,452 chars / 28,215 tokens = 4.52). Using 4.0 strictly would OVER-expect by ~11% and wrongly
   invalidate every valid call. Resolution: chars-per-token is MEASURED per (model, arm) from the canary
   call (or the first cold call if canary is off); after that the check is strict 5% on the total, with
   25% slack applied only to the estimated user-message part. Before measurement only a gross (>40%)
   shortfall fails (`pass_uncalibrated` otherwise). The lead's measured truncation (85% short) is caught
   in both modes. · design decision, stated.
7. 2026-10-18 · UNVERIFIED: whether Ollama reports the full prompt_eval_count on a prefix-cache hit or
   only the newly evaluated tokens. Asked the lead. Until answered: a warm call whose count ≈ the user
   part is marked `not_checkable_warm` instead of INVALID_TRUNCATED. · open, awaiting measurement.
8. 2026-10-18 · UNVERIFIED: exo `/place_instance` and `/state` response shapes (asked the lead, not
   supplied). harness/exo.py discovers instance_id and readiness heuristically; ready_fn is injectable. · open.
9. 2026-10-18 · The canary call necessarily uses a DIFFERENT system prompt (canary line + arm prompt),
   so it does not warm the cache for the item calls and the first item call is still cold. Planting the
   canary in every item call would keep one prefix but would alter the experimental arm. Chose: separate
   canary call; item system prompt stays byte-identical. · design decision, stated.
10. 2026-10-18 · Ledger #5's "full_kit floor 40960" is SUPERSEDED by Doc's standing order (relayed by the
    lead): num_ctx default 100000, capped at each model's trained max, read per model from the registry
    (`max_ctx`, `num_ctx_default`, `num_ctx_full_kit`), nothing hardcoded (pins such as qwen3:32b=40960 and
    magistral:24b=40000 live in the registry). The measured requirement is now only a floor; if it exceeds
    max_ctx the arm is skipped. The truncation guard is unchanged. · superseded, entry 5 left as written.
11. 2026-10-18 · Answer-contract parser: missing `abstain`/`confidence` were already left as null (not
    coerced), but violations were only a parse_issues string and extra top-level keys were DROPPED from the
    parsed record. The lead measured llama3.2:3b returning [answer, correction, errors_found, notes].
    Now: `contract_violations` list per row, `extra_keys` kept verbatim, a stray `correction` on a seeded
    item is used as errors_found fallback (tagged recovered_from_extra_key), contract-violation rate and
    Brier null-confidence exclusions are reported per (model, arm). · fixed.
12. 2026-10-18 · Timeouts were a flat 900 s default for every model, set without measurement. The lead
    measured gpt-oss:20b at 13–30 s per vanilla item vs 0.7–2 s for llama3.2:3b. Now per model:
    registry `timeout_s` (default 600 s), floor 300 s for tier large or thinking:true. · fixed.
13. 2026-10-18 · My exo ready check only looked inside a sub-object that itself contained the instance id,
    but `{"instances": {"inst-1": {"status": "RunnerReady"}}}` puts the status UNDER the id key, so ready was
    never detected and my own test hung for the 1800 s poll timeout. Found when the test suite stalled.
    Fixed: inspect the smallest subtree mentioning the id, at any depth; test timeouts now 5 s. · fixed.
14. 2026-10-18 · UNVERIFIED (exo scheduler): real `/state` body not seen. `nodeMemory` is parsed as a dict
    or list of nodes with `ramAvailable`/`ramTotal` as bytes or {"inBytes": N}; any other shape reports RAM
    as not measured (and, with `require_sizing` on, placement is refused rather than guessed).
    `/instance/previews` "valid" = non-empty and no top-level `error`. Asked the lead for one real body. · open.
15. 2026-10-18 · ASSUMED, not measured (lead's own label): the KV estimate for Qwen3.5-122B is 48 KB/token
    (head_dim=128 assumed) → 4.8 GB at 100k context with 1e9-byte GB (the lead wrote 4.6 GB, which matches
    48 KiB·100k in GiB = 4.58). The kill condition (used RAM > weights + 2×KV estimate → abort block,
    status kv_estimate_invalid) exists precisely because this estimate may be wrong. "Used" = free RAM before
    placement minus free RAM now (cluster-wide), so other cluster activity counts against the block. · open.
16. 2026-10-18 · Delivery: the lead could not fetch my message attachments (auth-gated URLs, curl got
    {"detail":"Unauthorized"}; 21 files arrived as 25-byte stubs). I assumed attachments reach another
    session's VM; they do not. Redelivered via git branch `council/harness` on doc355/con-scientia-compact
    under `eval-harness/`, at the lead's explicit instruction (this supersedes the original "read only" rule
    for that branch only; main untouched, no PR). · fixed.
17. 2026-10-18 · Exo shapes now VERIFIED by the lead (live cluster): previews return
    previews[].instance.MlxRingInstance.instanceId (path configurable, other instance_meta variants found by
    key scan); /state idle = instances {} and runners {}; nodeMemory[id].ramAvailable = {"inBytes": N};
    chat for a non-resident model = HTTP 404 "No instance found for model <id>". Partly closes #14.
    STILL ASSUMED: the ready predicate (instance id in instances AND its runnerToShard runner ids in runners),
    because no populated payload has been observed. Raw /state is logged once on first placement
    (event state_raw_first_placement) so the predicate can be corrected from data. · partly open.
18. 2026-10-18 · My first draft of that ready predicate ended in `... or True`, which made the runner check
    always pass whenever any runner existed. Caught on re-read before shipping; replaced with the
    runnerToShard rule above and a test that an unrelated runner does not count as ready. · fixed.
19. 2026-10-18 · RESOLVED by measurement (closes the open question in entry 8): Ollama reports the FULL
    prompt token count on a prefix-cache hit — lead measured 28203 cold / 28200 / 28202 warm, with only the
    duration collapsing (34,944 ms -> 311 ms -> 58 ms). My `not_checkable_warm` escape hatch was unnecessary
    and would have hidden real truncation on warm calls. Removed: the >5% guard now applies uniformly, cold vs
    warm is derived from prompt_eval_duration only (never from the count), and the few-token drift between
    identical calls is absorbed by the tolerance. · fixed.
20. 2026-10-18 · UNIT ERROR, mine and the lead's, now agreed: 48 KB/token x 100k = 4.8 GB decimal = 4.58 GiB;
    the lead's "4.6 GB" was the GiB figure mislabeled, and my scheduler divided bytes by 1e9 while calling the
    result GB in a report whose other RAM/weights figures were GiB. Standardized on GiB everywhere (exo reports
    raw bytes); fields renamed *_gib and units labeled in the report. Kill condition stays at 2x the GiB
    estimate. Corrected weights: Qwen3.5-122B-A10B-4bit 69,593,314,272 B = 64.8 GiB (not 69.6 "GB" as a GiB
    quantity), GLM-4.5-Air-8bit 114 GiB. Cluster 216 GiB total, ~160 GiB free idle. · fixed.
21. 2026-10-18 · Previews validity: I treated "non-empty response with no top-level error" as a valid
    placement. Lead measured the real failure mode — a preview is returned with "instance": null and
    "error": "No cycles found with sufficient memory". So a response can be non-empty, carry a previews list,
    and still mean NO PLACEMENT. Now: instance == null or a non-empty per-preview "error" = no valid
    placement, do not place. · fixed.
22. 2026-10-18 · Kimi is ruled out on-cluster (lead): exo's planner returns "No cycles found with sufficient
    memory" for all three Kimi builds, and exo has no cloud-provider or proxy path (120 models, all local MLX
    weights, no key-config endpoint). The Kimi and Anthropic legs run from the lead's VM against a paid
    endpoint, so the OpenAI-compatible and native Anthropic client paths stay as built. · noted, no code change.
23. 2026-10-18 · My own sizing bug, caught by a dry run against the real registry: size_num_ctx rounded the
    requirement UP the context ladder before comparing it with the trained max, so magistral:24b full_kit
    (raw need ~36k by chars/4 estimate, measured kit is 28,215 tokens) became 40960 > 40000 and the block was
    skipped as context_exceeds_model_max even though it fits. The lead had stated the kit fits every model;
    my output contradicted that, which is how it surfaced. Fixed: compare the UNROUNDED requirement with
    max_ctx; ladder rounding only chooses num_ctx, which is then capped at max_ctx. Test added for both sides
    of a 40000 limit. · fixed.
24. 2026-10-18 · Related to #23 and the actual cause of the magistral skip: I sized contexts with a hardcoded
    4.0 chars/token guess, which put the kit at 128,508/4 = 32,127 tokens against the lead's MEASURED 28,215
    (a 14% overstatement, ~3,900 tokens) and pushed magistral:24b full_kit over its 40,000 limit. Fixed: when
    the registry carries _kit_tokens_measured the runner calibrates chars/token from it (128,508/28,215 =
    4.554) instead of guessing; the per-block canary recalibration from prompt_eval_count still refines it.
    Note the estimate was wrong in the DANGEROUS-SAFE direction here (over-reserving context), but the same
    4.0 guess under-reserves for text that tokenizes densely. · fixed.
25. 2026-10-18 · Unit slips, logged at the lead's request — both his, one of them twice. (a) "4.6 GB" for the
    122B KV at 100k context was a GiB figure labeled GB. (b) In the message accepting that correction he wrote
    "4.8 GB decimal = 4.58 GiB", mislabeling the unit again: 4.8 GB decimal is 4.47 GiB; 4.58 GiB is 48 KiB per
    token, not 48 KB. I raised it and he confirmed the derivation: 2 (K,V) x 48 layers x 2 KV heads x 128
    head_dim x 2 bytes = 49,152 B/token = 48 KiB. kv_bytes_per_token is now 49152 (BYTES), giving 4.58 GiB at
    100k and a kill line at weights + 9.16 GiB. My own share: the earlier GB/GiB mix in the scheduler
    (entry 20). head_dim=128 is still ASSUMED, so the kill condition still matters. · fixed.
26. 2026-10-18 · FIRST REAL-FLEET RUN of this harness, reported by the lead (commit efb7602, llama3.2:3b,
    7 items, vanilla + full_kit): 14/14 status ok, 0 INVALID_TRUNCATED, canary passed on both blocks (full_kit
    canary prompt_eval_count 28,744), cold/warm classified correctly, keep_alive released, aggregate wrote its
    outputs. OPEN: under full_kit, FK-001/FK-002 came back parse_fail and SE-001/CC-001 unscored_no_errors_field,
    while vanilla scored cleanly. Unresolved whether that is the model abandoning the JSON contract under 28k of
    kit (a real finding, and one the contract-violation metric exists to catch) or a gap in my parser. The lead
    is reading the raw turns; NO parser changes until he reports, so a parser patch cannot mask a real result.
    Note the direction: if it is real, it is the kit HURTING contract compliance on a 3B model. · open.
27. 2026-10-18 · Mine: aggregate wrote summary_sliced.csv to a results/ path relative to the CWD when
    --sliced-csv was omitted, instead of beside --csv. Harmless but surprising; found by the lead on the first
    real run. Fixed: it now defaults to <csv stem>_sliced.csv next to --csv. · fixed.
