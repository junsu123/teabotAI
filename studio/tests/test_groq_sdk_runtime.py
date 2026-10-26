"""Production Groq SDK parity tests. No real network connections or real API keys."""
import sys
import types
import unittest
from unittest.mock import patch

from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import free_cloud_providers as cloud


class FakeStatusError(Exception):
    def __init__(self,status_code):self.status_code=status_code
class FakeConnectionError(Exception):pass
class FakeAPIError(Exception):pass

class FakeResponse:
    def __init__(self,data):self.data=data
    def model_dump(self):return self.data

class GroqSdkTests(unittest.TestCase):
    def setUp(self):
        self.calls=[]
        self.closed=0
        self.returned={"choices":[{"message":{"content":"Xin chào bằng tiếng Việt."},"finish_reason":"stop"}]}
        owner=self
        class Client:
            def __init__(self,*,api_key,timeout,max_retries):
                owner.calls.append(("init",api_key,timeout,max_retries))
                self.chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=self.generate))
                self.models=types.SimpleNamespace(list=self.list_models)
            def generate(self,**kwargs):
                owner.calls.append(("chat",kwargs))
                return FakeResponse(owner.returned)
            def list_models(self):
                owner.calls.append(("models",))
                return FakeResponse({"data":[{"id":"openai/gpt-oss-120b"},{"id":"openai/gpt-oss-20b"}]})
            def close(self):owner.closed+=1
        fake=types.ModuleType("groq")
        fake.Groq=Client
        fake.APIStatusError=FakeStatusError
        fake.APIConnectionError=FakeConnectionError
        fake.APIError=FakeAPIError
        self.patch=patch.dict(sys.modules,{"groq":fake})
        self.patch.start()
    def tearDown(self):self.patch.stop()

    def test_real_runtime_uses_official_sdk_with_saved_key(self):
        key="gsk_TEST_KEY_NOT_REAL"
        actual=cloud.groq_chat("ceo","Lập kế hoạch",key=key,model="openai/gpt-oss-120b")
        self.assertIn("Xin chào",actual)
        self.assertEqual(self.calls[0][0:2],("init",key))
        call=self.calls[1]
        self.assertEqual(call[0],"chat")
        self.assertEqual(call[1]["model"],"openai/gpt-oss-120b")
        self.assertEqual(call[1]["messages"][1]["role"],"user")
        self.assertIn("Lập kế hoạch",call[1]["messages"][1]["content"])
        self.assertIn("tiếng việt",call[1]["messages"][0]["content"].lower())
        self.assertEqual(call[1]["reasoning_effort"],"low")
        self.assertEqual(self.closed,1)

    def test_sdk_models_list_and_short_chat(self):
        key="gsk_TEST_NOT_REAL"
        result=cloud.test_groq(key)
        self.assertTrue(result["ok"])
        self.assertEqual(self.calls[1][0],"models")
        result2=cloud.test_groq_chat(key)
        self.assertTrue(result2["ok"])
        self.assertEqual(self.calls[-1][0],"chat")
        self.assertEqual(self.calls[-1][1]["model"],"openai/gpt-oss-120b")
        self.assertEqual(self.closed,2)

    def test_sdk_saved_agent_uses_exact_selected_model(self):
        result=cloud.test_saved_groq_agent("gsk_NO_REAL_KEY","ceo","openai/gpt-oss-120b")
        self.assertTrue(result["ok"])
        self.assertEqual(result["model"],"openai/gpt-oss-120b")
        self.assertEqual(self.calls[1][1]["model"],"openai/gpt-oss-120b")

    def test_sdk_status_errors_never_echo_secrets(self):
        def fail(*args,**kwargs):
            raise FakeStatusError(403)
        # Set mock SDK create method via constructor override.
        fake=sys.modules["groq"]
        old=fake.Groq
        class Denied(old):
            def generate(self,**kwargs):return fail()
        fake.Groq=Denied
        try:
            with self.assertRaisesRegex(RuntimeError,"Groq SDK HTTP 403") as recorded:
                cloud.groq_chat("ceo","test",key="gsk_SECRET_MUST_NOT_APPEAR",model="openai/gpt-oss-120b")
            self.assertNotIn("gsk_SECRET_MUST_NOT_APPEAR",str(recorded.exception))
        finally:
            fake.Groq=old

    def test_sdk_rate_limit_is_temporary(self):
        fake=sys.modules["groq"]
        old=fake.Groq
        class Throttled(old):
            def generate(self,**kwargs):raise FakeStatusError(429)
        fake.Groq=Throttled
        try:
            with self.assertRaisesRegex(cloud.TemporaryProviderError,"429"):
                cloud.groq_chat("ceo","test",key="gsk_dummy",model="openai/gpt-oss-120b")
        finally:
            fake.Groq=old

if __name__=="__main__":
    unittest.main()
