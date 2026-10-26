"""Read-only, local session status inspection for user-owned browser profiles.

Cookies are queried *inside* an authorized persistent Playwright context.
No cookie name/value, storage state, token, account identifier or URL query is
exported to logs, responses, Telegram or GitHub. Cookies alone do not prove
a currently valid Shopee/TikTok session.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


STATUS_FILE = "login_status.json"
ACTIVE_STATES = {"logged_in", "logged_out", "unknown", "error", "checking"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def domain_belongs_to_shop(url, platform):
    host = (urlparse(url).hostname or "").lower()
    suffix = ".shopee.vn" if platform == "shopee" else ".tiktok.com"
    return host == suffix[1:] or host.endswith(suffix)


def classify(platform, url, cookie_count, password_visible=False, seller_ui=False):
    """Conservative result. No direct cookie bytes are needed to classify."""
    path = (urlparse(url).path or "").lower().rstrip("/")
    host = (urlparse(url).hostname or "").lower()
    if password_visible or any(x in path.split("/") for x in ("login", "signin", "sign-in")):
        return "logged_out", "Đang hiển thị màn hình đăng nhập."
    if not domain_belongs_to_shop(url, platform):
        return "unknown", "Trình duyệt chưa ở trang Seller Center được xác định."
    if platform == "shopee":
        # Shopee Seller Center's authenticated pages commonly use /portal/.
        authenticated_area = host == "banhang.shopee.vn" and (path == "/portal" or path.startswith("/portal/"))
    else:
        # TikTok Shop paths vary by locale and rollout; rely on visible
        # authenticated navigation rather than assuming all paths are private.
        authenticated_area = False
    if cookie_count > 0 and (authenticated_area or seller_ui):
        return "logged_in", "Có cookie và tín hiệu trang quản trị đã đăng nhập."
    if cookie_count == 0:
        return "unknown", "Không thấy cookie áp dụng cho Seller Center; chưa đủ dữ liệu để kết luận đã logout."
    return "unknown", "Có cookie nhưng chưa xác thực được trang quản trị; cookie có thể đã hết hạn."


def read_status(profile_dir):
    path = Path(profile_dir) / STATUS_FILE
    if not path.is_file():
        return {"status": "unknown", "cookie_count": 0, "checked_at": None,
                "message": "Chưa kiểm tra đăng nhập"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {key: data.get(key) for key in ("status", "cookie_count", "checked_at", "message")} | {
            "status": data.get("status") if data.get("status") in ACTIVE_STATES else "unknown"
        }
    except (ValueError, OSError, TypeError):
        return {"status": "unknown", "cookie_count": 0, "checked_at": None,
                "message": "Không đọc được kết quả kiểm tra cũ"}


def write_status(profile_dir, state, count=0, message=""):
    from shop_profiles import _private_write
    if state not in ACTIVE_STATES:
        raise ValueError("Trạng thái đăng nhập không hợp lệ")
    _private_write(Path(profile_dir) / STATUS_FILE, {
        "status": state,
        "cookie_count": max(0, int(count)),
        "checked_at": now(),
        "message": str(message)[:250],
    })


def _active_page(context, platform):
    candidates = [p for p in context.pages if not p.is_closed()]
    for page in reversed(candidates):
        if domain_belongs_to_shop(page.url, platform):
            return page
    return candidates[-1] if candidates else None


def inspect_context(context, account):
    """Read status, not authentication material. No external network/API calls."""
    platform = account["platform"]
    page = _active_page(context, platform)
    if page is None:
        return "unknown", 0, "Không còn tab trình duyệt đang mở."
    try:
        # Scopes cookies to Seller Center. Never serialize these cookie objects.
        scoped = context.cookies([account["start_url"]])
        count = len(scoped)
    except Exception:
        count = 0
    password_visible = False
    try:
        password_visible = page.locator('input[type="password"]').first.is_visible(timeout=1000)
    except Exception:
        pass
    seller_ui = False
    try:
        # A visible seller navigation affordance is an additional signal;
        # selectors are heuristic and may change between UI versions.
        seller_ui = page.locator('nav a[href*="/portal/"], aside a[href*="/portal/"]').first.is_visible(timeout=1000)
    except Exception:
        pass
    state, explanation = classify(platform, page.url, count, password_visible, seller_ui)
    return state, count, explanation


def inspect_and_save(context, account, profile_dir):
    state, count, msg = inspect_context(context, account)
    write_status(profile_dir, state, count, msg)
    return read_status(profile_dir)
