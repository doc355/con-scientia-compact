"""One chat() interface over two backends: Ollama native and OpenAI-compatible.

Every number recorded here comes from the backend response or from a wall clock.
Nothing is estimated in this module; missing fields stay None.
"""
from __future__ import annotations

import json
import subprocess
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional

Message = Dict[str, str]


@dataclass
class ModelSpec:
    id: str                       # harness-wide unique id, e.g. "qwen3-8b@ollama-box1"
    backend: str                  # "ollama" | "openai" | "exo" (OpenAI-compatible) | "anthropic" (Messages API)
    base_url: str                 # "http://HOST:11434" or "http://HOST:52415" or "https://api.x.com"
    model: str                    # name the backend expects
    family: str                   # e.g. "qwen", "llama", "gemma", "gpt", "claude"
    lineage: str = ""             # optional finer/coarser grouping, e.g. "alibaba", "meta"
    price_per_mtok_in: float = 0.0
    price_per_mtok_out: float = 0.0
    num_ctx: Optional[int] = None         # Ollama only; Ollama truncates silently past this
    max_tokens: Optional[int] = None      # completion cap (num_predict for Ollama)
    api_key_env: Optional[str] = None     # env var holding the key (never the key itself)
    timeout_s: float = 600.0
    options: Dict[str, Any] = field(default_factory=dict)  # extra backend options
    system_role: bool = True              # False -> system prompt is prepended to first user msg
    tier: str = ""                        # registry metadata, carried into results
    thinking: bool = False                # registry metadata: model emits reasoning
    think: Optional[bool] = None          # Ollama top-level "think" param; sent only if set
    needs_instance: bool = False          # exo: place/delete an instance around this model's runs
    price_per_mtok_cache_write: Optional[float] = None   # provider prompt caching prices (per MTok)
    price_per_mtok_cache_read: Optional[float] = None
    prompt_cache: bool = False            # anthropic: cache_control ephemeral on the system block
    num_ctx_default: Optional[int] = None  # registry: target num_ctx for non-full-kit arms (capped at max_ctx)
    num_ctx_full_kit: Optional[int] = None # registry: target num_ctx for full_kit
    weights_gib: Optional[float] = None   # GiB    # exo scheduler: resident weight size
    kv_bytes_per_token: Optional[float] = None  # exo scheduler: KV-cache estimate (lead-supplied, may be ASSUMED)
    keep_alive: Optional[str] = None      # ollama: hold model loaded for the block
    max_ctx: Optional[int] = None         # model max context override (else /api/show for ollama)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ModelSpec":
        known = set(ModelSpec.__dataclass_fields__)
        unknown = set(d) - known
        if unknown:
            raise ValueError(f"model {d.get('id')}: unknown keys {sorted(unknown)}")
        return ModelSpec(**d)

    def cost_usd(self, prompt_tokens: Optional[int], completion_tokens: Optional[int]) -> Optional[float]:
        if prompt_tokens is None or completion_tokens is None:
            return None
        return (prompt_tokens * self.price_per_mtok_in + completion_tokens * self.price_per_mtok_out) / 1e6

    def cost_breakdown(self, r: "ChatResult") -> Dict[str, Optional[float]]:
        """prompt_tokens is TOTAL input incl. cache writes/reads. Returns cost with caching as billed,
        and as-if-uncached (all input at price_in). None where a needed count or price is missing."""
        if r.prompt_tokens is None or r.completion_tokens is None:
            return {"cost_usd": None, "cost_uncached_usd": None}
        uncached = self.cost_usd(r.prompt_tokens, r.completion_tokens)
        cw, cr = r.cache_creation_input_tokens or 0, r.cache_read_input_tokens or 0
        if not (cw or cr):
            return {"cost_usd": uncached, "cost_uncached_usd": uncached}
        p_cw = self.price_per_mtok_cache_write
        p_cr = self.price_per_mtok_cache_read
        if (cw and p_cw is None) or (cr and p_cr is None):
            return {"cost_usd": None, "cost_uncached_usd": uncached}  # never invent a cache price
        plain = r.prompt_tokens - cw - cr
        cost = (plain * self.price_per_mtok_in + cw * (p_cw or 0) + cr * (p_cr or 0)
                + r.completion_tokens * self.price_per_mtok_out) / 1e6
        return {"cost_usd": cost, "cost_uncached_usd": uncached}


@dataclass
class ChatResult:
    content: str = ""
    thinking: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_s: Optional[float] = None            # wall clock, request start -> response parsed
    backend_timing: Dict[str, Any] = field(default_factory=dict)  # raw backend timing fields
    finish_reason: Optional[str] = None
    error: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None
    prompt_eval_duration_ns: Optional[int] = None    # ollama only
    thinking_tokens: Optional[int] = None            # only when the backend reports it separately
                                                     # (Ollama counts thinking INSIDE eval_count)
    cache_creation_input_tokens: Optional[int] = None
    cache_read_input_tokens: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


ChatFn = Callable[[ModelSpec, List[Message]], ChatResult]


def _post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: float) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fold_system(messages: List[Message]) -> List[Message]:
    """For models without a system role: prepend system text to the first user message."""
    sys_parts = [m["content"] for m in messages if m["role"] == "system"]
    rest = [dict(m) for m in messages if m["role"] != "system"]
    if sys_parts and rest:
        rest[0]["content"] = "\n\n".join(sys_parts) + "\n\n---\n\n" + rest[0]["content"]
    return rest


def _chat_ollama(spec: ModelSpec, messages: List[Message], temperature: float) -> ChatResult:
    options: Dict[str, Any] = {"temperature": temperature, **spec.options}
    if spec.num_ctx:
        options["num_ctx"] = spec.num_ctx
    keep = {"keep_alive": spec.keep_alive} if spec.keep_alive is not None else {}
    if spec.max_tokens:
        options["num_predict"] = spec.max_tokens
    payload: Dict[str, Any] = {"model": spec.model, "messages": messages, "stream": False, "options": options, **keep}
    if spec.think is not None:
        payload["think"] = spec.think
    t0 = time.perf_counter()
    body = _post_json(spec.base_url.rstrip("/") + "/api/chat", payload, {}, spec.timeout_s)
    latency = time.perf_counter() - t0
    msg = body.get("message") or {}
    timing_keys = ("total_duration", "load_duration", "prompt_eval_count", "prompt_eval_duration",
                   "eval_count", "eval_duration")
    return ChatResult(
        content=msg.get("content") or "",
        thinking=msg.get("thinking"),
        prompt_tokens=body.get("prompt_eval_count"),
        completion_tokens=body.get("eval_count"),
        latency_s=latency,
        backend_timing={k: body.get(k) for k in timing_keys},  # durations in nanoseconds
        finish_reason=body.get("done_reason"),
        raw=body,
        prompt_eval_duration_ns=body.get("prompt_eval_duration"),
    )


def _chat_openai(spec: ModelSpec, messages: List[Message], temperature: float) -> ChatResult:
    headers = {}
    if spec.api_key_env:
        key = os.environ.get(spec.api_key_env)
        if not key:
            raise RuntimeError(f"env var {spec.api_key_env} not set for model {spec.id}")
        headers["Authorization"] = f"Bearer {key}"
    payload: Dict[str, Any] = {"model": spec.model, "messages": messages,
                               "temperature": temperature, "stream": False, **spec.options}
    if spec.max_tokens:
        payload["max_tokens"] = spec.max_tokens
    base = spec.base_url.rstrip("/")
    url = base + ("/chat/completions" if base.endswith("/v1") else "/v1/chat/completions")
    t0 = time.perf_counter()
    body = _post_json(url, payload, headers, spec.timeout_s)
    latency = time.perf_counter() - t0
    choice = (body.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    usage = body.get("usage") or {}
    return ChatResult(
        content=msg.get("content") or "",
        thinking=msg.get("reasoning_content") or msg.get("reasoning"),
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        latency_s=latency,
        backend_timing={"usage": usage},
        finish_reason=choice.get("finish_reason"),
        raw=body,
        cache_read_input_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
        thinking_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
    )


def _chat_anthropic(spec: ModelSpec, messages: List[Message], temperature: float) -> ChatResult:
    """Native Anthropic Messages API. With spec.prompt_cache the system block carries
    cache_control: {"type": "ephemeral"}."""
    key = os.environ.get(spec.api_key_env or "ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(f"env var {spec.api_key_env or 'ANTHROPIC_API_KEY'} not set for model {spec.id}")
    system_text = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    sys_block: Dict[str, Any] = {"type": "text", "text": system_text}
    if spec.prompt_cache:
        sys_block["cache_control"] = {"type": "ephemeral"}
    payload: Dict[str, Any] = {"model": spec.model, "max_tokens": spec.max_tokens or 4096,
                               "temperature": temperature,
                               "messages": [m for m in messages if m["role"] != "system"], **spec.options}
    if system_text:
        payload["system"] = [sys_block]
    base = spec.base_url.rstrip("/")
    url = base + ("/messages" if base.endswith("/v1") else "/v1/messages")
    t0 = time.perf_counter()
    body = _post_json(url, payload, {"x-api-key": key, "anthropic-version": "2023-06-01"}, spec.timeout_s)
    latency = time.perf_counter() - t0
    blocks = body.get("content") or []
    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    think = "".join(b.get("thinking", "") for b in blocks if b.get("type") == "thinking") or None
    u = body.get("usage") or {}
    cw, cr = u.get("cache_creation_input_tokens"), u.get("cache_read_input_tokens")
    inp = u.get("input_tokens")
    total_in = None if inp is None else inp + (cw or 0) + (cr or 0)  # Anthropic input_tokens excludes cache
    return ChatResult(content=text, thinking=think, prompt_tokens=total_in, completion_tokens=u.get("output_tokens"),
                      latency_s=latency, backend_timing={"usage": u}, finish_reason=body.get("stop_reason"),
                      raw=body, cache_creation_input_tokens=cw, cache_read_input_tokens=cr)


def _chat_external(spec: ModelSpec, messages: List[Message], temperature: float) -> ChatResult:
    """An outside harness (e.g. a multi-model composite with its own gates) treated as one model.
    spec.options["cmd"] (argv list; request JSON on stdin) or spec.options["url"] (request JSON POSTed).
    Request: {"model", "messages", "temperature", "max_tokens"}. Reply JSON: {"content", optional "thinking",
    "prompt_tokens", "completion_tokens", "trace"}. The whole reply is kept in raw, so gate traces are recorded."""
    opts = dict(spec.options)
    cmd, url = opts.pop("cmd", None), opts.pop("url", None)
    req = {"model": spec.model, "messages": messages, "temperature": temperature,
           "max_tokens": spec.max_tokens, **opts}
    t0 = time.perf_counter()
    if cmd:
        p = subprocess.run(cmd, input=json.dumps(req), capture_output=True, text=True, timeout=spec.timeout_s)
        if p.returncode != 0:
            raise RuntimeError(f"external harness exit {p.returncode}: {p.stderr[-2000:]}")
        body = json.loads(p.stdout)
    elif url:
        body = _post_json(url, req, {}, spec.timeout_s)
    else:
        raise RuntimeError("external backend needs options.cmd or options.url")
    latency = time.perf_counter() - t0
    return ChatResult(content=body.get("content") or "", thinking=body.get("thinking"),
                      prompt_tokens=body.get("prompt_tokens"), completion_tokens=body.get("completion_tokens"),
                      latency_s=latency, backend_timing={"external": True}, finish_reason=body.get("finish_reason"),
                      raw=body)


def chat(spec: ModelSpec, messages: List[Message], temperature: float = 0.0,
         retries: int = 2, backoff_s: float = 5.0) -> ChatResult:
    """Never raises for transport/HTTP errors: returns ChatResult(error=...)."""
    msgs = messages if spec.system_role else _fold_system(messages)
    fn = {"ollama": _chat_ollama, "openai": _chat_openai, "exo": _chat_openai,
          "anthropic": _chat_anthropic, "external": _chat_external}.get(spec.backend)
    if fn is None:
        return ChatResult(error=f"unknown backend {spec.backend!r}")
    last_err = None
    for attempt in range(retries + 1):
        try:
            return fn(spec, msgs, temperature)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:2000]
            last_err = f"HTTP {e.code}: {detail}"
            if 400 <= e.code < 500 and e.code != 429:
                break
        except Exception as e:  # noqa: BLE001 - transport errors recorded, not hidden
            last_err = f"{type(e).__name__}: {e}"
        if attempt < retries:
            time.sleep(backoff_s * (attempt + 1))
    return ChatResult(error=last_err)
