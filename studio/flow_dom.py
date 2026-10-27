"""Extract Flow credits from the live DOM of the OWNER'S isolated Chrome window.

An explicit add-account operation launches Chrome with a random loopback CDP
port and a dedicated non-default user-data-dir. Playwright attaches read-only;
it never inspects browser cookies, auth headers, storage, or login inputs.
Full rendered HTML is read briefly in memory, NEVER persisted, logged or sent
to the UI. Only a single Gmail and the labeled credit number are retained.
Windows UI Automation remains the fallback if CDP is unavailable.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import re
import time

import flow_accounts
import flow_profiles


class _FlowHtml(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.emails=set()
        self.credits=set()
        self.depth=0
        self.credits_depth=None
        self.fragments=[]

    def handle_starttag(self, tag, attributes):
        attrs=dict(attributes)
        cls=(attrs.get("class") or "").split()
        if tag=="a" and "credits-link" in cls:
            href=attrs.get("href","")
            try:
                parsed=urlparse(href)
                if parsed.scheme=="https" and parsed.hostname=="accounts.google.com":
                    for key,values in parse_qs(parsed.query).items():
                        if key.lower()=="email" and len(values)==1:
                            self.emails.add(flow_accounts.normalize_email(values[0]))
            except (ValueError,TypeError):
                pass
        # HTML void elements never receive a closing tag.
        if tag not in ("area","base","br","col","embed","hr","img","input",
                       "link","meta","param","source","track","wbr"):
            self.depth+=1
        if self.credits_depth is None and any(
            x in cls for x in ("credits-count","credits-label","credits-info")
        ):
            self.credits_depth=self.depth
            self.fragments=[]

    def handle_data(self, data):
        if self.credits_depth is not None and self.depth>=self.credits_depth:
            self.fragments.append(str(data)[:160])

    def handle_endtag(self, tag):
        if self.credits_depth is not None and self.depth==self.credits_depth:
            value=" ".join(x.strip() for x in self.fragments if x.strip())[:240]
            if value:
                try:
                    self.credits.add(flow_profiles.parse_credit_text(value))
                except ValueError:
                    # Dedicated credits-count may contain just a number.
                    if re.fullmatch(r"\d{1,7}|\d{1,3}(?:[., ]\d{3})+",value):
                        try:
                            self.credits.add(flow_profiles.parse_credit_text(
                                value+" Google Flow credits"))
                        except ValueError:
                            pass
            self.credits_depth=None
            self.fragments=[]
        self.depth=max(0,self.depth-1)


def parse_flow_html(rendered_html, visible_email=None):
    """Read source markers from a rendered snapshot; never return raw HTML."""
    if not isinstance(rendered_html,str) or len(rendered_html)>6_000_000:
        return None
    parser=_FlowHtml()
    parser.feed(rendered_html)
    if visible_email:
        try:
            address=flow_accounts.normalize_email(visible_email)
            if not parser.emails:
                parser.emails.add(address)
        except ValueError:
            pass
    if len(parser.emails)!=1 or len(parser.credits)!=1:
        return None
    return next(iter(parser.emails)),next(iter(parser.credits))


def _visible_single_email(page):
    """Get only an unambiguous displayed email label, not hidden form values."""
    try:
        matches=page.evaluate("""() => {
          const rx = /^[\\w.+-]+@[\\w.-]+\\.[A-Za-z]{2,24}$/;
          const candidates=[];
          for (const e of document.querySelectorAll(
            '[data-testid*="email" i], [class*="email" i], [aria-label*="account" i], a.credits-link'
          )) {
            if (candidates.length>=20) break;
            const st=getComputedStyle(e);
            if(st.display==='none'||st.visibility==='hidden'||!e.getClientRects().length)continue;
            const txt=(e.innerText||e.getAttribute('aria-label')||'').trim();
            if(rx.test(txt))candidates.push(txt.toLowerCase());
          }
          return [...new Set(candidates)];
        }""")
        if isinstance(matches,list) and len(matches)==1 and isinstance(matches[0],str):
            return matches[0]
    except Exception:
        pass
    return None


def read_flow_tab(page):
    """Read post-JavaScript page.content() (rendered DOM HTML) in memory only."""
    parsed=urlparse(page.url)
    if parsed.scheme!="https" or parsed.hostname!="labs.google":
        return None
    # This is the complete *rendered* DOM snapshot, not the initial GET HTML.
    # Do NOT save, print, transmit or return the snapshot itself.
    html=page.content()
    result=parse_flow_html(html,_visible_single_email(page))
    del html
    return result


def _credit_menu(page):
    """Open only the account popup on Flow, never any login or video control."""
    for selector in (
        "button[aria-label*='account' i]",
        "button[aria-label*='profile' i]",
        "button[aria-label*='tài khoản' i]",
        "button:has(img[alt*='avatar' i])",
    ):
        try:
            button=page.locator(selector).first
            if button.is_visible(timeout=300):
                button.click(timeout=950)
                return True
        except Exception:
            pass
    return False


def devtools_port(folder):
    """Trust only port advertised by the exact private Chrome profile."""
    file=Path(folder)/"DevToolsActivePort"
    try:
        lines=file.read_text(encoding="ascii").splitlines()
        value=int(lines[0].strip())
        return value if 1024<=value<=65535 else None
    except (OSError,ValueError,IndexError,UnicodeError):
        return None


def wait_for_dom_account(chrome,folder,*,timeout_seconds=900,
                         polling_seconds=3,connect_wait_seconds=12,
                         sleep=time.sleep,clock=time.monotonic):
    """Return (email, credits, owned_window_or_None, source) or None.

    If no Chrome CDP listener is available, return fast for UIA fallback.
    Never attach to a port supplied by the user or to another Chrome profile.
    """
    from playwright.sync_api import sync_playwright
    import flow_uia
    begin=clock()
    port=None
    while chrome.poll() is None and clock()-begin<connect_wait_seconds:
        port=devtools_port(folder)
        if port is not None:break
        sleep(.3)
    if port is None:return None
    with sync_playwright() as playwright:
        browser=playwright.chromium.connect_over_cdp(
            "http://127.0.0.1:"+str(port),timeout=6000)
        current=None
        stable=0
        ui_current=None
        ui_stable=0
        opened=set()
        end=clock()+max(0,timeout_seconds)
        while chrome.poll() is None and clock()<end:
            reading=None
            for context in browser.contexts:
                for page in context.pages:
                    try:
                        found=read_flow_tab(page)
                        if found:
                            reading=found
                            break
                        if urlparse(page.url).hostname=="labs.google":
                            # Avoid repeatedly toggling the avatar menu.
                            page_id=id(page)
                            if page_id not in opened:
                                opened.add(page_id)
                                _credit_menu(page)
                    except Exception:
                        continue
                if reading:break
            stable=stable+1 if reading and reading==current else 1 if reading else 0
            current=reading
            windows=flow_uia.owned_chrome_windows(chrome.pid)
            ui_reading=None
            ui_window=None
            for window in windows:
                try:
                    values=flow_uia.extract_account(flow_uia.visible_text_labels(window))
                    if values:
                        ui_reading=values
                        ui_window=window
                        break
                except Exception:
                    continue
            ui_stable=ui_stable+1 if ui_reading and ui_reading==ui_current else 1 if ui_reading else 0
            ui_current=ui_reading
            if stable>=2:
                return reading[0],reading[1],windows[0] if windows else None,'browser_dom'
            if ui_stable>=2:
                return ui_reading[0],ui_reading[1],ui_window,'browser_uia'
            sleep(polling_seconds)
    return None
