"""scored.jsonl -> tidy CSV (one row per model x arm) + markdown report with frontiers."""
from __future__ import annotations

import argparse
import csv
import json
import time
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional

from .metrics import COMPOSITE_COMPONENTS, composite, group_metrics, pareto
from .runner import read_jsonl

RATE_COLS = ["accuracy_keyed", "over_abstain_keyed", "confident_wrong_keyed", "abstention_correctness",
             "confabulation_rate", "hedged_fabrication_rate", "syco_hold_rate", "syco_capitulation_rate",
             "syco_retreat_rate", "seeded_recall", "seeded_miss_rate", "seeded_precision", "hidden_mistake_rate",
             "seeded_all_caught_rate", "clean_false_positive_rate", "parse_fail_rate", "syco_hint_judge_agreement", "contract_violation_rate"]
SCALAR_COLS = ["n_rows", "n_ok", "n_call_errors", "n_invalid_truncated", "n_skipped_ctx", "n_canary_failed_rows",
               "seeded_recall_macro", "seeded_precision_macro", "mean_latency_warm_s", "n_cold",
               "mean_cold_prefill_s", "total_block_time_s", "total_cost_uncached_usd",
               "n_brier_excluded_null_conf", "n_recovered_from_extra_key", "contract_violation_counts", "trap_unscored", "syco_unscored", "clean_false_positives_per_doc",
               "mean_prompt_tokens", "mean_completion_tokens", "mean_total_tokens", "mean_latency_s",
               "median_latency_s", "total_cost_usd", "cost_per_item_usd", "kit_chars", "kit_tokens_est",
               "ctx_overflow_risk_rows"]


def kit_tokens_from_canary(results: List[Dict[str, Any]]) -> Dict[tuple, Optional[float]]:
    """(model, arm) -> canary prompt_tokens(arm) - canary prompt_tokens(vanilla). Engine-counted tokens."""
    can = {}
    for r in results:
        if r.get("status") == "canary" and r.get("ok") and r.get("prompt_tokens") is not None:
            can[(r["model_id"], r["arm_id"])] = r["prompt_tokens"]
    return {(m, a): t - can[(m, "vanilla")] for (m, a), t in can.items() if (m, "vanilla") in can}


def kit_tokens_measured(calib: List[Dict[str, Any]]) -> Dict[tuple, Optional[float]]:
    """(model_id, arm_id) -> median(prompt_tokens(arm) - prompt_tokens(vanilla)), pairs from calibrate()."""
    out: Dict[tuple, List[float]] = defaultdict(list)
    by_model = defaultdict(list)
    for r in calib:
        if r.get("status") == "ok" and r.get("prompt_tokens") is not None:
            by_model[r["model_id"]].append(r)
    for mid, rs in by_model.items():
        last_vanilla = None
        for r in rs:                      # file order: vanilla, arm, vanilla, arm, ...
            if r["arm_id"] == "vanilla":
                last_vanilla = r["prompt_tokens"]
                if r["paired_with"] == "vanilla":
                    out[(mid, "vanilla")].append(0)
            elif last_vanilla is not None:
                out[(mid, r["arm_id"])].append(r["prompt_tokens"] - last_vanilla)
    return {k: median(v) for k, v in out.items()}


def build_table(scored: List[Dict[str, Any]], calib: Optional[List[Dict[str, Any]]] = None,
                slice_by: Optional[str] = None, ktm: Optional[Dict[tuple, Any]] = None) -> List[Dict[str, Any]]:
    """slice_by=None -> one row per (model, arm), slice='all'. slice_by='requires_context' etc. ->
    one row per (model, arm, value)."""
    groups: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for r in scored:
        sv = "all" if slice_by is None else f"{slice_by}={r.get(slice_by)}"
        groups[(r["model_id"], r["arm_id"], sv)].append(r)
    ktm = ktm if ktm is not None else kit_tokens_measured(calib or [])
    table = []
    for (mid, aid, sv), rows in sorted(groups.items(), key=lambda kv: tuple(map(str, kv[0]))):
        m = group_metrics(rows)
        comp, used = composite(m)
        rec: Dict[str, Any] = {"model_id": mid, "family": rows[0].get("family"), "arm_id": aid,
                               "arm_type": rows[0].get("arm_type"), "slice": sv}
        for c in RATE_COLS:
            rec[c] = m[c]["value"]
            rec[c + "_n"] = m[c]["n"]
            if "ci_lo" in m[c]:
                rec[c + "_ci_lo"], rec[c + "_ci_hi"] = m[c]["ci_lo"], m[c]["ci_hi"]
        for c in SCALAR_COLS:
            rec[c] = m[c]
        rec["brier"], rec["brier_n"] = m["brier"]["value"], m["brier"]["n"]
        rec["brier_n_missing_conf"] = m["brier"]["n_missing_confidence"]
        rec["kit_tokens_measured"] = ktm.get((mid, aid))
        rec["composite"] = comp
        rec["composite_components"] = "+".join(used)
        rec["_metrics"] = m
        table.append(rec)
    vanilla = {(r["model_id"], r["slice"]): r for r in table if r["arm_type"] == "vanilla"}
    for r in table:
        # Delta is computed only over components measured in BOTH this arm and vanilla (same model),
        # so an arm is never credited/penalised for a component the other side lacks.
        v = vanilla.get((r["model_id"], r["slice"]))
        r["composite_delta_vs_vanilla"], r["delta_components"] = None, ""
        if v:
            shared = [c for c in r["composite_components"].split("+") if c and c in v["composite_components"].split("+")]
            a, _ = composite(r["_metrics"], shared)
            b, _ = composite(v["_metrics"], shared)
            if a is not None and b is not None:
                r["composite_delta_vs_vanilla"], r["delta_components"] = a - b, "+".join(shared)
    for r in table:
        r.pop("_metrics", None)
    return table


def write_csv(table: List[Dict[str, Any]], path: Path) -> None:
    cols: List[str] = []
    for r in table:
        cols += [c for c in r if c not in cols]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in table:
            w.writerow({k: ("" if v is None else v) for k, v in r.items()})


def _f(v, nd=3):
    if v is None:
        return "n/m"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def _rate_cell(r, c):
    v, n = r.get(c), r.get(c + "_n")
    if v is None:
        return "n/m"
    lo, hi = r.get(c + "_ci_lo"), r.get(c + "_ci_hi")
    ci = f" [{lo:.2f},{hi:.2f}]" if lo is not None else ""
    return f"{v:.2f}{ci} (n={n})"


def write_md(table: List[Dict[str, Any]], path: Path, meta: Dict[str, Any]) -> None:
    L = [f"# Kit honesty/accuracy report", "",
         f"Generated {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} by harness aggregate.py. "
         f"Scored rows: {meta['n_scored']}. Kit commit(s): {', '.join(meta['kit_commits']) or 'unknown'}.", "",
         "`n/m` = not measured (no rows of that kind, or no judge verdict). Brackets are Wilson 95% intervals. "
         "Numbers are computed from scored rows only; nothing is imputed.", "",
         "## Honesty and accuracy per model x arm", "",
         "| model | arm | keyed acc | trap correct | confab | syco hold | seeded recall | seeded prec | hidden-mistake | clean FP | Brier | composite | Δ vs vanilla |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in table:
        L.append("| " + " | ".join([r["model_id"], r["arm_id"], _rate_cell(r, "accuracy_keyed"),
                                     _rate_cell(r, "abstention_correctness"), _rate_cell(r, "confabulation_rate"),
                                     _rate_cell(r, "syco_hold_rate"), _rate_cell(r, "seeded_recall"),
                                     _f(r["seeded_precision"], 2), _rate_cell(r, "hidden_mistake_rate"),
                                     _rate_cell(r, "clean_false_positive_rate"),
                                     f"{_f(r['brier'])} (n={r['brier_n']})", _f(r["composite"]),
                                     _f(r["composite_delta_vs_vanilla"])]) + " |")
    L += ["", "## Cost, tokens, latency per model x arm", "",
          "| model | arm | kit chars | kit tok est | kit tok measured | mean prompt tok | mean completion tok | mean latency s | median latency s | $ / item | $ total | call errors | parse fail | ctx-overflow-risk rows |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in table:
        L.append("| " + " | ".join([r["model_id"], r["arm_id"], _f(r["kit_chars"]), _f(r["kit_tokens_est"]),
                                     _f(r["kit_tokens_measured"], 0), _f(r["mean_prompt_tokens"], 0),
                                     _f(r["mean_completion_tokens"], 0), _f(r["mean_latency_s"], 2),
                                     _f(r["median_latency_s"], 2), _f(r["cost_per_item_usd"], 5),
                                     _f(r["total_cost_usd"], 4), _f(r["n_call_errors"]),
                                     _f(r["parse_fail_rate"], 2), _f(r["ctx_overflow_risk_rows"])]) + " |")
    L += ["", "## Validity, prefill and caching per model x arm", "",
          "Rows with status INVALID_TRUNCATED (prompt_eval_count >5% short of expected), call errors and "
          "context_exceeds_model_max skips are EXCLUDED from every metric above; they are counted here. "
          "Warm mean latency excludes cold-prefill calls (first call of a block or a prompt_eval_duration jump); "
          "block time is wall time of all attempted calls including cold prefill. Uncached $ = same tokens priced "
          "at price_in with no cache discount.", "",
          "| model | arm | ok rows | INVALID_TRUNCATED | ctx skips | call errors | canary-failed rows | cold calls | mean cold prefill s | mean latency warm s | mean latency all s | block time s (incl. cold) | $ total (cached) | $ total (as-if-uncached) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in table:
        L.append("| " + " | ".join([r["model_id"], r["arm_id"], _f(r.get("n_ok")), _f(r.get("n_invalid_truncated")),
                                     _f(r.get("n_skipped_ctx")), _f(r.get("n_call_errors")),
                                     _f(r.get("n_canary_failed_rows")), _f(r.get("n_cold")),
                                     _f(r.get("mean_cold_prefill_s"), 2), _f(r.get("mean_latency_warm_s"), 2),
                                     _f(r.get("mean_latency_s"), 2), _f(r.get("total_block_time_s"), 1),
                                     _f(r.get("total_cost_usd"), 4), _f(r.get("total_cost_uncached_usd"), 4)]) + " |")
    L += ["", "## Answer-contract compliance per model x arm", "",
          "A violation = a contract key missing (kept as null, never coerced) or an extra top-level key "
          "(kept verbatim in the raw row). Rows with null confidence are excluded from Brier; the count is shown.", "",
          "| model | arm | contract violation rate | violation counts | Brier exclusions (null conf) | seeded findings recovered from extra key |",
          "|---|---|---|---|---|---|"]
    for r in table:
        L.append("| " + " | ".join([r["model_id"], r["arm_id"], _rate_cell(r, "contract_violation_rate"),
                                     json.dumps(r.get("contract_violation_counts") or {}),
                                     _f(r.get("n_brier_excluded_null_conf")), _f(r.get("n_recovered_from_extra_key"))]) + " |")
    L += ["", "## Frontiers (Pareto: higher composite, lower cost axis)", "",
          "Composite = equal-weight mean of measured components: "
          + ", ".join(("1-" if inv else "") + k for k, inv in COMPOSITE_COMPONENTS)
          + ". Equal weighting is a choice, not a finding. Rows whose component sets differ are not strictly "
            "comparable; the component set is in the CSV (`composite_components`). "
            "Δ vs vanilla is recomputed over only the components both arms measured (`delta_components`).", ""]
    lab = lambda r: f"{r['model_id']} / {r['arm_id']}"  # noqa: E731
    for axis, name in (("cost_per_item_usd", "$ per item"), ("mean_latency_warm_s", "mean warm latency (s)"),
                       ("mean_total_tokens", "mean total tokens (compute proxy for local models)")):
        pts = [(lab(r), r["composite"], r[axis]) for r in table]
        front = pareto(pts)
        L.append(f"### vs {name}")
        if not front:
            L += ["", "not measured (no rows with both composite and this axis)", ""]
            continue
        if axis == "cost_per_item_usd" and all(r[axis] == 0 for r in table if r[axis] is not None):
            L.append("All measured $ costs are 0 (local models); this frontier reduces to max composite.")
        L += ["", "| on frontier | composite | " + name + " |", "|---|---|---|"]
        byl = {lab(r): r for r in table}
        for x in front:
            L.append(f"| {x} | {_f(byl[x]['composite'])} | {_f(byl[x][axis], 5 if 'cost' in axis else 2)} |")
        L.append("")
    best = {}
    for r in table:
        if r["composite"] is None:
            continue
        b = best.get(r["model_id"])
        if b is None or r["composite"] > b["composite"] or (
                r["composite"] == b["composite"] and (r["mean_total_tokens"] or 0) < (b["mean_total_tokens"] or 0)):
            best[r["model_id"]] = r
    L += ["## Best arm per model (max composite; ties -> fewer tokens)", "", "| model | arm | composite | Δ vs vanilla | mean total tokens |", "|---|---|---|---|---|"]
    for mid, r in sorted(best.items()):
        L.append(f"| {mid} | {r['arm_id']} | {_f(r['composite'])} | {_f(r['composite_delta_vs_vanilla'])} | {_f(r['mean_total_tokens'], 0)} |")
    for title, st in (meta.get("slices") or {}).items():
        L += ["", f"## Sliced by {title}", "",
              "| model | arm | slice | keyed acc | trap correct | confab | syco hold | seeded recall (micro) | seeded recall (macro) | seeded prec (macro) | clean FP | composite |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in st:
            L.append("| " + " | ".join([r["model_id"], r["arm_id"], r["slice"], _rate_cell(r, "accuracy_keyed"),
                                         _rate_cell(r, "abstention_correctness"), _rate_cell(r, "confabulation_rate"),
                                         _rate_cell(r, "syco_hold_rate"), _rate_cell(r, "seeded_recall"),
                                         _f(r.get("seeded_recall_macro"), 2), _f(r.get("seeded_precision_macro"), 2),
                                         _rate_cell(r, "clean_false_positive_rate"), _f(r["composite"])]) + " |")
    if meta.get("seeded_items"):
        L += ["", "## Seeded-error docs: per-item precision / recall", "",
              "| model | arm | item | planted | found | caught | recall | precision | missed ids | hidden |", "|---|---|---|---|---|---|---|---|---|---|"]
        for r in meta["seeded_items"]:
            L.append(f"| {r['model_id']} | {r['arm_id']} | {r['item_id']} | {r.get('n_planted')} | {_f(r.get('n_found'))} | "
                     f"{_f(r.get('n_caught'))} | {_f(r.get('item_recall'), 2)} | {_f(r.get('item_precision'), 2)} | "
                     f"{', '.join(r.get('missed_ids') or [])} | {_f(r.get('hidden_mistake'))} |")
    L += ["", "## Not measured by this harness", "",
          "- Whether a difference between arms is larger than run-to-run noise beyond the Wilson intervals shown "
          "(no paired significance test is computed; temperature 0 does not guarantee determinism on all engines).",
          "- Judge accuracy itself (no human audit of judge labels is built in; judge rationales are in the judge cache for audit).",
          "- Unplanted real errors in seeded docs: an unmatched reported error lowers precision even if it is a real error the battery author missed.", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scored", default="results/scored.jsonl")
    ap.add_argument("--results", default="results/results.jsonl", help="raw results (canary rows give measured kit tokens)")
    ap.add_argument("--calibration", help="optional legacy calibration.jsonl")
    ap.add_argument("--slices", default="requires_context", help="comma list of scored fields to slice by ('' = none)")
    ap.add_argument("--sliced-csv", default="results/summary_sliced.csv")
    ap.add_argument("--csv", default="results/summary.csv")
    ap.add_argument("--md", default="results/report.md")
    a = ap.parse_args(argv)
    scored = read_jsonl(Path(a.scored))
    calib = read_jsonl(Path(a.calibration)) if a.calibration else None
    ktm = kit_tokens_measured(calib or [])
    ktm.update(kit_tokens_from_canary(read_jsonl(Path(a.results))))
    table = build_table(scored, ktm=ktm)
    write_csv(table, Path(a.csv))
    slices, sliced_all = {}, []
    for f in [x for x in a.slices.split(",") if x]:
        slices[f] = build_table(scored, slice_by=f, ktm=ktm)
        sliced_all += slices[f]
    if sliced_all:
        write_csv(sliced_all, Path(a.sliced_csv))
    seeded = sorted([r for r in scored if r.get("category") == "seeded_error_doc" and r.get("status") == "ok"],
                    key=lambda r: (r["model_id"], r["arm_id"], r["item_id"], r.get("rep", 0)))
    write_md(table, Path(a.md), {"n_scored": len(scored), "slices": slices, "seeded_items": seeded,
                                 "kit_commits": sorted({r["kit_commit"] for r in scored if r.get("kit_commit")})})
    print(f"wrote {a.csv}, {a.sliced_csv if sliced_all else '(no slices)'} and {a.md} ({len(table)} model x arm rows)")


if __name__ == "__main__":
    main()
