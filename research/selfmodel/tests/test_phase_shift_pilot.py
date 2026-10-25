"""Pre-registered phase reversal controls; no autonomous LLM claims."""

import json
import tempfile
import unittest
from pathlib import Path

from research.selfmodel.phase_shift_pilot import (
    PHASE_LABELS,
    run_phase_shift_pilot,
    main,
)


class PhaseShiftPilotTests(unittest.TestCase):
    def test_four_explicit_hidden_phases_and_independent_seeds(self):
        report = run_phase_shift_pilot(seed=31, independent_runs=3, episodes_per_phase=24)
        self.assertEqual(report["schema"], "are-selfmodel-phase-shift-pilot-1")
        self.assertEqual(report["independent_runs"], 3)
        self.assertEqual(report["episodes_total"], 3 * 4 * 24)
        self.assertEqual(tuple(report["phases"]), PHASE_LABELS)
        self.assertEqual(len(report["seeds"]), 3)
        self.assertEqual(len(set(report["seeds"])), 3)
        self.assertFalse(report["is_language_model"])
        self.assertFalse(report["subjective_experience_inferred"])
        self.assertFalse(report["phase_schedule_visible_to_policy"])
        for run in report["runs"]:
            schedule = run["expiry_schedules"]
            self.assertEqual(schedule["A"], schedule["A_return"])
            self.assertNotEqual(schedule["A"], schedule["B"])
            self.assertNotEqual(schedule["A"], schedule["C_novel"])
            self.assertNotEqual(schedule["B"], schedule["C_novel"])
            self.assertEqual([len(schedule[p]) for p in PHASE_LABELS], [8] * 4)
            for phase in run["measurements"]:
                self.assertIn(phase["phase"], PHASE_LABELS)
                for arm, data in phase["arms"].items():
                    self.assertEqual(data["successes"] + data["failures"], 24)
                    self.assertGreaterEqual(data["remaining_synapses"], 0)
                    self.assertLessEqual(data["remaining_synapses"], 256)

    def test_frozen_controls_never_train_and_damage_only_after_failure(self):
        report = run_phase_shift_pilot(seed=17, independent_runs=4, episodes_per_phase=40, damage_every_failures=3)
        for run in report["runs"]:
            last = None
            for phase in run["measurements"]:
                arms = phase["arms"]
                self.assertEqual(arms["frozen_no_damage"]["total_learning_updates"], 0)
                self.assertEqual(arms["frozen_with_damage"]["total_learning_updates"], 0)
                self.assertEqual(arms["frozen_no_damage"]["remaining_synapses"], 256)
                self.assertEqual(arms["learned_no_damage"]["remaining_synapses"], 256)
                self.assertLessEqual(arms["frozen_with_damage"]["remaining_synapses"], 256)
                self.assertLessEqual(arms["learned_with_damage"]["remaining_synapses"], 256)
                if last:
                    self.assertLessEqual(arms["frozen_with_damage"]["remaining_synapses"], last)
                last = arms["frozen_with_damage"]["remaining_synapses"]

    def test_metrics_identify_relearning_at_phase_boundaries(self):
        report = run_phase_shift_pilot(seed=17, independent_runs=8, episodes_per_phase=64)
        for run in report["runs"]:
            self.assertEqual(len(run["measurements"]), 4)
            for phase in run["measurements"]:
                for arm, metrics in phase["arms"].items():
                    if metrics["first_success_offset"] is not None:
                        self.assertTrue(0 <= metrics["first_success_offset"] < 64)
                    self.assertEqual(metrics["phase_episode_count"], 64)
                    self.assertTrue(0 <= metrics["successes"] <= 64)
            frozen = run["measurements"][-1]["arms"]["frozen_no_damage"]
            self.assertEqual(frozen["total_learning_updates"], 0)
        self.assertEqual(report["evidence_level"], "reproducible_toy_reversal_pilot")
        self.assertEqual(report["inference_unit"], "independent_random_seed_not_episode")

    def test_same_seed_and_parameters_reproduce_exact_report(self):
        a = run_phase_shift_pilot(seed=22, independent_runs=4, episodes_per_phase=12)
        b = run_phase_shift_pilot(seed=22, independent_runs=4, episodes_per_phase=12)
        self.assertEqual(a, b)

    def test_invalid_bounds_fail_closed(self):
        bad = [
            {"seed": True}, {"seed": -1}, {"seed": 2**64},
            {"independent_runs": 0}, {"independent_runs": 129}, {"independent_runs": True},
            {"episodes_per_phase": 0}, {"episodes_per_phase": 2001},
            {"damage_every_failures": 0}, {"damage_every_failures": False},
            {"learning_rate": -0.1}, {"learning_rate": float("inf")},
        ]
        for args in bad:
            with self.subTest(args=args), self.assertRaises(ValueError):
                run_phase_shift_pilot(**args)

    def test_output_file_is_created_exclusively(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "out.json"
            self.assertEqual(main(["--independent-runs", "2", "--episodes-per-phase", "8", "--output", str(out)]), 0)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["independent_runs"], 2)
            with self.assertRaises(FileExistsError):
                main(["--independent-runs", "2", "--episodes-per-phase", "8", "--output", str(out)])


if __name__ == "__main__":
    unittest.main()
