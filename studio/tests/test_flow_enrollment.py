"""Offline tests for adding a blank Google Flow profile without entering email."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import flow_accounts
import flow_profiles
import flow_enrollment


class FlowEnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/"db.sqlite3"
        self.profiles=Path(self.tmp.name)/"profiles"
        self.records=Path(self.tmp.name)/"records"
        flow_accounts.setup(self.db)
        flow_profiles.setup(self.db,self.profiles)

    def test_start_requires_no_email_and_creates_isolated_profile(self):
        with mock.patch.object(flow_enrollment.subprocess,"Popen") as proc:
            r=flow_enrollment.start(self.db,self.profiles,self.records)
            proc.assert_called_once()
        self.assertTrue(r["ok"])
        eid=r["enrollment_id"]
        self.assertEqual(len(eid),32)
        self.assertTrue((self.profiles/eid).is_dir())
        self.assertTrue((self.profiles/eid/flow_profiles.LOCK_NAME).is_file())
        self.assertEqual(flow_accounts.list_accounts(self.db),[])
        self.assertEqual(flow_enrollment.get_status(eid,self.records)["status"],"opening")
        args=proc.call_args.args[0]
        self.assertIn(eid,args)
        self.assertFalse(any("gmail.com" in str(part) for part in args))

    def test_visible_flow_user_email_and_credits_are_detected(self):
        p=mock.Mock()
        p.url="https://labs.google/fx/tools/flow"
        p.is_closed.return_value=False
        p.locator.return_value.first.is_visible.return_value=True
        p.locator.return_value.first.inner_text.return_value="account@gmail.com"
        with mock.patch.object(flow_enrollment.flow_profiles,
                               "credit_from_dom",return_value=996) as credit:
            self.assertEqual(flow_enrollment.detect_visible_account(p),
                             ("account@gmail.com",996))
            credit.assert_called_once_with(p)
        p.context.cookies.assert_not_called()
        p.evaluate.assert_not_called()

    def test_ignore_non_google_page_and_invalid_email(self):
        p=mock.Mock()
        p.url="https://example.com"
        p.is_closed.return_value=False
        self.assertIsNone(flow_enrollment.detect_visible_account(p))
        p.locator.assert_not_called()
        p.url="https://labs.google/fx/tools/flow"
        p.locator.return_value.first.is_visible.return_value=True
        p.locator.return_value.first.inner_text.return_value="not an email"
        with mock.patch.object(flow_enrollment.flow_profiles,
                               "credit_from_dom",return_value=50) as credits:
            self.assertIsNone(flow_enrollment.detect_visible_account(p))
            credits.assert_not_called()

    def test_verified_email_becomes_persistent_profile_with_credit(self):
        eid="a"*32
        (self.profiles/eid).mkdir()
        email=flow_enrollment.register_verified(self.db,eid,"New@Gmail.com",996)
        self.assertEqual(email,"new@gmail.com")
        acc=flow_accounts.list_accounts(self.db)[0]
        self.assertEqual(acc["balance"],996)
        self.assertEqual(acc["balance_source"],"browser_dom")
        info=flow_profiles.ensure_profile(self.db,email,self.profiles)
        self.assertEqual(info["profile_id"],eid)
        self.assertEqual(info["folder"],self.profiles/eid)

    def test_existing_gmail_will_not_be_overwritten(self):
        flow_accounts.add_accounts(self.db,"existing@gmail.com")
        current=flow_profiles.ensure_profile(self.db,"existing@gmail.com",self.profiles)
        flow_accounts.update_balance(self.db,"existing@gmail.com",50)
        with self.assertRaisesRegex(ValueError,"DUPLICATE_EMAIL"):
            flow_enrollment.register_verified(self.db,"b"*32,"existing@gmail.com",996)
        self.assertEqual(flow_accounts.list_accounts(self.db)[0]["balance"],50)
        self.assertEqual(flow_profiles.ensure_profile(
            self.db,"existing@gmail.com",self.profiles)["profile_id"],current["profile_id"])

    def test_extension_report_stores_gmail_credit_and_prevents_replay(self):
        with mock.patch.object(flow_enrollment.subprocess, "Popen"):
            item=flow_enrollment.start(self.db,self.profiles,self.records)
        eid=item["enrollment_id"]
        token=(self.profiles/eid/flow_profiles.LOCK_NAME).read_text(encoding="utf-8")
        with self.assertRaises(ValueError):
            flow_enrollment.capture_from_extension(
                self.db,eid,"f"*32,"owner@gmail.com",996,self.profiles,self.records)
        result=flow_enrollment.capture_from_extension(
            self.db,eid,token,"owner@gmail.com",996,self.profiles,self.records)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"],"completed")
        self.assertEqual(flow_enrollment.get_status(eid,self.records)["credits"],996)
        self.assertEqual(flow_accounts.list_accounts(self.db)[0]["balance"],996)
        self.assertEqual(flow_profiles.ensure_profile(
            self.db,"owner@gmail.com",self.profiles)["profile_id"],eid)
        with self.assertRaises(ValueError):
            flow_enrollment.capture_from_extension(
                self.db,eid,token,"other@gmail.com",100,self.profiles,self.records)

    def test_extension_duplicate_does_not_replace_existing_profile(self):
        flow_accounts.add_accounts(self.db,"owner@gmail.com")
        original=flow_profiles.ensure_profile(self.db,"owner@gmail.com",self.profiles)
        flow_accounts.update_balance(self.db,"owner@gmail.com",50)
        with mock.patch.object(flow_enrollment.subprocess,"Popen"):
            item=flow_enrollment.start(self.db,self.profiles,self.records)
        eid=item["enrollment_id"]
        token=(self.profiles/eid/flow_profiles.LOCK_NAME).read_text(encoding="utf-8")
        result=flow_enrollment.capture_from_extension(
            self.db,eid,token,"owner@gmail.com",996,self.profiles,self.records)
        self.assertEqual(result["status"],"duplicate")
        self.assertEqual(flow_accounts.list_accounts(self.db)[0]["balance"],50)
        self.assertEqual(flow_profiles.ensure_profile(
            self.db,"owner@gmail.com",self.profiles)["profile_id"],original["profile_id"])

    def test_worker_launches_normal_chrome_with_pair_page_and_no_unsafe_flags(self):
        with mock.patch.object(flow_enrollment.subprocess,"Popen"):
            item=flow_enrollment.start(self.db,self.profiles,self.records)
        eid=item["enrollment_id"]
        token=(self.profiles/eid/flow_profiles.LOCK_NAME).read_text(encoding="utf-8")
        with (mock.patch.object(flow_enrollment.flow_profiles,"chrome_binary",
                                return_value="C:/Chrome/chrome.exe"),
              mock.patch.object(flow_enrollment.subprocess,"Popen") as launch):
            def simulate_extension(timeout=None):
                flow_enrollment.capture_from_extension(
                    self.db,eid,token,"owner@gmail.com",996,self.profiles,self.records)
                return 0
            launch.return_value.wait.side_effect=simulate_extension
            flow_enrollment.worker(self.db,eid,token,self.profiles,self.records)
            cmd=launch.call_args.args[0]
            self.assertEqual(cmd[0],"C:/Chrome/chrome.exe")
            self.assertTrue(any("--user-data-dir=" in x for x in cmd))
            self.assertTrue(any("/flow-extension-pair?" in x for x in cmd))
            self.assertFalse(any("no-sandbox" in x or "remote-debugging" in x for x in cmd))
        self.assertEqual(flow_enrollment.get_status(eid,self.records)["status"],"completed")
        self.assertTrue((self.profiles/eid).is_dir())
        self.assertFalse((self.profiles/eid/flow_profiles.LOCK_NAME).exists())

    def test_extension_closes_background_chrome_and_releases_profile_lock(self):
        with mock.patch.object(flow_enrollment.subprocess,"Popen"):
            eid=flow_enrollment.start(self.db,self.profiles,self.records)["enrollment_id"]
        token=(self.profiles/eid/flow_profiles.LOCK_NAME).read_text(encoding="utf-8")
        with (mock.patch.object(flow_enrollment.flow_profiles,"chrome_binary",
                                return_value="C:/Chrome/chrome.exe"),
              mock.patch.object(flow_enrollment.subprocess,"Popen") as launch):
            tries=[0]
            def simulated_wait(timeout):
                tries[0]+=1
                if tries[0]==1:
                    flow_enrollment.capture_from_extension(
                        self.db,eid,token,"owner@gmail.com",996,self.profiles,self.records)
                    raise flow_enrollment.subprocess.TimeoutExpired("chrome",timeout)
                if tries[0]==2:
                    raise flow_enrollment.subprocess.TimeoutExpired("chrome",timeout)
                return 0
            launch.return_value.wait.side_effect=simulated_wait
            flow_enrollment.worker(self.db,eid,token,self.profiles,self.records)
            launch.return_value.terminate.assert_called_once()
        self.assertFalse((self.profiles/eid/flow_profiles.LOCK_NAME).exists())
        self.assertEqual(flow_enrollment.get_status(eid,self.records)["status"],"completed")

    def test_worker_preserves_profile_on_browser_close_without_extension(self):
        with mock.patch.object(flow_enrollment.subprocess,"Popen"):
            eid=flow_enrollment.start(self.db,self.profiles,self.records)["enrollment_id"]
        token=(self.profiles/eid/flow_profiles.LOCK_NAME).read_text(encoding="utf-8")
        with (mock.patch.object(flow_enrollment.flow_profiles,"chrome_binary",
                                return_value="C:/Chrome/chrome.exe"),
              mock.patch.object(flow_enrollment.subprocess,"Popen") as launch):
            launch.return_value.wait.return_value=0
            flow_enrollment.worker(self.db,eid,token,self.profiles,self.records)
        self.assertEqual(flow_enrollment.get_status(eid,self.records)["status"],"needs_manual")
        self.assertTrue((self.profiles/eid).is_dir())
        self.assertFalse((self.profiles/eid/flow_profiles.LOCK_NAME).exists())
        saved=flow_enrollment.complete_manually(
            self.db,eid,"owner@gmail.com",50,self.profiles,self.records)
        self.assertEqual(saved["status"],"completed")

    def test_manually_confirmed_profile_cannot_be_reassigned(self):
        with mock.patch.object(flow_enrollment.subprocess, "Popen"):
            eid = flow_enrollment.start(self.db, self.profiles, self.records)["enrollment_id"]
        flow_enrollment.save_status(
            eid, "needs_manual", "Need confirmation", records_dir=self.records)
        with self.assertRaisesRegex(ValueError, "đóng Chrome"):
            flow_enrollment.complete_manually(
                self.db, eid, "owner@gmail.com", 50, self.profiles, self.records)
        (self.profiles/eid/flow_profiles.LOCK_NAME).unlink()
        saved = flow_enrollment.complete_manually(
            self.db, eid, "owner@gmail.com", 50, self.profiles, self.records)
        self.assertEqual(saved["status"], "completed")
        with self.assertRaises(ValueError):
            flow_enrollment.complete_manually(
                self.db, eid, "other@gmail.com", 50, self.profiles, self.records)

    def test_status_endpoint_never_exposes_chrome_cookie(self):
        eid="c"*32
        flow_enrollment.save_status(eid,"completed","Đã lưu",
                                    email="test@gmail.com",credits=996,records_dir=self.records)
        result=flow_enrollment.get_status(eid,self.records)
        self.assertEqual(result["email"],"test@gmail.com")
        self.assertEqual(result["credits"],996)
        self.assertNotIn("cookies",result)
        self.assertNotIn("token",result)
        with self.assertRaises(ValueError):
            flow_enrollment.get_status("../unsafe",self.records)


if __name__=="__main__":
    unittest.main()
