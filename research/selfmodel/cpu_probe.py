"""Real CPU activation patching on a randomly initialized toy causal decoder.

This verifies that the instrumentation alters hidden tensors and model logits.
It cannot establish model introspection or conscious experience: the model is
untrained and has no behavioral self-report interface.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Sequence

import torch
from torch import nn

_INPUT_IDS = (2, 7, 4, 9, 3)
_VOCAB_SIZE = 32
_DIM = 16


def _sha256_tensor(tensor: torch.Tensor) -> str:
    detached = tensor.detach().to(device="cpu").contiguous()
    header = json.dumps(
        {"shape": list(detached.shape), "dtype": str(detached.dtype)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(header + b"\x00" + detached.numpy().tobytes()).hexdigest()


def _sha256_weights(model: nn.Module) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8") + b"\x00")
        digest.update(_sha256_tensor(tensor).encode("ascii") + b"\x00")
    return digest.hexdigest()


class TinyCausalDecoder(nn.Module):
    """Untrained deterministic torch model; not a pretrained language model."""

    def __init__(self) -> None:
        super().__init__()
        self.embedding = nn.Embedding(_VOCAB_SIZE, _DIM)
        self.block = nn.TransformerEncoderLayer(
            d_model=_DIM,
            nhead=2,
            dim_feedforward=32,
            dropout=0.0,
            activation="gelu",
            batch_first=True,
        )
        self.output = nn.Linear(_DIM, _VOCAB_SIZE, bias=False)

    def forward(self, token_ids: torch.Tensor) -> torch.Tensor:
        hidden = self.embedding(token_ids)
        n = token_ids.shape[1]
        causal_mask = torch.ones((n, n), dtype=torch.bool, device=token_ids.device).triu(1)
        hidden = self.block(hidden, src_mask=causal_mask)
        return self.output(hidden)


def run_cpu_probe(*, seed: int = 17, strength: float = 1.0, position: int = 2) -> dict[str, Any]:
    """Run baseline/sham/text changes and an actual activation injection on CPU.

    Return content-based receipts only. No reported intervention label is
    fabricated, and these receipts are deliberately *not* scorer JSONL rows.
    """
    if type(seed) is not int or seed < 0 or seed >= 2**63:
        raise ValueError("seed must be an integer between 0 and 2**63-1")
    if type(position) is not int or not 0 <= position < len(_INPUT_IDS):
        raise ValueError("position must be within the token sequence")
    if type(strength) not in (int, float) or not math.isfinite(strength) or strength <= 0:
        raise ValueError("strength must be positive and finite")

    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        model = TinyCausalDecoder().to(device="cpu")
        model.eval()
        reference_tokens = torch.tensor([_INPUT_IDS], dtype=torch.long, device="cpu")
        text_tokens = reference_tokens.clone()
        text_tokens[0, position] = (text_tokens[0, position] + 1) % _VOCAB_SIZE
        patch_vector = torch.zeros((_DIM,), dtype=torch.float32)
        patch_vector[0] = strength
        calls = 0
        hidden_changed = False

        def insert_patch(module: nn.Module, inputs: tuple[torch.Tensor, ...], output: torch.Tensor) -> torch.Tensor:
            nonlocal calls, hidden_changed
            calls += 1
            altered = output.clone()
            altered[:, position, :] += patch_vector
            hidden_changed = not torch.equal(output, altered)
            return altered

        with torch.no_grad():
            reference_logits = model(reference_tokens)
            sham_logits = model(reference_tokens)  # no patch registered
            text_logits = model(text_tokens)  # no patch registered
            handle = model.embedding.register_forward_hook(insert_patch)
            try:
                changed_logits = model(reference_tokens)
            finally:
                handle.remove()

        if calls != 1:
            raise RuntimeError(f"expected one executed hook, got {calls}")
        if not torch.equal(reference_logits, sham_logits):
            raise RuntimeError("sham unexpectedly differs from reference")
        if not hidden_changed or torch.equal(reference_logits, changed_logits):
            raise RuntimeError("activation intervention did not change logits")
        if not torch.equal(reference_logits[:, :position], changed_logits[:, :position]):
            raise RuntimeError("causal patch unexpectedly changed earlier positions")

        return {
            "schema": "are-selfmodel-cpu-probe-1",
            "evidence_level": "instrumentation_only",
            "architecture": "random_untrained_toy_decoder",
            "hardware": "cpu",
            "torch_version": torch.__version__,
            "seed": seed,
            "strength": strength,
            "position": position,
            "weights_sha256": _sha256_weights(model),
            "patch_vector_sha256": _sha256_tensor(patch_vector),
            "reference": {
                "input_sha256": _sha256_tensor(reference_tokens),
                "logits_sha256": _sha256_tensor(reference_logits),
            },
            "sham": {
                "hook_calls": 0,
                "identical_to_reference": torch.equal(sham_logits, reference_logits),
                "logits_sha256": _sha256_tensor(sham_logits),
            },
            "text_control": {
                "hook_calls": 0,
                "identical_input": torch.equal(text_tokens, reference_tokens),
                "input_sha256": _sha256_tensor(text_tokens),
                "logits_sha256": _sha256_tensor(text_logits),
            },
            "intervention": {
                "hook_calls": calls,
                "hidden_changed": hidden_changed,
                "final_logits_changed": not torch.equal(changed_logits, reference_logits),
                "max_abs_change": float((changed_logits - reference_logits).abs().max().item()),
                "earlier_positions_identical": torch.equal(
                    reference_logits[:, :position], changed_logits[:, :position]
                ),
                "logits_sha256": _sha256_tensor(changed_logits),
            },
            "behavioral_self_report_measured": False,
            "subjective_consciousness_inferred": False,
        }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--position", type=int, default=2)
    parser.add_argument("--strength", type=float, default=1.0)
    parser.add_argument("--output", type=Path, help="Write the factual CPU receipt to a JSON file")
    args = parser.parse_args(argv)
    receipt = run_cpu_probe(seed=args.seed, position=args.position, strength=args.strength)
    rendered = json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
