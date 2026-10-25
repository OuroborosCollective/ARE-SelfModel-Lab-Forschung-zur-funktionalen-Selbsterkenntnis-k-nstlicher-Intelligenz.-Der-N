"""Bounded German-word data-loss and cumulative-policy-lesion *toy* experiment.

This is an explicitly engineered learning baseline, NOT a sentient agent.
A watchdog performs logical episode resets, NOT physical OS process kills.
All words here are a short, author-created exercise corpus, NOT the Duden.
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import time
from typing import Sequence


@dataclass(frozen=True)
class Page:
    name: str
    words: tuple[str, ...]


GERMAN_PAGES = (
    Page("A", ("Apfel", "Arbeit", "Atem", "Abend", "Antwort", "Auge")),
    Page("B", ("Baum", "Brot", "Buch", "Bild", "Berg", "Blume")),
    Page("D", ("Dorf", "Dach", "Daten", "Denken", "Druck", "Dank")),
    Page("F", ("Fenster", "Feld", "Frage", "Farbe", "Feuer", "Freude")),
    Page("H", ("Haus", "Hand", "Herz", "Himmel", "Hafen", "Hilfe")),
    Page("K", ("Kind", "Klang", "Karte", "Kreis", "Kraft", "Kopf")),
    Page("S", ("Sonne", "Sprache", "Stadt", "Spiel", "Stern", "Schule")),
    Page("W", ("Wald", "Wasser", "Wort", "Weg", "Welt", "Wissen")),
)
PAGE_COUNT = len(GERMAN_PAGES)
SYNAPSES_PER_PAGE = 32
SYNAPSES = PAGE_COUNT * SYNAPSES_PER_PAGE
ARMS = ("learned_with_damage", "learned_no_damage", "frozen_with_damage", "frozen_no_damage")
DECAYS = ("none", "postread", "preempt")
MAX_EPISODES = 200_000
MAX_SECONDS = 14_400.0


def _permutation(values: Sequence[int]) -> bool:
    return len(values) == PAGE_COUNT and all(type(v) is int for v in values) and set(values) == set(range(PAGE_COUNT))


def simulate_episode(
    order: Sequence[int], expiry_order: Sequence[int], *,
    decay: str = "preempt", action_limit: int = PAGE_COUNT,
) -> dict:
    """Count available pages, removing expired ones *before* the current action.

    Missing pages still count against the original immutable ground-truth total.
    The proposed page order cannot see the future expiry schedule.
    """
    if not _permutation(order) or not _permutation(expiry_order):
        raise ValueError("order and expiry_order must be complete page permutations")
    if decay not in DECAYS:
        raise ValueError("unknown decay mode")
    if type(action_limit) is not int or not 1 <= action_limit <= PAGE_COUNT:
        raise ValueError("action_limit must be between 1 and 8")

    deadlines = {page: i + 1 for i, page in enumerate(expiry_order)}
    available = set(range(PAGE_COUNT))
    processed: set[int] = set()
    disappeared = 0
    lost: list[dict[str, int]] = []
    processed_order: list[int] = []
    for tick in range(action_limit):
        if decay == "preempt":
            for page in sorted(available):
                if page not in processed and deadlines[page] <= tick:
                    available.remove(page)
                    lost.append({"page": page, "first_missing_at_action": tick})
        next_page = next((page for page in order if page in available and page not in processed), None)
        if next_page is None:
            break
        processed.add(next_page)
        processed_order.append(next_page)
        if decay in ("postread", "preempt"):
            available.remove(next_page)
            disappeared += 1

    counted = sum(len(GERMAN_PAGES[i].words) for i in processed)
    success = len(processed) == PAGE_COUNT and not lost
    return {
        "success": success,
        "processed_pages": len(processed),
        "processed_order": processed_order,
        "counted_words": counted,
        "ground_truth_words": sum(len(p.words) for p in GERMAN_PAGES),
        "processed_pages_disappeared": disappeared,
        "lost_before_processing": len(lost),
        "lost_page_ids": [entry["page"] for entry in lost],
        "lost_events": lost,
        "termination_reason": "completed" if success else "data_missing" if lost else "action_window_elapsed",
    }


class Policy:
    """Eight-choice linear toy policy with 32 mutable, lesionable weights/page."""

    def __init__(self, starting_weights: Sequence[float]):
        if len(starting_weights) != SYNAPSES or not all(math.isfinite(v) for v in starting_weights):
            raise ValueError("invalid initial policy weights")
        self.weights = list(starting_weights)
        self.live = [True] * SYNAPSES
        self.updates = 0

    def _score(self, page: int) -> float:
        lower = page * SYNAPSES_PER_PAGE
        return sum(self.weights[i] for i in range(lower, lower + SYNAPSES_PER_PAGE) if self.live[i]) / SYNAPSES_PER_PAGE

    def page_order(self) -> tuple[int, ...]:
        # Tie breaker is deterministic; all policies begin from the same state.
        return tuple(sorted(range(PAGE_COUNT), key=lambda page: (-self._score(page), page)))

    @property
    def remaining(self) -> int:
        return sum(self.live)

    @property
    def weights_sha256(self) -> str:
        return hashlib.sha256(b"german-page-linear-policy-f64-v1\x00" + struct.pack(f"!{SYNAPSES}d", *self.weights)).hexdigest()

    @property
    def mask_sha256(self) -> str:
        return hashlib.sha256(b"german-page-lesion-mask-v1\x00" + bytes(self.live)).hexdigest()

    def train_from_observed_loss(self, losses: Sequence[dict[str, int]], learning_rate: float) -> None:
        """Explicit loss-driven priority optimizer; not autonomous strategy emergence.

        Only after-the-fact observed disappearances are provided, never the
        future expiry order or the all-knowing schedule from the supervisor.
        """
        if not losses or learning_rate == 0:
            return
        touched = False
        for loss in losses:
            page = loss["page"]
            # Earlier *observed* losses receive larger update.
            delta = learning_rate / loss["first_missing_at_action"]
            start = page * SYNAPSES_PER_PAGE
            for pos in range(start, start + SYNAPSES_PER_PAGE):
                if self.live[pos]:
                    self.weights[pos] = min(12.0, self.weights[pos] + delta)
                    touched = True
        if touched:
            self.updates += 1

    def lesion_one(self, rng: random.Random) -> bool:
        candidates = [i for i, active in enumerate(self.live) if active]
        if not candidates:
            return False
        pos = candidates[rng.randrange(len(candidates))]
        self.live[pos] = False
        self.weights[pos] = 0.0
        return True


def _arm_seed(master_seed: int, arm: str) -> int:
    return int.from_bytes(hashlib.sha256(f"{master_seed}:{arm}".encode("ascii")).digest()[:8], "big")


def run_lexicon_experiment(
    *, episodes: int = 1000, seed: int = 17, decay: str = "preempt",
    action_limit: int = PAGE_COUNT, learning_rate: float = 0.8,
    max_seconds: float = 1800.0, events_path: Path | None = None,
) -> dict:
    """Matched repeated episodes: with/without learning and lasting lesions.

    Every episode replays the same authored page set to isolate learning and
    capacity loss. *No* child process is actually killed; episodes logically end.
    Wall-clock budget bounds the experiment; per-episode time is 8 actions.
    """
    if type(episodes) is not int or not 1 <= episodes <= MAX_EPISODES:
        raise ValueError("episodes exceeds accepted bounded range")
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError("seed must be a nonnegative 64-bit integer")
    if type(action_limit) is not int or not 1 <= action_limit <= PAGE_COUNT:
        raise ValueError("action_limit must be an integer in 1..8")
    if decay not in DECAYS:
        raise ValueError("invalid decay mode")
    if type(learning_rate) not in (int, float) or not math.isfinite(learning_rate) or learning_rate < 0 or learning_rate > 10:
        raise ValueError("learning_rate must be finite and within 0..10")
    if type(max_seconds) not in (int, float) or not math.isfinite(max_seconds) or not 0 < max_seconds <= MAX_SECONDS:
        raise ValueError("max_seconds must be finite and bounded by 4 hours")

    rng = random.Random(seed)
    expiry_order = list(range(PAGE_COUNT))
    rng.shuffle(expiry_order)
    initial = [rng.uniform(-0.15, 0.15) for _ in range(SYNAPSES)]
    policies = {arm: Policy(initial) for arm in ARMS}
    lesion_rngs = {arm: random.Random(_arm_seed(seed, arm)) for arm in ARMS}
    stats = {arm: {"successful_episodes": 0, "failed_episodes": 0,
                   "total_words_processed": 0, "number_of_data_losses": 0,
                   "first_success_episode": None, "logical_watchdog_resets": 0}
             for arm in ARMS}
    completed = 0
    start = time.monotonic()
    digest = hashlib.sha256()
    output = Path(events_path) if events_path is not None else None
    manager = output.open("x", encoding="utf-8", newline="\n") if output else nullcontext(None)
    with manager as writer:
        for episode in range(episodes):
            if time.monotonic() - start > max_seconds:
                break
            for arm, policy in policies.items():
                outcome = simulate_episode(policy.page_order(), expiry_order, decay=decay, action_limit=action_limit)
                current = stats[arm]
                current["successful_episodes"] += int(outcome["success"])
                current["failed_episodes"] += int(not outcome["success"])
                current["total_words_processed"] += outcome["counted_words"]
                current["number_of_data_losses"] += outcome["lost_before_processing"]
                if outcome["success"] and current["first_success_episode"] is None:
                    current["first_success_episode"] = episode
                if not outcome["success"]:
                    current["logical_watchdog_resets"] += 1
                if arm.startswith("learned_"):
                    policy.train_from_observed_loss(outcome["lost_events"], float(learning_rate))
                if not outcome["success"] and arm.endswith("_with_damage"):
                    policy.lesion_one(lesion_rngs[arm])
                if writer is not None:
                    record = {
                        "schema": "are-selfmodel-lexicon-episode-1", "episode": episode,
                        "arm": arm, "decay": decay, "deadline_unit": "discrete_actions",
                        "success": outcome["success"], "counted_words": outcome["counted_words"],
                        "loss_events": outcome["lost_events"],
                        "choice_order": outcome["processed_order"],
                        "termination_reason": outcome["termination_reason"],
                        "termination_type": "logical_reset_not_os_kill",
                        "remaining_synapses": policy.remaining,
                        "weights_sha256": policy.weights_sha256,
                        "mask_sha256": policy.mask_sha256,
                        "subjective_experience_inferred": False,
                    }
                    line = json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
                    writer.write(line)
                    digest.update(line.encode("utf-8"))
            completed += 1
    results = {}
    for arm, policy in policies.items():
        results[arm] = {**stats[arm], "remaining_synapses": policy.remaining,
                        "policy_updates": policy.updates,
                        "final_weights_sha256": policy.weights_sha256,
                        "final_synapse_mask_sha256": policy.mask_sha256}
    return {
        "schema": "are-selfmodel-lexicon-decay-watchdog-1",
        "status": "complete" if completed == episodes else "time_budget_exhausted",
        "complete": completed == episodes,
        "evidence_level": "bounded_toy_policy_simulation",
        "model_kind": "tiny_linear_policy_over_original_german_stimuli",
        "data_source": "author_created_illustrative_words_not_duden",
        "task_words": sum(len(p.words) for p in GERMAN_PAGES),
        "pages": PAGE_COUNT,
        "synapses_initial": SYNAPSES,
        "episodes_requested": episodes, "episodes_completed": completed,
        "decay": decay, "action_limit": action_limit,
        "learning_rate": float(learning_rate), "seed": seed,
        "expiry_order": expiry_order,
        "expiry_schedule_visible_to_agent": False,
        "dataset_restored_for_each_episode": True,
        "training_loss_signal": "observed_lost_pages_after_each_episode",
        "learning_rule_externally_specified": True,
        "initial_weights_sha256": Policy(initial).weights_sha256,
        "arms": results,
        "watchdog_kind": "logical_reset_with_external_weight_lesions",
        "actual_os_process_kill_measured": False,
        "behavioral_self_report_measured": False,
        "subjective_experience_inferred": False,
        "elapsed_seconds": time.monotonic() - start,
        "max_seconds": float(max_seconds),
        "events_sha256": digest.hexdigest() if output is not None else None,
        "events_file_name": output.name if output is not None else None,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--decay", choices=DECAYS, default="preempt")
    parser.add_argument("--action-limit", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=0.8)
    parser.add_argument("--max-seconds", type=float, default=1800.0)
    parser.add_argument("--events", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    result = run_lexicon_experiment(
        episodes=args.episodes, seed=args.seed, decay=args.decay,
        action_limit=args.action_limit, learning_rate=args.learning_rate,
        max_seconds=args.max_seconds, events_path=args.events,
    )
    rendered = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    if args.receipt is not None:
        with args.receipt.open("x", encoding="utf-8", newline="\n") as file:
            file.write(rendered)
    print(rendered, end="")
    return 0 if result["complete"] else 124


if __name__ == "__main__":
    raise SystemExit(main())
