"""Offline tests: read-only local session inspection; never persist cookie secrets."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

LEGACY=Path(__file__).resolve().parents[2]/"legacy"/"tea_ai_local"
sys.path.insert(0,str(LEGACY))
import session_monitor as sm


class Locator:
    def __init__(self,visible=False):
        self.visible=visible
    @property
    def first(self):
        return self
    def is_visible(self, timeout=1000):
        return self.visible


class FakePage:
    def __init__(self,url,password=False,seller=False):
        self.url=url
        self.password=password
        self.seller=seller
    def is_closed(self):
        return False
    def locator(self, selector):
        return Locator(self.password if 'password' in selector else self.seller)


class FakeContext:
    def __init__(self,page,cookies):
        self.pages=[page]
        self._cookies=cookies
        self.requested_urls=[]
    def cookies(self,urls):
        self.requested_urls=urls
        return self._cookies


class SessionMonitorTests(unittest.TestCase):
    def test_login_form_always_means_logged_out(self):
        status,_=sm.classify('shopee','https://banhang.shopee.vn/login',4,True)
        self.assertEqual(status,'logged_out')

    def test_authenticated_portal_with_cookie(self):
        status,_=sm.classify('shopee','https://banhang.shopee.vn/portal/home',3)
        self.assertEqual(status,'logged_in')

    def test_cookie_alone_is_not_proof(self):
        status,_=sm.classify('shopee','https://banhang.shopee.vn/',20)
        self.assertEqual(status,'unknown')
        status,_=sm.classify('tiktok','https://seller-vn.tiktok.com/',20)
        self.assertEqual(status,'unknown')

    def test_missing_cookie_cannot_be_logged_in(self):
        status,_=sm.classify('shopee','https://banhang.shopee.vn/portal/home',0)
        self.assertEqual(status,'unknown')

    def test_cookie_values_never_leave_browser_process(self):
        context=FakeContext(FakePage('https://banhang.shopee.vn/portal/home'),
                            [{'name':'session','value':'SUPER_SECRET_COOKIE_VALUE','domain':'.shopee.vn'}])
        account={'platform':'shopee','start_url':'https://banhang.shopee.vn/'}
        with tempfile.TemporaryDirectory() as t:
            report=sm.inspect_and_save(context,account,Path(t))
            saved=(Path(t)/sm.STATUS_FILE).read_text(encoding='utf-8')
            self.assertEqual(report['status'],'logged_in')
            self.assertEqual(report['cookie_count'],1)
            self.assertNotIn('SUPER_SECRET_COOKIE_VALUE',saved)
            self.assertNotIn('session',saved.lower())
            self.assertEqual(context.requested_urls,[account['start_url']])

    def test_private_status_does_not_claim_login_when_absent(self):
        with tempfile.TemporaryDirectory() as t:
            x=sm.read_status(Path(t))
            self.assertEqual(x['status'],'unknown')


if __name__ == '__main__':
    unittest.main()
