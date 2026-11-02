# Slurm Cluster Agent Skill

[简体中文](README.md) | [English](README.en.md)

Let an agent use ACES and other Slurm clusters over SSH. The skill provides operating guidance and PVC/XPU adaptation knowledge; the Python standard-library CLI handles setup, certificate renewal, transfers and job operations. Supports macOS/Linux; on Windows, use the Linux workflow below through WSL2. Requirements: Python 3.9+ and OpenSSH 9+.

```bash
git clone https://github.com/jz0204/slurm-cluster-skill.git
cd slurm-cluster-skill
```

## Windows (WSL2)

Follow the [Microsoft WSL installation guide](https://learn.microsoft.com/en-us/windows/wsl/install). In an administrator PowerShell window, run:

```powershell
wsl --install
```

Restart if prompted, open Ubuntu and create a Linux user. Then install dependencies in the **WSL Ubuntu terminal**:

```bash
sudo apt update
sudo apt install -y python3 openssh-client git
python3 --version
ssh -V
```

Confirm Python ≥3.9 and OpenSSH ≥9. Clone the repository into your WSL Linux home, such as `~/slurm-cluster-skill`, and run this guide's Bash commands there. The agent should also execute these commands in WSL. SSH configuration and credentials use WSL's `~/.ssh/aces/`. Keep the repository and credentials on the Linux file system to avoid `/mnt/c` [permission differences](https://learn.microsoft.com/en-us/windows/wsl/file-permissions). Certificates downloaded in a Windows browser can be passed to `install-cert` using a `/mnt/c/Users/.../Downloads/...` path; it copies them into WSL's credential directory. Save submitted `.sbatch` files with LF line endings.

WSL2 is the intended Linux compatibility path. End-to-end operation has not yet been tested on a Windows/WSL machine; running directly in native PowerShell/CMD is not currently supported.

## Give it to an agent

Tell the agent:

> Read `skills/slurm-cluster/SKILL.md` in this repository, help me configure my own ACES account, and follow its workflow to use the cluster.

Agents supporting standard skills can install the entire `skills/slurm-cluster` folder. For Codex, run this from the repository root; inspect any existing skill with the same name first rather than overwriting it:

```bash
mkdir -p ~/.codex/skills
ln -s "$PWD/skills/slurm-cluster" ~/.codex/skills/slurm-cluster
```

Restart or refresh the agent's skill discovery, then invoke `$slurm-cluster`. Downloading the repository alone may not make it discoverable; you can also explicitly ask the agent to read SKILL.md. The skill folder is self-contained and can be shared without local experiment history.

## First-time ACES setup

```bash
./aces setup --user YOUR_ACES_USERNAME
# Sign in to the ACES portal and download your matching private key/certificate pair.
./aces install-cert /path/to/id_aces_tamu /path/to/id_aces_tamu-cert.pub
```

Setup writes an isolated `~/.ssh/aces/config` without changing your global SSH configuration. On the first connection, verify host keys according to HPRC guidance using `ssh -F ~/.ssh/aces/config aces`. Each user needs their own account and allocation; this repository supplies no shared account or credentials.

First-time access and expired certificates require portal/SSO/MFA login. While a certificate is valid, renewal needs no browser: before each ACES remote operation, the CLI checks its validity and automatically renews it when less than 12 hours remain. There is no background renewal while the computer sleeps or the CLI is unused. `--no-renew` disables renewal for the current command; `./aces renew` renews manually. Previous credentials and protected staging directories are retained for recovery. No scheduled task is installed.

## Everyday use

```bash
./aces auth
./aces resources gpu                 # gpu / cpu / partitions / projects
./aces mkdir /absolute/remote/run
./aces upload ./train.py /absolute/remote/run/train.py
./aces submit --check --workdir /absolute/remote/run train.sbatch
./aces submit --workdir /absolute/remote/run train.sbatch -- --account=YOUR_PROJECT
./aces jobs
./aces jobs 1234567
./aces logs /absolute/remote/run/train-1234567.out
./aces download /absolute/remote/run/results.json ./results.json
./aces cancel 1234567
```

`submit` transmits and submits only the local sbatch script; upload training code and data separately first. `--check` does not submit a job. Once Slurm accepts a job, it runs independently of the agent's connection. Transfers can overwrite destinations; use a separate run directory. If the submission response is lost, inspect the queue before retrying. See [Slurm operations](skills/slurm-cluster/references/slurm.md).

For other clusters, use an existing SSH alias:

```bash
./aces --host OTHER_CLUSTER resources partitions
./aces --host OTHER_CLUSTER jobs
./aces --host OTHER_CLUSTER submit --workdir /remote/run train.sbatch
```

Generic mode reuses standard Slurm/SCP without ACES certificate renewal. It does not guess another cluster's account, partition, environment or quota. The CLI retains the name `aces` for compatibility.

## PVC requires more than submission flags

The [PVC guide](skills/slurm-cluster/references/pvc.md) helps the agent inspect CUDA dependencies, choose an XPU environment, verify forward/backward execution and checkpoints, then assess single-GPU LoRA, QLoRA or multiple GPUs. A small [XPU probe](skills/slurm-cluster/scripts/xpu_probe.py) and [Slurm template](skills/slurm-cluster/assets/pvc-probe.sbatch) are included; confirm the resource budget before running them.

Live checks have verified ACES certificate renewal over SSH, single-GPU CNN training with Torch 2.7 XPU, and CodeLlama 7B BF16 generation, short-sequence LoRA updates, adapter save/reload and local API calls through an SSH tunnel. An older Torch 2.1/IPEX environment failed to detect XPU. Shared paths and software versions can change, so the skill requires rechecking them. These small tests do not establish model-quality improvement, vLLM compatibility, quantization or distributed training.

Qwen2.5-1.5B-Instruct was also tested with the real OpenAI SDK and lm-eval generation backend. No formal GIS evaluation ran, and JSON outputs failed strict parsing. The [benchmark guide](skills/slurm-cluster/references/benchmarks.md) distinguishes API capabilities from evaluation results; the [ACES guide](skills/slurm-cluster/references/aces.md#capacity-and-queue-statistics) covers GPU/queue statistics and SU posting limitations.

## Validation and distribution

```bash
python3 -m unittest -v test_aces.py
```

Tests use real OpenSSH keys/certificates to check installation, rejection of expired/mismatched pairs, backups, permissions, SSH configuration resolution and automatic-renewal behavior. The CLI does not depend on PyYAML; the official skill validator requires it and can run in a separate development environment.

Distribute `skills/slurm-cluster/` or an archive of that folder. Existing HANDOFF, analysis and benchmarks are private local investigation/experiment records containing account information and are excluded by `.gitignore`; do not publish an archive of the entire workspace. No open-source license has been specified.
