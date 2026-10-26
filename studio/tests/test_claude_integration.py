"""Claude provider, GUI routing and privacy tests with no real Anthropic calls."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

STUDIO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(STUDIO))
import claude_provider as claude
import integration_settings as settings
import model_router as router


class MockKeyring:
    def __init__(self):self.saved={}
    def set_password(self,service,name,value):self.saved[(service,name)]=value
    def get_password(self,service,name):return self.saved.get((service,name))
    def delete_password(self,service,name):self.saved.pop((service,name),None)


class ClaudeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.json=Path(self.tmp.name)/"settings.json"
        self.usage=Path(self.tmp.name)/"openai_usage.sqlite3"
        self.keyring=MockKeyring()
        self.patches=[patch.object(settings,"SETTINGS",self.json),
                      patch.object(settings,"keyring_backend",lambda:self.keyring)]
        for p in self.patches:p.start()

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()

    def test_prefer_claude_routes_ceo_not_to_ollama(self):
        key="sk-ant-test-NOT-REAL"
        cfg=settings.save_ai_providers({"free_only":False,
            "claude_api_key":key,
            "agent_providers":{"ceo":"claude","strategy":"claude","compliance":"claude"},
            "claude_models":{"ceo":"claude-sonnet-4-6"},
            "monthly_limit_usd":12,"claude_monthly_limit_usd":20,
        })
        self.assertTrue(cfg["claude_key_configured"])
        self.assertEqual(cfg["agent_providers"]["ceo"],"claude")
        self.assertFalse(cfg["openai_key_configured"])
        saved=self.json.read_text(encoding="utf-8")
        self.assertNotIn(key,saved)
        env=settings.openai_env({})
        self.assertEqual(router.provider_for("ceo",env),"claude")
        self.assertEqual(router.provider_for("creative",env),"auto")
        self.assertEqual(router.configuration_status(env)["routes"]["ceo"]["model"],
                         "claude-sonnet-4-6")
        self.assertNotIn(key,json.dumps(cfg))

    def test_claude_actual_request_shape_and_vietnamese(self):
        settings.save_ai_providers({"free_only":False,
            "claude_api_key":"sk-ant-test-fake",
            "agent_providers":{"ceo":"claude"},
            "claude_monthly_limit_usd":5,
        })
        seen=[]
        def mocked(request):
            seen.append(json.loads(request.data.decode("utf-8")))
            self.assertEqual(request.get_header("X-api-key"),"sk-ant-test-fake")
            self.assertEqual(request.get_header("Anthropic-version"),"2023-06-01")
            return {"content":[{"type":"text","text":"CEO chọn phương án bằng tiếng Việt."}],
                    "usage":{"input_tokens":500,"output_tokens":150}}
        result=router.chat("ceo","Hãy chốt phương án",
          lambda a,p:self.fail("Claude must not silently fall back to Ollama"),
          self.usage,env=settings.openai_env({}),transport=mocked)
        self.assertIn("tiếng Việt",result)
        self.assertEqual(seen[0]["model"],"claude-sonnet-4-6")
        self.assertIn("TIẾNG VIỆT",seen[0]["system"])
        self.assertEqual(seen[0]["messages"][0]["role"],"user")
        self.assertEqual(claude.usage_month(self.usage.with_name("claude_usage.sqlite3"))["calls"],1)

    def test_claude_key_verification_without_generation(self):
        settings.save_ai_providers({"free_only":False,"claude_api_key":"sk-ant-mock",
            "agent_providers":{"ceo":"claude"}})
        def test_transport(req):
            self.assertTrue(req.full_url.endswith("/v1/models?limit=100"))
            self.assertEqual(req.get_header("X-api-key"),"sk-ant-mock")
            return {"data":[{"id":"claude-sonnet-4-6"}]}
        result=settings.test_claude(http=test_transport)
        self.assertTrue(result["ok"])
        self.assertEqual(result["unlisted_models"],[])

    def test_missing_key_no_silent_fallback(self):
        with self.assertRaisesRegex(ValueError,"Claude"):
            settings.save_ai_providers({"free_only":False,"agent_providers":{"ceo":"claude"}})
        with self.assertRaisesRegex(RuntimeError,"Claude API key"):
            router.chat("ceo","hi",lambda a,p:"fallback",self.usage,
                env={"TEA_AGENT_PROVIDER_CEO":"claude"},transport=lambda r: self.fail("network"))

    def test_limit_and_key_removal(self):
        settings.save_ai_providers({"free_only":False,"claude_api_key":"sk-ant-fake",
            "agent_providers":{"ceo":"claude"},"claude_monthly_limit_usd":0.000001})
        with self.assertRaisesRegex(RuntimeError,"chi phí"):
            router.chat("ceo","test",lambda a,p:"fallback",self.usage,
                        env=settings.openai_env({}),transport=lambda r:self.fail("network"))
        st=settings.remove_claude_key()
        self.assertFalse(st["claude_key_configured"])
        self.assertEqual(st["agent_providers"]["ceo"],"ollama")

    def test_legacy_openai_settings_still_work(self):
        settings.save_openai({"api_key":"sk-test-not-real","openai_agents":["strategy"]})
        self.assertEqual(settings.status()["agent_providers"]["strategy"],"openai")
        self.assertEqual(router.provider_for("strategy",settings.openai_env({})),"openai")


if __name__=="__main__":unittest.main()
