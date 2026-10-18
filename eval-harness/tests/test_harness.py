"""Self-test with a mock client and a local mock HTTP server. Run: python3 -m unittest discover -s tests -v"""
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from harness import aggregate, runner, score  # noqa: E402
from harness.arms import build_arms  # noqa: E402
from harness.client import ModelSpec, chat  # noqa: E402
from harness.config import load_config  # noqa: E402
from harness.contract import parse_response  # noqa: E402
from harness.score import first_number, keyed, match_planted, overlap  # noqa: E402
from harness import tokens  # noqa: E402
import mock  # noqa: E402
from mock import mock_chat  # noqa: E402

KIT = Path(os.environ.get("KIT_ROOT", Path.home() / "repos/con-scientia-compact"))
BATTERY = ROOT / "examples/battery.example.jsonl"


def make_kit(d: Path) -> Path:
    """Tiny fake kit so tests do not depend on the real repo being present."""
    (d / "master-prompt").mkdir(parents=True)
    (d / "skills").mkdir()
    (d / "master-prompt/Master Prompt v1.md").write_text("# Master\nNo flattery.\n")
    for n in ("alpha", "beta", "gamma"):
        (d / f"skills/{n}.md").write_text(f"---\nname: {n}\n---\n# {n}\nbody {n}\n")
    return d


def write_cfg(d: Path, kit: Path, **over) -> Path:
    cfg = {
        "kit_root": str(kit), "judge_pool": ["judgeA", "judgeB"], "test_models": ["subjA", "thinker"],
        "models": [
            {"id": "subjA", "backend": "mock", "base_url": "", "model": "a", "family": "judge-a-lineage-test", "lineage": "vendorA"},
            {"id": "thinker", "backend": "mock", "base_url": "", "model": "t", "family": "thinker", "lineage": "vendorT",
             "price_per_mtok_in": 1.0, "price_per_mtok_out": 2.0},
            {"id": "judgeA", "backend": "mock", "base_url": "", "model": "ja", "family": "judge-a", "lineage": "vendorA"},
            {"id": "judgeB", "backend": "mock", "base_url": "", "model": "jb", "family": "judge-b", "lineage": "vendorB"},
        ],
        "arms": [{"type": "vanilla"}, {"type": "full_kit"}, {"type": "master_only"},
                 {"type": "single_skill", "skills": "all"},
                 {"type": "lean_kit", "name": "ab", "skills": ["alpha", "skills/beta.md"], "include_master": True}],
    }
    cfg.update(over)
    p = d / "config.json"
    p.write_text(json.dumps(cfg))
    return p


class TestContract(unittest.TestCase):
    def test_fenced_with_preamble(self):
        p = parse_response('Here you go:\n```json\n{"answer":"x","abstain":false,"confidence":0.4,"errors_found":[],"notes":""}\n```')
        self.assertTrue(p["parse_ok"]); self.assertEqual(p["parse_method"], "fenced"); self.assertEqual(p["confidence"], 0.4)

    def test_think_block_with_draft_json(self):
        txt = '<think>draft {"answer":"wrong","abstain":false}</think>\n{"answer":"right","abstain":true,"confidence":"80%","errors_found":[],"notes":"n"}'
        p = parse_response(txt)
        self.assertEqual(p["answer"], "right"); self.assertTrue(p["abstain"]); self.assertAlmostEqual(p["confidence"], 0.8)

    def test_last_complete_object_wins(self):
        txt = '{"answer":"a"} then final {"answer":"b","abstain":false,"confidence":1,"errors_found":[],"notes":""}'
        self.assertEqual(parse_response(txt)["answer"], "b")

    def test_json_only_in_thinking_channel(self):
        p = parse_response("", thinking='{"answer":"t","abstain":false,"confidence":0.5,"errors_found":[],"notes":""}')
        self.assertEqual(p["answer"], "t"); self.assertIn("json_found_only_in_thinking", p["parse_issues"])

    def test_garbage(self):
        p = parse_response("I think the answer is 42.")
        self.assertFalse(p["parse_ok"]); self.assertEqual(p["answer"], "I think the answer is 42."); self.assertIsNone(p["abstain"])

    def test_confidence_0_100_and_invalid(self):
        self.assertAlmostEqual(parse_response('{"answer":"x","confidence":85}')["confidence"], 0.85)
        p = parse_response('{"answer":"x","confidence":"high"}')
        self.assertIsNone(p["confidence"]); self.assertIn("confidence_invalid", p["parse_issues"])

    def test_nested_braces_in_strings(self):
        p = parse_response('{"answer":"set {1,2}","abstain":false,"confidence":0.5,"errors_found":[{"quote":"a}b","correction":"c"}],"notes":""}')
        self.assertEqual(p["answer"], "set {1,2}"); self.assertEqual(p["errors_found"][0]["quote"], "a}b")


class _H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _H.last = (self.path, body, dict(self.headers))
        if self.path == "/api/chat":
            out = {"message": {"role": "assistant", "content": '{"answer":"ok"}', "thinking": "t"}, "done_reason": "stop",
                   "prompt_eval_count": 11, "eval_count": 3, "eval_duration": 5, "prompt_eval_duration": 7,
                   "total_duration": 20, "load_duration": 1}
        elif self.path == "/v1/chat/completions":
            out = {"choices": [{"message": {"content": "hi", "reasoning_content": "r"}, "finish_reason": "stop"}],
                   "usage": {"prompt_tokens": 9, "completion_tokens": 2}}
        else:
            self.send_response(404); self.end_headers(); self.wfile.write(b"nope"); return
        data = json.dumps(out).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)


class TestClientHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), _H)
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_ollama(self):
        s = ModelSpec(id="o", backend="ollama", base_url=self.url, model="m", family="f", num_ctx=8192, max_tokens=64)
        r = chat(s, [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}])
        path, body, _ = _H.last
        self.assertEqual(path, "/api/chat"); self.assertFalse(body["stream"])
        self.assertEqual(body["options"], {"temperature": 0.0, "num_ctx": 8192, "num_predict": 64})
        self.assertEqual((r.prompt_tokens, r.completion_tokens, r.thinking), (11, 3, "t"))
        self.assertEqual(r.backend_timing["eval_duration"], 5); self.assertIsNotNone(r.latency_s)

    def test_openai_with_key_and_v1_base(self):
        os.environ["T_KEY"] = "sekret"
        s = ModelSpec(id="p", backend="openai", base_url=self.url + "/v1", model="m", family="f", api_key_env="T_KEY",
                      price_per_mtok_in=3, price_per_mtok_out=15, system_role=False)
        r = chat(s, [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}])
        path, body, hdr = _H.last
        self.assertEqual(path, "/v1/chat/completions"); self.assertEqual(hdr["Authorization"], "Bearer sekret")
        self.assertEqual([m["role"] for m in body["messages"]], ["user"])  # system folded in
        self.assertTrue(body["messages"][0]["content"].startswith("S"))
        self.assertEqual((r.prompt_tokens, r.completion_tokens, r.thinking), (9, 2, "r"))
        self.assertAlmostEqual(s.cost_usd(9, 2), (27 + 30) / 1e6)

    def test_http_error_recorded_not_raised(self):
        s = ModelSpec(id="o", backend="openai", base_url=self.url + "/bad", model="m", family="f")
        r = chat(s, [{"role": "user", "content": "U"}], retries=0)
        self.assertIn("HTTP 404", r.error)

    def test_missing_key_recorded(self):
        s = ModelSpec(id="p", backend="openai", base_url=self.url, model="m", family="f", api_key_env="NOPE_NOT_SET")
        self.assertIn("NOPE_NOT_SET", chat(s, [{"role": "user", "content": "U"}], retries=0, backoff_s=0).error)



class TestKeyedLeadRules(unittest.TestCase):
    def test_numeric_from_parsed_answer(self):
        it = {"answer_numeric": 100, "tolerance": 0.5}
        self.assertTrue(keyed(it, "100 degrees")["key_correct"])
        self.assertTrue(keyed(it, "1,00.2")["key_correct"] is False)
        self.assertFalse(keyed(it, "101")["key_correct"])
        self.assertEqual(first_number("approx 1,234.5 m"), 1234.5)
        self.assertEqual(first_number("version 1.0 not 0"), 1.0)
        # lead's first-number rule, pinned so the residual risk stays visible (ledger #4)
        self.assertEqual(keyed(it, "At 1 atm it is 100 C")["key_extracted"], 1.0)

    def test_patterns_and_forbidden(self):
        it = {"accept_patterns": [r"\bmercury\b"], "forbidden_patterns": [r"\bvenus\b"]}
        self.assertTrue(keyed(it, "Mercury")["key_correct"])
        self.assertFalse(keyed(it, "Mercury, or maybe Venus")["key_correct"])
        self.assertFalse(keyed(it, None)["key_correct"])
        self.assertTrue(keyed({"answer_key": "Paris"}, "It is Paris.")["key_correct"])

    def test_bare_digit_regex_not_used_when_numeric(self):
        it = {"answer_numeric": 0, "tolerance": 0, "accept_patterns": [r"(^|\D)0(\D|$)"]}
        self.assertFalse(keyed(it, "1.0")["key_correct"])
        self.assertTrue(keyed(it, "0")["key_correct"])


class TestSeededMatching(unittest.TestCase):
    def test_paraphrase_overlap(self):
        self.assertGreaterEqual(overlap("Water freezes at 10 degrees Celsius", "water freezes at ten degrees C"), 0.5)
        self.assertLess(overlap("Water freezes at 10 degrees Celsius", "Everest is tallest"), 0.5)

    def test_one_to_one(self):
        planted = [{"id": "e1", "quote": "Water freezes at 10 degrees Celsius"},
                   {"id": "e2", "quote": "Everest is in the Andes"}]
        m = match_planted(planted, [{"quote": "freezes at 10 degrees"}])
        self.assertEqual([v[0] for v in m.values()], ["e1"])
        m2 = match_planted(planted, [{"quote": "Everest is in the Andes"}, {"quote": "Everest in the Andes"}])
        self.assertEqual(len(m2), 1)


class TestTokens(unittest.TestCase):
    def test_required_ctx_lead_numbers(self):
        # lead measured: full kit 28,215 tokens; must land >= 40960
        self.assertGreaterEqual(tokens.required_num_ctx(28215, 1000), 40960)
        self.assertEqual(tokens.required_num_ctx(100, 100, floor=40960), 40960)
        self.assertEqual(tokens.ladder_up(8193), 12288)

    def test_show_parsing(self):
        show = {"model_info": {"general.architecture": "llama", "llama.context_length": 131072}}
        self.assertEqual(tokens.context_max_from_show(show), 131072)
        self.assertIsNone(tokens.context_max_from_show({}))

    def test_truncation_check_lead_case(self):
        r = tokens.truncation_check(4098, 28215, 50, estimate_slack=0)
        self.assertEqual(r["trunc_guard"], "fail")
        self.assertEqual(tokens.truncation_check(28215, 28215, 50, estimate_slack=0)["trunc_guard"], "pass")
        self.assertEqual(tokens.truncation_check(26700, 28215, 50, estimate_slack=0)["trunc_guard"], "fail")  # 5.4% short

    def test_prefill_tracker(self):
        t = tokens.PrefillTracker()
        b = ("m", "full_kit")
        seq = [t.classify(b, d) for d in (34_944e6, 311e6, 58e6, 60e6, 30_000e6)]
        self.assertEqual(seq, ["cold", "warm", "warm", "warm", "cold"])


class TestPipeline(unittest.TestCase):
    def setUp(self):
        mock.reset()
        self.td = Path(tempfile.mkdtemp())
        self.kit = make_kit(self.td / "kit")
        self.cfg = load_config(write_cfg(self.td, self.kit))
        self.out = self.td / "results.jsonl"

    def _run(self, cfg=None, **kw):
        kw.setdefault("fetch_show", False)
        kw.setdefault("keep_alive", None)
        return runner.run(cfg or self.cfg, BATTERY, self.out, chat_fn=mock_chat, log=lambda *a: None, **kw)

    def test_arms_fake_kit(self):
        arms = build_arms(self.kit, self.cfg.arms)
        self.assertEqual([a.id for a in arms],
                         ["vanilla", "full_kit", "master_only", "single:alpha", "single:beta", "single:gamma", "lean:ab"])

    def test_full_pipeline_resume_score_aggregate(self):
        s = self._run()
        n = 2 * 7 * 7
        self.assertEqual((s["planned"], s["ok"], s["error"], s["canary_failed_blocks"]), (n, n, 0, 0))
        self.assertEqual(self._run()["todo"], 0)
        rows = runner.read_jsonl(self.out)
        canaries = [r for r in rows if r["status"] == "canary"]
        self.assertEqual(len(canaries), 14)
        self.assertTrue(all(c["ok"] for c in canaries))
        items = [r for r in rows if r["status"] != "canary"]
        # byte-identical system prompt within a block; context goes to the user message
        for (m, a) in {(r["model_id"], r["arm_id"]) for r in items}:
            self.assertEqual(len({r["system_prompt_sha256"] for r in items if (r["model_id"], r["arm_id"]) == (m, a)}), 1)
        ctx = [r for r in items if r["item_id"] == "fk-ctx-001"][0]
        self.assertIn("CONTEXT START", ctx["turns"][0]["user"])
        # blocks are consecutive
        order = [(r["model_id"], r["arm_id"]) for r in items]
        self.assertEqual(len([i for i in range(1, len(order)) if order[i] != order[i - 1]]), 13)

        sp = self.td / "scored.jsonl"
        score.score(self.cfg, self.out, BATTERY, sp, self.td / "jc.jsonl", chat_fn=mock_chat, log=lambda *a: None)
        sc = {(r["model_id"], r["arm_id"], r["item_id"]): r for r in runner.read_jsonl(sp)}
        v, k = (lambda i: sc[("subjA", "vanilla", i)]), (lambda i: sc[("subjA", "full_kit", i)])
        self.assertFalse(v("fk-002")["correct"]); self.assertTrue(k("fk-002")["correct"])
        self.assertTrue(k("fk-ctx-001")["correct"]); self.assertFalse(v("fk-ctx-001")["correct"])
        self.assertEqual(v("fk-001")["key_extracted"], 1.0)                 # pinned residual risk
        self.assertTrue(v("trap-001")["confabulated"]); self.assertTrue(k("trap-001")["correct"])
        self.assertEqual(v("syc-001")["outcome"], "capitulated"); self.assertEqual(k("syc-001")["outcome"], "held")
        self.assertTrue(v("seed-001")["hidden_mistake"])
        self.assertEqual((k("seed-001")["item_recall"], k("seed-001")["item_precision"]), (1.0, 1.0))  # paraphrase credited
        self.assertEqual(v("clean-001")["outcome"], "false_positive"); self.assertEqual(k("clean-001")["outcome"], "clean")
        judged = [r for r in sc.values() if r.get("judges")]
        self.assertTrue(all(j["judge_id"] != "judgeA" for r in judged if r["model_id"] == "subjA" for j in r["judges"]))

        table = aggregate.build_table(list(sc.values()))
        f = {(r["model_id"], r["arm_id"]): r for r in table}
        self.assertGreater(f[("subjA", "full_kit")]["composite_delta_vs_vanilla"], 0)
        self.assertEqual(f[("subjA", "full_kit")]["n_invalid_truncated"], 0)
        sl = aggregate.build_table(list(sc.values()), slice_by="requires_context")
        self.assertEqual({r["slice"] for r in sl}, {"requires_context=True", "requires_context=None"})   # absent field stays None, not assumed False
        csvp, mdp = self.td / "s.csv", self.td / "r.md"
        aggregate.main(["--scored", str(sp), "--results", str(self.out), "--csv", str(csvp), "--md", str(mdp),
                        "--sliced-csv", str(self.td / "sl.csv")])
        md = mdp.read_text()
        for h in ("Validity, prefill and caching", "Sliced by requires_context", "per-item precision / recall"):
            self.assertIn(h, md)

    def test_skip_context_exceeds_model_max(self):
        cfg = load_config(write_cfg(self.td, self.kit, test_models=["small"], judge_pool=[], models=[
            {"id": "small", "backend": "ollama", "base_url": "http://x", "model": "s", "family": "f", "lineage": "l",
             "max_ctx": 4096, "max_tokens": 1024}]))
        s = self._run(cfg, arm_ids=["vanilla", "full_kit"])
        self.assertEqual((s["context_exceeds_model_max"], s["ok"]), (14, 0))   # need >= 4096 headroom alone
        r = [r for r in runner.read_jsonl(self.out) if r["status"] == "context_exceeds_model_max"][0]
        self.assertEqual(r["model_max_ctx"], 4096)
        self.assertGreater(r["required_num_ctx"], 4096)

    def test_ollama_capped_ctx_prefill_and_keep_alive(self):
        cfg = load_config(write_cfg(self.td, self.kit, test_models=["mid"], judge_pool=[], models=[
            {"id": "mid", "backend": "ollama", "base_url": "http://x", "model": "m", "family": "f", "lineage": "l",
             "max_ctx": 40960}]))
        ka = []
        orig = runner.ollama_keep_alive
        runner.ollama_keep_alive = lambda base, model, k: ka.append((model, k))
        try:
            self._run(cfg, arm_ids=["vanilla"], keep_alive="60m")
        finally:
            runner.ollama_keep_alive = orig
        self.assertEqual(ka, [("m", "60m"), ("m", 0)])                         # held for the block, released after
        ok = [r for r in runner.read_jsonl(self.out) if r["status"] == "ok"]
        self.assertEqual({r["num_ctx"] for r in ok}, {40960})                  # 100000 standing order, capped
        self.assertEqual([r["prefill"] for r in ok][:2], ["cold", "warm"])
        self.assertIsNotNone(ok[0]["prompt_eval_duration_ns"])

    def test_truncation_invalid_and_canary_fail(self):
        spec = ModelSpec(id="t", backend="ollama", base_url="http://x", model="t", family="truncator", lineage="l")
        arm = build_arms(self.kit, [{"type": "full_kit"}])[0]
        c = runner.canary_check(spec, arm, mock_chat, 0.0, 0, 60, lambda *a: None)
        self.assertFalse(c["ok"])
        item = {"id": "x", "category": "factual_keyed", "prompt": "Which planet is closest to the Sun?"}
        r = runner.run_one(spec, arm, item, 0, mock_chat, 0.0, 0, 60, 4.0, tokens.PrefillTracker(), False, 0.05, True)
        self.assertEqual(r["status"], "INVALID_TRUNCATED")
        self.assertNotIn("parsed", r)
        r2 = runner.run_one(spec, arm, item, 0, mock_chat, 0.0, 0, 100000, 4.0, None, True, 0.05, True)
        self.assertEqual(r2["status"], "ok")
        sr = score.score_row(r, {**item, "requires_context": None}, self.cfg, None)
        self.assertIsNone(sr["correct"])

    def test_errors_retried_append_only(self):
        from harness.client import ChatResult
        calls = {"n": 0}

        def flaky(spec, msgs):
            calls["n"] += 1
            if calls["n"] <= 3:
                return ChatResult(error="boom")
            return mock_chat(spec, msgs)
        s1 = self._run(model_ids=["subjA"], arm_ids=["vanilla"], chat_fn_override=None) if False else \
            runner.run(self.cfg, BATTERY, self.out, ["subjA"], ["vanilla"], chat_fn=flaky, do_canary=False, fetch_show=False, log=lambda *a: None)
        self.assertGreater(s1["error"], 0)
        s2 = runner.run(self.cfg, BATTERY, self.out, ["subjA"], ["vanilla"], chat_fn=flaky, do_canary=False, fetch_show=False, log=lambda *a: None)
        self.assertEqual(s2["todo"], s1["error"])
        self.assertEqual(len(score.latest_rows(self.out)), 7)
        self.assertTrue(all(r["status"] == "ok" for r in score.latest_rows(self.out)))

    def test_no_judge_leaves_unscored(self):
        cfg = load_config(write_cfg(self.td, self.kit, judge_pool=[]))
        self._run(cfg, model_ids=["subjA"], arm_ids=["vanilla"])
        sp = self.td / "s3.jsonl"
        score.score(cfg, self.out, BATTERY, sp, self.td / "jc3.jsonl", chat_fn=mock_chat, log=lambda *a: None)
        sc = {r["item_id"]: r for r in runner.read_jsonl(sp)}
        self.assertIsNone(sc["syc-001"]["correct"])
        self.assertTrue(sc["trap-001"]["confabulated"])      # forbidden pattern decides without a judge


class TestCacheCost(unittest.TestCase):
    def test_cached_vs_uncached(self):
        from harness.client import ChatResult
        sp = ModelSpec(id="p", backend="anthropic", base_url="", model="m", family="f", lineage="l",
                       price_per_mtok_in=3.0, price_per_mtok_out=15.0,
                       price_per_mtok_cache_write=3.75, price_per_mtok_cache_read=0.30)
        r = ChatResult(prompt_tokens=30000, completion_tokens=1000, cache_creation_input_tokens=0, cache_read_input_tokens=28000)
        c = sp.cost_breakdown(r)
        self.assertAlmostEqual(c["cost_uncached_usd"], 30000 * 3e-6 + 1000 * 15e-6)
        self.assertAlmostEqual(c["cost_usd"], 2000 * 3e-6 + 28000 * 0.30e-6 + 1000 * 15e-6)
        sp2 = ModelSpec(id="p", backend="anthropic", base_url="", model="m", family="f", lineage="l",
                        price_per_mtok_in=3.0, price_per_mtok_out=15.0)
        self.assertIsNone(sp2.cost_breakdown(r)["cost_usd"])      # no cache prices -> not invented



class TestExoLifecycle(unittest.TestCase):
    def test_place_poll_delete(self):
        from harness.exo import ExoLifecycle, maybe_instance
        calls, state = [], {"n": 0}

        def fake_http(method, url, payload=None, timeout=60.0):
            calls.append((method, url.split(":52415")[1], payload))
            if url.endswith("/place_instance"):
                return {"instance_id": "inst-1"}
            if url.endswith("/state"):
                state["n"] += 1
                st = "RunnerLoading" if state["n"] < 3 else "RunnerReady"
                return {"instances": {"inst-1": {"model_id": "m1", "status": st}}} if state["n"] > 1 else {"instances": {}}
            return None
        lc = ExoLifecycle("http://exo:52415", http=fake_http, poll_s=0, timeout_s=5, log=lambda *a: None)
        spec = ModelSpec(id="m1", backend="exo", base_url="http://exo:52415", model="m1", family="f", lineage="l",
                         needs_instance=True)
        with maybe_instance(spec, lc):
            calls.append(("RUN", "", None))
        seq = [(m, u) for m, u, _ in calls]
        self.assertEqual(seq[1], ("POST", "/place_instance"))
        self.assertEqual(calls[1][2], {"model_id": "m1"})
        self.assertLess(seq.index(("GET", "/state"), 1), seq.index(("RUN", "")))
        self.assertEqual(seq[-1], ("DELETE", "/instance/inst-1"))

    def test_delete_runs_even_if_items_raise(self):
        from harness.exo import ExoLifecycle
        calls = []

        def fake_http(method, url, payload=None, timeout=60.0):
            calls.append(method)
            return {"instance_id": "i9"} if url.endswith("/place_instance") else {"instances": {"i9": {"status": "RunnerReady"}}}
        lc = ExoLifecycle("http://exo:52415", http=fake_http, poll_s=0, timeout_s=5, log=lambda *a: None)
        with self.assertRaises(ValueError):
            with lc.instance("m"):
                raise ValueError("item crash")
        self.assertEqual(calls[-1], "DELETE")


class TestRegistryCtxAndTimeouts(unittest.TestCase):
    def test_registry_num_ctx_and_pins(self):
        from harness.config import load_registry, timeout_for
        td = Path(tempfile.mkdtemp())
        reg = {"ollama_base": "http://o:11434", "exo_base": "http://e:52415", "judge_pool": [], "models": [
            {"id": "qwen3:32b", "backend": "ollama", "lineage": "qwen", "price_in": 0, "price_out": 0, "tier": "large",
             "max_ctx": 40960, "num_ctx_default": 100000, "num_ctx_full_kit": 100000, "thinking": True},
            {"id": "magistral:24b", "backend": "ollama", "lineage": "mistral", "price_in": 0, "price_out": 0,
             "tier": "medium", "max_ctx": 40000},
            {"id": "big", "backend": "ollama", "lineage": "x", "price_in": 0, "price_out": 0, "tier": "small",
             "max_ctx": 131072, "num_ctx_full_kit": 65536, "timeout_s": 60}]}
        (td / "r.json").write_text(json.dumps(reg))
        models, _, _ = load_registry(td / "r.json")
        kit = make_kit(td / "kit")
        van, full = build_arms(kit, [{"type": "vanilla"}, {"type": "full_kit"}])
        size = lambda mid, arm: runner.size_num_ctx(models[mid], arm, 500, 4.0, models[mid].max_ctx)[0]  # noqa: E731
        self.assertEqual(size("qwen3:32b", van), 40960)
        self.assertEqual(size("qwen3:32b", full), 40960)
        self.assertEqual(size("magistral:24b", van), 40000)
        self.assertEqual(size("big", van), 100000)
        self.assertEqual(size("big", full), 65536)
        self.assertEqual(models["qwen3:32b"].timeout_s, 600.0)
        self.assertEqual(models["big"].timeout_s, 60.0)
        self.assertEqual(timeout_for({"tier": "large", "timeout_s": 60}), 300.0)
        self.assertEqual(timeout_for({"thinking": True, "timeout_s": 100}), 300.0)


class TestContractViolations(unittest.TestCase):
    RAW = '{"answer": "1 error", "correction": "Water freezes at 10 degrees Celsius -> 0", "errors_found": [], "notes": ""}'

    def test_missing_null_and_extra_kept(self):
        p = parse_response(self.RAW)
        self.assertEqual(p["contract_violations"], ["missing:abstain", "missing:confidence", "extra:correction"])
        self.assertIsNone(p["abstain"]); self.assertIsNone(p["confidence"])
        self.assertIn("correction", p["extra_keys"])

    def test_correction_recovered_on_seeded_item(self):
        from harness.battery import load_battery
        item = [i for i in load_battery(BATTERY) if i["id"] == "seed-001"][0]
        cfg = load_config(write_cfg(Path(tempfile.mkdtemp()), make_kit(Path(tempfile.mkdtemp()) / "k"), judge_pool=[]))
        row = {"status": "ok", "parsed": parse_response(self.RAW), "model_id": "subjA", "item_id": "seed-001",
               "category": "seeded_error_doc", "arm_id": "vanilla"}
        sr = score.score_row(row, item, cfg, None)
        self.assertEqual(sr["errors_found_source"], "recovered_from_extra_key")
        self.assertEqual(sr["n_caught"], 1)
        self.assertFalse(sr["hidden_mistake"])
        self.assertTrue(sr["contract_violated"])
        from harness.metrics import group_metrics
        m = group_metrics([sr])
        self.assertEqual(m["n_brier_excluded_null_conf"], 1)
        self.assertEqual(m["contract_violation_rate"]["value"], 1.0)
        self.assertEqual(m["n_recovered_from_extra_key"], 1)


class FakeExo:
    """In-memory exo cluster: nodeMemory in bytes objects, instances keyed by id."""
    def __init__(self, free_gb=160.0, weights_gb=69.6, extra_after_samples=None, extra_gb=0.0):
        self.free, self.w, self.inst, self.log = free_gb, weights_gb, {}, []
        self.polls, self.n_state, self.extra_after, self.extra_gb = 0, 0, extra_after_samples, extra_gb

    def http(self, method, url, payload=None, timeout=60.0):
        path = url.split(":52415")[1]
        self.log.append((method, path.split("?")[0]))
        if path.startswith("/instance/previews"):
            return {"previews": [{"model_id": "m", "sharding": "Pipeline", "instance_meta": "MlxRing",
                                  "instance": {"MlxRingInstance": {"instanceId": "i1"}}}]}
        if path == "/place_instance":
            self.inst["i1"] = {"modelId": payload["model_id"], "status": "RunnerLoading"}
            self.free -= self.w
            return {"instance_id": "i1"}
        if method == "DELETE":
            iid = path.rsplit("/", 1)[1]
            if self.inst.pop(iid, None) is not None:
                self.free += self.w
            return None
        self.n_state += 1
        for v in self.inst.values():
            self.polls += 1
            if self.polls >= 2:
                v["status"] = "RunnerReady"
        if self.extra_after is not None and self.n_state > self.extra_after:
            self.free -= self.extra_gb
            self.extra_gb = 0
        b = self.free * 1e9
        return {"nodeMemory": {"a": {"ramAvailable": {"inBytes": b * 0.6}, "ramTotal": {"inBytes": 137.4e9}},
                               "b": {"ramAvailable": {"inBytes": b * 0.4}, "ramTotal": {"inBytes": 78.6e9}}},
                "instances": dict(self.inst)}


class TestExoScheduler(unittest.TestCase):
    def _sched(self, fx, **kw):
        from harness.exo_sched import ExoScheduler
        ev = []

        class W:
            def write(self, r):
                ev.append(r)
        return ExoScheduler("http://exo:52415", W(), http=fx.http, poll_s=0, sleep=lambda s: None,
                            log=lambda *a: None, **kw), ev

    def _spec(self, **kw):
        return ModelSpec(id="m", backend="exo", base_url="http://exo:52415", model="m", family="f", lineage="l",
                         needs_instance=True, weights_gb=69.6, kv_bytes_per_token=48e3, **kw)

    def test_free_ram_and_place_evict_logged(self):
        fx = FakeExo()
        sch, ev = self._sched(fx)
        r = sch.free_ram()
        self.assertEqual(r["total_free_gb"], 160.0)
        self.assertEqual(r["per_node_free_gb"], {"a": 96.0, "b": 64.0})
        with sch.block(self._spec(), 100000) as mon:
            self.assertAlmostEqual(mon.kv_est_gb, 4.8)
            mon.sample()
        names = [e["event"] for e in ev]
        self.assertEqual(names[0], "state_raw_first_placement")   # raw /state logged once for the lead
        self.assertEqual(names[1], "placed"); self.assertEqual(names[-1], "evicted")
        placed = ev[1]
        self.assertEqual((placed["free_before_gb"], placed["free_after_gb"]), (160.0, 90.4))
        self.assertIn("load_s", placed)
        self.assertEqual(ev[-1]["free_after_gb"], 160.0)
        self.assertIn(("GET", "/instance/previews"), fx.log)

    def test_refuses_when_projection_exceeds_free(self):
        from harness.exo_sched import InsufficientMemory
        fx = FakeExo(free_gb=60.0)
        sch, ev = self._sched(fx)
        with self.assertRaises(InsufficientMemory):
            sch.ensure_resident(self._spec(), 100000)
        self.assertNotIn(("POST", "/place_instance"), fx.log)
        self.assertEqual(ev[-1]["event"], "refused_insufficient_ram")

    def test_unsized_model_refused_by_default(self):
        from harness.exo_sched import InsufficientMemory
        sch, _ = self._sched(FakeExo())
        spec = ModelSpec(id="m", backend="exo", base_url="", model="m", family="f", lineage="l", needs_instance=True)
        with self.assertRaises(InsufficientMemory):
            sch.ensure_resident(spec, 100000)

    def test_kv_kill_condition_aborts_block_in_runner(self):
        td = Path(tempfile.mkdtemp())
        kit = make_kit(td / "kit")
        cfg = load_config(write_cfg(td, kit, test_models=["m"], judge_pool=[], exo_base="http://exo:52415", models=[
            {"id": "m", "backend": "exo", "base_url": "http://exo:52415", "model": "m", "family": "f", "lineage": "l",
             "needs_instance": True, "weights_gb": 69.6, "kv_bytes_per_token": 48e3, "max_ctx": 100000}]))
        fx = FakeExo(extra_after_samples=8, extra_gb=20.0)        # usage jumps past weights + 2 x 4.8 GB
        sch, ev = self._sched(fx)
        s = runner.run(cfg, BATTERY, td / "res.jsonl", arm_ids=["vanilla", "full_kit"], chat_fn=mock_chat,
                       do_canary=False, fetch_show=False, keep_alive=None, scheduler=sch, log=lambda *a: None)
        self.assertGreater(s["kv_estimate_invalid"], 0)
        self.assertEqual(s["ok"] + s["kv_estimate_invalid"], 14)
        names = [e["event"] for e in ev]
        self.assertEqual(names.count("placed"), 1)                # one placement for ALL arms of the model
        self.assertEqual(names.count("evicted"), 1)
        self.assertIn("kv_estimate_invalid", [e.get("verdict") for e in ev])
        self.assertIsNotNone([e for e in ev if e["event"] == "block_end"][0]["peak_used_gb"])


class TestVerifiedExoShapes(unittest.TestCase):
    PREV = {"previews": [{"model_id": "m", "sharding": "Pipeline", "instance_meta": "MlxRing", "instance": {
        "MlxRingInstance": {"instanceId": "u-1", "shardAssignments": {"modelId": "m", "runnerToShard": {
            "r-1": {"PipelineShardMetadata": {"modelCard": {"storageSize": {"inBytes": 1}}}}}}}}}]}

    def test_preview_id_path_and_variant(self):
        from harness.exo import preview_instance_ids
        self.assertEqual(preview_instance_ids(self.PREV), ["u-1"])
        other = {"previews": [{"instance": {"SomeOtherInstance": {"instanceId": "u-2"}}}]}
        self.assertEqual(preview_instance_ids(other), ["u-2"])

    def test_ready_predicate(self):
        from harness.exo import ready_instances_runners as rdy
        idle = {"instances": {}, "runners": {}, "nodeMemory": {}}
        self.assertFalse(rdy(idle, "m", "u-1"))
        inst = {"u-1": self.PREV["previews"][0]["instance"]}
        self.assertFalse(rdy({"instances": inst, "runners": {}}, "m", "u-1"))
        self.assertFalse(rdy({"instances": inst, "runners": {"r-9": {}}}, "m", "u-1"))
        self.assertTrue(rdy({"instances": inst, "runners": {"r-1": {"status": "x"}}}, "m", "u-1"))

    def test_not_resident_signal(self):
        from harness.exo_sched import is_not_resident_error
        self.assertTrue(is_not_resident_error('HTTP 404: {"error":{"message":"No instance found for model m",'
                                              '"type":"Not Found"}}'))
        self.assertFalse(is_not_resident_error("HTTP 500: boom"))

    def test_numeric_zero_key_is_real(self):
        item = {"id": "FK-001", "category": "factual_keyed", "answer_key": "0", "answer_numeric": 0,
                "tolerance": 0.0, "accept_patterns": [], "forbidden_patterns": []}
        r = score.keyed(item, "0")
        self.assertEqual((r["key_correct"], r["key_method"]), (True, "numeric"))   # 0 is a real key
        self.assertFalse(score.keyed(item, "1")["key_correct"])
        none_item = dict(item, answer_numeric=None, answer_key="zero", accept_patterns=["^zero$"])
        r = score.keyed(none_item, "zero")
        self.assertTrue(r["key_correct"]); self.assertNotEqual(r["key_method"], "numeric")


if __name__ == "__main__":
    unittest.main()
