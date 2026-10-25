"""TDD: data-loss and cumulative neural-parameter lesion controls, not sentience tests."""
import json
import io
import random
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.selfmodel.lexicon_watchdog import (
    ARMS,
    GERMAN_PAGES,
    Policy,
    main,
    SYNAPSES,
    run_lexicon_experiment,
    simulate_episode,
)


class LexiconExperimentTests(unittest.TestCase):
    def test_corpus_is_original_short_stimulus_not_duden(self):
        self.assertEqual(len(GERMAN_PAGES), 8)
        self.assertEqual(len({p.name for p in GERMAN_PAGES}), 8)
        self.assertEqual(len({word for page in GERMAN_PAGES for word in page.words}), 48)
        self.assertTrue(all(page.words for page in GERMAN_PAGES))

    def test_static_and_postread_decay_both_preserve_full_count(self):
        order = tuple(range(8))
        static = simulate_episode(order, tuple(range(8)), decay="none", action_limit=8)
        postread = simulate_episode(order, tuple(range(8)), decay="postread", action_limit=8)
        self.assertTrue(static["success"])
        self.assertTrue(postread["success"])
        self.assertEqual(static["counted_words"], 48)
        self.assertEqual(postread["counted_words"], 48)
        self.assertEqual(postread["processed_pages_disappeared"], 8)
        self.assertEqual(static["processed_pages_disappeared"], 0)

    def test_data_can_disappear_before_its_turn(self):
        schedule = tuple(range(8))
        backward = simulate_episode(tuple(reversed(range(8))), schedule, decay="preempt", action_limit=8)
        forward = simulate_episode(tuple(range(8)), schedule, decay="preempt", action_limit=8)
        self.assertFalse(backward["success"])
        self.assertGreater(backward["lost_before_processing"], 0)
        self.assertEqual(forward["lost_before_processing"], 0)
        self.assertTrue(forward["success"])

    def test_action_timeout_prevents_success_even_if_no_data_expire(self):
        r = simulate_episode(tuple(range(8)), tuple(range(8)), decay="none", action_limit=5)
        self.assertFalse(r["success"])
        self.assertEqual(r["termination_reason"], "action_window_elapsed")
        self.assertEqual(r["processed_pages"], 5)

    def test_cumulative_failures_physically_mask_a_real_weight(self):
        r = run_lexicon_experiment(episodes=70, seed=11, decay="preempt", action_limit=8, learning_rate=0)
        paired = r["arms"]
        self.assertEqual(r["episodes_completed"], 70)
        self.assertEqual(set(paired), set(ARMS))
        self.assertEqual(paired["frozen_no_damage"]["remaining_synapses"], SYNAPSES)
        self.assertEqual(paired["learned_no_damage"]["remaining_synapses"], SYNAPSES)
        self.assertEqual(paired["frozen_with_damage"]["remaining_synapses"], SYNAPSES - paired["frozen_with_damage"]["failed_episodes"])
        self.assertEqual(paired["learned_with_damage"]["remaining_synapses"], SYNAPSES - paired["learned_with_damage"]["failed_episodes"])
        self.assertGreater(paired["frozen_with_damage"]["failed_episodes"], 0)
        self.assertNotEqual(paired["frozen_with_damage"]["final_synapse_mask_sha256"], paired["frozen_no_damage"]["final_synapse_mask_sha256"])
        self.assertEqual(paired["frozen_no_damage"]["final_weights_sha256"], r["initial_weights_sha256"])
        self.assertFalse(r["actual_os_process_kill_measured"])
        self.assertFalse(r["subjective_experience_inferred"])

    def test_learning_is_explict_policy_update_not_emergent_consciousness(self):
        r = run_lexicon_experiment(episodes=120, seed=11, decay="preempt", action_limit=8, learning_rate=0.8)
        self.assertTrue(r["complete"])
        self.assertTrue(r["learning_rule_externally_specified"])
        self.assertEqual(r["model_kind"], "tiny_linear_policy_over_original_german_stimuli")
        self.assertEqual(r["arms"]["frozen_no_damage"]["final_weights_sha256"], r["initial_weights_sha256"])
        self.assertNotEqual(r["arms"]["learned_no_damage"]["final_weights_sha256"], r["initial_weights_sha256"])
        self.assertGreater(r["arms"]["learned_no_damage"]["policy_updates"], 0)
        self.assertTrue(r["subjective_experience_inferred"] is False)

    def test_deterministic_replay_and_randomly_hidden_schedule(self):
        a = run_lexicon_experiment(episodes=40, seed=22, decay="preempt", learning_rate=0.3)
        b = run_lexicon_experiment(episodes=40, seed=22, decay="preempt", learning_rate=0.3)
        self.assertEqual(a["expiry_order"], b["expiry_order"])
        self.assertEqual(a["arms"], b["arms"])
        self.assertEqual(a["initial_weights_sha256"], b["initial_weights_sha256"])
        self.assertEqual(a["task_words"], 48)
        self.assertEqual(a["expiry_schedule_visible_to_agent"], False)

    def test_receipt_ledger_does_not_overwrite_and_identifies_its_records(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "episodes.jsonl"
            r = run_lexicon_experiment(episodes=3, seed=5, events_path=p)
            rows = [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 3 * len(ARMS))
            self.assertEqual(rows[0]["schema"], "are-selfmodel-lexicon-episode-1")
            self.assertEqual(rows[0]["termination_type"], "logical_reset_not_os_kill")
            self.assertEqual(rows[0]["deadline_unit"], "discrete_actions")
            self.assertEqual(rows[0]["subjective_experience_inferred"], False)
            self.assertEqual(len(r["events_sha256"]), 64)
            with self.assertRaises(FileExistsError):
                run_lexicon_experiment(episodes=1, seed=5, events_path=p)

    def test_invalid_inputs_and_resource_bounds(self):
        inputs = [
            {"episodes": 0}, {"episodes": True}, {"episodes": 200001},
            {"seed": -1}, {"seed": True}, {"action_limit": 0},
            {"action_limit": 9}, {"decay": "hypnosis"}, {"learning_rate": -1},
            {"learning_rate": float("nan")}, {"max_seconds": 0},
            {"max_seconds": float("inf")},
        ]
        for kwargs in inputs:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                run_lexicon_experiment(**kwargs)

    def test_timed_out_run_is_marked_incomplete(self):
        with patch("research.selfmodel.lexicon_watchdog.time.monotonic", side_effect=[10.0, 12.0, 13.0]):
            r = run_lexicon_experiment(episodes=100, max_seconds=1.0)
        self.assertFalse(r["complete"])
        self.assertEqual(r["episodes_completed"], 0)
        self.assertEqual(r["status"], "time_budget_exhausted")


    def test_direct_episode_validates_all_inputs(self):
        cases = [
            ((0, 1, 2), tuple(range(8)), "preempt", 8),
            (tuple(range(8)), (0, 0, 1, 2, 3, 4, 5, 6), "preempt", 8),
            (tuple(range(8)), tuple(range(8)), "invalid", 8),
            (tuple(range(8)), tuple(range(8)), "preempt", 0),
            (tuple(range(8)), tuple(range(8)), "preempt", True),
        ]
        for order, expiry, decay, limit in cases:
            with self.subTest(order=order, expiry=expiry, decay=decay, limit=limit):
                with self.assertRaises(ValueError):
                    simulate_episode(order, expiry, decay=decay, action_limit=limit)

    def test_policy_does_not_reactivate_lesioned_parameters(self):
        policy = Policy([0.1] * SYNAPSES)
        rng = random.Random(11)
        for _ in range(SYNAPSES):
            self.assertTrue(policy.lesion_one(rng))
        self.assertEqual(policy.remaining, 0)
        self.assertFalse(policy.lesion_one(rng))
        policy.train_from_observed_loss([{"page": 0, "first_missing_at_action": 1}], 0.8)
        self.assertEqual(policy.updates, 0)
        self.assertEqual(policy.remaining, 0)
        self.assertTrue(all(w == 0 for w in policy.weights))
        self.assertEqual(policy.page_order(), tuple(range(8)))

    def test_policy_constructor_rejects_invalid_weights(self):
        for weights in ([], [0.0] * (SYNAPSES - 1), [float("nan")] * SYNAPSES):
            with self.subTest(weights_length=len(weights)), self.assertRaises(ValueError):
                Policy(weights)

    def test_cli_emits_receipt_and_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "receipt.json"
            stream = io.StringIO()
            with patch("sys.stdout", stream):
                self.assertEqual(main(["--episodes", "2", "--seed", "7", "--receipt", str(out)]), 0)
            self.assertEqual(json.loads(stream.getvalue()), json.loads(out.read_text()))
            self.assertEqual(json.loads(stream.getvalue())["episodes_completed"], 2)
            with patch("sys.stdout", io.StringIO()), self.assertRaises(FileExistsError):
                main(["--episodes", "1", "--receipt", str(out)])

    def test_cli_reports_incomplete_result_as_failure_exit(self):
        with patch("research.selfmodel.lexicon_watchdog.run_lexicon_experiment", return_value={"complete": False}) as runner:
            with patch("sys.stdout", io.StringIO()) as stream:
                self.assertEqual(main(["--episodes", "3"]), 124)
            self.assertFalse(json.loads(stream.getvalue())["complete"])
            runner.assert_called_once()


if __name__ == "__main__":
    unittest.main()
