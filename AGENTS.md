# Working on this repository

For using a cluster, read `skills/slurm-cluster/SKILL.md` and only the relevant references. This repository does not itself authorize compute jobs, transfers or credential issuance.

For implementation, keep the CLI standard-library-only. Its source is `skills/slurm-cluster/scripts/aces.py`; the root `aces` is a compatibility entrypoint. Run `python3 -m unittest -v test_aces.py` after changes. Preserve existing SSH configuration and local research artifacts. Read HANDOFF.MD if present before changing cluster behavior; it is private local history, not a portable cluster profile.
