"""Read visible Flow credits from a user-controlled Playwright Chrome window.

Authentication happens inside the browser and Chrome keeps its own profile
session. This module never reads or exports cookies, passwords, or tokens.
"""
from __future__ import annotations

from urllib.parse import urlparse, parse_qs
import time

import flow_accounts
import flow_profiles


def credits_account_email(page):
    """Require the full Gmail in the visible Flow credit-link destination."""
    try:
        href = page.locator("a.credits-link[href]").first.get_attribute(
            "href", timeout=1500)
        parsed = urlparse(href or "")
        if parsed.scheme != "https" or parsed.hostname != "accounts.google.com":
            return None
        for key, values in parse_qs(parsed.query).items():
            if key.lower() == "email" and len(values) == 1:
                return flow_accounts.normalize_email(values[0])
    except (ValueError, TypeError):
        return None
    except Exception:
        return None
    return None


def validated_credit(page, expected_email):
    """Read only displayed credits for the verified expected Gmail."""
    observed = credits_account_email(page)
    if observed is None:
        return "identity_unknown", None
    if observed != flow_accounts.normalize_email(expected_email):
        return "wrong_email", None
    try:
        return "verified", flow_profiles.credit_from_dom(page)
    except Exception:
        return "no_credit", None


def check_visible_pages(context, expected_email):
    """Use current Flow tabs only, never inspect credentials or site storage."""
    for page in context.pages:
        try:
            if page.is_closed() or urlparse(page.url).hostname != "labs.google":
                continue
            result = validated_credit(page, expected_email)
            if result[0] in ("verified", "wrong_email", "no_credit"):
                return result
        except Exception:
            continue
    return "awaiting_login", None


def observe_login(context, db_path, email, write_status,
                  deadline_seconds=600, poll_seconds=3):
    """Return True after validated credit persisted; caller closes context.

    On timeout or account mismatch, do not falsely mark Gmail authenticated.
    """
    deadline = time.monotonic() + deadline_seconds
    last_status = None
    while time.monotonic() < deadline:
        if not [p for p in context.pages if not p.is_closed()]:
            return False
        state, credits = check_visible_pages(context, email)
        if state == "verified":
            flow_accounts.update_browser_balance(db_path, email, credits)
            write_status("signin_captured",
                         "Đã xác minh Gmail và lưu tín dụng hiển thị từ Flow.")
            return True
        status = {
            "awaiting_login": ("signin_pending", "Đang chờ đăng nhập Google Flow"),
            "wrong_email": ("signin_wrong_account",
                            "Đang đăng nhập Gmail khác. Hãy chuyển đúng tài khoản đã thêm."),
            "identity_unknown": ("signin_verifying",
                                 "Chưa xác minh được địa chỉ Gmail trên Flow."),
            "no_credit": ("signin_verifying",
                          "Đã xác minh Gmail, đang chờ hiển thị tín dụng.")
        }.get(state, ("signin_pending", "Đang chờ đăng nhập"))
        if status != last_status:
            write_status(*status)
            last_status = status
        time.sleep(poll_seconds)
    write_status("signin_timeout",
                 "Chưa xác minh được Gmail và tín dụng. Hãy đóng Chrome thủ công.")
    return False
