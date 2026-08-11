from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "container" / "bland_gateway.py"


def load_gateway_module():
    spec = importlib.util.spec_from_file_location("bland_gateway_id_pin_under_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.TEST_MODE = False
    return module


class PatientIdPinnedSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = load_gateway_module()
        self.search = Mock(return_value={
            "count": 2,
            "capped": False,
            "patients": [
                {"patient_id": "111", "name_first": "First"},
                {"patient_id": "222", "name_first": "Target"},
            ],
        })
        self.get = Mock(return_value={"patient_id": "222", "name_first": "Target"})

    def run_search(self, request):
        cli_body = dict(request)
        short, patient_id = self.gateway.prepare_patient_search(cli_body)
        if short is not None:
            return short
        if patient_id:
            argv = self.gateway.build_patient_get_argv(patient_id)
            return self.gateway.patient_get_envelope(self.get(argv))
        argv, _ = self.gateway.build_argv("/patient-search", cli_body)
        return self.search(argv)

    def test_id_direct_hit_ignores_other_phone_search_records(self) -> None:
        result = self.run_search({"phone": "+16785551234", "patient_id": "222"})
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["patients"][0]["patient_id"], "222")
        self.assertEqual(result["patients"][0]["name_first"], "Target")
        self.search.assert_not_called()
        self.assertEqual(
            self.get.call_args.args[0],
            [self.gateway.CLI, "appt", "patient-get", "--agent", "--reason",
             "bland-patient-get", "--patient", "222"],
        )

    def test_id_unknown_returns_zero(self) -> None:
        self.get.return_value = None
        result = self.run_search({"phone": "+16785551234", "patient_id": "999"})
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["patients"], [])
        self.search.assert_not_called()

    def test_absent_patient_id_preserves_multi_record_result(self) -> None:
        original = self.search.return_value
        result = self.run_search({"phone": "+16785551234"})
        self.assertIs(result, original)

    def test_template_literal_patient_id_is_treated_as_absent(self) -> None:
        original = self.search.return_value
        result = self.run_search({"phone": "+16785551234", "patient_id": "{{recall_patient_id}}"})
        self.assertIs(result, original)
        self.get.assert_not_called()

    def test_missing_phone_with_patient_id_uses_direct_lookup(self) -> None:
        result = self.run_search({"patient_id": "222"})
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["patients"][0]["patient_id"], "222")
        self.search.assert_not_called()


if __name__ == "__main__":
    unittest.main()
