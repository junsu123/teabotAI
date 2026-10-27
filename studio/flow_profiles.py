"""Separate, persistent Google Flow Chrome profiles per registered Gmail.

Profile data (including Chrome's own session files) stays under studio/data/,
never travels through the dashboard/API, and must not be committed to Git.
Opening a profile is a user-initiated MANUAL browser action. No credit
scraping, cookie exports, auth bypass, Flow private APIs or video rendering.
Future permitted Flow integrations can resolve the assigned job's Gmail
to exactly this same profile via profile_for_job().
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
from urllib.parse import urlparse
import time
from datetime import datetime, timezone
from uuid import uuid4

import flow_accounts

ROOT = Path(__file__).resolve().parent
PROFILES = ROOT / "data" / "flow_chrome_profiles"
FLOW_URL = "https://labs.google/fx/tools/flow"
ID_RE = re.compile(r"^[a-f0-9]{32}$")
LOCK_NAME = ".flow_browser_in_use"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def private_dir(path):
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        path.chmod(0o700)


def connect(db_path):
    return flow_accounts.connect(db_path)


def setup(db_path, profiles_dir=None):
    """Non-destructive extra table; old Flow Gmail accounts remain intact."""
    root = Path(profiles_dir) if profiles_dir is not None else PROFILES
    private_dir(root)
    with connect(db_path) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS flow_browser_profiles (
            email TEXT PRIMARY KEY NOT NULL REFERENCES flow_accounts(email),
            profile_id TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            last_opened_at TEXT
        )""")
    # Migrate older saved Gmail rows without altering credits or job ownership.
    with connect(db_path) as c:
        emails = [r["email"] for r in c.execute("SELECT email FROM flow_accounts")]
    for email in emails:
        ensure_profile(db_path, email, root)


def ensure_profile(db_path, email, profiles_dir=None):
    """Idempotent binding of one registered Gmail to one private Chrome folder."""
    email = flow_accounts.normalize_email(email)
    root = Path(profiles_dir) if profiles_dir is not None else PROFILES
    private_dir(root)
    with connect(db_path) as c:
        if c.execute("SELECT 1 FROM flow_accounts WHERE email=?", (email,)).fetchone() is None:
            raise ValueError("Bạn cần thêm Gmail vào danh sách Flow trước")
        row = c.execute("SELECT profile_id FROM flow_browser_profiles WHERE email=?", (email,)).fetchone()
        if row:
            pid = row["profile_id"]
        else:
            pid = uuid4().hex
            c.execute("INSERT INTO flow_browser_profiles(email,profile_id,created_at) VALUES(?,?,?)",
                      (email, pid, now()))
    if not ID_RE.fullmatch(pid):
        raise ValueError("Mã Chrome profile Flow trong database không hợp lệ")
    folder = root / pid
    private_dir(folder)
    return {"email": email, "profile_id": pid, "folder": folder}


def ensure_many(db_path, raw_emails, profiles_dir=None):
    """Provision separate profiles for the just-added single/bulk Gmail list."""
    if isinstance(raw_emails, str):
        emails = raw_emails.replace(",", "\n").replace(";", "\n").splitlines()
    elif isinstance(raw_emails, list):
        emails = raw_emails
    else:
        raise ValueError("Danh sách Gmail không hợp lệ")
    items = []
    for email in emails:
        if not isinstance(email, str):
            raise ValueError("Gmail không hợp lệ")
        if email.strip():
            normal = flow_accounts.normalize_email(email)
            if normal not in items:
                items.append(normal)
    if not 1 <= len(items) <= 100:
        raise ValueError("Hãy nhập từ 1 đến 100 Gmail")
    return [ensure_profile(db_path, email, profiles_dir) for email in items]


def profile_for_job(db_path, job_id, profiles_dir=None):
    """Resolve an assigned video's exact Gmail/profile; no fallback account."""
    if isinstance(job_id, bool) or not isinstance(job_id, int) or job_id < 1:
        raise ValueError("Mã cảnh Flow không hợp lệ")
    with connect(db_path) as c:
        job = c.execute("SELECT id,email,status FROM flow_jobs WHERE id=?", (job_id,)).fetchone()
    if not job or job["status"] != "assigned" or not job["email"]:
        raise ValueError("Cảnh chưa được phân Gmail Flow đang hoạt động")
    result = ensure_profile(db_path, job["email"], profiles_dir)
    result["job_id"] = job_id
    return result


def _write_status(folder, status, message=""):
    # Minimal metadata only. Do NOT save cookies/tokens, pages, HTML or login data.
    value = {"status": status, "updated_at": now(), "message": str(message)[:180]}
    target = folder / "flow_status.json"
    temp = folder / "flow_status.tmp"
    temp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    if os.name != "nt":
        temp.chmod(0o600)
    temp.replace(target)


def list_profiles(db_path, profiles_dir=None):
    root = Path(profiles_dir) if profiles_dir is not None else PROFILES
    with connect(db_path) as c:
        profiles = [dict(r) for r in c.execute(
            "SELECT email,profile_id,created_at,last_opened_at FROM flow_browser_profiles")]
    out = {}
    for p in profiles:
        pid = p["profile_id"]
        if not ID_RE.fullmatch(pid):
            continue
        folder = root / pid
        status = "created"
        message = ""
        try:
            f = folder / "flow_status.json"
            if f.is_file():
                doc = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(doc, dict) and doc.get("status") in {
                    "created", "opening", "open", "closed", "error",
                    "checking_credits", "credits_updated", "credits_unavailable"
                }:
                    status = doc["status"]
                    message = str(doc.get("message") or "")[:180]
        except (OSError, ValueError):
            status = "error"
            message = "Không đọc được tình trạng Chrome profile"
        out[p["email"]] = {
            "profile_id": pid, "status": status, "message": message,
            "last_opened_at": p["last_opened_at"],
            "in_use": (folder / LOCK_NAME).exists()
        }
    return out


def _launch_for_profile(db_path, info, profiles_dir=None):
    """Reserve the profile before spawning to avoid duplicate Chrome writers."""
    root = Path(profiles_dir) if profiles_dir is not None else PROFILES
    folder = info["folder"]
    lock = folder / LOCK_NAME
    token = uuid4().hex
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError(
            "Profile đang được sử dụng. Hãy quay về Chrome đang mở và không khởi chạy trùng."
        ) from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(token)
        _write_status(folder, "opening", "Đang khởi động Chrome profile riêng")
        with connect(db_path) as c:
            c.execute("UPDATE flow_browser_profiles SET last_opened_at=? WHERE email=?",
                      (now(), info["email"]))
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "open-worker",
             str(Path(db_path).resolve()), info["email"], token, str(root.resolve())],
            cwd=str(ROOT),
            creationflags=flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        return {"ok": True, "email": info["email"], "profile_id": info["profile_id"],
                "message": "Đã yêu cầu mở Chrome profile riêng. Đăng nhập Google thủ công nếu cần."}
    except Exception:
        lock.unlink(missing_ok=True)
        _write_status(folder, "error", "Không khởi chạy được trình duyệt Flow")
        raise


def launch_for_email(db_path, email, profiles_dir=None):
    return _launch_for_profile(db_path, ensure_profile(db_path, email, profiles_dir), profiles_dir)


def launch_for_job(db_path, job_id, profiles_dir=None):
    return _launch_for_profile(db_path, profile_for_job(db_path, job_id, profiles_dir), profiles_dir)


def parse_credit_text(text):
    """Parse the UI's integer credit total; 1.016 / 1,016 => 1016.

    Refuse decimals and ambiguous formats instead of recording wrong balances.
    """
    if not isinstance(text, str):
        raise ValueError("Không đọc được chuỗi tín dụng")
    value = text.strip().replace("\u00a0", " ").replace("\u202f", " ")
    match = re.match(r"^(\d{1,3}(?:[., ]\d{3})+|\d{1,7})(?![\d.,])", value)
    if not match:
        raise ValueError("Định dạng tín dụng Flow chưa được hỗ trợ")
    number = int(re.sub(r"[., ]", "", match.group(1)))
    if number > 1000000:
        raise ValueError("Số dư nằm ngoài giới hạn phần mềm")
    if not re.search(r"(?:tín\s*dụng|credits?|Google\s*Flow)", value, re.I):
        # The short class name can be reused by the site. Require label context.
        raise ValueError("Không có nhãn tín dụng Google Flow")
    return number


def credit_from_dom(page):
    """Read visible text only. Never access cookies, localStorage, tokens or APIs."""
    selector = "a.credits-link span.credits-count, .credits-info span.credits-count"
    for attempt in range(2):
        try:
            node = page.locator(selector).first
            node.wait_for(state="visible", timeout=5500 if attempt else 2500)
            return parse_credit_text(node.inner_text(timeout=2500))
        except ValueError:
            raise
        except Exception:
            if attempt:
                break
            # Credits are often in the account dropdown. Open only controls
            # labelled as an account/profile control, never arbitrary buttons.
            openers = [
                "button[aria-label*='account' i]",
                "button[aria-label*='profile' i]",
                "button[aria-label*='tài khoản' i]",
                "button:has(img[alt*='avatar' i])",
                "button:has(img[alt*='profile' i])",
            ]
            for candidate in openers:
                try:
                    btn = page.locator(candidate).first
                    if btn.is_visible():
                        btn.click(timeout=2000)
                        break
                except Exception:
                    continue
    raise ValueError(
        "Không tìm thấy số dư Flow đang hiển thị. Đảm bảo bạn đăng nhập "
        "đúng Gmail trong Chrome profile; giao diện Flow có thể đã thay đổi."
    )


def read_profile_credits(db_path, email, profiles_dir=None):
    """One read-only, on-demand browser inspection using the saved Chrome profile.

    This is UI text extraction, not a supported/official Google credits API.
    It must run when the normal profile window is CLOSED (same profile directory).
    """
    info = ensure_profile(db_path, email, profiles_dir)
    folder = info["folder"]
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(folder), channel="chrome", headless=True,
            accept_downloads=False, viewport={"width": 1400, "height": 950},
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=35000)
            if urlparse(page.url).hostname != "labs.google":
                raise ValueError("Profile chưa đăng nhập Google Flow hoặc bị chuyển trang xác thực")
            balance = credit_from_dom(page)
        finally:
            context.close()
    flow_accounts.update_browser_balance(db_path, email, balance)
    return balance


def _reserve_credit_worker(db_path, info, profiles_dir=None):
    root = Path(profiles_dir) if profiles_dir is not None else PROFILES
    folder = info["folder"]
    lock = folder / LOCK_NAME
    token = uuid4().hex
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError(
            "Hãy đóng cửa sổ Chrome của Gmail này trước khi đọc điểm tín dụng."
        ) from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(token)
        _write_status(folder, "checking_credits", "Đang đọc tín dụng trên Flow bằng Chrome profile riêng")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "credits-worker",
             str(Path(db_path).resolve()), info["email"], token, str(root.resolve())],
            cwd=str(ROOT), creationflags=flags, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, close_fds=True)
        return {"ok": True, "email": info["email"],
                "message": "Đã bắt đầu kiểm tra điểm trên Chrome profile riêng. Đợi kết quả hiển thị trong bảng."}
    except Exception:
        lock.unlink(missing_ok=True)
        _write_status(folder, "credits_unavailable", "Không khởi động được phép đọc tín dụng")
        raise


def request_credit_check(db_path, email, profiles_dir=None):
    return _reserve_credit_worker(
        db_path, ensure_profile(db_path, email, profiles_dir), profiles_dir)


def credit_worker(db_path, email, token, profiles_dir=None):
    info = ensure_profile(db_path, email, profiles_dir)
    folder = info["folder"]
    lock = folder / LOCK_NAME
    if not ID_RE.fullmatch(token) or not lock.is_file() or lock.read_text(encoding="utf-8") != token:
        raise RuntimeError("Không có khóa Chrome profile hợp lệ")
    try:
        balance = read_profile_credits(db_path, email, profiles_dir)
        _write_status(folder, "credits_updated", "Đã đọc " + str(balance) +
                      " tín dụng từ giao diện Google Flow")
    except Exception as exc:
        # Do not overwrite the last known balance on login errors/DOM changes.
        message = str(exc) if isinstance(exc, ValueError) else (
            "Lỗi đọc tín dụng (" + type(exc).__name__ +
            "). Kiểm tra Chrome/Playwright và thử lại sau khi đăng nhập.")
        _write_status(folder, "credits_unavailable", message)
    finally:
        try:
            if lock.read_text(encoding="utf-8") == token:
                lock.unlink(missing_ok=True)
        except OSError:
            pass


def chrome_binary():
    """Use normal installed Google Chrome: manual login, no automation flags."""
    candidates = []
    if os.name == "nt":
        for key in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(key)
            if base:
                candidates.append(Path(base) / "Google" / "Chrome" /
                                  "Application" / "chrome.exe")
    elif sys.platform == "darwin":
        candidates.append(Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"))
    for name in ("google-chrome", "google-chrome-stable", "chrome"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError("Không tìm thấy Google Chrome. Hãy cài Chrome trên máy.")


def browser_worker(db_path, email, token, profiles_dir=None):
    """Open ordinary Chrome with dedicated user-data-dir; Google login is manual.

    No browser automation, hidden navigation, cookie inspection or token export.
    The same private directory can be used later by an explicitly approved
    integration, only after its ordinary Chrome window has closed.
    """
    info = ensure_profile(db_path, email, profiles_dir)
    folder = info["folder"]
    lock = folder / LOCK_NAME
    if not ID_RE.fullmatch(token) or not lock.is_file() or lock.read_text(encoding="utf-8") != token:
        raise RuntimeError("Phiên Chrome profile không có khóa hợp lệ")
    try:
        executable = chrome_binary()
        chrome = subprocess.Popen(
            [executable, "--user-data-dir=" + str(folder), "--new-window",
             "--no-first-run", FLOW_URL],
            cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _write_status(folder, "open", "Chrome profile đã mở để đăng nhập Google thủ công")
        chrome.wait()
        _write_status(folder, "closed", "Đã đóng Chrome profile")
        # Inspect the displayed balance after manual sign-in Chrome exits.
        # Browser profile is no longer in use by the normal Chrome process.
        try:
            balance = read_profile_credits(db_path, email, profiles_dir)
            _write_status(folder, "credits_updated",
                          "Đã đọc " + str(balance) + " tín dụng sau khi đóng Chrome")
        except Exception as exc:
            detail = str(exc) if isinstance(exc, ValueError) else (
                "Không tự đọc được tín dụng (" + type(exc).__name__ +
                "). Dùng nút Đọc tín dụng khi cần.")
            _write_status(folder, "credits_unavailable", detail)
    except Exception as exc:
        _write_status(folder, "error", "Không mở được Chrome: " + type(exc).__name__ +
                      ". Cần cài Google Chrome trên máy.")
    finally:
        try:
            if lock.read_text(encoding="utf-8") == token:
                lock.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    if len(sys.argv) != 6 or sys.argv[1] not in ("open-worker", "credits-worker"):
        raise SystemExit("Only the local dashboard can start a Flow profile worker")
    args = (Path(sys.argv[2]), sys.argv[3], sys.argv[4], Path(sys.argv[5]))
    if sys.argv[1] == "open-worker":
        browser_worker(*args)
    else:
        credit_worker(*args)
