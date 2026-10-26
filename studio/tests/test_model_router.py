"""Offline tests for Vietnamese agent language and optional model routing."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

STUDIO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(STUDIO))
import model_router as router

class ModelRouterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Path(self.tmp.name)/"usage.sqlite3"
    def tearDown(self):
        self.tmp.cleanup()

    def test_local_by_default_no_network(self):
        calls=[]
        def local(agent,prompt):
            calls.append((agent,prompt))
            return "Phương án đã được soạn bằng tiếng Việt."
        result=router.chat("ceo","Lập kế hoạch",local,self.db,env={})
        self.assertIn("tiếng Việt",result)
        self.assertEqual(len(calls),1)
        self.assertIn("tiếng Việt",calls[0][1])
        self.assertTrue(self.db.exists())  # Records the provider actually used.

    def test_provider_selection_and_cost_opt_in(self):
        env={"TEA_OPENAI_AGENTS":"ceo,strategy,compliance",
             "OPENAI_API_KEY":"test_key",
             "TEA_OPENAI_MONTHLY_LIMIT_USD":"5"}
        self.assertEqual(router.provider_for("ceo",env),"openai")
        self.assertEqual(router.provider_for("research",env),"ollama")
        self.assertEqual(router.model_for("ceo",env),"gpt-6.1-sol")
        self.assertEqual(router.model_for("creative",env),"gpt-6-luna")
        seen=[]
        def fake_transport(request):
            seen.append(json.loads(request.data.decode("utf-8")))
            self.assertEqual(request.get_header("Authorization"), "Bearer test_key")
            return {
                "output":[{"type":"reasoning","summary":[]},
                          {"type":"message","content":[
                            {"type":"output_text","text":"CEO chọn thử nghiệm 2 tiêu đề bằng tiếng Việt."}]}],
                "usage":{"input_tokens":600,"output_tokens":120}
            }
        def no_local(agent,prompt):
            raise AssertionError("Paid route should not call Ollama")
        result=router.chat("ceo","Phân tích rủi ro",no_local,self.db,env=env,
                           transport=fake_transport)
        self.assertIn("tiếng Việt",result)
        self.assertEqual(seen[0]["model"],"gpt-6.1-sol")
        self.assertEqual(seen[0]["store"],False)
        self.assertIn("TIẾNG VIỆT",seen[0]["instructions"])
        self.assertEqual(router.usage_month(self.db)["calls"],1)

    def test_missing_key_does_not_silently_use_local(self):
        env={"TEA_OPENAI_AGENTS":"ceo"}
        with self.assertRaisesRegex(RuntimeError,"OPENAI_API_KEY"):
            router.chat("ceo","abc",lambda a,p:"Fallback",self.db,env=env)

    def test_explicit_limit_blocks_network(self):
        env={"TEA_OPENAI_AGENTS":"ceo",
             "OPENAI_API_KEY":"dummy",
             "TEA_OPENAI_MONTHLY_LIMIT_USD":"0.000001"}
        with self.assertRaisesRegex(RuntimeError,"ngân sách"):
            router.chat("ceo","Test",lambda a,p:"No",self.db,
                        env=env,transport=lambda req: self.fail("Network should not be called"))

    def test_refuse_unapproved_model_and_agent(self):
        with self.assertRaises(ValueError):
            router.enabled_agents({"TEA_OPENAI_AGENTS":"admin"})
        with self.assertRaises(ValueError):
            router.model_for("ceo",{"TEA_OPENAI_MODEL_CEO":"unknown"})
        with self.assertRaises(ValueError):
            router.provider_for("random",{})

    def test_vietnamese_policy_preserves_json_identifiers(self):
        self.assertIn("tiếng Việt",router.VIETNAMESE_RULES)
        self.assertIn("JSON",router.VIETNAMESE_RULES)

if __name__=="__main__":
    unittest.main()
