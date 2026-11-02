# Working with jobs and files

In examples below `CLIENT` means `python3 /absolute/path/to/slurm-cluster/scripts/aces.py`; substitute the user's remote paths/account. Global flags precede the subcommand. Commands return nonzero on errors; SSH/site notices can appear on stderr.

```text
CLIENT resources gpu
CLIENT resources projects
CLIENT mkdir /absolute/remote/run-directory
CLIENT upload ./train.py /absolute/remote/run-directory/train.py
CLIENT submit --check --workdir /absolute/remote/run-directory run.sbatch
CLIENT submit --workdir /absolute/remote/run-directory run.sbatch -- --account=YOUR_PROJECT
CLIENT jobs
CLIENT jobs JOB_ID
CLIENT logs /absolute/remote/run-directory/train-JOB_ID.out
CLIENT download /absolute/remote/run-directory/results.json ./results.json
CLIENT cancel JOB_ID
```

SCP copies files/directories recursively and may overwrite destinations; use unique run directories. It does not delete destination-only files or synchronize deltas. Local source is resolved to an absolute path; remote paths must be absolute. Use `rsync` directly when resuming large transfers is needed; with isolated ACES config use `rsync -e 'ssh -F ~/.ssh/aces/config' ...`. Check quota and transfer only the requested files, not whole homes or credentials.

Submit transmits the local batch script via stdin. Other code/data must exist remotely. `--workdir` selects an existing remote directory. Put environment activation and resource directives in standard Slurm scripts; extra sbatch options follow the script. Output directories must exist before submission; `%j` separates job logs. Do not rely on local shell variables inside `#SBATCH` lines.

`--check` uses `sbatch --test-only`: an estimated ID/start time is not a job submission. `submit` returns after acceptance; remote jobs survive agent exit. On an uncertain SSH disconnect, inspect jobs/accounting and named logs before retrying. Keep the accepted ID. `jobs ID` uses sacct and may briefly lag. Query scontrol directly for pending reasons or full job configuration. Pending resources are not a program failure; inspect limits/account/QOS/reservations before changing requested hardware.

Use authorized cancellation for the user's selected job only. Check the batch exit code and expected artifacts after completion. A saved checkpoint should be reloadable; for training verify finite loss and actual parameter changes, not just a process exiting zero. Record node/framework/device and distinguish GPU allocator peak from board usage and Slurm host RAM.

## Local access to a model API

Run the model service inside the authorized GPU job, then forward a local loopback port through the login host to the allocated compute node. With the user's existing SSH alias, the shape is:

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8000:COMPUTE_NODE:MODEL_PORT CLUSTER_ALIAS
```

Replace the node/port/alias with the running job's values. For ACES isolated SSH configuration, also pass `-F ~/.ssh/aces/config`. A forward terminating on the login host connects to the compute node's network interface: a service listening only on compute-node `127.0.0.1` is unreachable by this route. If using a network listener, require API authentication. A tunnel terminating on the compute node can instead reach its loopback listener, but verify that site's compute-node SSH access/forwarding first.

Keep API keys out of logs, source, URLs, published artifacts and terminal output. A short pilot can use an owner-readable endpoint file in a private remote run directory; consume the key in client memory. Verify health, unauthorized rejection, and a real authenticated generation through the local tunnel. A local listener or login-node SSH banner alone does not establish model API reachability. Record local round-trip latency separately from server generation time and distinguish a minimal completion endpoint from a full OpenAI-compatible or streaming implementation.

After the pilot, stop its service/job, close the local tunnel and confirm terminal Slurm state. Production use requires its own lifetime, authentication and performance decisions. ACES GPU/PVC jobs have a documented 48-hour maximum; resubmission can queue/change nodes and require tunnel updates. SU charges accrue while resources are allocated, including idle API time. Credential renewal affects reconnects separately from the running job.

## Other clusters

```text
CLIENT --host YOUR_SSH_ALIAS resources partitions
CLIENT --host YOUR_SSH_ALIAS submit --workdir /your/cluster/path run.sbatch
CLIENT --host YOUR_SSH_ALIAS jobs
```

Uses the user's normal SSH config; no ACES renewal. Generic resources are raw `sinfo` node/GRES/CPU/memory state, not a promise of free GPUs. Generic projects uses `sacctmgr show assoc` if allowed; it is association data, not remaining quota. If unavailable, consult that site's account command/admin. Standard submission/query/log/transfer commands are reusable, but partitions, GRES naming, limits, scratch paths, modules and auth are site-specific. Do not run ACES setup for another cluster or assume it has PVC.

Source: https://slurm.schedmd.com/documentation.html
