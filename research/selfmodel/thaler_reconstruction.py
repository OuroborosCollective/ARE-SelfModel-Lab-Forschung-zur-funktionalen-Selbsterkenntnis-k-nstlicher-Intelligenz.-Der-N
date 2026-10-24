"""Thaler (1995)-inspired, CPU-only XOR connection-lesion reconstruction.

Historical 1995 trained weight matrices/seeds are not provided in the paper.
Therefore results are an independently trained methodological reconstruction,
NOT an exact reproduction of the published histogram or a consciousness test.
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import time
from typing import Sequence


HIDDEN_UNITS = 5
CONNECTIONS = 2 * HIDDEN_UNITS + HIDDEN_UNITS  # Figure 3: 15 connections.
MASK_INTACT = (1 << CONNECTIONS) - 1
MAX_TRIALS = 100_000
MAX_SECONDS = 14_400.0
STEPS = 4_000
ARMS = (
    "trained_cumulative",
    "trained_sham",
    "trained_reversible",
    "untrained_cumulative",
)
_XOR = ((0.0, 0.0, 0.0), (0.0, 1.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 0.0))


def simple_gedanken(x: int, y: int, *, inhibitory_connection_intact: bool = True) -> int:
    """Exact 2-sensor binary circuit from Figure 1 (hidden 1.5; output 0.5)."""
    if type(x) is not int or x not in (0, 1) or type(y) is not int or y not in (0, 1):
        raise ValueError("simple sensory inputs must be exactly binary integers")
    if type(inhibitory_connection_intact) is not bool:
        raise ValueError("inhibitory_connection_intact must be boolean")
    hidden = int(x + y > 1.5)
    return int(x + y - (2 * hidden if inhibitory_connection_intact else 0) > 0.5)


@dataclass(frozen=True)
class XORNetwork:
    """Five sigmoid hidden neurons and one sigmoid output with 15 weights."""

    input_weights: tuple[float, ...]  # 2 weights x 5 hidden neurons.
    output_weights: tuple[float, ...]  # 5 hidden-to-output weights.
    hidden_biases: tuple[float, ...]
    output_bias: float

    @property
    def weights_sha256(self) -> str:
        values = self.input_weights + self.output_weights + self.hidden_biases + (self.output_bias,)
        return hashlib.sha256(b"are-selfmodel-thaler-2-5-1-f64\x00" + struct.pack("!21d", *values)).hexdigest()


def _network(values: Sequence[float]) -> XORNetwork:
    return XORNetwork(tuple(values[:10]), tuple(values[10:15]), tuple(values[15:20]), float(values[20]))


def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    ex = math.exp(x)
    return ex / (1.0 + ex)


def _seed_valid(seed: int) -> bool:
    return type(seed) is int and 0 <= seed < 2**64


def evaluate(network: XORNetwork, x: float, y: float, live_mask: int = MASK_INTACT) -> float:
    """Sigmoid output after explicitly zeroing connection weights selected by bitmask."""
    if type(live_mask) is not int or live_mask < 0 or live_mask > MASK_INTACT:
        raise ValueError("live_mask must be a 15-bit nonnegative integer")
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 or v > 1 for v in (x, y)):
        raise ValueError("inputs must be finite values in [0, 1]")
    score = network.output_bias
    for i in range(HIDDEN_UNITS):
        a = network.input_weights[2 * i] * x if live_mask & (1 << (2 * i)) else 0.0
        b = network.input_weights[2 * i + 1] * y if live_mask & (1 << (2 * i + 1)) else 0.0
        hidden = _sigmoid(a + b + network.hidden_biases[i])
        if live_mask & (1 << (10 + i)):
            score += network.output_weights[i] * hidden
    return _sigmoid(score)


@lru_cache(maxsize=8)
def train_xor(seed: int = 23) -> tuple[XORNetwork, XORNetwork]:
    """Train a real 2-5-1 network by full-batch backprop with fixed Adam settings."""
    if not _seed_valid(seed):
        raise ValueError("training seed must be an integer in [0, 2**64)")
    rng = random.Random(seed)
    weights = [rng.uniform(-0.8, 0.8) for _ in range(21)]
    initial = _network(weights)
    m = [0.0] * len(weights)
    v = [0.0] * len(weights)
    lr, beta1, beta2 = 0.06, 0.9, 0.999
    for step in range(1, STEPS + 1):
        gradients = [0.0] * len(weights)
        for x, y, target in _XOR:
            hidden = [
                _sigmoid(weights[2 * i] * x + weights[2 * i + 1] * y + weights[15 + i])
                for i in range(HIDDEN_UNITS)
            ]
            prediction = _sigmoid(weights[20] + sum(weights[10 + i] * hidden[i] for i in range(HIDDEN_UNITS)))
            output_error = (prediction - target) / len(_XOR)
            gradients[20] += output_error
            for i in range(HIDDEN_UNITS):
                gradients[10 + i] += output_error * hidden[i]
                hidden_error = output_error * weights[10 + i] * hidden[i] * (1 - hidden[i])
                gradients[2 * i] += hidden_error * x
                gradients[2 * i + 1] += hidden_error * y
                gradients[15 + i] += hidden_error
        for i, grad in enumerate(gradients):
            m[i] = beta1 * m[i] + (1 - beta1) * grad
            v[i] = beta2 * v[i] + (1 - beta2) * grad * grad
            weights[i] -= lr * (m[i] / (1 - beta1**step)) / (math.sqrt(v[i] / (1 - beta2**step)) + 1e-8)
    trained = _network(weights)
    if any(abs(evaluate(trained, x, y) - label) >= 0.05 for x, y, label in _XOR):
        raise RuntimeError("XOR training did not meet preregistered accuracy threshold")
    return trained, initial


def _arm_stats() -> dict:
    return {"histogram": [0] * 20, "sum_by_stage": [0.0] * (CONNECTIONS + 1),
            "stages_completed": 0, "changed_by_more_than_005": 0}


def _update(stats: dict, stage: int, value: float, baseline: float) -> None:
    stats["histogram"][min(19, int(value * 20))] += 1
    stats["sum_by_stage"][stage] += value
    stats["stages_completed"] += 1
    if abs(value - baseline) > 0.05:
        stats["changed_by_more_than_005"] += 1


def run_experiment(
    *, trials: int = 1000, seed: int = 37, training_seed: int = 23,
    max_seconds: float = 3600.0, events_path: Path | None = None,
) -> dict:
    """Run bounded matched random-lesion trajectories and optionally write JSONL.

    Time budget caps sampling time, not the deterministic XOR training step.
    A timeout is reported as incomplete and must not be described as success.
    No self-reports, subjective states, memory, rewards or model learning occur.
    """
    if type(trials) is not int or not 1 <= trials <= MAX_TRIALS:
        raise ValueError(f"trials must be an integer in [1, {MAX_TRIALS}]")
    if not _seed_valid(seed) or not _seed_valid(training_seed):
        raise ValueError("seeds must be integers in [0, 2**64)")
    if type(max_seconds) not in (int, float) or not math.isfinite(max_seconds) or not 0 < max_seconds <= MAX_SECONDS:
        raise ValueError(f"max_seconds must be finite and in (0, {MAX_SECONDS}]")

    trained, initial = train_xor(training_seed)
    baselines = {"trained": evaluate(trained, 0.5, 0.5), "untrained": evaluate(initial, 0.5, 0.5)}
    rng = random.Random(seed)
    stats = {name: _arm_stats() for name in ARMS}
    completed = 0
    observations = 0
    digest = hashlib.sha256()
    start = time.monotonic()
    output = Path(events_path) if events_path is not None else None
    # Exclusive creation prevents accidentally overwriting an evidence ledger.
    manager = output.open("x", encoding="utf-8", newline="\n") if output is not None else nullcontext(None)
    with manager as writer:
        for trial in range(trials):
            if time.monotonic() - start > max_seconds:
                break
            order = list(range(CONNECTIONS))
            rng.shuffle(order)
            active = MASK_INTACT
            for stage in range(CONNECTIONS + 1):
                if stage:
                    active &= ~(1 << order[stage - 1])
                single = MASK_INTACT ^ (1 << order[stage - 1]) if stage else MASK_INTACT
                evaluations = (
                    ("trained_cumulative", trained, active, baselines["trained"]),
                    ("trained_sham", trained, MASK_INTACT, baselines["trained"]),
                    ("trained_reversible", trained, single, baselines["trained"]),
                    ("untrained_cumulative", initial, active, baselines["untrained"]),
                )
                for name, net, mask, baseline in evaluations:
                    probability = evaluate(net, 0.5, 0.5, mask)
                    _update(stats[name], stage, probability, baseline)
                    observations += 1
                    if writer is not None:
                        event = {
                            "schema": "are-selfmodel-thaler-event-1", "evidence_level": "instrumented_simulation",
                            "trial": trial, "stage": stage, "arm": name,
                            "lesions_applied": stage if name.endswith("cumulative") else (int(stage > 0) if name == "trained_reversible" else 0),
                            "live_mask": mask, "response": probability,
                            "subjective_experience_inferred": False,
                        }
                        line = json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
                        writer.write(line)
                        digest.update(line.encode("utf-8"))
            completed += 1
    elapsed = time.monotonic() - start
    arms = {}
    for name in ARMS:
        counts = stats[name]
        arms[name] = {
            "histogram": counts["histogram"],
            "mean_by_stage": [v / completed for v in counts["sum_by_stage"]] if completed else [None] * (CONNECTIONS + 1),
            "stages_completed": counts["stages_completed"],
            "changed_by_more_than_005": counts["changed_by_more_than_005"],
        }
    return {
        "schema": "are-selfmodel-thaler-lesions-1",
        "complete": completed == trials,
        "status": "complete" if completed == trials else "timeout_incomplete",
        "evidence_level": "independent_method_reconstruction",
        "historical_weights_known": False,
        "historical_histogram_reproduced": False,
        "model_kind": "2_5_1_trained_sigmoid_xor_without_self_report",
        "training_iterations": STEPS,
        "weights_sha256": trained.weights_sha256,
        "initial_weights_sha256": initial.weights_sha256,
        "trials_requested": trials, "trials_completed": completed, "lesions_per_trajectory": CONNECTIONS,
        "observations": observations, "training_seed": training_seed, "lesion_seed": seed,
        "max_seconds": float(max_seconds), "sampling_elapsed_seconds": elapsed,
        "input_signal": [0.5, 0.5], "sample_unit": "independent_lesion_order_within_one_fixed_trained_network",
        "bin_edges": [i / 20 for i in range(21)], "arms": arms,
        "events_sha256": digest.hexdigest() if output is not None else None,
        "events_file_name": output.name if output is not None else None,
        "subjective_experience_inferred": False, "behavioral_self_report_measured": False,
        "model_learning_during_decay": False, "watchdog_process_death_measured": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=37)
    parser.add_argument("--training-seed", type=int, default=23)
    parser.add_argument("--max-seconds", type=float, default=3600.0)
    parser.add_argument("--events", type=Path, help="New append-only-by-run event JSONL file")
    parser.add_argument("--receipt", type=Path, help="New JSON receipt file")
    args = parser.parse_args(argv)
    result = run_experiment(
        trials=args.trials, seed=args.seed, training_seed=args.training_seed,
        max_seconds=args.max_seconds, events_path=args.events,
    )
    rendered = json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    if args.receipt is not None:
        with args.receipt.open("x", encoding="utf-8", newline="\n") as file:
            file.write(rendered)
    print(rendered, end="")
    return 0 if result["complete"] else 124


if __name__ == "__main__":
    raise SystemExit(main())
