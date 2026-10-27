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

    def test_parse_localized_visible_credit_text(self):
        for raw,expected in [
            ("1.016 tín dụng Google Flow",1016),
            ("1,016 Google Flow credits",1016),
            ("50 tín dụng Google Flow",50),
            ("0 credits",0),
            ("1 016 tín dụng Google Flow",1016)
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(flow_profiles.parse_credit_text(raw), expected)
        for raw in ("3.5 credits", "hello", "1.016 điểm không rõ nguồn", "-10 credits", "1000001 credits"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    flow_profiles.parse_credit_text(raw)

    def test_visible_dom_reader_never_requires_cookie_access(self):
        page = mock.Mock()
        page.locator.return_value.first.inner_text.return_value = "1.016 tín dụng Google Flow"
        self.assertEqual(flow_profiles.credit_from_dom(page), 1016)
        page.locator.assert_called()
        page.context.cookies.assert_not_called()
        page.evaluate.assert_not_called()

    def test_credit_check_uses_the_same_profile_and_enforces_lock(self):
        flow_accounts.add_accounts(self.db, "a@gmail.com")
        info=flow_profiles.ensure_profile(self.db, "a@gmail.com", self.root)
        with mock.patch.object(flow_profiles.subprocess, "Popen") as spawned:
            result=flow_profiles.request_credit_check(self.db, "a@gmail.com", self.root)
            self.assertTrue(result["ok"])
            cmd=spawned.call_args.args[0]
            self.assertIn("credits-worker",cmd)
            self.assertIn("a@gmail.com",cmd)
            self.assertTrue((info["folder"]/flow_profiles.LOCK_NAME).is_file())
            with self.assertRaisesRegex(ValueError, "đóng cửa sổ Chrome"):
                flow_profiles.request_credit_check(self.db, "a@gmail.com", self.root)

    def test_browser_credit_update_records_source_without_overwriting_profile(self):
        flow_accounts.add_accounts(self.db,"a@gmail.com")
        initial=flow_profiles.ensure_profile(self.db,"a@gmail.com",self.root)
        flow_accounts.update_browser_balance(self.db,"a@gmail.com",1016)
        a=flow_accounts.list_accounts(self.db)[0]
        self.assertEqual(a["balance"],1016)
        self.assertEqual(a["verified_by"],"browser_dom")
        self.assertTrue(a["fresh"])
        updated=flow_profiles.ensure_profile(self.db,"a@gmail.com",self.root)
        self.assertEqual(initial["profile_id"],updated["profile_id"])


    def test_delete_removes_profile_and_requeues_unfinished_video(self):
        flow_accounts.add_accounts(self.db, "a@gmail.com")
        info = flow_profiles.ensure_profile(self.db, "a@gmail.com", self.root)
        (info["folder"] / "chrome_local_data").write_text("local-only", encoding="utf-8")
        with sqlite3.connect(self.db) as c:
            for n,status in [(1,"assigned"),(2,"completed")]:
                c.execute("""INSERT INTO flow_jobs
                    (mission_id,scene,prompt,model,credit_cost,email,status,created_at,updated_at)
                    VALUES (1,?,'test','veo3.1-lite',10,'a@gmail.com',?,'now','now')""",
                    (n,status))
        result = flow_profiles.delete_flow_profile(self.db, "a@gmail.com", self.root)
        self.assertTrue(result["ok"])
        self.assertFalse(info["folder"].exists())
        self.assertEqual(flow_accounts.list_accounts(self.db), [])
        self.assertEqual(flow_profiles.list_profiles(self.db,self.root), {})
        rows = flow_accounts.list_jobs(self.db)
        self.assertEqual(next(x for x in rows if x["scene"]==1)["status"], "queued")
        self.assertIsNone(next(x for x in rows if x["scene"]==1)["email"])
        # Completed history is preserved for audit.
        self.assertEqual(next(x for x in rows if x["scene"]==2)["email"], "a@gmail.com")

    def test_delete_rejects_profile_running_or_unknown_gmail(self):
        flow_accounts.add_accounts(self.db, "a@gmail.com")
        info = flow_profiles.ensure_profile(self.db, "a@gmail.com", self.root)
        lock = info["folder"] / flow_profiles.LOCK_NAME
        lock.write_text("running", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "đóng Chrome"):
            flow_profiles.delete_flow_profile(self.db, "a@gmail.com", self.root)
        self.assertTrue(info["folder"].exists())
        self.assertEqual(len(flow_accounts.list_accounts(self.db)), 1)
        lock.unlink()
        with self.assertRaisesRegex(ValueError, "không tồn tại"):
            flow_profiles.delete_flow_profile(self.db, "missing@gmail.com", self.root)

    def test_reload_sequentially_inspects_profiles_and_skips_open_window(self):
        flow_accounts.add_accounts(self.db, "one@gmail.com\ntwo@gmail.com")
        profiles = flow_profiles.ensure_many(self.db, ["one@gmail.com", "two@gmail.com"], self.root)
        opened = profiles[0]["folder"] / flow_profiles.LOCK_NAME
        opened.write_text("chrome running", encoding="utf-8")
        visited = []
        def fake_reader(db_path, email, token, root):
            visited.append(email)
            flow_accounts.update_browser_balance(db_path, email, 1016)
            flow_profiles._write_status(flow_profiles.ensure_profile(db_path,email,root)["folder"],
                                        "credits_updated", "Read 1016")
            (flow_profiles.ensure_profile(db_path,email,root)["folder"] / flow_profiles.LOCK_NAME).unlink()

        # Make the background thread deterministic for this offline unit test.
        with mock.patch.object(flow_profiles.threading, "Thread") as fake_thread, \
             mock.patch.object(flow_profiles, "credit_worker", side_effect=fake_reader):
            fake_thread.return_value.start.side_effect = lambda: flow_profiles._reload_all_worker(
                self.db, ["one@gmail.com","two@gmail.com"], self.root)
            flow_profiles.reload_all_credits(self.db, self.root)
        result = flow_profiles.reload_status()
        self.assertFalse(result["running"])
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(visited, ["two@gmail.com"])
        self.assertEqual(flow_accounts.list_accounts(self.db)[1]["balance"],1016)
        self.assertTrue(opened.is_file())

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
