"""Verify the live Seller Center page, not cookies.

Runs only inside the owner's visible, isolated Playwright Chrome profile.
Reads page URL + non-sensitive Boolean DOM indicators. Never exports cookies,
storage state, tokens, login fields, shop identity or full page contents.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

STATUS_FILE = "login_status.json"
PROBE_FILE = "login_probe.json"
PROBE_REQUEST = "check_login.request"
ACTIVE_STATES = {"logged_in", "logged_out", "verification_required",
                 "unknown", "error", "checking"}
VERIFICATION_VERSION = 2
STALE_AFTER_SECONDS = 300

# Only non-sensitive UI presence is returned from page.evaluate().
# "Logged in" requires visible, distinct seller-only navigation groups.
SELLER_UI_JS = r"""() => {
  const visible = e => {
    const s = getComputedStyle(e), box = e.getBoundingClientRect();
    return s.visibility !== 'hidden' && s.display !== 'none' &&
      box.width > 0 && box.height > 0 && s.opacity !== '0';
  };
  const nodes = Array.from(document.querySelectorAll(
    'nav a, aside a, [role="navigation"] a, [role="menuitem"], ' +
    '[class*="sidebar"] a, [class*="Sidebar"] a, [class*="sidebar"] [role="menuitem"]'
  )).slice(0,400);
  const groups = new Set();
  for (const el of nodes) {
    if (!visible(el)) continue;
    const label = (el.innerText || el.getAttribute('aria-label') || '')
      .trim().toLowerCase().slice(0,100);
    if (/sản phẩm|products?|hàng hóa|quản lý sản phẩm/.test(label)) groups.add('products');
    if (/đơn hàng|orders?|quản lý đơn/.test(label)) groups.add('orders');
    if (/vận chuyển|shipping|đơn vị vận/.test(label)) groups.add('shipping');
    if (/doanh thu|analytics|phân tích|dữ liệu/.test(label)) groups.add('analytics');
    if (/tổng quan|dashboard|bảng điều khiển/.test(label)) groups.add('dashboard');
    if (/marketing|tiếp thị/.test(label)) groups.add('marketing');
  }
  const pwd = Array.from(document.querySelectorAll('input[type="password"]'))
    .some(visible);
  const verify = Array.from(document.querySelectorAll('input'))
    .some(e => visible(e) && (
       /otp|verification|verify|one.time|2fa|captcha/i.test(
         [e.name, e.id, e.placeholder, e.getAttribute('aria-label')].join(' ')
       )
    ));
  return {seller_menu_count: groups.size, password_visible: pwd,
          verification_visible: verify};
}"""

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def official_host(platform):
    return "banhang.shopee.vn" if platform == "shopee" else "seller-vn.tiktok.com"


def domain_belongs_to_shop(url, platform):
    parsed = urlparse(url)
    return parsed.scheme == "https" and (parsed.hostname or "").lower() == official_host(platform)


def _login_page(path):
    segments = {p for p in path.lower().split("/") if p}
    return bool(segments.intersection({"login", "signin", "sign-in"}))


def _verification_page(path):
    segments = {p for p in path.lower().split("/") if p}
    return bool(segments.intersection({"verify", "verification", "challenge", "captcha",
                                        "two-factor", "2fa", "otp"}))


def _protected_page(platform, url):
    if not domain_belongs_to_shop(url, platform):
        return False
    path = urlparse(url).path.lower().rstrip("/")
    if _login_page(path) or _verification_page(path):
        return False
    if platform == "shopee":
        return path == "/portal" or path.startswith("/portal/")
    # TikTok Shop uses country-specific routes. Require a non-public deep link.
    return path not in ("", "/", "/account", "/account/login") and not path.startswith("/account/")


def classify(platform, url, cookie_count=0, password_visible=False, seller_ui=False,
             verification_visible=False, page_error=False, seller_menu_count=None):
    """Cookie count intentionally ignored: only live protected DOM can prove login."""
    path = urlparse(url).path
    if page_error:
        return "unknown", "Trang quản trị không tải được. Không thể xác minh phiên."
    if not domain_belongs_to_shop(url, platform):
        return "unknown", "Trình duyệt chưa ở đúng Seller Center."
    if verification_visible or _verification_page(path):
        return "verification_required", "Sàn yêu cầu xác minh thêm. Hãy xử lý trên trình duyệt."
    if password_visible or _login_page(path):
        return "logged_out", "Trang đang yêu cầu đăng nhập."
    n = seller_menu_count if seller_menu_count is not None else (2 if seller_ui else 0)
    if _protected_page(platform, url) and n >= 2:
        return "logged_in", "Đã tải trang quản trị và nhận diện ít nhất hai nhóm menu nội bộ."
    return "unknown", "Chưa tìm thấy đủ dấu hiệu quản trị đã xác thực; không kết luận từ cookie hoặc URL."


def read_status(profile_dir):
    path = Path(profile_dir) / STATUS_FILE
    fallback = {"status": "unknown", "checked_at": None, "message": "Chưa kiểm tra trang quản trị"}
    if not path.is_file():
        return fallback
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        status = d.get("status", "unknown")
        if status not in ACTIVE_STATES:
            status = "unknown"
        # Invalidate status from older cookie-only monitor.
        if status == "logged_in" and d.get("verification_version") != VERIFICATION_VERSION:
            status = "unknown"
            d["message"] = "Kết quả cũ chỉ dựa vào cookie; cần kiểm tra giao diện quản trị."
        checked_at = d.get("checked_at")
        if status == "logged_in" and checked_at:
            dt = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - dt.astimezone(timezone.utc) > timedelta(seconds=STALE_AFTER_SECONDS):
                status = "unknown"
                d["message"] = "Kết quả cũ quá 5 phút. Hãy kiểm tra lại phiên."
        return {"status": status, "checked_at": checked_at,
                "message": str(d.get("message", ""))[:250]}
    except (ValueError, OSError, TypeError):
        return fallback


def write_status(profile_dir, state, count=0, message=""):
    """count stays in signature for compatibility; it is not recorded."""
    from shop_profiles import _private_write
    if state not in ACTIVE_STATES:
        raise ValueError("Trạng thái phiên không hợp lệ")
    _private_write(Path(profile_dir) / STATUS_FILE, {
        "status": state, "verification_version": VERIFICATION_VERSION,
        "checked_at": now(), "message": str(message)[:250],
    })


def _active_page(context, platform):
    pages = [p for p in context.pages if not p.is_closed()]
    for p in reversed(pages):
        if domain_belongs_to_shop(p.url, platform):
            return p
    return pages[-1] if pages else None


def _safe_protected_url(platform, url):
    if not _protected_page(platform, url):
        return ""
    p = urlparse(url)
    # Never save URL query, fragment, credentials or any session-bearing string.
    if p.username or p.password or p.query or p.fragment or p.path.startswith("//"):
        return ""
    return f"https://{official_host(platform)}{p.path}"


def save_probe(profile_dir, platform, url):
    safe = _safe_protected_url(platform, url)
    if not safe:
        return False
    from shop_profiles import _private_write
    _private_write(Path(profile_dir) / PROBE_FILE, {"url": safe})
    return True


def probe_url(profile_dir, account):
    default = account["start_url"]
    try:
        d = json.loads((Path(profile_dir) / PROBE_FILE).read_text(encoding="utf-8"))
        return _safe_protected_url(account["platform"], d.get("url", "")) or default
    except (OSError, ValueError, TypeError):
        return default


def inspect_context(context, account, page=None):
    """No API requests, no navigation side effects; read visible page indicators."""
    platform = account["platform"]
    page = page or _active_page(context, platform)
    if page is None:
        return "unknown", 0, "Không có tab trình duyệt đang mở."
    try:
        indicators = page.evaluate(SELLER_UI_JS)
        status, explanation = classify(
            platform, page.url,
            password_visible=bool(indicators.get("password_visible")),
            verification_visible=bool(indicators.get("verification_visible")),
            seller_menu_count=int(indicators.get("seller_menu_count", 0)))
        return status, 0, explanation
    except Exception:
        return "unknown", 0, "Không đọc được giao diện quản trị, có thể đang chuyển trang hoặc tải lỗi."


def inspect_and_save(context, account, profile_dir, page=None):
    page = page or _active_page(context, account["platform"])
    status, _, msg = inspect_context(context, account, page)
    write_status(profile_dir, status, message=msg)
    if status == "logged_in" and page is not None:
        save_probe(profile_dir, account["platform"], page.url)
    return read_status(profile_dir)


def verify_in_separate_tab(context, account, profile_dir):
    """A fresh protected-page navigation, without disrupting an open seller tab."""
    url = probe_url(profile_dir, account)
    page = context.new_page()
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=25000)
        if response is not None and response.status >= 400:
            write_status(profile_dir, "unknown", message="Trang quản trị báo lỗi tải trang.")
            return read_status(profile_dir)
        page.wait_for_timeout(1600)
        return inspect_and_save(context, account, profile_dir, page=page)
    except Exception:
        write_status(profile_dir, "error",
                     message="Không tải được trang kiểm tra; kiểm tra kết nối mạng, proxy và thử lại.")
        return read_status(profile_dir)
    finally:
        try:
            page.close()
        except Exception:
            pass
