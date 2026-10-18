"""Battery loading, normalization and validation. One JSON object per line (JSONL).

Lead's schema (v1.0):
  id, category, prompt, answer_key, accept_patterns[regex], forbidden_patterns[regex],
  planted_errors[{quote, correction}], difficulty, source, notes
v1.1 optional additions:
  context (str, prepended to the user prompt), requires_context (bool),
  answer_numeric (number) + tolerance (number, absolute)
Harness extensions (optional, all categories): document (str), pressure_turns [str]
(extra user turns for multi-turn sycophancy), planted_errors[].id / .match [regex].
Unknown fields are kept and ignored. Lines starting with // are comments.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

CATEGORIES = ("factual_keyed", "trap_unanswerable", "sycophancy_pressure", "seeded_error_doc", "clean_control")


def normalize_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    it = dict(raw)
    it["accept_patterns"] = list(raw.get("accept_patterns") or [])
    it["forbidden_patterns"] = list(raw.get("forbidden_patterns") or [])
    it["pressure_turns"] = list(raw.get("pressure_turns") or [])
    pe = []
    for i, e in enumerate(raw.get("planted_errors") or []):
        if isinstance(e, str):
            e = {"quote": e, "correction": ""}
        pe.append({"id": str(e.get("id") or f"pe{i}"), "quote": str(e.get("quote") or ""),
                   "correction": str(e.get("correction") or ""), "match": list(e.get("match") or [])})
    it["planted_errors"] = pe
    rc = raw.get("requires_context")
    it["requires_context"] = bool(rc) if rc is not None else None
    return it


def validate_item(it: Dict[str, Any]) -> List[str]:
    p: List[str] = []
    for k in ("id", "category", "prompt"):
        if not it.get(k):
            p.append(f"missing {k}")
    c = it.get("category")
    if c not in CATEGORIES:
        p.append(f"bad category {c!r}")
    for fld in ("accept_patterns", "forbidden_patterns"):
        for rx in it.get(fld) or []:
            try:
                re.compile(rx)
            except re.error as e:
                p.append(f"{fld} regex {rx!r} invalid: {e}")
    if it.get("answer_numeric") is not None:
        try:
            float(it["answer_numeric"]); float(it.get("tolerance") or 0)
        except (TypeError, ValueError):
            p.append("answer_numeric/tolerance not numeric")
    if c == "factual_keyed" and it.get("answer_key") in (None, "") and it.get("answer_numeric") is None \
            and not it.get("accept_patterns"):
        p.append("factual_keyed needs answer_numeric, accept_patterns, or answer_key")
    if c == "seeded_error_doc" and not it.get("planted_errors"):
        p.append("seeded_error_doc needs planted_errors")
    if c == "seeded_error_doc":
        for e in it["planted_errors"]:
            if not e["quote"]:
                p.append(f"planted_error {e['id']} has empty quote")
    if c == "clean_control" and it.get("planted_errors"):
        p.append("clean_control must not have planted_errors")
    if it.get("requires_context") and not it.get("context"):
        p.append("requires_context=true but no context")
    return p


def load_battery(path: str | Path) -> List[Dict[str, Any]]:
    items, problems, seen = [], [], set()
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("//"):
            continue
        try:
            it = normalize_item(json.loads(line))
        except (json.JSONDecodeError, AttributeError) as e:
            problems.append(f"line {n}: invalid JSON object: {e}")
            continue
        for pr in validate_item(it):
            problems.append(f"line {n} ({it.get('id')}): {pr}")
        if it.get("id") in seen:
            problems.append(f"line {n}: duplicate id {it.get('id')}")
        seen.add(it.get("id"))
        items.append(it)
    if problems:
        raise ValueError("battery invalid:\n  " + "\n  ".join(problems))
    return items


def first_user_message(it: Dict[str, Any]) -> str:
    parts = []
    if it.get("context"):
        parts.append(f"CONTEXT START\n{it['context']}\nCONTEXT END")
    parts.append(it["prompt"])
    if it.get("document"):
        parts.append(f"DOCUMENT START\n{it['document']}\nDOCUMENT END")
    return "\n\n".join(parts)
