"""Cross product models x arms x items (x reps) -> one JSONL row per item-run.

Block structure: for each model, for each arm, all items run CONSECUTIVELY with a
byte-identical system prompt (item-specific context/document goes in the USER message),
so a local engine loads the model once and the prompt prefix stays cached. Default serial.

Per (model, arm) block, in order:
  1. (optional) query POST /api/show for the model's max context; size num_ctx from the
     measured/estimated system+longest-item tokens + headroom; SKIP the arm if the required
     context exceeds the model's max (status row context_exceeds_model_max) instead of truncating.
  2. (optional) a canary self-check call: a canary planted at the START of the system prompt;
     if it is not returned, the whole block is flagged (block_canary_ok=false on every row).
  3. the item calls, each checked for silent truncation (prompt_eval_count vs expected);
     a short call gets status INVALID_TRUNCATED and is excluded from metrics.

Resumable: rows with status=="ok" skip on rerun; error/invalid rows are retried (old rows stay,
append-only; newest row per (item,model,arm,rep) wins).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from contextlib import nullcontext
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .arms import CHARS_PER_TOKEN_EST, Arm, build_arms, gated_answer_arm, parse_gate, prompt_chars
from .battery import first_user_message, load_battery
from .client import ChatFn, ChatResult, ModelSpec, chat
from .config import Config, load_config
from .contract import parse_response
from .exo import ExoLifecycle, maybe_instance
from .config import DEFAULT_NUM_CTX, kit_chars_per_token
from .config import (ANSWER_TPS_FLOOR, CAP_SAFETY_MARGIN, PREFILL_HEADROOM_S, THINKING_TOKEN_FLOOR,
                     effective_cap_and_timeout)
from .tokens import thinking_from_show
from .exo_sched import ExoScheduler, KVEstimateInvalid, ollama_keep_alive
from .tokens import (HEADROOM, PrefillTracker, context_max_from_show, ollama_show,
                     required_num_ctx, truncation_check)

Key = Tuple[str, str, str, int]
CANARY_PREFIX = ("SYSTEM CANARY: the pass phrase is {canary}. If asked for the canary, return it exactly. "
                 "This line is a context-integrity check; ignore it otherwise.\n\n")
CANARY_PROMPT = 'Return ONLY this JSON: {"answer": "<the SYSTEM CANARY pass phrase, verbatim>", "abstain": false, "confidence": 1, "errors_found": [], "notes": ""}'


def row_key(r: Dict[str, Any]) -> Key:
    return (r["item_id"], r["model_id"], r["arm_id"], int(r.get("rep", 0)))


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"[warn] {path}:{n} unreadable line kept in file, ignored", file=sys.stderr)
    return out


def completed_keys(path: Path) -> Set[Key]:
    return {row_key(r) for r in read_jsonl(path) if r.get("status") == "ok"}


class JsonlWriter:
    def __init__(self, path: Path):
        self.path, self.lock = path, threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, row: Dict[str, Any]) -> None:
        line = json.dumps(row, ensure_ascii=False) + "\n"
        with self.lock, open(self.path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())


def _sum(vals) -> Optional[float]:
    vals = list(vals)
    return None if any(v is None for v in vals) else sum(vals)


def _call(spec: ModelSpec, messages, chat_fn: ChatFn, temperature: float, retries: int,
          num_ctx: Optional[int]) -> ChatResult:
    use = spec
    if num_ctx is not None and spec.backend == "ollama" and spec.num_ctx != num_ctx:
        use = ModelSpec(**{**spec.__dict__, "num_ctx": num_ctx})
    if chat_fn is chat:
        return chat(use, messages, temperature=temperature, retries=retries)
    return chat_fn(use, messages)


def is_degenerate(text: str) -> bool:
    """A reply dominated by a single repeated token/substring is a model breakdown (e.g. the escaped-newline
    loop the lead measured on FK-045), not an answer. True when, after whitespace normalization, a <=4-char
    unit tiles >80% of the content, or <=3 distinct characters make up the whole of a long reply. It is a FLAG
    only; it never changes correctness."""
    import re as _re
    from collections import Counter as _C
    t = _re.sub(r"\s+", "", text or "")
    if len(t) < 40:
        return False
    for w in range(1, 5):
        unit = t[:w]
        if unit and t.count(unit) * w >= 0.8 * len(t):
            return True
    if len(set(t)) <= 3:
        return True
    return _C(t).most_common(1)[0][1] >= 0.8 * len(t)


def _run_turns(spec: ModelSpec, arm: Arm, item: Dict[str, Any], chat_fn: ChatFn, temperature: float,
               retries: int, num_ctx: Optional[int], cpt: float, prefill: Optional[PrefillTracker],
               trunc_tolerance: float, cpt_measured: bool,
               contract_reminder: Optional[str]) -> Tuple[List[Dict[str, Any]], Optional[str], Dict[str, Any]]:
    """Runs an item's user turns against one spec. Pulled out of run_one so a capped generation can be
    retried with a bigger cap without duplicating the turn/guard logic."""
    def with_reminder(u: str) -> str:
        return f"{u}\n\n{contract_reminder}" if contract_reminder else u
    first_user = with_reminder(first_user_message(item))
    messages = [{"role": "system", "content": arm.system_prompt}, {"role": "user", "content": first_user}]
    user_turns = [first_user] + [with_reminder(t) for t in (item.get("pressure_turns") or [])] \
        if item["category"] == "sycophancy_pressure" else [first_user]
    turns: List[Dict[str, Any]] = []
    error, trunc = None, {}
    for i, u in enumerate(user_turns):
        if i > 0:
            messages.append({"role": "user", "content": u})
        res = _call(spec, messages, chat_fn, temperature, retries, num_ctx)
        t = res.to_dict()
        t["user"] = u
        expected = round((len(arm.system_prompt) + sum(len(m["content"]) for m in messages if m["role"] != "system")) / cpt)
        user_est = round(sum(len(m["content"]) for m in messages if m["role"] != "system") / cpt)
        if prefill is not None:
            t["prefill"] = prefill.classify((spec.id, arm.id), res.prompt_eval_duration_ns)
        tc = truncation_check(res.prompt_tokens, expected, user_est, tolerance=trunc_tolerance,
                              estimate_slack=0.25 if cpt_measured else 0.0)
        if not cpt_measured and tc["trunc_guard"] == "fail" and (tc.get("trunc_short_frac") or 0) < 0.40:
            # chars/token not yet measured for this block: only a gross shortfall counts as truncation
            tc["trunc_guard"] = "pass_uncalibrated"
        # Guard applies uniformly, warm or cold: Ollama reports the FULL prompt count on a cache hit
        # (lead measured 28203 cold / 28200 / 28202 warm); only prompt_eval_duration collapses.
        t.update(tc)
        turns.append(t)
        if res.error:
            error = f"turn {i}: {res.error}"
            break
        if tc.get("trunc_guard") == "fail":
            trunc = tc
            break
        messages.append({"role": "assistant", "content": res.content})
    return turns, error, trunc


def _cap_hit(turns: List[Dict[str, Any]], ctoks: Optional[int], cap: Optional[int],
             error: Optional[str]) -> bool:
    return bool(error is None and (
        any(str(t.get("finish_reason")).lower() in ("length", "max_tokens") for t in turns)
        or (cap and ctoks is not None and ctoks >= cap)))


def effective_answer_cap(budget: Optional[int], num_ctx: Optional[int], prompt_tokens_est: int,
                         margin: int = CAP_SAFETY_MARGIN) -> Tuple[Optional[int], Optional[str]]:
    """Answer budget actually available = min(our budget, num_ctx - prompt - margin), with cap_reason naming
    which bound won. Per (model, arm): num_ctx and the kit prompt differ. At 40960/40000 ctx the 28k full-kit
    prompt leaves ~12.7k for generation, so qwen3:32b and magistral:24b are 'context_bound' under full_kit
    while every model is 'thinking_floor' elsewhere - a confound the report must surface, not hide."""
    window_room = (num_ctx - prompt_tokens_est - margin) if num_ctx else None
    if budget is None:
        return window_room, ("context_bound" if window_room is not None else None)
    if window_room is None or budget <= window_room:
        return budget, "thinking_floor"
    return max(window_room, 0), "context_bound"


def thinking_chars(turns: List[Dict[str, Any]]) -> int:
    return sum(len(t.get("thinking") or "") for t in turns)


def run_gate(spec: ModelSpec, arm: Arm, item: Dict[str, Any], chat_fn: ChatFn, temperature: float,
             retries: int, num_ctx: Optional[int]) -> Tuple[Dict[str, Any], Arm]:
    """gated_kit step 1: the model sees only the skill index and must name what to load (forced choice)."""
    msgs = [{"role": "system", "content": arm.meta["gate_system"]},
            {"role": "user", "content": first_user_message(item)}]
    res = _call(spec, msgs, chat_fn, temperature, retries, num_ctx)
    g: Dict[str, Any] = {"error": res.error, "latency_s": res.latency_s, "prompt_tokens": res.prompt_tokens,
                         "completion_tokens": res.completion_tokens,
                         "finish_reason": getattr(res, "finish_reason", None), "raw": (res.content or "")[:2000]}
    g.update(parse_gate(res.content, list(arm.meta["gate_skills"]), int(arm.meta["gate_max_skills"])))
    return g, gated_answer_arm(arm, g["selected"])


def _with_gate(row: Dict[str, Any], gate: Optional[Dict[str, Any]], spec: ModelSpec) -> Dict[str, Any]:
    """Gate cost is part of the arm's cost: fold its latency and tokens into the row totals, keep it itemized."""
    if gate is None:
        return row
    row["gate"], row["gate_selected"] = gate, gate["selected"]
    for f in ("latency_s", "prompt_tokens", "completion_tokens"):
        row[f + "_answer"] = row.get(f)
        if row.get(f) is not None and gate.get(f) is not None:
            row[f] = row[f] + gate[f]
    row.update(spec.cost_breakdown(ChatResult(
        prompt_tokens=row.get("prompt_tokens"), completion_tokens=row.get("completion_tokens"),
        cache_creation_input_tokens=row.get("cache_creation_input_tokens"),
        cache_read_input_tokens=row.get("cache_read_input_tokens"))))
    return row


def run_one(spec: ModelSpec, arm: Arm, item: Dict[str, Any], rep: int, chat_fn: ChatFn,
            temperature: float, retries: int, num_ctx: Optional[int], cpt: float,
            prefill: Optional[PrefillTracker], block_canary_ok: Optional[bool],
            trunc_tolerance: float, cpt_measured: bool = False,
            contract_reminder: Optional[str] = None, cap_retry_max: int = 0,
            cap_reason: Optional[str] = None) -> Dict[str, Any]:
    gate = None
    if arm.type == "gated_kit":
        gate, arm = run_gate(spec, arm, item, chat_fn, temperature, retries, num_ctx)
        if gate["error"]:
            row = _skip_row(spec, arm, item, rep, "error", {"gate": gate})
            row["error"] = f"gate: {gate['error']}"
            return row
    args = (arm, item, chat_fn, temperature, retries, num_ctx, cpt, prefill, trunc_tolerance,
            cpt_measured, contract_reminder)
    turns, error, trunc = _run_turns(spec, *args)
    ctoks = _sum(t.get("completion_tokens") for t in turns)
    cap = spec.max_tokens
    hit_max = _cap_hit(turns, ctoks, cap, error)
    cap_retry: Optional[Dict[str, Any]] = None
    cap_retry_skipped_reason: Optional[str] = None
    # A capped generation has NO answer: it is a lost datum, not a result. Retry ONCE with a bigger bounded
    # cap before accepting it as capped (lead's requirement), and record both attempts. But when the WINDOW
    # bound the budget (cap_reason=context_bound) doubling the cap is impossible, so suppress the retry and say so.
    _can_retry = hit_max and not trunc and cap and cap_retry_max > cap
    if hit_max and not trunc and cap_reason == "context_bound":
        _can_retry, cap_retry_skipped_reason = False, "context_bound"
    elif hit_max and not trunc and not _can_retry:
        cap_retry_skipped_reason = "retry_disabled_or_not_larger"
    if _can_retry:
        retry_cap = min(cap * 2, cap_retry_max)
        eff = ModelSpec(**{**spec.__dict__, "max_tokens": retry_cap,
                           "timeout_s": max(spec.timeout_s,
                                            retry_cap / ANSWER_TPS_FLOOR + PREFILL_HEADROOM_S)})
        t2, e2, tr2 = _run_turns(eff, *args)
        c2 = _sum(t.get("completion_tokens") for t in t2)
        h2 = _cap_hit(t2, c2, retry_cap, e2)
        cap_retry = {"cap_first": cap, "cap_retry": retry_cap, "hit_max_first": True, "hit_max_retry": h2,
                     "completion_tokens_first": ctoks, "completion_tokens_retry": c2,
                     "thinking_chars_first": thinking_chars(turns)}
        turns, error, trunc, ctoks, cap, hit_max = t2, e2, tr2, c2, retry_cap, h2
    ptoks = _sum(t.get("prompt_tokens") for t in turns)
    cost = spec.cost_breakdown(ChatResult(
        prompt_tokens=ptoks, completion_tokens=ctoks,
        cache_creation_input_tokens=_sum(t.get("cache_creation_input_tokens") for t in turns),
        cache_read_input_tokens=_sum(t.get("cache_read_input_tokens") for t in turns)))
    degen = any(is_degenerate(t.get("content") or "") for t in turns)
    status = "error" if error else ("INVALID_TRUNCATED" if trunc else "OUTPUT_CAPPED" if hit_max else "ok")
    _tt = [t.get("thinking_tokens") for t in turns if t.get("thinking_tokens") is not None]
    row: Dict[str, Any] = {
        "run_id": uuid.uuid4().hex, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "item_id": item["id"], "category": item["category"], "requires_context": item.get("requires_context"),
        "difficulty": item.get("difficulty"), "rep": rep,
        "model_id": spec.id, "model": spec.model, "backend": spec.backend, "tier": spec.tier,
        "family": spec.family, "lineage": spec.lineage, "num_ctx": num_ctx,
        "arm_id": arm.id, "arm_type": arm.type, "kit_chars": arm.kit_chars, "kit_tokens_est": arm.kit_tokens_est,
        "kit_commit": arm.meta["kit_commit"], "system_prompt_sha256": arm.meta["system_prompt_sha256"],
        "chars_per_token_used": round(cpt, 3), "chars_per_token_measured": cpt_measured,
        "block_canary_ok": block_canary_ok,
        "temperature": temperature, "turns": turns,
        "status": status, "error": error,
        "finish_reason": turns[-1].get("finish_reason") if turns else None,
        "hit_max_tokens": hit_max, "degenerate_output": degen, "max_tokens_sent": cap,
        "effective_max_tokens": cap, "cap_reason": cap_reason,
        "cap_retry_skipped_reason": cap_retry_skipped_reason,
        "thinking": spec.thinking, "thinking_chars": thinking_chars(turns),
        "thinking_tokens": sum(_tt) if _tt else None,
        "retried_for_cap": cap_retry is not None,
        "prompt_tokens": ptoks, "completion_tokens": ctoks,
        "prompt_eval_duration_ns": turns[0].get("prompt_eval_duration_ns") if turns else None,
        "prefill": turns[0].get("prefill") if turns else None,
        "latency_s": _sum(t.get("latency_s") for t in turns),
        "cache_creation_input_tokens": _sum(t.get("cache_creation_input_tokens") for t in turns),
        "cache_read_input_tokens": _sum(t.get("cache_read_input_tokens") for t in turns),
        **cost,
    }
    if cap_retry:
        row["cap_retry"] = cap_retry
    if trunc:
        row["trunc"] = trunc
    if status == "ok":
        last = turns[-1]
        row["parsed"] = parse_response(last["content"], last.get("thinking"))
        if len(turns) > 1:
            row["first_parsed"] = parse_response(turns[0]["content"], turns[0].get("thinking"))
    return _with_gate(row, gate, spec)


def _skip_row(spec: ModelSpec, arm: Arm, item: Dict[str, Any], rep: int, reason: str,
              detail: Dict[str, Any]) -> Dict[str, Any]:
    return {"run_id": uuid.uuid4().hex, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "item_id": item["id"], "category": item["category"], "rep": rep,
            "model_id": spec.id, "model": spec.model, "backend": spec.backend, "family": spec.family,
            "lineage": spec.lineage, "arm_id": arm.id, "arm_type": arm.type,
            "status": reason, "error": reason, **detail}


def model_max_ctx(spec: ModelSpec, fetch_show: bool, log) -> Optional[int]:
    """Registry max_ctx wins (it carries the lead's trained-limit pins); else ollama POST /api/show."""
    if spec.max_ctx is not None:
        return spec.max_ctx
    if spec.backend == "ollama" and fetch_show:
        try:
            return context_max_from_show(ollama_show(spec.base_url, spec.model))
        except Exception as e:  # noqa: BLE001 - recorded, sizing continues without the cap
            log(f"[warn] /api/show failed for {spec.id}: {e}; cannot verify model max context")
    return None


def model_thinking(spec: ModelSpec, fetch_show: bool, log) -> Optional[bool]:
    """Ollama /api/show `capabilities`. Returns None when it cannot be determined (exo exposes no
    capabilities; those models are detected from the reply channel instead)."""
    if spec.backend == "ollama" and fetch_show:
        try:
            return thinking_from_show(ollama_show(spec.base_url, spec.model))
        except Exception as e:  # noqa: BLE001 - recorded, run continues on the registry flag
            log(f"[warn] /api/show capabilities failed for {spec.id}: {e}")
    return None


def size_num_ctx(spec: ModelSpec, arm: Arm, longest_user_chars: int, cpt: float, max_ctx: Optional[int],
                 default_num_ctx: int = DEFAULT_NUM_CTX) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    """Returns (num_ctx, max_ctx, skip_reason). Only sizes ollama/exo backends.

    Standing order: target = registry num_ctx_full_kit (full_kit arm) or num_ctx_default (other arms),
    else `default_num_ctx` (Doc's 100000); capped at the model's trained max. Nothing hardcoded per model.
    The measured requirement (system + longest item + headroom + completion reserve) is a FLOOR: if it
    exceeds the cap the arm is skipped (context_exceeds_model_max), never silently truncated.
    """
    if spec.backend not in ("ollama", "exo"):
        return None, max_ctx, None
    # The SKIP decision is PROMPT fit only (system + longest item + headroom). The completion reserve still
    # raises the num_ctx target below, but must not cause a skip: with the 16384 thinking floor, counting the
    # full reserve here would skip qwen3:32b (40960) and magistral:24b (40000) whose PROMPTS fit fine, which
    # contradicts the lead's measured "the kit fits every model". A model whose window cannot hold prompt +
    # full answer budget simply gets whatever generation room is left, and the cap/degenerate guards catch it.
    raw = round(prompt_chars(arm) / cpt) + round(longest_user_chars / cpt) + HEADROOM
    # Compare the UNROUNDED requirement with the trained max: ladder rounding (e.g. 36k -> 40960) must not
    # skip a block that fits under a non-ladder limit such as magistral:24b's 40000.
    if max_ctx is not None and raw > max_ctx:
        return raw, max_ctx, "context_exceeds_model_max"
    need = required_num_ctx(round(prompt_chars(arm) / cpt), round(longest_user_chars / cpt), HEADROOM,
                            completion_reserve=spec.max_tokens or 0)
    target = spec.num_ctx_full_kit if arm.type == "full_kit" else spec.num_ctx_default
    if target is None:
        target = spec.num_ctx or default_num_ctx
    want = max(int(target), need)
    return (min(want, max_ctx) if max_ctx else want), max_ctx, None


def canary_check(spec: ModelSpec, arm: Arm, chat_fn: ChatFn, temperature: float, retries: int,
                 num_ctx: Optional[int], log) -> Dict[str, Any]:
    canary = "ORCHID-" + uuid.uuid4().hex[:8].upper()
    sys = CANARY_PREFIX.format(canary=canary) + arm.system_prompt
    # Thinking models spend a 64-token budget on reasoning and return empty content (gpt-oss:20b, 2026-10-18),
    # which falsely failed every block; give them room to think and still answer.
    budget = 64 if not spec.thinking else max(1024, int(spec.max_tokens or 0))
    res = _call(ModelSpec(**{**spec.__dict__, "max_tokens": budget}),
                [{"role": "system", "content": sys}, {"role": "user", "content": CANARY_PROMPT}],
                chat_fn, temperature, retries, num_ctx)
    ok = (not res.error) and canary in (res.content or "")
    log(f"  canary {spec.id} | {arm.id}: {'OK' if ok else 'FAIL'}"
        + (f" ({res.error})" if res.error else f" ptok={res.prompt_tokens}"))
    return {"ok": ok, "canary": canary, "prompt_tokens": res.prompt_tokens, "error": res.error,
            "chars": len(sys) + len(CANARY_PROMPT), "latency_s": res.latency_s,
            "prompt_eval_duration_ns": res.prompt_eval_duration_ns,
            "returned": (res.content or "")[:200]}


def run(cfg: Config, battery_path: Path, out: Path, model_ids: Optional[List[str]] = None,
        arm_ids: Optional[List[str]] = None, reps: int = 1, chat_fn: ChatFn = chat,
        dry_run: bool = False, do_canary: bool = True, fetch_show: bool = True,
        lifecycle_log: Optional[Path] = None, scheduler: Optional[ExoScheduler] = None,
        keep_alive: Optional[str] = "60m", contract_reminder: Any = "__cfg__",
        log=print) -> Dict[str, int]:
    items = load_battery(battery_path)
    arms = build_arms(cfg.kit_root, cfg.arms, cfg.strip_frontmatter)
    if arm_ids:
        missing = set(arm_ids) - {a.id for a in arms}
        if missing:
            raise ValueError(f"unknown arms {sorted(missing)}; have {[a.id for a in arms]}")
        arms = [a for a in arms if a.id in arm_ids]
    model_ids = model_ids or cfg.raw.get("test_models") or list(cfg.models)
    longest_user = max((len(first_user_message(it)) + sum(len(t) for t in it.get("pressure_turns") or []))
                       for it in items)
    done = completed_keys(out)
    reminder = cfg.contract_reminder if contract_reminder == "__cfg__" else contract_reminder
    w = JsonlWriter(out)
    # run-level provenance: the contract reminder is part of the measurement instrument (lead's requirement),
    # so record it. status "run_meta" is skipped by every consumer (latest_rows/metrics filter on status).
    w.write({"status": "run_meta", "kind": "provenance",
             "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "contract_reminder": reminder, "contract_reminder_enabled": reminder is not None,
             "default_max_tokens": cfg.raw.get("default_max_tokens"),
             "thinking_max_tokens": int(cfg.raw.get("thinking_max_tokens", THINKING_TOKEN_FLOOR)),
             "cap_safety_margin": int(cfg.raw.get("cap_safety_margin", CAP_SAFETY_MARGIN)),
             "arms": [a.get("id") or a.get("type") for a in cfg.arms]})
    lcw = JsonlWriter(lifecycle_log) if lifecycle_log else None
    exo_lc = ExoLifecycle(cfg.exo_base, lcw, log=log) if cfg.exo_base else None
    if scheduler is None and cfg.exo_base and cfg.raw.get("exo_scheduler", True):
        scheduler = ExoScheduler(cfg.exo_base, lcw, log=log, **(cfg.raw.get("exo_scheduler_opts") or {}))
    stats = {"planned": 0, "todo": 0, "ok": 0, "error": 0, "INVALID_TRUNCATED": 0,
             "context_exceeds_model_max": 0, "canary_failed_blocks": 0, "kv_estimate_invalid": 0}
    prefill = PrefillTracker()
    cpt = CHARS_PER_TOKEN_EST
    fk = next((a for a in arms if a.type == "full_kit"), None)
    meas_cpt = kit_chars_per_token(cfg.registry_raw, fk.kit_chars if fk else None)
    if meas_cpt:
        cpt = meas_cpt
        log(f"chars/token calibrated from registry _kit_tokens_measured: {cpt:.3f} "
            f"(kit {fk.kit_chars} chars -> {cfg.registry_raw.get('_kit_tokens_measured')} measured tokens)")

    def emit(row):
        w.write(row)
        stats[row["status"]] = stats.get(row["status"], 0) + 1

    floor = int(cfg.raw.get("thinking_max_tokens", THINKING_TOKEN_FLOOR))
    cap_retry_max = int(cfg.raw.get("cap_retry_max", 2 * floor))
    cap_margin = int(cfg.raw.get("cap_safety_margin", CAP_SAFETY_MARGIN))
    for mid in model_ids:
        spec = cfg.models[mid]
        # Auto-detect thinking rather than trusting the registry flag: the lead's registry had gemma4:12b
        # wrong and it burned its whole 4096 cap on the thinking channel, answering nothing.
        shown = model_thinking(spec, fetch_show, log)
        thinking_eff = bool(spec.thinking or shown)
        if shown and not spec.thinking:
            log(f"[warn] {mid}: /api/show capabilities report 'thinking' but the registry says "
                f"thinking=false; applying the {floor}-token answer budget anyway")
        _cap, _tmo = effective_cap_and_timeout(spec, thinking_eff, cfg.raw.get("default_max_tokens"), floor)
        if (_cap, _tmo) != (spec.max_tokens, spec.timeout_s):
            log(f"{mid}: answer budget max_tokens={_cap} timeout={_tmo:.0f}s "
                f"(thinking={thinking_eff}, registry={spec.thinking})")
            spec = ModelSpec(**{**spec.__dict__, "max_tokens": _cap, "timeout_s": _tmo,
                                "thinking": thinking_eff})
        cur_spec = spec
        maxc = model_max_ctx(spec, fetch_show, log)
        plan = {a.id: size_num_ctx(spec, a, longest_user, cpt, maxc, cfg.raw.get("default_num_ctx", DEFAULT_NUM_CTX))
                for a in arms}
        block_ctx = max([nc for nc, _, sk in plan.values() if nc and not sk] or [0])
        sched = scheduler if (spec.backend == "exo" and spec.needs_instance and scheduler and not dry_run) else None
        # One exo model resident at a time: place once, run EVERY arm and item, evict. No mid-block rebalance.
        ctx = (nullcontext() if dry_run else                       # dry run places nothing on the cluster
               sched.block(spec, block_ctx) if sched else maybe_instance(spec, exo_lc))
        with ctx as blk:
            mon = blk if sched else None
            if spec.backend == "ollama" and keep_alive is not None and not dry_run:
                try:
                    ollama_keep_alive(spec.base_url, spec.model, keep_alive)
                except Exception as e:  # noqa: BLE001
                    log(f"[warn] keep_alive load failed for {mid}: {e}")
            for arm in arms:
                block = [(spec, arm, it, rep) for it in items for rep in range(reps)]
                stats["planned"] += len(block)
                pending = [b for b in block if (b[2]["id"], b[0].id, b[1].id, b[3]) not in done]
                if not pending:
                    continue
                num_ctx, max_ctx, skip = plan[arm.id]
                if skip:
                    log(f"[SKIP] {mid} | {arm.id}: {skip} (need≈{num_ctx} > max {max_ctx})")
                    for b in pending:
                        emit(_skip_row(spec, arm, b[2], b[3], skip,
                                       {"required_num_ctx": num_ctx, "model_max_ctx": max_ctx}))
                    continue
                stats["todo"] += len(pending)
                log(f"block {mid} | {arm.id} | num_ctx={num_ctx} | items={len(pending)}"
                    + (f" | model_max_ctx={max_ctx}" if max_ctx else ""))
                if dry_run:
                    continue
                canary = canary_check(spec, arm, chat_fn, cfg.temperature, cfg.retries, num_ctx, log) \
                    if do_canary else None
                block_ok = canary["ok"] if canary else None
                if canary:
                    emit_canary = {"status": "canary", "model_id": mid, "arm_id": arm.id, "num_ctx": num_ctx,
                                   "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **canary}
                    w.write(emit_canary)
                    if not block_ok:
                        stats["canary_failed_blocks"] += 1
                        log(f"[WARN] canary FAILED for {mid} | {arm.id}: rows flagged block_canary_ok=false")
                bcpt, measured = cpt, False
                if canary and canary["ok"] and canary.get("prompt_tokens"):
                    bcpt, measured = canary["chars"] / canary["prompt_tokens"], True
                aborted = None
                for (s, a, it, rep) in pending:
                    if aborted:
                        emit(_skip_row(s, a, it, rep, "kv_estimate_invalid", {"detail": aborted}))
                        continue
                    utext = first_user_message(it) + "".join(it.get("pressure_turns") or [])
                    p_est = round((prompt_chars(a) + len(utext)) / bcpt)
                    eff_cap, cap_reason = effective_answer_cap(cur_spec.max_tokens, num_ctx, p_est, cap_margin)
                    item_spec = cur_spec if eff_cap == cur_spec.max_tokens \
                        else ModelSpec(**{**cur_spec.__dict__, "max_tokens": eff_cap})
                    row = run_one(item_spec, a, it, rep, chat_fn, cfg.temperature, cfg.retries, num_ctx, bcpt,
                                  prefill, block_ok, cfg.raw.get("trunc_tolerance", 0.05), measured,
                                  contract_reminder=reminder, cap_retry_max=cap_retry_max, cap_reason=cap_reason)
                    # Reply-channel fallback (exo exposes no capabilities, and a registry flag can be wrong):
                    # the model demonstrably thinks, so apply the floor for the rest of its run.
                    if not thinking_eff and (row.get("thinking_chars") or 0) > 0:
                        thinking_eff = True
                        c2, t2 = effective_cap_and_timeout(cur_spec, True,
                                                           cfg.raw.get("default_max_tokens"), floor)
                        log(f"[warn] {mid}: emitted a non-empty thinking channel but was not flagged "
                            f"thinking; raising the answer budget to max_tokens={c2} timeout={t2:.0f}s")
                        cur_spec = ModelSpec(**{**cur_spec.__dict__, "max_tokens": c2, "timeout_s": t2,
                                                "thinking": True})
                    if not measured and row["status"] == "ok" and row["turns"][0].get("prompt_tokens") \
                            and row["turns"][0].get("prefill") == "cold":
                        chars = len(a.system_prompt) + len(row["turns"][0]["user"])
                        bcpt, measured = chars / row["turns"][0]["prompt_tokens"], True
                    emit(row)
                    if mon is not None:
                        try:
                            mon.sample()
                        except KVEstimateInvalid as e:
                            aborted = str(e)
                            log(f"[ABORT] {mid} | {a.id}: kv_estimate_invalid: {e}")
                    n = sum(stats[k] for k in ("ok", "error", "INVALID_TRUNCATED"))
                    log(f"[{n}/{stats['todo']}] {row['status']:16s} {mid} | {a.id} | {it['id']} "
                        f"| ptok={row['prompt_tokens']} ctok={row['completion_tokens']} "
                        f"prefill={row['prefill']} lat={row['latency_s'] and round(row['latency_s'],2)}s"
                        + (f" | {row['error'][:160]}" if row.get("error") else ""))
        if spec.backend == "ollama" and keep_alive is not None and not dry_run:
            try:
                ollama_keep_alive(spec.base_url, spec.model, 0)       # release after the model's blocks
                log(f"released keep_alive for {mid}")
            except Exception as e:  # noqa: BLE001
                log(f"[warn] keep_alive release failed for {mid}: {e}")
    log(f"done: {json.dumps(stats)}")
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("--battery", required=True)
    ap.add_argument("--out", default="results/results.jsonl")
    ap.add_argument("--models")
    ap.add_argument("--arms")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-canary", action="store_true")
    ap.add_argument("--no-show", action="store_true", help="skip POST /api/show model-max lookups")
    ap.add_argument("--keep-alive", default="60m", help="ollama keep_alive held for a model's blocks; '' disables")
    ap.add_argument("--lifecycle-log", default="results/exo_lifecycle.jsonl")
    ap.add_argument("--no-contract-reminder", action="store_true",
                    help="ablation: do NOT append the contract reminder to user turns")
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    mids = a.models.split(",") if a.models else None
    if mids:
        bad = [m for m in mids if m not in cfg.models]
        if bad:
            ap.error(f"unknown models {bad}")
    s = run(cfg, Path(a.battery), Path(a.out), mids, a.arms.split(",") if a.arms else None, a.reps,
            dry_run=a.dry_run, do_canary=not a.no_canary, fetch_show=not a.no_show,
            keep_alive=a.keep_alive or None,
            contract_reminder=(None if a.no_contract_reminder else "__cfg__"),
            lifecycle_log=Path(a.lifecycle_log))
    print(json.dumps(s))


if __name__ == "__main__":
    main()
