# RGrid – Architecture Decisions (Condensed)

- AD-001: Use Clerk as IdP → no custom auth; we mirror users/accounts minimally.
- AD-002: Multi-tenancy via accounts, projects, memberships tables in Postgres.
- AD-003: Runtime is Docker Engine on worker nodes; containers are ephemeral per job.
- AD-004: Default compute is Hetzner CX22; 1 job per vCPU → 2 jobs/node concurrently.
- AD-005: Queue is Postgres (FOR UPDATE SKIP LOCKED), not Redis.
- AD-006: Artifacts are stored in MinIO, accessed via presigned URLs.
- AD-007: Runner, not container, handles uploads/downloads.
- AD-008: Nodes are ephemeral (~60 min max) for cleanliness and predictable billing.
- AD-009: JobSpec is Kubernetes-inspired (runtime/image, command, env, resources, files, timeout).
