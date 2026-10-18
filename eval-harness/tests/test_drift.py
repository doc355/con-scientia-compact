import unittest
from harness.drift import compare

def rows(passes, cat="factual_keyed", lat=1.0, outcome=None):
    return {("m", "a", f"I{i}", 0): {"item_id": f"I{i}", "category": cat, "correct": p, "latency_s": lat,
            "outcome": outcome or ("correct" if p else "wrong")} for i, p in enumerate(passes)}

class DriftTests(unittest.TestCase):
    def test_identical_ok(self):
        b = rows([True] * 30 + [False] * 10)
        self.assertEqual(compare(b, dict(b))["verdict"], "OK")
    def test_large_drop_rolls_back(self):
        r = compare(rows([True] * 30 + [False] * 10), rows([True] * 15 + [False] * 25))
        self.assertEqual(r["verdict"], "ROLL BACK"); self.assertEqual(len(r["flips_down"]), 15)
    def test_single_flip_is_noise(self):
        r = compare(rows([True] * 30 + [False] * 10), rows([True] * 29 + [False] * 11))
        self.assertEqual(r["verdict"], "OK"); self.assertEqual(len(r["flips_down"]), 1)
    def test_dropped_answer_rolls_back(self):
        b = rows([True] * 5); c = dict(b); c.pop(("m", "a", "I0", 0))
        self.assertEqual(compare(b, c)["verdict"], "ROLL BACK")
    def test_confabulation_rise_rolls_back(self):
        c = rows([True] * 4 + [False]); c[("m", "a", "I4", 0)]["outcome"] = "confabulated"
        self.assertEqual(compare(rows([True] * 4 + [False]), c)["verdict"], "ROLL BACK")
    def test_latency_flag_only(self):
        r = compare(rows([True] * 5), rows([True] * 5, lat=3.0))
        self.assertEqual(r["verdict"], "OK"); self.assertTrue(any("LATENCY UP" in f for f in r["flags"]))

if __name__ == "__main__":
    unittest.main()

class IndicatorProbeTests(unittest.TestCase):
    def test_category_valid(self):
        from harness.battery import validate_item
        self.assertEqual(validate_item({"id": "X", "category": "indicator_probe", "prompt": "p"}), [])

class ContaminationGapTests(unittest.TestCase):
    def test_gap(self):
        from harness.drift import contamination_gap
        rows = {("m", "a", f"RG-bulk-{s}-{k}", 0): {"correct": s == 1618} for s in (1618, 55) for k in range(4)}
        self.assertEqual(contamination_gap(rows), {("m", "a", "bulk"): 1.0})


class CanaryBudgetTests(unittest.TestCase):
    def test_thinking_model_gets_room(self):
        import inspect
        from harness import runner
        src = inspect.getsource(runner.canary_check)
        self.assertIn("64 if not spec.thinking", src)


class TestDegenerateThinking(unittest.TestCase):
    def test_loop_flagged_and_cap_retry_skipped(self):
        from pathlib import Path
        from harness.runner import is_degenerate_thinking
        loop = "Wait, I should check if the Euler characteristic is 0. Yes, it is. " * 400
        self.assertTrue(is_degenerate_thinking(loop))
        self.assertFalse(is_degenerate_thinking(" ".join(f"w{i}" for i in range(3000))))
        self.assertFalse(is_degenerate_thinking("Wait, yes. " * 50))
        src = open(Path(__file__).resolve().parents[1] / "harness" / "runner.py").read()
        self.assertIn('"degenerate_thinking_loop"', src)
        self.assertIn('"sampling_options"', src)


class TestExternalHarnessBackend(unittest.TestCase):
    def test_cmd_harness_reply_and_trace_kept(self):
        import sys
        from harness.client import ModelSpec, chat
        echo = ("import json,sys;r=json.load(sys.stdin);"
                "print(json.dumps({'content':'ANS:'+r['messages'][-1]['content'],'trace':{'gates':['g1','g2']}}))")
        spec = ModelSpec(id="hydra@test", family="test", backend="external", base_url="", model="hydra-v1",
                         options={"cmd": [sys.executable, "-c", echo]})
        res = chat(spec, [{"role": "system", "content": "S"}, {"role": "user", "content": "Q"}], retries=0)
        self.assertIsNone(res.error)
        self.assertEqual(res.content, "ANS:Q")
        self.assertEqual(res.raw["trace"]["gates"], ["g1", "g2"])

    def test_failing_harness_is_an_error_not_a_drop(self):
        import sys
        from harness.client import ModelSpec, chat
        spec = ModelSpec(id="hydra@test", family="test", backend="external", base_url="", model="x",
                         options={"cmd": [sys.executable, "-c", "import sys;sys.exit(3)"]})
        res = chat(spec, [{"role": "user", "content": "Q"}], retries=0)
        self.assertIn("exit 3", res.error)


class TestIncompleteAndVoid(unittest.TestCase):
    def test_cut_off_reply_is_not_ok(self):
        from harness.runner import is_incomplete
        self.assertTrue(is_incomplete([{"content": "", "finish_reason": None, "thinking": "half a thou"}]))
        self.assertFalse(is_incomplete([{"content": "", "finish_reason": "stop"}]))
        self.assertFalse(is_incomplete([{"content": "{}", "finish_reason": None}]))

    def test_void_row_retires_ok_row_and_keeps_it(self):
        import json, tempfile
        from pathlib import Path
        from harness.runner import completed_keys, drop_voided, read_jsonl
        a = {"run_id": "r1", "status": "ok", "item_id": "FK-002", "model_id": "m", "arm_id": "vanilla", "rep": 0}
        b = {"run_id": "r2", "status": "ok", "item_id": "FK-003", "model_id": "m", "arm_id": "vanilla", "rep": 0}
        v = {"run_id": "v1", "status": "VOIDED", "voids_run_id": "r1", "item_id": "FK-002", "model_id": "m",
             "arm_id": "vanilla", "rep": 0, "reason": "cut off"}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.jsonl"
            p.write_text("\n".join(json.dumps(x) for x in (a, b, v)) + "\n")
            self.assertEqual(completed_keys(p), {("FK-003", "m", "vanilla", 0)})
            self.assertEqual(len(read_jsonl(p)), 3)
            self.assertEqual([r["run_id"] for r in drop_voided(read_jsonl(p))], ["r2"])


class TestSigtermUnwinds(unittest.TestCase):
    def test_sigterm_runs_finally(self):
        import subprocess, sys, textwrap
        code = textwrap.dedent("""
            import os, signal, time
            from harness.runner import install_sigterm_exit
            install_sigterm_exit()
            try:
                os.kill(os.getpid(), signal.SIGTERM); time.sleep(5)
            finally:
                print("EVICTED")
        """)
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=20)
        self.assertIn("EVICTED", p.stdout)
        self.assertEqual(p.returncode, 143)


class TestLoopDetectedInTail(unittest.TestCase):
    def test_late_loop_after_sound_reasoning_is_flagged(self):
        from harness.runner import is_degenerate_thinking
        import random
        random.seed(7)
        prose = " ".join(f"step{random.randrange(10**6)} of the computation" for _ in range(1200))
        loop = " Wait, I'll use 22.46." * 900
        self.assertTrue(is_degenerate_thinking(prose + loop))      # gemma FK-017 shape
        self.assertTrue(is_degenerate_thinking(loop))              # gemma FK-001 shape
        self.assertFalse(is_degenerate_thinking(prose))            # long but healthy
        self.assertFalse(is_degenerate_thinking(prose + " Wait, I'll use 22.46." * 3))

    def test_real_fk017_trace_is_flagged(self):
        import json, os
        from harness.runner import is_degenerate_thinking
        p = "run/results/stage1b.jsonl"
        if not os.path.exists(p):
            self.skipTest("results not present in this checkout")
        rows = [json.loads(l) for l in open(p) if l.strip()]
        r = [x for x in rows if x.get("item_id") == "FK-017" and x.get("model_id") == "gemma4:12b"]
        if not r:
            self.skipTest("FK-017 row not present")
        self.assertTrue(is_degenerate_thinking(r[-1]["turns"][0].get("thinking") or ""))
