"""Offline tests: multi-account Flow credits, scene allocation, and manual completion.

No Google credentials or browser automation are used.
"""
import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import flow_accounts as flow
import commerce_content as commerce


class FlowAccountsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Path(self.temp.name)/"flow.sqlite3"
        flow.setup(self.db)
        commerce.setup(self.db)
        self.scenes={"scenes":[{"scene":i,"duration_seconds":8,
           "veo_prompt":"Cảnh quảng bá trà túi lọc với hộp nguyên bản, giữ nhãn và chữ",
           "dialogue":"Trà thảo mộc tiện pha"} for i in range(1,6)]}
        with sqlite3.connect(self.db) as c:
            c.execute("""INSERT INTO commerce_outputs
               (mission_id,status,veo_prompts,updated_at)
               VALUES(123,'ready',?,?)""",(json.dumps(self.scenes),flow.utcnow()))

    def tearDown(self):
        self.temp.cleanup()

    def test_add_multiple_emails_without_creds_and_manual_balance(self):
        result=flow.add_accounts(self.db,"a@gmail.com\nb@gmail.com\na@gmail.com")
        self.assertTrue(result["ok"])
        self.assertEqual(len(flow.list_accounts(self.db)),2)
        self.assertTrue(all(a["balance"] is None for a in flow.list_accounts(self.db)))
        self.assertTrue(all(not a["eligible"] for a in flow.list_accounts(self.db)))
        flow.update_balance(self.db,"a@gmail.com",50,"Chrome Flow A")
        self.assertEqual(flow.list_accounts(self.db)[0]["available"],50)

    def test_assign_five_lite_clips_to_one_50_credit_account(self):
        flow.add_accounts(self.db,"one@gmail.com")
        flow.update_balance(self.db,"one@gmail.com",50)
        result=flow.enqueue_from_mission(self.db,123,"veo3.1-lite")
        self.assertTrue(result["ok"])
        jobs=flow.list_jobs(self.db)
        self.assertEqual(len(jobs),5)
        self.assertTrue(all(j["email"]=="one@gmail.com" and j["status"]=="assigned"
                            for j in jobs))
        acc=flow.list_accounts(self.db)[0]
        self.assertEqual(acc["reserved"],50)
        self.assertEqual(acc["available"],0)
        with self.assertRaisesRegex(ValueError,"đã có hàng đợi"):
            flow.enqueue_from_mission(self.db,123,"veo3.1-lite")

    def test_auto_allocate_next_account_when_first_credit_zero(self):
        flow.add_accounts(self.db,"a@gmail.com\nb@gmail.com")
        flow.update_balance(self.db,"a@gmail.com",50)
        flow.enqueue_from_mission(self.db,123,"veo3.1-fast")
        initial=flow.list_jobs(self.db)
        self.assertEqual(len([x for x in initial if x["status"]=="assigned"]),2)
        flow.update_balance(self.db,"b@gmail.com",50)
        allocation=flow.allocate(self.db)
        self.assertEqual(len(allocation["assigned"]),2)
        self.assertEqual(len([x for x in flow.list_jobs(self.db) if x["status"]=="assigned"]),4)
        # If the first account has a lower checked balance, old pending
        # assignments are released and safely placed on account B if space.
        flow.update_balance(self.db,"a@gmail.com",0)
        flow.allocate(self.db)
        jobs=flow.list_jobs(self.db)
        self.assertTrue(all(j["email"]!="a@gmail.com" for j in jobs if j["status"]=="assigned"))
        self.assertEqual(len([j for j in jobs if j["status"]=="assigned"]),2)
        self.assertEqual(len([j for j in jobs if j["status"]=="queued"]),3)

    def test_complete_is_explicit_and_never_claims_api_confirmation(self):
        flow.add_accounts(self.db,"a@gmail.com")
        flow.update_balance(self.db,"a@gmail.com",50)
        flow.enqueue_from_mission(self.db,123,"veo3.1-fast")
        target=next(j for j in flow.list_jobs(self.db) if j["status"]=="assigned")
        flow.job_action(self.db,target["id"],"complete")
        self.assertEqual(flow.list_accounts(self.db)[0]["balance"],30)
        self.assertEqual(next(j for j in flow.list_jobs(self.db) if j["id"]==target["id"])["status"],"completed")
        with self.assertRaisesRegex(ValueError,"đã xác nhận hoàn thành"):
            flow.job_action(self.db,target["id"],"retry")
        with self.assertRaisesRegex(ValueError,"chưa được phân"):
            flow.job_action(self.db,next(j["id"] for j in flow.list_jobs(self.db) if j["status"]=="queued"),"complete")

    def test_stale_or_unchecked_credits_never_used(self):
        flow.add_accounts(self.db,"a@gmail.com")
        flow.update_balance(self.db,"a@gmail.com",50)
        with sqlite3.connect(self.db) as c:
            old=(datetime.now(timezone.utc)-timedelta(hours=13)).isoformat()
            c.execute("UPDATE flow_accounts SET balance_checked_at=? WHERE email='a@gmail.com'",(old,))
        flow.enqueue_from_mission(self.db,123,"veo3.1-lite")
        self.assertEqual(len([j for j in flow.list_jobs(self.db) if j["status"]=="assigned"]),0)
        self.assertFalse(flow.list_accounts(self.db)[0]["fresh"])

    def test_quality_100_credits_not_allocated_to_50(self):
        flow.add_accounts(self.db,"a@gmail.com")
        flow.update_balance(self.db,"a@gmail.com",50)
        flow.enqueue_from_mission(self.db,123,"veo3.1-quality")
        self.assertTrue(all(j["status"]=="queued" for j in flow.list_jobs(self.db)))

    def test_invalid_email_and_negative_balance_rejected(self):
        for value in ("invalid","a@gmail.com@evil.net","bad<script>@gmail.com"):
            with self.assertRaises(ValueError):
                flow.add_accounts(self.db,value)
        flow.add_accounts(self.db,"valid@gmail.com")
        for value in (-1,1.5,False):
            with self.assertRaises(ValueError):
                flow.update_balance(self.db,"valid@gmail.com",value)
        with self.assertRaises(ValueError):
            flow.set_enabled(self.db,"valid@gmail.com","false")

if __name__=="__main__":
    unittest.main()
