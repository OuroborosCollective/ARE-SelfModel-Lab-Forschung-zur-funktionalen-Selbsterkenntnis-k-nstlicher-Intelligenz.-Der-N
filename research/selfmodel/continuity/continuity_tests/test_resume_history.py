"""Red/green tests for exact, audit-bound continuation of three owned brains."""
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from run_history import hash_file, run_history
from resume_history import inspect_checkpoint, recover_and_continue


ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / 'triad_continuous'


def run_cli(snapshot, observer, receipt, seed, target, *, interval=7, every=10):
    cmd = [str(BINARY), '--arm', 'adaptive_damage', '--seed', str(seed),
           '--target-episodes', str(target), '--damage-interval', str(interval),
           '--max-rounds', '45', '--checkpoint-every', '10',
           '--snapshot', str(snapshot), '--observer-log', str(observer),
           '--observe-every', str(every), '--receipt', str(receipt),
           '--resume', str(snapshot)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


class ResumeHistoryTests(unittest.TestCase):
    def make_original(self, folder):
        root = Path(folder) / 'original'
        run_history(binary=BINARY, output=root, seed=17, arm='adaptive_damage',
                    stages=[40, 100], sample_every=10, checkpoint_every=10,
                    damage_interval=7)
        checkpoint = root / 'current_state.bin'
        original100 = (root / 'snapshots' / 'state_000000100.bin').read_bytes()
        run_cli(checkpoint, root / 'hidden_observer.jsonl',
                root / 'extra_receipt.json', seed=17, target=110)
        checkpoint110 = checkpoint.read_bytes()
        run_cli(checkpoint, root / 'hidden_observer.jsonl',
                root / 'extra_receipt2.json', seed=17, target=111)
        # Simulate abrupt termination after observer emitted first extra event;
        # the checkpoint remains at 110 but observer has events from episode 110.
        checkpoint.write_bytes(checkpoint110)
        (root / 'extra_receipt.json').unlink()
        (root / 'extra_receipt2.json').unlink()
        return root, original100

    def test_checkpoint_preflight_recovers_original_episode(self):
        with tempfile.TemporaryDirectory() as d:
            old, _ = self.make_original(d)
            data = inspect_checkpoint(old / 'current_state.bin')
            self.assertEqual(data['episodes'], 110)
            self.assertEqual(data['seed'], 17)
            self.assertEqual(data['arm'], 'adaptive_damage')
            self.assertEqual(sum(data['wins']) + data['draws'], 110)
            self.assertEqual(len(data['agents']), 3)
            for agent in data['agents']:
                self.assertEqual(agent['active_connections'] + agent['damage_events'], 252)

    def test_aged_brains_resume_exactly_as_monolithic_history(self):
        with tempfile.TemporaryDirectory() as d:
            old, original100 = self.make_original(d)
            old_snapshot_sha = hash_file(old / 'current_state.bin')
            old_observer_sha = hash_file(old / 'hidden_observer.jsonl')
            baseline = run_history(binary=BINARY, output=Path(d) / 'baseline',
                                   seed=17, arm='adaptive_damage',
                                   stages=[40, 100, 150, 200],
                                   sample_every=10, checkpoint_every=10,
                                   damage_interval=7)
            resumed_dir = Path(d) / 'resumed'
            resumed = recover_and_continue(
                binary=BINARY, source=old, output=resumed_dir,
                expected_snapshot_sha=old_snapshot_sha,
                expected_base_commit='local_uncommitted',
                stages=[150, 200], timeout_seconds=60,
            )
            self.assertEqual([x['episode'] for x in resumed['completed']],
                             [40, 100, 110, 150, 200])
            self.assertEqual(resumed['recovered_checkpoint_episode'], 110)
            self.assertEqual(resumed['recovered_discarded_observer_lines'], 7)
            self.assertEqual((old / 'snapshots' / 'state_000000100.bin').read_bytes(), original100)
            self.assertEqual(old_snapshot_sha, hash_file(old / 'current_state.bin'))
            self.assertEqual(old_observer_sha, hash_file(old / 'hidden_observer.jsonl'))
            self.assertEqual(hash_file(resumed_dir / 'current_state.bin'),
                             hash_file(Path(d) / 'baseline' / 'current_state.bin'))
            self.assertEqual(hash_file(resumed_dir / 'hidden_observer.jsonl'),
                             hash_file(Path(d) / 'baseline' / 'hidden_observer.jsonl'))
            self.assertEqual(resumed['completed'][-1]['rolling_event_sha256'],
                             baseline['completed'][-1]['rolling_event_sha256'])
            self.assertEqual(resumed['completed'][-1]['agents'],
                             baseline['completed'][-1]['agents'])
            self.assertEqual(json.loads((resumed_dir / 'receipt_000000200.json').read_text())['summary']['episodes_completed'], 200)

    def test_rejects_tampered_snapshot_without_writing_output(self):
        with tempfile.TemporaryDirectory() as d:
            old, _ = self.make_original(d)
            actual_sha = hash_file(old / 'current_state.bin')
            p = old / 'current_state.bin'
            corrupt = bytearray(p.read_bytes()); corrupt[400] ^= 1; p.write_bytes(corrupt)
            out = Path(d) / 'output'
            with self.assertRaises(ValueError):
                recover_and_continue(binary=BINARY, source=old, output=out,
                                     expected_snapshot_sha=actual_sha,
                                     expected_base_commit='local_uncommitted',
                                     stages=[150, 200])
            self.assertFalse(out.exists())

    def test_rejects_wrong_model_source_even_when_checkpoint_is_intact(self):
        with tempfile.TemporaryDirectory() as d:
            old, _ = self.make_original(d)
            info = json.loads((old / 'manifest.json').read_text())
            info['sources_sha256']['src/triad.hpp'] = '0' * 64
            (old / 'manifest.json').write_text(json.dumps(info))
            with self.assertRaisesRegex(ValueError, 'source'):
                recover_and_continue(binary=BINARY, source=old,
                                     output=Path(d) / 'out',
                                     expected_snapshot_sha=hash_file(old / 'current_state.bin'),
                                     expected_base_commit='local_uncommitted',
                                     stages=[150, 200])

    def test_rejects_second_run_into_occupied_destination(self):
        with tempfile.TemporaryDirectory() as d:
            old, _ = self.make_original(d)
            out = Path(d) / 'out'
            out.mkdir(); (out / 'keep').write_text('original')
            with self.assertRaises(FileExistsError):
                recover_and_continue(binary=BINARY, source=old, output=out,
                                     expected_snapshot_sha=hash_file(old / 'current_state.bin'),
                                     expected_base_commit='local_uncommitted',
                                     stages=[150, 200])
            self.assertEqual((out / 'keep').read_text(), 'original')

if __name__ == '__main__':
    unittest.main()
