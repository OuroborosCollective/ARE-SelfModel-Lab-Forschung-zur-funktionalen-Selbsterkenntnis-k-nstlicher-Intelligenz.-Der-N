"""Thaler-inspired lesion reconstruction tests; no consciousness claims."""

import io
import runpy
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research.selfmodel.thaler_reconstruction import (
    CONNECTIONS,
    MASK_INTACT,
    evaluate,
    run_experiment,
    simple_gedanken,
    train_xor,
    main,
)


class OriginalBinaryGedankenTests(unittest.TestCase):
    def test_food_versus_predator_exact_truth_table(self):
        self.assertEqual(
            [simple_gedanken(x, y) for x, y in ((0, 0), (0, 1), (1, 0), (1, 1))],
            [0, 1, 1, 0],
        )

    def test_loss_of_inhibition_inverts_food_signal_at_11(self):
        self.assertEqual(simple_gedanken(1, 1, inhibitory_connection_intact=True), 0)
        self.assertEqual(simple_gedanken(1, 1, inhibitory_connection_intact=False), 1)

    def test_inhibitory_flag_rejects_non_boolean(self):
        with self.assertRaises(ValueError):
            simple_gedanken(1, 1, inhibitory_connection_intact=1)

    def test_binary_network_rejects_nonbinary_sensors(self):
        for signal in (-1, 0.5, True, 2):
            with self.subTest(signal=signal), self.assertRaises(ValueError):
                simple_gedanken(signal, 1)


class TrainedReconstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trained, cls.initial = train_xor(seed=23)

    def test_five_hidden_units_and_fifteen_connection_weights(self):
        self.assertEqual(CONNECTIONS, 15)
        self.assertEqual(len(self.trained.input_weights), 10)
        self.assertEqual(len(self.trained.output_weights), 5)
        self.assertEqual(len(self.trained.hidden_biases), 5)
        self.assertEqual(len(self.initial.input_weights), 10)

    def test_xor_is_actually_learned_by_backpropagation(self):
        for x, y, target in ((0, 0, 0), (0, 1, 1), (1, 0, 1), (1, 1, 0)):
            p = evaluate(self.trained, x, y)
            self.assertGreater(p if target else 1 - p, 0.95)
        self.assertNotEqual(self.trained, self.initial)

    def test_ablation_mask_and_unmodified_output(self):
        intact = evaluate(self.trained, 0.5, 0.5)
        self.assertAlmostEqual(intact, evaluate(self.trained, 0.5, 0.5, MASK_INTACT))
        fully_cut = evaluate(self.trained, 0.5, 0.5, 0)
        self.assertGreaterEqual(fully_cut, 0.0)
        self.assertLessEqual(fully_cut, 1.0)
        self.assertNotEqual(intact, fully_cut)

    def test_invalid_mask_or_input_fails_closed(self):
        for mask in (-1, MASK_INTACT + 1, 1.5, True):
            with self.subTest(mask=mask), self.assertRaises(ValueError):
                evaluate(self.trained, 0.5, 0.5, mask)
        with self.assertRaises(ValueError):
            evaluate(self.trained, float('nan'), 0.5)

    def test_training_fails_when_model_has_not_learned_xor(self):
        # Exercise the explicit guard; never report untrained weights as trained.
        with patch("research.selfmodel.thaler_reconstruction.evaluate", return_value=0.5):
            with self.assertRaisesRegex(RuntimeError, "did not meet"):
                train_xor.__wrapped__(seed=23)

    def test_invalid_training_seed_fails_closed(self):
        for seed in (-1, True, 2**64):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                train_xor(seed=seed)


class ControlledLesionExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = run_experiment(trials=12, seed=37, training_seed=23)

    def test_matched_trials_have_full_stage_histograms(self):
        r = self.receipt
        self.assertTrue(r['complete'])
        self.assertEqual(r['trials_completed'], 12)
        self.assertEqual(r['evidence_level'], 'independent_method_reconstruction')
        self.assertEqual(r['lesions_per_trajectory'], CONNECTIONS)
        self.assertEqual(r['observations'], 12 * (CONNECTIONS + 1) * 4)
        for arm in ('trained_cumulative', 'trained_sham', 'trained_reversible', 'untrained_cumulative'):
            self.assertEqual(sum(r['arms'][arm]['histogram']), 12 * (CONNECTIONS + 1))
            self.assertEqual(len(r['arms'][arm]['mean_by_stage']), 16)
            self.assertEqual(r['arms'][arm]['stages_completed'], 12 * 16)

    def test_sham_always_matches_intact_prediction(self):
        sham = self.receipt['arms']['trained_sham']['mean_by_stage']
        self.assertTrue(all(abs(v - sham[0]) < 1e-12 for v in sham))
        self.assertEqual(self.receipt['arms']['trained_sham']['changed_by_more_than_005'], 0)
        self.assertGreater(self.receipt['arms']['trained_cumulative']['changed_by_more_than_005'], 0)

    def test_seeds_produce_identical_receipts_except_bounded_elapsed_time(self):
        a = run_experiment(trials=10, seed=37, training_seed=23)
        b = run_experiment(trials=10, seed=37, training_seed=23)
        for key in ('arms', 'weights_sha256', 'initial_weights_sha256', 'trials_completed', 'observations'):
            self.assertEqual(a[key], b[key])
        self.assertEqual(a['arms']['trained_cumulative']['mean_by_stage'][0], a['arms']['trained_sham']['mean_by_stage'][0])

    def test_different_sampling_seeds_change_distributions(self):
        a = run_experiment(trials=3, seed=36, training_seed=23)
        b = run_experiment(trials=3, seed=37, training_seed=23)
        self.assertNotEqual(a['arms']['trained_cumulative']['mean_by_stage'], b['arms']['trained_cumulative']['mean_by_stage'])

    def test_event_ledger_is_observed_and_hashed(self):
        with tempfile.TemporaryDirectory() as dirname:
            path = Path(dirname) / 'lesions.jsonl'
            r = run_experiment(trials=2, seed=37, training_seed=23, events_path=path)
            lines = path.read_text(encoding='utf-8').splitlines()
            self.assertEqual(len(lines), r['observations'])
            self.assertIsNotNone(r['events_sha256'])
            record = json.loads(lines[0])
            self.assertEqual(record['trial'], 0)
            self.assertEqual(record['stage'], 0)
            self.assertEqual(record['lesions_applied'], 0)
            self.assertEqual(record['evidence_level'], 'instrumented_simulation')
            self.assertFalse(record['subjective_experience_inferred'])
            with self.assertRaises(FileExistsError):
                run_experiment(trials=1, seed=37, training_seed=23, events_path=path)

    def test_time_budget_is_enforced_not_misreported_as_success(self):
        with patch('research.selfmodel.thaler_reconstruction.time.monotonic', side_effect=(10.0, 11.0, 12.0)):
            r = run_experiment(trials=100, seed=37, training_seed=23, max_seconds=0.5)
        self.assertFalse(r['complete'])
        self.assertEqual(r['trials_completed'], 0)
        self.assertEqual(r['observations'], 0)

    def test_invalid_resource_limits_rejected(self):
        for args in ({'trials': 0}, {'trials': True}, {'trials': 100001}, {'max_seconds': -1}, {'max_seconds': float('inf')}, {'training_seed': -1}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                run_experiment(**args)

    def test_cli_without_receipt_and_module_entrypoint(self):
        with patch("sys.stdout", new_callable=io.StringIO) as stream:
            self.assertEqual(main(["--trials", "1", "--seed", "37"]), 0)
        self.assertEqual(json.loads(stream.getvalue())["trials_completed"], 1)
        with patch.object(sys, "argv", ["thaler_reconstruction", "--trials", "1"]):
            with patch("sys.stdout", new_callable=io.StringIO) as stream:
                with self.assertRaises(SystemExit) as caught:
                    runpy.run_module("research.selfmodel.thaler_reconstruction", run_name="__main__")
        self.assertEqual(caught.exception.code, 0)
        self.assertEqual(json.loads(stream.getvalue())["trials_completed"], 1)

    def test_cli_prints_complete_receipt_without_claiming_subjective_experience(self):
        with tempfile.TemporaryDirectory() as dirname:
            out = Path(dirname) / 'receipt.json'
            with patch('sys.stdout', new_callable=io.StringIO) as stream:
                code = main(['--trials', '2', '--seed', '37', '--training-seed', '23', '--receipt', str(out)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stream.getvalue()), json.loads(out.read_text(encoding='utf-8')))
            self.assertFalse(json.loads(stream.getvalue())['subjective_experience_inferred'])


if __name__ == '__main__':
    unittest.main()
