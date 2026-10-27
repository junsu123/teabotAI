"""Read only visible Google Flow labels through Windows UI Automation.

Used after the owner signs in via ordinary installed Google Chrome; NO
Playwright, remote debugging, extension, cookies, passwords or tokens. Chrome
138+ exposes Windows UIA natively. Results are best-effort and require two
consecutive matching snapshots before account/profile enrollment.
"""
from __future__ import annotations

from collections import deque
import re
import sys
import time

import flow_accounts
import flow_profiles

EMAIL_ONLY = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._%+\-]{0,62}@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,24}$")
FLOW_LABEL = re.compile(r"(?:tín\s*dụng\s*Google\s*Flow|Google\s*Flow\s*credits?)", re.I)
NUMBER_ONLY = re.compile(r"^\d{1,3}(?:[., ]\d{3})+$|^\d{1,7}$")
MAX_NODES = 1600
MAX_DEPTH = 24


def extract_account(labels):
    """Extract exactly one full email and labeled integer credit from UIA text.

    A free-standing number is never trusted unless adjacent to a literal
    'tín dụng Google Flow' or 'Google Flow credits' accessibility label.
    No other UIA field values are retained or transmitted.
    """
    if not isinstance(labels, (list, tuple)):
        return None
    items = []
    for item in labels[:MAX_NODES]:
        if isinstance(item, str):
            clean = " ".join(item.strip().split())[:220]
            if clean:
                items.append(clean)
    emails = set()
    credit_values = set()
    for index, value in enumerate(items):
        if EMAIL_ONLY.fullmatch(value):
            try:
                emails.add(flow_accounts.normalize_email(value))
            except ValueError:
                pass
        if FLOW_LABEL.search(value):
            try:
                credit_values.add(flow_profiles.parse_credit_text(value))
            except ValueError:
                # Chrome accessibility sometimes exposes the count and label
                # as adjacent Text nodes. Only accept a neighboring count.
                for neighbor in (index - 1, index + 1):
                    if 0 <= neighbor < len(items) and NUMBER_ONLY.fullmatch(items[neighbor]):
                        try:
                            credit_values.add(flow_profiles.parse_credit_text(
                                items[neighbor] + " " + value))
                        except ValueError:
                            pass
    if len(emails) != 1 or len(credit_values) != 1:
        return None
    return next(iter(emails)), next(iter(credit_values))


def _control_type(element):
    try:
        return str(element.element_info.control_type or "")
    except Exception:
        return ""


def visible_text_labels(window):
    """Inspect only accessible Text/Hyperlink *names*, never editable values.

    Cap the traversal to avoid slow Chrome trees. Return short-lived labels for
    parsing; do not log, persist, or expose a raw accessibility tree.
    """
    queue = deque([(window, 0)])
    collected = []
    inspected = 0
    while queue and inspected < MAX_NODES:
        node, depth = queue.popleft()
        inspected += 1
        kind = _control_type(node)
        if kind in ("Edit", "Password", "ComboBox"):
            continue
        if kind in ("Text", "Hyperlink"):
            try:
                if node.is_visible():
                    value = node.window_text()
                    if isinstance(value, str) and value.strip():
                        collected.append(value)
            except Exception:
                pass
        if depth < MAX_DEPTH:
            try:
                children = node.children()
                queue.extend((child, depth + 1) for child in children[:80])
            except Exception:
                pass
    return collected


def owned_chrome_windows(chrome_pid, desktop_factory=None):
    """Only inspect windows owned by the Chrome PID for the new profile.

    Never scan other Gmail/Chrome profiles. The dedicated user-data-dir makes
    the Chrome process/window association deterministic on normal launches.
    """
    if not isinstance(chrome_pid, int) or chrome_pid < 1:
        return []
    if desktop_factory is None:
        if sys.platform != "win32":
            return []
        from pywinauto import Desktop  # Windows-only optional dependency
        desktop_factory = lambda: Desktop(backend="uia")
    try:
        candidates = desktop_factory().windows()
    except Exception:
        return []
    result = []
    for window in candidates:
        try:
            if (window.process_id() == chrome_pid
                    and window.class_name() == "Chrome_WidgetWin_1"
                    and window.is_visible()):
                result.append(window)
        except Exception:
            continue
    return result


def wait_for_visible_account(chrome_process, *,
                             timeout_seconds=900, poll_seconds=2,
                             desktop_factory=None, sleep=time.sleep,
                             clock=time.monotonic):
    """Watch UIA without controlling Google login or opening another browser.

    Returns (email, credits, owned_window) on TWO stable readings, otherwise
    None. The operator may need to open Google Flow's account panel manually.
    """
    if sys.platform != "win32" and desktop_factory is None:
        return None
    deadline = clock() + timeout_seconds
    previous = None
    stable = 0
    while clock() < deadline and chrome_process.poll() is None:
        found = None
        for window in owned_chrome_windows(chrome_process.pid, desktop_factory):
            values = extract_account(visible_text_labels(window))
            if values:
                found = (values, window)
                break
        if found is not None:
            data, window = found
            stable = stable + 1 if data == previous else 1
            previous = data
            if stable >= 2:
                return data[0], data[1], window
        else:
            stable = 0
            previous = None
        sleep(poll_seconds)
    return None


def close_owned_window(window, chrome_pid):
    """Request a graceful close ONLY for the verified Chrome instance."""
    try:
        if window.process_id() != chrome_pid or window.class_name() != "Chrome_WidgetWin_1":
            return False
        window.close()
        return True
    except Exception:
        return False
