"""Offline tests for CEO product-file uploads and TikTok-to-video handoff."""
import base64
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

STUDIO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(STUDIO))
import product_video_workflow as pv
import ceo_engine


class ProductVideoWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.db=self.root/"test.sqlite3"
        with sqlite3.connect(self.db) as con:
            con.execute("""CREATE TABLE missions (
              id INTEGER PRIMARY KEY,agent_id TEXT NOT NULL,title TEXT NOT NULL,
              detail TEXT DEFAULT '',status TEXT DEFAULT 'pending',
              created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""")
        ceo_engine.setup(self.db)
        self.metadata_patch=patch.object(pv,"public_tiktok_metadata",
            side_effect=lambda urls:[{"url":u,"status":"unavailable","title":"","author":""} for u in urls])
        self.metadata_patch.start()

    def tearDown(self):
        self.metadata_patch.stop()
        self.tmp.cleanup()

    def payload(self):
        image=b"\x89PNG\r\n\x1a\n"+b"TEST_IMAGE_FAKE_BYTES"
        return {
            "product_name":"Trà thảo mộc mẫu",
            "ingredients":"Đinh lăng, cỏ ngọt",
            "tiktok_urls":"https://www.tiktok.com/@example/video/76543210",
            "research_notes":"Video mở đầu bằng một câu hỏi và giới thiệu cách pha trà.",
            "price_evidence":"URL đối thủ https://example.com/tea 39.000đ ngày 2026-10-20",
            "image3d":{"name":"hop-tra.png","type":"image/png",
                        "base64":base64.b64encode(image).decode("ascii")},
        }

    def new_mission(self):
        return pv.create_mission(self.db,self.root,"Xây dựng video quảng bá trà",
                                 "Kịch bản bán hàng 5 cảnh",self.payload())

    def test_uploads_and_metadata_are_private_and_linked_to_ceo(self):
        mid=self.new_mission()
        brief=pv.get_brief(self.db,mid)
        self.assertEqual(brief["product_name"],"Trà thảo mộc mẫu")
        self.assertEqual(len(brief["assets"]),1)
        asset=pv.get_asset(self.db,mid,brief["assets"][0]["id"])
        self.assertEqual(asset["mime"],"image/png")
        self.assertTrue(Path(asset["stored_path"]).is_file())
        with sqlite3.connect(self.db) as con:
            self.assertEqual(con.execute("SELECT agent_id FROM missions WHERE id=?",(mid,)).fetchone()[0],"ceo")
        self.assertEqual(pv.production(self.db,mid)["status"],"research_pending")

    def test_reject_malicious_urls_and_wrong_mime_without_creating_mission(self):
        for bad in ("https://tiktok.com.evil.example/video/123",
                    "http://www.tiktok.com/@a/video/1",
                    "https://user:password@www.tiktok.com/@a/video/1"):
            brief=self.payload()
            brief["tiktok_urls"]=bad
            with self.assertRaises(ValueError):
                pv.create_mission(self.db,self.root,"video test","",brief)
        bad=self.payload()
        bad["image3d"]["base64"]=base64.b64encode(b"not a png").decode()
        with self.assertRaises(ValueError):
            pv.create_mission(self.db,self.root,"video test","",bad)
        with sqlite3.connect(self.db) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM missions").fetchone()[0],0)

    def test_approved_script_goes_to_video_studio_as_storyboard_only(self):
        mid=self.new_mission()
        calls=[]
        def chat(agent,prompt):
            calls.append((agent,prompt))
            if agent=="research":return "Hook theo ghi chú, chưa xem video TikTok thật."
            if agent=="analyst":return "CHƯA XÁC MINH GIÁ BÁN LẺ; cần báo giá nguồn."
            if agent=="strategy":
                return json.dumps({"titles":["Trà thảo mộc Đinh Lăng Cỏ Ngọt dạng túi lọc",
                    "Trà túi lọc Đinh Lăng với Cỏ Ngọt tiện pha"],
                    "description":"Trà thảo mộc theo thông tin chủ cung cấp. Thành phần đinh lăng, "
                                   "cỏ ngọt. Giữ thông tin bao bì gốc; vui lòng xem nhãn trước khi dùng."},
                    ensure_ascii=False)
            if agent=="compliance":
                return json.dumps({"status":"approved","reason":"Không có công dụng y tế","required_changes":[]})
            if agent=="ceo":return "CEO chốt 5 prompt Veo 3, chờ duyệt sản xuất."
            if "5 prompt Veo 3" in prompt:
                return json.dumps({"scenes":[{"scene":i,"duration_seconds":8,
                    "veo_prompt":"Cảnh "+str(i)+": khung hình 9:16, giữ nguyên bao bì sản phẩm, "
                    "ánh sáng dịu và diễn xuất tự nhiên.","dialogue":"Giới thiệu trà"} for i in range(1,6)]},
                    ensure_ascii=False)
            return "Kịch bản 40 giây gồm 5 cảnh giới thiệu tên, thành phần và cách pha."
        self.assertTrue(ceo_engine.work_once(self.db,chat,lambda:{"/unused":"unused"}))
        room=pv.production(self.db,mid)
        self.assertEqual(room["status"],"awaiting_video_render")
        self.assertEqual(len(json.loads(room["storyboard"])["scenes"]),5)
        import commerce_content as cc
        commerce=cc.get(self.db,mid)
        self.assertIn("CHƯA XÁC MINH",commerce["retail_price"])
        self.assertIn("Trà thảo mộc",commerce["seo_title"])
        self.assertIn("Thành phần",commerce["seo_description"])
        self.assertIn("40 giây",commerce["script_40s"])
        self.assertEqual(len(json.loads(commerce["veo_prompts"])["scenes"]),5)
        self.assertIn("Hook",room["research"])
        self.assertIn("Kịch bản",room["script"])
        self.assertEqual([a for a,_ in calls],
                         ["research","analyst","strategy","creative","compliance","creative","ceo"])
        self.assertIn("CHƯA",calls[0][1])
        with sqlite3.connect(self.db) as con:
            self.assertEqual(con.execute("SELECT status FROM missions WHERE id=?",(mid,)).fetchone()[0],"done")

    def test_price_without_evidence_is_not_invented(self):
        import commerce_content as cc
        details=self.payload()
        details["price_evidence"]=""
        mid=pv.create_mission(self.db,self.root,"Tạo nội dung trà có giá chưa xác minh","",details)
        called=[]
        def chat(agent,prompt):
            called.append(agent)
            if agent=="research":return "Ghi chú tham khảo"
            if agent=="strategy":return json.dumps({"titles":[
                "Trà thảo mộc đinh lăng cỏ ngọt túi lọc",
                "Trà túi lọc đinh lăng và cỏ ngọt tiện pha"],
                "description":"Sản phẩm trà thảo mộc theo thông tin được cung cấp với "
                "hai thành phần đinh lăng và cỏ ngọt. Xem nhãn sản phẩm để biết thêm."},
                ensure_ascii=False)
            if agent=="compliance":
                return json.dumps({"status":"needs_review","reason":"Cần rà soát hồ sơ"})
            return "Kịch bản quảng bá 40 giây"
        ceo_engine.work_once(self.db,chat,lambda:{})
        self.assertNotIn("analyst",called)
        report=cc.get(self.db,mid)["retail_price"]
        self.assertIn("CHƯA XÁC MINH GIÁ BÁN LẺ",report)
        self.assertNotIn("39.000đ",report)

    def test_unverified_claims_cannot_autohandoff(self):
        mid=self.new_mission()
        def chat(agent,prompt):
            if agent=="research":return "Ghi chú tham khảo"
            if agent=="analyst":return "CHƯA XÁC MINH GIÁ"
            if agent=="strategy":return json.dumps({"titles":[
                "Trà đinh lăng túi lọc sử dụng hàng ngày",
                "Trà túi lọc đinh lăng và cỏ ngọt tiện pha"],
                "description":"Trà thảo mộc theo nhãn do chủ cung cấp. Thành phần đinh lăng và cỏ ngọt. "
                              "Xem kỹ hướng dẫn và thông tin in trên bao bì sản phẩm trước khi sử dụng."},
                ensure_ascii=False)
            if agent=="compliance":
                return json.dumps({"status":"needs_review","reason":"Thiếu chứng cứ",
                                   "required_changes":["Xóa công dụng y tế"]})
            if agent=="ceo":self.fail("CEO should not approve production before compliance")
            return "Kịch bản quảng bá an toàn nhưng cần xem xét"
        self.assertTrue(ceo_engine.work_once(self.db,chat,lambda:{}))
        room=pv.production(self.db,mid)
        self.assertEqual(room["status"],"needs_review")
        self.assertFalse(room["storyboard"])

    def test_tiktok_oembed_public_metadata_is_limited(self):
        self.metadata_patch.stop()
        try:
            def fake(endpoint):
                self.assertTrue(endpoint.startswith("https://www.tiktok.com/oembed?"))
                return {"title":"Giới thiệu trà", "author_name":"Người sáng tạo"}
            result=pv.public_tiktok_metadata(
                ["https://www.tiktok.com/@example/video/76543210"],fetch_json=fake)
            self.assertEqual(result[0]["status"],"public_metadata_only")
            self.assertEqual(result[0]["title"],"Giới thiệu trà")
            self.assertEqual(result[0]["author"],"Người sáng tạo")
            self.assertNotIn("transcript",result[0])
        finally:
            self.metadata_patch.start()

    def test_missing_compliance_json_does_not_autohandoff(self):
        self.assertFalse(pv.compliance_ok("Nội dung đã kiểm duyệt xong"))
        self.assertFalse(pv.compliance_ok('{"status":"approved"}'))
        self.assertTrue(pv.compliance_ok('{"status":"approved","reason":"Nội dung mô tả thông thường"}'))


if __name__=="__main__":
    unittest.main()
