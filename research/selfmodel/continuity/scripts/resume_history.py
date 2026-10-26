#!/usr/bin/env python3
"""Resume ONE C++ neural-triad lineage from the last VALID binary checkpoint.

This never silently restarts from seed. Every original receipt/snapshot is
validated; surplus observer rows written after the last checkpoint are removed
in a NEW output copy before recomputing those decisions. The old archive remains
byte-for-byte untouched. The original C++ model sources must match their hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
from typing import Any

from run_history import hash_file
from audit_observer import audit

MAX_TOURNAMENTS = 200_000_000
MAX_RECEIPT_SIZE = 1_000_000
AGENTS = 3
CONNECTIONS = 252


class BinaryReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def take(self, fmt: str):
        size = struct.calcsize('<' + fmt)
        if self.pos + size > len(self.data):
            raise ValueError('truncated checkpoint data')
        value = struct.unpack_from('<' + fmt, self.data, self.pos)[0]
        self.pos += size
        return value

    def chunk(self, count: int) -> bytes:
        if not 0 <= count <= len(self.data) - self.pos:
            raise ValueError('truncated checkpoint data')
        out = self.data[self.pos:self.pos + count]
        self.pos += count
        return out

    def label(self) -> str:
        count = self.take('I')
        if count > 256:
            raise ValueError('invalid label length')
        return self.chunk(count).decode('ascii')

    def series(self, fmt: str, count: int) -> list:
        return [self.take(fmt) for _ in range(count)]


def inspect_checkpoint(path: Path) -> dict[str, Any]:
    """Parse and independently validate the original Linux little-endian ABI.

    SHA256_CTX is opaque and remains as bytes; only the original C++ binary can
    restore it and continue the running event hash. Never synthesize RNG or hash.
    """
    p = Path(path)
    raw = p.read_bytes()
    if not 5000 <= len(raw) <= 65536 or len(raw) < 64:
        raise ValueError('checkpoint size invalid')
    payload, tail = raw[:-64], raw[-64:]
    try:
        expected = tail.decode('ascii')
    except UnicodeDecodeError as e:
        raise ValueError('invalid ASCII checkpoint digest') from e
    if any(c not in '0123456789abcdef' for c in expected) or hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError('checkpoint checksum mismatch')
    r = BinaryReader(payload)
    if r.label() != 'ARE-SM-CONTINUITY-1':
        raise ValueError('checkpoint schema mismatch')
    openssl_version = r.take('Q')
    sha_ctx_bytes = r.take('I')
    double_bytes = r.take('I')
    if sha_ctx_bytes < 64 or sha_ctx_bytes > 256 or double_bytes != 8:
        raise ValueError('checkpoint ABI incompatible with parser')
    seed = r.take('Q')
    arm = r.label()
    max_rounds, damage_interval = r.take('i'), r.take('i')
    if arm not in {'adaptive_damage', 'adaptive_intact', 'adaptive_amnesia', 'frozen_damage'}:
        raise ValueError('invalid trial arm')
    if not 1 <= damage_interval <= MAX_TOURNAMENTS or not 1 <= max_rounds <= 120:
        raise ValueError('invalid bounds')
    episodes, rounds, total_actions, draws, cap_hits = r.series('Q', 5)
    wins = r.series('Q', AGENTS)
    effective_aids = r.series('Q', AGENTS)
    attacks_on_small = r.series('Q', AGENTS)
    self_attacks = r.series('Q', AGENTS)
    effective_aid_matrix = [r.series('Q', AGENTS) for _ in range(AGENTS)]
    attack_matrix = [r.series('Q', AGENTS) for _ in range(AGENTS)]
    if not 1 <= episodes <= MAX_TOURNAMENTS or sum(wins) + draws != episodes:
        raise ValueError('checkpoint episode counters inconsistent')
    agents = []
    for agent_id in range(AGENTS):
        identity = r.take('i')
        flags = r.series('B', 4)
        w1, w2 = r.series('d', 180), r.series('d', 72)
        b1, b2 = r.series('d', 12), r.series('d', 6)
        masks = r.series('B', CONNECTIONS)
        if identity != agent_id or any(flag not in (0, 1) for flag in flags) or any(f not in (0, 1) for f in masks):
            raise ValueError('invalid model identity, flags or lesion mask')
        if (flags[0], flags[1], flags[2], flags[3]) != (
            int(arm != 'frozen_damage'), int(arm != 'adaptive_amnesia'),
            int(arm in {'adaptive_damage', 'frozen_damage'}), 1,
        ):
            raise ValueError('checkpoint model configuration mismatch')
        if any(value != 0.0 for value, flag in zip(w1 + w2, masks) if flag == 0):
            raise ValueError('disabled weight is nonzero')
        if any(not -1e20 < v < 1e20 for v in w1 + w2 + b1 + b2):
            raise ValueError('invalid neural parameter')
        helped_by, harmed_by, helped_other = [r.series('Q', AGENTS) for _ in range(3)]
        helped_recent, harmed_recent, helped_other_recent = [r.series('d', AGENTS) for _ in range(3)]
        a_wins, losses, a_draws, updates, lesions, lesion_rng = r.series('Q', 6)
        if (lesions != CONNECTIONS - sum(masks) or a_wins != wins[agent_id]
                or a_draws != draws or a_wins + losses + a_draws != episodes):
            raise ValueError('checkpoint personal counters inconsistent')
        agents.append({'name': ('Gross_A', 'Gross_B', 'Klein')[agent_id],
                       'wins': a_wins, 'losses': losses, 'draws': a_draws,
                       'updates': updates, 'damage_events': lesions,
                       'active_connections': sum(masks),
                       'helped_by': helped_by, 'harmed_by': harmed_by,
                       'helped_other': helped_other,
                       'helped_recent': helped_recent,
                       'harmed_recent': harmed_recent,
                       'helped_other_recent': helped_other_recent,
                       'lesion_rng': lesion_rng})
    rngs = r.series('Q', AGENTS)
    ctx = r.chunk(sha_ctx_bytes)
    if len(ctx) != sha_ctx_bytes or r.pos != len(payload):
        raise ValueError('checkpoint trailing/missing state')
    return {'schema': 'ARE-SM-CONTINUITY-1', 'episodes': episodes,
            'sha256': hashlib.sha256(raw).hexdigest(), 'seed': seed,
            'arm': arm, 'max_rounds': max_rounds,
            'damage_interval': damage_interval, 'openssl_version': openssl_version,
            'sha_ctx_size': sha_ctx_bytes, 'wins': wins, 'draws': draws,
            'rounds': rounds, 'total_actions': total_actions,
            'cap_hits': cap_hits, 'effective_aids': effective_aids,
            'attacks_on_small': attacks_on_small, 'self_attacks': self_attacks,
            'effective_aid_matrix': effective_aid_matrix,
            'attack_matrix': attack_matrix, 'agents': agents,
            'policy_rng_states': rngs}


def trim_to_checkpoint(observer_path: Path, episodes: int,
                       recorded_stages: list[dict]) -> tuple[bytes, int]:
    """Verify all legacy stage observer digests then discard only tail duplicates."""
    records = observer_path.read_bytes().splitlines(keepends=True)
    targets = {int(s['episode']): str(s['observer_sha256']) for s in recorded_stages}
    states = {stage: hashlib.sha256() for stage in targets}
    kept = []
    discarded = 0
    previous_ep = -1
    for line in records:
        row = json.loads(line)
        ep = row.get('episode')
        if type(ep) is not int or ep < previous_ep:
            raise ValueError('observer episode ordering invalid')
        previous_ep = ep
        for stage, digest in states.items():
            if ep < stage:
                digest.update(line)
        if ep < episodes:
            kept.append(line)
        else:
            discarded += 1
    for stage, digest in states.items():
        if digest.hexdigest() != targets[stage]:
            raise ValueError('previously certified observer stage digest mismatch')
    if discarded and not kept:
        raise ValueError('observer entirely outside checkpoint')
    if not discarded and records and previous_ep >= episodes:
        raise ValueError('observer cannot be trimmed')
    return b''.join(kept), discarded


def _verify_original(source: Path, model_root: Path,
                     *, expected_snapshot_sha: str, expected_base_commit: str) -> tuple[dict, dict, bytes, int]:
    src = Path(source)
    m = json.loads((src / 'manifest.json').read_text(encoding='utf-8'))
    if m.get('schema') != 'are-selfmodel-serial-history-1' or m.get('source_commit') != expected_base_commit:
        raise ValueError('original source commit or schema mismatch')
    if m.get('kind') != 'one_continuous_evolving_agent_triad_not_episode_clones':
        raise ValueError('original history is not a serial lineage')
    for rel, digest in m['sources_sha256'].items():
        source_file = model_root / rel
        if not source_file.is_file() or hash_file(source_file) != digest:
            raise ValueError('original model source sha256 mismatch: ' + rel)
    state = inspect_checkpoint(src / 'current_state.bin')
    if state['sha256'] != expected_snapshot_sha:
        raise ValueError('checkpoint digest differs from pinned original')
    if (state['seed'] != m['seed'] or state['arm'] != m['arm']
            or state['damage_interval'] != m['damage_interval']
            or state['max_rounds'] != m['max_rounds']):
        raise ValueError('checkpoint config differs from original trial')
    if m['completed'][-1]['episode'] >= state['episodes']:
        raise ValueError('no newer valid checkpoint to recover')
    for stage in m['completed']:
        if not 0 < stage['episode'] < state['episodes']:
            raise ValueError('invalid archive stage chronology')
        if hash_file(src / stage['checkpoint_archive']) != stage['checkpoint_sha256']:
            raise ValueError('archived stage checkpoint digest mismatch')
        receipt = json.loads((src / stage['receipt']).read_text())
        if (receipt['summary']['episodes_completed'] != stage['episode']
            or receipt['snapshot_sha256'] != stage['checkpoint_sha256']
            or receipt['observer_sha256'] != stage['observer_sha256']
            or receipt['summary']['rolling_event_sha256'] != stage['rolling_event_sha256']):
            raise ValueError('stage receipt/checkpoint identity mismatch')
    old_summary = json.loads((src / m['completed'][-1]['receipt']).read_text())['summary']
    for i, x in enumerate(state['agents']):
        older = old_summary['agents'][i]
        if x['wins'] < older['wins'] or x['losses'] < older['losses'] or x['damage_events'] < older['damage_events']:
            raise ValueError('recovered brain is not a valid later progression')
    trimmed, removed = trim_to_checkpoint(src / 'hidden_observer.jsonl', state['episodes'], m['completed'])
    if not trimmed:
        raise ValueError('empty observer log')
    return m, state, trimmed, removed


def _execute(binary: Path, directory: Path, manifest: dict, target: int,
             *, timeout_seconds: int, snapshot: Path, observer: Path) -> dict:
    result_path = directory / f'receipt_{target:09d}.json'
    if result_path.exists():
        raise FileExistsError('must not overwrite a previous checkpoint receipt')
    cmd = [str(binary.resolve()), '--arm', str(manifest['arm']), '--seed', str(manifest['seed']),
           '--target-episodes', str(target), '--damage-interval', str(manifest['damage_interval']),
           '--max-rounds', str(manifest['max_rounds']), '--checkpoint-every',
           str(manifest['checkpoint_every']), '--snapshot', str(snapshot),
           '--observer-log', str(observer), '--observe-every',
           str(manifest['sample_every']), '--receipt', str(result_path),
           '--resume', str(snapshot)]
    proc = subprocess.run(cmd, check=False, timeout=timeout_seconds, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f'C++ exact resume/checkpoint failed at {target}: rc={proc.returncode}; stderr={proc.stderr[-850:]}')
    r = json.loads(result_path.read_text(encoding='utf-8'))
    if (r['summary']['episodes_completed'] != target
            or r['snapshot_sha256'] != hash_file(snapshot)
            or r['observer_sha256'] != hash_file(observer)):
        raise ValueError('C++ checkpoint/observer stage verification failed')
    for a in r['summary']['agents']:
        if a['active_connections'] + a['damage_events'] != CONNECTIONS:
            raise ValueError('lesion invariant violated')
    return r


def recover_and_continue(*, binary: Path, source: Path, output: Path,
                         expected_snapshot_sha: str, expected_base_commit: str,
                         stages: list[int], timeout_seconds: int = 14400) -> dict:
    """Strictly recover a single lineage; no resets, forks, or overwrites."""
    binary, source, output = Path(binary), Path(source), Path(output)
    if not binary.is_file():
        raise ValueError('C++ experimental binary missing')
    if output.exists():
        raise FileExistsError('output directory already exists (refusing overwrite)')
    if not stages or len(stages) > 10 or any(type(x) is not int or x < 1 or x > MAX_TOURNAMENTS for x in stages):
        raise ValueError('invalid stage endpoints')
    if stages != sorted(set(stages)):
        raise ValueError('new targets must strictly increase')
    model_root = Path(__file__).resolve().parents[1]
    m, recovered, trimmed, removed = _verify_original(source, model_root,
                         expected_snapshot_sha=expected_snapshot_sha,
                         expected_base_commit=expected_base_commit)
    if stages[0] <= recovered['episodes']:
        raise ValueError('resume target must exceed recovered episode')
    shutil.copytree(source, output)
    checkpoint = output / 'current_state.bin'
    observer = output / 'hidden_observer.jsonl'
    observer.write_bytes(trimmed)
    # Recreate the receiver's verified 109M receipt without simulating an episode.
    m['checkpoint_every'] = m.get('checkpoint_every', 1_000_000)
    r = _execute(binary, output, m, recovered['episodes'],
                 timeout_seconds=60, snapshot=checkpoint, observer=observer)
    if r['snapshot_sha256'] != recovered['sha256']:
        raise ValueError('C++ recovered a different initial brain state')
    m['recovered_checkpoint_episode'] = recovered['episodes']
    m['recovered_checkpoint_sha256'] = recovered['sha256']
    m['recovered_discarded_observer_lines'] = removed
    m['recovery_source_commit'] = expected_base_commit
    m['recovery_status'] = 'c++_exact_zero_step_resume_verified'
    m['continuation_commit'] = os.getenv('GITHUB_SHA', 'local_uncommitted')
    m['continuation_binary_sha256'] = hash_file(binary)
    m['continuation_stages'] = stages
    m['legacy_artifact_untouched'] = True
    destination = output / 'snapshots'

    def record_stage(target, receipt, kind):
        frozen = destination / f'state_{target:09d}.bin'
        if frozen.exists():
            raise FileExistsError('target archive snapshot already exists')
        shutil.copyfile(checkpoint, frozen)
        if hash_file(frozen) != receipt['snapshot_sha256']:
            raise ValueError('snapshot freeze mismatch')
        s = receipt['summary']
        m['completed'].append({
            'episode': target, 'receipt': f'receipt_{target:09d}.json',
            'checkpoint_archive': str(frozen.relative_to(output)),
            'checkpoint_sha256': receipt['snapshot_sha256'],
            'observer_sha256': receipt['observer_sha256'],
            'rolling_event_sha256': s['rolling_event_sha256'],
            'stage_elapsed_seconds': s['elapsed_seconds'],
            'stage_provenance': kind,
            'agents': [{k: a[k] for k in ('name', 'wins', 'losses', 'damage_events',
                                          'active_connections', 'weights_sha256',
                                          'mask_sha256', 'helped_by', 'harmed_by')}
                       for a in s['agents']],
        })
        temp = output / 'manifest.partial'
        temp.write_text(json.dumps(m, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        os.replace(temp, output / 'manifest.json')
        print('RESUME_STAGE_OK', target, 'wins', s['wins'], 'active',
              [a['active_connections'] for a in s['agents']], flush=True)

    record_stage(recovered['episodes'], r, 'aborted_job_checkpoint_recovered')
    for target in stages:
        result = _execute(binary, output, m, target, timeout_seconds=timeout_seconds,
                          snapshot=checkpoint, observer=observer)
        record_stage(target, result, 'exact_serial_checkpoint_continuation')
    audit_report = audit(observer)
    if audit_report['sampled_agents'] != [0, 1, 2] or hash_file(observer) != m['completed'][-1]['observer_sha256']:
        raise ValueError('post-continuation observer audit mismatch')
    return m


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary', required=True, type=Path)
    p.add_argument('--original', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--expected-snapshot-sha', required=True)
    p.add_argument('--expected-base-commit', required=True)
    p.add_argument('--stages', default='150000000,200000000')
    p.add_argument('--inspect-only', action='store_true', help='audit original and verify original C++ zero-step load only')
    p.add_argument('--timeout-seconds', type=int, default=14400)
    a = p.parse_args()
    if not 60 <= a.timeout_seconds <= 20000:
        p.error('timeout_seconds must be in 60..20000')
    if a.inspect_only:
        import tempfile
        manifest, state, cleaned, removed = _verify_original(
            a.original, Path(__file__).resolve().parents[1],
            expected_snapshot_sha=a.expected_snapshot_sha,
            expected_base_commit=a.expected_base_commit,
        )
        with tempfile.TemporaryDirectory() as td:
            receipt = Path(td) / 'inspection_receipt.json'
            cmd = [str(a.binary.resolve()), '--arm', state['arm'], '--seed', str(state['seed']),
                   '--target-episodes', str(state['episodes']), '--damage-interval',
                   str(state['damage_interval']), '--max-rounds', str(state['max_rounds']),
                   '--checkpoint-every', '1000000', '--snapshot', str(a.original / 'current_state.bin'),
                   '--observer-log', str(a.original / 'hidden_observer.jsonl'), '--observe-every',
                   str(manifest['sample_every']), '--receipt', str(receipt),
                   '--resume', str(a.original / 'current_state.bin')]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
            if result.returncode:
                raise RuntimeError('native ABI or checkpoint load rejected: ' + result.stderr[-1200:])
            native = json.loads(receipt.read_text())
            if native['summary']['episodes_completed'] != state['episodes'] or native['snapshot_sha256'] != state['sha256']:
                raise ValueError('native readback disagrees with independent checkpoint parser')
        print('ORIGINAL_RESUME_PREFLIGHT_OK', json.dumps({
            'checkpoint_episode': state['episodes'], 'original_stages': len(manifest['completed']),
            'snapshot_sha256': state['sha256'], 'observer_tail_to_regenerate': removed,
            'old_source_sha256_verified': True, 'native_abi_verified': True,
        }, sort_keys=True), flush=True)
        return
    result = recover_and_continue(binary=a.binary, source=a.original, output=a.output,
                                  expected_snapshot_sha=a.expected_snapshot_sha,
                                  expected_base_commit=a.expected_base_commit,
                                  stages=[int(x) for x in a.stages.split(',')],
                                  timeout_seconds=a.timeout_seconds)
    print('COMPLETE', [x['episode'] for x in result['completed']], flush=True)


if __name__ == '__main__':
    main()
