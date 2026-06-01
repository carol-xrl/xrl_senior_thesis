# Auto-Experiment Queue Skill

This skill describes how the experiment queue works: how to define experiments, how the runner dispatches them, and how to monitor progress.

---

## Goal

Make full use of the GPU server by maintaining a topology-aware queue of experiments. The runner monitors GPU utilisation and automatically launches the next eligible experiment when the current one finishes, keeping the GPU as busy as possible within the 24-hour rental window.

---

## Overview

```
experiment_queue.yaml        ← single source of truth for all experiments
        │
        ▼
queue_runner.py              ← monitors GPU, respects dependencies, dispatches jobs
        │
        ├─── tmux session per job  (st_job_<name>)
        └─── st/outputs/logs/<name>.log
```

1. A **queue file** (`st/configs/experiment_queue.yaml`) lists every experiment: its script, config, dependencies, and estimated resource cost.
2. The **queue runner** (`st/scripts/queue_runner.py`) runs in its own tmux session (`st_queue`). Every 60 seconds it checks GPU utilisation. If utilisation has been below `gpu_idle_threshold` (default 20%) for at least 60 seconds **and** the current job has exited, it launches the next experiment that has all its dependencies satisfied.
3. Each job runs in its own tmux session and logs to `st/outputs/logs/<name>.log`.

---

## Queue File Format

`st/configs/experiment_queue.yaml`

```yaml
# Global settings
settings:
  gpu_idle_threshold: 20        # % GPU utilisation considered "idle"
  idle_duration_secs: 60        # seconds below threshold before next job launches
  log_dir: st/outputs/logs
  checkpoint_dir: /workspace/data/cpjump1/checkpoints

experiments:
  # --- Ablation: normalization ---
  - name: ablation_norm_none
    script: st/scripts/train.py
    config: st/configs/ablations/norm_none.yaml
    depends_on: []              # no dependencies, can run first
    estimated_gpu_hrs: 0.5
    smoke_tested: true

  - name: ablation_norm_plate
    script: st/scripts/train.py
    config: st/configs/ablations/norm_plate.yaml
    depends_on: []
    estimated_gpu_hrs: 0.5
    smoke_tested: true

  - name: ablation_norm_tvn
    script: st/scripts/train.py
    config: st/configs/ablations/norm_tvn.yaml
    depends_on: []
    estimated_gpu_hrs: 0.5
    smoke_tested: true

  # --- Ablation: loss ---
  - name: ablation_loss_mse
    script: st/scripts/train.py
    config: st/configs/ablations/loss_mse.yaml
    depends_on: []
    estimated_gpu_hrs: 0.5
    smoke_tested: true

  - name: ablation_loss_fourier
    script: st/scripts/train.py
    config: st/configs/ablations/loss_fourier.yaml
    depends_on: []
    estimated_gpu_hrs: 0.5
    smoke_tested: true

  - name: ablation_loss_fourier_cc
    script: st/scripts/train.py
    config: st/configs/ablations/loss_fourier_cc.yaml
    depends_on: []
    estimated_gpu_hrs: 0.5
    smoke_tested: true

  # --- Final model (depends on ablations being done) ---
  - name: final_dinov2b
    script: st/scripts/train.py
    config: st/configs/final_dinov2b.yaml
    depends_on:
      - ablation_norm_tvn
      - ablation_loss_fourier_cc
    estimated_gpu_hrs: 2.0
    smoke_tested: true

  # --- Evaluation (depends on final model checkpoint) ---
  - name: eval_all_axes
    script: st/scripts/evaluate.py
    config: st/configs/eval.yaml
    depends_on:
      - final_dinov2b
    estimated_gpu_hrs: 0.5
    smoke_tested: true
```

**Fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✓ | Unique identifier; used for log filename and tmux session name |
| `script` | ✓ | Path to Python entry point, relative to repo root |
| `config` | ✓ | Path to YAML config passed as `--config` argument |
| `depends_on` | ✓ | List of experiment names that must have `status: done` before this one runs. Use `[]` for no dependencies |
| `estimated_gpu_hrs` | ✓ | Rough estimate; used only for ETA display, not for scheduling |
| `smoke_tested` | ✓ | **Must be `true` before the runner will dispatch the job.** Set to `false` while developing |

---

## Dependency Topology

The runner does a topological sort at startup. A job becomes **eligible** when:

1. All jobs in `depends_on` have `status: done`.
2. The GPU has been idle for `idle_duration_secs`.
3. The job itself has `smoke_tested: true`.

If multiple jobs are eligible simultaneously (e.g., all normalization ablations have no dependencies), they are dispatched **one at a time** in queue order — the runner waits for the current job to finish before launching the next, because a single L40S is the bottleneck.

---

## Smoke Test Protocol

Before setting `smoke_tested: true` on any experiment, run it manually with a minimal data slice to confirm it runs end-to-end without crashing:

```bash
# Example smoke test: 2 wells, 2 epochs
python st/scripts/train.py \
  --config st/configs/ablations/loss_fourier_cc.yaml \
  --wells A01 A02 \
  --epochs 2 \
  --smoke-test

# Check exit code
echo $?   # must be 0
```

A smoke test must verify:
- Data loading works (correct TIFF paths, channel count, normalization).
- Forward pass runs without OOM.
- Loss is finite (not NaN) after step 1.
- Checkpoint saving works.
- Metric logging writes to `st/outputs/metrics/`.

Only after a clean smoke test run, set `smoke_tested: true` in the queue file and commit.

---

## Running the Queue

```bash
# Start a dedicated tmux session for the runner
tmux new -s st_queue
cd /workspace/xrl_senior_thesis_run

# Launch the runner
python st/scripts/queue_runner.py \
  --queue st/configs/experiment_queue.yaml \
  --state  st/outputs/queue_state.yaml \
  2>&1 | tee st/outputs/logs/queue.log
```

The runner writes live status to `st/outputs/queue_state.yaml`:

```yaml
# auto-generated by queue_runner.py — do not edit manually
experiments:
  ablation_norm_none:
    status: done          # pending | running | done | failed
    started_at: "2025-06-01T10:02:11"
    finished_at: "2025-06-01T10:34:55"
    tmux_session: st_job_ablation_norm_none
    log: st/outputs/logs/ablation_norm_none.log

  ablation_loss_fourier_cc:
    status: running
    started_at: "2025-06-01T10:35:10"
    finished_at: null
    tmux_session: st_job_ablation_loss_fourier_cc
    log: st/outputs/logs/ablation_loss_fourier_cc.log

  final_dinov2b:
    status: pending
    ...
```

---

## Monitoring

```bash
# Queue runner log (shows which job just launched, ETA)
tail -f st/outputs/logs/queue.log

# Specific job log
tail -f st/outputs/logs/ablation_loss_fourier_cc.log

# GPU utilisation
watch -n 5 nvidia-smi

# List all active tmux sessions
tmux ls

# Attach to a running job
tmux attach -t st_job_ablation_loss_fourier_cc
```

---

## Failure Handling

If a job exits with a non-zero code, the runner:
1. Marks it `status: failed` in `queue_state.yaml`.
2. Logs the exit code and last 20 lines of the job's log.
3. **Does not launch dependents** of the failed job.
4. Continues launching other eligible jobs that do not depend on the failed one.

To retry a failed job, manually set its status back to `pending` in `queue_state.yaml` and ensure the underlying issue is fixed.

---

## Key Rules

- **Never add an experiment with `smoke_tested: false` to the queue.** The runner will refuse to dispatch it, but keeping unvalidated entries in the file creates confusion.
- **One GPU, one job at a time.** Do not attempt concurrent training runs on the L40S.
- **Queue file is committed to git.** State file (`queue_state.yaml`) is gitignored (it is a runtime artifact).
- **Estimated hours are informational only.** Actual scheduling is purely event-driven (job exit + GPU idle).