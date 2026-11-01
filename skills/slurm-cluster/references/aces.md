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

Compute-node internet generally uses `module load WebProxy`; verify endpoint behavior in the job. Do not train/install huge environments on login nodes. Check shared/user environment paths and permissions for this account.

Sources (recheck when site behavior changes):
- https://hprc.tamu.edu/kb/User-Guides/ACES/Access/
- https://hprc.tamu.edu/kb/User-Guides/ACES/Batch/
- https://hprc.tamu.edu/kb/Software/WebProxy/
- https://hprc.tamu.edu/kb/User-Guides/AMS/
