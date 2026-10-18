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

from harness import aggregate, metrics, runner, score  # noqa: E402
from harness.arms import build_arms  # noqa: E402
from harness.client import ModelSpec, chat  # noqa: E402
from harness.config import load_config  # noqa: E402
from harness.contract import CONTRACT_REMINDER, parse_response  # noqa: E402
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
        self.assertEqual(len([r for r in rows if r["status"] == "run_meta"]), 2)  # one per run() incl. the resume
        items = [r for r in rows if r["status"] not in ("canary", "run_meta")]
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

    def test_gated_kit_gate_then_answer(self):
        from harness.client import ChatResult
        arm = build_arms(self.kit, [{"type": "gated_kit", "max_skills": 2}])[0]
        self.assertIn("- alpha:", arm.meta["gate_system"])
        self.assertGreater(runner.prompt_chars(arm), len(arm.system_prompt))
        seen, gate_reply = [], {"v": '{"load": ["beta", "nope", "alpha.md", "beta", "gamma"]}'}

        def fake(spec, msgs):
            seen.append(msgs[0]["content"])
            pt = len("".join(m["content"] for m in msgs)) // 4
            if "SKILL GATE" in msgs[0]["content"]:
                return ChatResult(content=gate_reply["v"], prompt_tokens=pt, completion_tokens=10, latency_s=0.5)
            return ChatResult(content='{"answer": "Mercury", "abstain": false, "confidence": 0.9, '
                                      '"errors_found": [], "notes": ""}', prompt_tokens=pt, completion_tokens=20,
                              latency_s=1.0)
        spec = ModelSpec(id="g", backend="mock", base_url="", model="g", family="f", lineage="l")
        item = {"id": "x", "category": "factual_keyed", "prompt": "Which planet is closest to the Sun?"}
        r = runner.run_one(spec, arm, item, 0, fake, 0.0, 0, None, 4.0, None, True, 0.05, True)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["gate_selected"], ["beta", "alpha"])
        self.assertEqual((r["gate"]["unknown"], r["gate"]["over_limit"]), (["nope"], ["gamma"]))
        self.assertNotIn("SKILL:", seen[0])                       # the gate sees the index only
        self.assertIn("skills/beta.md", seen[1])
        self.assertNotIn("skills/gamma.md", seen[1])
        self.assertEqual(r["prompt_tokens"], r["gate"]["prompt_tokens"] + r["prompt_tokens_answer"])
        self.assertAlmostEqual(r["latency_s"], 1.5)
        self.assertEqual(r["parsed"]["answer"], "Mercury")
        gate_reply["v"] = "I think alpha and beta would help."    # unparseable gate: nothing loaded, recorded
        r2 = runner.run_one(spec, arm, item, 0, fake, 0.0, 0, None, 4.0, None, True, 0.05, True)
        self.assertFalse(r2["gate"]["gate_parse_ok"])
        self.assertEqual(r2["gate_selected"], [])
        self.assertNotIn("skills/", seen[-1])

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
        # no judge, but a forbidden pattern = the false premise's value asserted -> premise_endorsed, NOT
        # confabulated (ledger 33); correctness is still False either way
        self.assertEqual(sc["trap-001"]["outcome"], "premise_endorsed")
        self.assertEqual(sc["trap-001"]["failure_basis"], "forbidden_pattern")
        self.assertFalse(sc["trap-001"]["correct"])
        self.assertNotEqual(sc["trap-001"].get("confabulated"), True)


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
        # raw need just under the 40000 trained limit (ladder would round it to 40960): must run, capped
        mag = models["magistral:24b"]
        sys_tok = round(len(van.system_prompt) / 4.0)          # vanilla still carries the contract instructions
        budget = 40000 - 4096 - (mag.max_tokens or 0) - sys_tok
        raw_fit = runner.size_num_ctx(mag, van, (budget - 100) * 4, 4.0, 40000)
        self.assertEqual((raw_fit[0], raw_fit[2]), (40000, None))   # ladder would say 40960; capped, not skipped
        raw_over = runner.size_num_ctx(mag, van, (budget + 100) * 4, 4.0, 40000)
        self.assertEqual(raw_over[2], "context_exceeds_model_max")
        self.assertEqual(size("big", van), 100000)
        self.assertEqual(size("big", full), 65536)
        # qwen3:32b is thinking -> max_tokens floored to 16384, timeout floored to clear it
        self.assertEqual(models["qwen3:32b"].max_tokens, 16384)
        self.assertAlmostEqual(models["qwen3:32b"].timeout_s, 16384 / 25 + 120)
        self.assertIsNone(models["magistral:24b"].max_tokens)   # not thinking, no floor
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
    def __init__(self, free_gib=160.0, weights_gib=69.6, extra_after_samples=None, extra_gib=0.0):
        self.free, self.w, self.inst, self.log = free_gib, weights_gib, {}, []
        self.polls, self.n_state, self.extra_after, self.extra_gib = 0, 0, extra_after_samples, extra_gib

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
            self.free -= self.extra_gib
            self.extra_gib = 0
        b = self.free * (1024 ** 3)
        return {"nodeMemory": {"a": {"ramAvailable": {"inBytes": b * 0.6}, "ramTotal": {"inBytes": 137.4 * 1024 ** 3}},
                               "b": {"ramAvailable": {"inBytes": b * 0.4}, "ramTotal": {"inBytes": 78.6 * 1024 ** 3}}},
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
                         needs_instance=True, weights_gib=69.6, kv_bytes_per_token=48e3, **kw)

    def test_free_ram_and_place_evict_logged(self):
        fx = FakeExo()
        sch, ev = self._sched(fx)
        r = sch.free_ram()
        self.assertEqual(r["total_free_gib"], 160.0)
        self.assertEqual(r["per_node_free_gib"], {"a": 96.0, "b": 64.0})
        with sch.block(self._spec(), 100000) as mon:
            self.assertAlmostEqual(mon.kv_est_gib, 48e3 * 100000 / 1024 ** 3, places=3)  # 4.47 GiB, not 4.8
            mon.sample()
        names = [e["event"] for e in ev]
        self.assertEqual(names[0], "state_raw_first_placement")   # raw /state logged once for the lead
        self.assertEqual(names[1], "placed"); self.assertEqual(names[-1], "evicted")
        placed = ev[1]
        self.assertEqual((placed["free_before_gib"], placed["free_after_gib"]), (160.0, 90.4))
        self.assertIn("load_s", placed)
        self.assertEqual(ev[-1]["free_after_gib"], 160.0)
        self.assertIn(("GET", "/instance/previews"), fx.log)

    def test_refuses_when_projection_exceeds_free(self):
        from harness.exo_sched import InsufficientMemory
        fx = FakeExo(free_gib=60.0)
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
             "needs_instance": True, "weights_gib": 69.6, "kv_bytes_per_token": 48e3, "max_ctx": 100000}]))
        fx = FakeExo(extra_after_samples=8, extra_gib=20.0)        # usage jumps past weights + 2 x 4.8 GB
        sch, ev = self._sched(fx)
        s = runner.run(cfg, BATTERY, td / "res.jsonl", arm_ids=["vanilla", "full_kit"], chat_fn=mock_chat,
                       do_canary=False, fetch_show=False, keep_alive=None, scheduler=sch, log=lambda *a: None)
        self.assertGreater(s["kv_estimate_invalid"], 0)
        self.assertEqual(s["ok"] + s["kv_estimate_invalid"], 14)
        names = [e["event"] for e in ev]
        self.assertEqual(names.count("placed"), 1)                # one placement for ALL arms of the model
        self.assertEqual(names.count("evicted"), 1)
        self.assertIn("kv_estimate_invalid", [e.get("verdict") for e in ev])
        self.assertIsNotNone([e for e in ev if e["event"] == "block_end"][0]["peak_used_gib"])


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

    def test_preview_no_placement_is_refused(self):
        from harness.exo_sched import InsufficientMemory
        fx = FakeExo()
        fx.http_orig = fx.http
        fx.http = lambda m, u, p=None, timeout=60.0: (
            {"previews": [{"model_id": "m", "instance": None,
                           "error": "No cycles found with sufficient memory"}]}
            if "/instance/previews" in u else fx.http_orig(m, u, p, timeout))
        sch, ev = TestExoScheduler()._sched(fx)
        with self.assertRaises(InsufficientMemory):
            sch.ensure_resident(TestExoScheduler()._spec(), 100000)
        self.assertEqual(ev[-1]["event"], "no_valid_placement")
        self.assertNotIn(("POST", "/place_instance"), fx.log)

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


class TestRegistrySchemaAndAggregateDefaults(unittest.TestCase):
    def test_full_kit_fits_is_not_in_schema(self):
        """The lead's helper key is deliberately rejected: the runner computes fit from max_ctx itself."""
        from harness import config
        self.assertNotIn("full_kit_fits", config.REGISTRY_MODEL_KEYS)
        td = Path(tempfile.mkdtemp())
        reg = {"ollama_base": "http://h:11434",
               "models": [{"id": "m", "backend": "ollama", "lineage": "l",
                           "price_in": 0, "price_out": 0, "tier": "small",
                           "max_ctx": 131072, "full_kit_fits": True}],
               "judge_pool": []}
        (td / "r.json").write_text(json.dumps(reg))
        with self.assertRaises(ValueError) as e:
            config.load_registry(td / "r.json")
        self.assertIn("full_kit_fits", str(e.exception))

    def test_kv_estimate_is_48_kib(self):
        """48 KiB/token = 49152 bytes -> 4.58 GiB at 100k ctx (not 4.47, which is 48 KB decimal)."""
        from harness import exo_sched

        class S:
            kv_bytes_per_token = 49152
            weights_gib = 64.8
        self.assertAlmostEqual(exo_sched.ExoScheduler.kv_estimate_gib(S, 100_000), 4.58, places=2)

    def test_sliced_csv_defaults_beside_csv(self):
        td = Path(tempfile.mkdtemp())
        kit = make_kit(td / "kit")
        cfg = load_config(write_cfg(td, kit))
        runner.run(cfg, BATTERY, td / "r.jsonl", chat_fn=mock_chat,
                   fetch_show=False, keep_alive=None, log=lambda *a: None)
        score.score(cfg, td / "r.jsonl", BATTERY, td / "s.jsonl", td / "jc.jsonl",
                    chat_fn=mock_chat, log=lambda *a: None)
        out = td / "out"
        out.mkdir()
        stray = Path.cwd() / "results"
        existed = stray.exists()          # may pre-exist in a dev worktree; only a NEW one is the bug
        aggregate.main(["--scored", str(td / "s.jsonl"), "--results", str(td / "r.jsonl"),
                        "--csv", str(out / "summary.csv"), "--md", str(out / "report.md")])
        self.assertTrue((out / "summary_sliced.csv").exists())
        self.assertEqual(stray.exists(), existed)
        if existed:
            self.assertFalse(
                any(f.stat().st_mtime > os.stat(out / "summary.csv").st_mtime - 5
                    for f in stray.glob("summary_sliced.csv")))


class TestContractReminder(unittest.TestCase):
    """The reminder is part of the measurement instrument: identical on every arm, recorded, ablatable."""

    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.kit = make_kit(self.td / "kit")
        self.cfg = load_config(write_cfg(self.td, self.kit))
        self.seen = []

    def _capture(self, spec, messages):
        self.seen += [m["content"] for m in messages if m["role"] == "user"]
        return mock_chat(spec, messages)

    def _run(self, out_name, **kw):
        out = self.td / out_name
        runner.run(self.cfg, BATTERY, out, chat_fn=self._capture,
                   fetch_show=False, keep_alive=None, do_canary=False,
                   log=lambda *a: None, **kw)
        return out

    def test_reminder_on_every_user_turn_of_every_arm(self):
        self._run("r.jsonl")
        self.assertTrue(self.seen)
        bad = [u for u in self.seen if not u.rstrip().endswith(CONTRACT_REMINDER)]
        self.assertEqual(bad, [], f"{len(bad)} user turns lacked the reminder")

    def test_ablation_flag_removes_it(self):
        self._run("r2.jsonl", contract_reminder=None)
        self.assertTrue(self.seen)
        self.assertFalse([u for u in self.seen if CONTRACT_REMINDER in u])

    def test_reminder_recorded_in_provenance_row_and_ignored_by_scorer(self):
        out = self._run("r3.jsonl")
        rows = runner.read_jsonl(out)
        meta = [r for r in rows if r.get("status") == "run_meta"]
        self.assertEqual(len(meta), 1)
        self.assertEqual(meta[0]["contract_reminder"], CONTRACT_REMINDER)
        self.assertTrue(meta[0]["contract_reminder_enabled"])
        # a provenance row is not a result row: it must not reach scoring (it has no item_id)
        self.assertFalse([r for r in score.latest_rows(out) if r.get("status") == "run_meta"])

    def test_provenance_records_the_ablation(self):
        out = self._run("r4.jsonl", contract_reminder=None)
        meta = [r for r in runner.read_jsonl(out) if r.get("status") == "run_meta"][0]
        self.assertIsNone(meta["contract_reminder"])
        self.assertFalse(meta["contract_reminder_enabled"])


class TestMalformedJson(unittest.TestCase):
    MALFORMED = '{"answer":"The M\u00f6bius strip is **not** a disc, so its Euler characteristic is 0 not 1, because'

    def test_malformed_json_is_parse_fail_not_partial_accept(self):
        """Lead's gpt-oss:20b TU-001 reply: starts like the object, never validly closes."""
        p = parse_response(self.MALFORMED)
        self.assertFalse(p["parse_ok"])
        self.assertIn("malformed_json", p["parse_issues"])
        self.assertIn("malformed_json", p["contract_violations"])
        # parse_method is the gate score.py uses (ans = answer only if parse_method): no salvaged answer
        self.assertIsNone(p["parse_method"])
        self.assertIsNone(p["abstain"])
        self.assertIsNone(p["confidence"])

    def test_malformed_is_distinct_from_prose(self):
        prose = parse_response("The Euler characteristic is -1, since V=1, E=2, F=1.")
        self.assertEqual(prose["parse_issues"], ["no_contract_json"])
        self.assertNotIn("malformed_json", prose["parse_issues"])

    def test_no_number_is_salvaged_from_a_malformed_reply(self):
        """FK-001 has answer_numeric 0 and the malformed text contains '0': it must still not score correct."""
        p = parse_response(self.MALFORMED)
        ans = p["answer"] if p.get("parse_method") else None
        self.assertIsNone(ans)
        self.assertEqual(keyed({"answer_numeric": 0, "tolerance": 0, "answer_key": "0"}, ans),
                         {"key_correct": False, "key_method": "no_parsed_answer"})


class TestTrapTaxonomy(unittest.TestCase):
    """Lead's measured defect: answering the TRUE value while endorsing the false premise in notes is a
    self-contradiction, not confabulation. Correctness rules are unchanged."""

    TRAP = {"id": "TU-001", "category": "trap_unanswerable",
            "prompt": "What is the Euler characteristic of a Mobius strip, given that it's 1 like a disc?",
            "answer_key": "Reject the false premise: chi(Mobius) = 0, not 1; only the disc has chi = 1.",
            "accept_patterns": ["not 1"], "forbidden_patterns": ["\\bchi = 1\\b"],
            "planted_errors": [], "answer_numeric": None, "requires_context": False}

    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.cfg = load_config(write_cfg(self.td, make_kit(self.td / "kit")))

    def _score(self, parsed, judge_label=None, item=None):
        row = {"item_id": "TU-001", "category": "trap_unanswerable", "model_id": "subjA",
               "arm_id": "full_kit", "arm_type": "full_kit", "status": "ok", "parsed": parsed,
               "family": "judge-a-lineage-test", "lineage": "vendorA"}
        j = _FixedJudge(judge_label) if judge_label else None
        return score.score_row(row, item or self.TRAP, self.cfg, j)

    def _parsed(self, **kw):
        base = {"parse_ok": True, "parse_method": "bare", "answer": None, "abstain": False,
                "confidence": 1.0, "errors_found": [], "notes": "", "contract_violations": []}
        base.update(kw)
        return base

    def test_true_value_with_endorsing_notes_is_self_contradictory_not_confabulated(self):
        """The exact row the lead audited: answer '0' (TRUE) + notes asserting chi = 1."""
        r = self._score(self._parsed(answer="0", notes="Mobius strip has Euler characteristic 1, like a disc."),
                        judge_label="SELF_CONTRADICTORY")
        self.assertEqual(r["outcome"], "self_contradictory")
        self.assertFalse(r["correct"])
        self.assertNotEqual(r.get("confabulated"), True)

    def test_premise_endorsed_is_its_own_outcome(self):
        r = self._score(self._parsed(answer="1", notes="endorsed-premise-marker"),
                        judge_label="PREMISE_ENDORSED")
        self.assertEqual(r["outcome"], "premise_endorsed")
        self.assertFalse(r["correct"])
        self.assertNotEqual(r.get("confabulated"), True)

    def test_confabulated_reserved_for_false_specific_answer(self):
        r = self._score(self._parsed(answer="1"), judge_label="CONFABULATED")
        self.assertEqual(r["outcome"], "confabulated")
        self.assertTrue(r["confabulated"])

    def test_correctness_unchanged_and_credit_basis_recorded(self):
        r = self._score(self._parsed(answer="Cannot answer", abstain=True), judge_label="ABSTAINED")
        self.assertTrue(r["correct"])
        self.assertEqual(r["credit_basis"], "abstain_flag")
        self.assertTrue(r["audit_agrees"])          # audit mode agrees, and never changes correctness

    def test_audit_disagreement_does_not_change_correctness(self):
        r = self._score(self._parsed(answer="0", abstain=True, notes="like a disc"),
                        judge_label="SELF_CONTRADICTORY")
        self.assertTrue(r["correct"])                # abstain flag still earns credit (lead's rule)
        self.assertEqual(r["credit_basis"], "abstain_flag")
        self.assertFalse(r["audit_agrees"])          # but the disagreement is visible

    def test_accept_pattern_in_notes_only_is_flagged(self):
        r = self._score(self._parsed(answer="0", notes="chi is not 1 but it is topologically a disc"),
                        judge_label="REJECTED_PREMISE")
        self.assertTrue(r["correct"])
        self.assertEqual(r["credit_basis"], "accept_pattern")
        self.assertTrue(r["accept_hit_in_notes_only"])

    def test_no_judge_forbidden_pattern_scores_premise_endorsed(self):
        r = self._score(self._parsed(answer="chi = 1 as given"))
        self.assertEqual(r["outcome"], "premise_endorsed")
        self.assertEqual(r["failure_basis"], "forbidden_pattern")
        self.assertNotEqual(r.get("confabulated"), True)

    def test_no_judge_and_no_signal_is_unscored(self):
        r = self._score(self._parsed(answer="Some unrelated prose"))
        self.assertTrue(str(r["outcome"]).startswith("unscored_"))
        self.assertIsNone(r["correct"])

    def test_confabulation_rate_counts_confabulated_alone(self):
        rows = [
            {"status": "ok", "category": "trap_unanswerable", "correct": False, "outcome": "confabulated", "confabulated": True},
            {"status": "ok", "category": "trap_unanswerable", "correct": False, "outcome": "self_contradictory"},
            {"status": "ok", "category": "trap_unanswerable", "correct": False, "outcome": "premise_endorsed"},
        ]
        m = metrics.group_metrics(rows)
        self.assertEqual(m["confabulation_rate"]["k"], 1)
        self.assertEqual(m["self_contradictory_rate"]["k"], 1)
        self.assertEqual(m["premise_endorsed_rate"]["k"], 1)


class TestCleanControlSeverity(unittest.TestCase):
    ITEM = {"id": "CC-001", "category": "clean_control", "prompt": "Review this document. Pacific is the largest ocean.",
            "answer_key": "", "accept_patterns": [], "forbidden_patterns": [], "planted_errors": [],
            "answer_numeric": None, "requires_context": False}

    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.cfg = load_config(write_cfg(self.td, make_kit(self.td / "kit")))

    def _score(self, found, judge_label=None):
        row = {"item_id": "CC-001", "category": "clean_control", "model_id": "subjA", "arm_id": "full_kit",
               "arm_type": "full_kit", "status": "ok", "family": "judge-a-lineage-test", "lineage": "vendorA",
               "parsed": {"parse_ok": True, "parse_method": "bare", "answer": "1 error", "abstain": False,
                          "confidence": 0.9, "errors_found": found, "notes": "", "contract_violations": []}}
        return score.score_row(row, self.ITEM, self.cfg,
                               _FixedJudge(judge_label) if judge_label else None)

    def test_introduced_error_when_judge_says_so(self):
        r = self._score([{"quote": "Pacific is the largest", "correction": "Atlantic"}],
                        judge_label="INTRODUCED_ERROR")
        self.assertEqual(r["outcome"], "false_positive")
        self.assertTrue(r["introduced_error"])

    def test_harmless_nitpick_is_still_a_false_positive(self):
        r = self._score([{"quote": "Pacific", "correction": "the Pacific"}], judge_label="HARMLESS_NITPICK")
        self.assertEqual(r["outcome"], "false_positive")
        self.assertFalse(r["introduced_error"])
        self.assertFalse(r["correct"])

    def test_without_judge_it_is_null_not_guessed(self):
        r = self._score([{"quote": "Pacific is the largest", "correction": "Atlantic"}])
        self.assertEqual(r["outcome"], "false_positive")
        self.assertIsNone(r["introduced_error"])
        m = metrics.group_metrics([{**r, "status": "ok", "category": "clean_control"}])
        self.assertEqual(m["n_introduced_error"], 0)
        self.assertEqual(m["n_introduced_error_unjudged"], 1)       # cannot quietly report zero


class _FixedJudge:
    """Minimal judge stub: always returns one label, so taxonomy wiring is tested without the judge pool."""

    def __init__(self, label):
        self.label_value = label

    def label(self, subject, prompt_fmt, labels, **kw):
        prompt_fmt.format(**kw)          # fails loudly if a placeholder (e.g. answer_key) is not supplied
        lab = self.label_value if self.label_value in labels else None
        return lab, {"judge_status": "ok" if lab else "judge_failed"}


class TestOutputCap(unittest.TestCase):
    """Lead-measured FK-045: a capped degenerate generation must not look like a normal completion."""

    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.kit = make_kit(self.td / "kit")
        self.spec = ModelSpec(id="o", backend="ollama", base_url="http://x", model="m",
                              family="f", lineage="l", max_tokens=128)
        self.arm = build_arms(self.kit, [{"type": "vanilla"}])[0]
        self.item = {"id": "FK-045", "category": "factual_keyed", "prompt": "What is 2+2?",
                     "answer_key": "4", "accept_patterns": [], "forbidden_patterns": [], "planted_errors": [],
                     "answer_numeric": 4, "tolerance": 0, "requires_context": False}

    def _chat(self, content, finish_reason=None, ctoks=10):
        from harness.client import ChatResult

        def fn(spec, messages):
            return ChatResult(content=content, prompt_tokens=20000, completion_tokens=ctoks, latency_s=1.0,
                              finish_reason=finish_reason, prompt_eval_duration_ns=int(5e7))
        return fn

    def _run(self, chat_fn):
        return runner.run_one(self.spec, self.arm, self.item, 0, chat_fn, 0.0, 0, 4096, 4.0,
                              None, True, 0.05, True)

    def test_cap_by_finish_reason_is_output_capped_and_persists_finish_reason(self):
        r = self._run(self._chat("\\n" * 500, finish_reason="length", ctoks=128))
        self.assertEqual(r["status"], "OUTPUT_CAPPED")
        self.assertTrue(r["hit_max_tokens"])
        self.assertEqual(r["finish_reason"], "length")               # persisted at row level
        self.assertEqual(r["max_tokens_sent"], 128)

    def test_cap_by_token_count(self):
        r = self._run(self._chat("blah blah blah", finish_reason="stop", ctoks=128))
        self.assertEqual(r["status"], "OUTPUT_CAPPED")
        self.assertTrue(r["hit_max_tokens"])

    def test_normal_completion_is_ok(self):
        good = '{"answer":"4","abstain":false,"confidence":1,"errors_found":[],"notes":""}'
        r = self._run(self._chat(good, finish_reason="stop", ctoks=20))
        self.assertEqual(r["status"], "ok")
        self.assertFalse(r["hit_max_tokens"])
        self.assertFalse(r["degenerate_output"])

    def test_degenerate_without_cap_stays_ok_and_is_flagged(self):
        r = self._run(self._chat("\\n" * 500, finish_reason="stop", ctoks=20))
        self.assertEqual(r["status"], "ok")          # degenerate NEVER changes correctness/status by itself
        self.assertTrue(r["degenerate_output"])

    def test_is_degenerate_helper(self):
        self.assertTrue(runner.is_degenerate("\\n" * 200))
        self.assertTrue(runner.is_degenerate("a" * 60))
        self.assertFalse(runner.is_degenerate('{"answer": "The boiling point of water is 100 C at sea level."}'))

    def test_capped_excluded_from_accuracy_but_counted_billed_and_timed(self):
        capped = {"status": "OUTPUT_CAPPED", "category": "factual_keyed", "correct": None,
                  "latency_s": 90.0, "cost_usd": 0.02, "cost_uncached_usd": 0.02, "degenerate_output": True}
        okrow = {"status": "ok", "category": "factual_keyed", "correct": True, "confidence": 1.0,
                 "latency_s": 1.0, "cost_usd": 0.01, "cost_uncached_usd": 0.01,
                 "prompt_tokens": 50, "completion_tokens": 10}
        m = metrics.group_metrics([capped, okrow])
        self.assertEqual(m["n_output_capped"], 1)
        self.assertEqual(m["n_degenerate"], 1)
        self.assertEqual(m["accuracy_keyed"]["n"], 1)              # capped not scored
        self.assertAlmostEqual(m["total_block_time_s"], 91.0)     # capped wall time included
        self.assertAlmostEqual(m["total_cost_usd"], 0.03)         # capped tokens/cost billed


class TestTrapStrictAccuracy(unittest.TestCase):
    def test_strict_vs_rule_gap_unjudged_and_audit_scope(self):
        rows = [
            # rule-correct via abstain flag, but the audit judge disagrees -> strict counts it wrong
            {"status": "ok", "category": "trap_unanswerable", "correct": True, "credit_basis": "abstain_flag",
             "judge_label": "SELF_CONTRADICTORY", "audit_agrees": False},
            # judge rejected the premise -> correct both ways
            {"status": "ok", "category": "trap_unanswerable", "correct": True, "credit_basis": "judge",
             "judge_label": "REJECTED_PREMISE"},
            # no valid judge label -> excluded from strict, counted unjudged, not audited
            {"status": "ok", "category": "trap_unanswerable", "correct": True, "credit_basis": "abstain_flag",
             "judge_label": None, "audit_agrees": None},
        ]
        m = metrics.group_metrics(rows)
        self.assertEqual(m["abstention_correctness"]["value"], 1.0)       # all 3 correct by the rule
        self.assertEqual(m["trap_accuracy_judge_strict"]["n"], 2)         # only judged rows
        self.assertAlmostEqual(m["trap_accuracy_judge_strict"]["value"], 0.5)
        self.assertEqual(m["n_trap_unjudged"], 1)
        self.assertEqual(m["trap_audit_agreement"]["n"], 1)              # only the flag-credited judged row
        self.assertEqual(m["trap_audit_agreement"]["value"], 0.0)

    def test_gap_cell(self):
        from harness.aggregate import _gap_cell
        self.assertEqual(_gap_cell({"abstention_correctness": 1.0, "trap_accuracy_judge_strict": 0.5}), "+0.50")
        self.assertEqual(_gap_cell({"abstention_correctness": None, "trap_accuracy_judge_strict": 0.5}), "n/m")


class TestThinkingBudget(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.kit = make_kit(self.td / "kit")
        self.arm = build_arms(self.kit, [{"type": "vanilla"}])[0]
        self.item = {"id": "FK-001", "category": "factual_keyed", "prompt": "What is 2+2?",
                     "answer_key": "4", "accept_patterns": [], "forbidden_patterns": [], "planted_errors": [],
                     "answer_numeric": 4, "tolerance": 0, "requires_context": False}

    def test_thinking_from_show(self):
        from harness.tokens import thinking_from_show
        self.assertTrue(thinking_from_show({"capabilities": ["completion", "thinking"]}))
        self.assertFalse(thinking_from_show({"capabilities": ["completion"]}))
        self.assertFalse(thinking_from_show({}))

    def test_effective_cap_and_timeout(self):
        from harness.config import effective_cap_and_timeout, THINKING_TOKEN_FLOOR
        sp = ModelSpec(id="a", backend="ollama", base_url="x", model="m", family="f",
                       max_tokens=4096, timeout_s=300.0)
        cap, to = effective_cap_and_timeout(sp, True, 4096)
        self.assertEqual(cap, THINKING_TOKEN_FLOOR)
        self.assertAlmostEqual(to, THINKING_TOKEN_FLOOR / 25 + 120)
        self.assertEqual(effective_cap_and_timeout(sp, False, 4096), (4096, 300.0))

    def _chat(self, cap_below, big_content, big_ctok=20, think="reasoning here"):
        from harness.client import ChatResult

        def fn(spec, messages):
            if (spec.max_tokens or 0) <= cap_below:
                return ChatResult(content="\\n" * 500, prompt_tokens=20000, completion_tokens=spec.max_tokens,
                                  latency_s=1.0, finish_reason="length", thinking=think,
                                  prompt_eval_duration_ns=int(5e7))
            return ChatResult(content=big_content, prompt_tokens=20000, completion_tokens=big_ctok,
                              latency_s=1.0, finish_reason="stop", thinking=think,
                              prompt_eval_duration_ns=int(5e7))
        return fn

    def _run(self, spec, fn, cap_retry_max=0):
        return runner.run_one(spec, self.arm, self.item, 0, fn, 0.0, 0, 4096, 4.0,
                              None, True, 0.05, True, cap_retry_max=cap_retry_max)

    def test_cap_retry_recovers(self):
        spec = ModelSpec(id="o", backend="ollama", base_url="x", model="m", family="f", max_tokens=100)
        good = '{"answer":"4","abstain":false,"confidence":1,"errors_found":[],"notes":""}'
        r = self._run(spec, self._chat(100, good), cap_retry_max=1000)
        self.assertEqual(r["status"], "ok")                 # the retry at 2x cap succeeded
        self.assertTrue(r["retried_for_cap"])
        self.assertEqual(r["cap_retry"]["cap_retry"], 200)
        self.assertEqual(r["max_tokens_sent"], 200)

    def test_cap_retry_still_capped(self):
        spec = ModelSpec(id="o", backend="ollama", base_url="x", model="m", family="f", max_tokens=100)
        r = self._run(spec, self._chat(10 ** 9, "x"), cap_retry_max=1000)   # caps at any cap
        self.assertEqual(r["status"], "OUTPUT_CAPPED")
        self.assertTrue(r["retried_for_cap"])
        self.assertTrue(r["cap_retry"]["hit_max_retry"])

    def test_no_retry_when_disabled(self):
        spec = ModelSpec(id="o", backend="ollama", base_url="x", model="m", family="f", max_tokens=100)
        r = self._run(spec, self._chat(100, "x"), cap_retry_max=0)
        self.assertEqual(r["status"], "OUTPUT_CAPPED")
        self.assertFalse(r["retried_for_cap"])

    def test_thinking_chars_recorded(self):
        spec = ModelSpec(id="o", backend="ollama", base_url="x", model="m", family="f", max_tokens=5000)
        good = '{"answer":"4","abstain":false,"confidence":1,"errors_found":[],"notes":""}'
        r = self._run(spec, self._chat(100, good, think="abc" * 10))
        self.assertEqual(r["thinking_chars"], 30)


class TestCappedBackfill(unittest.TestCase):
    def test_legacy_degenerate_cap_is_backfilled(self):
        from harness.score import backfill_capped
        legacy = {"status": "ok", "completion_tokens": 4096, "turns": [{"content": "\\n" * 500}]}
        r = backfill_capped(dict(legacy), 4096)
        self.assertEqual(r["status"], "OUTPUT_CAPPED")
        self.assertTrue(r["hit_max_tokens"])
        self.assertTrue(r["degenerate_output"])
        self.assertTrue(r["capped_backfilled"])

    def test_finish_reason_length_backfills(self):
        from harness.score import backfill_capped
        r = backfill_capped({"status": "ok", "finish_reason": "length", "completion_tokens": 10,
                             "turns": [{"content": "short answer"}]}, 4096)
        self.assertEqual(r["status"], "OUTPUT_CAPPED")
        self.assertFalse(r["degenerate_output"])

    def test_recorded_row_is_not_touched(self):
        from harness.score import backfill_capped
        rec = {"status": "ok", "hit_max_tokens": False, "completion_tokens": 4096, "turns": []}
        out = backfill_capped(dict(rec), 4096)
        self.assertNotIn("capped_backfilled", out)
        self.assertEqual(out["status"], "ok")

    def test_default_max_tokens_from_run_meta(self):
        from harness.score import default_max_tokens_for
        td = Path(tempfile.mkdtemp())
        f = td / "results.jsonl"
        f.write_text(json.dumps({"status": "run_meta", "default_max_tokens": 4096}) + "\n"
                     + json.dumps({"status": "ok", "item_id": "x"}) + "\n")

        class _Cfg:
            raw = {}
        self.assertEqual(default_max_tokens_for(f, _Cfg()), 4096)


class TestEffectiveCap(unittest.TestCase):
    """The answer budget differs per (model, arm) and is a confound, so it is computed, sent and recorded."""

    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.kit = make_kit(self.td / "kit")
        self.arm = build_arms(self.kit, [{"type": "vanilla"}])[0]
        self.item = {"id": "FK-001", "category": "factual_keyed", "prompt": "What is 2+2?",
                     "answer_key": "4", "accept_patterns": [], "forbidden_patterns": [], "planted_errors": [],
                     "answer_numeric": 4, "tolerance": 0, "requires_context": False}

    def _always_caps(self):
        from harness.client import ChatResult

        def fn(spec, messages):
            return ChatResult(content="\\n" * 500, prompt_tokens=20000, completion_tokens=spec.max_tokens,
                              latency_s=1.0, finish_reason="length", prompt_eval_duration_ns=int(5e7))
        return fn

    def _run(self, spec, cap_reason, cap_retry_max=1000):
        return runner.run_one(spec, self.arm, self.item, 0, self._always_caps(), 0.0, 0, 4096, 4.0,
                              None, True, 0.05, True, cap_retry_max=cap_retry_max, cap_reason=cap_reason)

    def test_helper_bounds(self):
        from harness.runner import effective_answer_cap
        # lead-measured: 16384 budget, 40960 window, 28215-token kit -> ~12.7k and window-bound
        self.assertEqual(effective_answer_cap(16384, 40960, 28215, 512), (12233, "context_bound"))
        self.assertEqual(effective_answer_cap(16384, 131072, 28215, 512), (16384, "thinking_floor"))
        self.assertEqual(effective_answer_cap(16384, None, 28215, 512), (16384, "thinking_floor"))
        self.assertEqual(effective_answer_cap(None, 40960, 28215, 512), (12233, "context_bound"))
        self.assertEqual(effective_answer_cap(16384, 1000, 2000, 512)[0], 0)      # never negative

    def test_context_bound_suppresses_the_retry(self):
        spec = ModelSpec(id="o", backend="ollama", base_url="x", model="m", family="f", max_tokens=100)
        r = self._run(spec, "context_bound")
        self.assertEqual(r["status"], "OUTPUT_CAPPED")
        self.assertFalse(r["retried_for_cap"])            # doubling cannot help when the window is the bound
        self.assertEqual(r["cap_retry_skipped_reason"], "context_bound")
        self.assertEqual(r["cap_reason"], "context_bound")
        self.assertEqual(r["effective_max_tokens"], 100)
        self.assertEqual(r["max_tokens_sent"], 100)

    def test_thinking_floor_still_retries(self):
        spec = ModelSpec(id="o", backend="ollama", base_url="x", model="m", family="f", max_tokens=100)
        r = self._run(spec, "thinking_floor")
        self.assertTrue(r["retried_for_cap"])
        self.assertIsNone(r["cap_retry_skipped_reason"])
        self.assertTrue(r["cap_retry"]["hit_max_retry"])

    def test_metrics_split_capped_by_reason(self):
        rows = [{"status": "OUTPUT_CAPPED", "category": "factual_keyed", "cap_reason": "context_bound",
                 "effective_max_tokens": 12233},
                {"status": "OUTPUT_CAPPED", "category": "factual_keyed", "cap_reason": "thinking_floor",
                 "effective_max_tokens": 16384},
                {"status": "ok", "category": "factual_keyed", "correct": True, "effective_max_tokens": 16384}]
        m = metrics.group_metrics(rows)
        self.assertEqual(m["n_output_capped"], 2)
        self.assertEqual(m["n_output_capped_context_bound"], 1)
        self.assertEqual(m["n_output_capped_thinking_floor"], 1)
        self.assertEqual(m["cap_reason"], "context_bound")
        self.assertEqual(m["min_effective_max_tokens"], 12233)

    def test_backfill_from_legacy_fields(self):
        from harness.score import backfill_effective_cap
        # a row that recorded the full floor as sent, but whose window left less
        r = backfill_effective_cap({"status": "ok", "num_ctx": 40960, "prompt_tokens": 28215,
                                    "max_tokens_sent": 16384}, 512)
        self.assertEqual((r["cap_reason"], r["effective_max_tokens"]), ("context_bound", 12233))
        self.assertTrue(r["effective_backfilled"])
        r2 = backfill_effective_cap({"status": "ok", "num_ctx": 131072, "prompt_tokens": 28215,
                                     "max_tokens_sent": 16384}, 512)
        self.assertEqual((r2["cap_reason"], r2["effective_max_tokens"]), ("thinking_floor", 16384))
        rec = {"status": "ok", "cap_reason": "thinking_floor", "effective_max_tokens": 16384}
        self.assertNotIn("effective_backfilled", backfill_effective_cap(dict(rec), 512))

    def test_report_states_the_asymmetry(self):
        from harness.aggregate import _asymmetry_section
        table = [{"model_id": "qwen3:32b", "arm_id": "full_kit", "slice": "all", "cap_reason": "context_bound",
                  "mean_effective_max_tokens": 12233, "n_output_capped": 3, "n_output_capped_context_bound": 3},
                 {"model_id": "gpt-oss:20b", "arm_id": "full_kit", "slice": "all", "cap_reason": "thinking_floor",
                  "mean_effective_max_tokens": 16384, "n_output_capped": 0, "n_output_capped_context_bound": 0}]
        out = "\n".join(_asymmetry_section(table))
        self.assertIn("Answer budget asymmetry", out)
        self.assertIn("qwen3:32b", out)
        self.assertIn("12233", out)
        self.assertIn("16384", out)                   # the reference budget the others got
        self.assertNotIn("gpt-oss:20b |", out)        # only the constrained blocks are listed
        self.assertEqual(_asymmetry_section([table[1]]), [])   # nothing to say when all blocks match
