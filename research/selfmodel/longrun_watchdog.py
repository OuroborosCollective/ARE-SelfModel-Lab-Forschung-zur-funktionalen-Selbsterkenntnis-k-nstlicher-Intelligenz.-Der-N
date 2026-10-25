"""Wall-clock-bounded, unthrottled German lexical-loss toy-policy endurance run.

A checkpointed, observational experiment; *not* conscious or self-motivated AI.
Episodes are logical resets, not operating-system process kills. No sleep,
external language model, protected dictionary content, network, or database.
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import time
from typing import Callable, Sequence

from research.selfmodel.lexicon_watchdog import (
    ARMS, GERMAN_PAGES, PAGE_COUNT, Policy, SYNAPSES,
    _arm_seed, simulate_episode,
)

MAX_DURATION_SECONDS = 14400.0
MAX_EPISODES = 100_000_000
DEFAULT_DAMAGE_INTERVAL = 250_000


def _bounded_number(value: object, name: str, maximum: float) -> float:
    if type(value) not in (float, int) or not math.isfinite(value) or not 0 < value <= maximum:
        raise ValueError(f"{name} must be a finite positive number <= {maximum}")
    return float(value)


def run_duration_experiment(
    *, duration_seconds: float = 3600.0, max_episodes: int = 80_000_000,
    seed: int = 17, damage_every_failures: int = DEFAULT_DAMAGE_INTERVAL,
    progress_seconds: float = 60.0, learning_rate: float = 0.8,
    clock: Callable[[], float] = time.monotonic,
    progress_path: Path | None = None, verbose: bool = False,
) -> dict:
    """Continue the original four arms at full speed until a wall-clock deadline.

    First failing episode lesions one policy parameter; thereafter one additional
    parameter per *damage_every_failures* failed episodes in each damage arm.
    The 8 German toy-word pages reset every episode; only engineered learned
    policy weights and damage masks persist. No physical kill or consciousness.
    """
    duration = _bounded_number(duration_seconds, "duration_seconds", MAX_DURATION_SECONDS)
    period = _bounded_number(progress_seconds, "progress_seconds", 3600.0)
    if type(max_episodes) is not int or not 1 <= max_episodes <= MAX_EPISODES:
        raise ValueError("max_episodes must be an integer in 1..100000000")
    if type(damage_every_failures) is not int or not 1 <= damage_every_failures <= MAX_EPISODES:
        raise ValueError("damage_every_failures must be an integer in 1..100000000")
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError("seed must be a nonnegative 64-bit integer")
    if type(learning_rate) not in (int, float) or not math.isfinite(learning_rate) or not 0 <= learning_rate <= 10:
        raise ValueError("learning_rate must be finite and in 0..10")
    if not callable(clock):
        raise ValueError("clock must be callable")

    rand = random.Random(seed)
    expiry_order = list(range(PAGE_COUNT))
    rand.shuffle(expiry_order)
    initial = [rand.uniform(-0.15, 0.15) for _ in range(SYNAPSES)]
    policies = {arm: Policy(initial) for arm in ARMS}
    lesion_rngs = {arm: random.Random(_arm_seed(seed, arm)) for arm in ARMS}
    stats = {arm: {
        "successful_episodes": 0, "failed_episodes": 0,
        "total_words_processed": 0, "number_of_data_losses": 0,
        "first_success_episode": None, "logical_watchdog_resets": 0,
        "lesions_applied": 0,
    } for arm in ARMS}
    progress_digest = hashlib.sha256()
    progress_records = 0
    completed = 0
    start = clock()
    if not math.isfinite(start):
        raise ValueError("clock returned non-finite start")
    next_progress = period
    state = "episode_cap_reached"
    last_elapsed = 0.0
    output = Path(progress_path) if progress_path is not None else None
    manager = output.open("x", encoding="utf-8", newline="\n") if output else nullcontext(None)

    def emit(writer, *, phase: str, elapsed: float) -> None:
        nonlocal progress_records
        record = {
            "schema": "are-selfmodel-longrun-progress-1", "phase": phase,
            "elapsed_seconds": elapsed, "episodes_completed": completed,
            "epochs_per_second": (completed / elapsed if elapsed > 0 else None),
            "damage_every_failures": damage_every_failures,
            "arms": {arm: {
                "successful_episodes": stats[arm]["successful_episodes"],
                "failed_episodes": stats[arm]["failed_episodes"],
                "lesions_applied": stats[arm]["lesions_applied"],
                "remaining_synapses": policies[arm].remaining,
                "policy_updates": policies[arm].updates,
                "weights_sha256": policies[arm].weights_sha256,
                "mask_sha256": policies[arm].mask_sha256,
            } for arm in ARMS},
            "evidence_level": "bounded_toy_policy_simulation",
            "subjective_experience_inferred": False,
        }
        if writer is not None:
            line = json.dumps(record, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n"
            writer.write(line)
            writer.flush()
            os.fsync(writer.fileno())
            progress_digest.update(line.encode("utf-8"))
            progress_records += 1
        if verbose:
            frozen = stats["frozen_with_damage"]
            print(
                f"PROGRESS phase={phase} seconds={elapsed:.2f} episodes={completed} "
                f"eps_per_sec={(completed / elapsed if elapsed > 0 else 0):.1f} "
                f"frozen_lesions={frozen['lesions_applied']} ",
                file=sys.stderr, flush=True,
            )

    with manager as writer:
        for episode in range(max_episodes):
            elapsed = clock() - start
            if not math.isfinite(elapsed) or elapsed < last_elapsed:
                raise ValueError("nonmonotonic or non-finite experiment clock")
            last_elapsed = elapsed
            if elapsed >= duration:
                state = "duration_elapsed"
                break
            for arm, policy in policies.items():
                outcome = simulate_episode(policy.page_order(), expiry_order, decay="preempt", action_limit=PAGE_COUNT)
                current = stats[arm]
                successful = outcome["success"]
                current["successful_episodes"] += int(successful)
                current["failed_episodes"] += int(not successful)
                current["total_words_processed"] += outcome["counted_words"]
                current["number_of_data_losses"] += outcome["lost_before_processing"]
                if successful and current["first_success_episode"] is None:
                    current["first_success_episode"] = episode
                if not successful:
                    current["logical_watchdog_resets"] += 1
                if arm.startswith("learned_"):
                    policy.train_from_observed_loss(outcome["lost_events"], float(learning_rate))
                if not successful and arm.endswith("_with_damage"):
                    failures = current["failed_episodes"]
                    if failures == 1 or (failures - 1) % damage_every_failures == 0:
                        if policy.lesion_one(lesion_rngs[arm]):
                            current["lesions_applied"] += 1
            completed += 1
            if elapsed >= next_progress:
                emit(writer, phase="checkpoint", elapsed=elapsed)
                next_progress = period * (int(elapsed // period) + 1)
        elapsed = clock() - start
        if not math.isfinite(elapsed) or elapsed < last_elapsed:
            raise ValueError("nonmonotonic or non-finite experiment clock")
        emit(writer, phase="final", elapsed=elapsed)

    return {
        "schema": "are-selfmodel-lexicon-duration-1",
        "status": state,
        "duration_completed": state == "duration_elapsed",
        "run_mode": "unthrottled_duration",
        "duration_seconds_requested": duration,
        "elapsed_seconds": elapsed,
        "episodes_requested_cap": max_episodes,
        "episodes_completed": completed,
        "episodes_per_second_observed": completed / elapsed if elapsed else 0,
        "damage_every_failures": damage_every_failures,
        "damage_schedule": "one_lesion_on_first_failure_then_one_each_N_failures",
        "learning_rate": float(learning_rate),
        "learning_rule_externally_specified": True,
        "seed": seed,
        "expiry_order": expiry_order,
        "expiry_schedule_visible_to_agent": False,
        "model_kind": "tiny_linear_policy_over_original_german_stimuli",
        "data_source": "author_created_illustrative_words_not_duden",
        "data_set_restored_every_episode": True,
        "dataset_decay_per_episode": "preempt_on_every_action",
        "synapses_initial": SYNAPSES,
        "words_per_episode": sum(len(page.words) for page in GERMAN_PAGES),
        "arms": {arm: {
            **stats[arm],
            "remaining_synapses": policy.remaining,
            "policy_updates": policy.updates,
            "final_weights_sha256": policy.weights_sha256,
            "final_synapse_mask_sha256": policy.mask_sha256,
        } for arm, policy in policies.items()},
        "progress_file_name": output.name if output is not None else None,
        "progress_records": progress_records,
        "progress_sha256": progress_digest.hexdigest() if output is not None else None,
        "watchdog_kind": "logical_reset_with_external_weight_lesions",
        "actual_os_process_kill_measured": False,
        "behavioral_self_report_measured": False,
        "subjective_experience_inferred": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration-seconds", type=float, default=3600.0)
    parser.add_argument("--max-episodes", type=int, default=80_000_000)
    parser.add_argument("--damage-every-failures", type=int, default=DEFAULT_DAMAGE_INTERVAL)
    parser.add_argument("--progress-seconds", type=float, default=60.0)
    parser.add_argument("--learning-rate", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--progress", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    result = run_duration_experiment(
        duration_seconds=args.duration_seconds, max_episodes=args.max_episodes,
        seed=args.seed, damage_every_failures=args.damage_every_failures,
        progress_seconds=args.progress_seconds, learning_rate=args.learning_rate,
        progress_path=args.progress, verbose=not args.quiet,
    )
    rendered = json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    if args.receipt is not None:
        with args.receipt.open("x", encoding="utf-8", newline="\n") as file:
            file.write(rendered)
    print(rendered, end="")
    return 0 if result["duration_completed"] else 124


if __name__ == "__main__":
    raise SystemExit(main())
