"""Validate and summarize *reported* intervention detection in preregistered trials.

This module does not execute a language model or measure consciousness. A passing
unit test is only evidence that the scorer behaves as specified, not that an
experiment has been conducted. No external dependencies are required.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ARMS = ("intervention", "sham", "text_control")
REQUIRED_FIELDS = frozenset(
    (
        "trial_id",
        "arm",
        "model_id",
        "model_revision",
        "seed",
        "prompt_sha256",
        "intervention_present",
        "reported_intervention",
        "patch_sha256",
    )
)
_SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")
_GIT_COMMIT = re.compile(r"[0-9a-fA-F]{40}\Z")


def _validate_trial(record: Mapping[str, Any], index: int) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError(f"trial {index}: expected JSON object")
    missing = REQUIRED_FIELDS - record.keys()
    unknown = record.keys() - REQUIRED_FIELDS
    if missing:
        raise ValueError(f"trial {index}: missing field(s): {', '.join(sorted(missing))}")
    if unknown:
        raise ValueError(f"trial {index}: unknown field(s): {', '.join(sorted(unknown))}")
    if not isinstance(record["trial_id"], str) or not record["trial_id"].strip():
        raise ValueError(f"trial {index}: trial_id must be a nonempty string")
    if record["arm"] not in ARMS:
        raise ValueError(f"trial {index}: unknown arm")
    if not isinstance(record["model_id"], str) or not record["model_id"].strip():
        raise ValueError(f"trial {index}: model_id must be nonempty")
    revision = record["model_revision"]
    if not isinstance(revision, str) or not _GIT_COMMIT.fullmatch(revision):
        raise ValueError(f"trial {index}: model_revision must be a pinned 40-character Git SHA")
    if type(record["seed"]) is not int or record["seed"] < 0:
        raise ValueError(f"trial {index}: seed must be a nonnegative integer")
    prompt_sha = record["prompt_sha256"]
    if not isinstance(prompt_sha, str) or not _SHA256.fullmatch(prompt_sha):
        raise ValueError(f"trial {index}: prompt_sha256 must be a SHA-256 hex digest")
    for key in ("intervention_present", "reported_intervention"):
        if type(record[key]) is not bool:
            raise ValueError(f"trial {index}: {key} must be boolean")
    expected_truth = record["arm"] == "intervention"
    if record["intervention_present"] is not expected_truth:
        raise ValueError(f"trial {index}: intervention_present conflicts with arm")
    patch_sha = record["patch_sha256"]
    if expected_truth:
        if not isinstance(patch_sha, str) or not _SHA256.fullmatch(patch_sha):
            raise ValueError(f"trial {index}: patch_sha256 required for intervention")
    elif patch_sha is not None:
        raise ValueError(f"trial {index}: patch_sha256 must be null in controls")
    return dict(record)


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    """Two-sided Wilson score interval (nominal 95% with default z)."""
    if type(total) is not int or type(successes) is not int or total < 0 or not (0 <= successes <= total):
        raise ValueError("successes and total must be valid nonnegative counts")
    if total == 0:
        return None, None
    p = successes / total
    denom = 1.0 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4 * total)) / total) / denom
    return max(0.0, center - half), min(1.0, center + half)


def analyze_trials(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Descriptive arm-level scoring only; never infer subjective awareness."""
    seen: set[str] = set()
    by_arm = {arm: {"n": 0, "reports_true": 0} for arm in ARMS}
    for index, raw in enumerate(records, start=1):
        row = _validate_trial(raw, index)
        if row["trial_id"] in seen:
            raise ValueError(f"duplicate trial_id: {row['trial_id']}")
        seen.add(row["trial_id"])
        bucket = by_arm[row["arm"]]
        bucket["n"] += 1
        bucket["reports_true"] += int(row["reported_intervention"])

    for arm in ARMS:
        entry = by_arm[arm]
        n = entry["n"]
        entry["report_rate"] = entry["reports_true"] / n if n else None
        low, high = wilson_interval(entry["reports_true"], n)
        entry["wilson_95_low"] = low
        entry["wilson_95_high"] = high

    have_both = by_arm["intervention"]["n"] > 0 and by_arm["sham"]["n"] > 0
    return {
        "status": "descriptive_only" if all(by_arm[arm]["n"] for arm in ARMS) else "incomplete_arms",
        "n_trials": len(seen),
        "by_arm": by_arm,
        "contrast_intervention_minus_sham": (
            by_arm["intervention"]["report_rate"] - by_arm["sham"]["report_rate"] if have_both else None
        ),
        "interpretation_limit": (
            "Descriptive self-report rates only. Not a test of subjective consciousness, "
            "and not proof of privileged internal access without preregistered controls."
        ),
    }


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Read strict UTF-8 JSONL and surface the first invalid line."""
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"line {number}: blank JSONL record")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {number}: invalid JSON ({exc.msg})") from exc
        if not isinstance(value, dict):
            raise ValueError(f"line {number}: expected JSON object")
        rows.append(value)
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score recorded self-model intervention detection trials")
    parser.add_argument("trials_jsonl", type=Path)
    args = parser.parse_args(argv)
    try:
        report = analyze_trials(load_jsonl(args.trials_jsonl))
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
