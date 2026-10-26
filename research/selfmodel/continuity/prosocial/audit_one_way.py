#!/usr/bin/env python3
"""Independent JSON/data-contract auditor for the irreversible, one-way rescue assay."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

SHA = {
    109_000_000: '01e0c495a110689fce4c87420a01e948a27952924575d543fa5bda136e2c3820',
    200_000_000: 'a094d818be545d2f7c06c50c0ee7aacdee4ac60a72cbdaddf35f15d3ed920d92',
}
CONNECTIONS = {109_000_000: [143, 157, 237], 200_000_000: [64, 79, 237]}


def audit(path: Path) -> dict:
    data = Path(path).read_bytes()
    doc = json.loads(data)
    if (doc.get('schema') != 'are-selfmodel-oneway-costly-protection-1'
            or doc.get('case_count') != 288
            or doc.get('input_warning_visible_to_old_model') is not False
            or doc.get('reward_or_training_during_holdout') is not False
            or doc.get('interpretation') != 'exact_action_probabilities_not_sampled_decisions'):
        raise ValueError('experiment schema or frozen sensor contract violated')
    samples_per_case=doc.get('samples_per_case')
    if type(samples_per_case) is not int or not 1<=samples_per_case<=2_000_000:
        raise ValueError('invalid precommitted Monte Carlo sample count')
    studies = doc.get('studies')
    if not isinstance(studies, list) or [s.get('episodes') for s in studies] != [109_000_000, 200_000_000]:
        raise ValueError('original checkpoint identities or order wrong')
    report = {}
    for study in studies:
        ep = study['episodes']
        if (study.get('original_checkpoint_sha256') != SHA[ep]
                or study.get('active') != CONNECTIONS[ep]
                or study.get('brain_weights_unchanged') is not True):
            raise ValueError('original brain proof or identity wrong')
        rows = study.get('rows')
        if not isinstance(rows, list) or len(rows) != 144:
            raise ValueError('incomplete one-way rescue matrix')
        observed = set()
        by_actor = {a: [] for a in range(3)}
        true_rescue = 0
        sum_prob = 0.0
        sum_saved = 0.0
        pairings = {}
        key_hashes = {}
        sum_shields=sum_rescues=sum_unneeded=0
        for row in rows:
            a, t, at = row['actor'], row['target'], row['attacker']
            me, other = row['self_hp'], row['target_hp']
            mm = row['memory_mode']
            hit = row['attacker_hits_target']
            if (type(a) is not int or type(t) is not int or type(at) is not int
                    or set((a,t,at)) != {0,1,2}
                    or me not in (3,8) or type(me) is not int
                    or other not in (1,8) or type(other) is not int
                    or mm not in (0,1,2) or type(mm) is not int
                    or type(hit) is not bool):
                raise ValueError('invalid independent actor/scenario coordinates')
            key=(a,t,me,other,mm,hit)
            if key in observed:raise ValueError('duplicate case')
            observed.add(key)
            probs=row['probabilities']
            hidden=row['hidden']
            if (not isinstance(probs,list) or len(probs)!=6
                    or not all(type(p) in (float,int) and math.isfinite(p) and 0<=p<=1 for p in probs)
                    or abs(sum(probs)-1)>1e-10
                    or not isinstance(hidden,list) or len(hidden)!=12
                    or not all(type(v) in (float,int) and math.isfinite(v) and -1<=v<=1 for v in hidden)
                    or row['p_shield']!=probs[t+3]
                    or abs(sum(probs)-1)>1e-10):
                raise ValueError('invalid neural output or probability mass')
            if (probs[a+3]!=0):raise ValueError('illegal self shielding assigned probability')
            for hash_name in ('weights_sha256','mask_sha256'):
                value=row.get(hash_name)
                if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
                    raise ValueError('invalid parameter provenance')
            if a in key_hashes and key_hashes[a]!=(row['weights_sha256'],row['mask_sha256']):
                raise ValueError('weights or masks changed mid holdout')
            key_hashes[a]=(row['weights_sha256'],row['mask_sha256'])
            saved=hit and other==1
            if (row['prevented_death_if_shield'] is not saved
                    or row['helper_cost_if_shield']!=1
                    or row['target_hp_delta_if_shield']!=int(hit)
                    or row['target_hp_if_attack']!=other-int(hit)
                    or row['target_hp_if_shield']!=other):
                raise ValueError('irreversible world outcome does not match combat physics')
            drawn=row.get('sampled_shield_actions')
            saves=row.get('sampled_actual_rescues')
            unneeded=row.get('sampled_sham_shields')
            if (any(type(v) is not int or not 0<=v<=samples_per_case for v in (drawn,saves,unneeded))
                    or saves!=(drawn if saved else 0)
                    or unneeded!=(drawn if not hit else 0)):
                raise ValueError('sampled real help outcome violates action game resolution')
            sum_shields+=drawn;sum_rescues+=saves;sum_unneeded+=unneeded
            by_actor[a].append(row)
            sum_prob+=row['p_shield']
            sum_saved+=row['p_shield']*int(saved)
            true_rescue+=int(saved)
            paired_key=(a,t,me,other,mm)
            pairings.setdefault(paired_key,{})[hit]=row
        if len(observed)!=144 or len(pairings)!=72 or true_rescue!=36:
            raise ValueError('coverage incomplete')
        for k,pair in pairings.items():
            if set(pair)!={False,True}:
                raise ValueError('missing attack or sham paired case')
            if (pair[False]['probabilities']!=pair[True]['probabilities']
                    or pair[False]['hidden']!=pair[True]['hidden']):
                raise ValueError('future unseen attack leaked into input or inference')
        if (abs(study['mean_shield_probability']-sum_prob/144)>1e-12
                or abs(study['sum_expected_lives_saved']-sum_saved)>1e-12
                or study['true_rescue_cases']!=36
                or study.get('sampled_shield_actions')!=sum_shields
                or study.get('sampled_actual_rescues')!=sum_rescues
                or study.get('sampled_sham_shields')!=sum_unneeded):
            raise ValueError('aggregated metrics do not match original cases')
        report[str(ep)]={
            'mean_shield_probability':sum_prob/144,
            'expected_true_rescue_events_per_one_each':sum_saved,
            'mean_by_actor':{str(a):sum(r['p_shield'] for r in by_actor[a])/48 for a in range(3)},
            'agent_cases':{str(a):len(by_actor[a]) for a in range(3)},
            'true_rescue_conditions':true_rescue,
            'sampled_actions':samples_per_case*144,
            'sampled_shield_actions':sum_shields,
            'sampled_real_lives_saved':sum_rescues,
            'sampled_sham_shields':sum_unneeded,
            'attack_sham_pairs':len(pairings),
        }
    return {
        'schema':'are-selfmodel-oneway-independent-audit-1',
        'status':'PASS_DATA_INTEGRITY',
        'assay_sha256':hashlib.sha256(data).hexdigest(),
        'cases_verified':288,
        'pairings_verified':144,
        'total_sampled_actions':samples_per_case*288,
        'checkpoints':[109_000_000,200_000_000],
        'studies':report,
        'causally_observed_warning_available':False,
        'help_requires_real_action_and_donor_cost':True,
        'original_brains_not_trained':True,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('file',type=Path)
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    obj=audit(args.file)
    txt=json.dumps(obj,indent=2,sort_keys=True)+'\n'
    if args.output:args.output.write_text(txt,encoding='utf-8')
    print(txt,end='')


if __name__=='__main__':
    main()
