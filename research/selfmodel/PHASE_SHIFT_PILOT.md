# A-B-A-C phase shift: 32 independent seeded toy-policy experiments

Status (2026-10-25): **local reproducible pilot**, no trained language model, no natural-language thought, no proof of pain or consciousness.

## Why this follows the hour run

The [3600-second readback](evidence/hour_3600_review_2026-10-25.md) confirmed **31,809,129** logical episodes, but the learning arms had *unchanged weights and lesion masks from minute 1 to minute 60*. Their environment remained fixed; repetition does not prove capacity to handle a changing world.

## Pre-specified change of task conditions

Uses the original `Policy`, `simulate_episode` and authored 48 German word tokens from `lexicon_watchdog.py`; no Duden or external corpus. Each independent seeded run has four consecutive phases of equal length, without resetting the policy:

- **A**: New, internally hidden data-expiry order learned from observed losses.
- **B**: New independently drawn and *different* hidden order (concept drift).
- **A_return**: Reinstates exactly A to measure interference/retention.
- **C_novel**: A third, previously unseen order (transfer to novel order).

Paired four arms start with identical weights: frozen/learned and lesion/no-lesion. The learning rule is always *explicitly programmed*: it boosts pages already observed lost during the last episode. The agent cannot see the future order or free-write notes. In damaged arms, the first failure disables one weight, and one additional weight is disabled for every `--damage-every-failures` failures. Default interval **250,000** as in original one-hour run, thus only the first lesion generally occurs in the short pilot.

Independent analysis unit: **seed**, not episode. The 32-seed by four-phase by 64-episode run includes **8,192 dependent episodes** (plus four matched control arms each episode). We report descriptive mean rates over seeds, not p-values from correlated repetitions.

## Local 32-seed pilot (with deterministic random streams)

| Phase | Learned, no damage: mean success rate | Learned, with damage: mean success rate | Mean episode of first success (learned, no damage) |
|---|---:|---:|---:|
| A | 94.09% | 94.09% | 3.78 |
| B | 81.15% | 81.25% | 12.06 |
| A_return | 73.73% | 74.46% | 16.81 |
| C_novel | 72.27% | 73.83% | 17.75 |

Both frozen controls achieved **0%** in all four phases across these seeds. All 32 learned runs eventually completed each phase at least once in this configuration; the result follows from the *programmed optimizer* and a deliberately repeated order within each phase. Return to A shows poorer early success than the first acquisition; this is **exploratory evidence of policy interference**, not a demonstration of personal memory, fear, pain, or subjective self-experience. A different training rule or phase duration can yield other results.

The complete seed-level JSON was generated locally with the original source. Running the GitHub CI workflow on the committed code provides **independent execution** and a GitHub artifact; do not claim that until it completes and is read back.

### Local reproduction

From repository root, Python standard library only:

```bash
python -m unittest discover -s research/selfmodel/tests -p 'test_phase_shift_pilot.py' -v
python -m research.selfmodel.phase_shift_pilot \
  --seed 17 --independent-runs 32 --episodes-per-phase 64 \
  --damage-every-failures 250000 --learning-rate 0.8 \
  --output phase_shift_pilot_32x64.json
```

### Limits and next experiment

A **real agent** test must separately instrument an actual pretrained small German-capable model, its language outputs, explicit memory tools, and independent OS process restarts. Randomness, hidden changing schedules, prompt leakage and harness-generated files must be independently audited. The phase-shift pilot does **not** measure any of these properties.
