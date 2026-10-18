"""exo instance lifecycle for registry models with needs_instance=true.

  POST   {exo_base}/place_instance  {"model_id": id}
  GET    {exo_base}/state           poll until a runner for that model is ready
  DELETE {exo_base}/instance/{instance_id}

The response shapes of these endpoints were NOT available to the harness author
(UNVERIFIED; see WRONG_IDEAS_LEDGER.md). So:
  * instance_id is taken from the POST response if it carries one of INSTANCE_ID_KEYS;
    otherwise it is found by diffing the instance ids present in /state before vs after.
  * "ready" = /state contains, inside the part of the state that mentions this instance id
    or model id, a status string/key from ready_tokens (configurable).
Every step is logged to lifecycle.jsonl with wall-clock timings (instance load time is a real cost).
Override any of this by passing ready_fn / instance_id_fn.
"""
from __future__ import annotations

import json
import time
import urllib.request
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, List, Optional, Set

INSTANCE_ID_KEYS = ("instance_id", "instanceId", "id")
DEFAULT_READY_TOKENS = ("RunnerReady", "RunnerRunning", "ready", "Ready", "READY", "running", "loaded", "RunnerLoaded")
INSTANCE_CONTAINER_KEYS = ("instances", "Instances")


def _http(method: str, url: str, payload: Optional[Dict[str, Any]] = None, timeout: float = 60.0) -> Any:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8", "replace")
    try:
        return json.loads(body) if body.strip() else None
    except json.JSONDecodeError:
        return body


def _walk(o: Any) -> Iterator[Any]:
    yield o
    if isinstance(o, dict):
        for k, v in o.items():
            yield k
            yield from _walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk(v)


def _mentions(o: Any, needle: str) -> bool:
    return any(isinstance(x, str) and needle in x for x in _walk(o))


def instance_ids_in_state(state: Any) -> Set[str]:
    ids: Set[str] = set()
    for x in _walk(state):
        if isinstance(x, dict):
            for ck in INSTANCE_CONTAINER_KEYS:
                c = x.get(ck)
                if isinstance(c, dict):
                    ids.update(str(k) for k in c)
                elif isinstance(c, list):
                    ids.update(str(e.get(k)) for e in c if isinstance(e, dict) for k in INSTANCE_ID_KEYS if e.get(k))
    return ids


def _find_instance_id(resp: Any) -> Optional[str]:
    if isinstance(resp, dict):
        for k in INSTANCE_ID_KEYS[:2]:
            if resp.get(k):
                return str(resp[k])
        for v in resp.values():
            if isinstance(v, dict):
                got = _find_instance_id(v)
                if got:
                    return got
        if resp.get("id"):
            return str(resp["id"])
    return None


def _subtrees_mentioning(state: Any, needle: str) -> List[Any]:
    """Dict subtrees that mention the needle (as a key or a string value), smallest first.
    The status for an instance usually sits in the subtree UNDER its id, which does not repeat
    the id itself, so the smallest mentioning subtree is the one to inspect."""
    out = [x for x in _walk(state) if isinstance(x, dict) and _mentions(x, needle)]
    return sorted(out, key=lambda x: len(json.dumps(x, default=str)))


def _dig(o: Any, path: str) -> Any:
    """Dotted path lookup, e.g. instance.MlxRingInstance.instanceId."""
    for part in path.split("."):
        if not isinstance(o, dict) or part not in o:
            return None
        o = o[part]
    return o


# Verified by the lead against the live cluster: GET /instance/previews?model_id=... ->
# {"previews":[{"instance":{"MlxRingInstance":{"instanceId": "<uuid>", ...}}}]}. Other instance_meta
# variants (e.g. a different wrapper key than MlxRingInstance) are tolerated by falling back to a scan.
PREVIEW_ID_PATHS = ("instance.MlxRingInstance.instanceId",)


def preview_instance_ids(previews: Any, paths=PREVIEW_ID_PATHS) -> list:
    """instanceIds offered by /instance/previews, in order. Configurable dotted paths, then a key scan."""
    plist = previews.get("previews") if isinstance(previews, dict) else previews
    out = []
    for pv in plist if isinstance(plist, list) else []:
        got = next((v for v in (_dig(pv, p) for p in paths) if isinstance(v, str)), None)
        if got is None:                       # unknown instance_meta variant: scan for an instanceId key
            got = next((x for x in _walk(pv) if isinstance(x, dict) and isinstance(x.get("instanceId"), str)), None)
            got = got and got["instanceId"]
        if got:
            out.append(got)
    return out


def ready_instances_runners(state: Any, model_id: str, instance_id: Optional[str], tokens=()) -> bool:
    """ASSUMPTION (lead has not yet observed a populated payload): ready = the instance id appears in
    state["instances"] AND its runner(s) appear in state["runners"]. Runner ids are taken from the instance's
    shardAssignments.runnerToShard keys when present (all must be in runners); without that, any runner
    entry mentioning the instance or model counts. Idle (verified) = both dicts empty. Override with ready_fn."""
    if not isinstance(state, dict):
        return False
    inst, runners = state.get("instances"), state.get("runners")
    if not isinstance(inst, dict) or not inst or not isinstance(runners, dict) or not runners:
        return False
    key = instance_id if (instance_id and instance_id in inst) else next(
        (k for k, v in inst.items() if _mentions({k: v}, model_id)), None)
    if key is None:
        return False
    r2s = next((x["runnerToShard"] for x in _walk(inst[key]) if isinstance(x, dict)
                and isinstance(x.get("runnerToShard"), dict)), None)
    if r2s:
        return all(r in runners for r in r2s)
    return any(_mentions({rk: rv}, key) or _mentions({rk: rv}, model_id) for rk, rv in runners.items())


def default_ready(state: Any, model_id: str, instance_id: Optional[str], tokens) -> bool:
    """True if the smallest /state subtree mentioning the instance (or model) carries a ready token
    anywhere inside it, as a key or a string value."""
    for needle in [n for n in (instance_id, model_id) if n]:
        for sub in _subtrees_mentioning(state, needle):
            if any(isinstance(x, str) and x in tokens for x in _walk(sub)):
                return True
    return False


class ExoLifecycle:
    def __init__(self, exo_base: str, log_writer=None, ready_tokens=DEFAULT_READY_TOKENS,
                 poll_s: float = 5.0, timeout_s: float = 1800.0, http: Callable = _http,
                 ready_fn: Optional[Callable] = None, log=print):
        self.base = exo_base.rstrip("/")
        self.w, self.tokens, self.poll_s, self.timeout_s = log_writer, tuple(ready_tokens), poll_s, timeout_s
        self.http, self.ready_fn, self.log = http, ready_fn, log

    def _event(self, **kw):
        kw["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.log(f"[exo] {kw}")
        if self.w:
            self.w.write(kw)

    @contextmanager
    def instance(self, model_id: str):
        t0 = time.perf_counter()
        before: Set[str] = set()
        try:
            before = instance_ids_in_state(self.http("GET", self.base + "/state"))
        except Exception as e:  # noqa: BLE001
            self._event(event="state_read_failed_before_place", model_id=model_id, error=str(e))
        resp = self.http("POST", self.base + "/place_instance", {"model_id": model_id})
        iid = _find_instance_id(resp)
        self._event(event="placed", model_id=model_id, instance_id=iid, response=resp)
        ready = False
        try:
            while time.perf_counter() - t0 < self.timeout_s:
                state = self.http("GET", self.base + "/state")
                if iid is None:
                    new = instance_ids_in_state(state) - before
                    if len(new) == 1:
                        iid = new.pop()
                        self._event(event="instance_id_from_state_diff", model_id=model_id, instance_id=iid)
                ok = (self.ready_fn or (lambda s, m, i: default_ready(s, m, i, self.tokens)))(state, model_id, iid)
                if ok:
                    ready = True
                    break
                time.sleep(self.poll_s)
            load_s = time.perf_counter() - t0
            self._event(event="ready" if ready else "ready_timeout", model_id=model_id, instance_id=iid,
                        load_s=round(load_s, 2))
            if not ready:
                raise TimeoutError(f"exo instance for {model_id} not ready after {self.timeout_s}s")
            yield {"instance_id": iid, "load_s": load_s}
        finally:
            if iid:
                try:
                    self.http("DELETE", f"{self.base}/instance/{iid}")
                    self._event(event="deleted", model_id=model_id, instance_id=iid,
                                total_s=round(time.perf_counter() - t0, 2))
                except Exception as e:  # noqa: BLE001 - reported, never swallowed silently
                    self._event(event="delete_failed", model_id=model_id, instance_id=iid, error=str(e))
            else:
                self._event(event="delete_skipped_no_instance_id", model_id=model_id,
                            note="instance may still be running on exo; check /state manually")


@contextmanager
def maybe_instance(spec, lifecycle: Optional[ExoLifecycle]):
    if spec.backend == "exo" and spec.needs_instance:
        if lifecycle is None:
            raise RuntimeError(f"{spec.id} needs_instance but no exo lifecycle configured (exo_base missing?)")
        with lifecycle.instance(spec.model) as info:
            yield info
    else:
        yield None
