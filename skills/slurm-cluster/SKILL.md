---
name: slurm-cluster
description: Operate Slurm HPC clusters through SSH, including ACES certificate setup and renewal, resource and allocation checks, file transfer, batch jobs, and Intel PVC/XPU workload adaptation. Use when a user wants an agent to run or troubleshoot work on a Slurm cluster.
---

# Slurm cluster operations

Use the bundled `scripts/aces.py` with Python 3 and OpenSSH. Resolve paths from this skill directory, not the user's working directory. It supports macOS/Linux; Windows users should use WSL with its own SSH configuration.

## Select the path

- ACES onboarding/authentication: read [references/aces.md](references/aces.md). Each user needs their own resource account/allocation. The skill supplies no credentials or entitlement.
- Upload, submit, monitor, collect results: read [references/slurm.md](references/slurm.md). `--host OTHER_ALIAS` uses an already configured SSH alias for other Slurm clusters; ACES auth/resources/environment assumptions do not transfer.
- Intel PVC or CUDA-to-XPU adaptation: read [references/pvc.md](references/pvc.md) before selecting an environment or editing training code. Idle GPU counts alone do not establish suitability.

## Execution contract

Identify the user's cluster/account, workload, remote working directory and resource/time budget from the request and available configuration. Ask only for missing decisions that materially change the work. Existing authorization carries forward; this skill does not itself authorize submissions, data uploads or credential changes. A request to install/teach the skill is not permission to run training.

Use CLI help for syntax. Prefer SSH and Slurm over portal automation. ACES operations automatically renew a still-valid local certificate with less than 12 hours remaining; expiry/bootstrap needs user portal login. `--no-renew` makes resource queries read-only with respect to credentials. No daemon is installed.

Keep computation inside a Slurm allocation. Submit one authorized pilot before scaling a new environment. Record job ID, partition/GRES, environment, code/data paths and log/output paths. A successful `sbatch` means accepted, not trained. Confirm terminal state, exit code and workload output; an empty `squeue` is not proof of success. Never blindly retry an ambiguous submission.

Use scheduler-provided device visibility. Do not override GPU masks to reach unallocated hardware. Never silently fall back to CPU for a GPU task. Preserve failed-run logs and original code. Use user-owned environments or containers; do not modify shared environments.

Report what was actually verified: configuration, allocation, GPU operation, learning/checkpoint behavior, and performance are separate claims. Record new cluster-specific pitfalls in the user's project handoff/run notes, not as universal rules or copied personal account data in this distributable skill.
