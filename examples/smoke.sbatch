#!/bin/bash
#SBATCH --job-name=aces-cli-smoke
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=256M
#SBATCH --time=00:01:00
#SBATCH --output=aces-cli-smoke-%j.out
set -eu
hostname
printf 'ACES CLI submission works. Job: %s\n' "$SLURM_JOB_ID"
