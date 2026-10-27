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
