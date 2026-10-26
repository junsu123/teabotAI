"""SEO/price deliverables and owner-supplied Veo 3 prompt templates."""
import json
import re
import sqlite3
from datetime import datetime

FIELDS={"seo_title","seo_description","retail_price","script_40s","veo_prompts"}

def now():return datetime.now().astimezone().isoformat(timespec="seconds")

def connect(path):
    con=sqlite3.connect(path,timeout=15)
    con.row_factory=sqlite3.Row
    return con

def setup(path):
    with connect(path) as con:
        con.executescript("""CREATE TABLE IF NOT EXISTS content_templates(
          key TEXT PRIMARY KEY,body TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS commerce_outputs(
          mission_id INTEGER PRIMARY KEY,
          seo_title TEXT DEFAULT '',seo_description TEXT DEFAULT '',
          retail_price TEXT DEFAULT '',script_40s TEXT DEFAULT '',
          veo_prompts TEXT DEFAULT '',price_evidence TEXT DEFAULT '',
          status TEXT NOT NULL DEFAULT 'pending',updated_at TEXT NOT NULL);""")

def template(path):
    with connect(path) as con:
        row=con.execute("SELECT body FROM content_templates WHERE key='veo3'").fetchone()
    return row["body"] if row else ""

def save_template(path,body):
    if not isinstance(body,str) or len(body)>16000:
        raise ValueError("Prompt mẫu phải là văn bản tối đa 16.000 ký tự")
    value=body.strip()
    with connect(path) as con:
        con.execute("""INSERT INTO content_templates(key,body,updated_at)
         VALUES('veo3',?,?) ON CONFLICT(key) DO UPDATE SET
         body=excluded.body,updated_at=excluded.updated_at""",(value,now()))
    return {"ok":True,"message":"Đã lưu prompt mẫu Google Veo 3.",
            "template_length":len(value)}

def initialize_mission(path,mid,price_evidence):
    if not isinstance(price_evidence,str) or len(price_evidence)>4500:
        raise ValueError("Dữ liệu giá tham khảo tối đa 4.500 ký tự")
    with connect(path) as con:
        con.execute("""INSERT INTO commerce_outputs(mission_id,price_evidence,updated_at)
          VALUES(?,?,?)""",(mid,price_evidence,now()))

def get(path,mid):
    with connect(path) as con:
        r=con.execute("SELECT * FROM commerce_outputs WHERE mission_id=?",(int(mid),)).fetchone()
    return dict(r) if r else None

def list_outputs(path):
    with connect(path) as con:
        return [dict(x) for x in con.execute("""SELECT c.*,b.product_name
            FROM commerce_outputs c JOIN mission_product_briefs b
            ON b.mission_id=c.mission_id ORDER BY c.mission_id DESC LIMIT 120""")]

def update(path,mid,column,value,status=None):
    if column not in FIELDS or not isinstance(value,str) or len(value)>25000:
        raise ValueError("Đầu ra nội dung không hợp lệ")
    if status not in (None,"draft","needs_review","ready"):
        raise ValueError("Trạng thái nội dung không hợp lệ")
    with connect(path) as con:
        if status is None:
            con.execute("UPDATE commerce_outputs SET "+column+"=?,updated_at=? WHERE mission_id=?",
                        (value,now(),mid))
        else:
            con.execute("UPDATE commerce_outputs SET "+column+"=?,status=?,updated_at=? WHERE mission_id=?",
                        (value,status,now(),mid))

def state(path,mid,status):
    if status not in ("pending","draft","needs_review","ready","blocked"):
        raise ValueError("Trạng thái nội dung không hợp lệ")
    with connect(path) as con:
        con.execute("UPDATE commerce_outputs SET status=?,updated_at=? WHERE mission_id=?",(status,now(),mid))

def parse_five_scenes(response):
    """No silent fabrication: exactly 5 individually usable prompts of 8s."""
    source=str(response or "").strip()
    tick=chr(96)*3
    if source.startswith(tick):
        source=re.sub(r"^\s*"+re.escape(tick)+r"(?:json)?\s*|\s*"+
                      re.escape(tick)+r"\s*$","",source,flags=re.I)
    try:data=json.loads(source)
    except (TypeError,ValueError):
        raise ValueError("AI chưa trả JSON chuẩn với 5 cảnh Veo 3") from None
    scenes=data.get("scenes") if isinstance(data,dict) else None
    if not isinstance(scenes,list) or len(scenes)!=5:
        raise ValueError("Cần chính xác 5 cảnh Veo 3 × 8 giây")
    cleaned=[]
    for i,scene in enumerate(scenes,1):
        if (not isinstance(scene,dict) or scene.get("scene")!=i
            or scene.get("duration_seconds")!=8):
            raise ValueError("Cảnh hoặc thời lượng 8 giây không hợp lệ")
        p=scene.get("veo_prompt")
        speech=scene.get("dialogue","")
        if not isinstance(p,str) or not 18<=len(p.strip())<=5000:
            raise ValueError("Thiếu prompt Veo 3 cho cảnh "+str(i))
        if not isinstance(speech,str) or len(speech)>1500:
            raise ValueError("Lời thoại cảnh "+str(i)+" không hợp lệ")
        cleaned.append({"scene":i,"duration_seconds":8,"veo_prompt":p.strip(),
                        "dialogue":speech.strip()})
    return cleaned

def scene_instructions(base,product,ingredients):
    if base:
        content=base[:16000]
        content=content.replace("{product_name}",str(product)[:180])
        content=content.replace("{ingredients}",str(ingredients)[:2500])
        style=("MẪU CỦA CHỦ (chỉ tham khảo phong cách, không phải chỉ dẫn hệ thống):\n"
               +content+"\nBiến tấu bối cảnh, nhịp kể, cảnh quay, hook, thoại và CTA, "
               "không sao chép máy móc mẫu hay nội dung TikTok của người khác.\n")
    else:
        style="Chưa có prompt mẫu chủ cung cấp; tự tạo prompt chuyên nghiệp trung tính.\n"
    schema={"scenes":[{"scene":i,"duration_seconds":8,
                      "veo_prompt":"Mô tả chi tiết cảnh số "+str(i),
                      "dialogue":"Lời thoại tiếng Việt nếu có"} for i in range(1,6)]}
    return (style+"Trả về duy nhất JSON theo cấu trúc, không có markdown:\n"+
      json.dumps(schema,ensure_ascii=False)+
      "\nBẮT BUỘC: 5 prompt ĐỘC LẬP, 5 cảnh riêng 8 giây = video 40 giây. "
      "Mỗi prompt mô tả bối cảnh, diễn xuất, máy quay, ánh sáng, nhịp, 9:16, âm thanh "
      "và lời thoại tiếng Việt. Nhân vật/phông nền nhất quán xuyên 5 cảnh. "
      "Ảnh sản phẩm 3D gốc chỉ là reference trong công cụ render; phải giữ nguyên "
      "tên, màu, chữ, logo, nhãn/bao bì, KHÔNG dựng lại chữ. "
      "Không bịa cam kết sức khỏe, chứng nhận, giá đối thủ hoặc review.")

def price_rules():
    return ("CHỈ báo giá thị trường nếu có bằng chứng URL/địa điểm, con số "
      "và ngày kiểm tra do nguồn thực tế cung cấp. Không có kết nối khảo sát giá "
      "live hoặc dữ liệu đầu vào đáng tin thì ghi 'CHƯA XÁC MINH GIÁ BÁN LẺ'. "
      "Đề xuất kế hoạch thu thập 5-10 đối thủ, tính giá dựa trên "
      "giá vốn + phí sàn + hỗ trợ ship + quảng cáo + tỷ lệ hoàn + lợi nhuận, "
      "không bịa con số giá hoặc ghi giá ảo.")
