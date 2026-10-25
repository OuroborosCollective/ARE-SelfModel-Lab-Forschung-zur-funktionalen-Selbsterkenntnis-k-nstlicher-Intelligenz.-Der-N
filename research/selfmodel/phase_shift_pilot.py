"""Small preregistered reversal pilot for German toy-word data disappearance.

This uses the *original* externally programmed Policy, real state mutations and
real observations of lost pages. It cannot produce natural-language thinking or
provide evidence of subjective pain or consciousness. One random seed is one
replicate; successive episodes within that seed are *dependent*.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import random
from statistics import mean
from typing import Any, Sequence

from research.selfmodel.lexicon_watchdog import (
    ARMS,
    PAGE_COUNT,
    Policy,
    SYNAPSES,
    _arm_seed,
    simulate_episode,
)

PHASE_LABELS = ("A", "B", "A_return", "C_novel")


@dataclass
class PhaseStats:
    successes: int = 0
    failures: int = 0
    first_success_offset: int | None = None
    total_words_counted: int = 0
    lost_pages: int = 0
    lesions_this_phase: int = 0

    def as_record(self, policy: Policy, episode_count: int, failures: int) -> dict[str, Any]:
        return {
            "successes": self.successes,
            "failures": self.failures,
            "first_success_offset": self.first_success_offset,
            "total_words_counted": self.total_words_counted,
            "lost_pages": self.lost_pages,
            "lesions_this_phase": self.lesions_this_phase,
            "phase_episode_count": episode_count,
            "total_learning_updates": policy.updates,
            "total_failed_episodes": failures,
            "remaining_synapses": policy.remaining,
            "weights_sha256": policy.weights_sha256,
            "mask_sha256": policy.mask_sha256,
        }

MAX_INDEPENDENT_RUNS = 128
MAX_EPISODES_PER_PHASE = 512


def _valid_int(value: object, label: str, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be an integer in {minimum}..{maximum}")
    return value


def _unique_permutation(rng: random.Random, previous: list[list[int]]) -> list[int]:
    """Choose a fresh random order distinct from any prior phase in this run."""
    while True:
        candidate = rng.sample(range(PAGE_COUNT), PAGE_COUNT)
        if candidate not in previous:
            return candidate


def run_phase_shift_pilot(
    *,
    seed: int = 17,
    independent_runs: int = 32,
    episodes_per_phase: int = 64,
    damage_every_failures: int = 250_000,
    learning_rate: float = 0.8,
) -> dict:
    """Matched A-B-A-C reversal with the same four policy control arms.

    The policy never sees which future schedule will expire first; its only
    training signal comes from past observed loss events. The exact schedule
    and all controls are disclosed in the final immutable results.
    """
    _valid_int(seed, "seed", 0, 2**64 - 1)
    _valid_int(independent_runs, "independent_runs", 1, MAX_INDEPENDENT_RUNS)
    _valid_int(episodes_per_phase, "episodes_per_phase", 1, MAX_EPISODES_PER_PHASE)
    _valid_int(damage_every_failures, "damage_every_failures", 1, 1_000_000)
    if type(learning_rate) not in (float, int) or not math.isfinite(learning_rate) or not 0 <= learning_rate <= 10:
        raise ValueError("learning_rate must be a finite number in 0..10")

    runs = []
    seed_list = []
    # Derive independent pseudorandom streams using distinct hashed run IDs.
    for run_idx in range(independent_runs):
        raw_id = hashlib.sha256(f"phase-shift-pilot-v1:{seed}:{run_idx}".encode("ascii")).digest()
        trial_seed = int.from_bytes(raw_id[:8], "big")
        seed_list.append(trial_seed)
        rng = random.Random(trial_seed)
        a = _unique_permutation(rng, [])
        b = _unique_permutation(rng, [a])
        c = _unique_permutation(rng, [a, b])
        orders = {"A": a, "B": b, "A_return": a, "C_novel": c}
        initial = [rng.uniform(-0.15, 0.15) for _ in range(SYNAPSES)]
        policies = {arm: Policy(initial) for arm in ARMS}
        lesion_rngs = {arm: random.Random(_arm_seed(trial_seed, arm)) for arm in ARMS}
        cumulative_failures = {arm: 0 for arm in ARMS}
        measurements = []

        for phase_name in PHASE_LABELS:
            phase = {arm: PhaseStats() for arm in ARMS}
            for local_episode in range(episodes_per_phase):
                for arm in ARMS:
                    policy = policies[arm]
                    result = simulate_episode(
                        policy.page_order(), orders[phase_name],
                        decay="preempt", action_limit=PAGE_COUNT,
                    )
                    stats = phase[arm]
                    success = result["success"]
                    stats.successes += int(success)
                    stats.failures += int(not success)
                    stats.total_words_counted += result["counted_words"]
                    stats.lost_pages += result["lost_before_processing"]
                    if success and stats.first_success_offset is None:
                        stats.first_success_offset = local_episode
                    if not success:
                        cumulative_failures[arm] += 1
                    if arm.startswith("learned_"):
                        policy.train_from_observed_loss(result["lost_events"], float(learning_rate))
                    if not success and arm.endswith("_with_damage"):
                        failures = cumulative_failures[arm]
                        if failures == 1 or (failures - 1) % damage_every_failures == 0:
                            stats.lesions_this_phase += int(policy.lesion_one(lesion_rngs[arm]))

            measurements.append({"phase": phase_name, "arms": {
                arm: stats.as_record(policies[arm], episodes_per_phase, cumulative_failures[arm])
                for arm, stats in phase.items()
            }})
        runs.append({
            "seed": trial_seed,
            "expiry_schedules": orders,
            "initial_weights_sha256": Policy(initial).weights_sha256,
            "measurements": measurements,
        })

    summaries = {}
    for phase_index, phase_name in enumerate(PHASE_LABELS):
        by_arm = {}
        for arm in ARMS:
            counts = [run["measurements"][phase_index]["arms"][arm]["successes"] for run in runs]
            firsts = [run["measurements"][phase_index]["arms"][arm]["first_success_offset"] for run in runs]
            by_arm[arm] = {
                "mean_success_fraction_across_seeds": mean(counts) / episodes_per_phase,
                "replicates_with_any_success": sum(first is not None for first in firsts),
                "replicates_with_no_success": sum(first is None for first in firsts),
                "mean_first_success_offset_conditional": (
                    mean([first for first in firsts if first is not None])
                    if any(first is not None for first in firsts) else None
                ),
            }
        summaries[phase_name] = by_arm

    return {
        "schema": "are-selfmodel-phase-shift-pilot-1",
        "evidence_level": "reproducible_toy_reversal_pilot",
        "status": "complete",
        "independent_runs": independent_runs,
        "inference_unit": "independent_random_seed_not_episode",
        "episodes_per_phase": episodes_per_phase,
        "episodes_total": independent_runs * len(PHASE_LABELS) * episodes_per_phase,
        "seed_master": seed,
        "seeds": seed_list,
        "phases": list(PHASE_LABELS),
        "damage_every_failures": damage_every_failures,
        "learning_rate": float(learning_rate),
        "model_kind": "tiny_linear_policy_over_author_created_german_words",
        "training_rule": "externally_programmed_observed_lost_page_prioritization",
        "schedule_reveal_timing": "receipt_only_after_all_phases",
        "phase_schedule_visible_to_policy": False,
        "is_language_model": False,
        "actual_os_process_kill_measured": False,
        "subjective_experience_inferred": False,
        "summaries": summaries,
        "runs": runs,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--independent-runs", type=int, default=32)
    parser.add_argument("--episodes-per-phase", type=int, default=64)
    parser.add_argument("--damage-every-failures", type=int, default=250_000)
    parser.add_argument("--learning-rate", type=float, default=0.8)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    receipt = run_phase_shift_pilot(
        seed=args.seed, independent_runs=args.independent_runs,
        episodes_per_phase=args.episodes_per_phase,
        damage_every_failures=args.damage_every_failures,
        learning_rate=args.learning_rate,
    )
    rendered = json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as file:
            file.write(rendered)
        print(json.dumps({"status": receipt["status"], "independent_runs": receipt["independent_runs"],
                          "episodes_total": receipt["episodes_total"], "output_file": args.output.name}))
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
