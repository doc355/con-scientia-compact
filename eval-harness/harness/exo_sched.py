"""exo memory scheduler. exo has no shared pool: each instance reserves its own RAM until deleted.

Policy (lead): ONE exo model resident at a time. place -> run every item for all its arms -> evict -> next.
No mid-block rebalancing (reloading 65-114 GiB dominates the clock).

  free_ram()                 GET /state, sum nodeMemory[*].ramAvailable (per node + total)
  ensure_resident(model, ctx) previews check -> weights + KV estimate + margin <= free -> POST /place_instance
                             -> poll /state until ready (default 20 min) -> instance_id
  evict(instance_id)         DELETE /instance/{id}, confirm it is gone from /state
  block(spec, ctx)           context manager: ensure_resident ... yield BlockMonitor ... evict (always)
  BlockMonitor.sample()      after each call: RAM used by the block vs weights + kill_factor x KV estimate;
                             over the line -> raises KVEstimateInvalid (abort block, do not OOM the cluster)

VERIFIED by the lead on the live cluster: nodeMemory = {peer_id: {"ramTotal": {"inBytes": N},
  "ramAvailable": {"inBytes": N}, ...}}; previews[].instance.MlxRingInstance.instanceId; a preview with
  instance == null or a non-empty "error" ("No cycles found with sufficient memory") = no valid placement.
ASSUMED: the ready predicate (see exo.ready_instances_runners); raw /state is logged once on first placement.
Every place/evict/sample is logged (timestamp, free RAM before/after, load seconds).
"""
from __future__ import annotations

import time
import urllib.parse
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

from .exo import (DEFAULT_READY_TOKENS, _find_instance_id, _http, default_ready, instance_ids_in_state,
                   preview_instance_ids, ready_instances_runners)

GIB = 1024 ** 3   # all RAM/weights/KV figures are GiB (exo reports raw bytes)


class InsufficientMemory(RuntimeError):
    pass


class KVEstimateInvalid(RuntimeError):
    pass


NOT_RESIDENT_MARKER = "No instance found for model"      # verified: HTTP 404 body from a chat call


def is_not_resident_error(err: Optional[str]) -> bool:
    """Authoritative 'model has no instance' signal: HTTP 404 {"error":{"message":"No instance found ..."}}."""
    return bool(err) and ("404" in err or "Not Found" in err) and NOT_RESIDENT_MARKER.lower() in err.lower()


def _bytes(v: Any) -> Optional[float]:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict):
        for k in ("inBytes", "in_bytes", "bytes"):
            if isinstance(v.get(k), (int, float)):
                return float(v[k])
    return None


def ram_from_state(state: Any) -> Dict[str, Any]:
    nm = state.get("nodeMemory") if isinstance(state, dict) else None
    if nm is None:
        return {"per_node_free_gib": {}, "total_free_gib": None, "total_ram_gib": None, "measured": False}
    items = nm.items() if isinstance(nm, dict) else enumerate(nm)
    free, total = {}, {}
    for nid, info in items:
        if not isinstance(info, dict):
            continue
        a, t = _bytes(info.get("ramAvailable")), _bytes(info.get("ramTotal"))
        if a is not None:
            free[str(nid)] = a / GIB
        if t is not None:
            total[str(nid)] = t / GIB
    return {"per_node_free_gib": {k: round(v, 2) for k, v in free.items()},
            "total_free_gib": round(sum(free.values()), 2) if free else None,
            "total_ram_gib": round(sum(total.values()), 2) if total else None,
            "measured": bool(free)}


class BlockMonitor:
    def __init__(self, sched: "ExoScheduler", spec, num_ctx: int, free_before_gib: Optional[float]):
        self.sched, self.spec, self.num_ctx = sched, spec, num_ctx
        self.free_before = free_before_gib
        self.peak_used_gib: Optional[float] = None
        self.kv_est_gib = sched.kv_estimate_gib(spec, num_ctx)
        self.limit_gib = (None if spec.weights_gib is None or self.kv_est_gib is None
                         else spec.weights_gib + sched.kill_factor * self.kv_est_gib)

    def sample(self) -> Dict[str, Any]:
        r = self.sched.free_ram()
        used = None if (self.free_before is None or r["total_free_gib"] is None) else self.free_before - r["total_free_gib"]
        if used is not None:
            self.peak_used_gib = used if self.peak_used_gib is None else max(self.peak_used_gib, used)
        ev = {"event": "sample", "model_id": self.spec.id, "used_gib": None if used is None else round(used, 2),
              "peak_used_gib": None if self.peak_used_gib is None else round(self.peak_used_gib, 2),
              "limit_gib": self.limit_gib, "free_gib": r["total_free_gib"]}
        if used is not None and self.limit_gib is not None and used > self.limit_gib:
            self.sched._event(**ev, verdict="kv_estimate_invalid")
            raise KVEstimateInvalid(f"{self.spec.id}: observed {used:.1f} GiB > weights {self.spec.weights_gib} GiB "
                                    f"+ {self.sched.kill_factor} x KV est {self.kv_est_gib:.2f} GiB")
        return ev


class ExoScheduler:
    def __init__(self, exo_base: str, log_writer=None, http: Callable = _http, poll_s: float = 10.0,
                 ready_timeout_s: float = 1200.0, evict_timeout_s: float = 300.0, margin: float = 0.15,
                 kill_factor: float = 2.0, require_sizing: bool = True, ready_tokens=DEFAULT_READY_TOKENS,
                 ready_fn: Optional[Callable] = None, log=print, sleep: Callable = time.sleep,
                 state_log_once: bool = True, ready_probe: Optional[Callable] = None):
        self.base = exo_base.rstrip("/")
        self.w, self.http, self.log, self.sleep = log_writer, http, log, sleep
        self.poll_s, self.ready_timeout_s, self.evict_timeout_s = poll_s, ready_timeout_s, evict_timeout_s
        self.margin, self.kill_factor, self.require_sizing = margin, kill_factor, require_sizing
        self.tokens = tuple(ready_tokens)
        # Default predicate is the lead's instances+runners ASSUMPTION; ready_probe is the documented
        # fallback (a trial chat call that must not 404 "No instance found for model").
        self.ready_fn = ready_fn or ready_instances_runners
        self.ready_probe, self.state_log_once, self._state_logged = ready_probe, state_log_once, False
        self.resident: Optional[Dict[str, Any]] = None

    def _event(self, **kw):
        kw["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.log(f"[exo-sched] {kw}")
        if self.w:
            self.w.write(kw)

    def state(self) -> Any:
        return self.http("GET", self.base + "/state")

    def free_ram(self, state: Any = None) -> Dict[str, Any]:
        return ram_from_state(self.state() if state is None else state)

    @staticmethod
    def kv_estimate_gib(spec, num_ctx: int) -> Optional[float]:
        return None if spec.kv_bytes_per_token is None else spec.kv_bytes_per_token * num_ctx / GIB

    def ensure_resident(self, spec, num_ctx: int) -> str:
        mid = spec.model
        if self.resident and self.resident["model"] == mid:
            return self.resident["instance_id"]
        if self.resident:                                   # one exo model at a time
            self.evict(self.resident["instance_id"])
        st = self.state()
        before_ids, ram = instance_ids_in_state(st), ram_from_state(st)
        prev = self.http("GET", f"{self.base}/instance/previews?" + urllib.parse.urlencode({"model_id": mid}))
        offered = preview_instance_ids(prev)
        if not offered:   # every preview had instance==null or a non-empty error (or no instanceId)
            self._event(event="no_valid_placement", model_id=mid, previews=prev)
            raise InsufficientMemory(f"{mid}: no valid placement in /instance/previews")
        kv = self.kv_estimate_gib(spec, num_ctx)
        projected = None if spec.weights_gib is None else (spec.weights_gib + (kv or 0)) * (1 + self.margin)
        if projected is None or kv is None or ram["total_free_gib"] is None:
            msg = (f"{mid}: memory check not computable (weights_gib={spec.weights_gib}, kv_est_gib={kv}, "
                   f"free_gib={ram['total_free_gib']})")
            self._event(event="memory_check_not_computable", model_id=mid, detail=msg)
            if self.require_sizing:
                raise InsufficientMemory(msg)
        elif projected > ram["total_free_gib"]:
            self._event(event="refused_insufficient_ram", model_id=mid, projected_gib=round(projected, 2),
                        free_gib=ram["total_free_gib"])
            raise InsufficientMemory(f"{mid}: projected {projected:.1f} GiB > free {ram['total_free_gib']} GiB")
        t0 = time.perf_counter()
        resp = self.http("POST", self.base + "/place_instance", {"model_id": mid})
        iid = _find_instance_id(resp) or (preview_instance_ids(resp) or offered or [None])[0]
        ready = False
        while time.perf_counter() - t0 < self.ready_timeout_s:
            st = self.state()
            if iid is None:
                new = instance_ids_in_state(st) - before_ids
                if len(new) == 1:
                    iid = new.pop()
            if self.state_log_once and not self._state_logged:
                self._state_logged = True     # raw /state once, so the predicate can be corrected from real data
                self._event(event="state_raw_first_placement", model_id=mid, instance_id=iid, state=st)
            if self.ready_fn(st, mid, iid, self.tokens) or default_ready(st, mid, iid, self.tokens) or (
                    self.ready_probe is not None and self.ready_probe(mid, iid)):
                ready = True
                break
            self.sleep(self.poll_s)
        after = ram_from_state(self.state())
        load_s = round(time.perf_counter() - t0, 2)
        self._event(event="placed" if ready else "place_timeout", model_id=mid, instance_id=iid, load_s=load_s,
                    free_before_gib=ram["total_free_gib"], free_after_gib=after["total_free_gib"],
                    per_node_free_after_gib=after["per_node_free_gib"], projected_gib=projected)
        if not ready:
            if iid:
                self.evict(iid)
            raise TimeoutError(f"{mid}: not ready after {self.ready_timeout_s}s")
        self.resident = {"model": mid, "instance_id": iid, "free_before_gib": ram["total_free_gib"], "load_s": load_s}
        return iid

    def evict(self, instance_id: str) -> bool:
        before = self.free_ram()
        t0 = time.perf_counter()
        self.http("DELETE", f"{self.base}/instance/{instance_id}")
        gone = False
        while time.perf_counter() - t0 < self.evict_timeout_s:
            st = self.state()
            if instance_id not in instance_ids_in_state(st):
                gone = True
                break
            self.sleep(self.poll_s)
        after = self.free_ram()
        self._event(event="evicted" if gone else "evict_unconfirmed", instance_id=instance_id,
                    free_before_gib=before["total_free_gib"], free_after_gib=after["total_free_gib"],
                    evict_s=round(time.perf_counter() - t0, 2))
        if self.resident and self.resident["instance_id"] == instance_id:
            self.resident = None
        return gone

    @contextmanager
    def block(self, spec, num_ctx: int):
        iid = self.ensure_resident(spec, num_ctx)
        mon = BlockMonitor(self, spec, num_ctx, self.resident["free_before_gib"])
        try:
            yield mon
        finally:
            self._event(event="block_end", model_id=spec.id, instance_id=iid,
                        peak_used_gib=None if mon.peak_used_gib is None else round(mon.peak_used_gib, 2),
                        limit_gib=mon.limit_gib)
            self.evict(iid)


def ollama_keep_alive(base_url: str, model: str, keep_alive, http: Callable = _http) -> Any:
    """POST /api/generate with no prompt: loads (keep_alive='60m') or releases (keep_alive=0) a model."""
    return http("POST", base_url.rstrip("/") + "/api/generate", {"model": model, "keep_alive": keep_alive})
