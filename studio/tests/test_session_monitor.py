"""Offline checks for protected-page DOM verification (no cookie authentication)."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

LEGACY = Path(__file__).resolve().parents[2] / "legacy" / "tea_ai_local"
sys.path.insert(0, str(LEGACY))
import session_monitor as sm


class FakePage:
    def __init__(self, url, menu_count=0, password=False, verify=False):
        self.url = url
        self.result = {
            "seller_menu_count": menu_count, "password_visible": password,
            "verification_visible": verify,
        }
    def is_closed(self):
        return False
    def evaluate(self, script):
        assert "seller_menu_count" in script
        return self.result


class FakeContext:
    def __init__(self, page):
        self.pages = [page]
    def cookies(self, *_):
        raise AssertionError("Cookie must not be read to determine login")


class SessionMonitorTests(unittest.TestCase):
    def test_portal_url_alone_does_not_mean_login(self):
        state, _ = sm.classify("shopee", "https://banhang.shopee.vn/portal/home", 100)
        self.assertEqual(state, "unknown")

    def test_verified_seller_navigation_indicates_login(self):
        state, _ = sm.classify("shopee", "https://banhang.shopee.vn/portal/home",
                               0, seller_menu_count=2)
        self.assertEqual(state, "logged_in")

    def test_tiktok_deep_page_with_two_seller_sections(self):
        state, _ = sm.classify("tiktok", "https://seller-vn.tiktok.com/product/manage",
                               0, seller_menu_count=3)
        self.assertEqual(state, "logged_in")

    def test_login_form_even_with_navigation_is_logged_out(self):
        state, _ = sm.classify("shopee", "https://banhang.shopee.vn/account/login",
                               100, password_visible=True, seller_menu_count=10)
        self.assertEqual(state, "logged_out")

    def test_verification_requires_human(self):
        state, _ = sm.classify("tiktok", "https://seller-vn.tiktok.com/account/verify",
                               0, verification_visible=True)
        self.assertEqual(state, "verification_required")

    def test_wrong_domain_is_never_valid(self):
        state, _ = sm.classify("shopee", "https://banhang.shopee.vn.evil.example/portal",
                               0, seller_menu_count=3)
        self.assertEqual(state, "unknown")

    def test_no_private_auth_data_saved(self):
        page = FakePage("https://banhang.shopee.vn/portal/product/list?token=SUPER_SECRET",
                        menu_count=3)
        ctx = FakeContext(page)
        account = {"platform": "shopee", "start_url": "https://banhang.shopee.vn/"}
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            result = sm.inspect_and_save(ctx, account, folder)
            # A stale visible tab is NOT enough; needs a fresh protected load.
            self.assertEqual(result["status"], "checking")
            result = sm.inspect_and_save(ctx, account, folder, fresh_navigation=True)
            self.assertEqual(result["status"], "logged_in")
            status_text = (folder / sm.STATUS_FILE).read_text(encoding="utf-8")
            self.assertNotIn("SUPER_SECRET", status_text)
            self.assertNotIn("cookie_count", status_text)
            # Query (and any token) is stripped; only the safe protected path persists.
            self.assertTrue((folder / sm.PROBE_FILE).exists())
            probe_text = (folder / sm.PROBE_FILE).read_text(encoding="utf-8")
            self.assertNotIn("SUPER_SECRET", probe_text)
            self.assertEqual(json.loads(probe_text)["url"],
                             "https://banhang.shopee.vn/portal/product/list")

    def test_save_safe_verified_protected_url_and_expire(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            self.assertTrue(sm.save_probe(folder, "shopee",
                          "https://banhang.shopee.vn/portal/products"))
            account = {"platform": "shopee", "start_url": "https://banhang.shopee.vn/"}
            self.assertEqual(sm.probe_url(folder, account),
                             "https://banhang.shopee.vn/portal/products")
            self.assertFalse(sm.save_probe(folder, "shopee",
                             "https://banhang.shopee.vn.evil.test/portal/products"))
            sm.write_status(folder, "logged_in", message="DOM đã xác nhận")
            saved = json.loads((folder / sm.STATUS_FILE).read_text(encoding="utf-8"))
            saved["checked_at"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            (folder / sm.STATUS_FILE).write_text(json.dumps(saved), encoding="utf-8")
            self.assertEqual(sm.read_status(folder)["status"], "unknown")

    def test_invalidates_cookie_only_legacy_status(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / sm.STATUS_FILE).write_text(
                json.dumps({"status":"logged_in", "cookie_count":100, "checked_at":sm.now()}),
                encoding="utf-8")
            self.assertEqual(sm.read_status(folder)["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
