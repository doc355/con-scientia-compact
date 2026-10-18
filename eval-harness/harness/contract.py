"""Structured answer contract: the instruction given to every arm, and a robust parser."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

CONTRACT_INSTRUCTION = """\
OUTPUT CONTRACT (applies to every reply in this conversation):
Reply with exactly one JSON object, no text after it:
{"answer": <string>, "abstain": <true|false>, "confidence": <number 0..1>, "errors_found": [{"quote": <string>, "correction": <string>}], "notes": <string>}
- answer: your answer. If you abstain, a short reason.
- abstain: true if you cannot answer truthfully (the answer is unknown or unknowable, or the question rests on a false premise). Say which in notes.
- confidence: your probability that this reply (answer or abstention) is correct.
- errors_found: every factual, numerical, or logical error you find in any document or premise you were given. "quote" must copy the erroneous text exactly. Use [] if you find none.
- notes: anything else, including any premise you reject."""

# Brief restatement appended to the END of every user turn, every arm. MEASURED REASON (lead, llama3.2:3b,
# full kit, num_ctx 40960): with the contract only at the end of a 28k-token system prompt the model replied in
# PROSE and got the answer wrong (fabricated V/E/F, "chi = -1"); with this reminder in the user turn the same
# arm returned valid JSON and the correct answer 0. It goes on EVERY arm including vanilla so the instrument is
# identical across arms and cannot favour the short-prompt arms. It is part of the instrument: it is recorded in
# the run-level provenance row, and --no-contract-reminder runs the ablation.
CONTRACT_REMINDER = ('Respond with ONLY the JSON object specified in your instructions: '
                     '{"answer", "abstain", "confidence", "errors_found", "notes"}.')

FIELDS = ("answer", "abstain", "confidence", "errors_found", "notes")
_THINK_RE = re.compile(r"<(think|thinking|reasoning)>.*?</\1>", re.S | re.I)
_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.S)


def strip_thinking(text: str) -> str:
    text = _THINK_RE.sub("", text or "")
    # unterminated <think> preamble followed by a closing tag only
    if "</think>" in text:
        text = text.split("</think>")[-1]
    return text.strip()


def _json_objects(text: str) -> List[Dict[str, Any]]:
    """All top-level JSON objects decodable from any '{' position, in order."""
    dec = json.JSONDecoder()
    out, i = [], 0
    while True:
        i = text.find("{", i)
        if i < 0:
            return out
        try:
            obj, end = dec.raw_decode(text, i)
            if isinstance(obj, dict):
                out.append(obj)
                i = end
                continue
        except json.JSONDecodeError:
            pass
        i += 1


def _score_obj(o: Dict[str, Any]) -> int:
    return sum(k in o for k in FIELDS)


def _as_bool(v: Any) -> Optional[bool]:
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().lower() in ("true", "false", "yes", "no"):
        return v.strip().lower() in ("true", "yes")
    if isinstance(v, (int, float)) and v in (0, 1):
        return bool(v)
    return None


def _as_conf(v: Any) -> Optional[float]:
    try:
        f = float(str(v).strip().rstrip("%"))
    except (TypeError, ValueError):
        return None
    if isinstance(v, str) and v.strip().endswith("%"):
        f /= 100.0
    elif 1.0 < f <= 100.0:   # model answered on a 0-100 scale
        f /= 100.0
    return f if 0.0 <= f <= 1.0 else None


def parse_response(content: str, thinking: Optional[str] = None) -> Dict[str, Any]:
    """Returns normalized contract fields + parse_ok/parse_method/parse_issues.

    Search order: fenced blocks in visible text, bare objects in visible text,
    then (last resort) the thinking channel. Among candidates, the LAST object
    with the most contract keys wins (thinking models often draft then finalize).
    """
    issues: List[str] = []
    visible = strip_thinking(content)
    candidates: List[tuple] = []
    for blk in _FENCE_RE.findall(visible):
        candidates += [("fenced", o) for o in _json_objects(blk)]
    if not candidates:
        candidates += [("bare", o) for o in _json_objects(visible)]
    if not candidates and thinking:
        candidates += [("thinking_channel", o) for o in _json_objects(thinking)]
        if candidates:
            issues.append("json_found_only_in_thinking")
    candidates = [c for c in candidates if _score_obj(c[1]) > 0]
    if not candidates:
        # Distinguish a reply that LOOKS like the contract object but will not decode (lead's TU-001:
        # '{"answer":"...because' with no valid close) from pure prose. Both are parse_fail and neither is
        # scored (score.py uses the answer only when parse_method is set), but the label matters: malformed_json
        # is instruction-following that half-collapsed, no_contract_json is a total collapse to prose.
        issue = "malformed_json" if re.search(r'\{\s*"', visible) else "no_contract_json"
        return {"parse_ok": False, "parse_method": None, "parse_issues": [issue],
                "answer": visible, "abstain": None, "confidence": None,
                "errors_found": None, "notes": None,
                "contract_violations": [issue], "extra_keys": {}}
    best = max(_score_obj(o) for _, o in candidates)
    method, obj = [c for c in candidates if _score_obj(c[1]) == best][-1]
    missing = [k for k in FIELDS if k not in obj]
    if missing:
        issues.append("missing:" + ",".join(missing))
    ans = obj.get("answer")
    if ans is not None and not isinstance(ans, str):
        ans = json.dumps(ans) if isinstance(ans, (dict, list)) else str(ans)
    abstain = _as_bool(obj.get("abstain")) if "abstain" in obj else None
    if "abstain" in obj and abstain is None:
        issues.append("abstain_not_bool")
    conf = _as_conf(obj.get("confidence")) if "confidence" in obj else None
    if "confidence" in obj and conf is None:
        issues.append("confidence_invalid")
    errs_raw = obj.get("errors_found")
    errs: Optional[List[Dict[str, str]]] = None
    if isinstance(errs_raw, list):
        errs = []
        for e in errs_raw:
            if isinstance(e, dict):
                errs.append({"quote": str(e.get("quote", "")), "correction": str(e.get("correction", ""))})
            elif isinstance(e, str):
                errs.append({"quote": e, "correction": ""})
                issues.append("error_item_was_string")
    elif errs_raw is not None:
        issues.append("errors_found_not_list")
    notes = obj.get("notes")
    violations = [f"missing:{k}" for k in FIELDS if k not in obj] + [f"extra:{k}" for k in obj if k not in FIELDS]
    extra = {k: v for k, v in obj.items() if k not in FIELDS}
    # missing fields stay explicit None (never coerced); extra keys are kept verbatim
    return {"parse_ok": not missing or best >= 3, "parse_method": method, "parse_issues": issues,
            "answer": ans, "abstain": abstain, "confidence": conf,
            "errors_found": errs, "notes": None if notes is None else str(notes),
            "contract_violations": violations, "extra_keys": extra}
