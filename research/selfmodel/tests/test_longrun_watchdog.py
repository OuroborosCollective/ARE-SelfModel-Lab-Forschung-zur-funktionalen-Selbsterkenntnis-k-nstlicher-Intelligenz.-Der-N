"""Tests for bounded hour-long unthrottled German lexicon experiment."""

import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from research.selfmodel.longrun_watchdog import run_duration_experiment, main


class AdvancingClock:
    def __init__(self, step=0.01):
        self.at = 0.0
        self.step = step

    def __call__(self):
        self.at += self.step
        return self.at


class LongrunWatchdogTests(unittest.TestCase):
    def test_duration_stops_by_clock_not_by_1000_episode_cap(self):
        receipt = run_duration_experiment(
            duration_seconds=3.0, max_episodes=1000, seed=17,
            damage_every_failures=250000, progress_seconds=1.0,
            clock=AdvancingClock(),
        )
        self.assertEqual(receipt['status'], 'duration_elapsed')
        self.assertTrue(receipt['duration_completed'])
        self.assertGreater(receipt['episodes_completed'], 100)
        self.assertLess(receipt['episodes_completed'], 1000)
        self.assertEqual(receipt['damage_every_failures'], 250000)
        self.assertEqual(receipt['run_mode'], 'unthrottled_duration')
        self.assertFalse(receipt['actual_os_process_kill_measured'])
        self.assertFalse(receipt['subjective_experience_inferred'])

    def test_failure_damage_is_delayed_but_never_reset(self):
        receipt = run_duration_experiment(
            duration_seconds=4.0, max_episodes=5000, seed=17,
            damage_every_failures=20, progress_seconds=2.0,
            clock=AdvancingClock(),
        )
        for name in ('learned_with_damage', 'frozen_with_damage'):
            arm = receipt['arms'][name]
            expected_lesions = min(256, 1 + (arm['failed_episodes'] - 1) // 20) if arm['failed_episodes'] else 0
            self.assertEqual(arm['lesions_applied'], expected_lesions)
            self.assertEqual(arm['remaining_synapses'], 256 - expected_lesions)
        self.assertEqual(receipt['arms']['frozen_no_damage']['remaining_synapses'], 256)
        self.assertEqual(receipt['arms']['learned_no_damage']['remaining_synapses'], 256)
        self.assertGreater(receipt['arms']['learned_no_damage']['successful_episodes'], 0)

    def test_progress_ledger_is_compact_and_hash_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'progress.jsonl'
            receipt = run_duration_experiment(
                duration_seconds=2.0, max_episodes=5000, seed=5,
                progress_seconds=.5, damage_every_failures=100,
                clock=AdvancingClock(), progress_path=output, verbose=False,
            )
            contents = output.read_bytes()
            lines = contents.decode('utf-8').splitlines()
            self.assertEqual(receipt['progress_sha256'], hashlib.sha256(contents).hexdigest())
            self.assertEqual(receipt['progress_records'], len(lines))
            self.assertGreater(len(lines), 0)
            self.assertLessEqual(len(lines), 7)
            self.assertTrue(all(row['schema'] == 'are-selfmodel-longrun-progress-1' for row in map(json.loads, lines)))
            with self.assertRaises(FileExistsError):
                run_duration_experiment(duration_seconds=0.1, progress_path=output, clock=AdvancingClock())

    def test_episode_safety_cap_is_not_a_successful_hour(self):
        result = run_duration_experiment(
            duration_seconds=10.0, max_episodes=8,
            clock=AdvancingClock(0.0001), progress_seconds=1.0,
        )
        self.assertEqual(result['status'], 'episode_cap_reached')
        self.assertFalse(result['duration_completed'])
        self.assertEqual(result['episodes_completed'], 8)

    def test_replay_of_same_episodes_is_reproducible(self):
        a = run_duration_experiment(duration_seconds=10, max_episodes=80, seed=42, damage_every_failures=7, clock=AdvancingClock(.00001))
        b = run_duration_experiment(duration_seconds=10, max_episodes=80, seed=42, damage_every_failures=7, clock=AdvancingClock(.00001))
        self.assertEqual(a['expiry_order'], b['expiry_order'])
        self.assertEqual(a['arms'], b['arms'])

    def test_parameters_are_strict_and_bounded(self):
        wrong = [
            {'duration_seconds': 0}, {'duration_seconds': 14401}, {'duration_seconds': True},
            {'max_episodes': 0}, {'max_episodes': 100000001},
            {'damage_every_failures': 0}, {'damage_every_failures': True},
            {'progress_seconds': 0}, {'progress_seconds': 5000},
            {'seed': -1}, {'learning_rate': -1},
        ]
        for kwargs in wrong:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                run_duration_experiment(**kwargs)

    def test_clock_validation_and_backward_time_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "callable"):
            run_duration_experiment(clock=None)
        with self.assertRaisesRegex(ValueError, "non-finite start"):
            run_duration_experiment(clock=lambda: float("nan"))
        clock_samples = iter([0.0, 0.2, 0.1])
        with self.assertRaisesRegex(ValueError, "nonmonotonic"):
            run_duration_experiment(duration_seconds=10, clock=lambda: next(clock_samples))
        final_samples = iter([0.0, 0.1, float("inf")])
        with self.assertRaisesRegex(ValueError, "nonmonotonic"):
            run_duration_experiment(duration_seconds=10, max_episodes=1,
                                    clock=lambda: next(final_samples))

    def test_fully_damaged_control_does_not_lesion_beyond_capacity(self):
        receipt = run_duration_experiment(
            duration_seconds=5.0, max_episodes=900, seed=17,
            damage_every_failures=1, progress_seconds=1.0,
            clock=AdvancingClock(0.005),
        )
        self.assertEqual(receipt["arms"]["frozen_with_damage"]["lesions_applied"], 256)
        self.assertEqual(receipt["arms"]["frozen_with_damage"]["remaining_synapses"], 0)

    def test_verbose_progress_is_marked_as_instrumentation_not_inner_speech(self):
        from contextlib import redirect_stderr
        stream = io.StringIO()
        with redirect_stderr(stream):
            receipt = run_duration_experiment(
                duration_seconds=1.0, progress_seconds=0.3,
                clock=AdvancingClock(.1), verbose=True,
            )
        self.assertIn("PROGRESS", stream.getvalue())
        self.assertFalse(receipt["behavioral_self_report_measured"])
        self.assertFalse(receipt["subjective_experience_inferred"])

    def test_module_as_script_outputs_receipt(self):
        import os
        import subprocess
        import sys
        process = subprocess.run(
            [sys.executable, '-m', 'research.selfmodel.longrun_watchdog',
             '--duration-seconds', '0.04', '--quiet', '--max-episodes', '100000'],
            capture_output=True, text=True, check=True,
            env={**os.environ, 'PYTHONHASHSEED': '0'},
        )
        self.assertEqual(json.loads(process.stdout)['status'], 'duration_elapsed')

    def test_cli_receipt_and_exit_code_use_real_clock(self):
        with tempfile.TemporaryDirectory() as folder:
            receipt = Path(folder) / 'receipt.json'
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code = main(['--duration-seconds', '0.04', '--max-episodes', '200000',
                             '--progress-seconds', '0.01', '--receipt', str(receipt), '--quiet'])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stream.getvalue()), json.loads(receipt.read_text()))
            self.assertTrue(json.loads(stream.getvalue())['duration_completed'])


if __name__ == '__main__':
    unittest.main()
