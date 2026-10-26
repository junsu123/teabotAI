"""Offline integration setup tests. No live OpenAI or Telegram requests."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

STUDIO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(STUDIO))
import integration_settings as settings
import model_router

class FakeKeyring:
    def __init__(self):self.store={}
    def get_password(self,service,name):return self.store.get((service,name))
    def set_password(self,service,name,value):self.store[(service,name)]=value
    def delete_password(self,service,name):self.store.pop((service,name),None)

class SetupTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.settings_file=Path(self.folder.name)/"settings.json"
        self.fake=FakeKeyring()
        self.p1=patch.object(settings,"SETTINGS",self.settings_file)
        self.p2=patch.object(settings,"keyring_backend",lambda:self.fake)
        self.p1.start();self.p2.start()
    def tearDown(self):
        self.p2.stop();self.p1.stop();self.folder.cleanup()

    def test_openai_form_can_enable_ceo_and_save_key_safely(self):
        token="sk-mock-integration-key-not-real"
        status=settings.save_openai({"api_key":token,"openai_agents":["ceo"],
             "openai_models":{"ceo":"gpt-6.1-sol"},"monthly_limit_usd":7})
        self.assertTrue(status["openai_key_configured"])
        self.assertEqual(status["openai_agents"],["ceo"])
        self.assertNotIn(token,self.settings_file.read_text(encoding="utf-8"))
        self.assertNotIn(token,json.dumps(status))
        self.assertEqual(settings.openai_env({})["OPENAI_API_KEY"],token)
        self.assertEqual(model_router.provider_for("ceo",settings.openai_env({})),"openai")
        self.assertEqual(model_router.provider_for("creative",settings.openai_env({})),"ollama")

    def test_telegram_token_only_in_keyring_and_testable(self):
        token="0000000000:FAKE_TEST_TOKEN_FOR_LOCAL_CHECK"
        status=settings.save_telegram({"bot_token":token,
             "telegram_allowed_ids":"12345678, 987654321",
             "telegram_autostart":True})
        self.assertEqual(status["telegram_allowed_ids"],["12345678","987654321"])
        self.assertNotIn(token,self.settings_file.read_text(encoding="utf-8"))
        self.assertNotIn(token,json.dumps(status))
        def fake_request(req):
            self.assertTrue(req.full_url.startswith("https://api.telegram.org/bot"))
            return {"ok":True,"result":{"username":"my_testing_bot"}}
        response=settings.test_telegram(http=fake_request)
        self.assertEqual(response["bot_username"],"my_testing_bot")
        self.assertNotIn(token,str(response))
        self.assertEqual(settings.telegram_env()["TEA_TELEGRAM_TOKEN"],token)

    def test_openai_read_only_connection_test(self):
        settings.save_openai({"api_key":"sk-test-not-real",
              "openai_agents":["ceo"],"monthly_limit_usd":12})
        def fake_request(req):
            self.assertEqual(req.full_url,"https://api.openai.com/v1/models")
            self.assertTrue(req.get_header("Authorization").startswith("Bearer "))
            return {"data":[{"id":"gpt-6.1-sol"}]}
        checked=settings.test_openai(http=fake_request)
        self.assertTrue(checked["ok"])
        self.assertEqual(checked["unlisted_models"],[])

    def test_reject_invalid_telegram_id_and_disabled_api_keys(self):
        with self.assertRaises(ValueError):
            settings.save_telegram({"bot_token":"fake","telegram_allowed_ids":"@user",
                                    "telegram_autostart":False})
        with self.assertRaises(ValueError):
            settings.save_openai({"openai_agents":["ceo"]})
        self.assertFalse(settings.status()["openai_key_configured"])
        self.assertFalse(settings.status()["telegram_token_configured"])

    def test_gui_settings_override_environment(self):
        settings.save_openai({"openai_agents":[]})
        env=settings.openai_env({"TEA_OPENAI_AGENTS":"ceo",
                                 "OPENAI_API_KEY":"legacy-test-key-not-real"})
        self.assertEqual(env["TEA_OPENAI_AGENTS"],"")
        self.assertEqual(env["OPENAI_API_KEY"],"")
        self.assertEqual(model_router.provider_for("ceo",env),"ollama")

if __name__=="__main__":
    unittest.main()
