"""Offline tests for isolated persistent Google Flow Chrome profiles.

No Chrome is launched and no Google login, cookies or Flow APIs are accessed.
"""
from pathlib import Path
from unittest import TestCase, mock
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import flow_accounts
import flow_profiles


class FlowProfileTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "test.sqlite3"
        self.root = Path(self.temp.name) / "chrome_profiles"
        flow_accounts.setup(self.db)
        flow_profiles.setup(self.db, self.root)

    def test_each_gmail_gets_persistent_unique_folder(self):
        flow_accounts.add_accounts(self.db, "one@gmail.com\ntwo@gmail.com")
        records = flow_profiles.ensure_many(
            self.db, "one@gmail.com\ntwo@gmail.com", self.root)
        self.assertEqual(len(records), 2)
        self.assertNotEqual(records[0]["profile_id"], records[1]["profile_id"])
        self.assertTrue(all(x["folder"].is_dir() for x in records))
        same = flow_profiles.ensure_profile(self.db, "one@gmail.com", self.root)
        self.assertEqual(records[0]["profile_id"], same["profile_id"])
        self.assertEqual(len(flow_profiles.list_profiles(self.db, self.root)), 2)

    def test_migration_provisions_existing_gmail_without_touching_balance(self):
        flow_accounts.add_accounts(self.db, "existing@gmail.com")
        flow_accounts.update_balance(self.db, "existing@gmail.com", 50)
        flow_profiles.setup(self.db, self.root)
        flow_profiles.setup(self.db, self.root)
        self.assertEqual(
            flow_accounts.list_accounts(self.db)[0]["balance"], 50)
        self.assertEqual(len(flow_profiles.list_profiles(self.db, self.root)), 1)

    def test_cannot_create_profile_for_unknown_or_malformed_gmail(self):
        for addr in ["not-an-email", "unknown@gmail.com", "../unsafe"]:
            with self.assertRaises(ValueError):
                flow_profiles.ensure_profile(self.db, addr, self.root)

    def test_job_bound_to_exact_assigned_account(self):
        flow_accounts.add_accounts(self.db, "a@gmail.com\nb@gmail.com")
        flow_profiles.ensure_many(self.db, "a@gmail.com\nb@gmail.com", self.root)
        with sqlite3.connect(self.db) as con:
            con.execute("""INSERT INTO flow_jobs
              (mission_id,scene,prompt,model,credit_cost,email,status,
               created_at,updated_at)
              VALUES (1,1,'test','veo3.1-lite',10,'b@gmail.com',
                      'assigned','now','now')""")
            con.execute("""INSERT INTO flow_jobs
              (mission_id,scene,prompt,model,credit_cost,status,
               created_at,updated_at)
              VALUES (1,2,'test','veo3.1-lite',10,'queued','now','now')""")
        info = flow_profiles.profile_for_job(self.db, 1, self.root)
        self.assertEqual(info["email"], "b@gmail.com")
        self.assertEqual(
            info["profile_id"],
            flow_profiles.ensure_profile(self.db, "b@gmail.com", self.root)["profile_id"])
        with self.assertRaises(ValueError):
            flow_profiles.profile_for_job(self.db, 2, self.root)

    def test_open_reserves_profile_and_prevents_second_window(self):
        flow_accounts.add_accounts(self.db, "a@gmail.com")
        flow_profiles.ensure_profile(self.db, "a@gmail.com", self.root)
        with mock.patch.object(flow_profiles.subprocess, "Popen") as spawned:
            result = flow_profiles.launch_for_email(self.db, "a@gmail.com", self.root)
            self.assertTrue(result["ok"])
            spawned.assert_called_once()
            cmd = spawned.call_args.args[0]
            self.assertIn("a@gmail.com", cmd)
            self.assertNotIn("password", " ".join(cmd).lower())
            with self.assertRaisesRegex(ValueError, "đang được sử dụng"):
                flow_profiles.launch_for_email(self.db, "a@gmail.com", self.root)

    def test_snapshot_does_not_expose_profile_folder_or_secrets(self):
        flow_accounts.add_accounts(self.db, "a@gmail.com")
        flow_profiles.ensure_profile(self.db, "a@gmail.com", self.root)
        record = flow_profiles.list_profiles(self.db, self.root)["a@gmail.com"]
        self.assertNotIn("folder", record)
        self.assertNotIn("cookie", record)
        self.assertNotIn("token", record)


if __name__ == "__main__":
    import unittest
    unittest.main()
