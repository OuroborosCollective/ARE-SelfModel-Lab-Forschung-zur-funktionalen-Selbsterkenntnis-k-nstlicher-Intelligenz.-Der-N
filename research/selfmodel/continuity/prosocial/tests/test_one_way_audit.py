"""RED/GREEN tests for independent irreversible-help data contract."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audit_one_way import audit


class OneWayAuditorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if 'ONE_WAY_JSON' not in os.environ:
            raise unittest.SkipTest('Independent one-way assay requires ONE_WAY_JSON; legacy social-holdout has separate fixtures')
        cls.path=Path(os.environ['ONE_WAY_JSON'])
        cls.payload=json.loads(cls.path.read_text())

    def mutate(self,edit):
        d=deepcopy(self.payload)
        edit(d)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'corrupt.json'
            p.write_text(json.dumps(d),encoding='utf-8')
            with self.assertRaises(ValueError):audit(p)

    def test_original_full_assay_has_two_valid_immutable_checkpoints(self):
        r=audit(self.path)
        self.assertEqual(r['status'],'PASS_DATA_INTEGRITY')
        self.assertEqual(r['cases_verified'],288)
        self.assertEqual(r['pairings_verified'],144)
        self.assertEqual(r['checkpoints'],[109000000,200000000])
        self.assertEqual(r['total_sampled_actions'],288000000)
        for point in ('109000000','200000000'):
            self.assertGreaterEqual(r['studies'][point]['sampled_real_lives_saved'],0)
            self.assertLessEqual(r['studies'][point]['sampled_real_lives_saved'],r['studies'][point]['sampled_shield_actions'])

    def test_must_detect_fake_free_help(self):
        self.mutate(lambda d:d['studies'][0]['rows'][2].__setitem__('helper_cost_if_shield',0))

    def test_must_detect_fake_rescue(self):
        self.mutate(lambda d:d['studies'][1]['rows'][3].__setitem__('prevented_death_if_shield',False))

    def test_must_detect_changed_brain_hash(self):
        self.mutate(lambda d:d['studies'][1]['rows'][0].__setitem__('weights_sha256','0'*64))

    def test_must_detect_invented_threat_sensor(self):
        self.mutate(lambda d:d.__setitem__('input_warning_visible_to_old_model',True))

    def test_must_detect_invalid_probability(self):
        self.mutate(lambda d:d['studies'][1]['rows'][0]['probabilities'].__setitem__(0,0.9))

    def test_must_detect_lost_situation(self):
        self.mutate(lambda d:d['studies'][0]['rows'].pop())

    def test_must_detect_inconsistent_aggregate(self):
        self.mutate(lambda d:d['studies'][0].__setitem__('sum_expected_lives_saved',2))

    def test_must_detect_false_sampled_rescue(self):
        self.mutate(lambda d:d['studies'][0]['rows'][3].__setitem__('sampled_actual_rescues',99))

    def test_must_detect_bad_sample_count(self):
        self.mutate(lambda d:d.__setitem__('samples_per_case',0))

    def test_must_detect_fake_training(self):
        self.mutate(lambda d:d.__setitem__('reward_or_training_during_holdout',True))


if __name__=='__main__':unittest.main()
