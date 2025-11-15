# RGrid – Container Security (Condensed)

Hardening measures:
- Docker containers run non-root where possible.
- `--cap-drop=ALL`, `--read-only`, `--network=none` by default.
- Only `/work/<job_id>` is writable inside container, mounted as `/app`.
- CPU/memory/pids are limited per job using cgroups.
- No secrets (DB, storage creds, API keys) are mounted or injected.
- Nodes are ephemeral; rebuilt often to reduce risk of long-lived compromise.

Future:
- Add seccomp profiles.
- Optional network-enabled jobs behind stricter policies.
