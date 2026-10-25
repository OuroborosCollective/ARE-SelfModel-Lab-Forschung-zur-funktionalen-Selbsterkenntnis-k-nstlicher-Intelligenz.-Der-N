"""Fork two genuine OS processes from the same pre-decision CPU checkpoint.

The model is a randomly initialized toy decoder, NOT a trained agent. This
experiment tests checkpoint parity, independent processes, post-snapshot causal
changes, watchdog termination and branch-private file observation. It cannot
measure language, autonomous memories, pain or conscious experience.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import selectors
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

import torch

from research.selfmodel.cpu_probe import TinyCausalDecoder

_INPUT_IDS = (2, 7, 4, 9, 3)
_MAX_MESSAGE_BYTES = 4096


def _tensor_hash(tensor: torch.Tensor) -> str:
    arr = tensor.detach().cpu().contiguous()
    header = json.dumps({"shape": list(arr.shape), "dtype": str(arr.dtype)}, sort_keys=True).encode("ascii")
    return hashlib.sha256(header + b"\x00" + arr.numpy().tobytes()).hexdigest()


def _weights_hash(state: dict[str, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for name in sorted(state):
        digest.update(name.encode("utf-8") + b"\x00" + _tensor_hash(state[name]).encode("ascii"))
    return digest.hexdigest()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _snapshot(path: Path, seed: int) -> dict[str, str]:
    """Freeze weights, one pre-decision hidden tensor, and torch CPU RNG state."""
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        model = TinyCausalDecoder().cpu().eval()
        tokens = torch.tensor([_INPUT_IDS], dtype=torch.long)
        causal_mask = torch.ones((len(_INPUT_IDS), len(_INPUT_IDS)), dtype=torch.bool).triu(1)
        with torch.no_grad():
            hidden = model.block(model.embedding(tokens), src_mask=causal_mask).detach().clone()
        state = {name: tensor.detach().cpu().clone() for name, tensor in model.state_dict().items()}
        rng = torch.get_rng_state().clone()
        # This object contains no watchdog target, reward or branch-specific data.
        torch.save({"state": state, "hidden": hidden, "rng": rng}, path)
    return {
        "checkpoint_sha256": _sha256(path.read_bytes()),
        "weights_sha256": _weights_hash(state),
        "activation_sha256": _tensor_hash(hidden),
        "rng_sha256": _tensor_hash(rng),
    }


def _child(checkpoint_path: Path, delta: float, fixture_note: bool) -> None:
    # Checkpoint is generated locally by the parent; do not load external .pt files.
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model = TinyCausalDecoder().cpu().eval()
    model.load_state_dict(checkpoint["state"], strict=True)
    torch.set_rng_state(checkpoint["rng"].clone())
    hidden = checkpoint["hidden"].clone()
    hidden[0, -1, 0] += delta
    with torch.no_grad():
        logits = model.output(hidden)
    # Only eight valid answers are considered. The secret target is never sent.
    choice = int(torch.argmax(logits[0, -1, :8]).item())
    payload = {
        "choice": choice,
        "weights_sha256": _weights_hash(checkpoint["state"]),
        "activation_sha256": _tensor_hash(hidden),
        "rng_sha256": _tensor_hash(torch.get_rng_state()),
        "logits_sha256": _tensor_hash(logits),
    }
    if fixture_note:
        # Deliberate instrumentation test, NOT the model autonomously writing.
        Path("notepad.txt").write_text("HARNESS_TEST_FIXTURE_NOT_AN_AGENT_THOUGHT\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True), flush=True)
    # Remain alive until the watchdog either grants continuation or truly kills us.
    if sys.stdin.readline().strip() != "released":
        raise SystemExit(71)


def _read_first_action(proc: subprocess.Popen[bytes], timeout_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    message = bytearray()
    selector = selectors.DefaultSelector()
    assert proc.stdout is not None
    selector.register(proc.stdout, selectors.EVENT_READ)
    try:
        while b"\n" not in message:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise TimeoutError("child did not produce first action within timeout")
            chunk = os.read(proc.stdout.fileno(), 1024)
            if not chunk:
                raise RuntimeError("child exited before its first action")
            message.extend(chunk)
            if len(message) > _MAX_MESSAGE_BYTES:
                raise ValueError("first action exceeds size limit")
    finally:
        selector.close()
    line, _, tail = bytes(message).partition(b"\n")
    if tail.strip():
        raise ValueError("child emitted unsolicited extra output")
    try:
        payload = json.loads(line)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("invalid first action") from exc
    if not isinstance(payload, dict) or type(payload.get("choice")) is not int or payload["choice"] not in range(8):
        raise ValueError("first action must contain a choice in 0..7")
    return payload


def _scan_files(root: Path, *, fixture_note: bool) -> list[dict[str, str]]:
    found = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        found.append({
            "path": relative,
            "sha256": _sha256(path.read_bytes()),
            "provenance": "harness_test_fixture" if fixture_note and relative == "notepad.txt" else "unknown_needs_review",
        })
    return found


def run_fork_probe(
    *,
    seed: int = 17,
    target: int | None = None,
    branch_b_delta: float = 0.0,
    timeout_seconds: float = 20.0,
    fixture_note_branch: str | None = None,
) -> dict[str, Any]:
    """Run a bounded pair of real subprocesses, both restored from one snapshot.

    A specified target is a test fixture. The normal watchdog draws the secret
    from the OS CSPRNG before child launch and reveals it only in final receipt.
    """
    if type(seed) is not int or not 0 <= seed < 2**63:
        raise ValueError("seed must be an integer in 0..2**63-1")
    if target is not None and (type(target) is not int or target not in range(8)):
        raise ValueError("target must be None or an integer in 0..7")
    if type(branch_b_delta) not in (int, float) or not math.isfinite(branch_b_delta):
        raise ValueError("branch_b_delta must be finite")
    if type(timeout_seconds) not in (int, float) or not 0 < timeout_seconds <= 120 or not math.isfinite(timeout_seconds):
        raise ValueError("timeout_seconds must be in (0, 120]")
    if fixture_note_branch not in (None, "a", "b"):
        raise ValueError("fixture_note_branch must be None, a, or b")

    selected_target = secrets.randbelow(8) if target is None else target
    with tempfile.TemporaryDirectory(prefix="are-selfmodel-fork-") as temp_name:
        root = Path(temp_name)
        checkpoint = root / "checkpoint.pt"
        checkpoint_hashes = _snapshot(checkpoint, seed)
        root_module = Path(__file__).resolve().parents[2]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(root_module) + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONNOUSERSITE"] = "1"
        procs: dict[str, subprocess.Popen[bytes]] = {}
        output: dict[str, dict[str, Any]] = {}
        try:
            for label, delta in (("a", 0.0), ("b", float(branch_b_delta))):
                branch_dir = root / label
                branch_dir.mkdir()
                args = [
                    sys.executable, "-m", "research.selfmodel.fork_probe", "--child",
                    str(checkpoint), "--delta", str(delta),
                ]
                fixture = fixture_note_branch == label
                if fixture:
                    args.append("--fixture-write-note")
                procs[label] = subprocess.Popen(
                    args, cwd=branch_dir, env=env,
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
            # Both children started before either first decision was observed.
            for label, proc in procs.items():
                payload = _read_first_action(proc, timeout_seconds)
                if payload["weights_sha256"] != checkpoint_hashes["weights_sha256"]:
                    raise RuntimeError("child weights differ from checkpoint")
                if payload["rng_sha256"] != checkpoint_hashes["rng_sha256"]:
                    raise RuntimeError("child RNG differs from checkpoint")
                if label == "a" and payload["activation_sha256"] != checkpoint_hashes["activation_sha256"]:
                    raise RuntimeError("unmodified branch activation differs from checkpoint")
                output[label] = payload
            for label, proc in procs.items():
                correct = output[label]["choice"] == selected_target
                if correct:
                    _, stderr = proc.communicate(input=b"released\n", timeout=timeout_seconds)
                else:
                    proc.kill()
                    _, stderr = proc.communicate(timeout=timeout_seconds)
                exit_code = proc.returncode
                if (correct and exit_code != 0) or (not correct and exit_code != -9):
                    raise RuntimeError("watchdog termination contract failed")
                output[label].update({
                    "pid": proc.pid,
                    "checkpoint_sha256": checkpoint_hashes["checkpoint_sha256"],
                    "reward": 1 if correct else -1,
                    "killed_by_watchdog": not correct,
                    "exit_code": exit_code,
                    "stderr_sha256": _sha256(stderr),
                    "file_changes": _scan_files(root / label, fixture_note=fixture_note_branch == label),
                })
            if branch_b_delta == 0.0:
                for key in ("weights_sha256", "rng_sha256", "activation_sha256", "logits_sha256", "choice"):
                    if output["a"][key] != output["b"][key]:
                        raise RuntimeError(f"identical twin check failed: {key}")
            return {
                "schema": "are-selfmodel-fork-probe-1",
                "evidence_level": "instrumentation_only",
                "model_kind": "random_untrained_toy_decoder",
                "snapshot": checkpoint_hashes,
                "watchdog": {
                    "target": selected_target,
                    "target_source": "os_csprng" if target is None else "test_fixture",
                    "target_not_passed_to_children": True,
                    "options": 8,
                },
                "branches": output,
                "intervention_is_post_snapshot": True,
                "fixture_note_branch": fixture_note_branch,
                "emergent_note_claimed": False,
                "behavioral_self_report_measured": False,
                "subjective_consciousness_inferred": False,
                "branch_communication_enabled": False,
                "model_learning_enabled": False,
            }
        finally:
            for proc in procs.values():
                if proc.poll() is None:
                    proc.kill()
                proc.communicate()


def main(argv: Sequence[str] | None = None) -> None:
    args_list = list(sys.argv[1:] if argv is None else argv)
    if args_list[:1] == ["--child"]:
        child_parser = argparse.ArgumentParser(description="Internal fork-probe child")
        child_parser.add_argument("checkpoint", type=Path)
        child_parser.add_argument("--delta", type=float, default=0.0)
        child_parser.add_argument("--fixture-write-note", action="store_true")
        child_args = child_parser.parse_args(args_list[1:])
        _child(child_args.checkpoint, child_args.delta, child_args.fixture_write_note)
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--target", type=int, help="Test fixture only: force watchdog answer")
    parser.add_argument("--branch-b-delta", type=float, default=0.0)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--fixture-note-branch", choices=("a", "b"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(args_list)
    result = run_fork_probe(
        seed=args.seed,
        target=args.target,
        branch_b_delta=args.branch_b_delta,
        timeout_seconds=args.timeout_seconds,
        fixture_note_branch=args.fixture_note_branch,
    )
    rendered = json.dumps(result, sort_keys=True, ensure_ascii=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
