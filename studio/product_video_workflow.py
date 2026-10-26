"""Local CEO video briefs, TikTok reference notes, and protected files."""
import base64
import binascii
import hashlib
import io
import json
import os
import re
import sqlite3
import uuid
import commerce_content
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

IMAGE_TYPES={"image/png":".png","image/jpeg":".jpg","image/webp":".webp"}
DOC_TYPES={"application/pdf":".pdf",**IMAGE_TYPES}
MAX_REF=8


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def db(path):
    c=sqlite3.connect(path,timeout=15)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA busy_timeout=15000")
    return c


def setup(path):
    with db(path) as c:
        c.executescript("""CREATE TABLE IF NOT EXISTS mission_product_briefs(
            mission_id INTEGER PRIMARY KEY, product_name TEXT NOT NULL,
            ingredients TEXT NOT NULL, tiktok_urls TEXT NOT NULL DEFAULT '[]',
            research_notes TEXT DEFAULT '', document_text TEXT DEFAULT '',
            document_status TEXT DEFAULT 'not_provided',created_at TEXT NOT NULL,
            veo_template TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS mission_assets(
            id INTEGER PRIMARY KEY, mission_id INTEGER NOT NULL, kind TEXT NOT NULL,
            filename TEXT NOT NULL, stored_path TEXT NOT NULL, mime TEXT NOT NULL,
            size_bytes INTEGER NOT NULL, sha256 TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS mission_assets_mission ON mission_assets(mission_id);
        CREATE TABLE IF NOT EXISTS video_production(
            mission_id INTEGER PRIMARY KEY, research TEXT DEFAULT '',
            script TEXT DEFAULT '', compliance TEXT DEFAULT '',
            storyboard TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'research_pending',
            updated_at TEXT NOT NULL);""")
        existing={r["name"] for r in c.execute("PRAGMA table_info(mission_product_briefs)")}
        if "veo_template" not in existing:
            c.execute("ALTER TABLE mission_product_briefs ADD COLUMN veo_template TEXT NOT NULL DEFAULT ''")
    commerce_content.setup(path)
    # Older product missions predate separate SEO/pricing deliverable rows.
    # They receive empty fields without changing their existing work.
    with db(path) as c:
        c.execute("""INSERT OR IGNORE INTO commerce_outputs(mission_id,updated_at)
                    SELECT mission_id,? FROM mission_product_briefs""",(now(),))


def field(value,title,limit,required=False):
    if not isinstance(value,str):
        raise ValueError(title+" phải là văn bản")
    v=value.strip()
    if len(v)>limit or (required and len(v)<2):
        raise ValueError("Hãy nhập "+title.lower()+" hợp lệ (tối đa "+str(limit)+" ký tự)")
    return v


def references(value):
    urls=value.splitlines() if isinstance(value,str) else value
    if not isinstance(urls,list) or len(urls)>MAX_REF:
        raise ValueError("Tối đa 8 link TikTok")
    out=[]
    for link in urls:
        if not isinstance(link,str) or len(link)>600:raise ValueError("Link không hợp lệ")
        link=link.strip()
        if not link:continue
        p=urlsplit(link)
        host=(p.hostname or "").lower().rstrip(".")
        if p.scheme!="https" or host not in (
            "tiktok.com","www.tiktok.com","m.tiktok.com","vm.tiktok.com","vt.tiktok.com"
        ) or p.username or p.password or p.port not in (None,443):
            raise ValueError("Chỉ nhận link TikTok HTTPS chính thức")
        out.append(link)
    return list(dict.fromkeys(out))


def decode(obj,kind):
    if not obj:return None
    if not isinstance(obj,dict):raise ValueError("Tệp đính kèm không hợp lệ")
    name=obj.get("name");mime=obj.get("type");encoded=obj.get("base64")
    allowed=IMAGE_TYPES if kind=="image3d" else DOC_TYPES
    if not isinstance(name,str) or not 1<=len(name)<=140 or any(
        ord(ch)<32 or ch in "/\\:" for ch in name
    ):raise ValueError("Tên tệp không hợp lệ")
    if mime not in allowed or not name.lower().endswith(allowed[mime]):
        raise ValueError("Ảnh: PNG/JPG/WebP; giấy công bố: PDF/PNG/JPG/WebP")
    limit=8*1024*1024 if kind=="image3d" else 12*1024*1024
    if not isinstance(encoded,str) or len(encoded)>4*((limit+2)//3)+4:
        raise ValueError("Dung lượng tệp vượt giới hạn")
    try:raw=base64.b64decode(encoded,validate=True)
    except (ValueError,binascii.Error):raise ValueError("Dữ liệu tệp không hợp lệ") from None
    if not raw or len(raw)>limit:raise ValueError("Tệp vượt giới hạn")
    good=(raw.startswith(b"\x89PNG\r\n\x1a\n") if mime=="image/png"
          else raw.startswith(b"\xff\xd8\xff") if mime=="image/jpeg"
          else raw.startswith(b"RIFF") and raw[8:12]==b"WEBP" if mime=="image/webp"
          else raw.startswith(b"%PDF-") if mime=="application/pdf" else False)
    if not good:raise ValueError("Nội dung tệp khác định dạng được khai báo")
    return {"name":name,"mime":mime,"suffix":allowed[mime],"data":raw}


def extract_document(upload):
    if not upload:return "", "not_provided"
    if upload["mime"]!="application/pdf":return "", "image_needs_manual_review"
    try:
        from pypdf import PdfReader
        reader=PdfReader(io.BytesIO(upload["data"]),strict=True)
        if reader.is_encrypted:return "", "password_protected"
        if len(reader.pages)>40:return "", "too_many_pages"
        text="\n".join((p.extract_text() or "")[:2200] for p in reader.pages[:15])[:9000].strip()
        return (text,"pdf_text_unverified") if text else ("","scan_needs_manual_review")
    except ImportError:return "", "pdf_parser_not_installed"
    except Exception:return "", "pdf_needs_manual_review"


def prepare(payload):
    if not isinstance(payload,dict):raise ValueError("Hồ sơ sản phẩm không hợp lệ")
    name=field(payload.get("product_name",""),"Tên sản phẩm",180,True)
    ingredients=field(payload.get("ingredients",""),"Thành phần",2500,True)
    notes=field(payload.get("research_notes",""),"Ghi chú video",4200)
    price_notes=field(payload.get("price_evidence",""),"Dữ liệu giá tham khảo",4500)
    urls=references(payload.get("tiktok_urls",[]))
    image=decode(payload.get("image3d"),"image3d")
    paper=decode(payload.get("disclosure_file"),"disclosure")
    if sum(len(x["data"]) for x in (image,paper) if x)>20*1024*1024:
        raise ValueError("Tổng tệp tối đa 20 MB")
    text,status=extract_document(paper)
    return {"name":name,"ingredients":ingredients,"notes":notes,
            "price_evidence":price_notes,"urls":urls,
            "image":image,"paper":paper,"document_text":text,"document_status":status}


def create_mission(db_path,data_dir,title,detail,payload):
    brief=prepare(payload)
    if not 3<=len(title)<=150 or len(detail)>2000:
        raise ValueError("Tiêu đề/yêu cầu nhiệm vụ không hợp lệ")
    base=payload.get("veo_prompt_template")
    if base is None:base=commerce_content.template(db_path)
    if not isinstance(base,str) or len(base)>16000:
        raise ValueError("Mẫu Google Veo 3 vượt giới hạn 16.000 ký tự")
    directory=Path(data_dir)/"product_missions"/uuid.uuid4().hex
    stored=[]
    try:
        for kind in ("image","paper"):
            f=brief[kind]
            if f:
                directory.mkdir(parents=True,exist_ok=True)
                try:os.chmod(directory,0o700)
                except OSError:pass
                path=directory/(uuid.uuid4().hex+f["suffix"])
                with path.open("xb") as fp:fp.write(f["data"])
                try:os.chmod(path,0o600)
                except OSError:pass
                stored.append((kind,f,path))
        with db(db_path) as c:
            cur=c.execute("""INSERT INTO missions(agent_id,title,detail,status,created_at,updated_at)
               VALUES('ceo',?,?,'pending',?,?)""",(title,detail,now(),now()))
            mid=cur.lastrowid
            c.execute("""INSERT INTO mission_product_briefs
               (mission_id,product_name,ingredients,tiktok_urls,research_notes,document_text,document_status,created_at,veo_template)
               VALUES(?,?,?,?,?,?,?,?,?)""",(mid,brief["name"],brief["ingredients"],
                json.dumps(brief["urls"],ensure_ascii=False),brief["notes"],
                brief["document_text"],brief["document_status"],now(),base.strip()))
            for kind,f,path in stored:
                c.execute("""INSERT INTO mission_assets
                  (mission_id,kind,filename,stored_path,mime,size_bytes,sha256)
                  VALUES(?,?,?,?,?,?,?)""",(mid,"image3d" if kind=="image" else "disclosure",
                  f["name"],str(path),f["mime"],len(f["data"]),
                  hashlib.sha256(f["data"]).hexdigest()))
            c.execute("INSERT INTO video_production(mission_id,status,updated_at) VALUES(?,'research_pending',?)",(mid,now()))
            c.execute("""INSERT INTO commerce_outputs(mission_id,price_evidence,status,updated_at)
                         VALUES(?,?,'pending',?)""",(mid,brief["price_evidence"],now()))
        return mid
    except Exception:
        for _,_,p in stored:
            try:p.unlink()
            except OSError:pass
        try:directory.rmdir()
        except OSError:pass
        raise


def get_brief(db_path,mid,include_doc=True):
    with db(db_path) as c:
        row=c.execute("SELECT * FROM mission_product_briefs WHERE mission_id=?",(int(mid),)).fetchone()
        if not row:return None
        info=dict(row)
        info["tiktok_urls"]=json.loads(info["tiktok_urls"])
        info["assets"]=[dict(r) for r in c.execute(
            "SELECT id,kind,filename,mime,size_bytes FROM mission_assets WHERE mission_id=? ORDER BY id",(mid,))]
        if not include_doc:
            info.pop("document_text",None)
            info.pop("veo_template",None)
        return info


def production(db_path,mid):
    with db(db_path) as c:
        r=c.execute("SELECT * FROM video_production WHERE mission_id=?",(int(mid),)).fetchone()
        return dict(r) if r else None


def list_production(db_path):
    with db(db_path) as c:
        return [dict(r) for r in c.execute("""SELECT v.*,b.product_name
           FROM video_production v JOIN mission_product_briefs b ON v.mission_id=b.mission_id
           ORDER BY v.mission_id DESC LIMIT 120""")]


def stage(db_path,mid,column,text,status):
    if column not in ("research","script","compliance","storyboard"):
        raise ValueError("Giai đoạn không hợp lệ")
    with db(db_path) as c:
        c.execute("UPDATE video_production SET "+column+"=?,status=?,updated_at=? WHERE mission_id=?",
                  (str(text)[:20000],status,now(),mid))


def state(db_path,mid,status):
    if status not in ("research_pending","research_complete","script_complete",
                      "needs_review","awaiting_video_render","blocked"):
        raise ValueError("Trạng thái không hợp lệ")
    with db(db_path) as c:
        c.execute("UPDATE video_production SET status=?,updated_at=? WHERE mission_id=?",(status,now(),mid))


def public_tiktok_metadata(urls,fetch_json=None):
    """Retrieve only public oEmbed metadata from the official TikTok host.

    This is NOT a download, transcription, view-counter query or permission
    to copy a creator's script. Failures are represented as unavailable.
    """
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen
    result=[]
    for url in urls[:MAX_REF]:
        row={"url":url,"status":"unavailable","title":"","author":""}
        try:
            endpoint="https://www.tiktok.com/oembed?"+urlencode({"url":url})
            if fetch_json is None:
                request=Request(endpoint,headers={"User-Agent":"TeaMarsStudio/1.0",
                                                  "Accept":"application/json"})
                with urlopen(request,timeout=4) as response:
                    metadata=json.loads(response.read(50000).decode("utf-8"))
            else:
                metadata=fetch_json(endpoint)
            if isinstance(metadata,dict):
                title=metadata.get("title","")
                author=metadata.get("author_name","")
                row.update(status="public_metadata_only",
                    title=title[:300] if isinstance(title,str) else "",
                    author=author[:120] if isinstance(author,str) else "")
        except Exception:
            # Unsupported/private/removed videos or network blocks must not
            # stop the rest of the CEO production pipeline.
            pass
        result.append(row)
    return result


def summary(brief):
    description={"pdf_text_unverified":"PDF trích được chữ (CHƯA xác minh)",
      "image_needs_manual_review":"Ảnh giấy công bố chưa đọc nội dung",
      "scan_needs_manual_review":"PDF scan chưa đọc chữ",
      "not_provided":"Chưa tải giấy công bố"}.get(brief["document_status"],"Chưa xác minh giấy tờ")
    return ("Tên: "+brief["product_name"]+"\nThành phần: "+brief["ingredients"]+
      "\nLink tham khảo (CHƯA xem được nội dung):\n"+"\n".join(brief["tiktok_urls"])+
      "\nGhi chú do chủ doanh nghiệp cung cấp (CHƯA kiểm chứng):\n"+brief["research_notes"]+
      "\nGiấy tờ: "+description+"\nVăn bản PDF trích được (CHƯA xác minh):\n"+
      brief["document_text"][:7500]+"\nẢnh sản phẩm 3D là tham chiếu nhãn gốc; AI văn bản chưa xem trực tiếp pixels.\n")


def compliance_ok(answer):
    cleaned=str(answer).strip()
    if cleaned.startswith(chr(96)*3):
        cleaned=re.sub(r"^\s*"+re.escape(chr(96)*3)+r"(?:json)?\s*|\s*"+re.escape(chr(96)*3)+r"\s*$","",cleaned,flags=re.I)
    try:obj=json.loads(cleaned)
    except (ValueError,TypeError):return False
    return isinstance(obj,dict) and obj.get("status")=="approved" and bool(obj.get("reason"))


def get_asset(db_path,mid,aid):
    with db(db_path) as c:
        x=c.execute("SELECT * FROM mission_assets WHERE mission_id=? AND id=?",(int(mid),int(aid))).fetchone()
        return dict(x) if x else None
