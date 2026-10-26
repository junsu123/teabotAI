"""Tests for SEO outputs, owner Veo template, scene constraints and safe reruns."""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import commerce_content as cc
import product_video_workflow as pv
import ceo_engine


class CommerceOutputTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"studio.sqlite3"
        with sqlite3.connect(self.path) as c:
            c.execute("""CREATE TABLE missions(id INTEGER PRIMARY KEY,agent_id TEXT,
                 title TEXT,detail TEXT,status TEXT,created_at TEXT,updated_at TEXT)""")
        ceo_engine.setup(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def mission(self):
        return pv.create_mission(self.path,Path(self.tmp.name),
             "Viết nội dung sản phẩm trà","Tạo SEO, giá bán, 5 prompt video 40 giây",
             {"product_name":"Trà Ba Kích","ingredients":"Ba kích, đinh lăng",
              "price_evidence":"Nguồn A có URL, giá ghi 39.000đ ngày 01/01/2026"})

    def test_template_persisted_and_snapshot_per_product(self):
        example="Mở đầu một cảnh tại cửa hàng {product_name}. Thành phần {ingredients}."
        result=cc.save_template(self.path,example)
        self.assertTrue(result["ok"])
        first=self.mission()
        self.assertEqual(pv.get_brief(self.path,first)["veo_template"],example)
        cc.save_template(self.path,"Mẫu mới khác")
        self.assertEqual(pv.get_brief(self.path,first)["veo_template"],example)
        second=self.mission()
        self.assertEqual(pv.get_brief(self.path,second)["veo_template"],"Mẫu mới khác")
        instructions=cc.scene_instructions(example,"Trà Ba Kích","Ba kích, đinh lăng")
        self.assertIn("Trà Ba Kích",instructions)
        self.assertIn("Ba kích, đinh lăng",instructions)
        self.assertIn("5 prompt ĐỘC LẬP",instructions)

    def test_seo_and_prompt_validation(self):
        raw=json.dumps({"titles":["Trà thảo mộc ba kích túi lọc nguyên bản",
                 "Trà ba kích, đinh lăng túi lọc tiện pha"],
                 "description":"Trà thảo mộc túi lọc, thành phần ba kích và đinh lăng. "
                 "Đóng gói tiện dụng, tham khảo hướng dẫn in trên bao bì để sử dụng."},ensure_ascii=False)
        title,description=cc.parse_seo(raw)
        self.assertIn("1.",title)
        self.assertIn("thành phần",description.lower())
        with self.assertRaises(ValueError):
            cc.parse_seo("Trà này rất tốt")
        output=json.dumps({"scenes":[{"scene":i,"duration_seconds":8,
                       "veo_prompt":"Cảnh quay trà túi lọc chất lượng thương mại giữ nguyên bao bì",
                       "dialogue":"Giới thiệu trà"} for i in range(1,6)]},ensure_ascii=False)
        scenes=cc.parse_five_scenes(output)
        self.assertEqual(len(scenes),5)
        self.assertEqual(sum(x["duration_seconds"] for x in scenes),40)
        with self.assertRaises(ValueError):
            cc.parse_five_scenes(json.dumps({"scenes":[{"scene":1,
                  "duration_seconds":8,"veo_prompt":"Mô tả hợp lệ ở đây"}]}))
        with self.assertRaises(ValueError):
            cc.parse_five_scenes(json.dumps({"scenes":[{"scene":i,
                  "duration_seconds":6,"veo_prompt":"Mô tả dài đủ dùng cho mỗi cảnh"} for i in range(1,6)]}))

    def test_price_evidence_and_outputs_are_persisted(self):
        mid=self.mission()
        self.assertIn("39.000đ",cc.get(self.path,mid)["price_evidence"])
        cc.update(self.path,mid,"retail_price","Giá có nguồn, chưa xác minh")
        cc.update(self.path,mid,"seo_title","Trà túi lọc ba kích")
        cc.update(self.path,mid,"seo_description","Mô tả đã kiểm duyệt")
        cc.update(self.path,mid,"script_40s","5 cảnh mỗi cảnh 8 giây")
        self.assertEqual(len(cc.list_outputs(self.path)),1)
        self.assertEqual(cc.get(self.path,mid)["retail_price"],"Giá có nguồn, chưa xác minh")

    def test_retry_clears_stale_prompts_but_keeps_price_evidence(self):
        mid=self.mission()
        cc.update(self.path,mid,"veo_prompts",'{"scenes":"old"}',"ready")
        cc.update(self.path,mid,"seo_title","OLD SEO")
        pv.stage(self.path,mid,"storyboard","OLD STORYBOARD","awaiting_video_render")
        with sqlite3.connect(self.path) as c:
            c.execute("UPDATE missions SET status='blocked' WHERE id=?",(mid,))
        ceo_engine.retry(self.path,mid)
        self.assertEqual(cc.get(self.path,mid)["status"],"pending")
        self.assertEqual(cc.get(self.path,mid)["veo_prompts"],"")
        self.assertEqual(cc.get(self.path,mid)["seo_title"],"")
        self.assertIn("39.000đ",cc.get(self.path,mid)["price_evidence"])
        self.assertEqual(pv.production(self.path,mid)["storyboard"],"")

    def test_no_fake_market_quotes_without_sources(self):
        self.assertIn("Không có kết nối khảo sát giá",cc.price_rules())
        self.assertIn("KHÔNG",cc.scene_instructions("","Trà","Cỏ ngọt").upper())


if __name__=="__main__":unittest.main()
