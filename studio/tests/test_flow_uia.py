"""Platform-independent unit tests for the Windows UI Automation Flow reader."""
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import flow_uia


class FakeElement:
    def __init__(self, kind, name="", children=None, *, visible=True, pid=111):
        self.element_info = mock.Mock(control_type=kind)
        self.kind = kind
        self.name = name
        self.descendants = children or []
        self.pid = pid
        self.visible = visible
        self.reads = 0
        self.closed = False

    def children(self):
        return self.descendants

    def is_visible(self):
        return self.visible

    def window_text(self):
        self.reads += 1
        return self.name

    def class_name(self):
        return "Chrome_WidgetWin_1" if self.kind == "Window" else self.kind

    def process_id(self):
        return self.pid

    def close(self):
        self.closed = True


class FakeDesktop:
    def __init__(self, windows):
        self._windows = windows

    def windows(self):
        return self._windows


class FlowUiaTests(unittest.TestCase):
    def test_parse_gmail_and_localized_credits_from_same_accessible_window(self):
        self.assertEqual(flow_uia.extract_account([
            "Google Flow",
            "owner@gmail.com",
            "1.016 tín dụng Google Flow",
        ]), ("owner@gmail.com", 1016))
        self.assertEqual(flow_uia.extract_account([
            "user@gmail.com", "996", "tín dụng Google Flow",
        ]), ("user@gmail.com", 996))
        self.assertEqual(flow_uia.extract_account([
            "one@gmail.com", "996 Google Flow credits",
        ]), ("one@gmail.com", 996))

    def test_reject_missing_credit_label_or_multiple_email_or_ambiguous_credit(self):
        self.assertIsNone(flow_uia.extract_account(["owner@gmail.com", "996"]))
        self.assertIsNone(flow_uia.extract_account([
            "one@gmail.com", "other@gmail.com", "996 tín dụng Google Flow",
        ]))
        self.assertIsNone(flow_uia.extract_account([
            "owner@gmail.com", "996 tín dụng Google Flow",
            "50 tín dụng Google Flow",
        ]))
        self.assertIsNone(flow_uia.extract_account([
            "owner@gmail.com", "3.5 tín dụng Google Flow",
        ]))
        self.assertIsNone(flow_uia.extract_account([
            "owner@gmail.com", "đăng nhập thành công",
        ]))

    def test_only_accessible_text_and_hyperlink_not_form_field_values(self):
        secret = FakeElement("Edit", "not-a-real-user@gmail.com")
        email = FakeElement("Text", "owner@gmail.com")
        credits = FakeElement("Text", "996 tín dụng Google Flow")
        root = FakeElement("Window", children=[secret, email, credits])
        labels = flow_uia.visible_text_labels(root)
        self.assertEqual(flow_uia.extract_account(labels),
                         ("owner@gmail.com", 996))
        self.assertEqual(secret.reads, 0)

    def test_waits_for_two_stable_readings_from_only_owned_chrome(self):
        stranger = FakeElement("Window", children=[
            FakeElement("Text", "wrong@gmail.com"),
            FakeElement("Text", "900 tín dụng Google Flow"),
        ], pid=222)
        owned = FakeElement("Window", children=[
            FakeElement("Text", "owner@gmail.com"),
            FakeElement("Text", "996 tín dụng Google Flow"),
        ], pid=111)
        chrome = mock.Mock(pid=111)
        chrome.poll.return_value = None
        ticks = iter([0, 0, 1, 2, 3])
        result = flow_uia.wait_for_visible_account(
            chrome, timeout_seconds=10,
            desktop_factory=lambda: FakeDesktop([stranger, owned]),
            sleep=lambda _: None, clock=lambda: next(ticks))
        self.assertIsNotNone(result)
        self.assertEqual(result[:2], ("owner@gmail.com", 996))
        self.assertIs(result[2], owned)

    def test_closes_only_matching_chrome_window(self):
        foreign = FakeElement("Window", pid=333)
        owned = FakeElement("Window", pid=111)
        self.assertFalse(flow_uia.close_owned_window(foreign, 111))
        self.assertFalse(foreign.closed)
        self.assertTrue(flow_uia.close_owned_window(owned, 111))
        self.assertTrue(owned.closed)


if __name__ == "__main__":
    unittest.main()
