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
