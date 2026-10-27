"""Tests of post-login DOM/HTML credit extraction. No real Google login."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import flow_dom


HTML="""<!doctype html><html><head><meta charset="utf-8"></head><body>
<script>window.fakeToken='token-that-must-never-be-returned';</script>
<div><a class="credits-link" href="https://accounts.google.com/AccountChooser?continue=flow&amp;email=owner%40gmail.com">
  <span class="credits-count">50 Google Flow credits</span>
</a></div></body></html>"""


class FakePage:
    def __init__(self,html=HTML,url="https://labs.google/fx/tools/flow"):
        self.url=url
        self.html=html
        self.calls=0
    def content(self):
        self.calls+=1
        return self.html
    def evaluate(self,script):
        return []


class FlowDomTests(unittest.TestCase):
    def test_full_rendered_html_reads_only_owner_email_and_credits(self):
        page=FakePage()
        self.assertEqual(flow_dom.read_flow_tab(page),("owner@gmail.com",50))
        self.assertEqual(page.calls,1)
        output=flow_dom.parse_flow_html(HTML)
        self.assertEqual(output,("owner@gmail.com",50))
        self.assertNotIn("token-that-must-never-be-returned",str(output))

    def test_missing_email_or_credit_must_not_mark_as_verified(self):
        without_email="""<html><body><span class="credits-count">50 credits</span></body></html>"""
        without_credit="""<html><body><a class="credits-link" href="https://accounts.google.com/path?email=owner@gmail.com">Account</a></body></html>"""
        self.assertIsNone(flow_dom.parse_flow_html(without_email))
        self.assertIsNone(flow_dom.parse_flow_html(without_credit))
        self.assertIsNone(flow_dom.parse_flow_html(HTML.replace("50 Google Flow credits","50 random visits")))

    def test_wrong_domain_or_multiple_credits_rejected(self):
        page=FakePage(url="https://accounts.google.com/signin")
        self.assertIsNone(flow_dom.read_flow_tab(page))
        self.assertEqual(page.calls,0)
        multiple=HTML.replace("</a>","<span class='credits-count'>25 Google Flow credits</span></a>")
        self.assertIsNone(flow_dom.parse_flow_html(multiple))

    def test_devtools_port_only_from_this_private_profile(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t)
            self.assertIsNone(flow_dom.devtools_port(folder))
            (folder/"DevToolsActivePort").write_text("49152\n/devtools/browser/xyz\n")
            self.assertEqual(flow_dom.devtools_port(folder),49152)
            (folder/"DevToolsActivePort").write_text("https://attacker.example")
            self.assertIsNone(flow_dom.devtools_port(folder))

    def test_large_snapshot_never_returned_or_logged(self):
        self.assertIsNone(flow_dom.parse_flow_html("x"*6_000_001))
        self.assertIsNone(flow_dom.parse_flow_html("<html>sign in, password: value</html>"))

    def test_page_dynamic_dom_update_after_login(self):
        page=FakePage(html="<html><body>Vui lòng đăng nhập</body></html>")
        self.assertIsNone(flow_dom.read_flow_tab(page))
        page.html=HTML
        self.assertEqual(flow_dom.read_flow_tab(page),("owner@gmail.com",50))


if __name__=="__main__":
    unittest.main()
