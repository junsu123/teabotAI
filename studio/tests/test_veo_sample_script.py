"""The owner can preview five Veo 3 scenes through CEO without saving missions.

All model responses in this suite are mocked; no API tokens or credentials.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import commerce_content as cc


def fake_scenes():
    return {"scenes":[{
        "scene":i,"duration_seconds":8,
        "action":"Cảnh quay giới thiệu bao bì sản phẩm, góc máy ngang và ánh sáng mềm.",
        "dialogue":"Trà thảo mộc túi lọc tiện pha mỗi ngày.",
        "veo_prompt":"Vertical 9:16 commercial video in a tea factory, scene "+
                     str(i)+", preserve exact packaging and label, no rebranding."
    } for i in range(1,6)]}


class SampleScriptTests(unittest.TestCase):
    def test_ceo_receives_sample_script_prompt_and_returns_five_8s_scenes(self):
        observed=[]
        template="Quay tại xưởng trà, công nhân giới thiệu {product_name} với {ingredients}."
        def chat(agent,prompt):
            observed.append((agent,prompt))
            return json.dumps(fake_scenes(),ensure_ascii=False)
        result=cc.create_sample_script("Trà đinh lăng","Đinh lăng, cỏ ngọt",template,chat)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["scenes"]),5)
        self.assertEqual(sum(item["duration_seconds"] for item in result["scenes"]),40)
        self.assertEqual(observed[0][0],"ceo")
        self.assertIn("Quay tại xưởng trà",observed[0][1])
        self.assertIn("Trà đinh lăng",observed[0][1])
        self.assertIn("Đinh lăng, cỏ ngọt",observed[0][1])
        self.assertIn("VEO3_5_SCENES_STRUCTURED",observed[0][1])
        self.assertIn("action",observed[0][1])
        self.assertNotIn("đã tạo MP4",result["message"].split("Đây là")[0])

    def test_no_sample_when_product_or_ingredients_missing(self):
        calls=[]
        def fail(agent,prompt):
            calls.append((agent,prompt))
            raise AssertionError("Should not call AI for invalid product brief")
        for product,ingredients in [("","Cỏ ngọt"),("Trà",""),("T","Cỏ ngọt")]:
            with self.assertRaisesRegex(ValueError,"Nhập"):
                cc.create_sample_script(product,ingredients,"Mẫu",fail)
        self.assertFalse(calls)

    def test_no_fabricated_scene_when_ai_returns_invalid_data(self):
        def faulty(agent,prompt):
            return json.dumps({"scenes":fake_scenes()["scenes"][:4]})
        with self.assertRaisesRegex(ValueError,"5 cảnh"):
            cc.create_sample_script("Trà ba kích","Ba kích","Mẫu",faulty)

    def test_no_sample_without_visual_action(self):
        bad=fake_scenes()
        for scene in bad["scenes"]:
            scene.pop("action")
        with self.assertRaisesRegex(ValueError,"hành động"):
            cc.create_sample_script("Trà ba kích","Ba kích","Mẫu",lambda a,p:json.dumps(bad))

    def test_draft_prompt_does_not_change_saved_master_template(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"db.sqlite3"
            cc.setup(path)
            cc.save_template(path,"Mẫu chính thức được lưu")
            result=cc.create_sample_script("Trà đinh lăng","Cỏ ngọt",
              "Mẫu hiện đang gõ, chưa bấm lưu",lambda agent,prompt:json.dumps(fake_scenes()))
            self.assertTrue(result["ok"])
            self.assertEqual(cc.template(path),"Mẫu chính thức được lưu")


if __name__=="__main__":
    unittest.main()
