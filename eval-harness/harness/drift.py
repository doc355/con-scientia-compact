"""Drift / rollback tracker: compare a candidate scored run against a baseline scored run, per item.
Usage: python -m harness.drift BASELINE_scored.jsonl CANDIDATE_scored.jsonl [--z 2.0] [--lat 1.25] [--cost 1.25]
Prints ROLL BACK or OK with the exact items/categories that moved. Never edits either file."""
import argparse, json, math, statistics, sys
from collections import defaultdict

def load(path):
    rows = {}
    for line in open(path, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("item_id") in (None, "canary") or r.get("status") == "canary":
            continue
        rows[(r.get("model_id"), r.get("arm_id"), r["item_id"], r.get("rep", 0))] = r
    return rows

def passed(r):
    v = r.get("correct")
    if v is None and r.get("outcome") is not None:
        v = r["outcome"] == "correct"
    return None if v is None else bool(v)

def confab(r):
    return r.get("outcome") in ("confabulated", "confident_wrong") or bool(r.get("confident_wrong"))

def two_prop_drop(p1, n1, p2, n2, z):
    if not n1 or not n2:
        return False, 0.0
    p = (p1 * n1 + p2 * n2) / (n1 + n2)
    se = math.sqrt(max(p * (1 - p), 1e-12) * (1 / n1 + 1 / n2))
    d = (p2 - p1) / se
    return d <= -z, d

def compare(base, cand, z=2.0, lat_ratio=1.25, cost_ratio=1.25):
    keys = sorted(set(base) & set(cand), key=str)
    missing = sorted(set(base) - set(cand), key=str)
    flips_down, flips_up = [], []
    groups = defaultdict(lambda: {"b": [], "c": [], "bconf": 0, "cconf": 0, "blat": [], "clat": [], "bcost": 0.0, "ccost": 0.0})
    for k in keys:
        b, c = base[k], cand[k]
        pb, pc = passed(b), passed(c)
        if pb is True and pc is False:
            flips_down.append(k)
        elif pb is False and pc is True:
            flips_up.append(k)
        g = groups[(k[0], k[1], b.get("category"))]
        if pb is not None and pc is not None:
            g["b"].append(pb); g["c"].append(pc)
        g["bconf"] += confab(b); g["cconf"] += confab(c)
        for side, r in (("b", b), ("c", c)):
            if isinstance(r.get("latency_s"), (int, float)):
                g[side + "lat"].append(r["latency_s"])
            g[side + "cost"] += float(r.get("cost_usd") or 0)
    flags = []
    for gk, g in sorted(groups.items(), key=str):
        n = len(g["b"])
        if n:
            drop, zz = two_prop_drop(sum(g["b"]) / n, n, sum(g["c"]) / n, n, z)
            if drop:
                flags.append(f"ACCURACY DROP {gk}: {sum(g['b'])}/{n} -> {sum(g['c'])}/{n} (z={zz:.2f})")
        if g["cconf"] > g["bconf"]:
            flags.append(f"CONFABULATION UP {gk}: {g['bconf']} -> {g['cconf']}")
        if g["blat"] and g["clat"] and statistics.median(g["clat"]) > lat_ratio * statistics.median(g["blat"]):
            flags.append(f"LATENCY UP {gk}: p50 {statistics.median(g['blat']):.2f}s -> {statistics.median(g['clat']):.2f}s")
        if g["bcost"] > 0 and g["ccost"] > cost_ratio * g["bcost"]:
            flags.append(f"COST UP {gk}: ${g['bcost']:.4f} -> ${g['ccost']:.4f}")
    if missing:
        flags.append(f"DROPPED ANSWERS: {len(missing)} baseline items absent from candidate")
    verdict = "ROLL BACK" if any(f.startswith(("ACCURACY DROP", "CONFABULATION UP", "DROPPED")) for f in flags) else "OK"
    return {"verdict": verdict, "flags": flags, "flips_down": flips_down, "flips_up": flips_up,
            "compared": len(keys), "missing": missing}

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline"); ap.add_argument("candidate")
    ap.add_argument("--z", type=float, default=2.0); ap.add_argument("--lat", type=float, default=1.25)
    ap.add_argument("--cost", type=float, default=1.25)
    a = ap.parse_args(argv)
    r = compare(load(a.baseline), load(a.candidate), a.z, a.lat, a.cost)
    print(f"{r['verdict']}  compared={r['compared']}  pass->fail={len(r['flips_down'])}  fail->pass={len(r['flips_up'])}")
    for f in r["flags"]:
        print("  " + f)
    for k in r["flips_down"]:
        print("  FLIP DOWN", k)
    return 1 if r["verdict"] == "ROLL BACK" else 0

if __name__ == "__main__":
    sys.exit(main())


ANCHOR_SEEDS = (1618, 2718, 3141)


def contamination_gap(rows, anchors=ANCHOR_SEEDS):
    """Randomized items are named RG-<template>-<seed>-<k>. Per (model, arm, template): pass rate on fixed anchor
    seeds minus pass rate on fresh seeds. A large positive gap means the anchors were memorized."""
    acc = defaultdict(lambda: {"a": [], "f": []})
    for (m, arm, iid, _rep), r in rows.items():
        parts = str(iid).split("-")
        if len(parts) < 4 or parts[0] != "RG":
            continue
        p = passed(r)
        if p is None:
            continue
        side = "a" if int(parts[2]) in anchors else "f"
        acc[(m, arm, parts[1])][side].append(p)
    out = {}
    for k, v in acc.items():
        if v["a"] and v["f"]:
            out[k] = sum(v["a"]) / len(v["a"]) - sum(v["f"]) / len(v["f"])
    return out
