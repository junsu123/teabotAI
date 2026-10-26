"""Offline regression tests for CEO task processing; no Ollama needed."""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import ceo_engine as ceo


class CEOWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Path(self.temp.name)/"ceo.sqlite3"
        with sqlite3.connect(self.db) as c:
            c.execute("""CREATE TABLE missions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL, title TEXT NOT NULL,
                detail TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
        ceo.setup(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def mission(self, status="pending"):
        with ceo.connect(self.db) as c:
            cur=c.execute("""INSERT INTO missions(agent_id,title,detail,status,created_at,updated_at)
                 VALUES ('ceo','Lên kế hoạch bán trà','Soạn đề xuất trong nội bộ',?,?,?)""",
                 (status,ceo.now(),ceo.now()))
            return cur.lastrowid

    def state(self,mid):
        with ceo.connect(self.db) as c:
            return c.execute("SELECT status FROM missions WHERE id=?",(mid,)).fetchone()["status"]

    def test_plan_parser_rejects_unknown_agents(self):
        agents,_=ceo.parse_plan('{"agents":["evil","creative","creative","compliance"],"reason":"ok"}')
        self.assertEqual(agents,["creative","compliance"])

    def test_job_runs_and_produces_ceo_report(self):
        mid=self.mission()
        calls=[]
        def chat(agent,prompt):
            calls.append(agent)
            if len(calls)==1:
                return '{"agents":["creative","compliance"],"reason":"Chuẩn bị bản nháp"}'
            if agent=="ceo":
                return "Báo cáo CEO: có bản nháp, cần chủ duyệt trước khi đăng."
            return f"Bản nháp nội bộ của {agent}; chưa đăng sản phẩm."
        self.assertTrue(ceo.work_once(self.db,chat,lambda:{"TRA-01":{"title":"Trà","price":40000,"stock":10}}))
        self.assertEqual(self.state(mid),"done")
        reports,steps=ceo.get_progress(self.db)
        self.assertIn("Báo cáo CEO",reports[mid]["report"])
        self.assertEqual(len(steps[mid]),4)  # 2 agents, progress + result
        self.assertEqual(calls,["ceo","creative","compliance","ceo"])
        self.assertFalse(ceo.work_once(self.db,chat,dict))

    def test_ollama_failure_blocks_then_retry(self):
        mid=self.mission()
        def broken(agent,prompt):
            raise RuntimeError("Cannot connect to Ollama 127.0.0.1:11434")
        ceo.work_once(self.db,broken,dict)
        self.assertEqual(self.state(mid),"blocked")
        reports,_=ceo.get_progress(self.db)
        self.assertIn("Ollama",reports[mid]["error"])
        ceo.retry(self.db,mid)
        self.assertEqual(self.state(mid),"pending")
        with self.assertRaises(ValueError):
            ceo.retry(self.db,mid)

    def test_restart_marks_interrupted_work_blocked(self):
        mid=self.mission("in_progress")
        ceo.setup(self.db)
        self.assertEqual(self.state(mid),"blocked")
        reports,_=ceo.get_progress(self.db)
        self.assertIn("gián đoạn",reports[mid]["error"])


if __name__=="__main__":
    unittest.main()
