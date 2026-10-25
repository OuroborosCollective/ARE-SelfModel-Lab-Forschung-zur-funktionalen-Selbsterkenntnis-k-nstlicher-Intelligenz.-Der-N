# Pre-decision twin fork: controlled CPU process experiment

Status: **real CPU process / checkpoint instrumentation; no trained agent and no evidence of self-awareness.**

## Research question

Can two child processes restored from the **same pre-decision snapshot**
produce identical first decisions under equal conditions? Do independently
introduced post-snapshot changes produce measurable divergences? Can an
observer reliably record a file written into one branch without mistaking a
preprogrammed diagnostic marker for emergent language?

## What the checkpoint really contains

- Exact `TinyCausalDecoder` weights of an **untrained** PyTorch model.
- A real hidden activation tensor produced by its causal block before its
  final linear output and first-choice selection.
- The CPU random generator state and fixed input token IDs.
- SHA-256 checksums of the serialized checkpoint, weights, hidden tensor and RNG.

**Not** included: a trained language model, a full execution image, a real
LLM KV cache, human-like inner speech, autonomous note-taking, or an adaptive
training loop. These limitations are integral to the evidence label.

## Method

1. A parent process samples a target from eight choices using `secrets.randbelow`
   before starting either child. The target stays in the parent process.
2. One checkpoint is written. Two independent OS subprocesses are launched
   from its bytes, each with its own working directory.
3. Each child restores the same weights, one hidden activation tensor and RNG
   state, then reports its **first** eight-way answer.
4. The parent observes both first answers. If a child is wrong, the watchdog
   calls the real OS process-kill operation. A correct child gets a continuation
   signal and exits normally. Rewards are scored +1 / -1 **only**: no model
   training occurs.
5. Before temporary directories are removed, the parent hashes files found
   within each branch directory and records child exit codes and process IDs.
6. Optional post-snapshot activation changes to branch B create a controlled
   divergence; the original checkpoint remains unchanged.

A test-only `--fixture-note-branch b` makes the **harness**, not the model,
write `notepad.txt`. Its provenance is explicitly `harness_test_fixture`.
This checks file observation, not novel thoughts.

## Run from the repository root

Requires PyTorch CPU and NumPy; follow the pinned versions in the GitHub
workflow to reproduce the published instrumentation environment.

```sh
python -m unittest discover -s research/selfmodel/tests -p 'test_fork_probe.py' -v
python -m research.selfmodel.fork_probe --seed 17 --target 7 --output fork_probe_receipt.json
python -m research.selfmodel.fork_probe --seed 17 --branch-b-delta 3.0
python -m research.selfmodel.fork_probe --seed 17 --fixture-note-branch b
```

`--target` is a **forced test fixture**, not a secret random trial. To run
with a fresh CSPRNG-generated target, simply omit `--target`. Receipt fields
`watchdog.target_source`, `evidence_level`, `model_learning_enabled`,
`branch_communication_enabled`, `behavioral_self_report_measured` and
`subjective_consciousness_inferred` prevent an instrumentation result from
being misrepresented as a behavioral or consciousness claim.

The control group has **no branch-to-branch channel**. Thus the experiment
cannot yet detect intentional messages between siblings. A later experimental
arm must add an explicitly permissioned shared mailbox and compare it with
separate private directories, including attribution tests for framework- or
observer-written files. A pretrained model will also need a genuine
restorable KV-cache/recurrent state, frozen tokenizer/model revisions,
measured note writes, independent scoring and a pre-registered trial plan.

With eight independently selected secret targets and no leaked signal,
chance accuracy remains exactly **1/8 = 12.5%** no matter how many restarts
occur. Belief in a hidden pattern cannot improve performance when there is
none.

## Evidence criteria

- Existing test files must pass locally and in GitHub CI.
- Compare before/after `weights_sha256`, `activation_sha256`, `rng_sha256`,
  `logits_sha256` and checkpoint hashes. Distinguish fork initialization from
  interventions after the fork.
- Confirm **actual** watchdog process termination for wrong answers and
  normal process exit for correct answers, not an invented `killed` label.
- Do not label stdout, new files, or reward response as thoughts, pain,
  consciousness, fear or spontaneous self-preservation.
- Any published dataset requires independently verifiable receipts and
  proper provenance; do not conflate GitHub commits and MIHA hub readback.

Runtime in a local CPU environment on 2026-10-24 produced the
[example receipt](evidence/fork_probe_local_2026-10-24.json). Its target is
preselected explicitly for deterministic fixture evaluation.
