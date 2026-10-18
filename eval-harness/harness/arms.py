"""Assemble the system prompt for each arm from the kit on disk (read-only)."""
from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import json

from .contract import CONTRACT_INSTRUCTION, strip_thinking

_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.S)
_DESC_RE = re.compile(r"^description:\s*(.+)$", re.M | re.I)
# PREREG-001 H3 (Doc): skills as tools in quick-use slots, activated by a forced gate. Step 1 sees only the
# index and must name the skills it needs; step 2 answers with master + exactly those skills loaded.
GATE_INSTRUCTION = """SKILL GATE (step 1 of 2). Do NOT answer the user's message yet.
Below is an index of skills. Choose the skills you must load to answer the user's message truthfully and
accurately, at most {k}. Use [] if none apply.
Reply with ONLY this JSON object: {{"load": [<skill name>, ...]}}

SKILL INDEX:
{index}"""
CHARS_PER_TOKEN_EST = 4.0  # crude heuristic; labeled *_est everywhere. Real counts come from backends.


@dataclass
class Arm:
    id: str
    type: str
    files: List[Path] = field(default_factory=list)
    system_prompt: str = ""
    kit_chars: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def kit_tokens_est(self) -> int:
        return round(self.kit_chars / CHARS_PER_TOKEN_EST)


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _kit_commit(root: Path) -> Optional[str]:
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001 - not a git checkout; recorded as None
        return None


def master_prompt_path(root: Path) -> Path:
    found = sorted((root / "master-prompt").glob("*.md"))
    if len(found) != 1:
        raise FileNotFoundError(f"expected exactly 1 master prompt in {root/'master-prompt'}, found {len(found)}")
    return found[0]


def skill_paths(root: Path) -> Dict[str, Path]:
    return {p.stem: p for p in sorted((root / "skills").glob("*.md"))}


def _resolve_skill(root: Path, name: str) -> Path:
    p = Path(name)
    if p.suffix == ".md" and (p.is_absolute() or (root / p).exists()):
        return p if p.is_absolute() else root / p
    skills = skill_paths(root)
    if name not in skills:
        raise KeyError(f"skill {name!r} not found in {root/'skills'}; have {sorted(skills)}")
    return skills[name]


def _read(path: Path, strip_frontmatter: bool) -> str:
    text = path.read_text(encoding="utf-8")
    return _FRONTMATTER_RE.sub("", text, count=1) if strip_frontmatter else text


def skill_description(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    fm = _FRONTMATTER_RE.match(text)
    m = _DESC_RE.search(fm.group(0)) if fm else None
    if m:
        return m.group(1).strip()
    body = _FRONTMATTER_RE.sub("", text, count=1).strip().splitlines()
    return body[0].lstrip("# ").strip() if body else path.stem


def _assemble(root: Path, files: List[Path], strip_frontmatter: bool) -> str:
    parts = []
    for f in files:
        label = "MASTER PROMPT" if f.parent.name == "master-prompt" else "SKILL"
        parts.append(f"===== {label}: {f.relative_to(root) if f.is_relative_to(root) else f} =====\n"
                     + _read(f, strip_frontmatter).strip())
    return "\n\n".join(parts)


def _make(root: Path, commit: Optional[str], strip_frontmatter: bool, arm_id: str, typ: str,
          files: List[Path]) -> Arm:
    kit = _assemble(root, files, strip_frontmatter) if files else ""
    sp = (kit + "\n\n" + CONTRACT_INSTRUCTION) if kit else CONTRACT_INSTRUCTION
    return Arm(id=arm_id, type=typ, files=files, system_prompt=sp, kit_chars=len(kit),
               meta={"kit_commit": commit, "strip_frontmatter": strip_frontmatter,
                     "system_prompt_sha256": sha256(sp),
                     "files": [{"path": str(f.relative_to(root)) if f.is_relative_to(root) else str(f),
                                "sha256": sha256(f.read_text(encoding="utf-8"))} for f in files]})


def prompt_chars(arm: Arm) -> int:
    """Largest system prompt this arm can send (gated_kit grows after the gate), for context sizing."""
    return max(len(arm.system_prompt), int(arm.meta.get("max_prompt_chars") or 0))


def gated_answer_arm(arm: Arm, stems: List[str]) -> Arm:
    root = Path(arm.meta["root"])
    files = [master_prompt_path(root)] + [Path(arm.meta["gate_skills"][s]) for s in stems]
    out = _make(root, arm.meta["kit_commit"], arm.meta["strip_frontmatter"], arm.id, arm.type, files)
    out.meta.update({k: v for k, v in arm.meta.items() if k.startswith("gate_") or k in ("root", "max_prompt_chars")})
    return out


def parse_gate(text: str, known: List[str], k: int) -> Dict[str, Any]:
    """Strict: only a JSON object with a list under "load" counts. Unknown names and names past the limit are
    dropped but recorded, so a sloppy gate is measured, not silently repaired."""
    out: Dict[str, Any] = {"gate_parse_ok": False, "selected": [], "unknown": [], "over_limit": []}
    for m in re.finditer(r"\{[^{}]*\}", strip_thinking(text or "")):
        try:
            d = json.loads(m.group(0))
        except ValueError:
            continue
        if isinstance(d, dict) and isinstance(d.get("load"), list):
            out["gate_parse_ok"] = True
            for raw in d["load"]:
                n = str(raw).strip()
                n = n[:-3] if n.endswith(".md") else n
                if n not in known:
                    out["unknown"].append(n)
                elif n in out["selected"] or n in out["over_limit"]:
                    continue
                elif len(out["selected"]) < k:
                    out["selected"].append(n)
                else:
                    out["over_limit"].append(n)
            break
    return out


def build_arms(root: Path, arm_specs: List[Dict[str, Any]], strip_frontmatter: bool = False) -> List[Arm]:
    """Arm spec types:
      {"type":"vanilla"}
      {"type":"full_kit"}                       master + every skills/*.md
      {"type":"master_only"}
      {"type":"single_skill","skills":"all"}    expands to one arm per skill
      {"type":"single_skill","skills":["sophistry-refusal", ...]}
      {"type":"lean_kit","name":"lean1","skills":[...]}
      {"type":"gated_kit","max_skills":3}        master + skill index; skills loaded per item by a forced gate
    single_skill / lean_kit accept "include_master": bool (default false).
    Skills may be given by stem name or by .md path (relative to kit_root or absolute).
    """
    root = Path(root)
    commit = _kit_commit(root)
    mp = master_prompt_path(root)
    all_skills = list(skill_paths(root).values())
    arms: List[Arm] = []

    def make(arm_id: str, typ: str, files: List[Path]) -> Arm:
        return _make(root, commit, strip_frontmatter, arm_id, typ, files)

    for spec in arm_specs:
        t = spec["type"]
        if t == "vanilla":
            arms.append(make(spec.get("name", "vanilla"), t, []))
        elif t == "full_kit":
            arms.append(make(spec.get("name", "full_kit"), t, [mp] + all_skills))
        elif t == "master_only":
            arms.append(make(spec.get("name", "master_only"), t, [mp]))
        elif t == "single_skill":
            names = spec.get("skills", "all")
            paths = all_skills if names == "all" else [_resolve_skill(root, n) for n in names]
            for p in paths:
                files = ([mp] if spec.get("include_master") else []) + [p]
                prefix = "single+master:" if spec.get("include_master") else "single:"
                arms.append(make(prefix + p.stem, t, files))
        elif t == "lean_kit":
            if "name" not in spec:
                raise ValueError("lean_kit arm needs a 'name'")
            files = ([mp] if spec.get("include_master") else []) + [_resolve_skill(root, n) for n in spec["skills"]]
            arms.append(make("lean:" + spec["name"], t, files))
        elif t == "gated_kit":
            k = int(spec.get("max_skills", 3))
            index = "\n".join(f"- {p.stem}: {skill_description(p)}" for p in all_skills)
            a = make(spec.get("name", "gated_kit"), t, [mp])
            biggest = sorted((len(_read(p, strip_frontmatter)) for p in all_skills), reverse=True)[:k]
            a.meta.update({"gate_system": GATE_INSTRUCTION.format(k=k, index=index), "gate_max_skills": k,
                           "gate_skills": {p.stem: str(p) for p in all_skills}, "root": str(root),
                           "max_prompt_chars": len(a.system_prompt) + sum(biggest) + 200 * k})
            arms.append(a)
        else:
            raise ValueError(f"unknown arm type {t!r}")
    ids = [a.id for a in arms]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise ValueError(f"duplicate arm ids {sorted(dup)}")
    return arms
