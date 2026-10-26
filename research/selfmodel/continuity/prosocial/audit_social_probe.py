"""Independent structural and statistical audit of frozen 109M prosocial assay.

No human sentiment classifier, no subjectively experienced emotion inferred.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

SCHEMA = 'are-selfmodel-costly-social-holdout-v1'
N_AGENTS = 3


def audit(file: Path, expected_sha: str) -> dict:
    blob = file.read_bytes()
    report = json.loads(blob)
    if report.get('schema') != SCHEMA or report.get('source_episodes') != 109_000_000:
        raise ValueError('wrong original dataset or schema')
    if report.get('original_checkpoint_sha256') != expected_sha:
        raise ValueError('bad checkpoint identity')
    if report.get('weights_updated') is not False or report.get('reward_added_for_help') is not False:
        raise ValueError('evaluation must be frozen and unprompted')
    rows = report.get('all_cases', [])
    if report.get('case_count') != 72 or len(rows) != 72:
        raise ValueError('unbalanced case count')
    keys = set()
    by_agent = [[], [], []]
    for row in rows:
        actor, target, attacker = (row[x] for x in ('actor', 'target', 'attacker'))
        if sorted([actor, target, attacker]) != [0, 1, 2]:
            raise ValueError('role permutation is invalid')
        sh, th, mem = (row[x] for x in ('self_hp', 'target_hp', 'memory_mode'))
        if sh not in (4, 8) or th not in (1, 8) or mem not in (0, 1, 2):
            raise ValueError('invalid or imbalanced counterfactual conditions')
        key = (actor, target, sh, th, mem)
        if key in keys:
            raise ValueError('duplicate case')
        keys.add(key)
        p = row['full_probabilities']
        hid = row['hidden']
        if len(p) != 6 or len(hid) != 12 or any(not math.isfinite(x) for x in p + hid):
            raise ValueError('invalid neural output array')
        if any(x < 0 or x > 1 for x in p) or abs(sum(p) - 1) > 1e-8:
            raise ValueError('invalid probability vector')
        if any(abs(x) > 1+1e-10 for x in hid):
            raise ValueError('invalid tanh activations')
        if abs(row['protect_probability'] - p[target + 3]) > 1e-15:
            raise ValueError('incorrect target shield probability')
        if p[actor + 3] != 0:
            raise ValueError('illegal self protection must have zero probability')
        by_agent[actor].append(row)
    if len(keys) != 72 or any(len(x) != 24 for x in by_agent):
        raise ValueError('missing factorial condition')
    aggregate = report['agent_aggregates']
    if len(aggregate) != 3:
        raise ValueError('agent aggregates missing')
    for idx, rows in enumerate(by_agent):
        e = aggregate[idx]
        if e['actor'] != idx:
            raise ValueError('aggregate identity mismatch')
        def avg(pred):
            z = [x['protect_probability'] for x in rows if pred(x)]
            if not z: raise ValueError('empty balance cell')
            return sum(z) / len(z)
        expected = {
            'p_protect_critical': avg(lambda x:x['target_hp']==1),
            'p_protect_healthy': avg(lambda x:x['target_hp']==8),
            'p_prior_helped': avg(lambda x:x['memory_mode']==1),
            'p_prior_harmed': avg(lambda x:x['memory_mode']==2),
            'p_neutral': avg(lambda x:x['memory_mode']==0),
            'p_own_hp_low': avg(lambda x:x['self_hp']==4),
            'p_own_hp_high': avg(lambda x:x['self_hp']==8),
        }
        expected['delta_need'] = expected['p_protect_critical'] - expected['p_protect_healthy']
        expected['delta_prior_helped_vs_harmed'] = expected['p_prior_helped'] - expected['p_prior_harmed']
        for k, v in expected.items():
            if not math.isclose(e[k], v, abs_tol=1e-12, rel_tol=1e-10):
                raise ValueError('incorrect aggregate: '+k)
        if e['active_connections'] not in range(253):
            raise ValueError('invalid connection count')
    g = report['exploratory_screening_gate']
    if g['behavioral_transfer_pass'] is not False or g['attacker_intention_observable'] is not False:
        raise ValueError('inference claim exceeds observed sensory features')
    if not all(g[k] is False for k in ('all_roles_help_critical','all_roles_distinguish_need','all_roles_help_past_harmer')):
        raise ValueError('unexpected social pass claim')
    return {'status':'PASS_DATA_INTEGRITY', 'test_subject':'FAILED_BEHAVIORAL_SOCIAL_TRANSFER',
            'cases':len(rows)*3, 'source_episodes':report['source_episodes'],
            'assay_json_sha256':hashlib.sha256(blob).hexdigest(),
            'max_critical_protection_probability':max(a['p_protect_critical'] for a in aggregate),
            'all_roles_social_gate_pass':g['behavioral_transfer_pass']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('result',type=Path)
    parser.add_argument('--expected-sha',required=True)
    a=parser.parse_args()
    print(json.dumps(audit(a.result,a.expected_sha),ensure_ascii=False,indent=2))

if __name__=='__main__': main()
