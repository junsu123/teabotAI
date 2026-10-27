"""Monitor one user-launched, ordinary Chrome Flow sign-in; read only visible credit text.

Chrome itself saves its login cookies to its dedicated profile folder. This module
never reads/exports browser cookies, access tokens, response headers or storage.
A short-lived localhost CDP connection is used only to inspect the open Flow tab.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse, parse_qs
import time
import re

from playwright.sync_api import sync_playwright

import flow_accounts
import flow_profiles

CDP_FILE = "DevToolsActivePort"
MONITOR_SECONDS = 600
CREDIT_RETRY_SECONDS = 3


def credits_account_email(page):
    """Use ONLY the official AccountChooser link's Email parameter as identity.

    An unverified email or a truncated label is not enough to close the browser.
    """
    try:
        link = page.locator("a.credits-link[href]").first
        href = link.get_attribute("href", timeout=1250)
        if not isinstance(href, str):
            return None
        target = urlparse(href)
        if target.scheme != "https" or target.hostname != "accounts.google.com":
            return None
        values = parse_qs(target.query)
        for key, items in values.items():
            if key.lower() == "email" and len(items) == 1:
                try:
                    return flow_accounts.normalize_email(items[0])
                except ValueError:
                    return None
    except Exception:
        return None
    return None


def validated_credit(page, target_email):
    """Return integer credit only if the Flow page proves the expected Gmail."""
    target = flow_accounts.normalize_email(target_email)
    observed = credits_account_email(page)
    if observed is None:
        return "identity_unknown", None
    if observed != target:
        return "wrong_email", None
    try:
        return "verified", flow_profiles.credit_from_dom(page)
    except Exception:
        return "no_credit", None


def wait_for_cdp_port(folder, chrome_process, seconds=20):
    """Read only Chrome's devtools port number, never its websocket auth data."""
    path = Path(folder) / CDP_FILE
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if chrome_process.poll() is not None:
            raise RuntimeError("Chrome đã đóng trước khi kiểm tra đăng nhập")
        try:
            first = path.read_text(encoding="utf-8").splitlines()[0].strip()
            port = int(first)
            if 1024 <= port <= 65535:
                return port
        except (FileNotFoundError, ValueError, IndexError, OSError):
            pass
        time.sleep(.25)
    raise RuntimeError("Chrome không hỗ trợ theo dõi đăng nhập trong profile này")


def monitor_login(db_path, email, folder, chrome_process, write_status,
                  timeout_seconds=MONITOR_SECONDS):
    """Observe a *user-driven* Chrome sign-in and close only after verified credits.

    Chrome is deliberately left open if the wrong Gmail is active, no credit is
    visible, or DOM inspection cannot be established. Session remains in Chrome.
    """
    folder = Path(folder)
    try:
        port = wait_for_cdp_port(folder, chrome_process)
    except Exception as exc:
        write_status("signin_unmonitored", str(exc))
        return False

    deadline = time.monotonic() + timeout_seconds
    success = False
    last_state = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(
                f"http://127.0.0.1:{port}", timeout=12000)
            while time.monotonic() < deadline and chrome_process.poll() is None:
                tabs = [page for ctx in browser.contexts for page in ctx.pages
                        if not page.is_closed() and
                        urlparse(page.url).hostname == "labs.google"]
                outcome = "awaiting_login"
                balance = None
                for page in tabs:
                    outcome, balance = validated_credit(page, email)
                    if outcome in ("verified", "wrong_email", "identity_unknown"):
                        break
                if outcome == "verified":
                    # Critical: save the credit before declaring successful login
                    # and before Chrome closes. Chrome manages its own cookies.
                    flow_accounts.update_browser_balance(db_path, email, balance)
                    write_status("signin_captured",
                                 f"Đã xác minh tài khoản, lưu {balance} tín dụng; Chrome đang đóng")
                    success = True
                    try:
                        browser.close()
                    except Exception:
                        pass
                    break
                status = {
                    "awaiting_login": ("signin_pending",
                                       "Đang chờ bạn đăng nhập Google Flow"),
                    "wrong_email": ("signin_wrong_account",
                                    "Bạn đang đăng nhập Gmail khác. Hãy chuyển đúng Gmail đã thêm."),
                    "identity_unknown": ("signin_verifying",
                                         "Đã thấy Google Flow, nhưng chưa xác minh được Gmail."),
                    "no_credit": ("signin_verifying",
                                  "Đúng Gmail; đang chờ tín dụng hiển thị.")
                }.get(outcome, ("signin_pending", "Đang chờ đăng nhập"))
                if status != last_state:
                    write_status(*status)
                    last_state = status
                time.sleep(CREDIT_RETRY_SECONDS)
            if not success and chrome_process.poll() is None:
                write_status("signin_timeout",
                             "Chưa xác minh được Gmail và tín dụng. Chrome vẫn mở để bạn thao tác.")
    except Exception as exc:
        write_status("signin_unmonitored",
                     "Không theo dõi được đăng nhập (" + type(exc).__name__ +
                     "). Chrome vẫn mở; bạn có thể đóng thủ công.")
    return success
