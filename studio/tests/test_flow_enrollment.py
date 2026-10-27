"""Offline tests for new Flow Chrome profile sign-in using Windows UIA only."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import flow_accounts
import flow_profiles
import flow_enrollment


class FlowEnrollmentTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = Path(tmp.name) / "test.sqlite3"
        self.profiles = Path(tmp.name) / "profiles"
        self.records = Path(tmp.name) / "enrollments"
        flow_accounts.setup(self.db)
        flow_profiles.setup(self.db, self.profiles)

    def new_enrollment(self):
        with mock.patch.object(flow_enrollment.subprocess, "Popen") as launched:
            item = flow_enrollment.start(self.db, self.profiles, self.records)
        eid = item["enrollment_id"]
        token = (self.profiles / eid / flow_profiles.LOCK_NAME).read_text()
        return eid, token, launched

    def test_start_creates_blank_profile_without_email_or_extension(self):
        eid, token, launched = self.new_enrollment()
        self.assertEqual(len(eid), 32)
        self.assertNotIn("extension_path", flow_enrollment.start.__annotations__)
        self.assertEqual(flow_accounts.list_accounts(self.db), [])
        self.assertEqual(flow_enrollment.get_status(eid, self.records)["status"], "opening")
        cmd = launched.call_args.args[0]
        self.assertEqual(cmd[1], str(Path(flow_enrollment.__file__).resolve()))
        self.assertNotIn("flow-extension", " ".join(cmd))
        self.assertFalse(any("@" in str(x) for x in cmd))
        self.assertTrue((self.profiles / eid).is_dir())

    def test_verified_registration_persists_profile_and_credit_source(self):
        eid, _, _ = self.new_enrollment()
        email = flow_enrollment.register_verified(self.db, eid, "NEW@GMAIL.COM", 996)
        self.assertEqual(email, "new@gmail.com")
        account = flow_accounts.list_accounts(self.db)[0]
        self.assertEqual(account["balance"], 996)
        self.assertEqual(account["balance_source"], "browser_uia")
        self.assertEqual(account["verified_by"], "browser_uia")
        self.assertEqual(flow_profiles.ensure_profile(
            self.db, email, self.profiles)["profile_id"], eid)

    def test_duplicate_does_not_replace_existing_profile(self):
        flow_accounts.add_accounts(self.db, "owner@gmail.com")
        original = flow_profiles.ensure_profile(self.db, "owner@gmail.com", self.profiles)
        flow_accounts.update_balance(self.db, "owner@gmail.com", 50)
        eid, _, _ = self.new_enrollment()
        with self.assertRaisesRegex(ValueError, "DUPLICATE_EMAIL"):
            flow_enrollment.register_verified(self.db, eid, "owner@gmail.com", 996)
        account = flow_accounts.list_accounts(self.db)[0]
        self.assertEqual(account["balance"], 50)
        self.assertEqual(flow_profiles.ensure_profile(
            self.db, "owner@gmail.com", self.profiles)["profile_id"], original["profile_id"])

    def test_worker_uses_private_cdp_and_falls_back_to_uia_without_extension(self):
        eid, token, _ = self.new_enrollment()
        browser_window = mock.Mock()
        with (mock.patch.object(flow_enrollment.flow_profiles, "chrome_binary",
                                return_value="C:/Chrome/chrome.exe"),
              mock.patch.object(flow_enrollment.subprocess, "Popen") as launch,
              mock.patch("flow_dom.wait_for_dom_account",return_value=None) as dom,
              mock.patch("flow_uia.wait_for_visible_account",
                         return_value=("owner@gmail.com", 996, browser_window)) as read,
              mock.patch("flow_uia.close_owned_window", return_value=True) as close):
            launch.return_value.pid = 1234
            launch.return_value.wait.return_value = 0
            flow_enrollment.worker(self.db, eid, token, self.profiles, self.records)
            cmd = launch.call_args.args[0]
            self.assertEqual(cmd[0], "C:/Chrome/chrome.exe")
            self.assertTrue(any(part.startswith("--user-data-dir=") for part in cmd))
            self.assertFalse(any("no-sandbox" in part or "load-extension" in part for part in cmd))
            self.assertIn("--remote-debugging-port=0",cmd)
            self.assertIn("--remote-debugging-address=127.0.0.1",cmd)
            dom.assert_called_once()
            self.assertEqual(cmd[-1], flow_profiles.FLOW_URL)
            read.assert_called_once()
            close.assert_called_once_with(browser_window, 1234)
        result = flow_enrollment.get_status(eid, self.records)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["email"], "owner@gmail.com")
        self.assertEqual(result["credits"], 996)
        self.assertTrue((self.profiles / eid).is_dir())
        self.assertFalse((self.profiles / eid / flow_profiles.LOCK_NAME).exists())

    def test_worker_uses_dom_verified_email_and_closes_owned_window(self):
        eid,token,_=self.new_enrollment()
        window=mock.Mock()
        with (mock.patch.object(flow_enrollment.flow_profiles,"chrome_binary",
                                return_value="C:/Chrome/chrome.exe"),
              mock.patch.object(flow_enrollment.subprocess,"Popen") as launch,
              mock.patch("flow_dom.wait_for_dom_account",
                         return_value=("owner@gmail.com",50,window,"browser_dom")) as dom,
              mock.patch("flow_uia.close_owned_window",return_value=True) as closed,
              mock.patch("flow_uia.wait_for_visible_account") as legacy):
            launch.return_value.pid=2345
            launch.return_value.wait.return_value=0
            flow_enrollment.worker(self.db,eid,token,self.profiles,self.records)
            dom.assert_called_once()
            legacy.assert_not_called()
            closed.assert_called_once_with(window,2345)
        rows=flow_accounts.list_accounts(self.db)
        self.assertEqual(rows[0]["email"],"owner@gmail.com")
        self.assertEqual(rows[0]["balance"],50)
        self.assertEqual(rows[0]["balance_source"],"browser_dom")
        self.assertEqual(flow_enrollment.get_status(eid,self.records)["status"],"completed")

    def test_when_no_accessibility_data_profile_is_not_destroyed(self):
        eid, token, _ = self.new_enrollment()
        with (mock.patch.object(flow_enrollment.flow_profiles, "chrome_binary",
                                return_value="C:/Chrome/chrome.exe"),
              mock.patch.object(flow_enrollment.subprocess, "Popen") as launch,
              mock.patch("flow_dom.wait_for_dom_account",return_value=None),
              mock.patch("flow_uia.wait_for_visible_account", return_value=None)):
            launch.return_value.pid = 1345
            launch.return_value.wait.return_value = 0
            launch.return_value.poll.return_value = 0
            flow_enrollment.worker(self.db, eid, token, self.profiles, self.records)
        self.assertEqual(flow_enrollment.get_status(eid, self.records)["status"],
                         "needs_manual")
        self.assertTrue((self.profiles / eid).is_dir())
        self.assertFalse((self.profiles / eid / flow_profiles.LOCK_NAME).exists())
        final = flow_enrollment.complete_manually(
            self.db, eid, "owner@gmail.com", 50, self.profiles, self.records)
        self.assertEqual(final["status"], "completed")
        self.assertEqual(flow_accounts.list_accounts(self.db)[0]["balance_source"], "manual")

    def test_never_rebind_registered_email_or_deny_live_browser_lock(self):
        eid, _, _ = self.new_enrollment()
        flow_enrollment.save_status(eid, "needs_manual", "Manual required",
                                    records_dir=self.records)
        with self.assertRaisesRegex(ValueError, "vẫn đang mở"):
            flow_enrollment.complete_manually(self.db, eid, "owner@gmail.com", 996,
                                             self.profiles, self.records)
        (self.profiles / eid / flow_profiles.LOCK_NAME).unlink()
        flow_enrollment.complete_manually(self.db, eid, "owner@gmail.com", 996,
                                         self.profiles, self.records)
        with self.assertRaises(ValueError):
            flow_enrollment.complete_manually(self.db, eid, "other@gmail.com", 50,
                                             self.profiles, self.records)

    def test_status_never_exposes_password_cookie_or_lock_token(self):
        eid, _, _ = self.new_enrollment()
        flow_enrollment.save_status(eid, "completed", "Saved",
                                    email="test@gmail.com", credits=996,
                                    records_dir=self.records)
        status = flow_enrollment.get_status(eid, self.records)
        self.assertEqual(status["credits"], 996)
        for secret in ("cookie", "token", "password", "profile_folder"):
            self.assertNotIn(secret, status)
        with self.assertRaises(ValueError):
            flow_enrollment.get_status("../outside", self.records)


if __name__ == "__main__":
    unittest.main()
