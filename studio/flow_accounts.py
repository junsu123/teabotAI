"""Google Flow accounts and credit-aware human-reviewed prompt handoff.

No browser session scraping, saved passwords, Flow private endpoints, anti-bot
evasion, or claims of official credit API integration. Google Flow balance is
owner-entered; a job is only marked completed after manual confirmation.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone

EMAIL_RE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._%+\-]{0,62}@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}$")
MODELS={"veo3.1-lite":10,"veo3.1-fast":20,"veo3.1-quality":100}
VERIFY_HOURS=12


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path):
    c=sqlite3.connect(db_path,timeout=15,isolation_level="IMMEDIATE")
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA busy_timeout=15000")
    return c


def setup(db_path):
    with connect(db_path) as c:
        c.executescript("""CREATE TABLE IF NOT EXISTS flow_accounts (
          email TEXT PRIMARY KEY NOT NULL,
          profile_label TEXT NOT NULL DEFAULT '',
          balance INTEGER,
          balance_checked_at TEXT,
          balance_source TEXT NOT NULL DEFAULT 'not_checked',
          enabled INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL,updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS flow_jobs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          mission_id INTEGER NOT NULL,
          scene INTEGER NOT NULL,
          prompt TEXT NOT NULL,
          model TEXT NOT NULL,
          credit_cost INTEGER NOT NULL,
          email TEXT,
          status TEXT NOT NULL DEFAULT 'queued',
          completed_url TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(mission_id,scene),
          CHECK(scene BETWEEN 1 AND 5)
        );
        CREATE INDEX IF NOT EXISTS flow_jobs_account_status ON flow_jobs(email,status);
        """)


def normalize_email(email):
    if not isinstance(email,str):
        raise ValueError("Gmail không hợp lệ")
    value=email.strip().lower()
    if len(value)>150 or not EMAIL_RE.fullmatch(value) or value.count("@")!=1:
        raise ValueError("Địa chỉ email không hợp lệ: "+value[:70])
    return value


def add_accounts(db_path,mails):
    if isinstance(mails,str):
        values=mails.replace(",","\n").replace(";","\n").splitlines()
    elif isinstance(mails,list):
        values=mails
    else:
        raise ValueError("Danh sách Gmail không hợp lệ")
    unique=[]
    for value in values:
        if not isinstance(value,str):raise ValueError("Danh sách chứa email không hợp lệ")
        if not value.strip():continue
        email=normalize_email(value)
        if email not in unique:unique.append(email)
    if not unique or len(unique)>100:
        raise ValueError("Hãy nhập từ 1 đến 100 email")
    with connect(db_path) as c:
        for email in unique:
            c.execute("""INSERT OR IGNORE INTO flow_accounts(email,created_at,updated_at)
                        VALUES(?,?,?)""",(email,utcnow(),utcnow()))
    return {"ok":True,"added_or_existing":len(unique),
            "message":"Đã thêm danh sách email. Chưa kiểm tra tín dụng Flow; hãy nhập số dư thực tế."}


def update_balance(db_path,email,balance,profile_label=None):
    email=normalize_email(email)
    if isinstance(balance,bool) or not isinstance(balance,int) or not 0<=balance<=1000000:
        raise ValueError("Tín dụng phải là số nguyên không âm")
    if profile_label is not None and (not isinstance(profile_label,str) or len(profile_label)>100):
        raise ValueError("Tên profile quá dài hoặc không hợp lệ")
    with connect(db_path) as c:
        if not c.execute("SELECT 1 FROM flow_accounts WHERE email=?",(email,)).fetchone():
            raise ValueError("Tài khoản chưa được thêm")
        if profile_label is not None:
            c.execute("""UPDATE flow_accounts SET balance=?,balance_checked_at=?,
                 balance_source='manual',profile_label=?,updated_at=? WHERE email=?""",
                 (balance,utcnow(),profile_label.strip(),utcnow(),email))
        else:
            c.execute("""UPDATE flow_accounts SET balance=?,balance_checked_at=?,
                 balance_source='manual',updated_at=? WHERE email=?""",
                 (balance,utcnow(),utcnow(),email))
        _reconcile_locked(c)
    return {"ok":True,"message":"Đã lưu số dư do bạn đọc từ giao diện Flow; không phải kết quả kiểm tra tự động."}


def update_browser_balance(db_path, email, balance):
    """Record read-only credit text from the user's own Flow profile.

    Browser DOM readings are best effort, *not* the official Google credits API.
    Existing pending reservations are reconciled exactly as for manual input.
    """
    email = normalize_email(email)
    if isinstance(balance, bool) or not isinstance(balance, int) or not 0 <= balance <= 1000000:
        raise ValueError("Tín dụng đọc từ Google Flow không hợp lệ")
    with connect(db_path) as c:
        if not c.execute("SELECT 1 FROM flow_accounts WHERE email=?", (email,)).fetchone():
            raise ValueError("Gmail Flow chưa có trong database")
        c.execute("""UPDATE flow_accounts SET balance=?,balance_checked_at=?,
                 balance_source='browser_dom',updated_at=? WHERE email=?""",
                 (balance,utcnow(),utcnow(),email))
        _reconcile_locked(c)
    return {"ok": True, "balance": balance, "source": "browser_dom",
            "message": "Đã cập nhật tín dụng từ chữ hiển thị trong Google Flow."}


def set_enabled(db_path,email,enabled):
    email=normalize_email(email)
    if not isinstance(enabled,bool):raise ValueError("Trạng thái không hợp lệ")
    with connect(db_path) as c:
        n=c.execute("UPDATE flow_accounts SET enabled=?,updated_at=? WHERE email=?",
                    (int(enabled),utcnow(),email)).rowcount
        if not n:raise ValueError("Không tìm thấy tài khoản")
        _reconcile_locked(c)
    return {"ok":True}


def _fresh(value):
    if not value:return False
    try:
        checked=datetime.fromisoformat(value)
        return checked.tzinfo is not None and checked>=datetime.now(timezone.utc)-timedelta(hours=VERIFY_HOURS) and checked<=datetime.now(timezone.utc)+timedelta(minutes=2)
    except ValueError:return False


def _account_rows(c):
    data=[]
    reserved={r["email"]:r["total"] for r in c.execute("""SELECT email,SUM(credit_cost) total
       FROM flow_jobs WHERE status='assigned' GROUP BY email""")}
    for r in c.execute("SELECT * FROM flow_accounts ORDER BY email"):
        row=dict(r)
        row["fresh"]=_fresh(row["balance_checked_at"])
        row["reserved"]=reserved.get(row["email"],0)
        row["available"]=max(0,row["balance"]-row["reserved"]) if row["balance"] is not None else None
        row["eligible"]=bool(row["enabled"]) and row["fresh"] and row["available"] is not None
        row["verified_by"]={"manual":"manual","browser_dom":"browser_dom"}.get(row["balance_source"],"unknown")
        data.append(row)
    return data


def list_accounts(db_path):
    with connect(db_path) as c:
        return _account_rows(c)


def _reconcile_locked(c):
    """Release jobs reserved against unavailable/disabled/stale accounts.

    Do not silently mark anything submitted or completed.
    """
    rows={r["email"]:r for r in _account_rows(c)}
    for account in rows.values():
        if not account["eligible"]:
            c.execute("""UPDATE flow_jobs SET status='queued',email=NULL,updated_at=?
                     WHERE status='assigned' AND email=?""",(utcnow(),account["email"]))
            continue
        # Keep oldest assignments first; release newest if manual reported balance shrank.
        jobs=c.execute("""SELECT id,credit_cost FROM flow_jobs WHERE email=?
             AND status='assigned' ORDER BY id""",(account["email"],)).fetchall()
        consumed=0
        for job in jobs:
            consumed+=job["credit_cost"]
            if consumed>account["balance"]:
                c.execute("""UPDATE flow_jobs SET status='queued',email=NULL,updated_at=?
                             WHERE id=?""",(utcnow(),job["id"]))


def allocate(db_path):
    """Assign queued prompts in order only to accounts with recent manual credits."""
    with connect(db_path) as c:
        _reconcile_locked(c)
        assigned=[]
        accounts=_account_rows(c)
        for job in c.execute("SELECT id,credit_cost FROM flow_jobs WHERE status='queued' ORDER BY id").fetchall():
            eligible=[a for a in accounts if a["eligible"] and a["available"]>=job["credit_cost"]]
            if not eligible:continue
            # Balanced deterministic allocation: use the first eligible
            # account with the most currently available credits.
            chosen=sorted(eligible,key=lambda x:(-x["available"],x["email"]))[0]
            c.execute("""UPDATE flow_jobs SET email=?,status='assigned',updated_at=?
                        WHERE id=? AND status='queued'""",(chosen["email"],utcnow(),job["id"]))
            chosen["reserved"]+=job["credit_cost"]
            chosen["available"]-=job["credit_cost"]
            assigned.append({"job_id":job["id"],"email":chosen["email"]})
    return {"ok":True,"assigned":assigned,
            "message":"Đã phân bổ dựa trên tín dụng do bạn xác nhận; chưa gửi video tới Google Flow."}


def enqueue_from_mission(db_path,mission_id,model):
    import commerce_content as commerce
    if isinstance(mission_id,bool) or not isinstance(mission_id,int) or mission_id<1:
        raise ValueError("Mã nhiệm vụ không hợp lệ")
    if model not in MODELS:raise ValueError("Chưa hỗ trợ chế độ Flow này")
    work=commerce.get(db_path,mission_id)
    if not work or work["status"]!="ready":
        raise ValueError("Chưa có 5 prompt đã hoàn thành/kiểm duyệt cho nhiệm vụ")
    scenes=commerce.parse_five_scenes(work["veo_prompts"])
    with connect(db_path) as c:
        prior=c.execute("SELECT COUNT(*) FROM flow_jobs WHERE mission_id=?",(mission_id,)).fetchone()[0]
        if prior:raise ValueError("Nhiệm vụ đã có hàng đợi Flow; không tạo trùng 5 cảnh")
        for row in scenes:
            c.execute("""INSERT INTO flow_jobs(mission_id,scene,prompt,model,credit_cost,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?)""",(mission_id,row["scene"],row["veo_prompt"],model,
                                             MODELS[model],utcnow(),utcnow()))
    allocate(db_path)
    return {"ok":True,"message":"Đã đưa đúng 5 prompt vào hàng đợi Flow để chuẩn bị chuyển thủ công."}


def list_jobs(db_path):
    with connect(db_path) as c:
        return [dict(r) for r in c.execute("SELECT * FROM flow_jobs ORDER BY id DESC LIMIT 150")]


def job_action(db_path,job_id,action,completed_url=""):
    if isinstance(job_id,bool) or not isinstance(job_id,int) or job_id<1:
        raise ValueError("Mã video không hợp lệ")
    if action not in ("complete","retry","cancel"):
        raise ValueError("Hành động hàng đợi không hợp lệ")
    if not isinstance(completed_url,str) or len(completed_url)>600:
        raise ValueError("Link video không hợp lệ")
    if completed_url and not completed_url.startswith("https://labs.google/fx/"):
        raise ValueError("Chỉ lưu đường dẫn Google Flow chính thức hoặc để trống")
    with connect(db_path) as c:
        j=c.execute("SELECT * FROM flow_jobs WHERE id=?",(job_id,)).fetchone()
        if not j:raise ValueError("Không tìm thấy prompt")
        if action=="complete":
            if j["status"]!="assigned":
                raise ValueError("Prompt chưa được phân vào tài khoản. Chưa thể xác nhận hoàn thành.")
            acc=c.execute("SELECT * FROM flow_accounts WHERE email=?",(j["email"],)).fetchone()
            if not acc or acc["balance"] is None or acc["balance"]<j["credit_cost"]:
                raise ValueError("Số dư tài khoản thiếu; cần xác minh Flow lại trước khi xác nhận.")
            c.execute("""UPDATE flow_accounts SET balance=balance-?,updated_at=? WHERE email=?""",
                     (j["credit_cost"],utcnow(),j["email"]))
            c.execute("""UPDATE flow_jobs SET status='completed',completed_url=?,updated_at=? WHERE id=?""",
                      (completed_url,utcnow(),job_id))
        elif action=="retry":
            if j["status"]=="completed":
                raise ValueError("Video đã xác nhận hoàn thành; tránh tạo hoặc trừ phí lần nữa")
            c.execute("""UPDATE flow_jobs SET status='queued',email=NULL,updated_at=? WHERE id=?""",
                     (utcnow(),job_id))
        else:
            if j["status"]=="completed":raise ValueError("Không được hủy video đã hoàn thành")
            c.execute("""UPDATE flow_jobs SET status='cancelled',email=NULL,updated_at=? WHERE id=?""",
                      (utcnow(),job_id))
    # Automatic account allocation when another owned account has verified capacity.
    return allocate(db_path)
