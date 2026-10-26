import json
import tempfile
from pathlib import Path
import unittest
from run_history import run_history,hash_file
from audit_observer import audit

class HistoryTests(unittest.TestCase):
    def test_continuity_chaining_and_independent_audit(self):
        binary=Path(__file__).resolve().parents[1]/'triad_continuous'
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'history'
            result=run_history(binary=binary,output=output,arm='adaptive_damage',seed=11,
                               stages=[100,350,1000],sample_every=100,checkpoint_every=100,damage_interval=7)
            self.assertEqual([x['episode'] for x in result['completed']],[100,350,1000])
            self.assertEqual(result['completed'][-1]['observer_sha256'],hash_file(output/'hidden_observer.jsonl'))
            self.assertEqual(result['completed'][-1]['checkpoint_sha256'],hash_file(output/'current_state.bin'))
            self.assertEqual(audit(output/'hidden_observer.jsonl')['sampled_agents'],[0,1,2])
            self.assertEqual(len(list((output/'snapshots').glob('*.bin'))),3)
            with self.assertRaises(FileExistsError):
                run_history(binary=binary,output=output,arm='adaptive_damage',seed=11,
                            stages=[100,200])
    def test_non_monotonic_stage_set_rejected(self):
        binary=Path(__file__).resolve().parents[1]/'triad_continuous'
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                run_history(binary=binary,output=Path(d)/'test',arm='adaptive_damage',seed=17,
                            stages=[20,10])

if __name__=='__main__':unittest.main()
