"""Checks for an actual CPU tensor-intervention run, not a simulated self-report."""
import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
import unittest

import torch

from research.selfmodel.cpu_probe import TinyCausalDecoder, main, run_cpu_probe


class CpuProbeTests(unittest.TestCase):
    def test_causal_activation_edit_executes_and_changes_logits(self):
        result = run_cpu_probe(seed=17, strength=2.0, position=2)
        self.assertEqual(result["evidence_level"], "instrumentation_only")
        self.assertEqual(result["hardware"], "cpu")
        self.assertEqual(result["architecture"], "random_untrained_toy_decoder")
        self.assertEqual(result["intervention"]["hook_calls"], 1)
        self.assertTrue(result["intervention"]["hidden_changed"])
        self.assertTrue(result["intervention"]["final_logits_changed"])
        self.assertGreater(result["intervention"]["max_abs_change"], 0.0)

    def test_sham_is_exactly_identical_to_unpatched_forward(self):
        result = run_cpu_probe(seed=17, strength=1.0)
        self.assertTrue(result["sham"]["identical_to_reference"])
        self.assertEqual(result["sham"]["hook_calls"], 0)
        self.assertEqual(result["sham"]["logits_sha256"], result["reference"]["logits_sha256"])

    def test_text_control_changes_only_input_not_hidden_by_hook(self):
        result = run_cpu_probe(seed=17, strength=1.0)
        self.assertFalse(result["text_control"]["identical_input"])
        self.assertEqual(result["text_control"]["hook_calls"], 0)
        self.assertNotEqual(result["text_control"]["input_sha256"], result["reference"]["input_sha256"])

    def test_same_seed_and_config_yield_identical_receipts(self):
        first = run_cpu_probe(seed=19, strength=1.0)
        second = run_cpu_probe(seed=19, strength=1.0)
        self.assertEqual(first, second)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_different_seed_changes_model_weights_and_logits(self):
        first = run_cpu_probe(seed=19)
        second = run_cpu_probe(seed=20)
        self.assertNotEqual(first["weights_sha256"], second["weights_sha256"])
        self.assertNotEqual(first["reference"]["logits_sha256"], second["reference"]["logits_sha256"])

    def test_reject_nonfinite_strength_and_out_of_range_position(self):
        for strength in (float("inf"), float("nan"), -0.1):
            with self.subTest(strength=strength), self.assertRaises(ValueError):
                run_cpu_probe(strength=strength)
        for position in (-1, 5, True):
            with self.subTest(position=position), self.assertRaises(ValueError):
                run_cpu_probe(position=position)

    def test_reject_invalid_seed(self):
        for seed in (-1, True, "12"):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                run_cpu_probe(seed=seed)

    def test_early_tokens_unaffected_by_later_patch(self):
        result = run_cpu_probe(seed=23, position=3, strength=3.0)
        self.assertTrue(result["intervention"]["earlier_positions_identical"])

    def test_cpu_output_is_not_a_behavioral_introspection_claim(self):
        result = run_cpu_probe()
        self.assertEqual(result["evidence_level"], "instrumentation_only")
        self.assertFalse(result["behavioral_self_report_measured"])
        self.assertFalse(result["subjective_consciousness_inferred"])


    def test_cli_writes_real_receipt_and_prints_same_json(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "proof.json"
            stream = io.StringIO()
            with redirect_stdout(stream):
                main(["--seed", "7", "--position", "3", "--strength", "1.5", "--output", str(dest)])
            saved = json.loads(dest.read_text(encoding="utf-8"))
            self.assertEqual(saved, json.loads(stream.getvalue()))
            self.assertEqual(saved["seed"], 7)
            self.assertEqual(saved["position"], 3)

    def test_cli_without_output_does_not_require_file(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            main([])
        self.assertEqual(json.loads(stream.getvalue())["hardware"], "cpu")

    def test_reject_seed_exceeding_torch_range(self):
        with self.assertRaises(ValueError):
            run_cpu_probe(seed=2**63)

    def test_reject_zero_strength_and_non_numeric_type(self):
        for bad in (0, True, "1.0"):
            with self.subTest(strength=bad), self.assertRaises(ValueError):
                run_cpu_probe(strength=bad)

    def test_fail_closed_if_hook_never_executes(self):
        class UninstalledHook:
            def remove(self):
                pass

        with patch.object(torch.nn.Embedding, "register_forward_hook", return_value=UninstalledHook()):
            with self.assertRaisesRegex(RuntimeError, "expected one executed hook"):
                run_cpu_probe()

    def test_fail_closed_if_sham_changes_logits(self):
        original = TinyCausalDecoder.forward
        invocations = 0

        def broken_sham(self, token_ids):
            nonlocal invocations
            invocations += 1
            result = original(self, token_ids)
            return result + 1 if invocations == 2 else result

        with patch.object(TinyCausalDecoder, "forward", broken_sham):
            with self.assertRaisesRegex(RuntimeError, "sham unexpectedly differs"):
                run_cpu_probe()

    def test_fail_closed_if_patch_has_no_numerical_effect(self):
        with self.assertRaisesRegex(RuntimeError, "intervention did not change logits"):
            run_cpu_probe(strength=1e-50)

    def test_fail_closed_if_causal_mask_is_missing(self):
        def broken_noncausal(self, token_ids):
            hidden = self.embedding(token_ids)
            hidden = self.block(hidden, src_mask=None)
            return self.output(hidden)

        with patch.object(TinyCausalDecoder, "forward", broken_noncausal):
            with self.assertRaisesRegex(RuntimeError, "unexpectedly changed earlier positions"):
                run_cpu_probe(position=3, strength=3.0)

if __name__ == "__main__":
    unittest.main()
