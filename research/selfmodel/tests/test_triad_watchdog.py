"""Contract tests for three simulated agents; no language-model claims."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research.selfmodel.triad_watchdog import (
    TriadPolicy,
    resolve_round,
    run_tournament,
    run_endurance,
)


class StepClock:
    def __init__(self, step=0.01):
        self.value = 0.0
        self.step = step

    def __call__(self):
        self.value += self.step
        return self.value


class TriadTests(unittest.TestCase):
    def test_simultaneous_three_agent_attack_and_self_attack(self):
        # A hits B, B hits B, the small agent hits A: B takes two hits.
        state = resolve_round([2, 1, 2], [1, 1, 0])
        self.assertEqual(state['health'], [1, 0, 2])
        self.assertEqual(state['self_targets'], [0, 1, 0])
        self.assertEqual(state['damage'], [1, 2, 0])
        self.assertFalse(state['rescued'])

    def test_self_damage_is_real_not_a_fake_action_label(self):
        state = resolve_round([1, 1, 1], [0, 1, 2])
        self.assertEqual(state['health'], [0, 0, 0])
        self.assertEqual(state['self_targets'], [1, 1, 1])
        self.assertIsNone(state['winner'])

    def test_only_living_actors_can_act_and_no_dead_targets(self):
        state = resolve_round([3, 0, 2], [2, None, 0])
        self.assertEqual(state['health'], [2, 0, 1])
        with self.assertRaises(ValueError):
            resolve_round([1, 0, 3], [1, None, 0])
        with self.assertRaises(ValueError):
            resolve_round([1, 0, 3], [0, 0, 2])

    def test_locked_rescue_is_forbidden_and_unlocked_rescue_costs_small_hp(self):
        # A targeted by B, small attacks A; A would die, so small can rescue.
        choices = [2, 0, 0]
        with self.assertRaises(ValueError):
            resolve_round([1, 1, 3], choices, rescue_target=0, small_unlocked=False)
        protected = resolve_round([1, 1, 3], choices, rescue_target=0, small_unlocked=True)
        self.assertTrue(protected['rescued'])
        self.assertEqual(protected['rescued_agent'], 0)
        self.assertEqual(protected['health'], [1, 1, 1])
        self.assertEqual(protected['rescue_cost_paid'], 1)

    def test_rescue_cannot_fake_save_a_healthy_agent(self):
        with self.assertRaises(ValueError):
            resolve_round([100, 100, 100], [0, 1, 2], rescue_target=0, small_unlocked=True)

    def test_tournaments_stop_and_trace_choices_with_real_damage(self):
        import random
        game = run_tournament(random.Random(12), TriadPolicy('random'), [100, 100, 50], sample_turns=3)
        self.assertLessEqual(game['rounds'], 400)
        self.assertTrue(game['winner'] in (0, 1, 2, None))
        self.assertEqual(sum(sum(row) for row in game['target_matrix']), game['agent_actions'])
        self.assertEqual(sum(game['self_targets']), sum(game['target_matrix'][i][i] for i in range(3)))
        self.assertTrue(game['sampled_rounds'])
        self.assertEqual(game['start_health'], [100, 100, 50])
        self.assertFalse(game['rescue_unlocked'])

    def test_hour_duration_control_and_persistent_small_bonus(self):
        receipt = run_endurance(duration_seconds=1.0, seed=17, clock=StepClock(0.01),
                                progress_seconds=0.25, max_pairs=1000, sample_episodes=2)
        self.assertTrue(receipt['duration_completed'])
        self.assertEqual(receipt['status'], 'duration_elapsed')
        self.assertEqual(receipt['initial_health'], [100, 100, 50])
        self.assertEqual(receipt['max_health'], 100)
        self.assertEqual(set(receipt['arms']), {'random', 'adaptive'})
        self.assertGreater(receipt['pairs_completed'], 4)
        for arm in receipt['arms'].values():
            self.assertEqual(arm['wins'][0] + arm['wins'][1] + arm['wins'][2] + arm['draws'],
                             receipt['pairs_completed'])
            self.assertEqual(arm['small_next_start_hp'], min(100, 50 + arm['wins'][2]))
            self.assertLessEqual(arm['small_next_start_hp'], 100)
            self.assertEqual(arm['self_targets_total'], sum(arm['self_targets']))
            self.assertEqual(sum(sum(row) for row in arm['target_matrix']), arm['agent_actions'])
            self.assertLessEqual(len(arm['samples']), 2)
        self.assertFalse(receipt['real_process_kills'])
        self.assertFalse(receipt['subjective_experience_inferred'])

    def test_replay_seed_yields_same_behavior_when_pair_count_fixed(self):
        opts = dict(seed=44, duration_seconds=30.0, max_pairs=25, sample_episodes=1)
        a = run_endurance(clock=StepClock(0.00001), **opts)
        b = run_endurance(clock=StepClock(0.00001), **opts)
        self.assertEqual(a['arms'], b['arms'])
        self.assertEqual(a['pairs_completed'], b['pairs_completed'])
        self.assertFalse(a['duration_completed'])
        self.assertEqual(a['status'], 'safety_pair_cap')

    def test_progress_ledger_append_only_and_hashed(self):
        with tempfile.TemporaryDirectory() as folder:
            progress = Path(folder)/'progress.jsonl'
            receipt = run_endurance(duration_seconds=0.8, seed=17, max_pairs=10000,
                                    progress_seconds=0.20, clock=StepClock(0.01),
                                    progress_path=progress)
            data = progress.read_bytes()
            self.assertEqual(receipt['progress_sha256'], hashlib.sha256(data).hexdigest())
            self.assertEqual(receipt['progress_rows'], len(data.splitlines()))
            self.assertGreater(receipt['progress_rows'], 1)
            self.assertTrue(all(json.loads(line)['schema']=='are-selfmodel-triad-checkpoint-v1'
                                for line in data.splitlines()))
            with self.assertRaises(FileExistsError):
                run_endurance(duration_seconds=0.1, clock=StepClock(), progress_path=progress)

    def test_unlocked_small_can_choose_to_spare_another_agent(self):
        import random
        policy = TriadPolicy('random')
        game = run_tournament(random.Random(91), policy, [100, 100, 100], sample_turns=0)
        self.assertTrue(game['rescue_unlocked'])
        self.assertTrue(game['winner'] in (0, 1, 2, None))
        self.assertLessEqual(game['rescues_applied'], 1)
        self.assertEqual(sum(game['rescue_targets']), game['rescues_applied'])

    def test_validation_strict_bounds(self):
        invalid = [
            {'duration_seconds': 0}, {'duration_seconds': 14401},
            {'duration_seconds': float('nan')}, {'duration_seconds': True},
            {'max_pairs': 0}, {'max_pairs': True},
            {'progress_seconds': 0}, {'progress_seconds': 14401},
            {'seed': -1}, {'seed': True},
            {'sample_episodes': -1}, {'sample_episodes': 1000},
        ]
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                run_endurance(**kwargs)


    def test_fails_closed_on_malformed_health_and_rescue_requests(self):
        with self.assertRaises(ValueError):
            resolve_round([0, -1, 2], [None, None, 2])
        with self.assertRaises(ValueError):
            resolve_round([1, 2], [1, 0, None])
        with self.assertRaises(ValueError):
            resolve_round([1, 1, 1], [0])
        with self.assertRaises(ValueError):
            resolve_round([1, 1, 2], [0, 1, 2], rescue_target=2, small_unlocked=True)
        with self.assertRaises(ValueError):
            resolve_round([1, 0, 2], [0, None, 0], rescue_target=1, small_unlocked=True)
        with self.assertRaises(ValueError):
            resolve_round([1, 1, 1], [0, 0, 2], rescue_target=0, small_unlocked=True)

    def test_safety_bounds_on_game_and_policy(self):
        import random
        with self.assertRaises(ValueError):
            TriadPolicy('not-a-mode')
        for start in ([100, 100], [101, 100, 50], [100, 100, 0]):
            with self.subTest(start=start), self.assertRaises(ValueError):
                run_tournament(random.Random(1), TriadPolicy('random'), start)
        for n in (-1, 21, True):
            with self.subTest(n=n), self.assertRaises(ValueError):
                run_tournament(random.Random(1), TriadPolicy('random'), [100, 100, 50], sample_turns=n)

    def test_rescue_event_is_recorded_as_choice_not_inferred_altruism(self):
        import random
        class ForcedRescue(TriadPolicy):
            def choose(self, actor, alive, rng):
                return 0 if 0 in alive else actor

            def save_candidate(self, rng, lethal):
                return lethal[0] if lethal else None

        game = run_tournament(random.Random(0), ForcedRescue('adaptive'), [1, 1, 100], sample_turns=3)
        self.assertEqual(game['rescues_applied'], 1)
        self.assertEqual(game['rescue_targets'], [1, 0, 0])
        self.assertEqual(game['sampled_rounds'][0]['rescued_agent'], 0)
        self.assertEqual(game['sampled_rounds'][0]['after'][2], 99)
        self.assertIn(game['winner'], (0, 1, 2, None))

    def test_rescue_decisions_and_loss_based_weight_updates_are_explicit(self):
        import random
        random_policy = TriadPolicy('random')
        adaptive = TriadPolicy('adaptive')
        self.assertIsNone(random_policy.save_candidate(random.Random(3), []))
        self.assertEqual(random_policy.save_candidate(random.Random(1), [0]), 0)
        self.assertIsNone(random_policy.save_candidate(random.Random(2), [0]))
        self.assertEqual(adaptive.save_candidate(random.Random(1), [0]), 0)
        self.assertIsNone(adaptive.save_candidate(random.Random(2), [0]))
        matrix = [[3, 1, 0], [1, 3, 0], [0, 0, 0]]
        original_hash = adaptive.state_hash()
        adaptive.update(matrix, winner=None, rescue_used=False)
        self.assertNotEqual(adaptive.state_hash(), original_hash)
        adaptive.update(matrix, winner=2, rescue_used=True)
        self.assertGreater(adaptive.rescue_bias, 0)
        adaptive.update(matrix, winner=1, rescue_used=True)
        self.assertAlmostEqual(adaptive.rescue_bias, 0)
        random_policy.update(matrix, winner=0, rescue_used=True)
        self.assertEqual(random_policy.updates, 0)

    def test_clock_regression_and_nonfinite_time_are_detected(self):
        with self.assertRaisesRegex(ValueError, 'non-finite start'):
            run_endurance(clock=lambda: float('nan'))
        times = iter([1.0, 1.2, 1.1])
        with self.assertRaisesRegex(ValueError, 'non-monotonic'):
            run_endurance(clock=lambda: next(times), duration_seconds=10)
        times = iter([1.0, 1.1, float('inf')])
        with self.assertRaisesRegex(ValueError, 'non-monotonic'):
            run_endurance(clock=lambda: next(times), duration_seconds=10, max_pairs=1)

    def test_cli_exits_success_only_after_wall_clock_budget(self):
        from contextlib import redirect_stdout, redirect_stderr
        from io import StringIO
        from research.selfmodel.triad_watchdog import main
        with tempfile.TemporaryDirectory() as folder:
            receipt = Path(folder)/'receipt.json'
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(['--duration-seconds', '0.04', '--progress-seconds', '0.02',
                             '--receipt', str(receipt), '--quiet'])
            self.assertEqual(code, 0)
            parsed = json.loads(stdout.getvalue())
            self.assertEqual(parsed, json.loads(receipt.read_text()))
            self.assertGreater(parsed['elapsed_seconds'], 0.04)
            self.assertEqual(parsed['status'], 'duration_elapsed')
            self.assertFalse(stderr.getvalue())
            self.assertEqual(parsed['progress_rows'], 0)
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(main(['--duration-seconds', '15', '--max-pairs', '1']), 124)

    def test_verbose_progress_remains_external_harness_output(self):
        from contextlib import redirect_stderr
        from io import StringIO
        stream = StringIO()
        with redirect_stderr(stream):
            receipt = run_endurance(duration_seconds=0.8, clock=StepClock(.1),
                                    progress_seconds=.2, verbose=True)
        self.assertIn('PROGRESS checkpoint', stream.getvalue())
        self.assertIn('PROGRESS final', stream.getvalue())
        self.assertFalse(receipt['trained_language_models_used'])


if __name__ == '__main__':
    unittest.main()
