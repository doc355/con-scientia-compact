"""Config loading. JSON (stdlib) so the harness has zero dependencies.

Experiment config (config.json): kit_root, arms, thresholds, and EITHER
  "registry": "path/to/registry.json"   (lead's registry shape, see load_registry)
or an inline "models": [ModelSpec dicts] + "judge_pool": [ids].
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .contract import CONTRACT_REMINDER
from .client import ModelSpec

REGISTRY_MODEL_KEYS = {"id", "backend", "lineage", "price_in", "price_out", "tier", "thinking", "needs_instance",
                       # harness extensions, optional:
                       "model", "num_ctx", "max_tokens", "think", "options", "timeout_s", "family", "system_role",
                       "api_key_env", "base_url", "price_cache_write", "price_cache_read", "prompt_cache",
                       "max_ctx", "num_ctx_default", "num_ctx_full_kit", "weights_gib", "weights_bytes", "kv_bytes_per_token",
                       "keep_alive"}
DEFAULT_NUM_CTX = 100000        # Doc's standing order; capped per model at max_ctx
TIMEOUT_FLOOR_LARGE_S = 300.0   # lead: >=300 s for large/thinking models (gpt-oss:20b measured 13-30 s/item vanilla)
DEFAULT_TIMEOUT_S = 600.0
# Lead-measured: gemma4:12b (registry said thinking:false) spent its ENTIRE 4096 cap on the thinking channel
# and never emitted an answer on 3 of 5 items, 135 s each. Ollama counts thinking inside eval_count, so the
# only fix for that backend is a bigger cap for reasoning models.
THINKING_TOKEN_FLOOR = 16384
# Lead's budget note: at ~30 tok/s a 16k cap allows ~9 min/item, so the timeout must clear
# max_tokens / 25 tok/s + prefill headroom or a legitimate long reasoning run is killed as an error.
ANSWER_TPS_FLOOR = 25.0
PREFILL_HEADROOM_S = 120.0


def effective_cap_and_timeout(spec, thinking: bool, default_max_tokens: Optional[int] = None,
                              floor: int = THINKING_TOKEN_FLOOR) -> Tuple[Optional[int], float]:
    """Answer budget for a model, and a timeout that can actually wait for it.
    A thinking model gets at least `floor`; the timeout clears cap/ANSWER_TPS_FLOOR + prefill headroom."""
    base = spec.max_tokens if spec.max_tokens is not None else default_max_tokens
    cap = (max(base or 0, floor) or floor) if thinking else base
    timeout = spec.timeout_s
    if cap:
        timeout = max(timeout, cap / ANSWER_TPS_FLOOR + PREFILL_HEADROOM_S)
    return cap, timeout


def timeout_for(m: Dict[str, Any]) -> float:
    t = float(m.get("timeout_s", DEFAULT_TIMEOUT_S))
    if bool(m.get("thinking")) or str(m.get("tier", "")).lower() in ("large", "xl", "huge"):
        t = max(t, TIMEOUT_FLOOR_LARGE_S)
    return t


@dataclass
class Config:
    kit_root: Path
    models: Dict[str, ModelSpec]
    arms: List[Dict[str, Any]]
    judge_pool: List[str] = field(default_factory=list)
    judge_match_lineage: bool = True
    n_judges: int = 1
    temperature: float = 0.0
    concurrency: int = 1
    retries: int = 2
    strip_frontmatter: bool = False
    confab_confidence_threshold: float = 0.5
    exo_base: Optional[str] = None
    ollama_base: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    registry_raw: Dict[str, Any] = field(default_factory=dict)
    contract_reminder: Optional[str] = CONTRACT_REMINDER   # part of the instrument; see contract.py


def _reminder_from(d: Dict[str, Any]) -> Optional[str]:
    """Absent -> default reminder. Explicit "" or null -> disabled (the ablation)."""
    if "contract_reminder" not in d:
        return CONTRACT_REMINDER
    v = d["contract_reminder"]
    return None if v in ("", None) else str(v)


def kit_chars_per_token(reg: Dict[str, Any], kit_chars: Optional[int]) -> Optional[float]:
    """chars/token measured from the lead's registry: _kit_tokens_measured (28215) against the assembled
    full_kit char count. Beats the 4.0 guess, which overstated the kit by 14% and skipped magistral:24b."""
    n = reg.get("_kit_tokens_measured") if isinstance(reg, dict) else None
    return (kit_chars / n) if (n and kit_chars) else None


def load_registry(path: str | Path, default_num_ctx: Optional[int] = None,
                  default_max_tokens: Optional[int] = None) -> Tuple[Dict[str, ModelSpec], List[str], Dict[str, Any]]:
    """Lead's registry shape:
    {"ollama_base": "...", "exo_base": "...",
     "models": [{"id", "backend": "ollama|exo", "lineage", "price_in", "price_out", "tier",
                 "thinking"?, "needs_instance"?}],
     "judge_pool": [ids]}
    `id` is also the backend model name unless "model" is given. `family` defaults to `lineage`
    (the registry carries lineage only), so the judge rule is enforced at lineage level.
    Optional per-model extensions: num_ctx, max_tokens, think, options, timeout_s.
    """
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    models: Dict[str, ModelSpec] = {}
    for m in d["models"]:
        unknown = {k for k in set(m) if not k.startswith('_')} - REGISTRY_MODEL_KEYS
        if unknown:
            raise ValueError(f"registry model {m.get('id')}: unknown keys {sorted(unknown)}")
        be = m["backend"]
        if be not in ("ollama", "exo", "openai", "anthropic"):
            raise ValueError(f"registry model {m['id']}: backend must be ollama|exo|openai|anthropic, got {be!r}")
        # A registry-flagged thinking model gets the answer-budget floor and a timeout that clears it. Models
        # the registry has WRONG are caught at runtime from /api/show capabilities or the reply channel.
        _thinking = bool(m.get("thinking", False))
        _mt = m.get("max_tokens", default_max_tokens)
        if _thinking:
            _mt = max(_mt or 0, THINKING_TOKEN_FLOOR) or THINKING_TOKEN_FLOOR
        _to = timeout_for(m)
        if _mt:
            _to = max(_to, _mt / ANSWER_TPS_FLOOR + PREFILL_HEADROOM_S)
        base = m.get("base_url") or {"ollama": d.get("ollama_base"), "exo": d.get("exo_base")}.get(be)
        if not base:
            raise ValueError(f"registry model {m['id']}: no base url (set base_url, or ollama_base/exo_base)")
        spec = ModelSpec(
            id=m["id"], backend=be, base_url=base, model=m.get("model", m["id"]),
            family=m.get("family") or m["lineage"], lineage=m["lineage"],
            price_per_mtok_in=float(m.get("price_in", 0) or 0), price_per_mtok_out=float(m.get("price_out", 0) or 0),
            num_ctx=m.get("num_ctx", default_num_ctx), max_tokens=_mt,
            api_key_env=m.get("api_key_env"), timeout_s=_to,
            options=m.get("options") or {}, system_role=m.get("system_role", True),
            tier=str(m.get("tier", "")), thinking=bool(m.get("thinking", False)), think=m.get("think"),
            needs_instance=bool(m.get("needs_instance", False)),
            price_per_mtok_cache_write=m.get("price_cache_write"), price_per_mtok_cache_read=m.get("price_cache_read"),
            prompt_cache=bool(m.get("prompt_cache", False)), max_ctx=m.get("max_ctx"),
            num_ctx_default=m.get("num_ctx_default"), num_ctx_full_kit=m.get("num_ctx_full_kit"),
            weights_gib=(m.get("weights_gib") if m.get("weights_gib") is not None else
                         (m["weights_bytes"] / 1024 ** 3 if m.get("weights_bytes") is not None else None)),
            kv_bytes_per_token=m.get("kv_bytes_per_token"),
            keep_alive=m.get("keep_alive"),
        )
        if spec.id in models:
            raise ValueError(f"duplicate model id {spec.id}")
        models[spec.id] = spec
    jp = list(d.get("judge_pool", []))
    for j in jp:
        if j not in models:
            raise ValueError(f"judge {j} not in registry models")
    return models, jp, d


def load_config(path: str | Path) -> Config:
    path = Path(path)
    d = json.loads(path.read_text(encoding="utf-8"))

    def rel(p: str) -> Path:
        q = Path(p).expanduser()
        return q if q.is_absolute() else (path.parent / q).resolve()

    exo_base = ollama_base = None
    reg: Dict[str, Any] = {}
    if "registry" in d:
        models, judge_pool, reg = load_registry(rel(d["registry"]), d.get("default_num_ctx"), d.get("default_max_tokens"))
        exo_base, ollama_base = reg.get("exo_base"), reg.get("ollama_base")
        judge_pool = d.get("judge_pool", judge_pool)
    else:
        models = {}
        for m in d["models"]:
            spec = ModelSpec.from_dict(m)
            if spec.id in models:
                raise ValueError(f"duplicate model id {spec.id}")
            models[spec.id] = spec
        judge_pool = d.get("judge_pool", [])
        exo_base = d.get("exo_base")
    for j in judge_pool:
        if j not in models:
            raise ValueError(f"judge {j} not in models")
    return Config(contract_reminder=_reminder_from(d), registry_raw=reg if isinstance(reg, dict) else {}, 
        kit_root=rel(d["kit_root"]),
        models=models,
        arms=d.get("arms", [{"type": "vanilla"}, {"type": "full_kit"}, {"type": "master_only"}]),
        judge_pool=judge_pool,
        judge_match_lineage=d.get("judge_match_lineage", True),
        n_judges=d.get("n_judges", 1),
        temperature=d.get("temperature", 0.0),
        concurrency=d.get("concurrency", 1),
        retries=d.get("retries", 2),
        strip_frontmatter=d.get("strip_frontmatter", False),
        confab_confidence_threshold=d.get("confab_confidence_threshold", 0.5),
        exo_base=exo_base, ollama_base=ollama_base,
        raw=d,
    )
