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

from .client import ModelSpec

REGISTRY_MODEL_KEYS = {"id", "backend", "lineage", "price_in", "price_out", "tier", "thinking", "needs_instance",
                       # harness extensions, optional:
                       "model", "num_ctx", "max_tokens", "think", "options", "timeout_s", "family", "system_role",
                       "api_key_env", "base_url", "price_cache_write", "price_cache_read", "prompt_cache",
                       "max_ctx", "num_ctx_default", "num_ctx_full_kit", "weights_gb", "kv_bytes_per_token",
                       "keep_alive"}
DEFAULT_NUM_CTX = 100000        # Doc's standing order; capped per model at max_ctx
TIMEOUT_FLOOR_LARGE_S = 300.0   # lead: >=300 s for large/thinking models (gpt-oss:20b measured 13-30 s/item vanilla)
DEFAULT_TIMEOUT_S = 600.0


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
        unknown = set(m) - REGISTRY_MODEL_KEYS
        if unknown:
            raise ValueError(f"registry model {m.get('id')}: unknown keys {sorted(unknown)}")
        be = m["backend"]
        if be not in ("ollama", "exo", "openai", "anthropic"):
            raise ValueError(f"registry model {m['id']}: backend must be ollama|exo|openai|anthropic, got {be!r}")
        base = m.get("base_url") or {"ollama": d.get("ollama_base"), "exo": d.get("exo_base")}.get(be)
        if not base:
            raise ValueError(f"registry model {m['id']}: no base url (set base_url, or ollama_base/exo_base)")
        spec = ModelSpec(
            id=m["id"], backend=be, base_url=base, model=m.get("model", m["id"]),
            family=m.get("family") or m["lineage"], lineage=m["lineage"],
            price_per_mtok_in=float(m.get("price_in", 0) or 0), price_per_mtok_out=float(m.get("price_out", 0) or 0),
            num_ctx=m.get("num_ctx", default_num_ctx), max_tokens=m.get("max_tokens", default_max_tokens),
            api_key_env=m.get("api_key_env"), timeout_s=timeout_for(m),
            options=m.get("options") or {}, system_role=m.get("system_role", True),
            tier=str(m.get("tier", "")), thinking=bool(m.get("thinking", False)), think=m.get("think"),
            needs_instance=bool(m.get("needs_instance", False)),
            price_per_mtok_cache_write=m.get("price_cache_write"), price_per_mtok_cache_read=m.get("price_cache_read"),
            prompt_cache=bool(m.get("prompt_cache", False)), max_ctx=m.get("max_ctx"),
            num_ctx_default=m.get("num_ctx_default"), num_ctx_full_kit=m.get("num_ctx_full_kit"),
            weights_gb=m.get("weights_gb"), kv_bytes_per_token=m.get("kv_bytes_per_token"),
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
    return Config(
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
