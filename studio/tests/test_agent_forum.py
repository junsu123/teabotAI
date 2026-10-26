"""Internal discussions are bounded, auditable, and CEO-decided."""
import os
import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

STUDIO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(STUDIO))
import agent_forum as forum

class ForumTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Path(self.temp.name)/"meeting.db"
        forum.setup(self.db)
    def tearDown(self):self.temp.cleanup()

    def test_record_order_and_no_unknown_actor(self):
        forum.record(self.db,12,"ceo","creative","assignment","Đề xuất tiêu đề")
        forum.record(self.db,12,"creative","ceo","proposal","Ý kiến A")
        forum.record(self.db,13,"ceo","strategy","assignment","Không liên quan")
        rows=forum.get_messages(self.db,12)
        self.assertEqual([(r["sender"],r["kind"]) for r in rows],
                         [("ceo","assignment"),("creative","proposal")])
        with self.assertRaises(ValueError):
            forum.record(self.db,12,"owner","research","question","Bypass CEO")
        with self.assertRaises(ValueError):
            forum.record(self.db,12,"creative","owner","decision","Bypass owner")

    def test_debate_has_question_reply_and_revision(self):
        calls=[]
        def chat(agent,prompt):
            calls.append((agent,prompt))
            return "Ý kiến "+agent
        result=forum.debate(self.db,12,chat,["strategy","compliance"],
                  {"strategy":"Giả thuyết", "compliance":"Cần kiểm duyệt"},
                  "Chiến dịch trà",rounds=1)
        self.assertEqual(len(result),3)
        self.assertEqual([x["sender"] for x in result],
                         ["strategy","compliance","strategy"])
        self.assertEqual([x["kind"] for x in forum.get_messages(self.db,12)],
                         ["question","objection","revision"])
        self.assertEqual(len(calls),3)
        self.assertTrue(all("CEO" in p for _,p in calls))

    def test_no_unbounded_infinite_discussion(self):
        with patch.dict(os.environ,{"TEA_DEBATE_ROUNDS":"99"}):
            self.assertEqual(forum.configured_rounds(),2)
        with patch.dict(os.environ,{"TEA_DEBATE_ROUNDS":"0"}):
            self.assertEqual(forum.configured_rounds(),0)
        with patch.dict(os.environ,{"TEA_DEBATE_ROUNDS":"invalid"}):
            self.assertEqual(forum.configured_rounds(),1)
        def impossible(agent,prompt):
            raise AssertionError("No agent should run")
        self.assertEqual(forum.debate(self.db,12,impossible,
             ["strategy"],{"strategy":"test"},"brief"),[])
        self.assertEqual(forum.debate(self.db,12,impossible,
             ["strategy","creative"],{"strategy":"a","creative":"b"},
             "brief",rounds=0),[])

if __name__=="__main__":
    unittest.main()
