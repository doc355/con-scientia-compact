"""Context sizing, model context limits, truncation guard, prefill classification.

Measured basis (lead, fleet, llama3.2:3b, full kit 127,452 chars = 28,215 tokens):
  num_ctx=8192  -> prompt_eval_count=4098, kit silently truncated, canary lost.
  num_ctx=40960 -> prompt_eval_count=28215, canary exact.
So num_ctx is sized per (model, arm) from a MEASURED system-prompt token count, and every
call is checked against the expected prompt size.
"""
from __future__ import annotations

import json
import math
import urllib.request
from statistics import median
from typing import Any, Dict, List, Optional

CTX_LADDER = [2048, 4096, 8192, 12288, 16384, 24576, 32768, 40960, 49152, 65536, 81920, 98304,
              131072, 163840, 196608, 262144, 524288, 1048576]
HEADROOM = 4096
TRUNC_TOLERANCE = 0.05


def ladder_up(n: int) -> int:
    for v in CTX_LADDER:
        if v >= n:
            return v
    return int(2 ** math.ceil(math.log2(n)))


def required_num_ctx(system_tokens: int, longest_user_tokens: int, headroom: int = HEADROOM,
                     floor: Optional[int] = None, completion_reserve: int = 0) -> int:
    need = ladder_up(system_tokens + longest_user_tokens + headroom + completion_reserve)
    return max(need, floor or 0)


def ollama_show(base_url: str, model: str, timeout: float = 60.0) -> Dict[str, Any]:
    req = urllib.request.Request(base_url.rstrip("/") + "/api/show", method="POST",
                                 data=json.dumps({"model": model}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def context_max_from_show(show: Dict[str, Any]) -> Optional[int]:
    """Model's trained max context. /api/show puts it at model_info['<arch>.context_length']."""
    mi = show.get("model_info") or {}
    arch = mi.get("general.architecture")
    if arch and isinstance(mi.get(f"{arch}.context_length"), int):
        return mi[f"{arch}.context_length"]
    vals = [v for k, v in mi.items() if k.endswith(".context_length") and isinstance(v, int)]
    return max(vals) if vals else None


def expected_prompt_tokens(system_tokens: int, user_chars: int, chars_per_token: float) -> int:
    return round(system_tokens + user_chars / chars_per_token)


def truncation_check(observed: Optional[int], expected: Optional[int], user_est_tokens: int,
                     tolerance: float = TRUNC_TOLERANCE, estimate_slack: float = 0.25) -> Dict[str, Any]:
    """FAIL if observed < expected*(1-tolerance) - estimate_slack*user_est_tokens.
    The slack term exists because the user-message token count is estimated (chars / measured
    chars-per-token), not tokenized; set estimate_slack=0 for the lead's strict 5% rule."""
    if observed is None or expected is None:
        return {"trunc_guard": "not_checkable", "trunc_expected": expected, "trunc_observed": observed}
    floor = expected * (1 - tolerance) - estimate_slack * user_est_tokens
    return {"trunc_guard": "fail" if observed < floor else "pass", "trunc_expected": expected,
            "trunc_observed": observed, "trunc_short_frac": round(1 - observed / expected, 4) if expected else None}


class PrefillTracker:
    """cold = first call of a (model, arm) block in this process, or a prompt_eval_duration jump
    (> jump_factor x median of earlier calls in the block and > min_cold_ns). Derived from DURATION only,
    never from prompt_eval_count (counts are full-prompt on cache hits and drift by a few tokens)."""

    def __init__(self, jump_factor: float = 5.0, min_cold_ns: int = 1_000_000_000):
        self.hist: Dict[tuple, List[float]] = {}
        self.jump, self.min_cold = jump_factor, min_cold_ns

    def classify(self, block: tuple, duration: Optional[float]) -> str:
        h = self.hist.setdefault(block, [])
        if duration is None:
            label = "cold" if not h else "unknown"
            h.append(float("nan"))
            return label
        prior = [x for x in h if x == x]
        label = "cold" if not h or (prior and duration > self.jump * median(prior) and duration > self.min_cold) else "warm"
        h.append(duration)
        return label
