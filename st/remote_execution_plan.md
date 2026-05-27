# Local And Remote Execution Plan

## Background

There are two machines in the workflow:

1. Local Mac: planning, writing code, reviewing results, committing changes, and talking through decisions.
2. Rented GPU server: downloading CPJUMP1 images, extracting features, training models, running long experiments, and generating raw outputs.

Large image data should stay on the GPU server. The Mac should not download the full image subset unless we are debugging tiny smoke-test examples.

## Current RunPod Pod

Use the direct TCP endpoint for normal work because it supports `scp` and `rsync`:

```bash
ssh root@209.170.80.132 -p 20639 -i ~/.ssh/id_ed25519
```

Fallback endpoint:

```bash
ssh 4ummi44gx59ks6-6441117e@ssh.runpod.io -i ~/.ssh/id_ed25519
```

Observed hardware from the first SSH smoke check:

| Item | Value |
| --- | --- |
| Host | `a80a5edce179` |
| User | `root` |
| GPU | NVIDIA L40S |
| Visible VRAM | 46068 MiB |
| Driver | 570.195.03 |
| RAM | 503 GiB |
| Workspace | `/workspace` |

This matches the recommended single 48GB GPU plan.

## Source Of Truth

Use git as the source of truth for code, configs, and small metadata files.

Default workflow:

1. Write and test lightweight code on the Mac under `st/`.
2. Commit changes on branch `st`.
3. Push branch `st` to `origin`.
4. SSH to the GPU server.
5. Clone or pull the repo on the GPU server.
6. Run experiments on the GPU server.
7. Commit small code/report updates from Mac, not from the server unless necessary.

Data and large artifacts should not be committed.

Keep on GPU server only:

- Raw TIFF images.
- Download caches.
- Model checkpoints.
- Large feature files if they become too large for git.
- Intermediate tensors or embeddings.

Pull back to Mac when useful:

- Metric CSVs.
- Small summary tables.
- Final figures.
- Logs.
- Short experiment reports.

Use `rsync` or `scp` for result transfer if files are not appropriate for git.

## Git Sync Plan

Mac side:

```bash
git switch st
git status
git add st
git commit -m "Add ST benchmark plan"
git push -u origin st
```

GPU server side:

```bash
git clone https://github.com/carol-xrl/xrl_senior_thesis.git
cd xrl_senior_thesis
git switch st
```

For updates:

```bash
git pull --ff-only origin st
```

If the server cannot authenticate to GitHub for private repo access, use one of these fallbacks:

1. Set up a deploy key or GitHub token on the server.
2. Use `rsync` from Mac to server for the `st/` folder.
3. Use `scp` for a tarball snapshot of `st/`.

## Server Directory Layout

Recommended layout on the GPU server:

```text
~/xrl_senior_thesis/
  st/
    configs/
    scripts/
    src/
    outputs/
      metrics/
      figures/
      logs/

/data/cpjump1/
  images/
  features/
  checkpoints/
  caches/
```

The exact `/data` path can change depending on the rented machine. The important rule is that raw images and heavyweight outputs live outside git.

## Tmux Usage

Use separate tmux sessions for long jobs:

```bash
tmux new -s st_download
tmux new -s st_extract
tmux new -s st_train
tmux new -s st_eval
```

Inside each session, redirect logs:

```bash
mkdir -p st/outputs/logs
python st/scripts/example.py 2>&1 | tee st/outputs/logs/example.log
```

When monitoring:

```bash
tmux ls
tmux attach -t st_train
nvidia-smi
df -h
```

First remote pilot sequence:

```bash
git pull --ff-only origin st
python st/scripts/prepare_download_manifest.py --repo-root . --resolve-s3 --wells A01 A02 --dryrun
python st/scripts/prepare_download_manifest.py --repo-root . --resolve-s3 --wells A01 A02
```

Only after the tiny pilot download is verified should we remove `--wells A01 A02` for full plate download.

## SSH Skill To Create Later

After the GPU server is rented and we know:

- SSH hostname.
- SSH username.
- SSH key path.
- Remote working directory.
- GPU type.
- Disk mount path.
- Python/conda/container preference.

Create a dedicated Codex skill for remote experiment execution.

The skill should encode:

1. How to SSH into the server.
2. How to sync the `st` branch or `st/` folder.
3. How to activate the environment.
4. How to launch tmux jobs.
5. How to monitor GPU, disk, logs, and process status.
6. How to pull back metrics and figures.
7. What must never be copied back to the Mac, such as raw TIFF images.

Do not create that skill before server details are known. For now, keep this file as the execution contract.

## Practical Rule

The Mac owns code. The GPU server owns data and long-running compute.

Git synchronizes code. `rsync/scp` synchronizes selected results. Raw images stay remote.
