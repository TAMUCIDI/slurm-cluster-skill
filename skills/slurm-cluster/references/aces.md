# ACES access

## Bootstrap (once per user/machine)

Prerequisites: Python >=3.9, OpenSSH >=9 for SCP's default SFTP transport, an ACES resource account and project allocation. The resource username may differ from ACCESS ID or TAMU NetID. Get the username from the authenticated portal; never copy the author's account.

From this skill directory:

```bash
python3 scripts/aces.py setup --user YOUR_ACES_USERNAME
```

This writes only `~/.ssh/aces/config`, mode 600, and a mode-700 credential directory. Existing global SSH configuration is preserved. Repeating the same setup is harmless; a different existing config is not overwritten. The CLI uses this isolated file automatically; bare `ssh aces` does not. For direct SSH use `ssh -F ~/.ssh/aces/config aces`.

Sign in at https://portal-aces.hprc.tamu.edu, open Utilities → sshca, then download `id_aces_tamu` and `id_aces_tamu-cert.pub` to a protected non-project directory. Opening sshca generates credentials. The script is `/usr/local/bin/gen_ssh_cert.sh`; portal shell is another supported bootstrap path. Browser download dialogs can remember an unrelated project directory: select the location explicitly.

```bash
python3 scripts/aces.py install-cert /path/to/id_aces_tamu /path/to/id_aces_tamu-cert.pub
```

Installation checks the matching key, certificate type and validity, saves mode-600 files and retains the previous pair. It then tests SSH. On a fresh machine host-key trust can require a first interactive connection:

```bash
ssh -F ~/.ssh/aces/config aces
```

Verify jump/target host keys per site guidance. Do not disable checking or delete changed keys to hide a mismatch. If import succeeded but first connection failed on host trust, the credentials are already installed: resolve trust, then retry a query.

## Renewal

```bash
python3 scripts/aces.py auth
python3 scripts/aces.py renew
```

Normal remote commands auto-renew when less than 12h remains. They do not renew after expiry, during idle time, or on generic hosts. `--no-renew` disables this preflight for a command. Querying a queue can therefore update ACES credentials unless this flag is used.

Live-tested 2026-10-31: official generator permits login nodes; SSH generation → SCP retrieval → fresh connection succeeded without browser use. Actual certificate duration was about 48h despite the documentation's 49h. Check the certificate, not a fixed calendar assumption. Validity comparisons use UTC to handle DST changes; `auth` prints ssh-keygen's local-time display.

The generator can return exit zero on error and normally refuses regeneration within an hour. The client checks its success marker and never forces issuance. Run renewals serially. Failed transfers leave active local files unchanged, but remote signing may already have succeeded; retrieve that pair through portal if recovery is needed. Protected staging directories and `.previous` files are retained; no cleanup daemon. Import/renew is not a multi-process credential manager.

If expired or missing, log in to portal again; no bypass of SSO/MFA. Certificate expiry prevents new SSH connections but does not cancel already accepted Slurm jobs. Don't share a personal certificate with teammates or put credentials in a public repo/service.

## Site checks

`resources gpu/cpu/partitions/projects` invokes `gpuavail`, `cpuavail`, `sinfo`, `myproject`. Reserved/down/drained/unavailable devices are not ordinary available capacity. A current count is not a start-time guarantee.

Use `myproject` for allocation/account selection and `showquota` before large uploads. `myproject -j ACCOUNT` was observed to show the current user's job records, not full per-user project billing. Slurm TRES resource hours are not exact AMS SU charges. Request only the resources and duration the workload needs.

AMS can post completed jobs with a delay. Slurm's `AllocTRES billing` did not include the full GPU SU charge in the tested jobs. Label a calculation from actual elapsed time and the current AMS CPU/memory/GPU rates as an estimate until reconciled with posted records. A failed job can still cost SUs; an unchanged balance immediately after completion is not evidence of free compute.

Compute-node internet generally uses `module load WebProxy`; verify endpoint behavior in the job. Do not train/install huge environments on login nodes. Check shared/user environment paths and permissions for this account.

## Capacity and queue statistics

Timestamp each snapshot. Distinguish documented physical inventory, Slurm-configured devices (`CfgTRES`), allocated devices (`AllocTRES`) and ordinary available devices (`gpuavail`). An inventory/configuration gap has unknown physical status until checked; allocated cards are not measured GPU utilization. For an accounting of configured devices, use mutually exclusive categories for allocated, ordinary available, down/drained, idle-reserved and otherwise unavailable cards. Do not call every unallocated card usable or every unavailable card busy.

Use `squeue -r` to expand job arrays; task IDs can contain underscores. Preserve those elements in parsers and reconcile requested GPU totals with node allocations. Inspect pending reasons: per-user GPU limits, array concurrency limits, held jobs and dependencies differ from resource contention. A free GPU does not make every pending job eligible, and queue age does not predict a new job's wait.

For durations, distinguish running elapsed time, requested wall limits, pending age and completed actual runtime. A completed-job average should state its time window, included states, unique job/task count and whether it is weighted by jobs or GPUs; report a median alongside the mean. Successful completions omit still-running and unsuccessful jobs and do not estimate remaining runtime or wait time.

For `sacct`, use `--partition=pvc`; `-p` means parsable output. Keep raw queries and verify nonempty results before summarizing. Explicit start/end timestamps helped resolve an empty query in one investigation, but the cause was not established. For an exact elapsed window across DST, use timezone-aware timestamps and a UTC cutoff; the same local clock time on adjacent dates need not be 24 hours apart.

Sources (recheck when site behavior changes):
- https://hprc.tamu.edu/kb/User-Guides/ACES/Access/
- https://hprc.tamu.edu/kb/User-Guides/ACES/Batch/
- https://hprc.tamu.edu/kb/Software/WebProxy/
- https://hprc.tamu.edu/kb/User-Guides/AMS/
