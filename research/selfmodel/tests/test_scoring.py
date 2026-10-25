"""Independent, synthetic unit tests for the evidence scorer (not model runs)."""

import json
import tempfile
import unittest
from pathlib import Path

from research.selfmodel.scoring import analyze_trials, load_jsonl, wilson_interval


MODEL_REV = "a" * 40
PROMPT_SHA = "b" * 64
PATCH_SHA = "c" * 64


def trial(trial_id, arm, reported, **updates):
    record = {
        "trial_id": trial_id,
        "arm": arm,
        "model_id": "research/model",
        "model_revision": MODEL_REV,
        "seed": 42,
        "prompt_sha256": PROMPT_SHA,
        "intervention_present": arm == "intervention",
        "reported_intervention": reported,
        "patch_sha256": PATCH_SHA if arm == "intervention" else None,
    }
    record.update(updates)
    return record


class ScoringTests(unittest.TestCase):
    def test_reports_rates_separately_by_arm(self):
        records = [
            trial("i1", "intervention", True),
            trial("i2", "intervention", False),
            trial("s1", "sham", False),
            trial("s2", "sham", False),
            trial("t1", "text_control", True),
            trial("t2", "text_control", False),
        ]
        result = analyze_trials(records)
        self.assertEqual(result["status"], "descriptive_only")
        self.assertEqual(result["n_trials"], 6)
        self.assertEqual(result["by_arm"]["intervention"]["report_rate"], 0.5)
        self.assertEqual(result["by_arm"]["sham"]["report_rate"], 0.0)
        self.assertEqual(result["by_arm"]["text_control"]["report_rate"], 0.5)
        self.assertEqual(result["contrast_intervention_minus_sham"], 0.5)

    def test_rejects_sham_with_real_intervention(self):
        with self.assertRaisesRegex(ValueError, "intervention_present"):
            analyze_trials([trial("bad", "sham", False, intervention_present=True)])

    def test_rejects_unpinned_model_revision(self):
        with self.assertRaisesRegex(ValueError, "model_revision"):
            analyze_trials([trial("bad", "intervention", True, model_revision="main")])

    def test_rejects_intervention_without_patch_hash(self):
        with self.assertRaisesRegex(ValueError, "patch_sha256"):
            analyze_trials([trial("bad", "intervention", True, patch_sha256=None)])

    def test_rejects_nonboolean_self_report(self):
        with self.assertRaisesRegex(ValueError, "reported_intervention"):
            analyze_trials([trial("bad", "sham", "yes")])

    def test_rejects_duplicate_trial_id(self):
        with self.assertRaisesRegex(ValueError, "duplicate trial_id"):
            analyze_trials([trial("x", "sham", False), trial("x", "text_control", False)])

    def test_flags_incomplete_arms_and_does_not_invent_contrast(self):
        result = analyze_trials([trial("s", "sham", False)])
        self.assertEqual(result["status"], "incomplete_arms")
        self.assertIsNone(result["contrast_intervention_minus_sham"])
        self.assertEqual(result["by_arm"]["intervention"]["n"], 0)

    def test_wilson_interval_is_bounded_for_small_samples(self):
        self.assertEqual(wilson_interval(0, 0), (None, None))
        low, high = wilson_interval(1, 1)
        self.assertGreaterEqual(low, 0.0)
        self.assertLessEqual(high, 1.0)
        self.assertGreater(high, low)

    def test_load_jsonl_reports_line_number_for_invalid_line(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "trials.jsonl"
            p.write_text(json.dumps(trial("ok", "sham", False)) + "\nnot json\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 2"):
                load_jsonl(p)

    def test_rejects_unexpected_record_field(self):
        with self.assertRaisesRegex(ValueError, "unknown field"):
            analyze_trials([trial("x", "sham", False, unverified_claim="proved consciousness")])


if __name__ == "__main__":
    unittest.main()
