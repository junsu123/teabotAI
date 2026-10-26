"""Offline tests for automatic Gemini primary → Groq secondary routing."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError

STUDIO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(STUDIO))
import model_router
import free_cloud_providers as cloud
import integration_settings as settings
from unittest.mock import patch


class FakeKeyring:
    def __init__(self):self.values={}
    def set_password(self,svc,name,value):self.values[(svc,name)]=value
    def get_password(self,svc,name):return self.values.get((svc,name))
    def delete_password(self,svc,name):self.values.pop((svc,name),None)


class FreeFirstTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Path(self.tmp.name)/"usage.sqlite3"
        self.keyring=FakeKeyring()
        self.p1=patch.object(settings,"SETTINGS",Path(self.tmp.name)/"settings.json")
        self.p2=patch.object(settings,"keyring_backend",lambda:self.keyring)
        self.p1.start();self.p2.start()
    def tearDown(self):
        self.p2.stop();self.p1.stop();self.tmp.cleanup()

    def setup_free(self):
        return settings.save_ai_providers({
            "gemini_api_key":"test-gemini-not-real",
            "groq_api_key":"test-groq-not-real",
            "agent_providers":{"ceo":"auto","creative":"auto"},
            "provider_priority":["gemini","groq","claude","openai","ollama"],
            "allow_paid_fallback":False,
            "gemini_models":{"ceo":"gemini-3.8-flash"},
            "groq_models":{"ceo":"openai/gpt-oss-120b"},
        })

    def test_gui_settings_and_secrets_not_on_disk(self):
        result=self.setup_free()
        self.assertTrue(result["gemini_key_configured"])
        self.assertTrue(result["groq_key_configured"])
        disk=(Path(self.tmp.name)/"settings.json").read_text()
        self.assertNotIn("test-gemini-not-real",disk)
        self.assertNotIn("test-groq-not-real",disk)
        self.assertEqual(result["provider_priority"][0:2],["gemini","groq"])
        self.assertFalse(result["allow_paid_fallback"])
        self.assertEqual(model_router.provider_for("ceo",settings.openai_env({})),"auto")

    def test_gemini_wins_if_available(self):
        self.setup_free()
        requests=[]
        def respond(req):
            requests.append(req.full_url)
            self.assertEqual(req.get_header("X-goog-api-key"),"test-gemini-not-real")
            return {"candidates":[{"content":{"parts":[{"text":"CEO chọn phương án Gemini."}]}}]}
        answer=model_router.chat("ceo","Phân tích yêu cầu",lambda a,p:self.fail("Ollama used"),
              self.db,env=settings.openai_env({}),transport=respond)
        self.assertIn("Gemini",answer)
        self.assertEqual(len(requests),1)
        self.assertIn(":generateContent",requests[0])

    def test_quota_429_uses_groq_instead(self):
        self.setup_free()
        requests=[]
        def respond(req):
            requests.append(req.full_url)
            if "googleapis" in req.full_url:
                raise HTTPError(req.full_url,429,"Limit",hdrs=None,fp=None)
            self.assertEqual(req.get_header("Authorization"),"Bearer test-groq-not-real")
            return {"choices":[{"message":{"content":"CEO đã dùng Groq dự phòng."}}]}
        answer=model_router.chat("ceo","Bản nháp tiếng Việt",
            lambda a,p:self.fail("Local invoked"),self.db,
            env=settings.openai_env({}),transport=respond)
        self.assertIn("Groq",answer)
        self.assertEqual(len(requests),2)
        self.assertIn("api.groq.com",requests[1])

    def test_both_clouds_temporarily_down_falls_to_local_not_paid(self):
        self.setup_free()
        env=settings.openai_env({})
        # Even if keys are present, paid fallback must require explicit opt-in.
        env["OPENAI_API_KEY"]="fake-paid"
        env["ANTHROPIC_API_KEY"]="fake-paid"
        seen=[]
        def failing(req):
            seen.append(req.full_url)
            raise HTTPError(req.full_url,429,"Limit",hdrs=None,fp=None)
        result=model_router.chat("ceo","Yêu cầu",
            lambda a,p:"Ollama dự phòng đã xử lý",self.db,
            env=env,transport=failing)
        self.assertIn("Ollama",result)
        self.assertEqual(len(seen),2)

    def test_bad_credential_does_not_silently_switch(self):
        self.setup_free()
        seen=[]
        def respond(req):
            seen.append(req.full_url)
            raise HTTPError(req.full_url,401,"Unauthorized",hdrs=None,fp=None)
        with self.assertRaisesRegex(RuntimeError,"401"):
            model_router.chat("ceo","Yêu cầu",
                lambda a,p:self.fail("Must not fall back on invalid credential"),
                self.db,env=settings.openai_env({}),transport=respond)
        self.assertEqual(len(seen),1)

    def test_unsaved_groq_key_and_permissions(self):
        # The test button must work before the Save button.
        def read_models(request):
            self.assertEqual(request.get_header("Authorization"),"Bearer gsk-only-temporary")
            return {"data":[{"id":"openai/gpt-oss-120b"}]}
        test=settings.test_groq(http=read_models,key_override="gsk-only-temporary")
        self.assertTrue(test["ok"])
        self.assertIn("openai/gpt-oss-120b",test["supported_models"])
        self.assertFalse(settings.status()["groq_key_configured"])

    def test_wrong_grok_key_explained(self):
        with self.assertRaisesRegex(ValueError,"Grok"):
            settings.test_groq(key_override="xai-this-is-not-a-groq-key")

    def test_groq_auth_error_explained(self):
        def reject(request):
            raise HTTPError(request.full_url,401,"Unauthorized",hdrs=None,fp=None)
        with self.assertRaisesRegex(RuntimeError,"HTTP 401"):
            settings.test_groq(http=reject,key_override="gsk-sample")

    def test_groq_models_missing_gives_visible_warning(self):
        result=settings.test_groq(http=lambda req:{"data":[{"id":"custom/model"}]},
                                  key_override="gsk-sample")
        self.assertTrue(result["ok"])
        self.assertEqual(result["supported_models"],[])
        self.assertIn("Không có model",result["warning"])

    def test_direct_provider_and_free_key_tests(self):
        cfg=self.setup_free()
        settings.save_ai_providers({"agent_providers":{"ceo":"groq"}})
        env=settings.openai_env({})
        self.assertEqual(model_router.provider_for("ceo",env),"groq")
        models=settings.test_gemini(http=lambda req:{
            "models":[{"name":"models/gemini-3.8-flash"}]})
        self.assertIn("gemini-3.8-flash",models["supported_models"])
        groq=settings.test_groq(http=lambda req:{
            "data":[{"id":"openai/gpt-oss-120b"}]})
        self.assertIn("openai/gpt-oss-120b",groq["supported_models"])
        settings.remove_gemini_key()
        self.assertFalse(settings.status()["gemini_key_configured"])

if __name__=="__main__":unittest.main()
