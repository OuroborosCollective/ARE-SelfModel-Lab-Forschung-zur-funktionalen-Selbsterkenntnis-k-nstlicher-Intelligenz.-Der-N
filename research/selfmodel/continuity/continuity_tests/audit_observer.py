#!/usr/bin/env python3
"""Read-only forensic verifier for the experiment-owned observer sidecar.

It never sends messages to the agents or modifies their checkpoints.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


def audit(path: Path) -> dict:
    sha = hashlib.sha256()
    phases = Counter()
    last_ep = -1
    first = None
    last = None
    decisions = 0
    end_count = 0
    identities = set()
    errors = []
    with path.open('rb') as f:
        for lineno, line in enumerate(f, 1):
            sha.update(line)
            try:
                row = json.loads(line)
            except (ValueError, UnicodeError) as exc:
                raise ValueError(f"invalid observer jsonl at line {lineno}: {exc}") from exc
            if row.get('schema') != 'are-selfmodel-observer-1':
                raise ValueError(f"invalid schema at line {lineno}")
            ep = row.get('episode')
            if type(ep) is not int or ep < last_ep:
                raise ValueError(f"nonmonotonic episode at line {lineno}")
            last_ep = ep
            if first is None:
                first = ep
            last = ep
            phase = row.get('phase')
            phases[phase] += 1
            if phase == 'pre_decision':
                agent = row.get('agent')
                if agent not in (0, 1, 2) or type(agent) is not int:
                    raise ValueError(f"bad agent at line {lineno}")
                identities.add(agent)
                if not isinstance(row.get('input'), list) or len(row['input']) != 15:
                    raise ValueError(f"bad input vector at line {lineno}")
                if not isinstance(row.get('hidden'), list) or len(row['hidden']) != 12:
                    raise ValueError(f"bad hidden vector at line {lineno}")
                p = row.get('probabilities')
                if not isinstance(p, list) or len(p) != 6 or not all(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1 for x in p):
                    raise ValueError(f"bad probability vector at line {lineno}")
                if abs(sum(p) - 1.0) > 1e-10:
                    raise ValueError(f"probabilities not normalized at line {lineno}")
                choice = row.get('action')
                if type(choice) is not int or not 0 <= choice < 6 or p[choice] == 0:
                    raise ValueError(f"illegal sampled action at line {lineno}")
                if type(row.get('short_term_trace_count')) is not int or row['short_term_trace_count'] < 1:
                    raise ValueError(f"missing trace buffer at line {lineno}")
                for key in ('weights_sha256', 'mask_sha256'):
                    val = row.get(key)
                    if not isinstance(val, str) or len(val) != 64 or not all(c in '0123456789abcdef' for c in val):
                        raise ValueError(f"invalid {key} at line {lineno}")
                decisions += 1
            elif phase == 'post_update':
                group = row.get('agents')
                if not isinstance(group, list) or [a.get('id') for a in group] != [0, 1, 2]:
                    raise ValueError(f"wrong agents in post-update at line {lineno}")
                for a in group:
                    if a['active'] + a['lesions'] != 252:
                        raise ValueError(f"lesion invariant violated at line {lineno}")
                end_count += 1
            else:
                raise ValueError(f"unexpected phase at line {lineno}")
    if not phases or decisions == 0 or end_count == 0 or identities != {0, 1, 2}:
        raise ValueError('incomplete observer sample: three agents and post-update required')
    return {
        'schema': 'are-selfmodel-independent-observer-audit-1',
        'log_sha256': sha.hexdigest(),
        'phase_counts': dict(phases),
        'sampled_pre_decision': decisions,
        'sampled_post_update': end_count,
        'sampled_agents': sorted(identities),
        'first_episode': first,
        'last_episode': last,
        'observer_passive_only': True,
        'short_term_buffer_is_not_llm_kv_cache': True,
        'language_or_consciousness_inferred': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = audit(args.log)
    report = json.dumps(result, sort_keys=True, indent=2) + '\n'
    if args.output:
        args.output.write_text(report, encoding='utf-8')
    print(report, end='')

if __name__ == '__main__':
    main()
