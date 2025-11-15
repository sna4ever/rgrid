# RGrid – Runner Lifecycle (Condensed)

Steps on a worker node:
1. Startup: Docker + runner installed by cloud-init; runner registers with API.
2. Loop:
   - claim job (using internal API backed by DB queue).
   - create `/work/<job_id>` directory.
   - download input files via presigned GET URLs.
   - optionally write inline code from JobSpec.
   - run Docker container with `-v /work/<job_id>:/app -w /app` and CPU/mem limits.
   - stream logs back to API.
   - upload outputs defined in `files.outputs` via presigned PUT URLs.
   - record artifacts + execution status.
   - clean up `/work/<job_id>`.
3. Heartbeats: send regular health pings to API.
4. Drain: stop claiming jobs when node is marked draining; finish active jobs; exit so orchestrator can terminate the VM.
