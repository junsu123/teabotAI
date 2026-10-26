"""Encrypted local SQLite integration vault: real crypto, mocked OS key store.

Never make network calls or expose fake keys in logs.
"""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

STUDIO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(STUDIO))
import integration_settings as settings
import secret_vault


class MemoryKeyring:
    def __init__(self):self.values={}
    def get_password(self,service,name):return self.values.get((service,name))
    def set_password(self,service,name,value):self.values[(service,name)]=value
    def delete_password(self,service,name):self.values.pop((service,name),None)


class EncryptedIntegrationVaultTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/"integrations.local.json"
        self.keyring=MemoryKeyring()
        self.patches=[
            patch.object(settings,"SETTINGS",self.path),
            patch.object(settings,"keyring_backend",lambda:self.keyring),
        ]
        for p in self.patches:p.start()

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

    def test_all_provider_secrets_are_encrypted_sqlite_and_revealable(self):
        values={"gemini":"AIza-FAKE-NOT-REAL",
                "groq":"gsk-test-NOT-REAL",
                "claude":"sk-ant-test-NOT-REAL",
                "openai":"sk-test-NOT-REAL"}
        mapping={"gemini":settings.GEMINI_SECRET,"groq":settings.GROQ_SECRET,
                 "claude":settings.CLAUDE_SECRET,"openai":settings.OPENAI_SECRET}
        for k,v in values.items():
            settings.set_secret(mapping[k],v)
        db=secret_vault._db_path(self.path)
        self.assertTrue(db.is_file())
        raw=db.read_bytes()
        self.assertEqual(raw[:16],b"SQLite format 3\x00")
        for k,v in values.items():
            self.assertNotIn(v.encode(),raw)
            self.assertEqual(settings.reveal_secret(k),v)
            self.assertNotIn(v,json.dumps(settings.status(),ensure_ascii=False))
            self.assertNotIn(v,settings.openai_env({}).get("TEA_PROVIDER_PRIORITY",""))
            self.assertIsNone(self.keyring.get_password(settings.SERVICE,mapping[k]))
        master=self.keyring.get_password(settings.SERVICE,secret_vault.MASTER_KEY_NAME)
        self.assertTrue(master)
        self.assertNotIn(master.encode(),raw)
        # DB only carries ciphertext. No raw token even when opened with sqlite.
        with sqlite3.connect(db) as c:
            rows=c.execute("SELECT name,ciphertext FROM integration_secrets").fetchall()
        self.assertEqual(len(rows),4)
        for _,blob in rows:
            self.assertTrue(blob.startswith(b"gAAAA"))
            self.assertNotIn(b"sk-test",blob)

    def test_reveal_is_explicit_no_secret_in_status_and_replace(self):
        first="gsk-original-not-real"
        second="gsk-replaced-not-real"
        settings.set_secret(settings.GROQ_SECRET,first)
        self.assertNotIn(first,str(settings.status()))
        settings.set_secret(settings.GROQ_SECRET,second)
        self.assertEqual(settings.reveal_secret("groq"),second)
        raw=secret_vault._db_path(self.path).read_bytes()
        self.assertNotIn(first.encode(),raw)
        self.assertNotIn(second.encode(),raw)
        settings.delete_secret(settings.GROQ_SECRET)
        self.assertFalse(settings.status()["groq_key_configured"])
        with self.assertRaisesRegex(ValueError,"Chưa lưu"):
            settings.reveal_secret("groq")

    def test_legacy_windows_secret_migrates_to_database_and_is_deleted(self):
        legacy="gsk-legacy-test-NOT-REAL"
        self.keyring.set_password(settings.SERVICE,settings.GROQ_SECRET,legacy)
        self.assertEqual(settings.reveal_secret("groq"),legacy)
        self.assertIsNone(self.keyring.get_password(settings.SERVICE,settings.GROQ_SECRET))
        db=secret_vault._db_path(self.path)
        self.assertTrue(db.is_file())
        self.assertNotIn(legacy.encode(),db.read_bytes())
        self.assertEqual(settings.openai_env({})["GROQ_API_KEY"],legacy)

    def test_missing_master_key_never_reencrypts_with_new_key(self):
        settings.set_secret(settings.GROQ_SECRET,"gsk-example-test")
        self.keyring.delete_password(settings.SERVICE,secret_vault.MASTER_KEY_NAME)
        with self.assertRaisesRegex(RuntimeError,"Không tìm thấy khóa mã hóa"):
            settings.reveal_secret("groq")
        with self.assertRaisesRegex(RuntimeError,"đã có khóa"):
            settings.set_secret(settings.GROQ_SECRET,"another-example")
        self.assertIsNone(self.keyring.get_password(settings.SERVICE,secret_vault.MASTER_KEY_NAME))

    def test_unrecognized_or_unsaved_provider_cannot_be_read(self):
        for provider in ("../../etc/passwd","passwords","database","",None):
            with self.assertRaises(ValueError):
                settings.reveal_secret(provider)

    def test_telegram_token_encrypted_and_revealable(self):
        token="123456:FAKE_TELEGRAM_TOKEN"
        settings.save_telegram({"bot_token":token,"telegram_allowed_ids":"",
                                 "telegram_autostart":False})
        self.assertEqual(settings.reveal_secret("telegram"),token)
        self.assertEqual(settings.telegram_env()["TEA_TELEGRAM_TOKEN"],token)
        self.assertNotIn(token,self.path.read_text(encoding="utf-8"))
        self.assertNotIn(token,secret_vault._db_path(self.path).read_bytes().decode("latin1"))
        settings.remove_telegram_token()
        with self.assertRaises(ValueError):
            settings.reveal_secret("telegram")


if __name__=="__main__":
    unittest.main()
