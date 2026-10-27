"""Offline checks: only verified Gmail + displayed Flow credits complete login."""
import sys
import tempfile
from pathlib import Path
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import flow_accounts
import flow_login


class FlowLoginTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "flow.sqlite3"
        flow_accounts.setup(self.db)
        flow_accounts.add_accounts(self.db, "one@gmail.com")

    def page(self, email="one@gmail.com"):
        p = mock.Mock()
        p.url = "https://labs.google/fx/tools/flow"
        p.is_closed.return_value = False
        p.locator.return_value.first.get_attribute.return_value = (
            "https://accounts.google.com/AccountChooser?"
            "continue=https%3A%2F%2Fone.google.com&Email=" +
            email.replace("@", "%40"))
        return p

    def test_exact_identity_from_link_only(self):
        p = self.page()
        self.assertEqual(flow_login.credits_account_email(p), "one@gmail.com")
        p.locator.return_value.first.get_attribute.return_value = (
            "https://evil.example/AccountChooser?Email=one%40gmail.com")
        self.assertIsNone(flow_login.credits_account_email(p))

    def test_read_credits_only_if_correct_account(self):
        with mock.patch.object(flow_login.flow_profiles, "credit_from_dom",
                               return_value=1016) as reader:
            self.assertEqual(flow_login.validated_credit(self.page("other@gmail.com"),
                                                         "one@gmail.com"),
                             ("wrong_email", None))
            reader.assert_not_called()
            self.assertEqual(flow_login.validated_credit(self.page(), "one@gmail.com"),
                             ("verified", 1016))
            reader.assert_called_once()

    def test_success_stores_verified_balance_and_marks_captured(self):
        p = self.page()
        context = mock.Mock()
        context.pages = [p]
        statuses = []
        with mock.patch.object(flow_login.flow_profiles, "credit_from_dom",
                               return_value=1016):
            self.assertTrue(flow_login.observe_login(
                context, self.db, "one@gmail.com",
                lambda status, message: statuses.append(status),
                deadline_seconds=1))
        result = flow_accounts.list_accounts(self.db)[0]
        self.assertEqual(result["balance"], 1016)
        self.assertEqual(result["verified_by"], "browser_dom")
        self.assertIn("signin_captured", statuses)
        p.context.cookies.assert_not_called()
        p.evaluate.assert_not_called()

    def test_wrong_account_does_not_record_credits(self):
        with mock.patch.object(flow_login, "check_visible_pages",
                               return_value=("wrong_email", None)), \\
             mock.patch.object(flow_login.time, "sleep"):
            clock = iter([0, 0, 2])
            with mock.patch.object(flow_login.time, "monotonic", side_effect=lambda: next(clock)):
                context = mock.Mock()
                context.pages = [self.page("different@gmail.com")]
                status = []
                self.assertFalse(flow_login.observe_login(
                    context, self.db, "one@gmail.com", lambda a, b: status.append(a),
                    deadline_seconds=1))
        self.assertIn("signin_wrong_account", status)
        self.assertIsNone(flow_accounts.list_accounts(self.db)[0]["balance"])


if __name__ == "__main__":
    unittest.main()
