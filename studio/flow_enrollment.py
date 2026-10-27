"""One-click Flow enrollment with live DOM reading and Windows UIA fallback.

After the owner's manual login, CDP connects to exactly the Chrome process
started in this private profile and reads post-JavaScript DOM HTML in memory.
Only a verified Gmail and displayed credit number are saved; no extension,
password, cookie export, auth bypass, or raw HTML persistence.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

import flow_accounts
import flow_profiles

ROOT = Path(__file__).resolve().parent
PROFILES = flow_profiles.PROFILES
RECORDS = ROOT / "data" / "flow_enrollments"
TERMINAL = {"completed", "duplicate", "needs_manual", "failed"}


def status_path(enrollment_id, records_dir=None):
    if not isinstance(enrollment_id, str) or not flow_profiles.ID_RE.fullmatch(enrollment_id):
        raise ValueError("Mã phiên thêm tài khoản không hợp lệ")
    return (Path(records_dir) if records_dir is not None else RECORDS) / (enrollment_id + ".json")


def save_status(enrollment_id, state, message, *, email=None, credits=None, records_dir=None):
    dest = status_path(enrollment_id, records_dir)
    flow_profiles.private_dir(dest.parent)
    doc = {"id": enrollment_id, "status": state, "message": str(message)[:250],
           "email": email if state == "completed" else None,
           "credits": credits if state == "completed" else None,
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


def start(db_path, profiles_dir=None, records_dir=None):
    """Create a new independent Chrome profile, WITHOUT asking for a Gmail."""
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
    save_status(enrollment_id, "opening", "Đang mở Google Chrome thông thường.",
                records_dir=records)
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        subprocess.Popen([
            sys.executable, str(Path(__file__).resolve()), "worker",
            str(Path(db_path).resolve()), enrollment_id, token,
            str(root.resolve()), str(records.resolve())],
            cwd=str(ROOT), creationflags=flags,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    except Exception:
        save_status(enrollment_id, "failed", "Không mở được Chrome profile.",
                    records_dir=records)
        shutil.rmtree(folder, ignore_errors=True)
        raise
    return {"ok": True, "enrollment_id": enrollment_id,
            "message": "Chrome đang mở. Đăng nhập Flow và mở menu tài khoản nếu cần. "
                       "Phần mềm đọc DOM HTML đã render và tín dụng, rồi đóng profile khi xác minh được."}


def register_verified(db_path, enrollment_id, email, credits, source="browser_uia"):
    """Create account and profile mapping in ONE transaction, not overwrite old."""
    email = flow_accounts.normalize_email(email)
    if type(credits) is not int or not 0 <= credits <= 1000000:
        raise ValueError("Điểm tín dụng Flow không hợp lệ")
    if source not in ("browser_uia", "manual"):
        raise ValueError("Nguồn tín dụng không hợp lệ")
    when = flow_accounts.utcnow()
    with flow_accounts.connect(db_path) as c:
        if c.execute("SELECT 1 FROM flow_accounts WHERE email=?", (email,)).fetchone():
            raise ValueError("DUPLICATE_EMAIL")
        c.execute("""INSERT INTO flow_accounts
            (email,balance,balance_checked_at,balance_source,created_at,updated_at)
            VALUES(?,?,?,?,?,?)""", (email, credits, when, source, when, when))
        c.execute("""INSERT INTO flow_browser_profiles
            (email,profile_id,created_at,last_opened_at)
            VALUES(?,?,?,?)""", (email, enrollment_id, when, when))
    return email


def complete_manually(db_path, enrollment_id, email, credits,
                      profiles_dir=None, records_dir=None):
    """Fallback after Chrome closes; status labels such credits as manual."""
    root = Path(profiles_dir) if profiles_dir is not None else PROFILES
    records = Path(records_dir) if records_dir is not None else RECORDS
    current = get_status(enrollment_id, records)
    if current["status"] != "needs_manual":
        raise ValueError("Chỉ được xác nhận thủ công khi Chrome đã đóng.")
    folder = root / enrollment_id
    if not folder.is_dir() or (folder / flow_profiles.LOCK_NAME).exists():
        raise ValueError("Profile vẫn đang mở. Đóng Chrome rồi mới lưu tài khoản.")
    email = register_verified(db_path, enrollment_id, email, credits, source="manual")
    return save_status(enrollment_id, "completed",
                       "Đã lưu Gmail và điểm do bạn tự xác nhận.",
                       email=email, credits=credits, records_dir=records)


def worker(db_path, enrollment_id, token, profiles_dir=None, records_dir=None,
           timeout_seconds=900):
    """Watch *owned* Chrome window. UIA never controls the Google sign-in form."""
    root = Path(profiles_dir) if profiles_dir is not None else PROFILES
    records = Path(records_dir) if records_dir is not None else RECORDS
    folder = root / enrollment_id
    lock = folder / flow_profiles.LOCK_NAME
    if (not flow_profiles.ID_RE.fullmatch(token) or not lock.is_file()
            or lock.read_text(encoding="utf-8") != token):
        raise RuntimeError("Phiên Chrome profile không có khóa hợp lệ")

    discard = False
    completed_email = None
    try:
        exe = flow_profiles.chrome_binary()
        chrome = subprocess.Popen([
            exe, "--user-data-dir=" + str(folder), "--new-window",
            "--remote-debugging-port=0", "--remote-debugging-address=127.0.0.1",
            "--no-first-run", flow_profiles.FLOW_URL],
            cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        save_status(enrollment_id, "signin_pending",
                    "Hãy đăng nhập Google Flow và mở menu tài khoản để hiện "
                    "địa chỉ Gmail, số tín dụng. Không cần Extension.",
                    records_dir=records)
        discovered = None
        monitor_error = None
        try:
            import flow_dom
            save_status(enrollment_id, "verifying_dom",
                        "Đang đọc DOM/HTML sau đăng nhập trên đúng Chrome profile của bạn.",
                        records_dir=records)
            discovered = flow_dom.wait_for_dom_account(
                chrome, folder, timeout_seconds=timeout_seconds)
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            monitor_error = type(exc).__name__
        if discovered is None and chrome.poll() is None:
            # Chrome debugger may be disabled by enterprise policy.
            # Preserve the previous read-only UIA inspection as a fallback.
            try:
                import flow_uia
                save_status(enrollment_id, "verifying_uia",
                            "Không kết nối được DOM Chrome; đang đọc thông tin qua Windows UIA.",
                            records_dir=records)
                discovered = flow_uia.wait_for_visible_account(
                    chrome, timeout_seconds=timeout_seconds)
            except (ImportError, OSError, RuntimeError) as exc:
                monitor_error = type(exc).__name__

        if discovered is not None:
            email, credits, window = discovered
            try:
                completed_email = register_verified(
                    db_path, enrollment_id, email, credits, source="browser_uia")
                save_status(enrollment_id, "capturing",
                            "Đã lưu Gmail và tín dụng. Đang đóng Chrome profile riêng.",
                            records_dir=records)
            except ValueError as exc:
                if str(exc) != "DUPLICATE_EMAIL":
                    raise
                discard = True
                save_status(enrollment_id, "duplicate",
                            "Gmail này đã tồn tại. Giữ nguyên profile và điểm cũ.",
                            records_dir=records)
            # Request close only after the database confirms save/duplicate.
            import flow_uia
            if window is None:
                # DOM readers may work even when the Windows accessibility
                # tree cannot be inspected. Only close a window owned by
                # this dedicated Chrome process.
                owned = flow_uia.owned_chrome_windows(chrome.pid)
                window = owned[0] if owned else None
            closed = bool(window and flow_uia.close_owned_window(window, chrome.pid))
            if closed:
                try:
                    chrome.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    # Chrome can run without a window when background apps are
                    # enabled. Stop only this new profile's Chrome process.
                    if not flow_uia.owned_chrome_windows(chrome.pid):
                        chrome.terminate()
                        try:
                            chrome.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            pass
                    else:
                        chrome.wait()
            else:
                # Never force-kill Chrome while the owner is still signing in.
                chrome.wait()
            if completed_email:
                save_status(enrollment_id, "completed",
                            "Đã lưu Gmail và tín dụng. Chrome đã đóng.",
                            email=completed_email, credits=credits,
                            records_dir=records)
        else:
            if chrome.poll() is None:
                save_status(
                    enrollment_id, "signin_timeout",
                    ("Không đọc được thông tin qua UI Automation (" + monitor_error +
                     "). Hãy đóng Chrome để xác nhận Gmail/điểm thủ công."
                     if monitor_error else
                     "Chưa thấy Gmail và điểm. Mở menu tài khoản Google Flow; "
                     "nếu vẫn không được, đóng Chrome để nhập thủ công."),
                    records_dir=records)
            # Preserve the authenticated Chrome profile and browser-owned cookies.
            chrome.wait()
            save_status(enrollment_id, "needs_manual",
                        "Không thể tự nhận diện Gmail/điểm qua UI Automation. "
                        "Bạn có thể xác nhận hai giá trị thủ công; profile vẫn còn.",
                        records_dir=records)
    except FileNotFoundError:
        discard = True
        save_status(enrollment_id, "failed",
                    "Không tìm thấy Google Chrome trên máy.",
                    records_dir=records)
    except Exception as exc:
        save_status(enrollment_id, "failed",
                    "Không hoàn tất việc thêm tài khoản (" + type(exc).__name__ +
                    "). Profile vẫn được giữ nếu đã đăng nhập.",
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
    if len(sys.argv) != 7 or sys.argv[1] != "worker":
        raise SystemExit("Chỉ Mars Studio cục bộ được tạo phiên Chrome Flow")
    worker(Path(sys.argv[2]), sys.argv[3], sys.argv[4],
           Path(sys.argv[5]), Path(sys.argv[6]))
