#!/bin/bash
#SBATCH --job-name=xpu-probe
#SBATCH --partition=pvc
#SBATCH --gres=gpu:pvc:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:02:00
#SBATCH --output=xpu-probe-%j.out
set -euo pipefail
# Observed working on ACES 2026-11-01; verify this shared path for your account.
module purge
module load GCC/13.2.0
module load Python/3.11.5
/scratch/data/uv_envs/max_llama/bin/python -u xpu_probe.py
