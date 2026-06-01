# RunPod Skill

This skill covers how to SSH into the RunPod server and launch experiments via tmux.

---

## Background

| Item | Value |
|------|-------|
| GPU | NVIDIA H100 (80 GB VRAM) |
| RAM | `<RAM_GB>` GB |
| Disk | `/workspace` (large mounted storage); `/` is a ~50 GB container overlay — do **not** store data there |
| Workspace root | `/workspace/xrl_senior_thesis_run/` |
| Data root | `/workspace/data/cpjump1/` |

> Fill in `<RAM_GB>` after first SSH: run `free -h` to confirm.

---

## 1. SSH onto the Server

**Primary endpoint** (supports `scp` and `rsync`):

```bash
ssh root@<HOST> -p <PORT> -i ~/.ssh/id_ed25519
```

**Fallback endpoint:**

```bash
ssh <POD_ID>@ssh.runpod.io -i ~/.ssh/id_ed25519
```

> Fill in `<HOST>`, `<PORT>`, and `<POD_ID>` from the RunPod dashboard after pod creation.

**First-time setup on a new pod:**

```bash
# Clone repo (use token if private)
git clone https://github.com/carol-xrl/xrl_senior_thesis.git /workspace/xrl_senior_thesis_run
cd /workspace/xrl_senior_thesis_run
git switch ssl

# Install dependencies
pip install -r st/requirements.txt

# Verify GPU
nvidia-smi
df -h   # confirm /workspace has enough space
```

**Subsequent sessions — sync latest code:**

```bash
cd /workspace/xrl_senior_thesis_run
git pull --ff-only origin ssl
```

---

## 2. Directory Layout

```
/workspace/xrl_senior_thesis_run/
  st/
    configs/          # experiment YAML configs
    scripts/          # runnable entry points
    src/              # library code
    skills/           # this file and auto_experiment.md live here
    outputs/
      metrics/        # CSV results — pull back to Mac
      figures/        # plots — pull back to Mac
      logs/           # tmux-redirected stdout/stderr
      checkpoints/    # model weights — stay remote

/workspace/data/cpjump1/
  images/             # raw TIFFs (~130–160 GB for full subset)
  features/           # extracted embeddings
  caches/             # download caches
```

> Raw TIFFs and checkpoints **never** get committed to git or copied back to Mac.

---

## 3. Launching Experiments with tmux

All long-running jobs run inside named tmux sessions so they survive SSH disconnection.

### Named sessions

| Session | Purpose |
|---------|---------|
| `st_download` | Downloading CPJUMP1 images |
| `st_extract` | Feature extraction |
| `st_train` | Model training |
| `st_eval` | Evaluation / metrics |
| `st_queue` | Auto-experiment queue monitor (see `auto_experiment.md`) |

### Starting a session

```bash
tmux new -s st_train
# inside the session:
cd /workspace/xrl_senior_thesis_run
python st/scripts/train.py --config st/configs/dinov2b_fourier.yaml \
  2>&1 | tee st/outputs/logs/train_dinov2b_fourier.log
```

### Detach / reattach

```bash
# detach (keeps job running): Ctrl-B then D
tmux ls                    # list sessions
tmux attach -t st_train    # reattach
```

### Monitoring

```bash
nvidia-smi                            # GPU utilisation + VRAM
watch -n 5 nvidia-smi                 # live refresh every 5 s
df -h /workspace                      # disk usage
tail -f st/outputs/logs/train_dinov2b_fourier.log   # follow log
```

---

## 4. Running the Auto-Experiment Queue

The queue runner lives in a dedicated session and automatically dispatches the next experiment when the GPU is free. See [`auto_experiment.md`](auto_experiment.md) for the full specification.

```bash
tmux new -s st_queue
cd /workspace/xrl_senior_thesis_run
python st/scripts/queue_runner.py --queue st/configs/experiment_queue.yaml \
  2>&1 | tee st/outputs/logs/queue.log
```

> **Before adding any experiment to the queue, run a smoke test first** (see `auto_experiment.md` §Smoke Test).

---

## 5. Pulling Results Back to Mac

```bash
# From Mac — pull metrics and figures only
rsync -avz --progress \
  root@<HOST>:/workspace/xrl_senior_thesis_run/st/outputs/metrics/ \
  ~/Desktop/xrl_senior_thesis/st/outputs/metrics/ \
  -e "ssh -p <PORT> -i ~/.ssh/id_ed25519"

rsync -avz --progress \
  root@<HOST>:/workspace/xrl_senior_thesis_run/st/outputs/figures/ \
  ~/Desktop/xrl_senior_thesis/st/outputs/figures/ \
  -e "ssh -p <PORT> -i ~/.ssh/id_ed25519"
```

> Never rsync `images/`, `checkpoints/`, or `features/` to the Mac.

---

## 6. Practical Rules

- **Mac owns code.** Write and test locally, commit, push, then pull on server.
- **Server owns data and compute.** Images, checkpoints, and embeddings stay in `/workspace`.
- **Git syncs code.** `rsync`/`scp` syncs selected results.
- **Always use tmux.** Never run long jobs directly in an SSH shell.
- **Smoke-test first.** Validate every new script on 2 wells before full-plate runs.