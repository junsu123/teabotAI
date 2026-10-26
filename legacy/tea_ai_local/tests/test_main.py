"""Offline unit tests: no actual LLM calls and no internet required."""
import io
import sqlite3
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


class LocalTeaAgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patches = [
            patch.object(main, 'BASE', self.root),
            patch.object(main, 'DATA', self.root / 'data'),
            patch.object(main, 'OUT', self.root / 'outputs'),
            patch.object(main, 'DB_FILE', self.root / 'data' / 'tea_agent.sqlite3'),
            patch.object(main, 'CONFIG_FILE', self.root / 'config.json')
        ]
        for p in self.patches:
            p.start()
        main.setup()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def test_memory_persists_and_retrieves(self):
        ident = main.add_memory('test', 'Tiêu đề trà đinh lăng', 'Ý tưởng tối ưu nội dung',
                                'https://example.com', 'unverified')
        self.assertIn(str(ident), main.recent_memories('trà đinh lăng'))
        main.approve(ident)
        self.assertIn('approved', main.recent_memories('đinh lăng'))

    def test_feed_parser(self):
        xml = '<rss><channel><item><title>Tea</title><link>https://example.com/p</link><description>Marketing</description></item></channel></rss>'
        items = main.feed_items(xml, 'https://example.com/rss')
        self.assertEqual(items[0][1], 'Tea')
        self.assertIn('Marketing', items[0][2])

    def test_local_urls_blocked(self):
        for url in ('http://example.com', 'https://127.0.0.1/foo', 'https://localhost/foo'):
            with self.assertRaises(ValueError):
                main.validate_url(url)

    def test_sales_import_duplicate_and_metrics(self):
        csv_path = self.root / 's.csv'
        csv_path.write_text('campaign,variant,impressions,clicks,orders,revenue,ad_spend,cogs,fees,refunds\n'
                            'Trial,A,1000,100,10,400000,50000,120000,30000,0\n', encoding='utf-8')
        main.import_sales(csv_path)
        summary = main.latest_sales_summary()
        self.assertIn('CTR=10.00%', summary)
        self.assertIn('net_contribution=200000', summary)
        with self.assertRaises(ValueError):
            main.import_sales(csv_path)

    def test_sales_evaluation_learns_once_per_import(self):
        sample = self.root / 'sample.csv'
        sample.write_text('campaign,variant,impressions,clicks,orders,revenue,ad_spend,cogs,fees,refunds\n'
                          'A,hook1,500,50,5,200000,20000,90000,15000,0\n', encoding='utf-8')
        main.import_sales(sample)
        with patch.object(main, 'chat', return_value='Kết quả chỉ mang tính quan sát') as mocked:
            mid = main.evaluate_sales()
            self.assertIsInstance(mid, int)
            self.assertIsNone(main.evaluate_sales())
            mocked.assert_called_once()
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT status FROM memories WHERE id=?', (mid,)).fetchone()[0], 'unverified')

    def test_human_feedback_is_persisted(self):
        with main.db() as conn:
            conn.execute("INSERT INTO runs(goal,created_at,output_file,status) VALUES(?,?,?,?)",
                         ('Tăng doanh số trà', main.now(), '/tmp/report.md', 'awaiting_human_approval'))
            run_id = conn.execute('SELECT MAX(id) FROM runs').fetchone()[0]
        mem_id = main.feedback(run_id, 4, 'Luôn cần dẫn nguồn khi bàn về công dụng')
        with main.db() as conn:
            row = conn.execute('SELECT status,body FROM memories WHERE id=?', (mem_id,)).fetchone()
        self.assertEqual(row[0], 'approved')
        self.assertIn('Luôn cần dẫn nguồn', row[1])

    def test_all_six_agents_and_file_creation(self):
        names = []
        def fake_chat(agent, prompt, structured=False):
            names.append(agent)
            return f'Bản nháp từ {agent}'
        with patch.object(main, 'chat', side_effect=fake_chat):
            output = main.run_goal('Tạo nội dung combo trà thảo mộc')
        self.assertTrue(output.exists())
        self.assertEqual(names, ['research', 'analyst', 'strategy', 'creative', 'compliance', 'ceo'])
        self.assertIn('CHỜ DUYỆT', output.read_text(encoding='utf-8'))
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT status FROM runs').fetchone()[0], 'awaiting_human_approval')


if __name__ == '__main__':
    unittest.main()
