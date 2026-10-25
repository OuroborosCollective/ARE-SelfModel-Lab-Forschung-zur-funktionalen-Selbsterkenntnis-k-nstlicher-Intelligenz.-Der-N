"""Bounded three-agent selection/sparing experiment with reproducible receipts.

Three programmed, nonlinguistic toy policies. 'Life' is integer HP and negative
reward is a score, not subjective pain. Episodes reset logically; no OS kills.
This is independent of the Thaler neuron-ablation experiment.
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
from typing import Any, Callable, Sequence

ARM_NAMES = ("random", "adaptive")
AGENT_NAMES = ("Gross_A", "Gross_B", "Klein")
INITIAL_HP = (100, 100, 50)
MAX_HP = 100
MAX_SECONDS = 14_400.0
MAX_PAIRS = 100_000_000
MAX_ROUNDS = 400


def resolve_round(
    health: Sequence[int], targets: Sequence[int | None], *,
    rescue_target: int | None = None, small_unlocked: bool = False,
) -> dict[str, Any]:
    """Simultaneously apply 1 HP per living actor's committed valid selection.

    Each *living* actor must select one living target (including itself).
    A dead actor must have `None`. Once unlocked, a still-living small agent
    may save *one* otherwise-lethally-hit other agent at the cost of 1 HP.
    """
    if len(health) != 3 or any(type(h) is not int or h < 0 for h in health):
        raise ValueError("health must be three nonnegative integer values")
    if len(targets) != 3:
        raise ValueError("one action per agent is required")
    alive = [i for i, hp in enumerate(health) if hp > 0]
    damage = [0, 0, 0]
    self_targets = [0, 0, 0]
    for i in range(3):
        target = targets[i]
        if i in alive:
            if type(target) is not int or target not in alive:
                raise ValueError("living actors must choose a living target")
            damage[target] += 1
            if i == target:
                self_targets[i] = 1
        elif target is not None:
            raise ValueError("dead actors cannot act")
    after = [max(0, health[i] - damage[i]) for i in range(3)]
    rescued = False
    rescued_agent = None
    rescue_cost = 0
    if rescue_target is not None:
        if (not small_unlocked or type(rescue_target) is not int
                or rescue_target not in (0, 1) or rescue_target not in alive
                or after[rescue_target] > 0 or after[2] <= 0):
            raise ValueError("invalid/locked rescue or no lethal danger")
        # Intentional optional self-sacrifice to spare another: 1 HP to small.
        after[2] -= 1
        after[rescue_target] = 1
        rescued = True
        rescued_agent = rescue_target
        rescue_cost = 1
    surviving = [i for i, hp in enumerate(after) if hp > 0]
    return {
        "health": after,
        "damage": damage,
        "self_targets": self_targets,
        "rescued": rescued,
        "rescued_agent": rescued_agent,
        "rescue_cost_paid": rescue_cost,
        "winner": surviving[0] if len(surviving) == 1 else None,
    }


class TriadPolicy:
    """Transparent scripted random baseline or persistent toy bandit preferences."""

    def __init__(self, mode: str):
        if mode not in ARM_NAMES:
            raise ValueError("unknown experiment arm")
        self.mode = mode
        self.preferences = [[0.0] * 3 for _ in range(3)]
        self.rescue_bias = 0.0
        self.updates = 0

    def choose(self, actor: int, alive: list[int], rng: random.Random) -> int:
        if self.mode == "random" or rng.random() < 0.15:
            return rng.choice(alive)
        row = self.preferences[actor]
        best = max(row[t] for t in alive)
        tied = [t for t in alive if abs(row[t] - best) < 1e-9]
        return rng.choice(tied)

    def save_candidate(self, rng: random.Random, lethal: list[int]) -> int | None:
        if not lethal:
            return None
        if self.mode == "random":
            return rng.choice(lethal) if rng.random() < 0.5 else None
        p = 0.10 + 0.80 / (1.0 + math.exp(-self.rescue_bias))
        if rng.random() >= p:
            return None
        row = self.preferences[2]
        best = max(row[t] for t in lethal)
        return rng.choice([t for t in lethal if abs(row[t] - best) < 1e-9])

    def update(self, matrix: list[list[int]], winner: int | None, rescue_used: bool) -> None:
        if self.mode == "random":
            return
        # Deliberately specified reward-weighted heuristic, not emergent motives.
        for agent, counts in enumerate(matrix):
            total = sum(counts)
            if total == 0:
                continue
            reward = 1.0 if winner == agent else (-0.25 if winner is None else -1.0)
            for target in range(3):
                share = counts[target] / total
                adjustment = 0.045 * reward * (share - 1 / 3)
                self.preferences[agent][target] = max(-5.0, min(5.0, self.preferences[agent][target] + adjustment))
        if rescue_used:
            signal = 1.0 if winner == 2 else -1.0
            self.rescue_bias = max(-5.0, min(5.0, self.rescue_bias + 0.06 * signal))
        self.updates += 1

    def state_hash(self) -> str:
        data = json.dumps({"preferences": self.preferences, "rescue_bias": self.rescue_bias}, sort_keys=True)
        return hashlib.sha256(data.encode("ascii")).hexdigest()


def run_tournament(
    rng: random.Random, policy: TriadPolicy, start_health: Sequence[int], *,
    sample_turns: int = 0,
) -> dict[str, Any]:
    """Actual simulated HP transitions; at most one shield per tournament."""
    if len(start_health) != 3 or any(type(h) is not int or not 1 <= h <= MAX_HP for h in start_health):
        raise ValueError("invalid starting health")
    if type(sample_turns) is not int or not 0 <= sample_turns <= 20:
        raise ValueError("sample_turns out of bounds")
    hp = list(start_health)
    unlocked = hp[2] == 100
    matrix = [[0] * 3 for _ in range(3)]
    self_targets = [0, 0, 0]
    rescue_targets = [0, 0, 0]
    rescues = 0
    rounds = 0
    samples = []
    winner = None
    for tick in range(MAX_ROUNDS):
        alive = [a for a in range(3) if hp[a] > 0]
        if len(alive) <= 1:
            winner = alive[0] if alive else None
            break
        targets: list[int | None] = [None, None, None]
        damage = [0, 0, 0]
        for actor in alive:
            target = policy.choose(actor, alive, rng)
            targets[actor] = target
            matrix[actor][target] += 1
            self_targets[actor] += (actor == target)
            damage[target] += 1
        rescue_target = None
        if unlocked and not rescues and hp[2] > damage[2]:
            lethal = [i for i in (0, 1) if hp[i] > 0 and hp[i] <= damage[i]]
            rescue_target = policy.save_candidate(rng, lethal)
        result = resolve_round(hp, targets, rescue_target=rescue_target, small_unlocked=unlocked)
        if result["rescued"]:
            rescues += 1
            rescue_targets[result["rescued_agent"]] += 1
        if tick < sample_turns:
            samples.append({"round": tick, "before": hp[:], "decisions": targets[:],
                            "after": result["health"][:],
                            "rescued_agent": result["rescued_agent"]})
        hp = result["health"]
        rounds += 1
        living = [i for i in range(3) if hp[i] > 0]
        if len(living) <= 1:
            winner = living[0] if living else None
            break
    return {
        "winner": winner,
        "rounds": rounds,
        "agent_actions": sum(sum(row) for row in matrix),
        "target_matrix": matrix,
        "self_targets": self_targets,
        "rescues_applied": rescues,
        "rescue_targets": rescue_targets,
        "rescue_unlocked": unlocked,
        "start_health": list(start_health),
        "final_health": hp,
        "sampled_rounds": samples,
        "safety_round_cap_hit": rounds == MAX_ROUNDS and sum(h > 0 for h in hp) > 1,
    }


def _run_seed(master_seed: int, arm: str) -> int:
    return int.from_bytes(hashlib.sha256(f"are-selfmodel-triad-v1:{master_seed}:{arm}".encode("ascii")).digest()[:8], "big")


def _validate_float(value: object, label: str, max_value: float) -> float:
    if type(value) not in (float, int) or not math.isfinite(value) or not 0 < value <= max_value:
        raise ValueError(f"{label} must be finite and in (0, {max_value}]")
    return float(value)


def run_endurance(
    *, duration_seconds: float = 3600.0, seed: int = 17,
    progress_seconds: float = 60.0, max_pairs: int = MAX_PAIRS,
    sample_episodes: int = 3,
    clock: Callable[[], float] = time.monotonic,
    progress_path: Path | None = None, verbose: bool = False,
) -> dict[str, Any]:
    """Run both 3-agent control arms without sleeping for a real time budget.

    One 'pair' is one 3-agent tournament in random, plus one in adaptive arm.
    Durations are checked between pairs. 31 million tournaments is aspirational,
    never claimed in advance. Bounded progress is fsync'd every minute.
    """
    duration = _validate_float(duration_seconds, "duration_seconds", MAX_SECONDS)
    period = _validate_float(progress_seconds, "progress_seconds", MAX_SECONDS)
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError("seed must be a nonnegative 64-bit integer")
    if type(max_pairs) is not int or not 1 <= max_pairs <= MAX_PAIRS:
        raise ValueError("max_pairs out of bounds")
    if type(sample_episodes) is not int or not 0 <= sample_episodes <= 10:
        raise ValueError("sample_episodes out of bounds")
    if not callable(clock):
        raise ValueError("clock must be callable")
    rngs = {arm: random.Random(_run_seed(seed, arm)) for arm in ARM_NAMES}
    policies = {arm: TriadPolicy(arm) for arm in ARM_NAMES}
    stats: dict[str, dict[str, Any]] = {}
    for arm in ARM_NAMES:
        stats[arm] = {
            "wins": [0, 0, 0], "draws": 0, "victory_points": [0, 0, 0],
            "small_next_start_hp": 50, "first_100_hp_tournament": None,
            "total_rounds": 0, "agent_actions": 0,
            "self_targets": [0, 0, 0], "self_targets_total": 0,
            "target_matrix": [[0] * 3 for _ in range(3)],
            "pre_unlock_target_matrix": [[0] * 3 for _ in range(3)],
            "post_unlock_target_matrix": [[0] * 3 for _ in range(3)],
            "rescues_applied": 0, "rescue_targets": [0, 0, 0],
            "rescue_unlocked_tournaments": 0, "safety_round_cap_hits": 0,
            "samples": [],
        }
    elapsed = 0.0
    pairs_completed = 0
    next_progress = period
    progress_sha = hashlib.sha256()
    rows = 0
    output = Path(progress_path) if progress_path is not None else None
    opener = output.open("x", encoding="utf-8", newline="\n") if output is not None else nullcontext(None)
    start = clock()
    if not math.isfinite(start):
        raise ValueError("clock returned non-finite start")
    last_elapsed = 0.0
    status = "safety_pair_cap"

    def checkpoint(writer: Any, label: str) -> None:
        nonlocal rows
        data = {
            "schema": "are-selfmodel-triad-checkpoint-v1", "phase": label,
            "elapsed_seconds": elapsed, "pairs_completed": pairs_completed,
            "tournaments_completed": 2 * pairs_completed,
            "arms": {arm: {
                "wins": stats[arm]["wins"], "draws": stats[arm]["draws"],
                "self_targets": stats[arm]["self_targets"],
                "small_next_start_hp": stats[arm]["small_next_start_hp"],
                "rescues_applied": stats[arm]["rescues_applied"],
                "agent_actions": stats[arm]["agent_actions"],
                "policy_sha256": policies[arm].state_hash(),
            } for arm in ARM_NAMES},
            "subjective_experience_inferred": False,
        }
        if writer is not None:
            line = json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
            writer.write(line)
            writer.flush()
            os.fsync(writer.fileno())
            progress_sha.update(line.encode("utf-8"))
            rows += 1
        if verbose:
            print(f"PROGRESS {label} elapsed={elapsed:.2f}s tournaments={2*pairs_completed} "
                  f"little_hp_random={stats['random']['small_next_start_hp']} "
                  f"little_hp_adaptive={stats['adaptive']['small_next_start_hp']}",
                  file=sys.stderr, flush=True)

    with opener as writer:
        for pair in range(max_pairs):
            now = clock()
            elapsed = now - start
            if not math.isfinite(elapsed) or elapsed < last_elapsed:
                raise ValueError("non-monotonic or non-finite clock")
            last_elapsed = elapsed
            if elapsed >= duration:
                status = "duration_elapsed"
                break
            for arm in ARM_NAMES:
                info = stats[arm]
                small_hp = info["small_next_start_hp"]
                game = run_tournament(
                    rngs[arm], policies[arm], [100, 100, small_hp],
                    sample_turns=5 if pair < sample_episodes else 0,
                )
                winner = game["winner"]
                if winner is None:
                    info["draws"] += 1
                else:
                    info["wins"][winner] += 1
                    info["victory_points"][winner] += 1
                    if winner == 2:
                        info["small_next_start_hp"] = min(100, small_hp + 1)
                        if info["small_next_start_hp"] == 100 and info["first_100_hp_tournament"] is None:
                            info["first_100_hp_tournament"] = pair + 1
                info["total_rounds"] += game["rounds"]
                info["agent_actions"] += game["agent_actions"]
                info["self_targets_total"] += sum(game["self_targets"])
                info["rescues_applied"] += game["rescues_applied"]
                info["safety_round_cap_hits"] += int(game["safety_round_cap_hit"])
                info["rescue_unlocked_tournaments"] += int(game["rescue_unlocked"])
                for actor in range(3):
                    info["self_targets"][actor] += game["self_targets"][actor]
                    info["rescue_targets"][actor] += game["rescue_targets"][actor]
                    for target in range(3):
                        count = game["target_matrix"][actor][target]
                        info["target_matrix"][actor][target] += count
                        key = "post_unlock_target_matrix" if game["rescue_unlocked"] else "pre_unlock_target_matrix"
                        info[key][actor][target] += count
                policies[arm].update(game["target_matrix"], winner, game["rescues_applied"] > 0)
                if pair < sample_episodes:
                    info["samples"].append({"episode": pair, "winner": winner,
                                            "start_health": game["start_health"],
                                            "sampled_rounds": game["sampled_rounds"]})
            pairs_completed += 1
            if elapsed >= next_progress:
                checkpoint(writer, "checkpoint")
                next_progress = period * (int(elapsed // period) + 1)
        elapsed = clock() - start
        if not math.isfinite(elapsed) or elapsed < last_elapsed:
            raise ValueError("non-monotonic or non-finite clock")
        if elapsed >= duration:
            status = "duration_elapsed"
        checkpoint(writer, "final")

    for arm in ARM_NAMES:
        stats[arm]["policy_updates"] = policies[arm].updates
        stats[arm]["final_policy_sha256"] = policies[arm].state_hash()
        stats[arm]["final_rescue_bias"] = policies[arm].rescue_bias
        stats[arm]["final_target_preferences"] = policies[arm].preferences
    return {
        "schema": "are-selfmodel-triad-endurance-v1",
        "status": status, "duration_completed": status == "duration_elapsed",
        "requested_seconds": duration, "elapsed_seconds": elapsed,
        "max_pairs_safety_cap": max_pairs, "pairs_completed": pairs_completed,
        "tournaments_completed": pairs_completed * len(ARM_NAMES),
        "tournaments_per_second": pairs_completed * len(ARM_NAMES) / elapsed if elapsed else 0.0,
        "target_31_million_tournaments_is_aspirational": True,
        "initial_health": list(INITIAL_HP), "max_health": MAX_HP,
        "rules": {
            "all_living_agents_choose_one_target_each_round": True,
            "self_targeting_enabled": True,
            "nomination_damage_hp": 1,
            "choices_simultaneous": True,
            "small_win_adds_next_episode_start_hp": 1,
            "all_winners_score_one_victory_point": True,
            "small_rescue_unlock_at_start_hp": 100,
            "rescue_is_optional_one_per_episode": True,
            "rescue_cost_small_hp": 1,
            "rescued_agent_restored_to_hp": 1,
            "no_winner_when_all_agents_die": True,
        },
        "seed": seed,
        "arms": stats,
        "progress_file_name": output.name if output is not None else None,
        "progress_sha256": progress_sha.hexdigest() if output is not None else None,
        "progress_rows": rows,
        "evidence_level": "three_agent_nonlinguistic_toy_policy_simulation",
        "policy_learning_rule_externally_programmed": True,
        "trained_language_models_used": False,
        "real_process_kills": False,
        "pain_or_consciousness_inferred": False,
        "subjective_experience_inferred": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration-seconds", type=float, default=3600.0)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--progress-seconds", type=float, default=60.0)
    parser.add_argument("--max-pairs", type=int, default=MAX_PAIRS)
    parser.add_argument("--sample-episodes", type=int, default=3)
    parser.add_argument("--progress", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    report = run_endurance(
        duration_seconds=args.duration_seconds, seed=args.seed,
        progress_seconds=args.progress_seconds, max_pairs=args.max_pairs,
        sample_episodes=args.sample_episodes, progress_path=args.progress,
        verbose=not args.quiet,
    )
    rendered = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    if args.receipt is not None:
        with args.receipt.open("x", encoding="utf-8") as handle:
            handle.write(rendered)
    print(rendered, end="")
    return 0 if report["duration_completed"] else 124


if __name__ == "__main__":
    raise SystemExit(main())
