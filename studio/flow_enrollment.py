"""Blank Chrome Flow profile enrollment with identity sourced from visible page.

Cookie/session data belongs solely to the persistent Chrome profile directory.
No cookie, token, credential, or network response is exported or inspected.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.parse import urlparse
from uuid import uuid4

import flow_accounts
import flow_profiles

ROOT = Path(__file__).resolve().parent
PROFILES = flow_profiles.PROFILES
RECORDS = ROOT / "data" / "flow_enrollments"
TERMINAL = {"completed", "duplicate", "cancelled", "failed", "needs_manual"}
MAX_SECONDS = 900


def status_path(enrollment_id, records_dir=None):
    if not isinstance(enrollment_id, str) or not flow_profiles.ID_RE.fullmatch(enrollment_id):
        raise ValueError("Mã phiên thêm tài khoản không hợp lệ")
    return (Path(records_dir) if records_dir is not None else RECORDS) / (enrollment_id + ".json")


def save_status(enrollment_id, status, message, *, email=None, credits=None, records_dir=None):
    dest = status_path(enrollment_id, records_dir)
    flow_profiles.private_dir(dest.parent)
    doc = {"id": enrollment_id, "status": status, "message": str(message)[:200],
           "email": email if status == "completed" else None,
           "credits": credits if status == "completed" else None,
           "updated_at": flow_profiles.now()}
    temp = dest.with_suffix(".tmp")
    temp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    if os.name != "nt":
        temp.chmod(0o600)
    temp.replace(dest)
    return doc


def get_status(enrollment_id, records_dir=None):
    dest = status_path(enrollment_id, records_dir)
    if not dest.is_file():
        raise ValueError("Không tìm thấy phiên thêm tài khoản")
    obj = json.loads(dest.read_text(encoding="utf-8"))
    return {k: obj.get(k) for k in ("id", "status", "message", "email", "credits", "updated_at")}


def start(db_path, profiles_dir=None, records_dir=None, port=8765):
    """Create and launch brand-new Chrome data directory before Gmail is known."""
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("Cổng ứng dụng không hợp lệ")
    root = Path(profiles_dir) if profiles_dir is not None else PROFILES
    records = Path(records_dir) if records_dir is not None else RECORDS
    flow_profiles.private_dir(root)
    flow_profiles.private_dir(records)
    enrollment_id = uuid4().hex
    folder = root / enrollment_id
    flow_profiles.private_dir(folder)
    token = uuid4().hex
    lock = folder / flow_profiles.LOCK_NAME
    lock.write_text(token, encoding="utf-8")
    if os.name != "nt":
        lock.chmod(0o600)
    save_status(enrollment_id, "opening", "Đang mở Chrome profile mới để đăng nhập Google.",
                records_dir=records)
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        subprocess.Popen([
            sys.executable, str(Path(__file__).resolve()), "worker",
            str(Path(db_path).resolve()), enrollment_id, token,
            str(root.resolve()), str(records.resolve()), str(port)],
            cwd=str(ROOT), creationflags=flags, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, close_fds=True)
    except Exception:
        save_status(enrollment_id, "failed", "Không khởi chạy được Chrome profile.",
                    records_dir=records)
        shutil.rmtree(folder, ignore_errors=True)
        raise
    return {"ok": True, "enrollment_id": enrollment_id,
            "extension_path": str((ROOT/"flow_extension").resolve()),
            "message": "Đã tạo Chrome profile. Cài tiện ích TEA Mars trong profile, tải lại tab ghép kết nối rồi đăng nhập Flow."}


def detect_visible_account(page):
    """Read displayed Gmail and credit text only from a labs.google Flow tab."""
    try:
        if page.is_closed() or urlparse(page.url).hostname not in ("labs.google", "flow.google.com"):
            return None
        email_node = page.locator("flow-account-panel .user-email, .user-email").first
        if not email_node.is_visible():
            for selector in (
                "button[aria-label*='account' i]",
                "button[aria-label*='profile' i]",
                "button[aria-label*='tài khoản' i]",
                "button:has(img[alt*='avatar' i])",
            ):
                try:
                    btn = page.locator(selector).first
                    if btn.is_visible():
                        btn.click(timeout=1000)
                        break
                except Exception:
                    continue
        if not email_node.is_visible():
            return None
        email = flow_accounts.normalize_email(email_node.inner_text(timeout=1300))
        credits = flow_profiles.credit_from_dom(page)
        return email, credits
    except Exception:
        return None


def inspect_context(context):
    for page in context.pages:
        item = detect_visible_account(page)
        if item:
            return item
    return None


def register_verified(db_path, enrollment_id, email, credits):
    """Atomically create Gmail/account/profile mapping only AFTER verified sign-in."""
    email = flow_accounts.normalize_email(email)
    if isinstance(credits, bool) or not isinstance(credits, int) or not 0 <= credits <= 1000000:
        raise ValueError("Điểm tín dụng Google Flow không hợp lệ")
    when = flow_accounts.utcnow()
    with flow_accounts.connect(db_path) as c:
        if c.execute("SELECT 1 FROM flow_accounts WHERE email=?", (email,)).fetchone():
            raise ValueError("DUPLICATE_EMAIL")
        c.execute("""INSERT INTO flow_accounts
            (email,balance,balance_checked_at,balance_source,created_at,updated_at)
            VALUES(?,?,?,'browser_dom',?,?)""", (email, credits, when, when, when))
        c.execute("""INSERT INTO flow_browser_profiles
            (email,profile_id,created_at,last_opened_at) VALUES(?,?,?,?)""",
            (email, enrollment_id, when, when))
    return email



def capture_from_extension(db_path, enrollment_id, token, email, credits,
                           profiles_dir=None, records_dir=None):
    """Verified localhost extension report, never accepts or reads any cookie.

    The pairing token lives only in the local Chrome-profile lock and is not
    accessible via public dashboard status. Only one enrollment may claim it.
    """
    root = Path(profiles_dir) if profiles_dir is not None else PROFILES
    records = Path(records_dir) if records_dir is not None else RECORDS
    if not isinstance(token, str) or not flow_profiles.ID_RE.fullmatch(token):
        raise ValueError("Khóa ghép profile không hợp lệ")
    folder = root / status_path(enrollment_id, records).stem
    lock = folder / flow_profiles.LOCK_NAME
    if not lock.is_file() or lock.read_text(encoding="utf-8") != token:
        raise ValueError("Phiên ghép Chrome không còn hoạt động")
    state = get_status(enrollment_id, records)
    if state["status"] in ("completed","duplicate"):
        raise ValueError("Phiên đã được xử lý")
    if state["status"] not in ("opening","signin_pending"):
        raise ValueError("Chưa thể lưu dữ liệu cho phiên này")
    try:
        email = register_verified(db_path, enrollment_id, email, credits)
    except ValueError as exc:
        if str(exc) != "DUPLICATE_EMAIL":
            raise
        save_status(enrollment_id, "duplicate",
                    "Gmail đã có trong bảng. Không ghi đè profile cũ.",
                    records_dir=records)
        return {"ok":True,"status":"duplicate"}
    save_status(enrollment_id,"completed",
                "Đã lấy Gmail và tín dụng trực tiếp từ trang Flow. Đang đóng Chrome.",
                email=email,credits=credits,records_dir=records)
    return {"ok":True,"status":"completed","email":email,"credits":credits}


def complete_manually(db_path, enrollment_id, email, credits, profiles_dir=None,
                      records_dir=None):
    """Fallback only: after Chrome has CLOSED, owner confirms visible details."""
    root = Path(profiles_dir) if profiles_dir is not None else PROFILES
    records = Path(records_dir) if records_dir is not None else RECORDS
    current = get_status(enrollment_id, records)
    if current["status"] != "needs_manual":
        raise ValueError("Chỉ xác nhận thủ công sau khi Chrome đã đóng và chưa đọc được thông tin")
    info = root / enrollment_id
    if not info.is_dir() or (info / flow_profiles.LOCK_NAME).exists():
        raise ValueError("Profile vẫn đang mở; hãy đóng Chrome trước")
    email = flow_accounts.normalize_email(email)
    if isinstance(credits, bool) or not isinstance(credits, int) or not 0 <= credits <= 1000000:
        raise ValueError("Điểm phải là số nguyên không âm")
    register_verified(db_path, enrollment_id, email, credits)
    return save_status(enrollment_id, "completed",
                       "Đã lưu Gmail do bạn xác nhận và Chrome profile đã đăng nhập.",
                       email=email, credits=credits, records_dir=records)


def worker(db_path, enrollment_id, token, profiles_dir=None, records_dir=None,
           port=8765, timeout_seconds=MAX_SECONDS, check_interval=2):
    """Launch actual installed Chrome. The human performs ALL Google sign-in.

    This browser is not started by Playwright, Chromium, a WebView or CDP.
    After the user closes Chrome, optionally inspect already-signed-in Flow.
    Chrome keeps its cookies only in the private local profile directory.
    """
    root = Path(profiles_dir) if profiles_dir is not None else PROFILES
    records = Path(records_dir) if records_dir is not None else RECORDS
    folder = root / enrollment_id
    lock = folder / flow_profiles.LOCK_NAME
    if (not flow_profiles.ID_RE.fullmatch(token) or not lock.is_file()
            or lock.read_text(encoding="utf-8") != token):
        raise RuntimeError("Khóa Chrome profile không hợp lệ")
    discard = False
    try:
        exe = flow_profiles.chrome_binary()
        pair_url = ("http://127.0.0.1:" + str(int(port)) +
                    "/flow-extension-pair?id=" + enrollment_id + "&token=" + token)
        save_status(enrollment_id, "signin_pending",
                    "Mở Chrome thường. Cài tiện ích TEA Mars (mỗi profile 1 lần), "
                    "tải lại tab ghép kết nối và đăng nhập Google Flow.",
                    records_dir=records)
        chrome = subprocess.Popen(
            [exe, "--user-data-dir=" + str(folder), "--new-window",
             "--no-first-run", pair_url, flow_profiles.FLOW_URL],
            cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # The browser extension closes the window only on successful read.
        # If not installed, user closes manually and confirms in dashboard.
        chrome.wait()
        state = get_status(enrollment_id, records)["status"]
        if state in ("completed", "duplicate"):
            discard = state == "duplicate"
        else:
            save_status(enrollment_id, "needs_manual",
                        "Không nhận được dữ liệu từ tiện ích. Profile vẫn được giữ. "
                        "Hãy xác nhận Gmail và điểm trong Mars Studio.",
                        records_dir=records)
    except FileNotFoundError:
        discard = True
        save_status(enrollment_id, "failed", "Không tìm thấy Google Chrome.",
                    records_dir=records)
    except Exception as exc:
        save_status(enrollment_id,"failed",
                    "Lỗi mở hoặc theo dõi Chrome: " + type(exc).__name__,
                    records_dir=records)
    finally:
        try:
            if lock.read_text(encoding="utf-8") == token:
                lock.unlink(missing_ok=True)
        except OSError:
            pass
        if discard:
            shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) != 8 or sys.argv[1] != "worker":
        raise SystemExit("Only the local Flow dashboard may start enrollment")
    worker(Path(sys.argv[2]), sys.argv[3], sys.argv[4],
           Path(sys.argv[5]), Path(sys.argv[6]), int(sys.argv[7]))
