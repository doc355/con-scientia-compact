"""Assemble the system prompt for each arm from the kit on disk (read-only)."""
from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .contract import CONTRACT_INSTRUCTION

_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.S)
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


def _assemble(root: Path, files: List[Path], strip_frontmatter: bool) -> str:
    parts = []
    for f in files:
        label = "MASTER PROMPT" if f.parent.name == "master-prompt" else "SKILL"
        parts.append(f"===== {label}: {f.relative_to(root) if f.is_relative_to(root) else f} =====\n"
                     + _read(f, strip_frontmatter).strip())
    return "\n\n".join(parts)


def build_arms(root: Path, arm_specs: List[Dict[str, Any]], strip_frontmatter: bool = False) -> List[Arm]:
    """Arm spec types:
      {"type":"vanilla"}
      {"type":"full_kit"}                       master + every skills/*.md
      {"type":"master_only"}
      {"type":"single_skill","skills":"all"}    expands to one arm per skill
      {"type":"single_skill","skills":["sophistry-refusal", ...]}
      {"type":"lean_kit","name":"lean1","skills":[...]}
    single_skill / lean_kit accept "include_master": bool (default false).
    Skills may be given by stem name or by .md path (relative to kit_root or absolute).
    """
    root = Path(root)
    commit = _kit_commit(root)
    mp = master_prompt_path(root)
    all_skills = list(skill_paths(root).values())
    arms: List[Arm] = []

    def make(arm_id: str, typ: str, files: List[Path]) -> Arm:
        kit = _assemble(root, files, strip_frontmatter) if files else ""
        sp = (kit + "\n\n" + CONTRACT_INSTRUCTION) if kit else CONTRACT_INSTRUCTION
        return Arm(id=arm_id, type=typ, files=files, system_prompt=sp, kit_chars=len(kit),
                   meta={"kit_commit": commit, "strip_frontmatter": strip_frontmatter,
                         "system_prompt_sha256": sha256(sp),
                         "files": [{"path": str(f.relative_to(root)) if f.is_relative_to(root) else str(f),
                                    "sha256": sha256(f.read_text(encoding="utf-8"))} for f in files]})

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
        else:
            raise ValueError(f"unknown arm type {t!r}")
    ids = [a.id for a in arms]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise ValueError(f"duplicate arm ids {sorted(dup)}")
    return arms
