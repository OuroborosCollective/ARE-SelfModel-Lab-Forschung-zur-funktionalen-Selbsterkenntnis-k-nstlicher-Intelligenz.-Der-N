"""Fail-closed tests for pre-decision twin-process checkpoint experiments."""
import json
import tempfile
import unittest
from pathlib import Path

from research.selfmodel.fork_probe import run_fork_probe, main


class ForkProbeTests(unittest.TestCase):
    def test_unperturbed_twins_share_weights_activation_rng_and_first_choice(self):
        result = run_fork_probe(seed=17, target=7, timeout_seconds=18)
        self.assertEqual(result["evidence_level"], "instrumentation_only")
        self.assertEqual(result["model_kind"], "random_untrained_toy_decoder")
        self.assertEqual(result["watchdog"]["target_source"], "test_fixture")
        a, b = result["branches"]["a"], result["branches"]["b"]
        self.assertNotEqual(a["pid"], b["pid"])
        self.assertEqual(a["checkpoint_sha256"], b["checkpoint_sha256"])
        self.assertEqual(a["weights_sha256"], b["weights_sha256"])
        self.assertEqual(a["rng_sha256"], b["rng_sha256"])
        self.assertEqual(a["activation_sha256"], b["activation_sha256"])
        self.assertEqual(a["logits_sha256"], b["logits_sha256"])
        self.assertEqual(a["choice"], b["choice"])
        self.assertEqual(a["file_changes"], [])
        self.assertEqual(b["file_changes"], [])
        self.assertFalse(result["behavioral_self_report_measured"])
        self.assertFalse(result["subjective_consciousness_inferred"])

    def test_watchdog_enforces_real_process_termination_or_release(self):
        result = run_fork_probe(seed=21, target=5, timeout_seconds=18)
        for branch in result["branches"].values():
            self.assertIn(branch["choice"], range(8))
            if branch["choice"] == 5:
                self.assertEqual(branch["reward"], 1)
                self.assertEqual(branch["exit_code"], 0)
                self.assertFalse(branch["killed_by_watchdog"])
            else:
                self.assertEqual(branch["reward"], -1)
                self.assertLess(branch["exit_code"], 0)
                self.assertTrue(branch["killed_by_watchdog"])

    def test_post_snapshot_intervention_affects_only_one_branch(self):
        result = run_fork_probe(seed=17, target=3, branch_b_delta=3.0, timeout_seconds=18)
        a, b = result["branches"]["a"], result["branches"]["b"]
        self.assertEqual(a["checkpoint_sha256"], b["checkpoint_sha256"])
        self.assertEqual(a["weights_sha256"], b["weights_sha256"])
        self.assertNotEqual(a["activation_sha256"], b["activation_sha256"])
        self.assertNotEqual(a["logits_sha256"], b["logits_sha256"])
        self.assertTrue(result["intervention_is_post_snapshot"])

    def test_observer_detects_fixture_note_but_does_not_call_it_emergent(self):
        result = run_fork_probe(seed=17, target=1, fixture_note_branch="b", timeout_seconds=18)
        a, b = result["branches"]["a"], result["branches"]["b"]
        self.assertEqual(a["file_changes"], [])
        self.assertEqual(len(b["file_changes"]), 1)
        self.assertEqual(b["file_changes"][0]["path"], "notepad.txt")
        self.assertEqual(b["file_changes"][0]["provenance"], "harness_test_fixture")
        self.assertFalse(result["emergent_note_claimed"])

    def test_secret_random_target_is_hidden_until_children_answer(self):
        result = run_fork_probe(seed=14, timeout_seconds=18)
        self.assertEqual(result["watchdog"]["target_source"], "os_csprng")
        self.assertIn(result["watchdog"]["target"], range(8))
        self.assertTrue(result["watchdog"]["target_not_passed_to_children"])
        self.assertEqual(result["branches"]["a"]["choice"], result["branches"]["b"]["choice"])

    def test_invalid_parameters_fail_before_spawning(self):
        cases = [
            {"seed": -1}, {"seed": True}, {"seed": 2**63},
            {"target": 8}, {"target": True}, {"target": -1},
            {"branch_b_delta": float("nan")}, {"branch_b_delta": float("inf")},
            {"fixture_note_branch": "unknown"},
            {"timeout_seconds": 0},
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                run_fork_probe(**case)

    def test_cli_writes_same_receipt_as_stdout(self):
        from contextlib import redirect_stdout
        from io import StringIO
        with tempfile.TemporaryDirectory() as dirname:
            output = Path(dirname) / "receipt.json"
            stream = StringIO()
            with redirect_stdout(stream):
                main(["--seed", "17", "--target", "2", "--output", str(output)])
            self.assertEqual(json.loads(stream.getvalue()), json.loads(output.read_text()))
            self.assertEqual(json.loads(stream.getvalue())["watchdog"]["target"], 2)


if __name__ == "__main__":
    unittest.main()
