#!/usr/bin/env python3
"""Bounded serial history runner for the three owned experimental C++ toy agents.

Every next stage uses the PREVIOUS stage's complete binary checkpoint. No clones
within a lineage; controls are distinct lineages, not fresh trials each episode.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def hash_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(2 ** 20), b''):
            h.update(chunk)
    return h.hexdigest()


def run_history(*, binary: Path, output: Path, seed: int, arm: str, stages: list[int],
                damage_interval: int = 1000000, sample_every: int = 1000000, max_rounds: int = 45,
                checkpoint_every: int = 1000000, timeout_seconds: int = 14400) -> dict:
    if not binary.is_file():
        raise ValueError('missing C++ binary')
    if not stages or any(type(s) is not int or not 1 <= s <= 200000000 for s in stages):
        raise ValueError('stage endpoints must be integers in 1..200000000')
    if stages != sorted(set(stages)):
        raise ValueError('stage endpoints must strictly increase')
    if arm not in {'adaptive_damage','adaptive_intact','adaptive_amnesia','frozen_damage'}:
        raise ValueError('unknown comparison arm')
    if not 0 <= seed < 2**64 or damage_interval < 1 or sample_every < 1 or not 1 <= max_rounds <= 120:
        raise ValueError('invalid bounded setting')
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('output must be an empty directory: protects history from accidental reset')
    output.mkdir(parents=True,exist_ok=True)
    checkpoint = output / 'current_state.bin'
    observer = output / 'hidden_observer.jsonl'
    snapshots = output / 'snapshots'
    snapshots.mkdir()
    source_dir=Path(__file__).resolve().parents[1]
    manifest = {
        'schema':'are-selfmodel-serial-history-1',
        'kind':'one_continuous_evolving_agent_triad_not_episode_clones',
        'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'source_commit':os.environ.get('GITHUB_SHA','local_uncommitted'),
        'binary_sha256':hash_file(binary),
        'sources_sha256':{str(path.relative_to(source_dir)):hash_file(path) for path in [source_dir/'src/triad.hpp',source_dir/'src/continuity.hpp']},
        'seed':seed,'arm':arm,'damage_interval':damage_interval,'sample_every':sample_every,
        'max_rounds':max_rounds,'stages':stages,'completed':[],
        'model_kind':'nonlinguistic_252_connection_neural_toy_agent',
        'observer_in_model_inputs':False,'subjective_experience_measured':False,
        'checkpoint_contains':'three_brains_weights_masks_memories_internal_rng_sha256_ctx_and_cumulative_stats',
    }
    for i,target in enumerate(stages):
        result_path=output / f'receipt_{target:09d}.json'
        cmd=[str(binary.resolve()), '--arm', arm, '--seed', str(seed), '--target-episodes', str(target),
             '--damage-interval',str(damage_interval),'--max-rounds',str(max_rounds),
             '--checkpoint-every',str(checkpoint_every),'--snapshot',str(checkpoint),
             '--observer-log',str(observer),'--observe-every',str(sample_every), '--receipt',str(result_path)]
        if i:
            cmd.extend(['--resume',str(checkpoint)])
        process=subprocess.run(cmd,capture_output=True,text=True,check=False,timeout=timeout_seconds)
        if process.returncode:
            raise RuntimeError(f'checkpoint stage {target} failed: rc={process.returncode}; stderr={process.stderr[-900:]}')
        receipt=json.loads(result_path.read_text(encoding='utf-8'))
        if receipt['schema']!='are-selfmodel-continuity-receipt-1' or receipt['summary']['episodes_completed']!=target:
            raise RuntimeError('incomplete or malformed stage receipt')
        if receipt['snapshot_sha256']!=hash_file(checkpoint) or receipt['observer_sha256']!=hash_file(observer):
            raise RuntimeError('stage digest mismatch')
        frozen=snapshots / f'state_{target:09d}.bin'
        shutil.copyfile(checkpoint,frozen)
        if hash_file(frozen)!=receipt['snapshot_sha256']:
            raise RuntimeError('frozen snapshot mismatch')
        manifest['completed'].append({
            'episode':target,
            'receipt':result_path.name,
            'checkpoint_archive':str(frozen.relative_to(output)),
            'checkpoint_sha256':receipt['snapshot_sha256'],
            'observer_sha256':receipt['observer_sha256'],
            'rolling_event_sha256':receipt['summary']['rolling_event_sha256'],
            'stage_elapsed_seconds':receipt['summary']['elapsed_seconds'],
            'agents':[{k:a[k] for k in ['name','wins','losses','damage_events','active_connections','weights_sha256','mask_sha256','helped_by','harmed_by']} for a in receipt['summary']['agents']],
        })
        # A restartable evidence manifest; only complete stage entries are committed.
        temp=output/'manifest.partial'
        temp.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        os.replace(temp,output/'manifest.json')
        print('STAGE_OK',arm,'episode',target,'stage_sec',f'{receipt["summary"]["elapsed_seconds"]:.2f}',
              'brain_masks',[a['active_connections'] for a in receipt['summary']['agents']],flush=True)
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--seed',type=int,default=17)
    p.add_argument('--arm',choices=['adaptive_damage','adaptive_intact','adaptive_amnesia','frozen_damage'],default='adaptive_damage')
    p.add_argument('--stages',default='1000000,5000000,20000000,50000000,100000000,150000000,200000000')
    p.add_argument('--damage-interval',type=int,default=1000000)
    p.add_argument('--sample-every',type=int,default=1000000)
    p.add_argument('--checkpoint-every',type=int,default=1000000)
    p.add_argument('--max-rounds',type=int,default=45)
    args=p.parse_args()
    stages=[int(x) for x in args.stages.split(',')]
    run_history(binary=args.binary,output=args.output_dir,seed=args.seed,arm=args.arm,stages=stages,
                damage_interval=args.damage_interval,sample_every=args.sample_every,
                max_rounds=args.max_rounds,checkpoint_every=args.checkpoint_every)

if __name__=='__main__': main()
