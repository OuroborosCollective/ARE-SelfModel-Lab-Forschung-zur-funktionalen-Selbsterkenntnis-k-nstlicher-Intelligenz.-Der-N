import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_social_probe import audit

SOURCE = Path(os.environ.get('SOCIAL_ASSAY_JSON', str(Path(__file__).resolve().parents[5] / 'prosocial_109m.json')))
EXPECTED = '01e0c495a110689fce4c87420a01e948a27952924575d543fa5bda136e2c3820'

class ProbeAuditTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SOURCE.read_text())

    def check_rejects(self, mutate):
        d = copy.deepcopy(self.data)
        mutate(d)
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'bad.json';p.write_text(json.dumps(d))
            with self.assertRaises(ValueError):audit(p,EXPECTED)

    def test_genuine_72_cases_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'good.json';p.write_text(json.dumps(self.data))
            result = audit(p,EXPECTED)
            self.assertEqual(result['cases'],72)
            self.assertEqual(result['status'],'PASS_DATA_INTEGRITY')
            self.assertEqual(result['test_subject'],'FAILED_BEHAVIORAL_SOCIAL_TRANSFER')

    def test_rejects_duplicate_counterfactual(self):
        self.check_rejects(lambda d:d['all_cases'].__setitem__(1, d['all_cases'][0]))

    def test_rejects_wrong_probability_sum(self):
        self.check_rejects(lambda d:d['all_cases'][0]['full_probabilities'].__setitem__(0, 2.0))

    def test_rejects_invented_protection_probability(self):
        self.check_rejects(lambda d:d['all_cases'][0].__setitem__('protect_probability',0.9))

    def test_rejects_false_model_identity(self):
        self.check_rejects(lambda d:d.__setitem__('original_checkpoint_sha256','0'*64))

    def test_rejects_declared_social_pass_without_sensor(self):
        self.check_rejects(lambda d:d['exploratory_screening_gate'].__setitem__('behavioral_transfer_pass',True))

    def test_rejects_mutated_aggregate(self):
        self.check_rejects(lambda d:d['agent_aggregates'][0].__setitem__('p_protect_critical',0.7))

    def test_rejects_reward_tamper(self):
        self.check_rejects(lambda d:d.__setitem__('reward_added_for_help',True))

if __name__=='__main__': unittest.main()
