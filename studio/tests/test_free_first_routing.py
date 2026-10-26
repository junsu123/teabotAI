"""Offline tests for automatic Gemini primary → Groq secondary routing."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from io import BytesIO
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

    def test_free_mode_is_default_and_rejects_paid_selection(self):
        self.assertTrue(settings.status()["free_only"])
        with self.assertRaisesRegex(ValueError,"CHỈ MODEL"):
            settings.save_ai_providers({"agent_providers":{"ceo":"claude"}})
        with self.assertRaisesRegex(ValueError,"CHỈ MODEL"):
            settings.save_ai_providers({"agent_providers":{"ceo":"auto"},
                                        "allow_paid_fallback":True})
        self.assertTrue(settings.status()["free_only"])

    def test_free_only_blocks_paid_keys_even_from_legacy_config(self):
        self.setup_free()
        env=settings.openai_env({})
        env.update({"TEA_AGENT_PROVIDER_CEO":"openai","OPENAI_API_KEY":"fake",
                    "TEA_ALLOW_PAID_FALLBACK":"1"})
        with self.assertRaisesRegex(RuntimeError,"CHỈ MODEL"):
            model_router.chat("ceo","Kiểm tra",
                lambda a,p:self.fail("Not local"),self.db,
                env=env,transport=lambda req:self.fail("Paid request not permitted"))

    def test_free_only_autorouting_never_uses_paid_provider(self):
        self.setup_free()
        env=settings.openai_env({})
        env["TEA_ALLOW_PAID_FALLBACK"]="1"
        env["ANTHROPIC_API_KEY"]="fake-paid"
        env["OPENAI_API_KEY"]="fake-paid"
        seen=[]
        def fail_cloud(req):
            seen.append(req.full_url)
            raise HTTPError(req.full_url,429,"Slow",hdrs=None,fp=None)
        result=model_router.chat("ceo","Bản nháp",lambda a,p:"Phản hồi Ollama",
            self.db,env=env,transport=fail_cloud)
        self.assertEqual(result,"Phản hồi Ollama")
        self.assertEqual(len(seen),2)

    def test_only_free_tier_eligible_models_in_lists(self):
        self.assertIn("gemini-3.8-flash",cloud.GEMINI_FREE_TIER_MODELS)
        self.assertIn("gemini-2.5-flash-lite",cloud.GEMINI_FREE_TIER_MODELS)
        self.assertIn("openai/gpt-oss-120b",cloud.GROQ_FREE_TIER_MODELS)
        self.assertNotIn("claude-sonnet-4-6",cloud.GEMINI_FREE_TIER_MODELS)

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

    def test_unsaved_gemini_key_can_be_checked_before_save(self):
        def read_models(req):
            self.assertEqual(req.get_header("X-goog-api-key"),"gemini-unsaved-temporary")
            return {"models":[{"name":"models/gemini-3.8-flash"}]}
        checked=settings.test_gemini(http=read_models,
                                     key_override="gemini-unsaved-temporary")
        self.assertTrue(checked["ok"])
        self.assertIn("gemini-3.8-flash",checked["supported_models"])
        self.assertFalse(settings.status()["gemini_key_configured"])

    def test_saved_groq_agent_checks_saved_db_key_and_selected_ceo_model(self):
        self.setup_free()
        self.assertEqual(settings.read()["groq_models"]["ceo"],"openai/gpt-oss-120b")
        observed=[]
        def call(req):
            observed.append(req)
            self.assertEqual(req.get_method(),"POST")
            self.assertEqual(req.get_header("Authorization"),"Bearer test-groq-not-real")
            payload=json.loads(req.data.decode("utf-8"))
            self.assertEqual(payload["model"],"openai/gpt-oss-120b")
            self.assertEqual(payload["reasoning_effort"],"low")
            self.assertIs(payload["include_reasoning"],False)
            self.assertIn("system",payload["messages"][0]["role"])
            return {"choices":[{"message":{"content":"Kết nối hoạt động."}}]}
        result=settings.test_saved_groq_agent("ceo",http=call)
        self.assertTrue(result["ok"])
        self.assertEqual(result["model"],"openai/gpt-oss-120b")
        self.assertEqual(result["key_source"],"encrypted_sqlite")
        self.assertEqual(len(observed),1)
        self.assertNotIn("test-groq-not-real",str(result))

    def test_unsaved_test_key_does_not_replace_runtime_key(self):
        self.setup_free()
        old="test-groq-not-real"
        new="gsk-new-key-only-in-test"
        def check_typed(req):
            self.assertEqual(req.get_header("Authorization"),"Bearer "+new)
            return {"data":[{"id":"openai/gpt-oss-120b"}]}
        self.assertTrue(settings.test_groq(http=check_typed,key_override=new)["ok"])
        def check_saved(req):
            self.assertEqual(req.get_header("Authorization"),"Bearer "+old)
            return {"choices":[{"message":{"content":"OK"}}]}
        self.assertTrue(settings.test_saved_groq_agent("ceo",http=check_saved)["ok"])
        # Saving the updated key must cause the runtime diagnostic to use it.
        settings.set_secret(settings.GROQ_SECRET,new)
        def check_replaced(req):
            self.assertEqual(req.get_header("Authorization"),"Bearer "+new)
            return {"choices":[{"message":{"content":"OK"}}]}
        self.assertTrue(settings.test_saved_groq_agent("ceo",http=check_replaced)["ok"])

    def test_agent_specific_runtime_403_includes_safe_model(self):
        self.setup_free()
        env=settings.openai_env({})
        env["TEA_AGENT_PROVIDER_CEO"]="groq"
        def forbidden(req):
            raise HTTPError(req.full_url,403,"Forbidden",hdrs=None,fp=BytesIO(b""))
        with self.assertRaisesRegex(RuntimeError,"Groq/openai/gpt-oss-120b") as result:
            model_router.chat("ceo","Nhiệm vụ của CEO",
                lambda a,p:self.fail("Do not fall back silently"),
                self.db,env=env,transport=forbidden)
        self.assertIn("HTTP 403",str(result.exception))
        self.assertNotIn(env["GROQ_API_KEY"],str(result.exception))

    def test_live_groq_chat_distinguishes_models_403_and_chat_success(self):
        # The models listing may fail while the chat-completions endpoint works.
        # Do not silently consume tokens from the ordinary /models test.
        def forbidden_list(req):
            raise HTTPError(req.full_url,403,"Forbidden",hdrs=None,fp=BytesIO(b""))
        with self.assertRaisesRegex(RuntimeError,"HTTP 403"):
            settings.test_groq(http=forbidden_list,key_override="gsk-fake")
        captured=[]
        def ok_chat(req):
            captured.append(req)
            self.assertEqual(req.get_method(),"POST")
            self.assertTrue(req.full_url.endswith("/chat/completions"))
            self.assertEqual(req.get_header("Authorization"),"Bearer gsk-fake")
            body=json.loads(req.data)
            self.assertEqual(body["model"],"openai/gpt-oss-120b")
            self.assertEqual(body["max_completion_tokens"],100)
            self.assertEqual(len(body["messages"]),1)
            return {"choices":[{"message":{"role":"assistant","content":"OK"}}]}
        response=settings.test_groq_chat(http=ok_chat,key_override="gsk-fake")
        self.assertTrue(response["ok"])
        self.assertEqual(response["sample"],"OK")
        self.assertEqual(len(captured),1)
        self.assertFalse(settings.status()["groq_key_configured"])

    def test_live_groq_chat_403_reports_restriction(self):
        def denied(req):
            raise HTTPError(req.full_url,403,"Forbidden",hdrs=None,
                            fp=BytesIO(b'{"error":{"type":"permissions_error"}}'))
        with self.assertRaisesRegex(RuntimeError,"403"):
            settings.test_groq_chat(http=denied,key_override="gsk-fake")

    def test_live_groq_chat_no_key_never_calls_network(self):
        with self.assertRaisesRegex(ValueError,"API key"):
            settings.test_groq_chat(http=lambda req:self.fail("Never call network"))

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

    def test_groq_403_org_permission_code_is_explained_without_leaks(self):
        secret="DONOT_ECHO_SECRET"
        payload=json.dumps({"error":{"type":"permissions_error",
                    "code":"model_permission_blocked_org",
                    "message":"Blocked; leaked "+secret}}).encode()
        def blocked(req):
            raise HTTPError(req.full_url,403,"Forbidden",hdrs=None,fp=BytesIO(payload))
        with self.assertRaisesRegex(RuntimeError,"cấp tổ chức") as found:
            settings.test_groq(http=blocked,key_override="gsk-test-placeholder")
        self.assertNotIn(secret,str(found.exception))

    def test_groq_403_project_permission_code_is_explained(self):
        payload=json.dumps({"error":{"type":"permissions_error",
                    "code":"model_permission_blocked_project"}}).encode()
        def blocked(req):
            raise HTTPError(req.full_url,403,"Forbidden",hdrs=None,fp=BytesIO(payload))
        with self.assertRaisesRegex(RuntimeError,"cấp dự án"):
            settings.test_groq(http=blocked,key_override="gsk-test-placeholder")

    def test_groq_403_returns_safe_provider_error_code(self):
        secret="DO_NOT_EXPOSE_KEY"
        raw=json.dumps({"error":{"code":"access_denied","type":"permissions_error",
           "message":"This message contains "+secret}}).encode()
        def reject(req):
            raise HTTPError(req.full_url,403,"Forbidden",hdrs=None,fp=BytesIO(raw))
        with self.assertRaisesRegex(RuntimeError,"access_denied") as result:
            settings.test_groq(http=reject,key_override="gsk-test-placeholder")
        self.assertNotIn(secret,str(result.exception))
        self.assertIn("đọc danh sách model",str(result.exception))

    def test_groq_403_unsafe_error_code_is_hidden(self):
        code="gsk-not-a-real-key-THIS_MUST_NOT_APPEAR_TOKEN_VALUE_TOO_LONG_TO_BE_SAFE_ECHO"
        raw=json.dumps({"error":{"code":code,"message":"Denied"}}).encode()
        def reject(req):
            raise HTTPError(req.full_url,403,"Forbidden",hdrs=None,fp=BytesIO(raw))
        with self.assertRaises(RuntimeError) as result:
            settings.test_groq(http=reject,key_override="gsk-test-placeholder")
        self.assertNotIn(code,str(result.exception))

    def test_groq_html_access_denial_mentions_network_layer(self):
        def reject(req):
            raise HTTPError(req.full_url,403,"Forbidden",hdrs=None,
                            fp=BytesIO(b"<!doctype html><html><body>Forbidden</body></html>"))
        with self.assertRaisesRegex(RuntimeError,"lớp bảo vệ mạng"):
            settings.test_groq(http=reject,key_override="gsk-test-placeholder")

    def test_groq_403_unknown_does_not_claim_model_problem(self):
        def blocked(req):
            raise HTTPError(req.full_url,403,"Forbidden",hdrs=None,fp=BytesIO(b""))
        with self.assertRaisesRegex(RuntimeError,"không có quyền"):
            settings.test_groq(http=blocked,key_override="gsk-test-placeholder")

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
