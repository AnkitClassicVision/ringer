"""Regression tests for the id-pinned /patient-search failure.

Drop into tests/ alongside test_id_pinned_search.py.

These are written to FAIL against the gateway as it stands and to PASS once the
two-part fix lands. That is the point: the existing suite passes today while
production returns an empty result for a patient that provably exists, because
it injects a successful CLI result and then asserts the very argv that omits the
live data-source selector.

Evidence this was written from, all measured against the live gateway:
  {"last": "MA"}                  -> 200 ok=true count=199
  {"patient_id": "675624166"}     -> 200 ok=true count=0
and one of those 199 records carries patient_id 675624166 exactly.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "container" / "bland_gateway.py"

EXISTING_PATIENT = {"patient_id": "675624166", "name_first": "Test", "name_last": "MA"}


def load_gateway_module():
    spec = importlib.util.spec_from_file_location("bland_gateway_regression", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.TEST_MODE = False
    return module


class IdPinnedArgvTests(unittest.TestCase):
    """Part one of the fix: the direct read must select the live data source."""

    def setUp(self) -> None:
        self.gateway = load_gateway_module()

    def test_patient_get_argv_selects_the_live_data_source(self) -> None:
        argv = self.gateway.build_patient_get_argv("675624166")
        self.assertIn(
            "--data-source", argv,
            "build_patient_get_argv omits --data-source, so the CLI falls back to its "
            "'auto' mode and can try a local encrypted database the container cannot "
            "open, returning nothing. The proven-good invocation passes --data-source live.",
        )
        self.assertEqual(
            "live", argv[argv.index("--data-source") + 1],
            "the direct patient read must select the live source explicitly",
        )

    def test_patient_get_argv_still_pins_the_requested_patient(self) -> None:
        argv = self.gateway.build_patient_get_argv("675624166")
        self.assertIn("--patient", argv)
        self.assertEqual("675624166", argv[argv.index("--patient") + 1])


class BehaviourFaithfulCliTests(unittest.TestCase):
    """A CLI fake that behaves like the real one: it only answers with --data-source live."""

    def setUp(self) -> None:
        self.gateway = load_gateway_module()
        self.calls: list[list[str]] = []

    def fake_cli(self, argv):
        self.calls.append(list(argv))
        if "--data-source" in argv and argv[argv.index("--data-source") + 1] == "live":
            return dict(EXISTING_PATIENT)
        # Without the live selector the real CLI produced nothing usable.
        return None

    def test_existing_patient_resolves_through_the_pinned_path(self) -> None:
        argv = self.gateway.build_patient_get_argv("675624166")
        envelope = self.gateway.patient_get_envelope(self.fake_cli(argv))
        self.assertEqual(
            1, envelope.get("count"),
            "a patient that exists must resolve through the id-pinned path. Today the "
            "argv omits --data-source live, the fake returns nothing, and the envelope "
            "reports count 0, which is indistinguishable from 'no such patient'.",
        )
        self.assertEqual("675624166", envelope["patients"][0]["patient_id"])


class FailureMustNotLookLikeEmptinessTests(unittest.TestCase):
    """Part two of the fix: a failed direct read must not be reported as a success."""

    def setUp(self) -> None:
        self.gateway = load_gateway_module()

    def test_failed_direct_read_is_distinguishable_from_no_match(self) -> None:
        failed = self.gateway.patient_get_envelope(None)
        genuinely_absent = self.gateway.patient_get_envelope({})

        self.assertNotEqual(
            (failed.get("count"), failed.get("lookup_failed")),
            (genuinely_absent.get("count"), genuinely_absent.get("lookup_failed")),
            "A CLI timeout, a nonzero exit and an unparseable response all collapse into "
            "the same HTTP 200 with count 0 that a genuine no-match produces. Callers "
            "cannot tell a broken lookup from an absent patient, so a recall pathway "
            "silently treats an outage as 'this person does not exist'. The envelope must "
            "carry a distinguishing signal, or the handler must return an upstream error "
            "for the failure case.",
        )


if __name__ == "__main__":
    unittest.main()
