"""Regression checks: the owner must address AI CEO only.

Run from project root:
    python -m unittest discover -s studio/tests -v
"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

STUDIO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDIO))
import run


class CEORoutingTests(unittest.TestCase):
    def test_ceo_queue_records_only_ceo_recipient(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "test.sqlite3"
            with patch.object(run, "DB", db):
                with run.conn() as c:
                    c.execute("""CREATE TABLE missions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        agent_id TEXT NOT NULL, title TEXT NOT NULL,
                        detail TEXT DEFAULT '', status TEXT NOT NULL,
                        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
                mid = run.queue_ceo_mission("Nghiên cứu bán trà", "Báo cáo CEO")
                with run.conn() as c:
                    row = c.execute(
                        "SELECT agent_id, title, detail, status FROM missions WHERE id=?",
                        (mid,),
                    ).fetchone()
                self.assertEqual(row["agent_id"], "ceo")
                self.assertEqual(row["status"], "pending")
                self.assertEqual(row["title"], "Nghiên cứu bán trà")

    def test_invalid_mission_rejected(self):
        with self.assertRaises(ValueError):
            run.queue_ceo_mission("")

    def test_owner_ui_does_not_offer_employee_assignment(self):
        ui = (STUDIO / "static" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn('<select name="agent_id">', ui)
        self.assertIn('name="agent_id" value="ceo"', ui)
        self.assertIn("Gửi yêu cầu đến CEO", ui)


if __name__ == "__main__":
    unittest.main()
