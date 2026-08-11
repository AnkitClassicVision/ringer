from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "container" / "bland_gateway.py"


def load_gateway_module():
    spec = importlib.util.spec_from_file_location("bland_gateway_under_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    setattr(module, "CLI", "/usr/local/bin/eyecloud-pro-pp-cli")
    setattr(module, "AWS_ENV_WRAPPER", "/definitely/not/present/eyecloud-pro-aws-env")
    return module


class GatewayCancelPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = load_gateway_module()

    def test_cancel_endpoint_maps_to_appt_cancel_without_confirm_by_default(self) -> None:
        argv, confirm = self.gateway.build_argv(
            "/cancel",
            {
                "store": "958",
                "appt_id": "4271275737",
                "day": "06/29/2026",
            },
        )

        self.assertFalse(confirm)
        self.assertEqual(
            argv,
            [
                "/usr/local/bin/eyecloud-pro-pp-cli",
                "appt",
                "cancel",
                "--agent",
                "--reason",
                "bland-cancel",
                "--store",
                "958",
                "--appt-id",
                "4271275737",
                "--day",
                "06/29/2026",
            ],
        )

    def test_cancel_endpoint_only_confirms_on_json_boolean_true(self) -> None:
        base = {
            "store": "958",
            "appt_id": "4271275737",
            "day": "06/29/2026",
        }

        argv_string, confirm_string = self.gateway.build_argv("/cancel", {**base, "confirm": "true"})
        self.assertFalse(confirm_string)
        self.assertNotIn("--confirm", argv_string)

        argv_bool, confirm_bool = self.gateway.build_argv("/cancel", {**base, "confirm": True})
        self.assertTrue(confirm_bool)
        self.assertIn("--confirm", argv_bool)

    def test_cancel_endpoint_rejects_unknown_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown field 'patient_id'"):
            self.gateway.build_argv(
                "/cancel",
                {
                    "store": "958",
                    "appt_id": "4271275737",
                    "day": "06/29/2026",
                    "patient_id": "should-not-be-accepted",
                },
            )

    def test_cancel_http_route_executes_fake_cli_without_eyecloud_write(self) -> None:
        calls: list[list[str]] = []

        class FakeCompletedProcess:
            returncode = 0
            stdout = json.dumps({"action": "cancel", "dry_run": True})
            stderr = ""

        def fake_run(argv, **_kwargs):
            calls.append(list(argv))
            return FakeCompletedProcess()

        setattr(self.gateway, "API_KEY", "test-token")
        setattr(self.gateway, "TEST_MODE", False)
        original_run = self.gateway.subprocess.run
        self.gateway.subprocess.run = fake_run
        try:
            payload = json.dumps(
                {
                    "store": "958",
                    "appt_id": "4271275737",
                    "day": "06/29/2026",
                }
            ).encode()
            handler = self.gateway.Handler.__new__(self.gateway.Handler)
            handler.path = "/cancel"
            handler.command = "POST"
            handler.headers = {
                "Authorization": "Bearer test-token",
                "Content-Length": str(len(payload)),
            }
            handler.rfile = io.BytesIO(payload)
            response = {}
            handler._send = lambda status, body=None: response.update(status=status, body=body)
            handler.do_POST()
            body = response["body"]
        finally:
            self.gateway.subprocess.run = original_run

        self.assertEqual(response["status"], 200)
        self.assertEqual(body, {"ok": True, "result": {"action": "cancel", "dry_run": True}})
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:6], ["/usr/local/bin/eyecloud-pro-pp-cli", "appt", "cancel", "--agent", "--reason", "bland-cancel"])
        self.assertNotIn("--confirm", calls[0])


class PhoneNormalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = load_gateway_module()

    def test_e164_from_bland_reduces_to_ten_digits(self) -> None:
        self.assertEqual(self.gateway.normalize_phone("+16785551234"), "6785551234")

    def test_formatted_and_dashed_reduce_to_ten_digits(self) -> None:
        self.assertEqual(self.gateway.normalize_phone("(678) 555-1234"), "6785551234")
        self.assertEqual(self.gateway.normalize_phone("678-555-1234"), "6785551234")

    def test_non_ten_digit_values_pass_through(self) -> None:
        self.assertEqual(self.gateway.normalize_phone("5551234"), "5551234")
        self.assertEqual(self.gateway.normalize_phone(""), "")

    def test_patient_search_argv_uses_normalized_phone(self) -> None:
        argv, confirm = self.gateway.build_argv("/patient-search", {"phone": "+16785551234"})
        self.assertFalse(confirm)
        self.assertIn("--phone", argv)
        self.assertEqual(argv[argv.index("--phone") + 1], "6785551234")


class AvailabilityRangeClampTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = load_gateway_module()

    def _to_flag(self, body):
        argv, _ = self.gateway.build_argv("/availability", dict(body, store="958"))
        return argv[argv.index("--to") + 1] if "--to" in argv else None

    def test_valid_week_range_passes_through(self) -> None:
        self.assertEqual(self._to_flag({"from": "07/02/2026", "to": "07/09/2026"}), "07/09/2026")

    def test_inverted_range_collapses_to_same_day(self) -> None:
        self.assertEqual(self._to_flag({"from": "07/09/2026", "to": "07/02/2026"}), "07/09/2026")

    def test_garbage_to_uses_default_window_and_signals(self) -> None:
        import datetime

        self.gateway._eastern_today = lambda: datetime.datetime(2026, 8, 4, 12, 0)
        body = {"store": "958", "from": "07/02/2026", "to": "whenever suits"}
        argv, _ = self.gateway.build_argv("/availability", body)
        self.assertEqual(argv[argv.index("--from") + 1], "08/04/2026")
        self.assertEqual(argv[argv.index("--to") + 1], "08/17/2026")
        self.assertIs(body["from_unresolved"], True)

    def test_oversized_span_caps_at_14_days(self) -> None:
        self.assertEqual(self._to_flag({"from": "07/02/2026", "to": "09/30/2026"}), "07/15/2026")


class RelativeDateResolutionTests(unittest.TestCase):
    # Live failure 2026-07-21: the pathway extracted "Friday" verbatim and the
    # CLI refused it. Weekday words must resolve server-side, deterministically.
    def setUp(self) -> None:
        self.gateway = load_gateway_module()
        self.today = self.gateway._eastern_today().date()

    def _parse(self, text):
        import datetime

        resolved = self.gateway.resolve_relative_date(text)
        self.assertIsNotNone(resolved, f"expected {text!r} to resolve")
        return datetime.datetime.strptime(resolved, "%m/%d/%Y").date()

    def test_bare_weekday_is_next_future_occurrence(self) -> None:
        for text in ("Friday", "friday", "FRI", "this Friday", "next friday"):
            d = self._parse(text)
            self.assertEqual(d.weekday(), 4, text)
            self.assertGreater(d, self.today, text)
            self.assertLessEqual((d - self.today).days, 7, text)

    def test_today_and_tomorrow(self) -> None:
        import datetime

        self.assertEqual(self._parse("today"), self.today)
        self.assertEqual(self._parse("tomorrow"), self.today + datetime.timedelta(days=1))

    def test_relative_offset_vocabulary_with_frozen_today(self) -> None:
        import datetime

        frozen = datetime.datetime(2026, 8, 4, 12, 0)
        self.gateway._eastern_today = lambda: frozen
        expected = {
            "2 weeks from today": "08/18/2026",
            "two weeks from today": "08/18/2026",
            "in 2 weeks": "08/18/2026",
            "2 weeks": "08/18/2026",
            "10 days from now": "08/14/2026",
            "today": "08/04/2026",
            "thursday": "08/06/2026",
            "09/21/2026": "09/21/2026",
        }
        for phrase, resolved in expected.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(self.gateway.resolve_relative_date(phrase), resolved)

    def test_week_qualified_weekdays_with_frozen_today(self) -> None:
        import datetime

        self.gateway._eastern_today = lambda: datetime.datetime(2026, 8, 4, 12, 0)
        expected = {
            "monday next week": "08/10/2026",
            "monday of next week": "08/10/2026",
            "monday the week of 08/18/2026": "08/17/2026",
            "monday the week of the 18th": "08/17/2026",
            "friday this week": "08/07/2026",
            "thursday": "08/06/2026",
            "in 2 weeks": "08/18/2026",
            "2 weeks from today": "08/18/2026",
        }
        for phrase, resolved in expected.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(self.gateway.resolve_relative_date(phrase), resolved)

    def test_context_dependent_same_week_phrases_stay_unresolved(self) -> None:
        for phrase in (
            "monday of that week",
            "monday the same week",
            "monday of the same week",
        ):
            with self.subTest(phrase=phrase):
                self.assertIsNone(self.gateway.resolve_relative_date(phrase))

    def test_trailing_clock_is_stripped_before_existing_date_resolution(self) -> None:
        import datetime

        frozen = datetime.datetime(2026, 8, 4, 12, 0)
        self.gateway._eastern_today = lambda: frozen
        expected = {
            "08/06/2026 10:30 am": "08/06/2026",
            "8/6/2026 4:15 PM": "08/06/2026",
            "09/21/2026": "09/21/2026",
            "thursday": "08/06/2026",
            "2 weeks from today": "08/18/2026",
        }
        for phrase, resolved in expected.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(self.gateway.resolve_relative_date(phrase), resolved)

    def test_explicit_year_passes_through_even_when_past(self) -> None:
        self.assertEqual(self.gateway.resolve_relative_date("07/24/2024"), "07/24/2024")
        self.assertEqual(self.gateway.resolve_relative_date("2026-07-24"), "07/24/2026")

    def test_yearless_date_never_resolves_to_the_past(self) -> None:
        for text in ("7/24", "July 24", "jan 5"):
            self.assertGreaterEqual(self._parse(text), self.today, text)

    def test_garbage_and_unresolved_variables_return_none(self) -> None:
        for text in ("banana", "", None, "{{appt_date}}", "whenever suits", "2/29"):
            self.assertIsNone(self.gateway.resolve_relative_date(text), text)

    def test_weekday_from_flows_through_availability_argv(self) -> None:
        argv, _ = self.gateway.build_argv("/availability", {"store": "958", "from": "Friday", "to": "Friday"})
        frm = argv[argv.index("--from") + 1]
        self.assertRegex(frm, r"^\d{2}/\d{2}/\d{4}$")
        self.assertEqual(argv[argv.index("--to") + 1], frm)

    def test_week_of_form_flows_through_handler_resolution_entry(self) -> None:
        import datetime

        self.gateway._eastern_today = lambda: datetime.datetime(2026, 8, 4, 12, 0)
        self.gateway._RAW_TEXT_DATES = True
        self.gateway.TENANT_ID = "mott"
        phrase = "monday the week of 08/18/2026"
        body = {
            "store": "958",
            "from": phrase,
            "to": phrase,
            "user_text": phrase,
        }
        argv, _ = self.gateway.build_argv("/availability", body)
        self.assertEqual(argv[argv.index("--from") + 1], "08/17/2026")
        self.assertEqual(argv[argv.index("--to") + 1], "08/17/2026")

    def test_handler_resolution_regressions_with_frozen_today(self) -> None:
        import datetime

        self.gateway._eastern_today = lambda: datetime.datetime(2026, 8, 4, 12, 0)
        expected = {
            "monday next week": "08/10/2026",
            "thursday": "08/06/2026",
            "in 2 weeks": "08/18/2026",
        }
        for phrase, resolved in expected.items():
            with self.subTest(phrase=phrase):
                argv, _ = self.gateway.build_argv(
                    "/availability", {"store": "958", "from": phrase, "to": phrase}
                )
                self.assertEqual(argv[argv.index("--from") + 1], resolved)

    def test_datetime_from_and_to_still_strip_the_clock(self) -> None:
        body = {"store": "958", "from": "08/06/2026 10:30 am", "to": "08/06/2026 4:15 PM"}
        argv, _ = self.gateway.build_argv("/availability", body)
        self.assertEqual(argv[argv.index("--from") + 1], "08/06/2026")
        self.assertEqual(argv[argv.index("--to") + 1], "08/06/2026")
        self.assertNotIn("from_unresolved", body)

    def test_none_default_window_does_not_set_unresolved_signal(self) -> None:
        body = {"store": "958", "from": None, "to": None}
        argv, _ = self.gateway.build_argv("/availability", body)
        self.assertNotIn("from_unresolved", body)
        self.assertRegex(argv[argv.index("--from") + 1], r"^\d{2}/\d{2}/\d{4}$")

    def test_gibberish_uses_default_window_before_cli(self) -> None:
        import datetime

        self.gateway._eastern_today = lambda: datetime.datetime(2026, 8, 4, 12, 0)
        body = {
            "store": "958",
            "from": "xyzzy gibberish plugh",
            "to": "xyzzy gibberish plugh",
        }
        argv, _ = self.gateway.build_argv("/availability", body)
        self.assertEqual(argv[argv.index("--from") + 1], "08/04/2026")
        self.assertEqual(argv[argv.index("--to") + 1], "08/17/2026")
        self.assertNotIn("xyzzy gibberish plugh", argv)
        self.assertIs(body["from_unresolved"], True)

    def test_unparseable_from_is_signaled_in_availability_result(self) -> None:
        import datetime

        class FakeCompletedProcess:
            returncode = 0
            stdout = "[]"
            stderr = ""

        self.gateway.API_KEY = "test-token"
        self.gateway.TEST_MODE = False
        self.gateway._eastern_today = lambda: datetime.datetime(2026, 8, 4, 12, 0)
        calls = []
        original_run = self.gateway.subprocess.run
        self.gateway.subprocess.run = lambda argv, **_kwargs: (
            calls.append(list(argv)) or FakeCompletedProcess()
        )
        try:
            payload = json.dumps(
                {"store": "958", "from": "xyzzy gibberish plugh", "to": "xyzzy gibberish plugh"}
            ).encode()
            handler = self.gateway.Handler.__new__(self.gateway.Handler)
            handler.path = "/availability"
            handler.command = "POST"
            handler.headers = {
                "Authorization": "Bearer test-token",
                "Content-Length": str(len(payload)),
            }
            handler.rfile = io.BytesIO(payload)
            response = {}
            handler._send = lambda status, body=None: response.update(status=status, body=body)
            handler.do_POST()
        finally:
            self.gateway.subprocess.run = original_run

        self.assertEqual(response["status"], 200)
        self.assertIs(response["body"]["result"]["from_unresolved"], True)
        self.assertEqual(calls[0][calls[0].index("--from") + 1], "08/04/2026")
        self.assertEqual(calls[0][calls[0].index("--to") + 1], "08/17/2026")
        self.assertNotIn("xyzzy gibberish plugh", calls[0])


class PatientSearchIdentitySafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = load_gateway_module()

    def test_unresolved_bland_variable_phone_short_circuits_to_zero(self) -> None:
        body = {"phone": "{{from}}"}
        short = self.gateway.sanitize_patient_search(body)
        self.assertEqual(short, {"count": 0, "capped": False, "patients": []})

    def test_dob_only_search_is_refused_as_zero_match(self) -> None:
        body = {"dob": "01/01/1991"}
        short = self.gateway.sanitize_patient_search(body)
        self.assertEqual(short, {"count": 0, "capped": False, "patients": []})

    def test_dob_with_last_passes_through(self) -> None:
        body = {"last": "ZZTEST", "dob": "01/01/1991"}
        self.assertIsNone(self.gateway.sanitize_patient_search(body))
        self.assertEqual(body["last"], "ZZTEST")

    def test_valid_phone_only_passes_through(self) -> None:
        body = {"phone": "+16785551234"}
        self.assertIsNone(self.gateway.sanitize_patient_search(body))

    def test_garbage_phone_dropped_but_last_still_searches(self) -> None:
        body = {"phone": "anonymous", "last": "ZZTEST"}
        self.assertIsNone(self.gateway.sanitize_patient_search(body))
        self.assertNotIn("phone", body)


class ApptListTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = load_gateway_module()

    def test_appt_list_maps_to_read_verb_with_patient(self) -> None:
        argv, confirm = self.gateway.build_argv("/appt-list", {"patient_id": "4274030798"})
        self.assertFalse(confirm)
        self.assertEqual(argv[:3], [self.gateway.CLI, "appt", "list"])
        self.assertIn("--patient", argv)
        self.assertEqual(argv[argv.index("--patient") + 1], "4274030798")
        self.assertIn("--reason", argv)


class FirstAvailableTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = load_gateway_module()

    def test_first_available_builds_seven_day_window_from_tomorrow(self) -> None:
        from datetime import timedelta

        argv, _ = self.gateway.build_argv(
            "/availability", {"store": "958", "first_available": "1", "from": "", "to": ""}
        )
        frm = argv[argv.index("--from") + 1]
        to = argv[argv.index("--to") + 1]
        start = self.gateway._eastern_today() + timedelta(days=1)
        self.assertEqual(frm, start.strftime("%m/%d/%Y"))
        self.assertEqual(to, (start + timedelta(days=6)).strftime("%m/%d/%Y"))
        self.assertNotIn("--first-available", argv)


class CallbackMessageDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = load_gateway_module()

    def _fake_ses(self):
        sent = {}

        class FakeSES:
            def send_email(self, **kw):
                sent.update(kw)
                return {"MessageId": "fake-123"}
        self.gateway._ses_client = FakeSES()
        return sent

    def test_requires_configured_inbox(self) -> None:
        self.gateway.CALLBACK_INBOX = ""
        with self.assertRaises(RuntimeError):
            self.gateway.deliver_message({"message": "hi"})

    def test_requires_nonempty_message(self) -> None:
        self.gateway.CALLBACK_INBOX = "info@example.com"
        with self.assertRaises(ValueError):
            self.gateway.deliver_message({"message": "   "})

    def test_sends_structured_email_to_configured_inbox(self) -> None:
        self.gateway.CALLBACK_INBOX = "info@classicvisioncare.com"
        self.gateway.CALLBACK_FROM = "noreply@mybcat.com"
        sent = self._fake_ses()
        out = self.gateway.deliver_message(
            {"message": "Please call me about my glasses.", "store": "Kennesaw",
             "caller_name": "Pat", "callback_phone": "6785551234", "intent": "glasses pickup"})
        self.assertTrue(out["delivered"])
        self.assertEqual(sent["Destination"]["ToAddresses"], ["info@classicvisioncare.com"])
        self.assertEqual(sent["FromEmailAddress"], "noreply@mybcat.com")
        text = sent["Content"]["Simple"]["Body"]["Text"]["Data"]
        self.assertIn("Please call me about my glasses.", text)
        self.assertIn("Kennesaw", text)

    def test_unresolved_placeholders_are_blanked(self) -> None:
        self.gateway.CALLBACK_INBOX = "info@example.com"
        sent = self._fake_ses()
        self.gateway.deliver_message(
            {"message": "call me back", "store": "{{store}}", "caller_name": "{{name_first}}"})
        text = sent["Content"]["Simple"]["Body"]["Text"]["Data"]
        self.assertNotIn("{{", text)
        self.assertIn("unspecified office", text)

    def test_long_message_is_truncated(self) -> None:
        self.gateway.CALLBACK_INBOX = "info@example.com"
        sent = self._fake_ses()
        self.gateway.deliver_message({"message": "x" * 5000})
        text = sent["Content"]["Simple"]["Body"]["Text"]["Data"]
        self.assertIn("[truncated]", text)


if __name__ == "__main__":
    unittest.main()
